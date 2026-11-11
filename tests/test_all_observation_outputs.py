
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

DATASET_NAMES = [
    "synthetic_asteroid_observations",
    "synthetic_asteroid_inclined_observations",
    "synthetic_asteroid_eccentric_observations",
]


def validate_dataset(dataset_name):

    output_dir = (
        PROJECT_ROOT
        / "data"
        / "observations"
        / dataset_name
    )

    csv_path = output_dir / "observations.csv"
    metadata_path = output_dir / "metadata.json"

    # 1. Check output files
    assert csv_path.exists(), f"{dataset_name}: CSV not found."
    assert metadata_path.exists(), f"{dataset_name}: Metadata not found."

    observations = pd.read_csv(csv_path)

    with open(metadata_path, "r", encoding="utf-8") as file:
        metadata = json.load(file)

    # 2. Check required columns
    required_columns = [
        "time_years",
        "time_days",
        "ra_deg",
        "dec_deg",
        "sigma_ra_cosdec_arcsec",
        "sigma_dec_arcsec",
        "true_ra_deg",
        "true_dec_deg",
    ]

    for column in required_columns:
        assert column in observations.columns, (
            f"{dataset_name}: Missing column {column}"
        )

    # 3. Check observation count
    assert len(observations) == metadata["number_of_observations"]
    assert len(observations) == 262

    # 4. Check missing and invalid values
    assert not observations[required_columns].isnull().any().any()

    assert np.isfinite(
        observations[required_columns].to_numpy(dtype=float)
    ).all()

    # 5. Check timestamps
    assert observations["time_days"].is_monotonic_increasing
    assert observations["time_days"].is_unique

    assert np.allclose(
        observations["time_days"],
        observations["time_years"] * 365.25,
    )

    assert np.isclose(observations["time_days"].iloc[0], 0.0)
    assert np.isclose(observations["time_days"].iloc[-1], 1826.25)

    # 6. Check angular coordinate ranges
    assert observations["ra_deg"].between(0, 360).all()
    assert observations["true_ra_deg"].between(0, 360).all()

    assert observations["dec_deg"].between(-90, 90).all()
    assert observations["true_dec_deg"].between(-90, 90).all()

    # 7. Check configured uncertainties
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

    # 8. Calculate angular noise residuals
    ra_difference_deg = (
        observations["ra_deg"] - observations["true_ra_deg"] + 180
    ) % 360 - 180

    ra_residual_arcsec = (
        ra_difference_deg
        * np.cos(np.deg2rad(observations["true_dec_deg"]))
        * 3600
    )

    dec_residual_arcsec = (
        observations["dec_deg"] - observations["true_dec_deg"]
    ) * 3600

    ra_mean = np.mean(ra_residual_arcsec)
    dec_mean = np.mean(dec_residual_arcsec)

    ra_std = np.std(ra_residual_arcsec, ddof=1)
    dec_std = np.std(dec_residual_arcsec, ddof=1)

    assert abs(ra_mean) < 0.15
    assert abs(dec_mean) < 0.15

    assert abs(ra_std - expected_ra_sigma) < 0.15
    assert abs(dec_std - expected_dec_sigma) < 0.15

    # 9. Return validation statistics
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


if __name__ == "__main__":

    print("\nCOMPONENT 2: OBSERVATION DATASET VALIDATION")
    print("=" * 55)

    results = []

    for dataset_name in DATASET_NAMES:

        print(f"\nValidating: {dataset_name}")

        result = validate_dataset(dataset_name)
        results.append(result)

        print("Validation PASSED")
        print(f"Observations: {result['observations']}")
        print(
            f"RA range: {result['ra_min']:.4f} "
            f"to {result['ra_max']:.4f} degrees"
        )
        print(
            f"Dec range: {result['dec_min']:.4f} "
            f"to {result['dec_max']:.4f} degrees"
        )
        print(
            f"RA noise std: {result['ra_noise_std']:.4f} arcsec"
        )
        print(
            f"Dec noise std: {result['dec_noise_std']:.4f} arcsec"
        )

    print("\n" + "=" * 55)
    print("ALL THREE DATASETS VALIDATED SUCCESSFULLY")
    print("=" * 55)
