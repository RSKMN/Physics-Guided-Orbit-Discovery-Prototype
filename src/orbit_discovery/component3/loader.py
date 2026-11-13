"""Component 3 observation loading service.

Provides a strict loading interface that wraps the Component 2 loader with
additional validation for orbit estimation requirements.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import numpy as np

from orbit_discovery.component2_observations.c3_loader import load_observation_dataset as c2_load
from orbit_discovery.component3.models import ObservationDataset


def load_dataset_for_estimation(csv_path: Path | str) -> ObservationDataset:
    """Load and validate an observation dataset for Component 3 estimation.

    Parameters
    ----------
    csv_path : Path or str
        Path to the observation CSV file.

    Returns
    -------
    ObservationDataset
        A validated dataset container.

    Raises
    ------
    FileNotFoundError
        If the CSV or its associated metadata.json is missing.
    ValueError
        If the dataset fails schema validation or C3-specific constraints.
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Observation file not found: {path}")

    # Load data using the existing C2 loader (handles schema and truth separation)
    try:
        data = c2_load(path, validate=True)
    except ValueError as e:
        raise ValueError(f"Initial schema validation failed: {e}") from e

    # Load associated metadata
    metadata_path = path.parent / "metadata.json"
    if not metadata_path.exists():
        raise FileNotFoundError(f"Associated metadata.json not found in {path.parent}")

    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    # Component 3 specific validations
    _validate_numeric_constraints(data)
    _validate_coordinate_ranges(data)
    _validate_uncertainties(data)
    _validate_time_consistency(data)

    dataset = ObservationDataset(
        data=data,
        frame=data.get("frame", ""),
        time_scale=data.get("time_scale", ""),
        metadata=metadata,
    )
    dataset.validate()  # Validates ordering and final finity

    return dataset


def _validate_numeric_constraints(data: Dict[str, np.ndarray]) -> None:
    """Ensure all numeric arrays contain finite numerical values."""
    for key, arr in data.items():
        if key in ("frame", "time_scale"):
            continue  # scalar string metadata, not numeric arrays
        try:
            arr_float = np.asarray(arr, dtype=float)
        except (ValueError, TypeError):
            raise ValueError(f"Column '{key}' has incompatible type for numeric validation.")
        if not np.isfinite(arr_float).all():
            raise ValueError(f"Column '{key}' contains non-finite values (NaN/Inf).")


def _validate_coordinate_ranges(data: Dict[str, np.ndarray]) -> None:
    """Validate RA [0, 360] and Dec [-90, 90]."""
    ra = data["ra_deg"]
    dec = data["dec_deg"]

    if (ra < 0).any() or (ra > 360).any():
        raise ValueError("RA values found outside range [0, 360] degrees.")

    if (dec < -90).any() or (dec > 90).any():
        raise ValueError("Dec values found outside range [-90, 90] degrees.")


def _validate_uncertainties(data: Dict[str, np.ndarray]) -> None:
    """Ensure all uncertainties are positive."""
    for key in ["sigma_ra_cosdec_arcsec", "sigma_dec_arcsec"]:
        if (data[key] <= 0).any():
            raise ValueError(f"Measurement uncertainty '{key}' must be strictly positive.")


def _validate_time_consistency(data: Dict[str, np.ndarray]) -> None:
    """Check that time_days and time_years are consistent (365.25 d/yr)."""
    days = data["time_days"]
    years = data["time_years"]
    expected_days = years * 365.25
    if not np.allclose(days, expected_days, rtol=0, atol=1e-8):
        raise ValueError("time_days and time_years columns are inconsistent.")
