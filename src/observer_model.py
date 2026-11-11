
import numpy as np


def calculate_observer_positions(
    time_years,
    orbital_radius_au=1.0,
    orbital_period_years=1.0,
    initial_phase_deg=90.0
):
    """
    Calculate idealized observer positions in heliocentric
    ecliptic coordinates.

    Returns positions in AU with shape (N, 3).
    """

    time_years = np.asarray(time_years, dtype=float)

    if not np.isfinite(time_years).all():
        raise ValueError("Time values must be finite.")

    if orbital_radius_au <= 0:
        raise ValueError("Orbital radius must be positive.")

    if orbital_period_years <= 0:
        raise ValueError("Orbital period must be positive.")

    phase_rad = np.deg2rad(initial_phase_deg)

    angle = (
        2.0 * np.pi * time_years / orbital_period_years
        + phase_rad
    )

    x = orbital_radius_au * np.cos(angle)
    y = orbital_radius_au * np.sin(angle)
    z = np.zeros_like(time_years)

    return np.column_stack((x, y, z))


def calculate_relative_positions(
    asteroid_positions,
    observer_positions
):
    """
    Calculate asteroid positions relative to the observer.

    Both input arrays must use the same coordinate frame
    and distance unit.

    Returns asteroid-observer vectors in AU.
    """

    asteroid_positions = np.asarray(
        asteroid_positions, dtype=float
    )

    observer_positions = np.asarray(
        observer_positions, dtype=float
    )

    if asteroid_positions.shape != observer_positions.shape:
        raise ValueError(
            "Asteroid and observer position arrays must have "
            "the same shape."
        )

    if asteroid_positions.ndim != 2 or asteroid_positions.shape[1] != 3:
        raise ValueError("Position arrays must have shape (N, 3).")

    if not np.isfinite(asteroid_positions).all():
        raise ValueError("Asteroid positions contain invalid values.")

    if not np.isfinite(observer_positions).all():
        raise ValueError("Observer positions contain invalid values.")

    return asteroid_positions - observer_positions
