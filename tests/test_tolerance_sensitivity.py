"""Component 1 IAS15 tolerance-sensitivity check.

The test writes only to a pytest ``tmp_path`` directory. It can also be run as
a standalone script, in which case it uses a temporary directory unless an
explicit output root is supplied:

    python tests/test_tolerance_sensitivity.py [OUTPUT_ROOT]
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
SIMULATOR = ROOT / "src" / "configurable_simulator.py"
BASE_CONFIG = ROOT / "configs" / "synthetic_asteroid.json"

TOLERANCES = {
    "eps_1e9": 1e-9,
    "eps_1e12": 1e-12,
    "eps_1e13": 1e-13,
}

COLUMNS = [
    "x_au",
    "y_au",
    "z_au",
    "vx_au_per_year",
    "vy_au_per_year",
    "vz_au_per_year",
]

# The three tolerances are expected to agree far below this threshold for the
# standard five-year scenario. The threshold is a regression guard, not a
# scientific accuracy claim.
MAX_POSITION_DIFFERENCE_AU = 1e-9
MAX_VELOCITY_DIFFERENCE_AU_PER_YEAR = 1e-9


def run_tolerance_set(base_config_path: Path, output_root: Path) -> dict[str, pd.DataFrame]:
    """Run the base scenario at each tolerance and return the trajectories."""

    output_root = Path(output_root)
    config_dir = output_root / "configs"
    config_dir.mkdir(parents=True, exist_ok=True)

    with Path(base_config_path).open("r", encoding="utf-8") as file:
        base = json.load(file)

    results: dict[str, pd.DataFrame] = {}
    for name, epsilon in TOLERANCES.items():
        config = json.loads(json.dumps(base))
        config["simulation"]["integrator_epsilon"] = epsilon
        config["output"]["directory"] = str(output_root / name)
        config["output"]["save_plot"] = False

        config_path = config_dir / f"{name}.json"
        with config_path.open("w", encoding="utf-8") as file:
            json.dump(config, file, indent=4)

        subprocess.run(
            [sys.executable, str(SIMULATOR), str(config_path)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        results[name] = pd.read_csv(output_root / name / "trajectory.csv")

    return results


def _report_and_assert(results: dict[str, pd.DataFrame]) -> None:
    reference = results["eps_1e13"][COLUMNS].to_numpy()

    for name in TOLERANCES:
        values = results[name][COLUMNS].to_numpy()

        position_difference = np.linalg.norm(
            values[:, :3] - reference[:, :3], axis=1
        )
        velocity_difference = np.linalg.norm(
            values[:, 3:] - reference[:, 3:], axis=1
        )

        print(f"\n{name} (epsilon={TOLERANCES[name]:.0e})")
        print(
            "Maximum position difference: "
            f"{position_difference.max():.8e} AU"
        )
        print(
            "Maximum velocity difference: "
            f"{velocity_difference.max():.8e} AU/year"
        )

        assert np.isfinite(values).all()
        assert position_difference.max() < MAX_POSITION_DIFFERENCE_AU
        assert velocity_difference.max() < MAX_VELOCITY_DIFFERENCE_AU_PER_YEAR


def test_tolerance_sensitivity(tmp_path: Path) -> None:
    """IAS15 results must be insensitive to the tested tolerances."""

    results = run_tolerance_set(BASE_CONFIG, tmp_path)
    _report_and_assert(results)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "output_root",
        nargs="?",
        help="Directory for generated runs (default: a temporary directory).",
    )
    args = parser.parse_args(argv)

    if args.output_root is None:
        with tempfile.TemporaryDirectory(prefix="orbit-tolerance-") as tmp:
            results = run_tolerance_set(BASE_CONFIG, Path(tmp))
            _report_and_assert(results)
    else:
        results = run_tolerance_set(BASE_CONFIG, Path(args.output_root))
        _report_and_assert(results)

    print("\nTolerance sensitivity test completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
