
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

runs = {
    "original": ROOT / "data/runs/synthetic_asteroid/trajectory.csv",
    "eccentric": ROOT / "data/runs/synthetic_asteroid_eccentric/trajectory.csv",
}

data = {}

for name, path in runs.items():
    if not path.exists():
        raise FileNotFoundError(f"Missing trajectory: {path}")

    df = pd.read_csv(path)

    xyz = df[["x_au", "y_au", "z_au"]].to_numpy()
    radius = np.linalg.norm(xyz, axis=1)

    if not np.isfinite(df.select_dtypes(include="number")).all().all():
        raise ValueError(f"{name}: non-finite numeric values found")

    if not np.all(np.diff(df["time_years"]) > 0):
        raise ValueError(f"{name}: timestamps are not strictly increasing")

    data[name] = df

    print(f"\n{name.upper()}")
    print(f"Samples: {len(df)}")
    print(f"Minimum Sun-relative distance: {radius.min():.4f} AU")
    print(f"Maximum Sun-relative distance: {radius.max():.4f} AU")

original = data["original"]
eccentric = data["eccentric"]

if len(original) != len(eccentric):
    print("\nThe runs have different sample counts.")
else:
    position_a = original[["x_au", "y_au", "z_au"]].to_numpy()
    position_b = eccentric[["x_au", "y_au", "z_au"]].to_numpy()

    max_difference = np.linalg.norm(
        position_a - position_b, axis=1
    ).max()

    print(f"\nMaximum pointwise position difference: {max_difference:.6f} AU")

    if max_difference > 1e-6:
        print("PASS: Changing eccentricity changed the trajectory.")
    else:
        print("FAIL: Trajectories are unexpectedly similar.")
