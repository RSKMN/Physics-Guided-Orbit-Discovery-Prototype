"""Interpolation accuracy evaluation for asteroid trajectories.

Evaluates the numerical accuracy of the existing trajectory interpolation service
by comparing interpolated asteroid states against independently obtained direct
REBOUND IAS15 reference states.

This is an evaluation and validation stage. It does not redesign the propagation
system but quantifies interpolation errors to establish whether the current
trajectory resolution is suitable for subsequent orbit estimation.
"""

from __future__ import annotations

import math
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import rebound

from orbit_discovery.core.propagation import propagate_state, propagate_multi, _build_simulation
from orbit_discovery.core.propagation import propagate_from_trajectory
from orbit_discovery.component2_observations.loader import load_trajectory

#: Gravitational parameter used by the propagation service (AU^3 / yr^2 in units where Msun=1).
MU = 1.0

#: Default trajectory sampling interval (years).  The current simulator generates
#: 1001 samples over 5 years, giving a nominal interval of 0.005 yr.
DEFAULT_SAMPLING_INTERVAL = 0.005

#: Fine reference trajectory sampling interval (years).  Used to generate
#: high-accuracy reference states at evaluation epochs.  Finer than the
#: default trajectory spacing to ensure exact-epoch comparison.
FINE_SAMPLING_INTERVAL = 0.001

#: Tight integration epsilon for reference state generation (relative to IAS15 default).
REFERENCE_EPSILON = 1e-14

#: Small threshold to avoid dividing by zero in relative error calculations.
ZERO_TOL = 1e-15

#: Number of intermediate epochs to evaluate per trajectory segment.
N_INTERMEDIATE_EPOCHS = 9


@dataclass
class ReferenceState:
    """Reference asteroid state from direct REBOUND IAS15 propagation.

    Parameters
    ----------
    epoch_years : float
        Epoch in decimal years.
    x_au : float
        Heliocentric position x in AU.
    y_au : float
        Heliocentric position y in AU.
    z_au : float
        Heliocentric position z in AU.
    vx_au_per_year : float
        Heliocentric velocity x in AU/yr.
    vy_au_per_year : float
        Heliocentric velocity y in AU/yr.
    vz_au_per_year : float
        Heliocentric velocity z in AU/yr.
    """

    epoch_years: float
    x_au: float
    y_au: float
    z_au: float
    vx_au_per_year: float
    vy_au_per_year: float
    vz_au_per_year: float


@dataclass
class InterpolationResult:
    """Structured result of interpolation accuracy evaluation.

    Parameters
    ----------
    trajectory_name : str
        Name/identifier of the trajectory evaluated.
    sampling_interval_years : float
        Trajectory sampling interval used for the evaluation.
    reference_epsilon : float
        Integration epsilon used for reference state generation.
    comparison_epochs : int
        Number of intermediate epochs evaluated.
    position_errors_au : list[float]
        Position errors in AU at each comparison epoch, sorted by epoch.
    velocity_errors_au_per_yr : list[float]
        Velocity errors in AU/yr at each comparison epoch, sorted by epoch.
    mean_position_error_au : float
        Mean position error in AU.
    median_position_error_au : float
        Median position error in AU.
    rms_position_error_au : float
        RMS position error in AU.
    max_position_error_au : float
        Maximum position error in AU.
    position_error_p95_au : float
        95th percentile position error in AU.
    mean_velocity_error_au_per_yr : float
        Mean velocity error in AU/yr.
    median_velocity_error_au_per_yr : float
        Median velocity error in AU/yr.
    rms_velocity_error_au_per_yr : float
        RMS velocity error in AU/yr.
    max_velocity_error_au_per_yr : float
        Maximum velocity error in AU/yr.
    velocity_error_p95_au_per_yr : float
        95th percentile velocity error in AU/yr.
    warnings : list[str]
        Any warnings or limitations noted during evaluation.
    """

    trajectory_name: str
    sampling_interval_years: float
    reference_epsilon: float
    comparison_epochs: int
    position_errors_au: list[float]
    velocity_errors_au_per_yr: list[float]
    mean_position_error_au: float
    median_position_error_au: float
    rms_position_error_au: float
    max_position_error_au: float
    position_error_p95_au: float
    mean_velocity_error_au_per_yr: float
    median_velocity_error_au_per_yr: float
    rms_velocity_error_au_per_yr: float
    max_velocity_error_au_per_yr: float
    velocity_error_p95_au_per_yr: float
    warnings: list[str]


