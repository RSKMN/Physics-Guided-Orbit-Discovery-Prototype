"""CLI entry-point and output-path tests.

These tests exercise the dispatch layer in-process and, for module/console
execution, in a subprocess from a temporary working directory. Generated files
always go under ``tmp_path``.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from orbit_discovery.cli import main

REPO_ROOT = Path(__file__).resolve().parents[1]
SIMULATION_CONFIG = REPO_ROOT / "configs" / "synthetic_asteroid.json"
OBSERVATION_CONFIG = REPO_ROOT / "configs" / "synthetic_observations.json"
TRACKED_TRAJECTORY = REPO_ROOT / "data" / "runs" / "synthetic_asteroid" / "trajectory.csv"


def _subprocess_environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONPATH"] = os.pathsep.join(
        [str(REPO_ROOT / "src"), str(REPO_ROOT), environment.get("PYTHONPATH", "")]
    ).rstrip(os.pathsep)
    return environment


def _write_simulation_config(tmp_path: Path) -> tuple[Path, Path]:
    config = json.loads(SIMULATION_CONFIG.read_text(encoding="utf-8"))
    config["simulation_name"] = "cli_test_simulation"
    config["simulation"]["duration_years"] = 0.02
    config["simulation"]["output_interval_days"] = 1.0
    output_dir = tmp_path / "simulation_output"
    config["output"] = {"directory": str(output_dir), "save_plot": False}

    config_path = tmp_path / "simulation.json"
    config_path.write_text(json.dumps(config, indent=4), encoding="utf-8")
    return config_path, output_dir


def _write_observation_config(tmp_path: Path) -> tuple[Path, Path]:
    config = json.loads(OBSERVATION_CONFIG.read_text(encoding="utf-8"))
    config["observation_name"] = "cli_test_observations"
    config["input_trajectory"] = str(TRACKED_TRAJECTORY)
    config["observation_schedule"]["cadence_days"] = 30.0
    config["observation_schedule"]["start_day"] = 0.0
    config["observation_schedule"]["end_day"] = 90.0
    output_root = tmp_path / "observation_output"
    config["output"]["directory"] = str(output_root)

    config_path = tmp_path / "observations.json"
    config_path.write_text(json.dumps(config, indent=4), encoding="utf-8")
    return config_path, output_root / config["observation_name"]


def test_pyproject_declares_console_script() -> None:
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["scripts"]["orbit"] == "orbit_discovery.cli:main"


def test_module_execution_help_from_temporary_directory(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "orbit_discovery.cli", "--help"],
        cwd=tmp_path,
        env=_subprocess_environment(),
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "Orbit CLI" in result.stdout
    assert "simulate" in result.stdout


def test_module_execution_version_from_temporary_directory(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "orbit_discovery.cli", "--version"],
        cwd=tmp_path,
        env=_subprocess_environment(),
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "0.2.0" in result.stdout


def test_console_script_help_if_installed(tmp_path: Path) -> None:
    executable_name = "orbit.exe" if os.name == "nt" else "orbit"
    script = Path(sys.executable).parent / executable_name
    if not script.exists():
        pytest.skip("orbit console script is not installed in this interpreter")

    result = subprocess.run(
        [str(script), "--help"],
        cwd=tmp_path,
        env=_subprocess_environment(),
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "Orbit CLI" in result.stdout


def test_simulate_reports_configured_output_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(REPO_ROOT)
    config_path, output_dir = _write_simulation_config(tmp_path)

    exit_code = main(["simulate", "--config", str(config_path)])
    captured = capsys.readouterr()

    assert exit_code == 0, captured.err
    assert (output_dir / "trajectory.csv").exists()
    assert (output_dir / "metadata.json").exists()
    assert "Simulation name: cli_test_simulation" in captured.out
    assert str(output_dir) in captured.out
    assert "data/runs/synthetic_asteroid" not in captured.out


def test_simulate_rejects_unsupported_output_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(REPO_ROOT)
    config_path, _ = _write_simulation_config(tmp_path)

    exit_code = main(
        [
            "simulate",
            "--config",
            str(config_path),
            "--output-root",
            str(tmp_path / "elsewhere"),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "--output-root is not supported" in captured.err


def test_observe_uses_configured_output_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(REPO_ROOT)
    config_path, output_dir = _write_observation_config(tmp_path)

    exit_code = main(["observe", "--config", str(config_path)])
    captured = capsys.readouterr()

    assert exit_code == 0, captured.err
    assert (output_dir / "observations.csv").exists()
    assert (output_dir / "metadata.json").exists()
    assert str(output_dir) in captured.out


def test_observe_rejects_unsupported_output_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(REPO_ROOT)
    config_path, _ = _write_observation_config(tmp_path)

    exit_code = main(
        [
            "observe",
            "--config",
            str(config_path),
            "--output-root",
            str(tmp_path / "elsewhere"),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "--output-root is not supported" in captured.err
    assert not (tmp_path / "elsewhere").exists()


def test_unknown_command_returns_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["not-a-command"])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert "Unknown command" in captured.err
