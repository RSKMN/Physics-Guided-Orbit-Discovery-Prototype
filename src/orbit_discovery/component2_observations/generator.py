"""Synthetic astronomical observation generator.

Generates noisy RA/Dec observations from an asteroid trajectory, with strict
separation between measurement data (observation CSV) and ground-truth data
(ground_truth JSON).  The observation dataset never contains hidden simulation
truth, enabling truth-free orbit estimation (C3).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from orbit_discovery.component2_observations.loader import load_trajectory
from orbit_discovery.component2_observations.schedule import (
    generate_observation_times,
    interpolate_positions,
)
from orbit_discovery.component2_observations.observer import (
    calculate_observer_positions,
    calculate_relative_positions,
)
from orbit_discovery.component2_observations.frames import (
    ecliptic_to_equatorial,
    calculate_ra_dec,
)
from orbit_discovery.component2_observations.noise import add_measurement_noise


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DAYS_PER_YEAR = 365.25


def load_config(config_path):
    """Load the observation generator JSON configuration."""

    config_path = Path(config_path)

    if not config_path.is_absolute():
        config_path = PROJECT_ROOT / config_path

    if not config_path.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}"
        )

    with open(config_path, "r", encoding="utf-8") as file:
        config = json.load(file)

    return config, config_path


def generate_observations(config_path):
    """Run the complete synthetic observation generation pipeline.

    Returns
    -------
    observations : pandas.DataFrame
        Measurement-only dataset written to ``observations.csv``.  Contains
        ``obs_id``, ``time_years``, ``time_days``, ``ra_deg``, ``dec_deg``,
        ``sigma_ra_cosdec_arcsec``, ``sigma_dec_arcsec``.  **Does not**
        contain ``true_ra_deg`` or ``true_dec_deg``.
    metadata : dict
        Dataset metadata including ground-truth file reference.
    """

    # --------------------------------------------------
    # 1. Load asteroid trajectory
    # --------------------------------------------------

    config, config_file = load_config(config_path)

    input_path = Path(config["input_trajectory"])

    if not input_path.is_absolute():
        input_path = PROJECT_ROOT / input_path

    trajectory = load_trajectory(input_path)

    ground_truth_times = trajectory["time_days"]
    ground_truth_positions = trajectory["positions"]

    # --------------------------------------------------
    # 2. Generate observation schedule
    # --------------------------------------------------

    schedule = config["observation_schedule"]

    observation_times_days = generate_observation_times(
        start_day=schedule["start_day"],
        end_day=schedule["end_day"],
        cadence_days=schedule["cadence_days"],
        available_start_day=ground_truth_times[0],
        available_end_day=ground_truth_times[-1],
    )

    observation_times_years = observation_times_days / DAYS_PER_YEAR

    # --------------------------------------------------
    # 3. Interpolate asteroid positions at observation epochs
    # --------------------------------------------------

    asteroid_positions = interpolate_positions(
        ground_truth_times,
        ground_truth_positions,
        observation_times_days,
    )

    # --------------------------------------------------
    # 4. Calculate observer positions
    # --------------------------------------------------

    observer_config = config["observer"]

    observer_positions = calculate_observer_positions(
        time_years=observation_times_years,
        orbital_radius_au=observer_config["orbital_radius_au"],
        orbital_period_years=observer_config["orbital_period_years"],
        initial_phase_deg=observer_config["initial_phase_deg"],
    )

    # --------------------------------------------------
    # 5. Calculate relative positions (asteroid - observer)
    # --------------------------------------------------

    relative_positions = calculate_relative_positions(
        asteroid_positions,
        observer_positions,
    )

    # --------------------------------------------------
    # 6. Convert ecliptic to equatorial coordinates
    # --------------------------------------------------

    coordinate_config = config["coordinates"]

    equatorial_positions = ecliptic_to_equatorial(
        relative_positions,
        obliquity_deg=coordinate_config["obliquity_deg"],
    )

    true_ra_deg, true_dec_deg = calculate_ra_dec(equatorial_positions)

    # --------------------------------------------------
    # 7. Add measurement noise
    # --------------------------------------------------

    noise_config = config["measurement_noise"]

    (
        noisy_ra_deg,
        noisy_dec_deg,
        ra_noise_arcsec,
        dec_noise_arcsec,
    ) = add_measurement_noise(
        true_ra_deg,
        true_dec_deg,
        sigma_ra_cosdec_arcsec=noise_config["sigma_ra_cosdec_arcsec"],
        sigma_dec_arcsec=noise_config["sigma_dec_arcsec"],
        random_seed=noise_config["random_seed"],
    )

    # --------------------------------------------------
    # 8. Create observation dataset (measurements only, no truth)
    # --------------------------------------------------

    number_of_observations = len(observation_times_days)

    observations = pd.DataFrame({
        "obs_id": np.arange(number_of_observations, dtype=int),
        "time_years": observation_times_years,
        "time_days": observation_times_days,
        "ra_deg": noisy_ra_deg,
        "dec_deg": noisy_dec_deg,
        "sigma_ra_cosdec_arcsec": np.full(
            number_of_observations,
            noise_config["sigma_ra_cosdec_arcsec"],
        ),
        "sigma_dec_arcsec": np.full(
            number_of_observations,
            noise_config["sigma_dec_arcsec"],
        ),
    })

    # Ground-truth information is written to a separate file,
    # never embedded in the observation dataset.
    # This prevents C3 from accessing hidden simulation truth.

    # --------------------------------------------------
    # 9. Save output files
    # --------------------------------------------------

    output_config = config["output"]

    output_directory = Path(output_config["directory"])

    if not output_directory.is_absolute():
        output_directory = PROJECT_ROOT / output_directory

    observation_name = config["observation_name"]

    output_directory = output_directory / observation_name
    output_directory.mkdir(parents=True, exist_ok=True)

    csv_path = output_directory / "observations.csv"

    # Observation CSV contains measurement-only data (no truth columns)
    observations.to_csv(csv_path, index=False)

    # --------------------------------------------------
    # 10. Save ground-truth file (if requested)
    # --------------------------------------------------

    if output_config.get("save_noise_free_coordinates", False):
        # Interpolate asteroid positions at observation times
        # (already computed in step 3 as asteroid_positions)
        ground_truth_positions = asteroid_positions

        # Interpolate asteroid velocities at observation times
        # using np.interp on the trajectory time base
        vx_interp = np.interp(
            observation_times_days,
            ground_truth_times,
            trajectory["velocities"][:, 0],
        )
        vy_interp = np.interp(
            observation_times_days,
            ground_truth_times,
            trajectory["velocities"][:, 1],
        )
        vz_interp = np.interp(
            observation_times_days,
            ground_truth_times,
            trajectory["velocities"][:, 2],
        )
        ground_truth_velocities = np.column_stack([vx_interp, vy_interp, vz_interp])

        # Write true coordinates to a separate ground-truth file
        ground_truth = pd.DataFrame({
            "obs_id": np.arange(number_of_observations, dtype=int),
            "true_ra_deg": true_ra_deg,
            "true_dec_deg": true_dec_deg,
            "x_au": ground_truth_positions[:, 0],
            "y_au": ground_truth_positions[:, 1],
            "z_au": ground_truth_positions[:, 2],
            "vx_au_per_year": ground_truth_velocities[:, 0],
            "vy_au_per_year": ground_truth_velocities[:, 1],
            "vz_au_per_year": ground_truth_velocities[:, 2],
        })

        ground_truth_path = output_directory / "ground_truth.json"
        # Save as JSON for structured data with explicit schema
        ground_truth_dict = ground_truth.to_dict(orient="records")
        with open(ground_truth_path, "w", encoding="utf-8") as gf:
            json.dump(ground_truth_dict, gf, indent=4)

        # Also store metadata about the ground-truth file
        ground_truth_metadata = {
            "ground_truth_file": "ground_truth.json",
            "number_of_observations": number_of_observations,
            "true_ra_deg": True,
            "true_dec_deg": True,
            "includes_positions": True,
            "includes_velocities": True,
        }
    else:
        ground_truth_metadata = {
            "ground_truth_file": None,
            "number_of_observations": number_of_observations,
            "includes_positions": False,
            "includes_velocities": False,
        }

    # --------------------------------------------------
    # 11. Build metadata dictionary
    # --------------------------------------------------

    metadata = {
        "observation_name": observation_name,
        "input_trajectory": str(input_path.relative_to(PROJECT_ROOT))
            if input_path.is_relative_to(PROJECT_ROOT)
            else str(input_path),
        "configuration_file": str(config_file.relative_to(PROJECT_ROOT))
            if config_file.is_relative_to(PROJECT_ROOT)
            else str(config_file),
        "state_type": "synthetic_observations",
        "number_of_observations": number_of_observations,
        "observation_schedule": schedule,
        "observer": observer_config,
        "coordinates": coordinate_config,
        "measurement_noise": noise_config,
        "coordinate_units": {
            "time": "days and years",
            "right_ascension": "degrees",
            "declination": "degrees",
            "angular_uncertainty": "arcseconds",
            "distance": "AU",
        },
        "assumptions": [
            "Idealized circular Earth-like observer orbit",
            "Observer orbit lies in the heliocentric ecliptic plane",
            "Asteroid positions are interpolated from simulated ground truth",
            "Ecliptic coordinates are rotated using the configured obliquity",
            "Gaussian angular measurement noise is applied",
            "Observation times are elapsed simulation times, not real calendar dates",
            "Ground truth is stored separately in ground_truth.json; ",
            "observation CSV contains measurements only.",
        ],
        "output_file": "observations.csv",
        # Ground-truth metadata
        "ground_truth": ground_truth_metadata,
    }

    if output_config["save_metadata"]:
        metadata_path = output_directory / "metadata.json"

        with open(metadata_path, "w", encoding="utf-8") as file:
            json.dump(metadata, file, indent=4)

    # --------------------------------------------------
    # 12. Print summary
    # --------------------------------------------------

    print("\nSynthetic observation generation successful.")
    print(f"Observation name: {observation_name}")
    print(f"Number of observations: {number_of_observations}")

    print(
        f"Observation period: "
        f"{observation_times_days[0]:.2f} to "
        f"{observation_times_days[-1]:.2f} days"
    )

    print(f"\nOutput directory: {output_directory}")
    print(f"CSV file: {csv_path}")

    if output_config["save_metadata"]:
        print(f"Metadata file: {output_directory / 'metadata.json'}")

    print("\nFirst observation:")
    print(observations.iloc[0].to_string())

    return observations, metadata


def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic astronomical observations."
    )

    parser.add_argument(
        "--config",
        default="configs/synthetic_observations.json",
        help="Path to observation configuration JSON.",
    )

    args = parser.parse_args()

    generate_observations(args.config)


if __name__ == "__main__":
    main()