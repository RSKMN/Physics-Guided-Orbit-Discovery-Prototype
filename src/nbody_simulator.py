
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rebound


# --------------------------------------------------
# 1. Output directories
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PLOTS_DIR = PROJECT_ROOT / "plots"

DATA_DIR.mkdir(parents=True, exist_ok=True)
PLOTS_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# 2. Simulation configuration
# --------------------------------------------------

DURATION_YR = 5.0
NUMBER_OF_SAMPLES = 1000

# Synthetic planetary masses in solar masses.
# Orbital elements below are simplified, not real ephemerides.
PLANETS = [
    {
        "name": "Mercury",
        "mass": 1.660e-7,
        "a": 0.387,
        "phase_deg": 0.0,
    },
    {
        "name": "Venus",
        "mass": 2.447e-6,
        "a": 0.723,
        "phase_deg": 70.0,
    },
    {
        "name": "Earth",
        "mass": 3.003e-6,
        "a": 1.000,
        "phase_deg": 150.0,
    },
    {
        "name": "Jupiter",
        "mass": 9.545e-4,
        "a": 5.204,
        "phase_deg": 230.0,
    },
]


# --------------------------------------------------
# 3. Create the N-body system
# --------------------------------------------------

sim = rebound.Simulation()
sim.units = ("yr", "AU", "Msun")

# Add the Sun.
sim.add(m=1.0)

# Add planets on synthetic circular, coplanar orbits.
for planet in PLANETS:
    sim.add(
        m=planet["mass"],
        a=planet["a"],
        e=0.0,
        inc=0.0,
        M=np.radians(planet["phase_deg"]),
        primary=sim.particles[0],
    )

# Add the asteroid using the same initial orbital
# elements as the two-body baseline.
sim.add(
    m=0.0,
    a=2.5,
    e=0.2,
    inc=0.0,
    primary=sim.particles[0],
)

# Shift the whole system into its center-of-mass frame.
# All body states are shifted consistently.
sim.move_to_com()

# Use IAS15 for a high-accuracy adaptive integration.
sim.integrator = "ias15"


# --------------------------------------------------
# 4. Integrate and record asteroid states
# --------------------------------------------------

times = np.linspace(0.0, DURATION_YR, NUMBER_OF_SAMPLES)
rows = []

sun = sim.particles[0]
asteroid_index = 1 + len(PLANETS)

for t in times:
    sim.integrate(t)

    sun = sim.particles[0]
    asteroid = sim.particles[asteroid_index]

    # Record asteroid state relative to the Sun.
    dx = asteroid.x - sun.x
    dy = asteroid.y - sun.y
    dz = asteroid.z - sun.z

    dvx = asteroid.vx - sun.vx
    dvy = asteroid.vy - sun.vy
    dvz = asteroid.vz - sun.vz

    distance = np.sqrt(dx**2 + dy**2 + dz**2)

    rows.append({
        "time_yr": t,
        "x_AU": dx,
        "y_AU": dy,
        "z_AU": dz,
        "vx_AU_per_yr": dvx,
        "vy_AU_per_yr": dvy,
        "vz_AU_per_yr": dvz,
        "distance_AU": distance,
    })


# --------------------------------------------------
# 5. Save the trajectory
# --------------------------------------------------

df = pd.DataFrame(rows)

csv_path = DATA_DIR / "trajectory_nbody_synthetic.csv"
df.to_csv(csv_path, index=False)


# --------------------------------------------------
# 6. Plot the N-body trajectory
# --------------------------------------------------

fig, ax = plt.subplots(figsize=(9, 9))

ax.plot(
    df["x_AU"],
    df["y_AU"],
    color="royalblue",
    label="Asteroid: N-body",
)

ax.scatter(
    [0],
    [0],
    color="orange",
    s=180,
    label="Sun (relative origin)",
    zorder=4,
)

ax.set_xlabel("X relative to Sun (AU)")
ax.set_ylabel("Y relative to Sun (AU)")
ax.set_title("Synthetic N-body Asteroid Simulation")
ax.set_aspect("equal", adjustable="box")
ax.grid(True, alpha=0.3)
ax.legend()

plot_path = PLOTS_DIR / "nbody_synthetic_orbit.png"
fig.savefig(plot_path, dpi=150, bbox_inches="tight")
plt.show()


# --------------------------------------------------
# 7. Basic validation checks
# --------------------------------------------------

numeric_data = df.select_dtypes(include="number").to_numpy()

assert len(df) == NUMBER_OF_SAMPLES
assert np.isfinite(numeric_data).all()
assert np.all(np.diff(df["time_yr"]) > 0)

print("\nSynthetic N-body simulation completed.")
print(f"Bodies: Sun + {len(PLANETS)} planets + asteroid")
print(f"Duration: {DURATION_YR} years")
print(f"Samples: {len(df)}")
print(f"Minimum Sun-relative distance: {df['distance_AU'].min():.4f} AU")
print(f"Maximum Sun-relative distance: {df['distance_AU'].max():.4f} AU")
print(f"All numeric values finite: {np.isfinite(numeric_data).all()}")
print(f"Trajectory CSV: {csv_path}")
print(f"Orbit plot: {plot_path}")
