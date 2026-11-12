import sys
sys.path.insert(0, 'src')
import os
os.chdir('E:\\rskmn\\Npersonal\\projects\\yr4\\final\\prototype-1\\physics-guided-orbit-discovery-prototype')
from orbit_discovery.cli.cmd_compare import cmd

# Test 1: Both --simulation and --observation (should fail)
print("Test 1: Both --simulation and --observation")
args = ['--simulation', 'data\\runs\\synthetic_asteroid\\trajectory.csv', '--observation', 'data\\observations\\synthetic_asteroid_observations\\observations.csv']
exit_code = cmd(args)
print(f'Exit code: {exit_code}\n')

# Test 2: Invalid mode
print("Test 2: Invalid mode")
args = ['--simulation', 'data\\runs\\synthetic_asteroid\\trajectory.csv', '--mode', 'invalid']
exit_code = cmd(args)
print(f'Exit code: {exit_code}\n')

# Test 3: Missing file
print("Test 3: Missing file")
args = ['--simulation', 'nonexistent.csv', '--mode', 'summary']
exit_code = cmd(args)
print(f'Exit code: {exit_code}\n')

# Test 4: No arguments
print("Test 4: No arguments")
args = []
exit_code = cmd(args)
print(f'Exit code: {exit_code}\n')

# Test 5: Help
print("Test 5: Help")
args = ['--help']
exit_code = cmd(args)
print(f'Exit code: {exit_code}\n')

# Test 6: Version
print("Test 6: Version")
args = ['--version']
exit_code = cmd(args)
print(f'Exit code: {exit_code}\n')