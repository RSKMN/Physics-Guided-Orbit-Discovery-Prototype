
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

two_body = pd.read_csv(ROOT / "data" / "trajectory_two_body.csv")
nbody = pd.read_csv(ROOT / "data" / "trajectory_nbody_synthetic.csv")

# The two datasets should use the same sampling times.
assert len(two_body) == len(nbody)
assert np.allclose(two_body["time_yr"], nbody["time_yr"])

# Calculate the difference between Sun-relative positions.
dx = nbody["x_AU"].to_numpy() - two_body["x_AU"].to_numpy()
dy = nbody["y_AU"].to_numpy() - two_body["y_AU"].to_numpy()
dz = nbody["z_AU"].to_numpy() - two_body["z_AU"].to_numpy()

separation = np.sqrt(dx**2 + dy**2 + dz**2)

print("Two-body vs synthetic N-body comparison")
print(f"Maximum position difference: {separation.max():.8f} AU")
print(f"Final position difference:  {separation[-1]:.8f} AU")

fig, ax = plt.subplots(figsize=(9, 9))

ax.plot(
    two_body["x_AU"], two_body["y_AU"],
    label="Two-body baseline",
)

ax.plot(
    nbody["x_AU"], nbody["y_AU"],
    label="Synthetic N-body",
)

ax.scatter([0], [0], color="orange", s=150, label="Sun")
ax.set_xlabel("X relative to Sun (AU)")
ax.set_ylabel("Y relative to Sun (AU)")
ax.set_title("Two-body vs N-body Trajectories")
ax.set_aspect("equal", adjustable="box")
ax.grid(True, alpha=0.3)
ax.legend()

output = ROOT / "plots" / "two_body_vs_nbody.png"
fig.savefig(output, dpi=150, bbox_inches="tight")
plt.show()

print(f"Comparison plot saved to: {output}")


# Plot the distance between the two predicted positions
fig, ax = plt.subplots(figsize=(10, 5))

ax.plot(
    two_body["time_yr"],
    separation,
    color="darkred",
)

ax.set_xlabel("Time (years)")
ax.set_ylabel("Position difference (AU)")
ax.set_title("Difference Between Two-Body and N-Body Predictions")
ax.grid(True, alpha=0.3)

difference_plot = ROOT / "plots" / "trajectory_difference.png"
fig.savefig(difference_plot, dpi=150, bbox_inches="tight")
plt.show()

print(f"Difference plot saved to: {difference_plot}")
