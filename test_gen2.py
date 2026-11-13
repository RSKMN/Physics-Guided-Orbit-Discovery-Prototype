import sys
sys.path.insert(0, 'src')
from pathlib import Path
from orbit_discovery.component2_observations import generator
import pandas as pd
import json
import tempfile

tmp = Path(tempfile.mkdtemp())

# Write trajectory with 6 samples
traj_path = tmp / 'trajectory.csv'
df = pd.DataFrame({
    'time_years': [0.0, 0.25, 0.5, 1.0, 1.5, 2.0],
    'time_days': [0.0, 91.3125, 182.625, 365.25, 547.875, 730.5],
    'x_au': [1.0, 1.01, 1.02, 1.04, 1.05, 1.06],
    'y_au': [0.5, 0.51, 0.52, 0.53, 0.54, 0.55],
    'z_au': [0.1, 0.11, 0.12, 0.13, 0.14, 0.15],
    'vx_au_per_year': [0.01]*6,
    'vy_au_per_year': [0.02]*6,
    'vz_au_per_year': [0.003]*6,
})
df.to_csv(traj_path, index=False)

# Write config - save_noise_free_coordinates True
config_path = tmp / 'observations.json'
config = {
    'observation_name': 'test_obs',
    'input_trajectory': str(traj_path),
    'observer': {'model': 'idealized_circular', 'orbital_radius_au': 1.0, 'orbital_period_years': 1.0, 'initial_phase_deg': 90.0},
    'coordinates': {'input_frame': 'heliocentric_ecliptic', 'output_frame': 'equatorial', 'obliquity_deg': 23.43928, 'ra_unit': 'degrees', 'dec_unit': 'degrees'},
    'observation_schedule': {'cadence_days': 2.0, 'start_day': 0.0, 'end_day': 12.0},
    'measurement_noise': {'model': 'gaussian', 'sigma_ra_cosdec_arcsec': 0.5, 'sigma_dec_arcsec': 0.5, 'random_seed': 42},
    'output': {'directory': str(tmp / 'output'), 'save_noise_free_coordinates': True, 'save_metadata': True},
}
with open(config_path, 'w') as f:
    json.dump(config, f, indent=4)

obs, meta = generator.generate_observations(config_path)
print('Success!')
print('Observation columns:', list(obs.columns))
print('true_ra_deg in columns:', 'true_ra_deg' in obs.columns)
print('true_dec_deg in columns:', 'true_dec_deg' in obs.columns)

# Check output directory
output_dir = tmp / 'output' / 'test_obs'
print()
print('Output files:')
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
    print(f'Ground truth JSON: {len(gt)} records')
    first = gt[0]
    print(f'First record keys: {list(first.keys())}')
    print(f'First true_ra_deg: {first["true_ra_deg"]}')
    print(f'First true_dec_deg: {first["true_dec_deg"]}')
    print(f'First x_au: {first["x_au"]}')
    print(f'First vx_au_per_year: {first["vx_au_per_year"]}')