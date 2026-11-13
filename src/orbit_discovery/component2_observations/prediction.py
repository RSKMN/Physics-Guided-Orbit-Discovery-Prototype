"""Future sky-position prediction for asteroids.

Reuses the Stage 2.2 propagation service and Stage 2.4 observer geometry
to compute predicted positions (RA/Dec, distance, solar elongation) at
arbitrary requested observation epochs.

Output is explicitly separate from synthetic measurement CSV files and
C3 ground-truth data.  The caller decides whether and how to persist
predictions; if a CSV is required the caller must map fields explicitly
and omit any ground-truth columns.
"""

from __future__ import annotations

import math

import numpy as np

from orbit_discovery.component2_observations.observer import (
    calculate_observer_positions,
    calculate_observer_velocities,
    calculate_line_of_sight,
    calculate_sky_coordinates,
    calculate_solar_elongation,
)
from orbit_discovery.core.propagation import propagate_state, propagate_multi

#: Gravitational parameter used by the propagation service (AU^3 / yr^2 in units where Msun=1).
#: NOTE: REBOUND with sim.units = ("yr", "AU", "Msun") sets sim.G = 39.4769 (~4*pi^2),
#: so the *actual* gravitational parameter is 39.4769, not 1.0.  The declaration below is
#: retained for documentation only; computations that must agree with C1's REBOUND
#: propagation use MU_REBOUND.
MU = 1.0

#: Actual gravitational parameter used by REBOUND with sim.units = ("yr", "AU", "Msun").
#: Measured as sim.G = 39.476926421373 with M_sun = 1.0 Msun.
MU_REBOUND = 39.476926421373

#: Small tolerance for classifying an epoch as "inside" the trajectory span.
TRAJECTORY_TOL = 1e-9


class PredictionOutput:
    """Container for a single-epoch prediction result.

    This object is **not** a pandas DataFrame row and must not be written
    directly to an observation CSV.  The caller decides whether and how
    to persist it; if a CSV is required the caller must map fields
    explicitly and omit any ground-truth columns.

    Parameters
    ----------
    epoch_years : float
        Requested observation epoch in decimal years.
    astro_state : dict
        Heliocentric Cartesian state at ``epoch_years``::

            {
                "x_au": float,          # position x in AU
                "y_au": float,          # position y in AU
                "z_au": float,          # position z in AU
                "vx_au_per_year": float,  # velocity x in AU/yr
                "vy_au_per_year": float,  # velocity y in AU/yr
                "vz_au_per_year": float,  # velocity z in AU/yr
            }
    obs_state : dict
        Heliocentric Cartesian state of the observer at ``epoch_years``::

            {
                "x_au": float,
                "y_au": float,
                "z_au": float,
                "vx_au_per_year": float,
                "vy_au_per_year": float,
                "vz_au_per_year": float,
            }
    relative : dict
        Asteroid–observer relative position at ``epoch_years``::

            {
                "x_au": float,          # asteroid x minus observer x in AU
                "y_au": float,          # asteroid y minus observer y in AU
                "z_au": float,          # asteroid z minus observer z in AU
            }
    distance_au : float
        Observer–asteroid distance in AU.
    los_unit : np.ndarray
        Unit vector along the line-of-sight, shape (3,).
    ra_deg : float
        Predicted right ascension in degrees, normalised to [0, 360).
    dec_deg : float
        Predicted declination in degrees, in [-90, 90].
    elongation_deg : float
        Solar elongation angle in degrees (angle at the observer between
        the Sun and the asteroid).
    frame : str
        Declared coordinate frame, currently ``"equatorial_j2000"``.
    time_metadata : dict
        Metadata about the epoch and propagation method.
    """

    def __init__(
        self,
        epoch_years: float,
        astro_state: dict,
        obs_state: dict,
        relative: dict,
        distance_au: float,
        los_unit: np.ndarray,
        ra_deg: float,
        dec_deg: float,
        elongation_deg: float,
        frame: str,
        time_metadata: dict,
    ):
        self.epoch_years = epoch_years
        self.astro_state = astro_state
        self.obs_state = obs_state
        self.relative = relative
        self.distance_au = distance_au
        self.los_unit = los_unit
        self.ra_deg = ra_deg
        self.dec_deg = dec_deg
        self.elongation_deg = elongation_deg
        self.frame = frame
        self.time_metadata = time_metadata

    def __repr__(self) -> str:
        return (
            f"PredictionOutput(epoch={self.epoch_years:.4f} yr, "
            f"RA={self.ra_deg:.3f}°, Dec={self.dec_deg:.3f}°, "
            f"elong={self.elongation_deg:.3f}°, dist={self.distance_au:.4f} AU)"
        )


