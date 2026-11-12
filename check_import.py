"""Check which module is imported."""
import sys
import os

src_dir = os.path.join(os.path.dirname(__file__), 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Check the cmd_compare module location
from orbit_discovery.cli import cmd_compare
print("Module file:", cmd_compare.__file__)
print("Module path:", os.path.abspath(cmd_compare.__file__))

# Check if it's the right file
expected = os.path.abspath("src/orbit_discovery/cli/cmd_compare.py")
print("Expected path:", expected)
print("Match:", cmd_compare.__file__ == expected)