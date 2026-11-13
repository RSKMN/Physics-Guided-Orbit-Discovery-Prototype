import sys
sys.path.insert(0, 'src')
from pathlib import Path
from orbit_discovery.component2_observations.c5_loader import load_ground_truth_dataset
import json, tempfile, shutil

tmp = Path(tempfile.mkdtemp())

# Create a ground truth JSON file
gt_data = [
    {
        'obs_id': 0,
        'true_ra_deg': 333.502884,
        'true_dec_deg': -5.477114,
        'x_au': 1.0,
        'y_au': 0.5,
        'z_au': 0.1,
        'vx_au_per_year': 0.01,
        'vy_au_per_year': 0.02,
        'vz_au_per_year': 0.003,
    },
    {
        'obs_id': 1,
        'true_ra_deg': 336.262888,
        'true_dec_deg': -4.244672,
        'x_au': 1.02,
        'y_au': 0.52,
        'z_au': 0.11,
        'vx_au_per_year': 0.01,
        'vy_au_per_year': 0.02,
        'vz_au_per_year': 0.003,
    },
]

with open(tmp / 'ground_truth.json', 'w') as f:
    json.dump(gt_data, f, indent=4)

# Test 1: Load ground truth dataset
data = load_ground_truth_dataset(tmp / 'ground_truth.json')
print('Test 1: Load ground truth dataset PASSED')
print(f'  Number of records: {len(data["obs_id"])}')
print(f'  Columns: {list(data.keys())}')
print(f'  First true RA: {data["true_ra_deg"][0]:.4f} deg')
print(f'  First true Dec: {data["true_dec_deg"][0]:.4f} deg')
print(f'  First x_au: {data["x_au"][0]:.4f} AU')
print(f'  First vx_au_per_year: {data["vx_au_per_year"][0]:.4f} AU/yr')

# Test 2: FileNotFoundError for missing file
try:
    load_ground_truth_dataset(tmp / 'nonexistent.json')
    print('Test 2: FAIL - should have raised FileNotFoundError')
except FileNotFoundError as e:
    print('Test 2: FileNotFoundError PASSED')

# Test 3: Duplicate IDs detected
bad_data = [
    {'obs_id': 0, 'true_ra_deg': 1.0, 'true_dec_deg': 2.0, 'x_au': 3.0, 'y_au': 4.0, 'z_au': 5.0, 'vx_au_per_year': 0.1, 'vy_au_per_year': 0.2, 'vz_au_per_year': 0.3},
    {'obs_id': 0, 'true_ra_deg': 1.0, 'true_dec_deg': 2.0, 'x_au': 3.0, 'y_au': 4.0, 'z_au': 5.0, 'vx_au_per_year': 0.1, 'vy_au_per_year': 0.2, 'vz_au_per_year': 0.3},
]
bad_path = tmp / 'bad_gt.json'
with open(bad_path, 'w') as f:
    json.dump(bad_data, f, indent=4)
try:
    load_ground_truth_dataset(bad_path)
    print('Test 3: FAIL - should have raised ValueError for duplicate IDs')
except ValueError as e:
    print('Test 3: Duplicate ID detection PASSED:', str(e)[:50])

shutil.rmtree(tmp)
print()
print('All C5 loader tests completed successfully.')