def _validate_epoch(epoch_years: float) -> None:
    """Reject unsupported invalid epoch values.

    Parameters
    ----------
    epoch_years : float
        Requested observation epoch in decimal years.

    Raises
    ------
    ValueError
        If ``epoch_years`` is negative, NaN or infinite.
    """
    if epoch_years < 0:
        raise ValueError("Requested epoch must be >= 0 yr; negative times are not supported.")
    if not math.isfinite(epoch_years):
        raise ValueError("Requested epoch must be a finite number.")


def _classify_epoch(epoch_years: float, trajectory) -> str:
    """Determine whether an epoch is inside or beyond the trajectory span.

    Parameters
    ----------
    epoch_years : float
        Requested observation epoch.
    trajectory : dict or None
        Trajectory data dict as returned by ``loader.load_trajectory``.
        If ``None`` the epoch is always treated as "beyond".

    Returns
    -------
    str
        Either ``"inside"`` or ``"beyond"``.
    """
    if trajectory is None:
        return "beyond"
    times = trajectory["time_years"]
    # Epoch is inside if it falls within the inclusive span (with tiny tolerance)
    if times[0] - TRAJECTORY_TOL <= epoch_years <= times[-1] + TRAJECTORY_TOL:
        return "inside"
    return "beyond"


def predict_from_state(
    astro_x_au: float,
    astro_y_au: float,
    astro_z_au: float,
    astro_vx_au_per_year: float,
    astro_vy_au_per_year: float,
    astro_vz_au_per_year: float,
    epochs_years: list[float],
    observer: object | None = None,
    trajectory: dict | None = None,
) -> list[PredictionOutput]:
    """Predict sky positions for one asteroid at multiple epochs.

    Uses the shared propagation service to obtain the asteroid heliocentric
    state at each requested epoch.  For epochs inside the trajectory span
    linear interpolation is used; beyond the span REBOUND IAS15 numerical
    integration is performed.

    Parameters
    ----------
    astro_x_au, astro_y_au, astro_z_au : float
        Initial heliocentric Cartesian position of the asteroid in AU.
    astro_vx_au_per_year, astro_vy_au_per_year, astro_vz_au_per_year : float
        Initial heliocentric Cartesian velocity of the asteroid in AU/year.
    epochs_years : list of float
        Requested observation epochs in decimal years.  Must be >= 0.
    trajectory : dict or None, optional
        Trajectory data as returned by ``loader.load_trajectory``.  If
        provided, epochs inside the trajectory span are interpolated;
        epochs beyond are propagated with REBOUND IAS15.
    observer : object or None, optional
        Observer configuration object passed to ``calculate_observer_positions``
        and ``calculate_observer_velocities``.  If ``None`` the default
        Earth-like circular observer (1 AU, 1 yr period, phase 90°) is used.

    Returns
    -------
    list of ``PredictionOutput``
        One result per requested epoch, in the same order.

    Raises
    ------
    ValueError
        If any epoch is negative, non-finite, or if propagation fails.
    """
    # Validate all epochs up front
    for t in epochs_years:
        _validate_epoch(t)

    n = len(epochs_years)
    results: list[PredictionOutput] = []

    # Propagate asteroid state to all requested epochs.
    if trajectory is None:
        # No trajectory: propagate from the given initial state to each epoch.
        astro_states: list[dict] = []
        for t in epochs_years:
            s = propagate_state(
                astro_x_au, astro_y_au, astro_z_au,
                astro_vx_au_per_year, astro_vy_au_per_year, astro_vz_au_per_year,
                t,
            )
            astro_states.append(s)
    else:
        # Trajectory provided: use propagate_multi for all epochs.
        # It will interpolate inside the span and propagate beyond it.
        astro_states = propagate_multi(
            astro_x_au, astro_y_au, astro_z_au,
            astro_vx_au_per_year, astro_vy_au_per_year, astro_vz_au_per_year,
            epochs_years,
        )

    # Observer: compute position and velocity at each epoch.
    # The observer module functions accept time_years and orbital parameters.
    # If observer is None we pass no extra kwargs; the defaults (1 AU, 1 yr, phase 90°)
    # are used.
    if observer is not None:
        obs_positions = calculate_observer_positions(
            np.array(epochs_years),
            orbital_radius_au=getattr(observer, "orbital_radius_au", 1.0),
            orbital_period_years=getattr(observer, "orbital_period_years", 1.0),
            initial_phase_deg=getattr(observer, "initial_phase_deg", 90.0),
        )
        obs_velocities = calculate_observer_velocities(
            np.array(epochs_years),
            orbital_radius_au=getattr(observer, "orbital_radius_au", 1.0),
            orbital_period_years=getattr(observer, "orbital_period_years", 1.0),
            initial_phase_deg=getattr(observer, "initial_phase_deg", 90.0),
        )
    else:
        # Default observer: no extra kwargs, use defaults inside the functions
        obs_positions = calculate_observer_positions(np.array(epochs_years))
        obs_velocities = calculate_observer_velocities(np.array(epochs_years))

    # Process each epoch
    for i, t in enumerate(epochs_years):
        astro = astro_states[i]

        # Observer state at this epoch
        obs_x = obs_positions[i, 0]
        obs_y = obs_positions[i, 1]
        obs_z = obs_positions[i, 2]
        obs_vx = obs_velocities[i, 0]
        obs_vy = obs_velocities[i, 1]
        obs_vz = obs_velocities[i, 2]

        # Asteroid state at this epoch
        astro_state = {
            "x_au": astro["x_au"],
            "y_au": astro["y_au"],
            "z_au": astro["z_au"],
            "vx_au_per_year": astro["vx_au_per_year"],
            "vy_au_per_year": astro["vy_au_per_year"],
            "vz_au_per_year": astro["vz_au_per_year"],
        }

        # Relative position (asteroid - observer)
        rel_x = astro["x_au"] - obs_x
        rel_y = astro["y_au"] - obs_y
        rel_z = astro["z_au"] - obs_z
        relative = {"x_au": rel_x, "y_au": rel_y, "z_au": rel_z}

        # Distance
        distance_au = math.hypot(rel_x, rel_y, rel_z)

        # Line-of-sight unit vector
        los_unit = np.array([rel_x / distance_au, rel_y / distance_au, rel_z / distance_au])
        if not np.isfinite(los_unit).all():
            raise ValueError(f"Non-finite LOS unit vector at epoch {t} yr.")

        # Sky coordinates (RA, Dec) via ecliptic-to-equatorial
        # calculate_sky_coordinates expects (N, 3) array; reshape single vector
        ra_deg, dec_deg = calculate_sky_coordinates(los_unit.reshape(1, -1))

        # Solar elongation
        # calculate_solar_elongation expects (N, ) or (N, 1) arrays for positions;
        # reshape single epoch to (1, 3) to match the line-of-sight convention
        elongation_deg = calculate_solar_elongation(
            np.array([[astro["x_au"], astro["y_au"], astro["z_au"]]]),
            np.array([[obs_x, obs_y, obs_z]]),
        )

        # Frame and time metadata
        frame = "equatorial_j2000"
        time_metadata = {
            "epoch_years": t,
            "inside_trajectory": _classify_epoch(t, trajectory) == "inside",
            "propagation_method": (
                "interpolation" if _classify_epoch(t, trajectory) == "inside" else "numerical"
            ),
        }

        results.append(
            PredictionOutput(
                epoch_years=t,
                astro_state=astro_state,
                obs_state={
                    "x_au": obs_x,
                    "y_au": obs_y,
                    "z_au": obs_z,
                    "vx_au_per_year": obs_vx,
                    "vy_au_per_year": obs_vy,
                    "vz_au_per_year": obs_vz,
                },
                relative=relative,
                distance_au=distance_au,
                los_unit=los_unit,
                ra_deg=ra_deg,
                dec_deg=dec_deg,
                elongation_deg=elongation_deg,
                frame=frame,
                time_metadata=time_metadata,
            )
        )

    return results


