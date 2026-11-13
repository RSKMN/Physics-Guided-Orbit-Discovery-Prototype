"""C3-facing observation loader.

Provides a strict interface for Component 3 (orbit estimation) to load
standardized observation datasets.  This loader **never** exposes ground-truth
information; it returns only measurement data that would be available to an
orbit-determination algorithm operating on real astronomical observations.

The design enforces the truth-separation boundary established in Phase 1:
- Observation CSV contains no ``true_*`` columns.
- Ground truth resides in a separate ``ground_truth.json`` file.
- This loader only reads the observation CSV.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from orbit_discovery.component2_observations.schema import (
    V2_FORBIDDEN,
    V2_REQUIRED,
    validate_observation_schema,
)


def load_observation_dataset(
    csv_path: Path | str,
    *,
    validate: bool = True,
) -> dict[str, Any]:
    """Load an observation dataset from a CSV file.

    Parameters
    ----------
    csv_path : Path or str
        Path to the observation CSV file (``observations.csv``).
    validate : bool, optional
        Whether to validate the dataset against the v2 schema.
        Defaults to ``True``. Set to ``False`` for performance when the
        caller already guarantees schema compliance.

    Returns
    -------
    dict
        A dictionary with the following keys:

        - ``"obs_id"``: ``np.ndarray[int]`` - observation identifiers.
        - ``"time_days"``: ``np.ndarray[float]`` - elapsed days from reference epoch.
        - ``"time_years"``: ``np.ndarray[float]`` - elapsed years from reference epoch.
        - ``"ra_deg"``: ``np.ndarray[float]`` - right ascension in degrees.
        - ``"dec_deg"``: ``np.ndarray[float]`` - declination in degrees.
        - ``"sigma_ra_cosdec_arcsec"``: ``np.ndarray[float]`` - RA uncertainty in arcseconds.
        - ``"sigma_dec_arcsec"``: ``np.ndarray[float]`` - Dec uncertainty in arcseconds.
        - ``"frame"``: ``str`` - coordinate frame (from ``"frame"`` column).
        - ``"time_scale"``: ``str`` - time scale (from ``"time_scale"`` column).

        No ``true_ra_deg``, ``true_dec_deg``, or other ground-truth fields
        are included.

    Raises
    ------
    FileNotFoundError
        If ``csv_path`` does not exist.
    ValueError
        If ``validate`` is ``True`` and the dataset fails schema validation.
        Specifically, if forbidden columns (e.g. ``true_ra_deg``) are present.
    """
    path = Path(csv_path)

    if not path.exists():
        raise FileNotFoundError(f"Observation file not found: {path}")

    df = pd.read_csv(path)

    if validate:
        errors = validate_observation_schema(df)
        if errors:
            raise ValueError("Schema validation failed: " + "; ".join(errors))

    # --- Check for forbidden columns (ground-truth leakage) ---
    found_forbidden = set(df.columns) & V2_FORBIDDEN
    if found_forbidden:
        raise ValueError(
            f"Forbidden columns present in observation dataset: "
            f"{sorted(found_forbidden)}. "
            "These columns reveal ground-truth information and must be "
            "in a separate ground-truth dataset, not the observation CSV.",
        )

    # --- Extract required numeric columns ---
    result: Dict[str, Any] = {}
    numeric_required = V2_REQUIRED - {"frame", "time_scale"}
    for col in numeric_required:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}.")
        result[col] = df[col].to_numpy().astype(float)

    # --- Optional string columns ---
    result["frame"] = str(df["frame"].iloc[0]) if "frame" in df.columns else ""
    result["time_scale"] = (
        str(df["time_scale"].iloc[0]) if "time_scale" in df.columns else ""
    )

    return result


def load_observation_csv(csv_path: Path | str) -> pd.DataFrame:
    """Load the observation CSV into a pandas DataFrame without validation.

    This is a lower-level helper for code that already guarantees schema
    compliance and just needs the raw DataFrame.

    Parameters
    ----------
    csv_path : Path or str
        Path to the observation CSV file.

    Returns
    -------
    pandas.DataFrame
        The observation data.
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Observation file not found: {path}")
    return pd.read_csv(path)