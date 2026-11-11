
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "observations"
    / "synthetic_asteroid_observations"
)

CSV_PATH = OUTPUT_DIR / "observations.csv"
METADATA_PATH = OUTPUT_DIR / "metadata.json"


def validate_observation_output():

    # 1. Check that output files exist
    assert CSV_PATH.exists(), "Observations CSV not found."
    assert METADATA_PATH.exists(), "Metadata JSON not found."

    observations = pd.read_csv(CSV_PATH)

    with open(METADATA_PATH, "r", encoding="utf-8") as file:
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
            f"Missing column: {column}"
        )

    # 3. Check sample count
    assert len(observations) == metadata["number_of_observations"]

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

    # 7. Check configured uncertainty values
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
    # Wrap RA differences to handle the 0/360 degree boundary.
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

    # Allow reasonable variation for a finite random sample.
    assert abs(ra_mean) < 0.15
    assert abs(dec_mean) < 0.15

    assert abs(ra_std - expected_ra_sigma) < 0.15
    assert abs(dec_std - expected_dec_sigma) < 0.15

    # 9. Print validation summary
    print("\nObservation output validation PASSED.")

    print(f"Number of observations: {len(observations)}")
    print(
        f"Observation period: "
        f"{observations['time_days'].iloc[0]:.2f} to "
        f"{observations['time_days'].iloc[-1]:.2f} days"
    )

    print("\nCoordinate ranges:")
    print(
        f"RA: {observations['ra_deg'].min():.4f} to "
        f"{observations['ra_deg'].max():.4f} degrees"
    )
    print(
        f"Dec: {observations['dec_deg'].min():.4f} to "
        f"{observations['dec_deg'].max():.4f} degrees"
    )

    print("\nRecovered noise statistics (arcseconds):")
    print(f"RA mean: {ra_mean:.4f}")
    print(f"RA standard deviation: {ra_std:.4f}")
    print(f"Dec mean: {dec_mean:.4f}")
    print(f"Dec standard deviation: {dec_std:.4f}")

    print("\nAll dataset validation checks passed.")


if __name__ == "__main__":
    validate_observation_output()
