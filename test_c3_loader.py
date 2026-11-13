import sys
sys.path.insert(0, 'src')
from pathlib import Path
from orbit_discovery.component2_observations.c3_loader import load_observation_dataset
import pandas as pd
import json
import tempfile

tmp = Path(tempfile.mkdtemp())

# Write trajectory
traj_path = tmp / 'trajectory.csv'
df = pd.DataFrame({
    'time_years': [0.0, 0.25, 0.5],
    'time_days': [0.0, 91.3125, 182.625],
    'x_au': [1.0, 1.01, 1.02],
    'y_au': [0.5, 0.51, 0.52],
    'z_au': [0.1, 0.11, 0.12],
    'vx_au_per_year': [0.01]*3,
    'vy_au_per_year': [0.02]*3,
    'vz_au_per_year': [0.003]*3,
})
df.to_csv(traj_path, index=False)

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
with open(config_path, 'w') as f:
    json.dump(config, f, indent=4)

from orbit_discovery.component2_observations import generator
obs, meta = generator.generate_observations(config_path)

# Now test the C3 loader
csv_path = tmp / 'output' / 'test_obs' / 'observations.csv'
data = load_observation_dataset(csv_path)
print('C3 Loader test PASSED')
print(f'Number of observations: {len(data["obs_id"])}')
print(f'Columns in result: {list(data.keys())}')
print(f'RA range: {data["ra_deg"][0]:.4f} to {data["ra_deg"][-1]:.4f} deg')
print(f'Dec range: {data["dec_deg"][0]:.4f} to {data["dec_deg"][-1]:.4f} deg')
print(f'No truth columns in result: {"true_ra_deg" not in data and "true_dec_deg" not in data}')
print()
# Test that forbidden columns raise error
try:
    load_observation_dataset(csv_path)  # Should work fine
    print('Validation passed (no forbidden columns)')
except Exception as e:
    print(f'Validation error (unexpected): {e}')