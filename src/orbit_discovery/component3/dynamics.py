"""Component 3 dynamics: REBOUND-based forward propagation for trial orbits.

Constructs a fresh REBOUND simulation using Component 1's authoritative planetary
initial conditions (imported from ``configurable_simulator.BODY_DATA`` to avoid
duplicating planetary constants) and propagates a massless trial asteroid from
a supplied six-dimensional Cartesian state.

Conventions (matching Component 1):
- Units: AU, AU/year, years (REBOUND sim.units = ("yr", "AU", "Msun"))
- Frame: heliocentric ecliptic inertial
- Integrator: IAS15, epsilon = 1e-12
- Planets: circular, coplanar (e=0, inc=0), at perihelion on +x axis
- Asteroid: massless (m=0.0)
- Gravitational parameter: REBOUND's sim.G = 39.476926421373 with M_sun = 1.0 Msun
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import rebound

# Import BODY_DATA from Component 1 to avoid duplicating planetary constants.
from configurable_simulator import BODY_DATA  # noqa: E402

#: Default gravitational bodies (matches Component 1 synthetic scenarios).
DEFAULT_BODIES: list[str] = ["Sun", "Mercury", "Venus", "Earth", "Jupiter"]

#: Integrator settings matching Component 1.
DEFAULT_INTEGRATOR: str = "ias15"
DEFAULT_INTEGRATOR_EPSILON: float = 1e-12


def build_trial_simulation(
    bodies: list[str] | None = None,
    integrator_epsilon: float = DEFAULT_INTEGRATOR_EPSILON,
) -> rebound.Simulation:
    """Build a fresh REBOUND simulation matching Component 1's planetary model.

    The simulation contains the Sun, the requested planets (circular, coplanar
    initial conditions matching C1's BODY_DATA), and a massless placeholder
    asteroid particle as the last particle.  The caller sets the asteroid's
    Cartesian state after construction.

    Parameters
    ----------
    bodies : list of str, optional
        Gravitational bodies to include.  Defaults to C1's standard set.
    integrator_epsilon : float
        IAS15 integrator epsilon.

    Returns
    -------
    sim : rebound.Simulation
        Configured simulation with the asteroid as the last particle.

    Raises
    ------
    ValueError
        If ``Sun`` is not in ``bodies`` or an unsupported body is requested.
    """
    if bodies is None:
        bodies = list(DEFAULT_BODIES)

    if "Sun" not in bodies:
        raise ValueError("'Sun' must be included in gravitational_bodies.")

    sim = rebound.Simulation()
    sim.units = ("yr", "AU", "Msun")

    # Sun at the origin
    sim.add(m=1.0)

    # Planets: circular, coplanar, matching C1's BODY_DATA exactly
    for name in bodies:
        if name == "Sun":
            continue
        if name not in BODY_DATA:
            raise ValueError(f"Unsupported gravitational body: {name}")
        body = BODY_DATA[name]
        sim.add(
            m=body["mass"],
            a=body["a"],
            e=0.0,
            inc=0.0,
        )

    # Massless asteroid placeholder (state set by the caller)
    sim.add(m=0.0)

    sim.move_to_com()
    sim.integrator = DEFAULT_INTEGRATOR
    sim.integrator.epsilon = integrator_epsilon

    return sim


def _set_asteroid_state_heliocentric(
    sim: rebound.Simulation,
    sun_index: int,
    asteroid_index: int,
    rx: float,
    ry: float,
    rz: float,
    vx: float,
    vy: float,
    vz: float,
) -> None:
    """Set the asteroid's state as heliocentric (Sun-relative) Cartesian.

    After ``sim.move_to_com()``, the Sun is no longer at the origin.  The
    supplied state is interpreted as heliocentric coordinates, so we add the
    Sun's COM-frame position/velocity to place the asteroid correctly.
    """
    sun = sim.particles[sun_index]
    asteroid = sim.particles[asteroid_index]

    asteroid.x = sun.x + rx
    asteroid.y = sun.y + ry
    asteroid.z = sun.z + rz
    asteroid.vx = sun.vx + vx
    asteroid.vy = sun.vy + vy
    asteroid.vz = sun.vz + vz


def _get_asteroid_state_heliocentric(
    sim: rebound.Simulation,
    sun_index: int,
    asteroid_index: int,
    epoch_years: float,
) -> dict[str, Any]:
    """Read the asteroid's state as heliocentric (Sun-relative) Cartesian."""
    sun = sim.particles[sun_index]
    asteroid = sim.particles[asteroid_index]

    return {
        "epoch_years": float(epoch_years),
        "x_au": float(asteroid.x - sun.x),
        "y_au": float(asteroid.y - sun.y),
        "z_au": float(asteroid.z - sun.z),
        "vx_au_per_year": float(asteroid.vx - sun.vx),
        "vy_au_per_year": float(asteroid.vy - sun.vy),
        "vz_au_per_year": float(asteroid.vz - sun.vz),
    }


def propagate_trial_state(
    state: Any,
    epochs_years: list[float],
    bodies: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Propagate a trial asteroid state to multiple epochs.

    Uses a fresh REBOUND IAS15 simulation matching Component 1's physical model.
    The supplied state is interpreted as heliocentric Cartesian coordinates
    (AU, AU/year) in the heliocentric ecliptic inertial frame at the reference
    epoch (t = 0.0 yr).

    The simulation is built once and all epochs are integrated sequentially
    in sorted order for efficiency.  Results are returned in the original
    input order.

    Parameters
    ----------
    state : OrbitState
        Six-dimensional Cartesian asteroid state at the reference epoch.
    epochs_years : list of float
        Target epochs in elapsed simulation years.  Must be >= 0 and finite.
    bodies : list of str, optional
        Gravitational bodies.  Defaults to C1's standard set.

    Returns
    -------
    list of dict
        One entry per epoch, in input order, each with:
        ``epoch_years``, ``x_au``, ``y_au``, ``z_au``,
        ``vx_au_per_year``, ``vy_au_per_year``, ``vz_au_per_year``.

    Raises
    ------
    TypeError
        If ``state`` is not an OrbitState instance.
    ValueError
        If the state is non-finite, any epoch is negative or non-finite, or
        REBOUND integration fails.
    """
    from orbit_discovery.component3.models import OrbitState

    if not isinstance(state, OrbitState):
        raise TypeError("state must be an OrbitState instance.")

    state.validate()

    times = np.asarray(epochs_years, dtype=float)
    if times.size == 0:
        return []

    for t in times:
        if t < 0:
            raise ValueError(f"Epoch must be >= 0, got {t}.")
        if not math.isfinite(float(t)):
            raise ValueError(f"Epoch must be finite, got {t}.")

    sim = build_trial_simulation(bodies=bodies)
    sun_index = 0
    asteroid_index = sim.N - 1

    # Set the initial asteroid state (heliocentric, at reference epoch t=0)
    _set_asteroid_state_heliocentric(
        sim, sun_index, asteroid_index,
        state.rx, state.ry, state.rz,
        state.vx, state.vy, state.vz,
    )

    # Sort epochs for sequential REBOUND integration; track original order.
    order = np.argsort(times, kind="stable")
    sorted_times = times[order]

    results: list[dict[str, Any] | None] = [None] * len(times)

    for sorted_idx, t in enumerate(sorted_times):
        orig_idx = int(order[sorted_idx])
        t_float = float(t)

        try:
            sim.integrate(t_float)
        except Exception as e:
            raise ValueError(
                f"REBOUND integration failed at epoch_years={t_float}: {e}"
            ) from e

        results[orig_idx] = _get_asteroid_state_heliocentric(
            sim, sun_index, asteroid_index, t_float
        )

    return results  # type: ignore[return-value]


def propagate_trial_state_single(
    state: Any,
    target_time_years: float,
    bodies: list[str] | None = None,
) -> dict[str, Any]:
    """Propagate a trial asteroid state to a single epoch.

    Convenience wrapper around :func:`propagate_trial_state`.
    """
    results = propagate_trial_state(state, [target_time_years], bodies=bodies)
    return results[0]
