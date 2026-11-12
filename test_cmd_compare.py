import sys
sys.path.insert(0, 'src')
import os
os.chdir('E:\\rskmn\\Npersonal\\projects\\yr4\\final\\prototype-1\\physics-guided-orbit-discovery-prototype')
from orbit_discovery.cli.cmd_compare import cmd

# Test 1: Component 1 trajectory comparison with summary mode
print("Test 1: Component 1 trajectory comparison with summary mode")
args = ['--simulation', 'data\\runs\\synthetic_asteroid\\trajectory.csv', '--mode', 'summary']
exit_code = cmd(args)
print(f'Exit code: {exit_code}')
print()

# Test 2: Component 2 observation comparison with summary mode
print("Test 2: Component 2 observation comparison with summary mode")
args = ['--observation', 'data\\observations\\synthetic_asteroid_observations\\observations.csv', '--mode', 'summary']
exit_code = cmd(args)
print(f'Exit code: {exit_code}')