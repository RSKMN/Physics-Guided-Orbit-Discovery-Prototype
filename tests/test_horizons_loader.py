"""JPL Horizons loader integration test.

This test requires the optional ``astroquery`` dependency and network access.
It is marked ``integration`` and ``network`` so the default offline suite never
imports ``astroquery`` or contacts JPL.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# 2025-01-01 00:00 TDB
EPOCH_JD = 2460676.5
BODIES = ["Mercury", "Venus", "Earth", "Mars", "Jupiter", "Eros"]


@pytest.mark.integration
@pytest.mark.network
def test_horizons_loader_returns_sun_relative_states() -> None:
    pytest.importorskip("astroquery")

    from horizons_loader import load_horizons_states

    states = load_horizons_states(EPOCH_JD, BODIES)

    assert set(states) == set(BODIES)

    for name, state in states.items():
        assert state["epoch_jd_tdb"] == EPOCH_JD
        assert state["origin"] == "Sun"
        assert state["reference_plane"] == "ecliptic"

        values = [
            state["x"],
            state["y"],
            state["z"],
            state["vx"],
            state["vy"],
            state["vz"],
        ]
        assert np.isfinite(values).all()


def main() -> int:
    pytest.importorskip("astroquery")
    test_horizons_loader_returns_sun_relative_states()
    print("\nHorizons loader test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
