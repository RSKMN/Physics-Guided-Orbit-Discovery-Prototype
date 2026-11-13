"""Component 1 integration test.

Each configuration is copied into a temporary directory with an absolute
output directory so that the test never overwrites tracked ``data/runs/``
artefacts. The module can also be run directly; it then uses a temporary
directory.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

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


def run_configuration(config_path: Path, output_root: Path) -> Path:
    """Run one simulation with output redirected under ``output_root``."""

    with Path(config_path).open(encoding="utf-8") as file:
        config = json.load(file)

    output_dir = Path(output_root) / config_path.stem
    config["output"]["directory"] = str(output_dir)

    temp_config = Path(output_root) / f"{config_path.stem}.json"
    temp_config.write_text(json.dumps(config, indent=4), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "src" / "configurable_simulator.py"),
            str(temp_config),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, (
        f"Simulation failed for {config_path.name}\n"
        f"{result.stdout}\n{result.stderr}"
    )

    return output_dir


def check_output(config_path: Path, output_dir: Path) -> None:
    """Validate the generated trajectory, config copy and metadata."""

    with Path(config_path).open(encoding="utf-8") as file:
        config = json.load(file)

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
    assert metadata["simulation_name"] == config["simulation_name"]

    if config["output"].get("save_plot", False):
        assert (output_dir / "trajectory_xy.png").exists()
        assert (output_dir / "trajectory_3d.png").exists()


@pytest.mark.parametrize(
    "config_path",
    CONFIGS,
    ids=[path.stem for path in CONFIGS],
)
def test_configuration(config_path: Path, tmp_path: Path) -> None:
    """Each tracked simulation configuration must run and produce valid output."""

    output_dir = run_configuration(config_path, tmp_path)
    check_output(config_path, output_dir)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="orbit-c1-integration-") as tmp:
        output_root = Path(tmp)
        for config_path in CONFIGS:
            output_dir = run_configuration(config_path, output_root)
            check_output(config_path, output_dir)
            print(f"PASS: {config_path.name}")

    print("Component 1 integration test: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
