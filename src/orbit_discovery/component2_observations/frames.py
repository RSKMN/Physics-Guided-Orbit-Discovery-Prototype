
import numpy as np


def ecliptic_to_equatorial(
    relative_positions,
    obliquity_deg=23.43928
):
    """
    Convert ecliptic Cartesian vectors into equatorial
    Cartesian vectors.

    Input and output vectors use the same distance unit.
    """

    positions = np.asarray(relative_positions, dtype=float)

    if positions.ndim != 2 or positions.shape[1] != 3:
        raise ValueError("Positions must have shape (N, 3).")

    if not np.isfinite(positions).all():
        raise ValueError("Positions contain invalid values.")

    obliquity = np.deg2rad(obliquity_deg)

    x = positions[:, 0]
    y = positions[:, 1]
    z = positions[:, 2]

    x_eq = x
    y_eq = y * np.cos(obliquity) - z * np.sin(obliquity)
    z_eq = y * np.sin(obliquity) + z * np.cos(obliquity)

    return np.column_stack((x_eq, y_eq, z_eq))


def calculate_ra_dec(equatorial_positions):
    """
    Calculate right ascension and declination.

    Returns:
        RA in degrees, normalized to [0, 360).
        Dec in degrees, within [-90, 90].
    """

    positions = np.asarray(equatorial_positions, dtype=float)

    if positions.ndim != 2 or positions.shape[1] != 3:
        raise ValueError("Positions must have shape (N, 3).")

    if not np.isfinite(positions).all():
        raise ValueError("Positions contain invalid values.")

    x = positions[:, 0]
    y = positions[:, 1]
    z = positions[:, 2]

    distances = np.linalg.norm(positions, axis=1)

    if np.any(distances == 0):
        raise ValueError("Cannot calculate coordinates for zero vectors.")

    ra_rad = np.arctan2(y, x)
    dec_rad = np.arctan2(z, np.sqrt(x**2 + y**2))

    ra_deg = np.mod(np.rad2deg(ra_rad), 360.0)
    dec_deg = np.rad2deg(dec_rad)

    return ra_deg, dec_deg
