
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


def main():

    # Load ground truth
    trajectory = load_trajectory(
        "data/runs/synthetic_asteroid/trajectory.csv"
    )

    # Generate observation epochs
    observation_times_days = generate_observation_times(
        start_day=0.0,
        end_day=1826.25,
        cadence_days=7.0,
        available_start_day=trajectory["time_days"][0],
        available_end_day=trajectory["time_days"][-1]
    )

    observation_times_years = observation_times_days / 365.25

    # Interpolate asteroid positions
    asteroid_positions = interpolate_positions(
        trajectory["time_days"],
        trajectory["positions"],
        observation_times_days
    )

    # Calculate observer positions
    observer_positions = calculate_observer_positions(
        observation_times_years,
        initial_phase_deg=90.0
    )

    # Calculate relative positions
    relative_positions = calculate_relative_positions(
        asteroid_positions,
        observer_positions
    )

    # Convert coordinate frame
    equatorial_positions = ecliptic_to_equatorial(
        relative_positions,
        obliquity_deg=23.43928
    )

    # Calculate RA and Dec
    ra_deg, dec_deg = calculate_ra_dec(
        equatorial_positions
    )

    # Validation
    assert len(ra_deg) == 262
    assert len(dec_deg) == 262

    assert np.all((ra_deg >= 0) & (ra_deg < 360))
    assert np.all((dec_deg >= -90) & (dec_deg <= 90))

    assert np.isfinite(ra_deg).all()
    assert np.isfinite(dec_deg).all()

    print("\nCoordinate conversion successful.")

    print("Number of coordinates:", len(ra_deg))

    print("\nFirst observation:")
    print("RA:", ra_deg[0], "degrees")
    print("Dec:", dec_deg[0], "degrees")

    print("\nLast observation:")
    print("RA:", ra_deg[-1], "degrees")
    print("Dec:", dec_deg[-1], "degrees")

    print("\nRA range:")
    print(np.min(ra_deg), "to", np.max(ra_deg))

    print("\nDec range:")
    print(np.min(dec_deg), "to", np.max(dec_deg))


if __name__ == "__main__":
    main()
