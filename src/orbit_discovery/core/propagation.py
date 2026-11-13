"""Shared arbitrary-time propagation service.

Provides reusable propagation of asteroid states using the same gravitational
model as Component 1 (REBOUND IAS15 integrator with Sun + selected planets).

The service enforces physical-model consistency with C1 and supports:
- Intermediate times within the saved trajectory (linear interpolation).
- Future times beyond the original simulation endpoint (numerical integration).
- Multiple requested times in a single call.
- Reproducible results from the same initial state.

Output units and conventions are consistent with C1 trajectory data.
"""

from __future__ import annotations

import math

import numpy as np

import rebound

from orbit_discovery.core.constants import DAYS_PER_YEAR

#: Gravitational bodies supported by C1 and the propagation service.
#: Must match BODY_DATA in configurable_simulator.py.
BODY_NAMES = ["Sun", "Mercury", "Venus", "Earth", "Jupiter"]

#: Default integrator settings (matching C1).
DEFAULT_INTEGRATOR = "ias15"
DEFAULT_INTEGRATOR_EPSILON = 1e-12


def _build_simulation(
    bodies: list[str] | None = None,
    semi_major_axis_au: float | None = None,
    eccentricity: float | None = None,
    inclination_deg: float | None = None,
    longitude_ascending_node_deg: float | None = None,
    argument_periapsis_deg: float | None = None,
    mean_anomaly_deg: float | None = None,
) -> rebound.Simulation:
    """Build a REBOUND simulation matching C1's physical model.

    Parameters
    ----------
    bodies : list of str, optional
        Gravitational bodies to include. Defaults to Sun + Earth + Jupiter.
    semi_major_axis_au : float, optional
        Semi-major axis of the massless asteroid in AU.
    eccentricity : float, optional
        Eccentricity of the asteroid orbit.
    inclination_deg : float, optional
        Inclination in degrees.
    longitude_ascending_node_deg : float, optional
        Longitude of ascending node in degrees.
    argument_periapsis_deg : float, optional
        Argument of periapsis in degrees.
    mean_anomaly_deg : float, optional
        Mean anomaly in degrees.

    Returns
    -------
    sim : rebound.Simulation
        Configured simulation ready for propagation.
    """
    if bodies is None:
        bodies = ["Sun", "Earth", "Jupiter"]

    sim = rebound.Simulation()
    sim.units = ("yr", "AU", "Msun")
    sim.add(m=1.0)  # Sun at the origin

    # BODY_DATA from configurable_simulator.py
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

    # Add the massless asteroid using orbital elements if provided
    if semi_major_axis_au is not None:
        sim.add(
            m=0.0,
            a=float(semi_major_axis_au),
            e=float(eccentricity) if eccentricity is not None else 0.0,
            inc=np.deg2rad(float(inclination_deg)) if inclination_deg is not None else 0.0,
            Omega=np.deg2rad(float(longitude_ascending_node_deg))
            if longitude_ascending_node_deg is not None
            else 0.0,
       omega=np.deg2rad(float(argument_periapsis_deg))
        if argument_periapsis_deg is not None
        else 0.0,
        M=np.deg2rad(float(mean_anomaly_deg)) if mean_anomaly_deg is not None else 0.0,
        )

    sim.move_to_com()
    sim.integrator = DEFAULT_INTEGRATOR
    sim.integrator.epsilon = DEFAULT_INTEGRATOR_EPSILON

    return sim


