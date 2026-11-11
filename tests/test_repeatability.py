
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "synthetic_asteroid.json"
SIMULATOR = ROOT / "src" / "configurable_simulator.py"

RUN_A = ROOT / "data" / "repeatability" / "run_a"
RUN_B = ROOT / "data" / "repeatability" / "run_b"

# Read the original configuration and make temporary copies.
import json

with CONFIG.open("r", encoding="utf-8") as f:
    base_config = json.load(f)

temp_dir = ROOT / "configs" / "repeatability_temp"
temp_dir.mkdir(parents=True, exist_ok=True)

config_a = temp_dir / "run_a.json"
config_b = temp_dir / "run_b.json"

for path, output_dir in [
    (config_a, RUN_A),
    (config_b, RUN_B),
]:
    config = json.loads(json.dumps(base_config))
    config["output"]["directory"] = str(output_dir.relative_to(ROOT))

    with path.open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

try:
    # Run the exact same configuration twice.
    subprocess.run(
        [sys.executable, str(SIMULATOR), str(config_a)],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        [sys.executable, str(SIMULATOR), str(config_b)],
        cwd=ROOT,
        check=True,
    )

    df_a = pd.read_csv(RUN_A / "trajectory.csv")
    df_b = pd.read_csv(RUN_B / "trajectory.csv")

    if df_a.shape != df_b.shape:
        raise AssertionError("The two trajectory files have different shapes.")

    columns = [
        "time_years",
        "x_au", "y_au", "z_au",
        "vx_au_per_year",
        "vy_au_per_year",
        "vz_au_per_year",
    ]

    values_a = df_a[columns].to_numpy()
    values_b = df_b[columns].to_numpy()

    max_difference = np.max(np.abs(values_a - values_b))

    print(f"\nMaximum absolute difference: {max_difference:.12e}")

    if np.allclose(values_a, values_b, rtol=1e-10, atol=1e-12):
        print("PASS: identical configuration produces repeatable output.")
    else:
        raise AssertionError("Repeatability test failed.")

finally:
    # Remove only the temporary configuration files.
    shutil.rmtree(temp_dir, ignore_errors=True)
