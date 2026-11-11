
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

TRAJECTORY_FILES = [
    ROOT / "data/runs/synthetic_asteroid/trajectory.csv",
    ROOT / "data/runs/synthetic_asteroid_eccentric/trajectory.csv",
]

REQUIRED_COLUMNS = [
    "time_years",
    "time_days",
    "x_au",
    "y_au",
    "z_au",
    "vx_au_per_year",
    "vy_au_per_year",
    "vz_au_per_year",
]


def validate_trajectory(path):
    print(f"\nValidating: {path.parent.name}")

    df = pd.read_csv(path)

    missing = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    values = df[REQUIRED_COLUMNS].to_numpy(dtype=float)

    if not np.isfinite(values).all():
        raise ValueError("Trajectory contains NaN or infinite values.")

    if not np.all(np.diff(df["time_years"]) > 0):
        raise ValueError("Time values are not strictly increasing.")

    if not np.allclose(
        df["time_days"],
        df["time_years"] * 365.25,
        rtol=0,
        atol=1e-8,
    ):
        raise ValueError("Time columns are inconsistent.")

    print("PASS: required columns present")
    print("PASS: all values finite")
    print("PASS: timestamps strictly increasing")
    print("PASS: time columns consistent")
    print(f"Samples: {len(df)}")
    print(f"Duration: {df['time_years'].iloc[-1]:.6f} years")


for file_path in TRAJECTORY_FILES:
    validate_trajectory(file_path)

print("\nGround-truth validation completed.")