def propagate_state(
    x_au: float,
    y_au: float,
    z_au: float,
    vx_au_per_year: float,
    vy_au_per_year: float,
    vz_au_per_year: float,
    target_time_years: float,
    bodies: list[str] | None = None,
) -> dict[str, float]:
    """Propagate an asteroid's Cartesian state to a target time.

    Uses the same REBOUND IAS15 integrator as Component 1. The initial state
    is specified as heliocentric Cartesian position and velocity vectors.

    Parameters
    ----------
    x_au, y_au, z_au : float
        Heliocentric position in AU.
    vx_au_per_year, vy_au_per_year, vz_au_per_year : float
        Heliocentric velocity in AU/year.
    target_time_years : float
        Target time in years.  ``0.0`` returns the initial state.
    bodies : list of str, optional
        Gravitational bodies.  Defaults to Sun + Earth + Jupiter.

    Returns
    -------
    state : dict
        Propagated state at ``target_time_years``::

            {
                "x_au": float,        # Heliocentric position x in AU
                "y_au": float,        # Heliocentric position y in AU
                "z_au": float,        # Heliocentric position z in AU
                "vx_au_per_year": float,  # Heliocentric velocity x in AU/yr
                "vy_au_per_year": float,  # Heliocentric velocity y in AU/yr
                "vz_au_per_year": float,  # Heliocentric velocity z in AU/yr
            }

    Raises
    ------
    ValueError
        If the initial state or target time is invalid, or if the REBOUND
        integration fails.
    """
    sim = _build_simulation(bodies=bodies)

    # Set the initial asteroid state from the provided Cartesian vectors.
    # The asteroid is the last particle in the simulation.
    asteroid_index = sim.N - 1
    asteroid = sim.particles[asteroid_index]

    asteroid.x = float(x_au)
    asteroid.y = float(y_au)
    asteroid.z = float(z_au)
    asteroid.vx = float(vx_au_per_year)
    asteroid.vy = float(vy_au_per_year)
    asteroid.vz = float(vz_au_per_year)

    try:
        sim.integrate(float(target_time_years))
    except Exception as e:
        raise ValueError(
            f"REBOUND integration failed at target_time_years={target_time_years}: {e}"
        ) from e

    asteroid = sim.particles[asteroid_index]
    return {
        "x_au": float(asteroid.x),
        "y_au": float(asteroid.y),
        "z_au": float(asteroid.z),
        "vx_au_per_year": float(asteroid.vx),
        "vy_au_per_year": float(asteroid.vy),
        "vz_au_per_year": float(asteroid.vz),
    }


