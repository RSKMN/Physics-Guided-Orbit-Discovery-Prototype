"""Explicit observer geometry for synthetic observations.

Observer position is represented as a time-dependent Cartesian state in
heliocentric ecliptic inertial coordinates.

Conventions:
- Position: x, y, z in AU.
- Velocity: vx, vy, vz in AU/year.
- Reference frame: heliocentric ecliptic inertial (same as Component 1).
- Time: decimal years (yr), consistent with C1 trajectory data.
- Default observer: circular Earth-like orbit in the ecliptic plane.
"""

from __future__ import annotations

import math

import numpy as np

#: Default orbital radius for Earth-like observer in AU
DEFAULT_ORBITAL_RADIUS_AU = 1.0

#: Default orbital period for Earth-like observer in years
DEFAULT_ORBITAL_PERIOD_YEARS = 1.0

#: Default obliquity for ecliptic-to-equatorial conversion in degrees
DEFAULT_OBLIQUITY_DEG = 23.43928


class ObserverConfig:
    """Configuration for an observer orbit.

    Parameters
    ----------
    orbital_radius_au : float, optional
        Circular orbit radius in AU. Default: 1.0 (Earth-like).
    orbital_period_years : float, optional
        Orbital period in years. Default: 1.0 (Earth-like year).
    eccentricity : float, optional
        Orbital eccentricity. Default: 0.0 (circular).
    inclination : float, optional
        Orbital inclination in radians. Default: 0.0 (equatorial).
    initial_phase_deg : float, optional
        Initial orbital phase in degrees. Default: 90.0.
    reference_epoch_years : float, optional
        Reference epoch for phase calculation. Default: 0.0.
    """

    def __init__(
        self,
        orbital_radius_au: float = DEFAULT_ORBITAL_RADIUS_AU,
        orbital_period_years: float = DEFAULT_ORBITAL_PERIOD_YEARS,
        eccentricity: float = 0.0,
        inclination: float = 0.0,
        initial_phase_deg: float = 90.0,
        reference_epoch_years: float = 0.0,
    ):
        self.orbital_radius_au = orbital_radius_au
        self.orbital_period_years = orbital_period_years
        self.eccentricity = eccentricity
        self.inclination = inclination
        self.initial_phase_deg = initial_phase_deg
        self.reference_epoch_years = reference_epoch_years


def calculate_observer_positions(
    time_years,
    orbital_radius_au: float = DEFAULT_ORBITAL_RADIUS_AU,
    orbital_period_years: float = DEFAULT_ORBITAL_PERIOD_YEARS,
    initial_phase_deg: float = 90.0,
) -> np.ndarray:
    """Calculate idealized observer positions in heliocentric
    ecliptic coordinates.

    Returns positions in AU with shape (N, 3).

    The observer follows a circular orbit in the ecliptic plane by default,
    which is compatible with the existing synthetic observation pipeline.

    Parameters
    ----------
    time_years : np.ndarray
        Observation times in decimal years, shape (N,).
    orbital_radius_au : float, optional
        Circular orbit radius in AU. Default: 1.0 (Earth-like).
    orbital_period_years : float, optional
        Orbital period in years. Default: 1.0 (Earth-like year).
    initial_phase_deg : float, optional
        Initial orbital phase in degrees. Default: 90.0 (observer at y-axis at t=0).

    Returns
    -------
    positions : np.ndarray
        Heliocentric position vectors, shape (N, 3) in AU.
        Column 0: x, Column 1: y, Column 2: z.
    """
    time_years = np.asarray(time_years, dtype=float)

    if not np.isfinite(time_years).all():
        raise ValueError("Time values must be finite.")

    if orbital_radius_au <= 0:
        raise ValueError("Orbital radius must be positive.")

    if orbital_period_years <= 0:
        raise ValueError("Orbital period must be positive.")

    # Convert initial phase to radians
    phase_rad = math.radians(initial_phase_deg)

    # Mean motion
    n = 2.0 * math.pi / orbital_period_years

    # Mean anomaly at each time sample
    # M = n * t + phase_rad (using t relative to epoch 0)
    mean_anomaly = n * time_years + phase_rad

    # Circular orbit solution
    # For circular orbit: x = r * cos(M), y = r * sin(M), z = 0
    x = orbital_radius_au * np.cos(mean_anomaly)
    y = orbital_radius_au * np.sin(mean_anomaly)
    z = np.zeros_like(time_years)

    # Circular orbit velocity: v = sqrt(mu/r) perpendicular to position
    # With mu = 1 in project units
    v_mag = math.sqrt(1.0 / orbital_radius_au)
    vx = -v_mag * np.sin(mean_anomaly)
    vy = v_mag * np.cos(mean_anomaly)
    vz = np.zeros_like(time_years)

    # Position shape (N, 3)
    positions = np.column_stack((x, y, z))

    return positions


