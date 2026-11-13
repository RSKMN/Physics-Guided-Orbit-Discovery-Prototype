"""Component 3 observation model: predict apparent RA/Dec from a trial state.

Reuses Component 2's observer geometry and frame-conversion routines exactly,
without introducing light-time corrections, aberration, relativistic effects,
or any new observer physics.

Conventions (matching Component 2):
- Observer positions: heliocentric ecliptic inertial, AU
- Observer model: idealized circular orbit in the ecliptic plane
- Frame: ecliptic-to-equatorial rotation with fixed obliquity (23.43928 deg)
- RA: normalized to [0, 360) degrees
- Dec: clipped to [-90, 90] degrees
- No light-time correction, no aberration, no relativistic deflection
"""

from __future__ import annotations

from typing import Any

import numpy as np

from orbit_discovery.component2_observations.observer import (
    ObserverConfig,
    calculate_line_of_sight,
    calculate_observer_positions,
    calculate_sky_coordinates,
)
from orbit_discovery.component3.models import OrbitState


# Default observer metadata keys expected in observation metadata.
OBSERVER_KEY_DEFAULTS = {
    "orbital_radius_au": 1.0,
    "orbital_period_years": 1.0,
    "initial_phase_deg": 90.0,
}

OBLIQUITY_KEY = "obliquity_deg"
OBLIQUITY_DEFAULT = 23.43928


def reconstruct_observer_config(
    metadata: dict[str, Any],
) -> ObserverConfig:
    """Reconstruct an ObserverConfig from observation metadata.

    Extracts observer orbital parameters from the ``observer`` key of the
    observation dataset metadata (as written by Component 2's generator).

    Parameters
    ----------
    metadata : dict
        Observation dataset metadata, expected to contain an ``observer``
        sub-dictionary with keys ``orbital_radius_au``,
        ``orbital_period_years``, and ``initial_phase_deg``.

    Returns
    -------
    ObserverConfig
        Configured observer matching Component 2's model.

    Raises
    ------
    ValueError
        If required observer metadata is missing or invalid.
    """
    observer_meta = metadata.get("observer")
    if not isinstance(observer_meta, dict):
        raise ValueError(
            "Observation metadata missing 'observer' sub-dictionary."
        )

    try:
        return ObserverConfig(
            orbital_radius_au=float(
                observer_meta.get(
                    "orbital_radius_au", OBSERVER_KEY_DEFAULTS["orbital_radius_au"]
                )
            ),
            orbital_period_years=float(
                observer_meta.get(
                    "orbital_period_years",
                    OBSERVER_KEY_DEFAULTS["orbital_period_years"],
                )
            ),
            initial_phase_deg=float(
                observer_meta.get(
                    "initial_phase_deg",
                    OBSERVER_KEY_DEFAULTS["initial_phase_deg"],
                )
            ),
        )
    except (TypeError, ValueError) as e:
        raise ValueError(f"Invalid observer metadata: {e}") from e


def get_obliquity_deg(metadata: dict[str, Any]) -> float:
    """Extract the ecliptic obliquity from observation metadata.

    Parameters
    ----------
    metadata : dict
        Observation dataset metadata, expected to contain ``coordinates``
        with ``obliquity_deg``.

    Returns
    -------
    float
        Obliquity in degrees.
    """
    coords = metadata.get("coordinates", {})
    if not isinstance(coords, dict):
        return OBLIQUITY_DEFAULT
    try:
        return float(coords.get(OBLIQUITY_KEY, OBLIQUITY_DEFAULT))
    except (TypeError, ValueError):
        return OBLIQUITY_DEFAULT


