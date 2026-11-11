
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rebound

from horizons_loader import load_horizons_states


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
PLOTS_DIR = ROOT / "plots"

DATA_DIR.mkdir(exist_ok=True)
PLOTS_DIR.mkdir(exist_ok=True)

EPOCH_JD = 2460676.5  # 2025-01-01 00:00 TDB
DURATION_YR = 5.0
SAMPLES = 1000

PLANETS = ["Mercury", "Venus", "Earth", "Mars", "Jupiter"]
ASTEROID = "Eros"

# Download all states at the same epoch.
states = load_horizons_states(
    EPOCH_JD,
    PLANETS + [ASTEROID],
)

# Create the simulation with consistent units.
sim = rebound.Simulation()
sim.units = ("yr", "AU", "Msun")

# Sun at the origin. The other states are Sun-relative.
sim.add(m=1.0)

for name in PLANETS + [ASTEROID]:
    state = states[name]

    sim.add(
        m=state["mass"],
        x=state["x"],
        y=state["y"],
        z=state["z"],
        vx=state["vx"],
        vy=state["vy"],
        vz=state["vz"],
        
    )

# Translate all bodies together into the center-of-mass frame.
# This preserves their relative positions and velocities.
sim.move_to_com()

sim.integrator = "ias15"

times = np.linspace(0.0, DURATION_YR, SAMPLES)
rows = []

for t in times:
    sim.integrate(t)

    sun = sim.particles[0]
    asteroid_index = 1 + len(PLANETS)
    asteroid = sim.particles[asteroid_index]

    # Record asteroid state relative to the moving Sun.
    dx = asteroid.x - sun.x
    dy = asteroid.y - sun.y
    dz = asteroid.z - sun.z

    dvx = asteroid.vx - sun.vx
    dvy = asteroid.vy - sun.vy
    dvz = asteroid.vz - sun.vz

    rows.append({
        "time_yr": t,
        "x_AU": dx,
        "y_AU": dy,
        "z_AU": dz,
        "vx_AU_per_yr": dvx,
        "vy_AU_per_yr": dvy,
        "vz_AU_per_yr": dvz,
        "distance_AU": np.sqrt(dx**2 + dy**2 + dz**2),
    })

df = pd.DataFrame(rows)

csv_path = DATA_DIR / "trajectory_nbody_eros.csv"
df.to_csv(csv_path, index=False)

fig, ax = plt.subplots(figsize=(8, 8))
ax.plot(df["x_AU"], df["y_AU"], label="Eros: REBOUND")
ax.scatter([0], [0], color="orange", s=150, label="Sun")
ax.set_xlabel("X relative to Sun (AU)")
ax.set_ylabel("Y relative to Sun (AU)")
ax.set_title("Realistic-Initialization N-body Simulation")
ax.set_aspect("equal", adjustable="box")
ax.grid(True, alpha=0.3)
ax.legend()

plot_path = PLOTS_DIR / "nbody_eros.png"
fig.savefig(plot_path, dpi=150, bbox_inches="tight")
plt.show()

assert len(df) == SAMPLES
assert np.isfinite(df.select_dtypes("number").to_numpy()).all()

print("\nRealistic-initialization simulation completed.")
print(f"Asteroid: {ASTEROID}")
print(f"Epoch JD (TDB): {EPOCH_JD}")
print(f"Samples: {len(df)}")
print(f"CSV: {csv_path}")
print(f"Plot: {plot_path}")
