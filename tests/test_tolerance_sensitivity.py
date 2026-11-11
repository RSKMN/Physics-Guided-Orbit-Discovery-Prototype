
from pathlib import Path
import json
import subprocess
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SIMULATOR = ROOT / "src" / "configurable_simulator.py"
BASE_CONFIG = ROOT / "configs" / "synthetic_asteroid.json"

TEST_DIR = ROOT / "configs" / "tolerance_temp"
TEST_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_BASE = ROOT / "data" / "tolerance_tests"
OUTPUT_BASE.mkdir(parents=True, exist_ok=True)

with BASE_CONFIG.open("r", encoding="utf-8") as f:
    base = json.load(f)

configs = {
    "eps_1e9": 1e-9,
    "eps_1e12": 1e-12,
    "eps_1e13": 1e-13,
}

results = {}

try:
    for name, epsilon in configs.items():
        config = json.loads(json.dumps(base))
        config["simulation"]["integrator_epsilon"] = epsilon
        config["output"]["directory"] = str(
            (OUTPUT_BASE / name).relative_to(ROOT)
        )
        config_path = TEST_DIR / f"{name}.json"

        with config_path.open("w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)

        subprocess.run(
            [sys.executable, str(SIMULATOR), str(config_path)],
            cwd=ROOT,
            check=True,
        )

        results[name] = pd.read_csv(
            OUTPUT_BASE / name / "trajectory.csv"
        )

    columns = [
        "x_au", "y_au", "z_au",
        "vx_au_per_year",
        "vy_au_per_year",
        "vz_au_per_year",
    ]

    reference = results["eps_1e13"][columns].to_numpy()

    for name in configs:
        values = results[name][columns].to_numpy()

        position_difference = np.linalg.norm(
            values[:, :3] - reference[:, :3], axis=1
        )
        velocity_difference = np.linalg.norm(
            values[:, 3:] - reference[:, 3:], axis=1
        )

        print(f"\n{name} (epsilon={configs[name]:.0e})")
        print(
            "Maximum position difference: "
            f"{position_difference.max():.8e} AU"
        )
        print(
            "Maximum velocity difference: "
            f"{velocity_difference.max():.8e} AU/year"
        )

    print("\nTolerance sensitivity test completed.")

finally:
    import shutil
    shutil.rmtree(TEST_DIR, ignore_errors=True)
