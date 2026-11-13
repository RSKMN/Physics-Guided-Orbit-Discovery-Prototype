import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
os.chdir('E:\\rskmn\\Npersonal\\projects\\yr4\\final\\prototype-1\\physics-guided-orbit-discovery-prototype')

# Run the trajectory loader test
from tests.test_trajectory_loader import *
print("test_trajectory_loader imports OK")

from tests.test_component2_generator import *
print("test_component2_generator imports OK")