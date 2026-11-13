import sys
sys.path.insert(0, 'src')
from pathlib import Path
from orbit_discovery.component2_observations.c3_loader import load_observation_dataset
import pandas as pd
import json, tempfile

tmp = Path(tempfile.mkdtemp())

# Write trajectory
traj_path = tmp / 'trajectory.csv'
df_traj = pd.DataFrame({
    'time_years': [0.0, 0.25, 0.5],
    'time_days': [0.0, 91.3125, 182.625],
    'x_au': [1.0, 1.01, 1.02],
    'y_au': [0.5, 0.51, 0.52],
    'z_au': [0.1, 0.11, 0.12],
    'vx_au_per_year': [0.01]*3,
    'vy_au_per_year': [0.02]*3,
    'vz_au_per_year': [0.003]*3,
})
df_traj.to_csv(traj_path, index=False)

# Write config
config_path = tmp / 'observations.json'
config = {
    'observation_name': 'test_obs',
    'input_trajectory': str(traj_path),
    'observer': {'model': 'idealized_circular', 'orbital_radius_au': 1.0, 'orbital_period_years': 1.0, 'initial_phase_deg': 90.0},
    'coordinates': {'input_frame': 'heliocentric_ecliptic', 'output_frame': 'equatorial', 'obliquity_deg': 23.43928, 'ra_unit': 'degrees', 'dec_unit': 'degrees'},
    'observation_schedule': {'cadence_days': 2.0, 'start_day': 0.0, 'end_day': 6.0},
    'measurement_noise': {'model': 'gaussian', 'sigma_ra_cosdec_arcsec': 0.5, 'sigma_dec_arcsec': 0.5, 'random_seed': 42},
    'output': {'directory': str(tmp / 'output'), 'save_noise_free_coordinates': True, 'save_metadata': True},
}
with open(config_path, 'w') as f: json.dump(config, f, indent=4)

from orbit_discovery.component2_observations import generator
obs, meta = generator.generate_observations(config_path)

# Test 1: C3 loader works with clean observation CSV
csv_path = tmp / 'output' / 'test_obs' / 'observations.csv'
data = load_observation_dataset(csv_path)
print('Test 1: C3 loader works with clean observation CSV: PASS')
print(f'  No truth in result: {\"true_ra_deg\" not in data}')

# Test 2: Validator catches forbidden columns (simulate old format)
from orbit_discovery.component2_observations.schema import V2_FORBIDDEN
df_with_truth = pd.read_csv(csv_path)
found = set(df_with_truth.columns) & V2_FORBIDDEN
has_forbidden = len(found) > 0
print(f'Test 2: Forbidden columns detected: {\"true_ra_deg\" in found}')
print(f'  Forbidden columns found: {found}')

# Test 3: C3 loader with ground truth CSV should raise error
# Create a CSV with truth columns
csv_with_truth = tmp / 'output' / 'test_obs_with_truth' / 'observations.csv'
csv_with_truth.parent.mkdir(parents=True, exist_ok=True)
df_truth = pd.DataFrame({
    'obs_id': [0, 1, 2],
    'time_years': [0.0, 0.25, 0.5],
    'time_days': [0.0, 91.3125, 182.625],
    'ra_deg': [333.5, 336.3, 338.9],
    'dec_deg': [-5.5, -4.2, -3.1],
    'sigma_ra_cosdec_arcsec': [0.5, 0.5, 0.5],
    'sigma_dec_arcsec': [0.5, 0.5, 0.5],
    'true_ra_deg': [333.5, 336.3, 338.9],  # forbidden!
    'true_dec_deg': [-5.5, -4.2, -3.1],  # forbidden!
})
df_truth.to_csv(csv_with_truth, index=False)

try:
    data = load_observation_dataset(csv_with_truth)
    print('Test 3: FAIL - should have raised ValueError for forbidden columns')
except ValueError as e:
    print(f'Test 3: C3 loader rejects CSV with truth columns: PASS')
    print(f'  Error: {e}')

print()
print('All C3 loader tests completed.')