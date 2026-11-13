import subprocess
import sys

# Test 1: GeneratorSignatureAndConstantTests::test_absolute_config_path_is_preserved
result = subprocess.run(
    [sys.executable, '-m', 'pytest', 
     'tests/test_component2_generator.py::GeneratorSignatureAndConstantTests::test_absolute_config_path_is_preserved',
     '-v', '--tb=short'],
    capture_output=True, text=True,
    cwd='E:\\rskmn\\Npersonal\\projects\\yr4\\final\\prototype-1\\physics-guided-orbit-discovery-prototype'
)
print("="*60)
print("TEST 1: test_absolute_config_path_is_preserved")
print("="*60)
print(result.stdout)
if result.stderr:
    print("STDERR:")
    print(result.stderr)
print(f"Return code: {result.returncode}")
print()

# Test 2: test_generation_contract_and_reference_values
result2 = subprocess.run(
    [sys.executable, '-m', 'pytest', 
     'tests/test_component2_generator.py::ObservationGenerationTests::test_generation_contract_and_reference_values',
     '-v', '--tb=short'],
    capture_output=True, text=True,
    cwd='E:\\rskmn\\Npersonal\\projects\\yr4\\final\\prototype-1\\physics-guided-orbit-discovery-prototype'
)
print("="*60)
print("TEST 2: test_generation_contract_and_reference_values")
print("="*60)
print(result2.stdout)
if result2.stderr:
    print("STDERR:")
    print(result2.stderr)
print(f"Return code: {result2.returncode}")
print()

# Test 3: test_legacy_module_help_exits_successfully
result3 = subprocess.run(
    [sys.executable, '-m', 'pytest', 
     'tests/test_component2_generator.py::CompatibilityTests::test_legacy_module_help_exits_successfully',
     '-v', '--tb=short'],
    capture_output=True, text=True,
    cwd='E:\\rskmn\\Npersonal\\projects\\yr4\\final\\prototype-1\\physics-guided-orbit-discovery-prototype'
)
print("="*60)
print("TEST 3: test_legacy_module_help_exits_successfully")
print("="*60)
print(result3.stdout)
if result3.stderr:
    print("STDERR:")
    print(result3.stderr)
print(f"Return code: {result3.returncode}")