#!/usr/bin/env python3
"""Debug the propagation."""
import sys
sys.path.insert(0, 'src')
import numpy as np
from orbit_discovery.core.propagation import propagate_state
from orbit_discovery.component2_observations.loader import load_trajectory

traj = load_trajectory('data/runs/synthetic_asteroid/trajectory.csv')
times = np.asarray(traj['time_years'], dtype=float)
positions = np.asarray(traj['positions'], dtype=float)
velocities = np.asarray(traj['velocities'], dtype=float)

# Test propagate_state at t = times[1] = 0.005 yr
t_eval = times[1]
print(f't_eval = {t_eval:.4f}')

# Get initial state from sample 1
x0, y0, z0 = positions[1]
vx0, vy0, vz0 = velocities[1]

# Propagate
try:
    propagated = propagate_state(x0, y0, z0, vx0, vy0, vz0, t_eval)
    print(f'Propagated state: x={propagated["x_au"]:.6f}, y={propagated["y_au"]:.6f}')
    print(f'Reference state at sample 1: x={traj["positions"][1,0]:.6f}, y={traj["positions"][1,1]:.6f}')
    dx = abs(propagated["x_au"] - traj["positions"][1,0])
    dy = abs(propagated["y_au"] - traj["positions"][1,1])
    print(f'Difference: x diff={dx:.2e}, y diff={dy:.2e}')
except Exception as e:
    print(f'Error: {e}')