def calculate_observer_velocities(
    time_years,
    orbital_radius_au: float = DEFAULT_ORBITAL_RADIUS_AU,
    orbital_period_years: float = DEFAULT_ORBITAL_PERIOD_YEARS,
    initial_phase_deg: float = 90.0,
) -> np.ndarray:
    """Calculate observer heliocentric velocities at given times.

    Parameters
    ----------
    time_years : np.ndarray
        Observation times in decimal years, shape (N,).
    orbital_radius_au : float, optional
        Circular orbit radius in AU. Default: 1.0.
    orbital_period_years : float, optional
        Orbital period in years. Default: 1.0.
    initial_phase_deg : float, optional
        Initial orbital phase in degrees. Default: 90.0.

    Returns
    -------
    velocities : np.ndarray
        Heliocentric velocity vectors, shape (N, 3) in AU/year.
        Column 0: vx, Column 1: vy, Column 2: vz.
    """
    time_years = np.asarray(time_years, dtype=float)

    if not np.isfinite(time_years).all():
        raise ValueError("Time values must be finite.")

    if orbital_radius_au <= 0:
        raise ValueError("Orbital radius must be positive.")

    if orbital_period_years <= 0:
        raise ValueError("Orbital period must be positive.")

    # Convert initial phase to radians
    phase_rad = math.radians(initial_phase_deg)

    # Mean motion
    n = 2.0 * math.pi / orbital_period_years

    # Mean anomaly
    mean_anomaly = n * time_years + phase_rad

    # Circular orbit velocity
    v_mag = math.sqrt(1.0 / orbital_radius_au)
    vx = -v_mag * np.sin(mean_anomaly)
    vy = v_mag * np.cos(mean_anomaly)
    vz = np.zeros_like(time_years)

    # Velocity shape (N, 3)
    velocities = np.column_stack((vx, vy, vz))

    return velocities


def calculate_relative_positions(
    asteroid_positions,
    observer_positions,
) -> np.ndarray:
    """Calculate asteroid positions relative to the observer.

    Both input arrays must use the same coordinate frame and distance unit.

    Parameters
    ----------
    asteroid_positions : np.ndarray
        Heliocentric asteroid position vectors, shape (N, 3) in AU.
    observer_positions : np.ndarray
        Heliocentric observer position vectors, shape (N, 3) in AU.

    Returns
    -------
    relative_positions : np.ndarray
        Asteroid-observer position vectors, shape (N, 3) in AU.
        Row i = asteroid_positions[i] - observer_positions[i].
    """
    asteroid_positions = np.asarray(asteroid_positions, dtype=float)
    observer_positions = np.asarray(observer_positions, dtype=float)

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


