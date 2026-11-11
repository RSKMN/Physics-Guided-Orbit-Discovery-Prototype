
import numpy as np


ARCSEC_TO_DEG = 1.0 / 3600.0


def add_measurement_noise(
    ra_deg,
    dec_deg,
    sigma_ra_cosdec_arcsec=0.5,
    sigma_dec_arcsec=0.5,
    random_seed=42
):
    """
    Add Gaussian angular measurement noise to RA and Dec.

    RA uncertainty is specified in the tangent-plane
    direction: sigma_RA * cos(Dec).

    Returns:
        noisy_ra_deg
        noisy_dec_deg
        ra_noise_arcsec
        dec_noise_arcsec
    """

    ra_deg = np.asarray(ra_deg, dtype=float)
    dec_deg = np.asarray(dec_deg, dtype=float)

    if ra_deg.shape != dec_deg.shape:
        raise ValueError("RA and Dec arrays must have matching shapes.")

    if not np.isfinite(ra_deg).all() or not np.isfinite(dec_deg).all():
        raise ValueError("Coordinates must contain finite values.")

    if np.any((dec_deg < -90) | (dec_deg > 90)):
        raise ValueError("Declination must be between -90 and +90 degrees.")

    if sigma_ra_cosdec_arcsec < 0 or sigma_dec_arcsec < 0:
        raise ValueError("Noise uncertainties cannot be negative.")

    rng = np.random.default_rng(random_seed)

    # Independent Gaussian measurement errors
    ra_noise_arcsec = rng.normal(
        0.0, sigma_ra_cosdec_arcsec, size=ra_deg.shape
    )

    dec_noise_arcsec = rng.normal(
        0.0, sigma_dec_arcsec, size=dec_deg.shape
    )

    # Convert tangent-plane RA error to coordinate RA error
    cos_dec = np.cos(np.deg2rad(dec_deg))

    if np.any(np.abs(cos_dec) < 1e-12) and sigma_ra_cosdec_arcsec > 0:
        raise ValueError(
            "RA noise conversion is singular at the celestial poles."
        )

    ra_offset_deg = (
        ra_noise_arcsec * ARCSEC_TO_DEG / cos_dec
    )

    dec_offset_deg = (
        dec_noise_arcsec * ARCSEC_TO_DEG
    )

    noisy_ra_deg = np.mod(ra_deg + ra_offset_deg, 360.0)
    noisy_dec_deg = dec_deg + dec_offset_deg

    if np.any((noisy_dec_deg < -90) | (noisy_dec_deg > 90)):
        raise ValueError(
            "Noise produced declination outside the valid range."
        )

    return (
        noisy_ra_deg,
        noisy_dec_deg,
        ra_noise_arcsec,
        dec_noise_arcsec
    )
