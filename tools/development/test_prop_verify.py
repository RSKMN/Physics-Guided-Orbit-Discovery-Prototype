#!/usr/bin/env python3
import sys
sys.path.insert(0, 'src')
import numpy as np
from orbit_discovery.core.propagation import propagate_state
from orbit_discovery.component2_observations.loader import load_trajectory

traj = load_trajectory('data/runs/synthetic_asteroid/trajectory.csv')
times = np.asarray(traj['time_years'], dtype=float)
positions = np.asarray(traj['positions'], dtype=float)
velocities = np.asarray(traj['velocities'], dtype=float)

# At sample 1 (t=0.005):
print('=== At sample 1 (t=0.005) ===')
# Propagate from sample 1 initial state to t=0.005 (should be no-op essentially)
prop1 = propagate_state(positions[1,0], positions[1,1], positions[1,2],
                        velocities[1,0], velocities[1,1], velocities[1,2],
                        0.005)
print(f'propagate_state from sample 1 to t=0.005: x={prop1["x_au"]:.6f}, y={prop1["y_au"]:.6f}')

# Reference state at sample 1 (from _generate_reference_states)
from orbit_discovery.core.interpolation_validation import _generate_reference_states
ref_states = _generate_reference_states(traj, epsilon=1e-14)
ref1 = ref_states[1]
print(f'Ref state at sample 1: x={ref1.x_au:.6f}, y={ref1.y_au:.6f}')
print(f'Difference: x={abs(prop1["x_au"]-ref1.x_au):.2e}, y={abs(prop1["y_au"]-ref1.y_au):.2e}')

# Now propagate from sample 1 to t=0.0075 (midway to sample 2)
print('\n=== Propagate from sample 1 to t=0.0075 ===')
prop1_75 = propagate_state(positions[1,0], positions[1,1], positions[1,2],
                           velocities[1,0], velocities[1,1], velocities[1,2],
                           0.0075)
print(f'propagate_state from sample 1 to t=0.0075: x={prop1_75["x_au"]:.6f}, y={prop1_75["y_au"]:.6f}')

# What if we propagate from t=0 to t=0.0075?
prop0_75 = propagate_state(positions[0,0], positions[0,1], positions[0,2],
                           velocities[0,0], velocities[0,1], velocities[0,2],
                           0.0075)
print(f'propagate_state from sample 0 (t=0) to t=0.0075: x={prop0_75["x_au"]:.6f}, y={prop0_75["y_au"]:.6f}')

# Reference state at t=0.0075 (from _generate_reference_states, closest sample)
ref_states = _generate_reference_states(traj, epsilon=1e-14)
# Find closest sample to 0.0075
ref_idx = int(np.searchsorted(times, 0.0075, side="right") - 1)
print(f'Closest ref sample: {ref_idx}, t={times[ref_idx]:.4f}')
ref_0075 = ref_states[ref_idx]
print(f'Ref state at closest sample: x={ref_0075.x_au:.6f}, y={ref_0075.y_au:.6f}')