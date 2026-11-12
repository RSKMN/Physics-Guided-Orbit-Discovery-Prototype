import sys
sys.path.insert(0, 'src')
import os
os.chdir('E:\\rskmn\\Npersonal\\projects\\yr4\\final\\prototype-1\\physics-guided-orbit-discovery-prototype')
from orbit_discovery.cli.cmd_compare import cmd

# Test all modes for Component 1
print("=" * 60)
print("COMPONENT 1 TRAJECTORY COMPARISON")
print("=" * 60)

print("\n--- Mode: summary ---")
args = ['--simulation', 'data\\runs\\synthetic_asteroid\\trajectory.csv', '--mode', 'summary']
exit_code = cmd(args)
print(f'Exit code: {exit_code}\n')

print("--- Mode: residuals ---")
args = ['--simulation', 'data\\runs\\synthetic_asteroid\\trajectory.csv', '--mode', 'residuals']
exit_code = cmd(args)
print(f'Exit code: {exit_code}\n')

print("--- Mode: overlay ---")
args = ['--simulation', 'data\\runs\\synthetic_asteroid\\trajectory.csv', '--mode', 'overlay']
exit_code = cmd(args)
print(f'Exit code: {exit_code}\n')

# Test all modes for Component 2
print("=" * 60)
print("COMPONENT 2 OBSERVATION COMPARISON")
print("=" * 60)

print("\n--- Mode: summary ---")
args = ['--observation', 'data\\observations\\synthetic_asteroid_observations\\observations.csv', '--mode', 'summary']
exit_code = cmd(args)
print(f'Exit code: {exit_code}\n')

print("--- Mode: residuals ---")
args = ['--observation', 'data\\observations\\synthetic_asteroid_observations\\observations.csv', '--mode', 'residuals']
exit_code = cmd(args)
print(f'Exit code: {exit_code}\n')

print("--- Mode: overlay ---")
args = ['--observation', 'data\\observations\\synthetic_asteroid_observations\\observations.csv', '--mode', 'overlay']
exit_code = cmd(args)
print(f'Exit code: {exit_code}\n')