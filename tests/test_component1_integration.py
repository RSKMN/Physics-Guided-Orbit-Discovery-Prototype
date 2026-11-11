
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

CONFIGS = [
    ROOT / "configs" / "synthetic_asteroid.json",
    ROOT / "configs" / "synthetic_asteroid_eccentric.json",
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


def test_configuration(config_path):
    with config_path.open(encoding="utf-8") as file:
        config = json.load(file)

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "src" / "configurable_simulator.py"),
            str(config_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, (
        f"Simulation failed for {config_path.name}\n"
        f"{result.stdout}\n{result.stderr}"
    )

    output_dir = ROOT / config["output"]["directory"]

    for filename in [
        "trajectory.csv",
        "config.json",
        "metadata.json",
    ]:
        assert (output_dir / filename).exists(), f"Missing {filename}"

    trajectory = pd.read_csv(output_dir / "trajectory.csv")

    assert all(column in trajectory.columns for column in REQUIRED_COLUMNS)
    assert len(trajectory) > 1
    assert np.isfinite(trajectory[REQUIRED_COLUMNS].to_numpy()).all()
    assert np.all(np.diff(trajectory["time_years"]) > 0)

    metadata = json.loads(
        (output_dir / "metadata.json").read_text(encoding="utf-8")
    )
    assert metadata["state_type"] == "simulated_ground_truth"

    if config["output"].get("save_plot", False):
        assert (output_dir / "trajectory_xy.png").exists()
        assert (output_dir / "trajectory_3d.png").exists()

    print(f"PASS: {config_path.name}")


def main():
    for config_path in CONFIGS:
        test_configuration(config_path)

    print("Component 1 integration test: PASS")


if __name__ == "__main__":
    main()
