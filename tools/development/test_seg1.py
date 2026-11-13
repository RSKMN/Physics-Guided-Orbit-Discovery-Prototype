#!/usr/bin/env python3
import sys
sys.path.insert(0, 'src')
import numpy as np
from orbit_discovery.core.interpolation_validation import _generate_reference_states, _compute_interpolated_state, _compute_errors
from orbit_discovery.component2_observations.loader import load_trajectory
from orbit_discovery.core.propagation import propagate_state

traj = load_trajectory('data/runs/synthetic_asteroid/trajectory.csv')
times = np.asarray(traj['time_years'], dtype=float)
positions = np.asarray(traj['positions'], dtype=float)
velocities = np.asarray(traj['velocities'], dtype=float)

ref_states = _generate_reference_states(traj, epsilon=1e-14)

# Test segment 1 (between samples 1 and 2)
seg_idx = 1
t_start = float(times[seg_idx])  # 0.005
t_end = float(times[seg_idx + 1])  # 0.01
segment_duration = t_end - t_start

n_intermediate = 9
intermediate_epochs = np.linspace(
    t_start + segment_duration / (n_intermediate + 1),
    t_end - segment_duration / (n_intermediate + 1),
    n_intermediate,
)

print(f'Segment {seg_idx}: t_start={t_start:.4f}, t_end={t_end:.4f}')
print(f'intermediate_epochs: {intermediate_epochs[:3]}...')

all_pos_errors = []
all_vel_errors = []

for t_eval in intermediate_epochs:
    ref_idx = int(np.searchsorted(times, t_eval, side="right") - 1)
    print(f'  t_eval={t_eval:.6f}, ref_idx={ref_idx}, t_ref={times[ref_idx]:.6f}')
    
    # Propagate reference from t_ref to t_eval
    try:
        propagated = propagate_state(
            positions[ref_idx, 0], positions[ref_idx, 1], positions[ref_idx, 2],
            velocities[ref_idx, 0], velocities[ref_idx, 1], velocities[ref_idx, 2],
            t_eval
        )
        ref_state = type('R', (), {})()
        ref_state.epoch_years = t_eval
        ref_state.x_au = float(propagated["x_au"])
        ref_state.y_au = float(propagated["y_au"])
        ref_state.z_au = float(propagated["z_au"])
        ref_state.vx_au_per_year = float(propagated["vx_au_per_year"])
        ref_state.vy_au_per_year = float(propagated["vy_au_per_year"])
        ref_state.vz_au_per_year = float(propagated["vz_au_per_year"])
    except ValueError as e:
        print(f'    Propagation failed: {e}')
        ref_state = ref_states[ref_idx]
    
    # Get interpolated state
    try:
        interp = _compute_interpolated_state(traj, t_eval)
    except ValueError as e:
        print(f'    Interpolation failed: {e}')
        continue
    
    pos_err, vel_err = _compute_errors(ref_state, interp)
    all_pos_errors.append(pos_err)
    all_vel_errors.append(vel_err)
    
    print(f'    pos_err={pos_err:.2e} AU, vel_err={vel_err:.2e} AU/yr')

print(f'\nSegment {seg_idx} results:')
print(f'  mean pos err: {np.mean(all_pos_errors):.2e} AU')
print(f'  mean vel err: {np.mean(all_vel_errors):.2e} AU/yr')