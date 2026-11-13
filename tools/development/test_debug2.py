#!/usr/bin/env python3
import sys
sys.path.insert(0, 'src')
import numpy as np
from orbit_discovery.core.interpolation_validation import evaluate_trajectory, _generate_reference_states, _compute_interpolated_state, _compute_errors
from orbit_discovery.component2_observations.loader import load_trajectory
from orbit_discovery.core.propagation import propagate_state

traj = load_trajectory('data/runs/synthetic_asteroid/trajectory.csv')
times = np.asarray(traj['time_years'], dtype=float)
positions = np.asarray(traj['positions'], dtype=float)
velocities = np.asarray(traj['velocities'], dtype=float)

# Manually replicate the evaluate_trajectory logic for the first segment
n_samples = len(times)
n_intermediate = 9
sampling_interval = 0.005  # default

ref_states = _generate_reference_states(traj, epsilon=1e-14)

# First segment: between samples 0 and 1
seg_idx = 0
t_start = float(times[seg_idx])
t_end = float(times[seg_idx + 1])
segment_duration = t_end - t_start

intermediate_epochs = np.linspace(
    t_start + segment_duration / (n_intermediate + 1),
    t_end - segment_duration / (n_intermediate + 1),
    n_intermediate,
)

print(f'Segment {seg_idx}: t_start={t_start:.4f}, t_end={t_end:.4f}, duration={segment_duration:.4f}')
print(f'n_intermediate={n_intermediate}, intermediate_epochs={len(intermediate_epochs)}')
print()

all_pos_errors = []
all_vel_errors = []
segments_evaluated = 0

for i, t_eval in enumerate(intermediate_epochs):
    # Find enclosing sample index
    ref_idx = int(np.searchsorted(times, t_eval, side="right") - 1)
    if ref_idx < 0:
        ref_idx = 0
    if ref_idx >= len(times) - 1:
        ref_idx = len(times) - 2
    
    t_ref = float(times[ref_idx])
    
    # Propagate reference from t_ref to t_eval
    try:
        propagated = propagate_state(
            positions[ref_idx, 0], positions[ref_idx, 1], positions[ref_idx, 2],
            velocities[ref_idx, 0], velocities[ref_idx, 1], velocities[ref_idx, 2],
            t_eval
        )
        ref_state_type = type('R', (), {})()
        ref_state_type.epoch_years = t_eval
        ref_state_type.x_au = float(propagated["x_au"])
        ref_state_type.y_au = float(propagated["y_au"])
        ref_state_type.z_au = float(propagated["z_au"])
        ref_state_type.vx_au_per_year = float(propagated["vx_au_per_year"])
        ref_state_type.vy_au_per_year = float(propagated["vy_au_per_year"])
        ref_state_type.vz_au_per_year = float(propagated["vz_au_per_year"])
    except ValueError as e:
        print(f'  Propagation failed at epoch {t_eval:.4f}: {e}')
        ref_idx_fallback = ref_idx
        ref_state_type = ref_states[ref_idx_fallback]
    
    # Get interpolated state
    try:
        interp = _compute_interpolated_state(traj, t_eval)
    except ValueError as e:
        print(f'  Interpolation failed at epoch {t_eval:.4f}: {e}')
        continue
    
    # Compute errors
    pos_err, vel_err = _compute_errors(ref_state_type, interp)
    
    all_pos_errors.append(pos_err)
    all_vel_errors.append(vel_err)
    segments_evaluated += 1
    
    if i < 3:  # Print first 3
        print(f'  epoch {i+1}: t_eval={t_eval:.4f}, ref_idx={ref_idx}, t_ref={t_ref:.4f}')
        print(f'    propagated x={propagated["x_au"]:.6f}, y={propagated["y_au"]:.6f}')
        print(f'    ref_state_direct x={ref_states[ref_idx].x_au:.6f}, y={ref_states[ref_idx].y_au:.6f}')
        print(f'    interp x={interp["x_au"]:.6f}, y={interp["y_au"]:.6f}')
        print(f'    pos_err={pos_err:.2e} AU, vel_err={vel_err:.2e} AU/yr')

print(f'\nFirst segment: {len(all_pos_errors)} epochs evaluated')
print(f'Position errors: mean={np.mean(all_pos_errors):.2e}, median={np.median(all_pos_errors):.2e}')