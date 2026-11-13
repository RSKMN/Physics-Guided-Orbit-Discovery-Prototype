import sys
sys.path.insert(0, 'src')
from orbit_discovery.component2_observations import generator
from pathlib import Path
import json

# Regenerate each dataset
configs = [
    ('configs/synthetic_observations.json', 'synthetic_asteroid_observations'),
    ('configs/synthetic_observations_inclined.json', 'synthetic_asteroid_inclined_observations'),
    ('configs/synthetic_observations_eccentric.json', 'synthetic_asteroid_eccentric_observations'),
]

for config_path, dataset_name in configs:
    p = Path(config_path)
    print('Regenerating ' + dataset_name + '...')
    try:
        obs, meta = generator.generate_observations(p)
        obs_name = meta['observation_name']
        n_obs = meta['number_of_observations']
        print('  OK: ' + obs_name + ', ' + str(n_obs) + ' obs')
    except Exception as e:
        print('  ERROR: ' + str(e))

print()
print('Regeneration complete.')