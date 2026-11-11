
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from horizons_loader import load_horizons_states


# 2025-01-01 00:00 TDB
EPOCH_JD = 2460676.5

bodies = ["Mercury", "Venus", "Earth", "Mars", "Jupiter", "Eros"]

states = load_horizons_states(EPOCH_JD, bodies)

assert set(states) == set(bodies)

for name, state in states.items():
    assert state["epoch_jd_tdb"] == EPOCH_JD
    assert state["origin"] == "Sun"
    assert state["reference_plane"] == "ecliptic"

    values = [
        state["x"], state["y"], state["z"],
        state["vx"], state["vy"], state["vz"],
    ]

    assert np.isfinite(values).all()

print("\nHorizons loader test passed.")
print(f"Bodies loaded: {len(states)}")
