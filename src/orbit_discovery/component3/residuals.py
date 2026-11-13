"""Component 3 Phase 3B: angular residuals and chi-square for orbit estimation.

Computes the weighted nonlinear least-squares residuals used by the orbit
estimator: wrapped right-ascension residuals (tangent-plane, cos(dec)-weighted)
and declination residuals, converted to arcseconds and normalized by the
per-observation measurement uncertainties.

Design notes (see docs/component-3/PHASE_3_DESIGN.md, Section 3):

* ``sigma_ra_cosdec_arcsec`` is the tangent-plane RA uncertainty, i.e. it already
  contains one factor of cos(dec).  The wrapped RA difference is multiplied by
  cos(dec_obs) exactly once (the **observed** declination is the fixed
  reference), then converted to arcseconds.  No double application of cos(dec).
* Declination residuals are not wrapped because both observed and predicted
  declination lie in [-90, 90], so the difference is bounded by [-180, 180].
* Observations near the celestial pole (|cos(dec_obs)| below threshold) are
  geometrically degenerate and are screened out up front; the residual vector
  keeps a fixed structure over the retained observations.
* chi2 = r^T r over the normalized residuals.

This module is NumPy-only and contains no optimizer, no estimator, no forward
model, and no reference to ground truth.
"""

from __future__ import annotations

from typing import Any

import numpy as np


#: Threshold below which |cos(dec)| treats an observation as pole-degenerate.
#: Consistent with the C2 noise generator's pole guard.
POLE_COS_DEC_THRESHOLD: float = 1e-12

#: Arcseconds per degree (1 degree = 3600 arcseconds).
ARCCSEC_PER_DEGREE: float = 3600.0


def wrap_ra_difference(dra_raw_deg: float | np.ndarray) -> float | np.ndarray:
    """Wrap a raw right-ascension difference into [-180, 180) degrees.

    Implements ``((dra + 180) mod 360) - 180`` so that the residual is the
    shortest angular distance across the RA = 0/360 branch cut.  Applied once,
    before the cos(dec) factor.

    Parameters
    ----------
    dra_raw_deg : float or array-like
        Raw RA difference ``ra_obs - ra_pred`` in degrees.

    Returns
    -------
    float or ndarray
        Wrapped difference in [-180, 180) degrees.  A scalar input returns a
        Python float; an array input returns an ndarray of the same shape.
    """
    arr = np.asarray(dra_raw_deg, dtype=float)
    wrapped = ((arr + 180.0) % 360.0) - 180.0
    if wrapped.ndim == 0:
        return float(wrapped)
    return wrapped


def declination_difference(
    dec_obs_deg: float | np.ndarray,
    dec_pred_deg: float | np.ndarray,
) -> float | np.ndarray:
    """Declination residual ``dec_obs - dec_pred`` in degrees.

    No wrapping is applied because both observed and predicted declination lie
    in [-90, 90], so the difference is bounded by [-180, 180].

    Parameters
    ----------
    dec_obs_deg : float or array-like
        Observed declination in degrees.
    dec_pred_deg : float or array-like
        Predicted declination in degrees.

    Returns
    -------
    float or ndarray
        Declination difference in degrees.
    """
    obs = np.asarray(dec_obs_deg, dtype=float)
    pred = np.asarray(dec_pred_deg, dtype=float)
    dd = obs - pred
    if dd.ndim == 0:
        return float(dd)
    return dd


def pole_screen_mask(
    dec_obs_deg: float | np.ndarray,
    threshold: float = POLE_COS_DEC_THRESHOLD,
) -> bool | np.ndarray:
    """Screen observations for pole degeneracy.

    An observation is retained when ``|cos(dec_obs)| >= threshold``.  Near the
    celestial pole RA is ill-defined, so the tangent-plane RA residual is
    geometrically degenerate there.

    Parameters
    ----------
    dec_obs_deg : float or array-like
        Observed declination in degrees.
    threshold : float
        Minimum absolute value of cos(dec) for an observation to be retained.

    Returns
    -------
    bool or ndarray of bool
        ``True`` where the observation is retained (not pole-degenerate).  A
        scalar input returns a Python bool; an array input returns an ndarray.
    """
    arr = np.asarray(dec_obs_deg, dtype=float)
    threshold_f = float(threshold)
    if not np.isfinite(threshold_f) or not (0.0 < threshold_f <= 1.0):
        raise ValueError(
            "pole_threshold must be finite and in the interval (0, 1]."
        )
    cos_dec = np.cos(np.deg2rad(arr))
    mask = np.abs(cos_dec) >= threshold_f
    if mask.ndim == 0:
        return bool(mask)
    return mask