def _validate_trajectory(trajectory: dict) -> None:
    """Validate that a trajectory dict has the required structure.

    Parameters
    ----------
    trajectory : dict
        Trajectory data as returned by ``loader.load_trajectory``.

    Raises
    ------
    ValueError
        If the trajectory is invalid.
    """
    required_keys = {"time_years", "positions", "velocities"}
    missing = required_keys - set(trajectory.keys())
    if missing:
        raise ValueError(f"Trajectory missing required keys: {sorted(missing)}")

    times = np.asarray(trajectory["time_years"], dtype=float)
    positions = np.asarray(trajectory["positions"], dtype=float)
    velocities = np.asarray(trajectory["velocities"], dtype=float)

    if times.ndim != 1:
        raise ValueError("trajectory.time_years must be 1-dimensional")
    if positions.ndim != 2 or positions.shape[1] != 3:
        raise ValueError("trajectory.positions must be (N, 3)")
    if velocities.ndim != 2 or velocities.shape[1] != 3:
        raise ValueError("trajectory.velocities must be (N, 3)")
    if len(times) != positions.shape[0]:
        raise ValueError(
            f"trajectory.time_years length ({len(times)}) "
            f"must match positions rows ({positions.shape[0]})"
        )
    if len(times) != velocities.shape[0]:
        raise ValueError(
            f"trajectory.time_years length ({len(times)}) "
            f"must match velocities rows ({velocities.shape[0]})"
        )

    if not np.all(np.diff(times) > 0):
        raise ValueError("Trajectory timestamps must be strictly increasing.")


def _generate_reference_states(
    trajectory: dict,
    epsilon: float = REFERENCE_EPSILON,
) -> List[ReferenceState]:
    """Generate reference asteroid states using direct REBOUND IAS15 propagation.

    For each sample in the trajectory, propagate from that sample's state to
    the same epoch using tight integration settings.  This provides a high-precision
    baseline against which interpolation errors can be measured.

    Parameters
    ----------
    trajectory : dict
        Trajectory data as returned by ``loader.load_trajectory``.
    epsilon : float, optional
        REBOUND integrator epsilon tolerance. Tighter than the default 1e-12.

    Returns
    -------
    list of ``ReferenceState``
        Reference state at each trajectory sample epoch.
    """
    _validate_trajectory(trajectory)

    times = np.asarray(trajectory["time_years"], dtype=float)
    positions = np.asarray(trajectory["positions"], dtype=float)
    velocities = np.asarray(trajectory["velocities"], dtype=float)

    import rebound

    # Build simulation with tight epsilon
    sim = _build_simulation_with_epsilon(epsilon=epsilon)

    asteroid_index = sim.N - 1

    ref_states: List[ReferenceState] = []

    for i in range(len(times)):
        t = float(times[i])
        # Use the i-th sample as initial state and propagate to the same epoch.
        # Tight epsilon ensures the reference is essentially exact for the
        # two-body+perturbers model.
        asteroid = sim.particles[asteroid_index]
        asteroid.x = float(positions[i, 0])
        asteroid.y = float(positions[i, 1])
        asteroid.z = float(positions[i, 2])
        asteroid.vx = float(velocities[i, 0])
        asteroid.vy = float(velocities[i, 1])
        asteroid.vz = float(velocities[i, 2])

        try:
            sim.integrate(float(t))
        except Exception as e:
            raise ValueError(
                f"REBOUND integration failed at target_time_years={t}: {e}"
            ) from e

        asteroid = sim.particles[asteroid_index]
        ref_states.append(
            ReferenceState(
                epoch_years=t,
                x_au=float(asteroid.x),
                y_au=float(asteroid.y),
                z_au=float(asteroid.z),
                vx_au_per_year=float(asteroid.vx),
                vy_au_per_year=float(asteroid.vy),
                vz_au_per_year=float(asteroid.vz),
            )
        )

    return ref_states


