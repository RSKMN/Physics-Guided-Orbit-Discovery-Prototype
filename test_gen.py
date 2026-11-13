import sys
sys.path.insert(0, 'src')
from pathlib import Path
from orbit_discovery.component2_observations import generator
import pandas as pd
import json
import tempfile

tmp = Path(tempfile.mkdtemp())

# Write a proper trajectory with time columns
traj_path = tmp / 'trajectory.csv'
df = pd.DataFrame({
    'time_years': [0.0, 0.25],
    'time_days': [0.0, 91.3125],
    'x_au': [1.0, 1.02],
    'y_au': [0.5, 0.52],
    'z_au': [0.1, 0.11],
    'vx_au_per_year': [0.01, 0.01],
    'vy_au_per_year': [0.02, 0.02],
    'vz_au_per_year': [0.003, 0.003],
})
df.to_csv(traj_path, index=False)

# Write config - save_noise_free_coordinates True
config_path = tmp / 'observations.json'
config = {
    'observation_name': 'test_obs',
    'input_trajectory': str(traj_path),
    'observer': {
        'model': 'idealized_circular',
        'orbital_radius_au': 1.0,
        'orbital_period_years': 1.0,
        'initial_phase_deg': 90.0,
    },
    'coordinates': {
        'input_frame': 'heliocentric_ecliptic',
        'output_frame': 'equatorial',
        'obliquity_deg': 23.43928,
        'ra_unit': 'degrees',
        'dec_unit': 'degrees',
    },
    'observation_schedule': {
        'cadence_days': 2.0,
        'start_day': 0.0,
        'end_day': 2.0,
    },
    'measurement_noise': {
        'model': 'gaussian',
        'sigma_ra_cosdec_arcsec': 0.5,
        'sigma_dec_arcsec': 0.5,
        'random_seed': 42,
    },
    'output': {
        'directory': str(tmp / 'output'),
        'save_noise_free_coordinates': True,
        'save_metadata': True,
    },
}
with open(config_path, 'w') as f:
    json.dump(config, f, indent=4)

obs, meta = generator.generate_observations(config_path)

print('=== With save_noise_free_coordinates=True ===')
print('Observation columns:', list(obs.columns))
print('Ground truth in obs? true_ra_deg in columns:', 'true_ra_deg' in obs.columns)
print('Ground truth in obs? true_dec_deg in columns:', 'true_dec_deg' in obs.columns)
print()

# Check the output directory
output_dir = tmp / 'output' / 'test_obs'
print('Output directory contents:')
for f in sorted(output_dir.iterdir()):
    print(f'  {f.name}: is_file={f.is_file()}')

# Read observations CSV
obs_csv = pd.read_csv(output_dir / 'observations.csv')
print()
print('Observations CSV columns:', list(obs_csv.columns))
print('Ground truth columns in CSV:', [c for c in obs_csv.columns if 'true' in c.lower()])

# Read ground truth JSON
if (output_dir / 'ground_truth.json').exists():
    gt = json.load(open(output_dir / 'ground_truth.json'))
    print(f'\nGround truth JSON: {len(gt)} records')
    print(f'First record keys: {list(gt[0].keys())}')
    print(f'First true_ra_deg: {gt[0]["true_ra_deg"]}')
    print(f'First true_dec_deg: {gt[0]["true_dec_deg"]}')

# Now test with save_noise_free_coordinates=False
print('\n\n=== With save_noise_free_coordinates=False ===')
config2_path = tmp / 'observations2.json'
config2 = dict(config)
config2['output'] = dict(config['output'])
config2['output']['save_noise_free_coordinates'] = False
with open(config2_path, 'w') as f:
    json.dump(config2, f, indent=4)

obs2, meta2 = generator.generate_observations(config2_path)
print('Observation columns:', list(obs2.columns))
print('Ground truth in obs? true_ra_deg in columns:', 'true_ra_deg' in obs2.columns)
print('Ground truth in obs? true_dec_deg in columns:', 'true_dec_deg' in obs2.columns)
output_dir2 = tmp / 'output' / 'test_obs2'
# clean and regenerate
import shutil
if output_dir2.exists():
    shutil.rmtree(output_dir2)
obs2, meta2 = generator.generate_observations(config2_path)
print('Output directory2 contents:')
for f in sorted(output_dir2.iterdir()):
    print(f'  {f.name}: is_file={f.is_file()}')
if (output_dir2 / 'observations.csv').exists():
    obs2_csv = pd.read_csv(output_dir2 / 'observations.csv')
    print('Observations CSV2 columns:', list(obs2_csv.columns))
    print('Ground truth columns in CSV2:', [c for c in obs2_csv.columns if 'true' in c.lower()])