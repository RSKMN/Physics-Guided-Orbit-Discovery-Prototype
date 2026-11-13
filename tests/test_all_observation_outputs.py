"""Read-only validation of the three Component 2 observation datasets.

Updated for Phase 1: truth separation. Observation CSVs contain only
measurement data (no true_ra_deg / true_dec_deg). Ground-truth information
is stored in separate ground_truth.json files.

Importing this module performs no work. The validation runs only when pytest
calls the test function or the module is executed as a script.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from orbit_discovery.component2_observations.schema import (
    validate_observation_schema,
    V2_FORBIDDEN,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

DATASET_NAMES = [
    "synthetic_asteroid_observations",
    "synthetic_asteroid_inclined_observations",
    "synthetic_asteroid_eccentric_observations",
]


def validate_dataset(dataset_name: str) -> dict:
    """Validate one tracked observation dataset and return summary statistics.

    Phase 1 v2.0 contract:
    - observation CSV contains measurement-only data (no ground-truth).
    - ground_truth.json contains true coordinates and simulation state.
    """

    output_dir = PROJECT_ROOT / "data" / "observations" / dataset_name
    csv_path = output_dir / "observations.csv"
    metadata_path = output_dir / "metadata.json"
    ground_truth_path = output_dir / "ground_truth.json"

    # 1. Check output files exist
    assert csv_path.exists(), f"{dataset_name}: CSV not found."
    assert metadata_path.exists(), f"{dataset_name}: Metadata not found."
    assert ground_truth_path.exists(), (
        f"{dataset_name}: ground_truth.json not found. "
        "Truth separation not properly implemented."
    )

    observations = pd.read_csv(csv_path)

    with open(metadata_path, "r", encoding="utf-8") as file:
        metadata = json.load(file)

    # 2. Validate observation schema (forbidden columns check + required columns)
    errors = validate_observation_schema(observations)
    if errors:
        raise AssertionError(
            f"{dataset_name}: Schema validation errors: " + "; ".join(errors)
        )

    # 3. Check observation count
    assert len(observations) == metadata["number_of_observations"]
    assert len(observations) == 262

    # 4. Check required measurement columns are present (v2 schema required)
    required_measurement = {
        "time_years",
        "time_days",
        "ra_deg",
        "dec_deg",
        "sigma_ra_cosdec_arcsec",
        "sigma_dec_arcsec",
    }
    missing = required_measurement - set(observations.columns)
    assert not missing, f"{dataset_name}: Missing required measurement columns: {missing}"

    # 5. Check that forbidden (truth-revealing) columns are NOT present
    found_forbidden = set(observations.columns) & V2_FORBIDDEN
    assert not found_forbidden, (
        f"{dataset_name}: Forbidden truth columns present in observation CSV: "
        + str(sorted(found_forbidden))
    )

    # 6. Check no nulls in required measurement columns
    for col in required_measurement:
        assert observations[col].notna().all(), (
            f"{dataset_name}: Column '{col}' contains null values"
        )

    # 7. Check timestamps
    assert observations["time_days"].is_monotonic_increasing
    assert observations["time_days"].is_unique
    assert np.allclose(
        observations["time_days"],
        observations["time_years"] * 365.25,
    )
    assert np.isclose(observations["time_days"].iloc[0], 0.0)
    assert np.isclose(observations["time_days"].iloc[-1], 1826.25)

    # 8. Check angular coordinate ranges (measurement only, no truth)
    assert observations["ra_deg"].between(0, 360).all()
    assert observations["dec_deg"].between(-90, 90).all()

    # 9. Check configured uncertainties
    noise_config = metadata["measurement_noise"]
    expected_ra_sigma = noise_config["sigma_ra_cosdec_arcsec"]
    expected_dec_sigma = noise_config["sigma_dec_arcsec"]

    assert np.allclose(
        observations["sigma_ra_cosdec_arcsec"],
        expected_ra_sigma,
    )
    assert np.allclose(
        observations["sigma_dec_arcsec"],
        expected_dec_sigma,
    )

    # 10. Validate ground-truth file exists and contains expected fields
    with open(ground_truth_path, "r", encoding="utf-8") as f:
        ground_truth = json.load(f)

    assert isinstance(ground_truth, list), f"{dataset_name}: ground_truth.json should be a list"
    assert len(ground_truth) > 0, f"{dataset_name}: ground_truth.json should not be empty"
    assert len(ground_truth) == len(observations), (
        f"{dataset_name}: ground_truth.json has {len(ground_truth)} records "
        f"but observation CSV has {len(observations)}"
    )

    first = ground_truth[0]
    assert "true_ra_deg" in first, f"{dataset_name}: ground_truth missing true_ra_deg"
    assert "true_dec_deg" in first, f"{dataset_name}: ground_truth missing true_dec_deg"
    assert "x_au" in first, f"{dataset_name}: ground_truth missing x_au position"
    assert "y_au" in first, f"{dataset_name}: ground_truth missing y_au position"
    assert "z_au" in first, f"{dataset_name}: ground_truth missing z_au position"

    # 11. Check angular noise residuals (using ground truth for evaluation)
    with open(ground_truth_path, "r", encoding="utf-8") as f:
        ground_truth = json.load(f)
    gt_lookup = {rec["obs_id"]: rec for rec in ground_truth}

    ra_residuals_arcsec = []
    dec_residuals_arcsec = []
    for _, obs_row in observations.iterrows():
        oid = int(obs_row["obs_id"])
        if oid in gt_lookup:
            gt = gt_lookup[oid]
            ra_diff_deg = (obs_row["ra_deg"] - gt["true_ra_deg"] + 180) % 360 - 180
            ra_residual_arcsec = ra_diff_deg * np.cos(np.deg2rad(gt["true_dec_deg"])) * 3600
            dec_residual_arcsec = (obs_row["dec_deg"] - gt["true_dec_deg"]) * 3600
            ra_residuals_arcsec.append(ra_residual_arcsec)
            dec_residuals_arcsec.append(dec_residual_arcsec)

    if ra_residuals_arcsec:
        ra_mean = np.mean(ra_residuals_arcsec)
        dec_mean = np.mean(dec_residuals_arcsec)
        ra_std = np.std(ra_residuals_arcsec, ddof=1)
        dec_std = np.std(dec_residuals_arcsec, ddof=1)
    else:
        ra_mean = dec_mean = ra_std = dec_std = 0.0

    expected_ra_sigma = noise_config["sigma_ra_cosdec_arcsec"]
    expected_dec_sigma = noise_config["sigma_dec_arcsec"]

    assert abs(ra_mean) < 0.15, (
        f"{dataset_name}: RA mean residual {ra_mean:.4f} arcsec > 0.15"
    )
    assert abs(dec_mean) < 0.15, (
        f"{dataset_name}: Dec mean residual {dec_mean:.4f} arcsec > 0.15"
    )
    assert abs(ra_std - expected_ra_sigma) < 0.15, (
        f"{dataset_name}: RA std {ra_std:.4f} != expected {expected_ra_sigma:.4f}"
    )
    assert abs(dec_std - expected_dec_sigma) < 0.15, (
        f"{dataset_name}: Dec std {dec_std:.4f} != expected {expected_dec_sigma:.4f}"
    )

    # 12. Return validation statistics
    return {
        "dataset": dataset_name,
        "observations": len(observations),
        "ra_min": observations["ra_deg"].min(),
        "ra_max": observations["ra_deg"].max(),
        "dec_min": observations["dec_deg"].min(),
        "dec_max": observations["dec_deg"].max(),
        "ra_noise_mean": ra_mean,
        "ra_noise_std": ra_std,
        "dec_noise_mean": dec_mean,
        "dec_noise_std": dec_std,
    }


@pytest.mark.parametrize("dataset_name", DATASET_NAMES)
def test_observation_dataset(dataset_name: str) -> None:
    """Every tracked observation dataset must satisfy the Phase 1 v2.0 contract.

    The v2.0 observation schema separates measurements from ground truth:
    - observation CSV: measurement data only (no true_* columns).
    - ground_truth.json: true coordinates, positions, velocities for evaluation.
    """

    result = validate_dataset(dataset_name)
    print(f"\nValidated {dataset_name}: {result['observations']} observations")


def main() -> int:
    print("\nCOMPONENT 2: OBSERVATION DATASET VALIDATION (Phase 1 v2.0)")
    print("=" * 60)

    for dataset_name in DATASET_NAMES:
        print(f"\nValidating: {dataset_name}")
        result = validate_dataset(dataset_name)
        print("Validation PASSED")
        print(f"Observations: {result['observations']}")
        print(
            f"RA range: {result['ra_min']:.4f} to {result['ra_max']:.4f} degrees"
        )
        print(
            f"Dec range: {result['dec_min']:.4f} to {result['dec_max']:.4f} degrees"
        )
        print(f"RA noise std: {result['ra_noise_std']:.4f} arcsec")
        print(f"Dec noise std: {result['dec_noise_std']:.4f} arcsec")

    print("\n" + "=" * 60)
    print("ALL THREE DATASETS VALIDATED SUCCESSFULLY (Phase 1)")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())