def _build_simulation_with_epsilon(
    bodies: list[str] | None = None,
    epsilon: float = 1e-12,
) -> any:
    """Build a REBOUND simulation with a custom integrator epsilon.

    Parameters
    ----------
    bodies : list of str, optional
        Gravitational bodies.  Defaults to Sun + Earth + Jupiter.
    epsilon : float, optional
        REBOUND integrator epsilon tolerance.  Defaults to 1e-12 (the project
        default).

    Returns
    -------
    sim : rebound.Simulation
        Configured simulation with the specified epsilon.
    """
    if bodies is None:
        bodies = ["Sun", "Earth", "Jupiter"]

    sim = rebound.Simulation()
    sim.units = ("yr", "AU", "Msun")
    sim.add(m=1.0)  # Sun at the origin

    # BODY_DATA from propagation.py
    BODY_DATA = {
        "Mercury": {"mass": 1.6601e-7, "a": 0.3871},
        "Venus":   {"mass": 2.4478e-6, "a": 0.7233},
        "Earth":   {"mass": 3.0035e-6, "a": 1.0000},
        "Mars":    {"mass": 3.2272e-7, "a": 1.5237},
        "Jupiter": {"mass": 9.5458e-4, "a": 5.2028},
    }

    for name in bodies:
        if name == "Sun":
            continue
        if name not in BODY_DATA:
            raise ValueError(f"Unsupported gravitational body: {name}")
        body = BODY_DATA[name]
        sim.add(m=body["mass"], a=body["a"], e=0.0, inc=0.0)

    sim.move_to_com()
    sim.integrator = "ias15"
    sim.integrator.epsilon = epsilon

    return sim


def generate_trajectory_with_interval(
    initial_x_au: float,
    initial_y_au: float,
    initial_z_au: float,
    initial_vx_au_per_year: float,
    initial_vy_au_per_year: float,
    initial_vz_au_per_year: float,
    duration_years: float = 5.0,
    sampling_interval_years: float = DEFAULT_SAMPLING_INTERVAL,
    epsilon: float = REFERENCE_EPSILON,
    bodies: list[str] | None = None,
) -> dict:
    """Generate a trajectory at a specified sampling interval.

    Uses REBOUND IAS15 propagation to create a trajectory with the specified
    number of samples and sampling interval.  The initial state is propagated
    from t=0 to t=duration_years in steps of sampling_interval_years.
    The epsilon parameter controls integration accuracy and is consistent with
    the reference epsilon used in ``evaluate_trajectory``/``evaluate_sampling_intervals``.

    Parameters
    ----------
    initial_x_au, initial_y_au, initial_z_au : float
        Initial heliocentric position in AU.
    initial_vx_au_per_year, initial_vy_au_per_year, initial_vz_au_per_year : float
        Initial heliocentric velocity in AU/year.
    duration_years : float, optional
        Total propagation duration in years.  Defaults to 5.0 (the standard
        span used by the existing simulator).
    sampling_interval_years : float, optional
        Desired sampling interval in years.  Defaults to 0.005 yr (the project
        default).
    epsilon : float, optional
        REBOUND integrator epsilon tolerance.  Defaults to REFERENCE_EPSILON
        (1e-14), ensuring consistency with reference state generation.
    bodies : list of str, optional
        Gravitational bodies.  Defaults to Sun + Earth + Jupiter.

    Returns
    -------
    dict
        Trajectory dict as returned by ``loader.load_trajectory``, containing
        ``time_years``, ``time_days``, ``positions``, ``velocities``, and
        ``number_of_samples``.
    """
    if bodies is None:
        bodies = ["Sun", "Earth", "Jupiter"]

    # Compute number of samples
    n_samples = max(2, int(round(duration_years / sampling_interval_years)) + 1)

    # Build simulation with the specified epsilon and propagate
    sim = _build_simulation_with_epsilon(epsilon=epsilon, bodies=bodies)

    # Set initial asteroid state (last particle)
    asteroid_index = sim.N - 1
    asteroid = sim.particles[asteroid_index]
    asteroid.x = float(initial_x_au)
    asteroid.y = float(initial_y_au)
    asteroid.z = float(initial_z_au)
    asteroid.vx = float(initial_vx_au_per_year)
    asteroid.vy = float(initial_vy_au_per_year)
    asteroid.vz = float(initial_vz_au_per_year)

    # Propagate to all target times
    times = np.linspace(0.0, duration_years, n_samples)

    states: list[dict[str, float]] = []
    for t in times:
        try:
            sim.integrate(float(t))
        except Exception as e:
            raise ValueError(
                f"REBOUND integration failed at target_time_years={t}: {e}"
            ) from e
        asteroid = sim.particles[asteroid_index]
        states.append(
            {
                "x_au": float(asteroid.x),
                "y_au": float(asteroid.y),
                "z_au": float(asteroid.z),
                "vx_au_per_year": float(asteroid.vx),
                "vy_au_per_year": float(asteroid.vy),
                "vz_au_per_year": float(asteroid.vz),
            }
        )

    # Extract positions and velocities
    positions = np.array([[s["x_au"], s["y_au"], s["z_au"]] for s in states])
    velocities = np.array([[s["vx_au_per_year"], s["vy_au_per_year"], s["vz_au_per_year"]] for s in states])

    # Also compute time_days (assuming days = years * 365.25)
    time_days = times * 365.25

    return {
        "time_years": times.tolist(),
        "time_days": time_days.tolist(),
        "positions": positions.tolist(),
        "velocities": velocities.tolist(),
        "number_of_samples": n_samples,
    }


