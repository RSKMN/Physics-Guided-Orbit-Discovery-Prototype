
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.trajectory_loader import load_trajectory
from src.observation_schedule import (
    generate_observation_times,
    interpolate_positions
)


def main():

    # Load ground-truth trajectory
    trajectory = load_trajectory(
        "data/runs/synthetic_asteroid/trajectory.csv"
    )

    # Generate observation timestamps
    observation_times = generate_observation_times(
        start_day=0.0,
        end_day=1826.25,
        cadence_days=7.0,
        available_start_day=trajectory["time_days"][0],
        available_end_day=trajectory["time_days"][-1]
    )

    # Interpolate positions
    interpolated_positions = interpolate_positions(
        ground_truth_times_days=trajectory["time_days"],
        ground_truth_positions=trajectory["positions"],
        observation_times_days=observation_times
    )

    print("\nObservation scheduling results:")
    print("Number of observations:", len(observation_times))
    print("First observation day:", observation_times[0])
    print("Last observation day:", observation_times[-1])

    print("\nInterpolated position array shape:")
    print(interpolated_positions.shape)

    print("\nFirst interpolated position:")
    print(interpolated_positions[0])

    print("\nLast interpolated position:")
    print(interpolated_positions[-1])


if __name__ == "__main__":
    main()
