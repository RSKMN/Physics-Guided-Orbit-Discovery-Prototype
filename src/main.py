
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rebound


# --------------------------------------------------
# 1. Project output directories
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PLOTS_DIR = PROJECT_ROOT / "plots"

DATA_DIR.mkdir(parents=True, exist_ok=True)
PLOTS_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# 2. Simulation configuration
# --------------------------------------------------

SUN_MASS = 1.0           # Solar masses
ASTEROID_MASS = 0.0      # Massless test particle
SEMI_MAJOR_AXIS = 2.5    # AU
ECCENTRICITY = 0.2
INCLINATION_DEG = 0.0    # Degrees

SIMULATION_DURATION_YR = 5.0
NUMBER_OF_SAMPLES = 1000


# --------------------------------------------------
# 3. Create the gravitational system
# --------------------------------------------------

sim = rebound.Simulation()
sim.units = ("yr", "AU", "Msun")

# Add the Sun at the origin
sim.add(m=SUN_MASS)

# Add an asteroid on an elliptical orbit around the Sun
sim.add(
    m=ASTEROID_MASS,
    a=SEMI_MAJOR_AXIS,
    e=ECCENTRICITY,
    inc=np.radians(INCLINATION_DEG),
    primary=sim.particles[0],
)

# Use a high-accuracy adaptive integrator
sim.integrator = "ias15"


# --------------------------------------------------
# 4. Integrate and record the trajectory
# --------------------------------------------------

times = np.linspace(
    0.0,
    SIMULATION_DURATION_YR,
    NUMBER_OF_SAMPLES,
)

rows = []

for t in times:
    sim.integrate(t)

    asteroid = sim.particles[1]

    rows.append({
        "time_yr": t,
        "x_AU": asteroid.x,
        "y_AU": asteroid.y,
        "z_AU": asteroid.z,
        "vx_AU_per_yr": asteroid.vx,
        "vy_AU_per_yr": asteroid.vy,
        "vz_AU_per_yr": asteroid.vz,
    })


# --------------------------------------------------
# 5. Save the trajectory as CSV
# --------------------------------------------------

df = pd.DataFrame(rows)


# Calculate distance from the Sun at every recorded time
df["distance_AU"] = np.sqrt(
    df["x_AU"]**2
    + df["y_AU"]**2
    + df["z_AU"]**2
)

# Display the distance checks
print("\n--- Distance Check ---")
print(f"Minimum distance: {df['distance_AU'].min():.4f} AU")
print(f"Maximum distance: {df['distance_AU'].max():.4f} AU")
print(f"Number of rows: {len(df)}")


csv_path = DATA_DIR / "trajectory_two_body.csv"
df.to_csv(csv_path, index=False)


# --------------------------------------------------
# 6. Plot the orbit
# --------------------------------------------------

fig, ax = plt.subplots(figsize=(8, 8))

ax.plot(
    df["x_AU"],
    df["y_AU"],
    label="Asteroid trajectory",
    color="royalblue",
)

ax.scatter(
    [0], [0],
    color="orange",
    s=180,
    label="Sun",
    zorder=3,
)

ax.scatter(
    [df["x_AU"].iloc[0]],
    [df["y_AU"].iloc[0]],
    color="green",
    s=45,
    label="Asteroid start",
    zorder=4,
)

ax.set_xlabel("X position (AU)")
ax.set_ylabel("Y position (AU)")
ax.set_title("Two-Body Sun–Asteroid Simulation")
ax.set_aspect("equal", adjustable="box")
ax.grid(True, alpha=0.3)
ax.legend()

plot_path = PLOTS_DIR / "two_body_orbit.png"
fig.savefig(plot_path, dpi=150, bbox_inches="tight")
plt.show()


# --------------------------------------------------
# 7. Report results
# --------------------------------------------------

print("\nSimulation completed successfully.")
print(f"Number of samples: {len(df)}")
print(f"Simulation duration: {SIMULATION_DURATION_YR} years")
print(f"Trajectory CSV: {csv_path}")
print(f"Orbit plot: {plot_path}")

print("\nFirst five trajectory rows:")
print(df.head())

print("\nAll position and velocity values are finite:",
      np.isfinite(df.select_dtypes(include="number").to_numpy()).all())