def _compute_interpolated_state(
    trajectory: dict,
    target_time_years: float,
) -> dict[str, float]:
    """Compute an interpolated state at a target time using the trajectory service.

    This uses linear interpolation via ``np.interp`` for times within the
    trajectory span.

    Parameters
    ----------
    trajectory : dict
        Trajectory data as returned by ``loader.load_trajectory``.
    target_time_years : float
        Target time in years (must be within the trajectory span).

    Returns
    -------
    dict
        Interpolated state with keys ``x_au``, ``y_au``, ``z_au``,
        ``vx_au_per_year``, ``vy_au_per_year``, ``vz_au_per_year``.
    """
    from orbit_discovery.core.propagation import propagate_from_trajectory

    return propagate_from_trajectory(trajectory, target_time_years)


def _compute_errors(
    ref: ReferenceState,
    interp: dict[str, float],
) -> Tuple[float, float]:
    """Compute position and velocity errors between reference and interpolated states.

    Parameters
    ----------
    ref : ``ReferenceState``
        Reference state from direct propagation.
    interp : dict
        Interpolated state from the trajectory interpolation service.

    Returns
    -------
    position_error_au : float
        Euclidean distance error in AU.
    velocity_error_au_per_yr : float
        Euclidean distance error in AU/yr.
    """
    # Position error
    dx = ref.x_au - interp["x_au"]
    dy = ref.y_au - interp["y_au"]
    dz = ref.z_au - interp["z_au"]
    position_error_au = math.hypot(dx, dy, dz)

    # Velocity error
    dvx = ref.vx_au_per_year - interp["vx_au_per_year"]
    dvy = ref.vy_au_per_year - interp["vy_au_per_year"]
    dvz = ref.vz_au_per_year - interp["vz_au_per_year"]
    velocity_error_au_per_yr = math.hypot(dvx, dvy, dvz)

    return position_error_au, velocity_error_au_per_yr


def _compute_statistics(errors: List[float]) -> Dict[str, float]:
    """Compute error statistics: mean, median, RMS, max, and 95th percentile.

    Parameters
    ----------
    errors : list of float
        List of error values (in consistent units).

    Returns
    -------
    dict
        Statistics with keys: mean, median, rms, max, p95.
    """
    if not errors:
        return {
            "mean": float("nan"),
            "median": float("nan"),
            "rms": float("nan"),
            "max": float("nan"),
            "p95": float("nan"),
        }

    errors_arr = np.array(errors, dtype=float)
    # Handle non-finite values
    if not np.isfinite(errors_arr).all():
        errors_arr = np.where(np.isfinite(errors_arr), errors_arr, 1e6)

    mean_err = float(np.mean(errors_arr))
    median_err = float(np.median(errors_arr))
    rms_err = float(np.sqrt(np.mean(errors_arr ** 2)))
    max_err = float(np.max(errors_arr))
    p95_err = float(np.percentile(errors_arr, 95))

    return {
        "mean": mean_err,
        "median": median_err,
        "rms": rms_err,
        "max": max_err,
        "p95": p95_err,
    }