def compute_residuals(
    ra_obs_deg: float | np.ndarray,
    dec_obs_deg: float | np.ndarray,
    ra_pred_deg: float | np.ndarray,
    dec_pred_deg: float | np.ndarray,
    sigma_ra_cosdec_arcsec: float | np.ndarray,
    sigma_dec_arcsec: float | np.ndarray,
    pole_threshold: float = POLE_COS_DEC_THRESHOLD,
) -> dict[str, Any]:
    """Compute normalized angular residuals for a set of observations.

    For each observation ``i``:

    * ``dra_wrap = wrap(ra_obs - ra_pred)``  (deg, in [-180, 180))
    * ``dra_tan_arcsec = dra_wrap * cos(dec_obs) * 3600``  (arcsec)
    * ``dd_arcsec = (dec_obs - dec_pred) * 3600``  (arcsec, no wrapping)
    * ``w_ra = dra_tan_arcsec / sigma_ra_cosdec_arcsec``  (dimensionless)
    * ``w_dec = dd_arcsec / sigma_dec_arcsec``  (dimensionless)

    ``cos(dec_obs)`` uses the **observed** declination as the fixed reference,
    so the residual contains exactly one factor of cos(dec), matching the single
    cos(dec) already embedded in ``sigma_ra_cosdec_arcsec`` -- no double
    application.

    Observations with ``|cos(dec_obs)| < pole_threshold`` are excluded from the
    returned residual vector (both their RA and Dec components).  The residual
    vector keeps a fixed structure over the retained observations.

    Parameters
    ----------
    ra_obs_deg, dec_obs_deg : array-like
        Observed RA and declination in degrees.
    ra_pred_deg, dec_pred_deg : array-like
        Predicted RA and declination in degrees (from the forward model).
    sigma_ra_cosdec_arcsec, sigma_dec_arcsec : array-like
        Per-observation RA (tangent-plane) and Dec uncertainties in arcseconds.
        Must be positive and finite.
    pole_threshold : float
        Pole-screening threshold on |cos(dec_obs)|.

    Returns
    -------
    dict
        ``ra_arcsec``               : RA tangent-plane residual in arcsec (all obs)
        ``dec_arcsec``              : Dec residual in arcsec (all obs)
        ``ra_normalized``           : RA residual normalized by sigma (all obs)
        ``dec_normalized``          : Dec residual normalized by sigma (all obs)
        ``valid_mask``              : bool ndarray, True where observation retained
        ``residual_vector``         : 1-D ndarray of normalized residuals for
                                      retained observations, interleaved
                                      [w_ra_1, w_dec_1, w_ra_2, w_dec_2, ...]
        ``n_valid_scalar_residuals``: length of ``residual_vector``
        ``n_observations``          : total number of observations
        ``n_retained``              : number retained after pole screening
        ``n_excluded``              : number excluded by pole screening
    """
    ra_obs = np.asarray(ra_obs_deg, dtype=float)
    dec_obs = np.asarray(dec_obs_deg, dtype=float)
    ra_pred = np.asarray(ra_pred_deg, dtype=float)
    dec_pred = np.asarray(dec_pred_deg, dtype=float)
    sigma_ra = np.asarray(sigma_ra_cosdec_arcsec, dtype=float)
    sigma_dec = np.asarray(sigma_dec_arcsec, dtype=float)

    shapes = {
        "ra_obs": ra_obs.shape,
        "dec_obs": dec_obs.shape,
        "ra_pred": ra_pred.shape,
        "dec_pred": dec_pred.shape,
        "sigma_ra": sigma_ra.shape,
        "sigma_dec": sigma_dec.shape,
    }
    if not all(s == shapes["ra_obs"] for s in shapes.values()):
        raise ValueError(
            "All input arrays must have the same shape; got " + str(shapes)
        )

    if ra_obs.size == 0:
        raise ValueError("At least one observation is required.")

    # Validate angular inputs: finite values and declinations in [-90, 90].
    for name, arr in (
        ("ra_obs_deg", ra_obs),
        ("dec_obs_deg", dec_obs),
        ("ra_pred_deg", ra_pred),
        ("dec_pred_deg", dec_pred),
    ):
        if not np.all(np.isfinite(arr)):
            raise ValueError(f"{name} must contain only finite values.")
    if np.any((dec_obs < -90.0) | (dec_obs > 90.0)):
        raise ValueError("Observed declination must be within [-90, 90] degrees.")
    if np.any((dec_pred < -90.0) | (dec_pred > 90.0)):
        raise ValueError("Predicted declination must be within [-90, 90] degrees.")

    if not np.all(np.isfinite(sigma_ra)) or not np.all(np.isfinite(sigma_dec)):
        raise ValueError("Measurement uncertainties must be finite.")
    if np.any(sigma_ra <= 0) or np.any(sigma_dec <= 0):
        raise ValueError("Measurement uncertainties must be strictly positive.")

    # Pole screen: retain observations where |cos(dec_obs)| >= threshold.
    # (pole_screen_mask validates pole_threshold.)
    valid_mask = np.asarray(pole_screen_mask(dec_obs, pole_threshold), dtype=bool)
    n_retained = int(valid_mask.sum())
    if n_retained == 0:
        raise ValueError(
            "No observations retained after pole screening: every observation "
            "has |cos(dec_obs)| below the pole threshold."
        )

    # RA residual: wrap once, then apply cos(dec_obs) (observed reference),
    # then convert degrees -> arcseconds.  cos(dec) applied exactly once.
    dra_raw = ra_obs - ra_pred
    dra_wrap = wrap_ra_difference(dra_raw)
    cos_dec_obs = np.cos(np.deg2rad(dec_obs))
    dra_arcsec = dra_wrap * cos_dec_obs * ARCCSEC_PER_DEGREE

    # Dec residual: no wrapping, convert to arcseconds.
    dd = declination_difference(dec_obs, dec_pred)
    dd_arcsec = dd * ARCCSEC_PER_DEGREE

    # Normalize by uncertainties.
    ra_normalized = dra_arcsec / sigma_ra
    dec_normalized = dd_arcsec / sigma_dec

    # Build the fixed residual vector over retained observations only,
    # interleaved as [w_ra_1, w_dec_1, w_ra_2, w_dec_2, ...].
    valid_ra = np.asarray(ra_normalized)[valid_mask]
    valid_dec = np.asarray(dec_normalized)[valid_mask]
    residual_vector = np.empty(2 * n_retained, dtype=float)
    residual_vector[0::2] = valid_ra
    residual_vector[1::2] = valid_dec

    return {
        "ra_arcsec": dra_arcsec,
        "dec_arcsec": dd_arcsec,
        "ra_normalized": ra_normalized,
        "dec_normalized": dec_normalized,
        "valid_mask": valid_mask,
        "residual_vector": residual_vector,
        "n_valid_scalar_residuals": int(residual_vector.size),
        "n_observations": int(ra_obs.size),
        "n_retained": n_retained,
        "n_excluded": int(ra_obs.size) - n_retained,
    }


def chi_square(residual_vector: float | np.ndarray) -> float:
    """Chi-square objective ``chi2 = r^T r = sum(r^2)``.

    Parameters
    ----------
    residual_vector : array-like
        One-dimensional vector of normalized residuals (e.g. the
        ``residual_vector`` returned by :func:`compute_residuals`).

    Returns
    -------
    float
        Chi-square value, dimensionless.
    """
    r = np.asarray(residual_vector, dtype=float)
    if r.ndim != 1:
        r = r.ravel()
    if r.size == 0:
        raise ValueError("residual_vector must not be empty.")
    if not np.all(np.isfinite(r)):
        raise ValueError("residual_vector must not contain NaN or infinite values.")
    return float(np.dot(r, r))
