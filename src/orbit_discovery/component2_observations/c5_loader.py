"""C5-facing evaluation-only ground-truth loader.

Provides explicit access to ground-truth datasets for evaluation purposes
only. This interface must NOT be imported or used by Component 3 (orbit
estimation). It is designated for C5 evaluation functionality only.

The design enforces the truth-separation boundary established in Phase 1:
- Ground truth is stored in a separate ``ground_truth.json`` file.
- This loader only reads the ground-truth dataset.
- It must not be imported by the C3-facing observation loader.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import json
import numpy as np
import pandas as pd

from orbit_discovery.core.constants import DAYS_PER_YEAR


def load_ground_truth_dataset(
    ground_truth_path: Path | str,
    *,
    validate: bool = True,
) -> dict[str, Any]:
    """Load a ground-truth dataset from a JSON file.

    Parameters
    ----------
    ground_truth_path : Path or str
        Path to the ground-truth JSON file (``ground_truth.json``).
    validate : bool, optional
        Whether to validate the dataset structure.
        Defaults to ``True``.

    Returns
    -------
    dict
        A dictionary with the following keys:

        - ``"obs_id"``: ``np.ndarray[int]`` - observation identifiers.
        - ``"true_ra_deg"``: ``np.ndarray[float]`` - true right ascension in degrees.
        - ``"true_dec_deg"``: ``np.ndarray[float]`` - true declination in degrees.
        - ``"x_au"``: ``np.ndarray[float]`` - true Cartesian position in AU.
        - ``"y_au"``: ``np.ndarray[float]`` - true Cartesian position in AU.
        - ``"z_au"``: ``np.ndarray[float]`` - true Cartesian position in AU.
        - ``"vx_au_per_year"``: ``np.ndarray[float]`` - true velocity in AU/yr.
        - ``"vy_au_per_year"``: ``np.ndarray[float]`` - true velocity in AU/yr.
        - ``"vz_au_per_year"``: ``np.ndarray[float]`` - true velocity in AU/yr.
        - ``"epoch_jd_tdb"``: ``float``, optional - Julian Date in TDB.

    Raises
    ------
    FileNotFoundError
        If ``ground_truth_path`` does not exist.
    ValueError
        If the ground-truth file has an invalid structure.
    """
    path = Path(ground_truth_path)

    if not path.exists():
        raise FileNotFoundError(f"Ground-truth file not found: {path}")

    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(
            f"Ground-truth data should be a list of records, got {type(data).__name__}"
        )

    number_of_records = len(data)
    if number_of_records == 0:
        raise ValueError("Ground-truth file is empty.")

    # Convert to DataFrame for easy column access
    df = pd.DataFrame(data)
    result: dict[str, Any] = {}

    # Required ground-truth columns
    required_gt = {
        "obs_id",
        "true_ra_deg",
        "true_dec_deg",
        "x_au",
        "y_au",
        "z_au",
        "vx_au_per_year",
        "vy_au_per_year",
        "vz_au_per_year",
    }

    missing = required_gt - set(df.columns)
    if missing:
        raise ValueError(
            f"Ground-truth file missing required columns: {sorted(missing)}"
        )

    # Extract columns as numpy arrays
    for col in required_gt:
        result[col] = df[col].to_numpy().astype(float)

    # Optional columns
    if "epoch_jd_tdb" in df.columns:
        result["epoch_jd_tdb"] = df["epoch_jd_tdb"].to_numpy().astype(float)

    # Validation: check that no observation ID is duplicated
    obs_ids = result["obs_id"]
    if len(obs_ids) != len(set(obs_ids)):
        raise ValueError("Ground-truth file contains duplicate observation IDs.")

    return result


def load_ground_truth_csv(csv_path: Path | str) -> pd.DataFrame:
    """Load a ground-truth CSV (if stored in CSV format) into a pandas DataFrame.

    This is a lower-level helper for code that already guarantees data
    compliance and just needs the raw DataFrame.

    Parameters
    ----------
    csv_path : Path or str
        Path to the ground-truth CSV file.

    Returns
    -------
    pandas.DataFrame
        The ground-truth data.
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Ground-truth file not found: {path}")
    return pd.read_csv(path)


#: Re-export for convenience
ValidationError = ValueError


if __name__ == "__main__":
    # Simple CLI test
    import sys
    from pathlib import Path

    if len(sys.argv) < 2:
        print("Usage: python -m orbit_discovery.component2_observations.c5_loader <ground_truth_json_path>")
        sys.exit(1)

    gt_path = sys.argv[1]
    try:
        data = load_ground_truth_dataset(gt_path)
        print(f"\nLoaded ground-truth dataset from: {gt_path}")
        print(f"Number of records: {len(data['obs_id'])}")
        print(f"Columns: {list(data.keys())}")
        print(f"First obs true RA: {data['true_ra_deg'][0]:.4f} deg")
        print(f"First obs true Dec: {data['true_dec_deg'][0]:.4f} deg")
        print(f"First obs position x_au: {data['x_au'][0]:.4f} AU")
        print(f"First obs velocity vx_au_per_year: {data['vx_au_per_year'][0]:.4f} AU/yr")
    except Exception as e:
        print(f"\nError: {e}")
        print("\nExpected columns in ground_truth.json:")
        print("  obs_id, true_ra_deg, true_dec_deg, x_au, y_au, z_au")
        print("  vx_au_per_year, vy_au_per_year, vz_au_per_year")
        print("  (plus optional: epoch_jd_tdb)")
