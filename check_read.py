"""Check CSV column reading directly."""
import sys
import os
src_dir = os.path.join(os.path.dirname(__file__), 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from pathlib import Path
import pandas as pd

# Read CSV directly, bypassing the module
path = Path(r"E:\rskmn\Npersonal\projects\yr4\final\prototype-1\physics-guided-orbit-discovery-prototype\data\runs\synthetic_asteroid\trajectory.csv")
df = pd.read_csv(path, encoding="utf-16-le")

print("Direct read columns:", list(df.columns))
print("Number of columns:", len(df.columns))

# Now try through the module
from orbit_discovery.cli.cmd_compare import _read_trajectory_csv
df2 = _read_trajectory_csv(path)
print("Module read columns:", list(df2.columns))
print("Module read num columns:", len(df2.columns))