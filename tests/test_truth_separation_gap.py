"""Verify that tracked observation datasets have no truth columns embedded.

This test confirms the Phase 1 truth-separation implementation: observation
CSVs contain only measurement data (no true_ra_deg / true_dec_deg), while
ground truth resides in a separate ground_truth.json file.

Note: The original tracked data files (pre-Phase-1) contained truth columns in
the observation CSV. These were regenerated using the new C2 generator in
Phase 1. The ground-truth information is preserved in the separate
ground_truth.json files.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]

DATASETS = [
    "synthetic_asteroid_observations",
    "synthetic_asteroid_inclined_observations",
    "synthetic_asteroid_eccentric_observations",
]

TRUTH_COLUMNS = {"true_ra_deg", "true_dec_deg"}


def _check_dataset_columns(dataset: str) -> list[str]:
    """Return a list of truth columns found in the observation CSV, if any."""
    path = ROOT / "data" / "observations" / dataset / "observations.csv"
    if not path.exists():
        return ["file_not_found"]
    columns = set(pd.read_csv(path, nrows=0).columns)
    return sorted(columns & TRUTH_COLUMNS)


@pytest.mark.parametrize("dataset", DATASETS)
def test_observation_csv_has_no_truth_columns(dataset: str) -> None:
    """Observation CSV must not contain true_ra_deg or true_dec_deg.

    After Phase 1 truth separation, the measurement CSV contains only
    observational data. Ground-truth values (true RA/Dec, position, velocity)
    are stored in the separate ground_truth.json file.
    """
    leaked = _check_dataset_columns(dataset)
    assert not leaked, (
        f"Truth columns found in {dataset}/observations.csv: {leaked}"
    )


@pytest.mark.parametrize("dataset", DATASETS)
def test_ground_truth_available_for_dataset(dataset: str) -> None:
    """Ground-truth data must be present in the separate ground_truth.json file.

    The observation CSV deliberately does NOT contain true_* columns;
    they are available in the ground-truth dataset for evaluation purposes.
    """
    path = ROOT / "data" / "observations" / dataset / "ground_truth.json"
    assert path.exists(), (
        f"ground_truth.json not found in {dataset}; "
        "truth separation not properly implemented"
    )
    import json

    with open(path, "r", encoding="utf-8") as f:
        gt = json.load(f)
    # Verify the ground-truth file contains the expected truth fields
    assert isinstance(gt, list), f"ground_truth.json should be a list of records"
    assert len(gt) > 0, f"ground_truth.json should not be empty for {dataset}"
    first = gt[0]
    has_ra = "true_ra_deg" in first
    has_dec = "true_dec_deg" in first
    assert has_ra or has_dec, (
        f"ground_truth.json for {dataset} missing true RA/Dec fields"
    )