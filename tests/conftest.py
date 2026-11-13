"""Shared pytest configuration and fixtures.

The fixtures here are intentionally small. They provide stable repository
locations and keep test output out of tracked ``data/`` directories. Tests that
generate files must use pytest's ``tmp_path`` fixture; no autouse fixture writes
into the repository.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"


def pytest_configure() -> None:
    """Make the source tree importable without relying on an editable install.

    The project supports editable installation, but the offline test suite must
    also work when invoked with ``PYTHONPATH=src`` or from a plain checkout.
    """

    for path in (REPO_ROOT, SRC_DIR):
        entry = str(path)
        if entry not in sys.path:
            sys.path.insert(0, entry)


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Absolute path to the repository root."""

    return REPO_ROOT


@pytest.fixture(scope="session")
def configs_dir(repo_root: Path) -> Path:
    """Directory containing the tracked scientific configurations."""

    return repo_root / "configs"


@pytest.fixture(scope="session")
def synthetic_simulation_config(configs_dir: Path) -> Path:
    """The standard Component 1 simulation configuration."""

    return configs_dir / "synthetic_asteroid.json"


@pytest.fixture(scope="session")
def synthetic_observation_config(configs_dir: Path) -> Path:
    """The standard Component 2 observation configuration."""

    return configs_dir / "synthetic_observations.json"


@pytest.fixture(autouse=True)
def _headless_matplotlib(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent test runs from opening interactive matplotlib windows."""

    monkeypatch.setenv("MPLBACKEND", "Agg")


@pytest.fixture
def isolated_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Run a test from a temporary working directory.

    Useful for checking that module and console entry points do not depend on
    the repository being the current working directory.
    """

    monkeypatch.chdir(tmp_path)
    return tmp_path
