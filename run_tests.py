import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
os.chdir('E:\\rskmn\\Npersonal\\projects\\yr4\\final\\prototype-1\\physics-guided-orbit-discovery-prototype')

# Discover and run tests
loader = unittest.TestLoader()
suite = loader.discover('tests', pattern='test_*.py')

runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(suite)

# Exit with error code if there were failures
sys.exit(0 if result.wasSuccessful() else 1)