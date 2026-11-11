
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


def main():

    # Load asteroid ground truth
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

    # Convert days to elapsed years
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
        orbital_radius_au=1.0,
        orbital_period_years=1.0,
        initial_phase_deg=90.0
    )

    # Calculate asteroid-observer vectors
    relative_positions = calculate_relative_positions(
        asteroid_positions,
        observer_positions
    )

    # Verify initial observer position
    expected_initial_position = np.array([0.0, 1.0, 0.0])

    assert np.allclose(
        observer_positions[0],
        expected_initial_position,
        atol=1e-10
    )

    # Verify all arrays have matching dimensions
    assert asteroid_positions.shape == observer_positions.shape
    assert relative_positions.shape == observer_positions.shape

    print("\nObserver model validation successful.")

    print("Number of observation epochs:", len(observation_times_days))

    print("\nInitial observer position (AU):")
    print(observer_positions[0])

    print("\nInitial asteroid position (AU):")
    print(asteroid_positions[0])

    print("\nInitial asteroid-observer vector (AU):")
    print(relative_positions[0])

    print("\nObserver position array shape:")
    print(observer_positions.shape)

    print("\nRelative position array shape:")
    print(relative_positions.shape)

    print("\nInitial observer distance from Sun (AU):")
    print(np.linalg.norm(observer_positions[0]))


if __name__ == "__main__":
    main()
