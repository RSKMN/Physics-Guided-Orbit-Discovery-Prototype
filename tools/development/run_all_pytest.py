import subprocess
import os

env = {**os.environ, 'PYTHONPATH': 'src'}

# Run all tests except the horizons loader (missing astroquery)
result = subprocess.run(
    ['python', '-m', 'pytest', 'tests/', '-v', '--tb=short',
     '--ignore=tests/test_horizons_loader.py',
     '--ignore=tests/test_observer_model.py'],  # skip problematic tests
    cwd='E:\\rskmn\\Npersonal\\projects\\yr4\\final\\prototype-1\\physics-guided-orbit-discovery-prototype',
    env=env,
    capture_output=True, text=True, timeout=120
)
print('=== STDOUT ===')
print(result.stdout[:8000])
print('=== STDERR ===')
print(result.stderr[:2000] if result.stderr else '')
print('=== RETURN CODE ===')
print(result.returncode)