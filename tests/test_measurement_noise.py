
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.trajectory_loader import load_trajectory
from src.observation_schedule import (
    generate_observation_times,
    interpolate_positions
)
from src.observer_model import (
    calculate_observer_positions,
    calculate_relative_positions
)
from src.coordinate_converter import (
    ecliptic_to_equatorial,
    calculate_ra_dec
)
from src.measurement_noise import add_measurement_noise


def main():

    trajectory = load_trajectory(
        "data/runs/synthetic_asteroid/trajectory.csv"
    )

    observation_times_days = generate_observation_times(
        start_day=0.0,
        end_day=1826.25,
        cadence_days=7.0,
        available_start_day=trajectory["time_days"][0],
        available_end_day=trajectory["time_days"][-1]
    )

    observation_times_years = observation_times_days / 365.25

    asteroid_positions = interpolate_positions(
        trajectory["time_days"],
        trajectory["positions"],
        observation_times_days
    )

    observer_positions = calculate_observer_positions(
        observation_times_years,
        initial_phase_deg=90.0
    )

    relative_positions = calculate_relative_positions(
        asteroid_positions,
        observer_positions
    )

    equatorial_positions = ecliptic_to_equatorial(
        relative_positions
    )

    true_ra, true_dec = calculate_ra_dec(
        equatorial_positions
    )

    noisy_ra, noisy_dec, ra_noise, dec_noise = (
        add_measurement_noise(
            true_ra,
            true_dec,
            sigma_ra_cosdec_arcsec=0.5,
            sigma_dec_arcsec=0.5,
            random_seed=42
        )
    )

    # Validate output
    assert len(noisy_ra) == 262
    assert len(noisy_dec) == 262

    assert np.all((noisy_ra >= 0) & (noisy_ra < 360))
    assert np.all((noisy_dec >= -90) & (noisy_dec <= 90))

    assert np.isfinite(noisy_ra).all()
    assert np.isfinite(noisy_dec).all()

    # Reproducibility check
    repeated = add_measurement_noise(
        true_ra,
        true_dec,
        sigma_ra_cosdec_arcsec=0.5,
        sigma_dec_arcsec=0.5,
        random_seed=42
    )

    assert np.allclose(noisy_ra, repeated[0])
    assert np.allclose(noisy_dec, repeated[1])

    print("\nMeasurement noise validation successful.")

    print("Number of observations:", len(noisy_ra))

    print("\nFirst observation:")
    print("True RA:", true_ra[0])
    print("Noisy RA:", noisy_ra[0])
    print("True Dec:", true_dec[0])
    print("Noisy Dec:", noisy_dec[0])

    print("\nNoise statistics (arcseconds):")
    print("RA mean:", np.mean(ra_noise))
    print("RA standard deviation:", np.std(ra_noise))
    print("Dec mean:", np.mean(dec_noise))
    print("Dec standard deviation:", np.std(dec_noise))

    print("\nReproducibility check: PASSED")


if __name__ == "__main__":
    main()