def predict_from_trajectory(
    trajectory: dict,
    epochs_years: list[float],
    observer: object | None = None,
) -> list[PredictionOutput]:
    """Predict sky positions for one asteroid at multiple epochs, using a
    saved trajectory as the state source.

    For epochs inside the trajectory span linear interpolation is used;
    beyond the span REBOUND IAS15 numerical integration is performed.

    Parameters
    ----------
    trajectory : dict
        Trajectory data as returned by ``loader.load_trajectory``.  Must
        contain the keys ``time_years``, ``positions``, ``velocities``.
    epochs_years : list of float
        Requested observation epochs in decimal years.  Must be >= 0.
    observer : object or None, optional
        Observer configuration object passed to ``calculate_observer_positions``
        and ``calculate_observer_velocities``.  If ``None`` the default
        Earth-like circular observer (1 AU, 1 yr period, phase 90°) is used.

    Returns
    -------
    list of ``PredictionOutput``
        One result per requested epoch.

    Raises
    ------
    ValueError
        If any epoch is negative, non-finite, or if propagation/interpolation fails.
    """
    # Validate epochs
    for t in epochs_years:
        _validate_epoch(t)

    # Extract initial state from the first trajectory sample
    positions = np.asarray(trajectory["positions"], dtype=float)  # (N, 3)
    velocities = np.asarray(trajectory["velocities"], dtype=float)  # (N, 3)
    times = trajectory["time_years"]

    # Use the first sample as the initial state
    initial_x = float(positions[0, 0])
    initial_y = float(positions[0, 1])
    initial_z = float(positions[0, 2])
    initial_vx = float(velocities[0, 0])
    initial_vy = float(velocities[0, 1])
    initial_vz = float(velocities[0, 2])

    return predict_from_state(
        initial_x, initial_y, initial_z,
        initial_vx, initial_vy, initial_vz,
        epochs_years,
        observer=observer,
        trajectory=trajectory,
    )