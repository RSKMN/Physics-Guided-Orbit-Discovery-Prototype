
from pathlib import Path
import sys

import numpy as np
from astroquery.jplhorizons import Horizons

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from horizons_loader import load_horizons_states

EPOCH_JD = 2460676.5

# Load the initial states from the existing loader.
states = load_horizons_states(EPOCH_JD, ["Eros"])
state = states["Eros"]

# Query Eros again at exactly the same epoch and origin.
row = Horizons(
    id="433",
    location="@sun",
    epochs=EPOCH_JD,
).vectors(refplane="ecliptic")[0]

loader_position = np.array([state["x"], state["y"], state["z"]])
reference_position = np.array([
    float(row["x"]),
    float(row["y"]),
    float(row["z"]),
])

loader_velocity = np.array([
    state["vx"], state["vy"], state["vz"]
])

reference_velocity = np.array([
    float(row["vx"]) * 365.25,
    float(row["vy"]) * 365.25,
    float(row["vz"]) * 365.25,
])

print("\nInitial-state consistency check")
print("Position difference (AU):",
      np.linalg.norm(loader_position - reference_position))
print("Velocity difference (AU/year):",
      np.linalg.norm(loader_velocity - reference_velocity))
print("Epoch JD TDB:", EPOCH_JD)
print("Reference plane: ecliptic")
print("Origin: Sun")
