import subprocess
import sys

tests_to_run = [
    'tests/test_component2_generator.py::ObservationGenerationTests::test_metadata_output_can_be_disabled',
    'tests/test_component2_generator.py::ObservationGenerationTests::test_noise_free_coordinates_can_be_disabled',
    'tests/test_component2_generator.py::MetadataTests::test_metadata_keys_values_and_absolute_paths',
]

for test_path in tests_to_run:
    result = subprocess.run(
        [sys.executable, '-m', 'pytest', test_path, '-v', '--tb=short'],
        capture_output=True, text=True,
        cwd='E:\\rskmn\\Npersonal\\projects\\yr4\\final\\prototype-1\\physics-guided-orbit-discovery-prototype'
    )
    print("="*60)
    print(f"TEST: {test_path}")
    print("="*60)
    print(result.stdout)
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
    print(f"Return code: {result.returncode}")
    print()