def calculate_line_of_sight(
    asteroid_positions,
    observer_positions,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Calculate line-of-sight vectors and properties.

    Parameters
    ----------
    asteroid_positions : np.ndarray
        Heliocentric asteroid position vectors, shape (N, 3) in AU.
    observer_positions : np.ndarray
        Heliocentric observer position vectors, shape (N, 3) in AU.

    Returns
    -------
    relative_positions : np.ndarray
        Asteroid-observer vectors, shape (N, 3) in AU.
    los_unit_vectors : np.ndarray
        Unit vectors along the line-of-sight, shape (N, 3).
    distances : np.ndarray
        Observer-to-asteroid distances in AU, shape (N,).
    """
    relative_positions = calculate_relative_positions(
        asteroid_positions, observer_positions
    )

    # Compute distances
    distances = np.linalg.norm(relative_positions, axis=1)

    # Compute unit vectors (handle zero distance)
    los_unit_vectors = np.zeros_like(relative_positions)
    non_zero_mask = distances > 0
    los_unit_vectors[non_zero_mask] = (
        relative_positions[non_zero_mask] / distances[non_zero_mask, np.newaxis]
    )

    return relative_positions, los_unit_vectors, distances


def calculate_sky_coordinates(
    los_unit_vectors,
    obliquity_deg: float = DEFAULT_OBLIQUITY_DEG,
) -> tuple[np.ndarray, np.ndarray]:
    """Convert line-of-sight unit vectors to sky coordinates (RA, Dec).

    Uses the ecliptic-to-equatorial transformation with the configured
    obliquity.

    Parameters
    ----------
    los_unit_vectors : np.ndarray
        Unit vectors along the line-of-sight, shape (N, 3).
    obliquity_deg : float, optional
        Ecliptic obliquity in degrees. Default: 23.43928.

    Returns
    -------
    ra_deg : np.ndarray
        Right ascension in degrees, shape (N), normalized to [0, 360).
    dec_deg : np.ndarray
        Declination in degrees, shape (N), within [-90, 90].
    """
    los_unit_vectors = np.asarray(los_unit_vectors, dtype=float)

    if los_unit_vectors.ndim != 2 or los_unit_vectors.shape[1] != 3:
        raise ValueError("LOV vectors must have shape (N, 3).")

    if not np.isfinite(los_unit_vectors).all():
        raise ValueError("LOV vectors contain invalid values.")

    # Ecliptic-to-equatorial transformation
    obliquity = math.radians(obliquity_deg)

    x = los_unit_vectors[:, 0]
    y = los_unit_vectors[:, 1]
    z = los_unit_vectors[:, 2]

    # Equatorial Cartesian components
    x_eq = x
    y_eq = y * math.cos(obliquity) - z * math.sin(obliquity)
    z_eq = y * math.sin(obliquity) + z * math.cos(obliquity)

    # Calculate RA and Dec using numpy functions for array compatibility
    ra_rad = np.arctan2(y_eq, x_eq)
    ra_deg = np.degrees(ra_rad)
    ra_deg = np.mod(ra_deg, 360.0)

    dec_rad = np.arctan2(z_eq, np.sqrt(x**2 + y**2))
    dec_deg = np.degrees(dec_rad)
    dec_deg = np.clip(dec_deg, -90.0, 90.0)

    return ra_deg, dec_deg


def calculate_solar_elongation(
    asteroid_positions,
    observer_positions,
    sun_position=None,
) -> np.ndarray:
    """Calculate solar elongation angle.

    Solar elongation is the angle between the observer-asteroid line-of-sight
    and the observer-Sun line-of-sight.

    Parameters
    ----------
    asteroid_positions : np.ndarray
        Heliocentric asteroid position vectors, shape (N, 3) in AU.
    observer_positions : np.ndarray
        Heliocentric observer position vectors, shape (N, 3) in AU.
    sun_position : np.ndarray, optional
        Heliocentric Sun position vector in AU. Default: [1.0, 0.0, 0.0].

    Returns
    -------
    elongation_deg : np.ndarray
        Solar elongation angles in degrees, shape (N,).
    """
    relative_positions, los_unit_vectors, distances = calculate_line_of_sight(
        asteroid_positions, observer_positions
    )

    # Default Sun position (heliocentric)
    if sun_position is None:
        sun_position = np.array([1.0, 0.0, 0.0])

    sun_position = np.asarray(sun_position, dtype=float)

    # Observer-Sun unit vector
    sun_dist = np.linalg.norm(sun_position)
    if sun_dist > 0:
        sun_unit = sun_position / sun_dist
    else:
        sun_unit = np.array([1.0, 0.0, 0.0])

    # Solar elongation: angle between LOS unit vector and Sun unit vector
    # cos(elongation) = LOS · Sun
    dot_products = np.sum(los_unit_vectors * sun_unit, axis=1)
    # Clip to [-1, 1] for arccos
    dot_products = np.clip(dot_products, -1.0, 1.0)

    elongation_rad = np.arccos(dot_products)
    elongation_deg = np.degrees(elongation_rad)

    return elongation_deg