import subprocess
import sys

result = subprocess.run(
    [sys.executable, '-m', 'pytest', 'tests/', '--tb=line'],
    capture_output=True, text=True,
    cwd='E:\\rskmn\\Npersonal\\projects\\yr4\\final\\prototype-1\\physics-guided-orbit-discovery-prototype'
)

lines = result.stdout.splitlines()
passed = sum(1 for l in lines if 'PASSED' in l)
failed = sum(1 for l in lines if 'FAILED' in l)
skipped = sum(1 for l in lines if 'SKIPPED' in l)

print(f'Passed: {passed}')
print(f'Failed: {failed}')
print(f'Skipped: {skipped}')
print()
print('Failed tests:')
failed_tests = [l for l in lines if 'FAILED' in l]
for l in failed_tests:
    print('  ' + l)