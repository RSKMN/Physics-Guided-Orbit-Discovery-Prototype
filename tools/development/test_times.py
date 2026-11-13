#!/usr/bin/env python3
import sys
sys.path.insert(0, 'src')
import numpy as np
from orbit_discovery.component2_observations.loader import load_trajectory

traj = load_trajectory('data/runs/synthetic_asteroid/trajectory.csv')
times = np.asarray(traj['time_years'], dtype=float)
print(f'times[0] = {times[0]:.10f}')
print(f'times[1] = {times[1]:.10f}')
print(f'times[2] = {times[2]:.10f}')
print(f'times[100] = {times[100]:.10f}')
print(f'times[500] = {times[500]:.10f}')
print(f'times[999] = {times[999]:.10f}')
print(f'times[1000] = {times[1000]:.10f}')
print()

# Check the searchsorted behavior
t_eval = 0.006  # between samples 1 and 2
ref_idx = int(np.searchsorted(times, t_eval, side="right") - 1)
print(f't_eval = {t_eval:.6f}')
print(f'ref_idx = {ref_idx}, t_ref = {times[ref_idx]:.6f}')

t_eval2 = 0.050  # between samples 10 and 11
ref_idx2 = int(np.searchsorted(times, t_eval2, side="right") - 1)
print(f't_eval2 = {t_eval2:.6f}')
print(f'ref_idx2 = {ref_idx2}, t_ref = {times[ref_idx2]:.6f}')