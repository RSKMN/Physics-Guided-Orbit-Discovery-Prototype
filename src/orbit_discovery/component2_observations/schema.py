"""Schema validation for v2.0 standardized observation datasets."""

from __future__ import annotations

from typing import FrozenSet

import pandas as pd
from pathlib import Path


#: Forbidden column names (ground-truth-revealing).
#: These columns must NOT appear in the observation CSV;
#: they belong in a separate ground-truth dataset.
V2_FORBIDDEN: FrozenSet[str] = frozenset(
    {
        "true_ra_deg",
        "true_dec_deg",
        "true_x_au",
        "true_y_au",
        "true_z_au",
        "true_vx_au_per_year",
        "true_vy_au_per_year",
        "true_vz_au_per_year",
        "true_orbital_elements",
    }
)

#: Required column names for a v2.0 observation CSV.
V2_REQUIRED: FrozenSet[str] = frozenset(
    {
        "obs_id",
        "time_days",
        "time_years",
        "ra_deg",
        "dec_deg",
        "sigma_ra_cosdec_arcsec",
        "sigma_dec_arcsec",
    }
)

#: Allowed column names (required + optional).
V2_ALLOWED: FrozenSet[str] = frozenset(
    {
        "obs_id",
        "time_days",
        "time_years",
        "ra_deg",
        "dec_deg",
        "sigma_ra_cosdec_arcsec",
        "sigma_dec_arcsec",
        "frame",
        "time_scale",
        "epoch_jd_tdb",
        "observer_x_au",
        "observer_y_au",
        "observer_z_au",
        "observer_vx_au_per_year",
        "observer_vy_au_per_year",
        "observer_vz_au_per_year",
        "quality_flags",
        "source",
        "notes",
    }
)


def validate_observation_schema(
    df: pd.DataFrame,
    *,
    forbidden: FrozenSet[str] = V2_FORBIDDEN,
    required: FrozenSet[str] = V2_REQUIRED,
    allowed: FrozenSet[str] = V2_ALLOWED,
) -> list[str]:
    """Validate an observation DataFrame against the v2.0 schema.

    Parameters
    ----------
    df : pandas.DataFrame
        Observation dataset to validate.
    forbidden : FrozenSet[str], optional
        Column names that must NOT be present.
    required : FrozenSet[str], optional
        Column names that MUST be present.
    allowed : FrozenSet[str], optional
        Column names that are permitted (required + optional).

    Returns
    -------
    list[str]
        List of human-readable error messages. Empty list means validation
        passed.
    """
    errors: list[str] = []

    # 1. Check for forbidden columns
    found_forbidden = set(df.columns) & forbidden
    if found_forbidden:
        errors.append(
            f"Forbidden columns present: {sorted(found_forbidden)}. "
            "These reveal ground-truth information."
        )

    # 2. Check for missing required columns
    missing = required - set(df.columns)
    if missing:
        errors.append(f"Missing required columns: {sorted(missing)}.")

    # 3. Check for unexpected columns
    unexpected = set(df.columns) - allowed
    if unexpected:
        errors.append(
            f"Unexpected columns not in v2.0 schema: {sorted(unexpected)}. "
            "These are not part of the standardized observation format."
        )

    # 4. Check RA range
    if "ra_deg" in df.columns:
        ra = df["ra_deg"].astype(float)
        if not ra.between(0, 360, inclusive="left").all():
            errors.append("RA values outside [0, 360) degrees.")

    # 5. Check Dec range
    if "dec_deg" in df.columns:
        dec = df["dec_deg"].astype(float)
        if not dec.between(-90, 90).all():
            errors.append("Dec values outside [-90, 90] degrees.")

    # 6. Check uncertainties are positive
    for col in ["sigma_ra_cosdec_arcsec", "sigma_dec_arcsec"]:
        if col in df.columns:
            sig = df[col].astype(float)
            if (sig <= 0).any():
                errors.append(f"{col} must be positive (uncertainty).")

    return errors