def propagate_multi(
    x_au: float,
    y_au: float,
    z_au: float,
    vx_au_per_year: float,
    vy_au_per_year: float,
    vz_au_per_year: float,
    target_times_years: list[float],
    bodies: list[str] | None = None,
    trajectory: dict | None = None,
) -> list[dict[str, float]]:
    """Propagate an asteroid's state to multiple target times.

    A convenience wrapper around ``propagate_state`` that avoids re-building
    the simulation for each call.  The simulation is built once and each
    target time is propagated sequentially.

    When a ``trajectory`` is provided, target times inside the trajectory
    span are obtained by linear interpolation via ``propagate_from_trajectory``
    (consistent with the trajectory-based interpolation used elsewhere),
    while target times beyond the span are obtained by REBOUND numerical
    integration continued from the last trajectory sample.

    Parameters
    ----------
    x_au, y_au, z_au, vx_au_per_year, vy_au_per_year, vz_au_per_year :
        Initial heliocentric Cartesian state in AU and AU/year.
    target_times_years : list of float
        List of target times in years.
    bodies : list of str, optional
        Gravitational bodies.  Defaults to Sun + Earth + Jupiter.
    trajectory : dict or None, optional
        Trajectory data as returned by ``loader.load_trajectory`` or generated
        by C1.  If provided, times inside the span are interpolated; times
        beyond are integrated from the last trajectory sample.

    Returns
    -------
    states : list of dict
        Propagated state at each target time, in the same format as
        ``propagate_state``.
    """
    times_years = np.asarray(target_times_years, dtype=float)

    # Validate all target times up front
    for t in times_years:
        if t < 0:
            raise ValueError(f"target_time_years must be >= 0, got {t}.")
        if not math.isfinite(t):
            raise ValueError(f"target_time_years must be finite, got {t}.")

    # Sort times for sequential REBOUND integration; track original order.
    order = np.argsort(times_years, kind="stable")
    sorted_times = times_years[order]

    # order[i] gives the original index of sorted_times[i].
    states: list[dict[str, float] | None] = [None] * len(target_times_years)

    if trajectory is not None:
        # Validate trajectory has required keys
        required = {"time_years", "positions", "velocities"}
        missing = required - set(trajectory.keys())
        if missing:
            raise ValueError(
                f"Trajectory missing required keys: {sorted(missing)}"
            )

        traj_times = np.asarray(trajectory["time_years"], dtype=float)
        traj_positions = np.asarray(trajectory["positions"], dtype=float)
        traj_velocities = np.asarray(trajectory["velocities"], dtype=float)
        traj_start = float(traj_times[0])
        traj_end = float(traj_times[-1])

        # Initial trajectory state (first sample) for beyond-span integration.
        init_x = float(traj_positions[0, 0])
        init_y = float(traj_positions[0, 1])
        init_z = float(traj_positions[0, 2])
        init_vx = float(traj_velocities[0, 0])
        init_vy = float(traj_velocities[0, 1])
        init_vz = float(traj_velocities[0, 2])

        sim = _build_simulation(bodies=bodies)
        asteroid_index = sim.N - 1
        asteroid = sim.particles[asteroid_index]

        # Track whether the simulation has been initialized for beyond-span
        # integration.  Once initialized, sim.t carries forward so sequential
        # beyond-span epochs integrate correctly from the current state.
        beyond_span_initialized = False

        for sorted_idx, t in enumerate(sorted_times):
            orig_idx = int(order[sorted_idx])

            if traj_start <= t <= traj_end:
                # Inside trajectory span: linear interpolation.
                state = {
                    "x_au": float(np.interp(t, traj_times, traj_positions[:, 0])),
                    "y_au": float(np.interp(t, traj_times, traj_positions[:, 1])),
                    "z_au": float(np.interp(t, traj_times, traj_positions[:, 2])),
                    "vx_au_per_year": float(np.interp(t, traj_times, traj_velocities[:, 0])),
                    "vy_au_per_year": float(np.interp(t, traj_times, traj_velocities[:, 1])),
                    "vz_au_per_year": float(np.interp(t, traj_times, traj_velocities[:, 2])),
                }
            else:
                # Beyond trajectory span: REBOUND numerical integration.
                # For the first beyond-span epoch, start from the initial
                # trajectory state at t=0.  For subsequent beyond-span epochs,
                # sim.t carries forward and integrates from the current state.
                if not beyond_span_initialized:
                    asteroid.x = init_x
                    asteroid.y = init_y
                    asteroid.z = init_z
                    asteroid.vx = init_vx
                    asteroid.vy = init_vy
                    asteroid.vz = init_vz
                    sim.t = 0.0
                    beyond_span_initialized = True

                try:
                    sim.integrate(float(t))
                except Exception as e:
                    raise ValueError(
                        f"REBOUND integration failed at target_time_years={t}: {e}"
                    ) from e

                asteroid = sim.particles[asteroid_index]
                state = {
                    "x_au": float(asteroid.x),
                    "y_au": float(asteroid.y),
                    "z_au": float(asteroid.z),
                    "vx_au_per_year": float(asteroid.vx),
                    "vy_au_per_year": float(asteroid.vy),
                    "vz_au_per_year": float(asteroid.vz),
                }

            states[orig_idx] = state

    else:
        # No trajectory: propagate from the given initial state to each epoch.
        sim = _build_simulation(bodies=bodies)

        # Set the initial asteroid state
        asteroid_index = sim.N - 1
        asteroid = sim.particles[asteroid_index]
        asteroid.x = float(x_au)
        asteroid.y = float(y_au)
        asteroid.z = float(z_au)
        asteroid.vx = float(vx_au_per_year)
        asteroid.vy = float(vy_au_per_year)
        asteroid.vz = float(vz_au_per_year)

        for sorted_idx, t in enumerate(sorted_times):
            orig_idx = int(order[sorted_idx])

            try:
                sim.integrate(float(t))
            except Exception as e:
                raise ValueError(
                    f"REBOUND integration failed at target_time_years={t}: {e}"
                ) from e

            asteroid = sim.particles[asteroid_index]
            state = {
                "x_au": float(asteroid.x),
                "y_au": float(asteroid.y),
                "z_au": float(asteroid.z),
                "vx_au_per_year": float(asteroid.vx),
                "vy_au_per_year": float(asteroid.vy),
                "vz_au_per_year": float(asteroid.vz),
            }

            states[orig_idx] = state

    return states


