"""Component 1 repeatability check.

The test writes only to a pytest ``tmp_path`` directory. It can also be run as
a standalone script, in which case it uses a temporary directory unless an
explicit output root is supplied:

    python tests/test_repeatability.py [OUTPUT_ROOT]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "synthetic_asteroid.json"
SIMULATOR = ROOT / "src" / "configurable_simulator.py"

COLUMNS = [
    "time_years",
    "x_au",
    "y_au",
    "z_au",
    "vx_au_per_year",
    "vy_au_per_year",
    "vz_au_per_year",
]


def run_repeatability_pair(base_config_path: Path, output_root: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run the same configuration twice and return both trajectories.

    All generated files are placed under ``output_root``. The function does not
    touch tracked ``data/`` or ``configs/`` files.
    """

    output_root = Path(output_root)
    config_dir = output_root / "configs"
    config_dir.mkdir(parents=True, exist_ok=True)

    with Path(base_config_path).open("r", encoding="utf-8") as file:
        base_config = json.load(file)

    frames = []
    for run_name in ("run_a", "run_b"):
        run_dir = output_root / run_name
        config = json.loads(json.dumps(base_config))
        config["output"]["directory"] = str(run_dir)
        config["output"]["save_plot"] = False

        config_path = config_dir / f"{run_name}.json"
        with config_path.open("w", encoding="utf-8") as file:
            json.dump(config, file, indent=4)

        subprocess.run(
            [sys.executable, str(SIMULATOR), str(config_path)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        frames.append(pd.read_csv(run_dir / "trajectory.csv"))

    return frames[0], frames[1]


def test_repeatability(tmp_path: Path) -> None:
    """An identical configuration must produce identical trajectory values."""

    df_a, df_b = run_repeatability_pair(CONFIG, tmp_path)

    assert df_a.shape == df_b.shape

    values_a = df_a[COLUMNS].to_numpy()
    values_b = df_b[COLUMNS].to_numpy()

    max_difference = float(np.max(np.abs(values_a - values_b)))
    print(f"\nMaximum absolute difference: {max_difference:.12e}")

    np.testing.assert_allclose(values_a, values_b, rtol=1e-10, atol=1e-12)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "output_root",
        nargs="?",
        help="Directory for generated runs (default: a temporary directory).",
    )
    args = parser.parse_args(argv)

    if args.output_root is None:
        with tempfile.TemporaryDirectory(prefix="orbit-repeatability-") as tmp:
            df_a, df_b = run_repeatability_pair(CONFIG, Path(tmp))
    else:
        df_a, df_b = run_repeatability_pair(CONFIG, Path(args.output_root))

    values_a = df_a[COLUMNS].to_numpy()
    values_b = df_b[COLUMNS].to_numpy()
    max_difference = float(np.max(np.abs(values_a - values_b)))
    print(f"\nMaximum absolute difference: {max_difference:.12e}")
    print("PASS: identical configuration produces repeatable output.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