def predict_apparent_coordinates(
    asteroid_states: list[dict[str, Any]],
    epochs_years: list[float],
    observer_config: ObserverConfig | None = None,
    obliquity_deg: float = OBLIQUITY_DEFAULT,
) -> list[dict[str, Any]]:
    """Predict apparent RA/Dec for a trial asteroid at observation epochs.

    Uses Component 2's observer geometry and frame conversion exactly:
    observer positions (heliocentric ecliptic) → relative position vectors
    (asteroid − observer) → line-of-sight unit vectors → ecliptic-to-equatorial
    rotation → RA/Dec.

    Observer velocity is not calculated because Component 2's sky-coordinate
    model does not require it (no light-time or aberration corrections).

    Parameters
    ----------
    asteroid_states : list of dict
        Propagated asteroid states from :func:`propagate_trial_state`.  Each
        entry must contain ``x_au``, ``y_au``, ``z_au``, ``vx_au_per_year``,
        ``vy_au_per_year``, ``vz_au_per_year``, and ``epoch_years``.
    epochs_years : list of float
        Observation epochs in elapsed simulation years.  Must match
        ``asteroid_states`` in length and order.
    observer_config : ObserverConfig, optional
        Observer configuration.  Defaults to Component 2's standard
        Earth-like circular observer (1 AU, 1 yr, phase 90°).
    obliquity_deg : float
        Ecliptic obliquity in degrees.  Default: 23.43928.

    Returns
    -------
    list of dict
        One entry per epoch, in input order, each containing:
        ``epoch_years``, ``x_au``, ``y_au``, ``z_au``,
        ``vx_au_per_year``, ``vy_au_per_year``, ``vz_au_per_year``,
        ``observer_x_au``, ``observer_y_au``, ``observer_z_au``,
        ``ra_deg``, ``dec_deg``.

    Raises
    ------
    ValueError
        If inputs are invalid, mismatched, or contain non-finite values.
    """
    if len(asteroid_states) != len(epochs_years):
        raise ValueError(
            f"Mismatched lengths: {len(asteroid_states)} asteroid states "
            f"vs {len(epochs_years)} epochs."
        )

    n = len(asteroid_states)
    if n == 0:
        return []

    epochs = np.asarray(epochs_years, dtype=float)
    if not np.all(np.isfinite(epochs)):
        raise ValueError("All epochs must be finite.")

    # Extract asteroid positions
    positions = np.zeros((n, 3))
    velocities = np.zeros((n, 3))
    for i, state in enumerate(asteroid_states):
        try:
            positions[i, 0] = float(state["x_au"])
            positions[i, 1] = float(state["y_au"])
            positions[i, 2] = float(state["z_au"])
            velocities[i, 0] = float(state["vx_au_per_year"])
            velocities[i, 1] = float(state["vy_au_per_year"])
            velocities[i, 2] = float(state["vz_au_per_year"])
        except (KeyError, TypeError, ValueError) as e:
            raise ValueError(
                f"Asteroid state at index {i} is missing required fields: {e}"
            ) from e

    if not np.all(np.isfinite(positions)):
        raise ValueError("Asteroid positions contain non-finite values.")
    if not np.all(np.isfinite(velocities)):
        raise ValueError("Asteroid velocities contain non-finite values.")

    # Observer configuration
    if observer_config is None:
        observer_config = ObserverConfig()

    # Observer positions at epochs (heliocentric ecliptic, AU)
    observer_positions = calculate_observer_positions(
        epochs,
        orbital_radius_au=observer_config.orbital_radius_au,
        orbital_period_years=observer_config.orbital_period_years,
        initial_phase_deg=observer_config.initial_phase_deg,
    )

    if observer_positions.shape != (n, 3):
        raise ValueError(
            f"Observer position shape mismatch: expected ({n}, 3), "
            f"got {observer_positions.shape}."
        )

    if not np.all(np.isfinite(observer_positions)):
        raise ValueError("Observer positions contain non-finite values.")

    # Relative positions (asteroid − observer) and LOS unit vectors
    relative, los_unit_vectors, _ = calculate_line_of_sight(
        positions, observer_positions
    )

    # Ecliptic-to-equatorial → RA/Dec
    ra_deg, dec_deg = calculate_sky_coordinates(
        los_unit_vectors, obliquity_deg=obliquity_deg
    )

    # Build results in input order
    results: list[dict[str, Any]] = []
    for i in range(n):
        results.append(
            {
                "epoch_years": float(epochs[i]),
                "x_au": float(positions[i, 0]),
                "y_au": float(positions[i, 1]),
                "z_au": float(positions[i, 2]),
                "vx_au_per_year": float(velocities[i, 0]),
                "vy_au_per_year": float(velocities[i, 1]),
                "vz_au_per_year": float(velocities[i, 2]),
                "observer_x_au": float(observer_positions[i, 0]),
                "observer_y_au": float(observer_positions[i, 1]),
                "observer_z_au": float(observer_positions[i, 2]),
                "ra_deg": float(ra_deg[i]),
                "dec_deg": float(dec_deg[i]),
            }
        )

    return results


def predict_from_orbit_state(
    state: OrbitState,
    epochs_years: list[float],
    observer_config: ObserverConfig | None = None,
    obliquity_deg: float = OBLIQUITY_DEFAULT,
    bodies: list[str] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """End-to-end forward model: propagate state then predict apparent coordinates.

    Parameters
    ----------
    state : OrbitState
        Six-dimensional Cartesian asteroid state at the reference epoch.
    epochs_years : list of float
        Observation epochs in elapsed simulation years.
    observer_config : ObserverConfig, optional
        Observer configuration.  Defaults to Component 2's standard observer.
    obliquity_deg : float
        Ecliptic obliquity in degrees.
    bodies : list of str, optional
        Gravitational bodies for propagation.

    Returns
    -------
    tuple of (propagation_results, predictions)
        propagation_results : list of dict with Cartesian states per epoch.
        predictions : list of dict with apparent RA/Dec per epoch.
    """
    from orbit_discovery.component3.dynamics import propagate_trial_state

    propagation_results = propagate_trial_state(
        state, epochs_years, bodies=bodies
    )
    predictions = predict_apparent_coordinates(
        propagation_results, epochs_years,
        observer_config=observer_config,
        obliquity_deg=obliquity_deg,
    )
    return propagation_results, predictions