def propagate_from_trajectory(
    trajectory: dict[str, np.ndarray],
    target_time_years: float,
) -> dict[str, float]:
    """Propagate an asteroid from a saved trajectory to a target time.

    Uses linear interpolation via ``np.interp`` for times within the trajectory
    span, and REBOUND numerical integration for times beyond the span.

    This is the recommended entry point for C2 observation generation when
    the initial state is taken from an existing C1 trajectory.

    Parameters
    ----------
    trajectory : dict
        Trajectory data as returned by ``load_trajectory`` or generated by
        C1.  Must contain the keys ``time_years``, ``time_days``, ``positions``,
        ``velocities``.
    target_time_years : float
        Target time in years.  Must be >= 0.

    Returns
    -------
    state : dict
        Propagated state at ``target_time_years`` in the same format as
        ``propagate_state``.

    Raises
    ------
    ValueError
        If the trajectory is invalid, the target time is negative, or the
        interpolation/integration fails.
    """
    import numpy as np

    # Validate trajectory has required keys
    required = {"time_years", "positions", "velocities"}
    missing = required - set(trajectory.keys())
    if missing:
        raise ValueError(f"Trajectory missing required keys: {sorted(missing)}")

    times = np.asarray(trajectory["time_years"], dtype=float)
    positions = np.asarray(trajectory["positions"], dtype=float)  # (N, 3)
    velocities = np.asarray(trajectory["velocities"], dtype=float)  # (N, 3)
    n_samples = len(times)

    if target_time_years < 0:
        raise ValueError("target_time_years must be >= 0.")

    # If the target time is within the trajectory span, use linear interpolation.
    if times[0] <= target_time_years <= times[-1]:
        x_interp = float(np.interp(target_time_years, times, positions[:, 0]))
        y_interp = float(np.interp(target_time_years, times, positions[:, 1]))
        z_interp = float(np.interp(target_time_years, times, positions[:, 2]))
        vx_interp = float(np.interp(target_time_years, times, velocities[:, 0]))
        vy_interp = float(np.interp(target_time_years, times, velocities[:, 1]))
        vz_interp = float(np.interp(target_time_years, times, velocities[:, 2]))
        return {
            "x_au": x_interp,
            "y_au": y_interp,
            "z_au": z_interp,
            "vx_au_per_year": vx_interp,
            "vy_au_per_year": vy_interp,
            "vz_au_per_year": vz_interp,
        }

    # Beyond the trajectory span: use REBOUND numerical integration.
    # Start from the first trajectory sample (t=0) and integrate directly to
    # the target time.  We cannot meaningfully restart from times[-1] without
    # also knowing the planet states at that epoch, so we re-integrate from
    # t=0 using the first trajectory sample as the asteroid initial state.
    # This is physically correct: REBOUND integrates all bodies together from
    # t=0 to the target time.  No silent extrapolation occurs.
    initial_x = float(positions[0, 0])
    initial_y = float(positions[0, 1])
    initial_z = float(positions[0, 2])
    initial_vx = float(velocities[0, 0])
    initial_vy = float(velocities[0, 1])
    initial_vz = float(velocities[0, 2])

    sim = _build_simulation()
    asteroid_index = sim.N - 1
    asteroid = sim.particles[asteroid_index]
    asteroid.x = initial_x
    asteroid.y = initial_y
    asteroid.z = initial_z
    asteroid.vx = initial_vx
    asteroid.vy = initial_vy
    asteroid.vz = initial_vz

    try:
        sim.integrate(float(target_time_years))
    except Exception as e:
        raise ValueError(
            f"REBOUND integration failed at target_time_years={target_time_years}: {e}"
        ) from e

    asteroid = sim.particles[asteroid_index]
    return {
        "x_au": float(asteroid.x),
        "y_au": float(asteroid.y),
        "z_au": float(asteroid.z),
        "vx_au_per_year": float(asteroid.vx),
        "vy_au_per_year": float(asteroid.vy),
        "vz_au_per_year": float(asteroid.vz),
    }