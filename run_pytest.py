import subprocess
import os

env = {**os.environ, 'PYTHONPATH': 'src'}
result = subprocess.run(
    ['python', '-m', 'pytest', 'tests/test_trajectory_loader.py', 'tests/test_component2_generator.py', '-v', '--tb=short'],
    cwd='E:\\rskmn\\Npersonal\\projects\\yr4\\final\\prototype-1\\physics-guided-orbit-discovery-prototype',
    env=env,
    capture_output=True, text=True, timeout=120
)
print('=== STDOUT ===')
print(result.stdout[:5000])
print('=== STDERR ===')
print(result.stderr[:2000] if result.stderr else '')
print('=== RETURN CODE ===')
print(result.returncode)