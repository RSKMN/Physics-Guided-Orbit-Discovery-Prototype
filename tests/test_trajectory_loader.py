
import sys
from pathlib import Path

# Add the project root to Python's module search path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.trajectory_loader import load_trajectory


def main():
    trajectory = load_trajectory(
        "data/runs/synthetic_asteroid/trajectory.csv"
    )

    print("\nValidation results:")
    print("Position array shape:", trajectory["positions"].shape)
    print("Velocity array shape:", trajectory["velocities"].shape)

    print("\nFirst asteroid position:")
    print(trajectory["positions"][0])

    print("\nLast asteroid position:")
    print(trajectory["positions"][-1])


if __name__ == "__main__":
    main()
