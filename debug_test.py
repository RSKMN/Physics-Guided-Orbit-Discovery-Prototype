import subprocess
import os

env = {**os.environ, 'PYTHONPATH': 'src'}
result = subprocess.run(
    ['python', '-m', 'pytest', 'tests/test_component2_generator.py::ObservationGenerationTests::test_generation_contract_and_reference_values', '-v', '--tb=long'],
    cwd='E:\\rskmn\\Npersonal\\projects\\yr4\\final\\prototype-1\\physics-guided-orbit-discovery-prototype',
    env=env,
    capture_output=True, text=True, timeout=60
)
print('=== STDOUT ===')
print(result.stdout)
print('=== STDERR ===')
print(result.stderr)
print('=== RC ===')
print(result.returncode)