def evaluate_trajectory(
    trajectory: dict,
    sampling_interval: float | None = None,
    reference_epsilon: float = REFERENCE_EPSILON,
    n_intermediate: int = N_INTERMEDIATE_EPOCHS,
) -> InterpolationResult:
    """Evaluate interpolation accuracy for a single trajectory.

    For each segment between consecutive trajectory samples, evaluate the
    interpolation error at ``n_intermediate`` equally-spaced intermediate epochs.
    The interpolation result is compared against a reference state obtained from
    a high-accuracy reference trajectory generated independently using REBOUND
    IAS15 with tight integration settings.  The reference trajectory is sampled
    at 0.001 yr intervals, and reference states at the evaluation epochs are
    obtained via ``propagate_from_trajectory`` (linear interpolation on the
    fine reference trajectory).  This ensures comparison at matching epochs
    without the epoch-mismatch bug that previously inflated reported interpolation
    errors.

    The reference trajectory is generated at a fine sampling interval (0.001 yr)
    using tight IAS15 epsilon (1e-14), providing high-accuracy reference states
    at exactly the evaluation epochs.  This eliminates the epoch-mismatch bug
    that previously inflated reported interpolation errors by comparing reference
    states at sample epochs rather than at the evaluation epochs.

    Parameters
    ----------
    trajectory : dict
        Trajectory data as returned by ``loader.load_trajectory``.
    sampling_interval : float or None, optional
        Trajectory sampling interval in years.  If None, inferred from the
        trajectory duration and number of samples.
    reference_epsilon : float, optional
        Integration epsilon for reference state generation. Defaults to 1e-14.
    n_intermediate : int, optional
        Number of intermediate epochs to evaluate per trajectory segment.
        Defaults to 9 (evaluating at 10 equally-spaced points including
        the start and end of each segment).

    Returns
    -------
    ``InterpolationResult``
        Structured evaluation result containing error statistics and metadata.

    Raises
    ------
    ValueError
        If the trajectory is invalid, or if no intermediate epochs can be
        evaluated (e.g., trajectory with fewer than 2 samples).
    """
    _validate_trajectory(trajectory)

    times = np.asarray(trajectory["time_years"], dtype=float)
    n_samples = len(times)

    if n_samples < 2:
        raise ValueError("Trajectory must contain at least two samples.")

    # Determine sampling interval
    if sampling_interval is None:
        sampling_interval = float(
            (times[-1] - times[0]) / (n_samples - 1)
        )

    # Extract positions and velocities from trajectory
    positions = np.asarray(trajectory["positions"], dtype=float)
    velocities = np.asarray(trajectory["velocities"], dtype=float)

    # Generate a high-accuracy reference trajectory independently
    # using REBOUND IAS15 with the same initial conditions
    initial_x = float(positions[0, 0])
    initial_y = float(positions[0, 1])
    initial_z = float(positions[0, 2])
    initial_vx = float(velocities[0, 0])
    initial_vy = float(velocities[0, 1])
    initial_vz = float(velocities[0, 2])

    ref_traj = generate_trajectory_with_interval(
        initial_x_au=initial_x,
        initial_y_au=initial_y,
        initial_z_au=initial_z,
        initial_vx_au_per_year=initial_vx,
        initial_vy_au_per_year=initial_vy,
        initial_vz_au_per_year=initial_vz,
        duration_years=float((times[-1] - times[0])),
        sampling_interval_years=FINE_SAMPLING_INTERVAL,
        epsilon=reference_epsilon,
        bodies=["Sun", "Earth", "Jupiter"],
    )

    # Collect errors at intermediate epochs
    all_position_errors: List[float] = []
    all_velocity_errors: List[float] = []

    # Track evaluation
    segments_evaluated = 0
    segments_warnings: List[str] = []

    # Evaluate each segment between consecutive samples
    for seg_idx in range(n_samples - 1):
        t_start = float(times[seg_idx])
        t_end = float(times[seg_idx + 1])
        segment_duration = t_end - t_start

        if segment_duration <= 0:
            segments_warnings.append(
                f"Segment {seg_idx} has non-positive duration; skipping."
            )
            continue

        # Generate n_intermediate equally-spaced epochs within (t_start, t_end)
        # Exclusive of endpoints to avoid trivial zero-error comparisons at
        # exact sample points.
        intermediate_epochs = np.linspace(
            t_start + segment_duration / (n_intermediate + 1),
            t_end - segment_duration / (n_intermediate + 1),
            n_intermediate,
        )

        for t_eval in intermediate_epochs:
            # Get reference state at t_eval from the fine reference trajectory
            # using propagate_from_trajectory (linear interpolation on the
            # fine reference trajectory).  This ensures the reference state is
            # at exactly the same epoch as the interpolated trajectory state,
            # eliminating the epoch-mismatch bug.
            try:
                ref_interp = propagate_from_trajectory(ref_traj, t_eval)
                ref_state = ReferenceState(
                    epoch_years=t_eval,
                    x_au=float(ref_interp["x_au"]),
                    y_au=float(ref_interp["y_au"]),
                    z_au=float(ref_interp["z_au"]),
                    vx_au_per_year=float(ref_interp["vx_au_per_year"]),
                    vy_au_per_year=float(ref_interp["vy_au_per_year"]),
                    vz_au_per_year=float(ref_interp["vz_au_per_year"]),
                )
            except ValueError as e:
                segments_warnings.append(
                    f"Reference propagation failed at epoch {t_eval:.6f} yr: {e}"
                )
                continue

            # Get interpolated state at t_eval
            try:
                interp = _compute_interpolated_state(trajectory, t_eval)
            except ValueError as e:
                segments_warnings.append(
                    f"Interpolation failed at epoch {t_eval:.6f} yr: {e}"
                )
                continue

            # Compute errors
            pos_error, vel_error = _compute_errors(ref_state, interp)

            all_position_errors.append(pos_error)
            all_velocity_errors.append(vel_error)
            segments_evaluated += 1

    # Compute statistics
    pos_stats = _compute_statistics(all_position_errors) if all_position_errors else {
        "mean": float("nan"),
        "median": float("nan"),
        "rms": float("nan"),
        "max": float("nan"),
        "p95": float("nan"),
    }
    vel_stats = _compute_statistics(all_velocity_errors) if all_velocity_errors else {
        "mean": float("nan"),
        "median": float("nan"),
        "rms": float("nan"),
        "max": float("nan"),
        "p95": float("nan"),
    }

    # Determine trajectory name
    trajectory_name = "unknown"
    if "trajectory_name" in trajectory:
        trajectory_name = trajectory["trajectory_name"]
    else:
        # Try to infer from the file path if available
        input_path = trajectory.get("input_path", "")
        if input_path:
            trajectory_name = Path(input_path).name

    result = InterpolationResult(
        trajectory_name=trajectory_name,
        sampling_interval_years=sampling_interval,
        reference_epsilon=reference_epsilon,
        comparison_epochs=segments_evaluated,
        position_errors_au=sorted(all_position_errors),
        velocity_errors_au_per_yr=sorted(all_velocity_errors),
        mean_position_error_au=pos_stats["mean"],
        median_position_error_au=pos_stats["median"],
        rms_position_error_au=pos_stats["rms"],
        max_position_error_au=pos_stats["max"],
        position_error_p95_au=pos_stats["p95"],
        mean_velocity_error_au_per_yr=vel_stats["mean"],
        median_velocity_error_au_per_yr=vel_stats["median"],
        rms_velocity_error_au_per_yr=vel_stats["rms"],
        max_velocity_error_au_per_yr=vel_stats["max"],
        velocity_error_p95_au_per_yr=vel_stats["p95"],
        warnings=segments_warnings,
    )

    return result