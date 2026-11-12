"""Check actual CSV column names."""
import sys
import os
src_dir = os.path.join(os.path.dirname(__file__), 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from pathlib import Path
import pandas as pd

# Read the CSV
path = Path(r"E:\rskmn\Npersonal\projects\yr4\final\prototype-1\physics-guided-orbit-discovery-prototype\data\runs\synthetic_asteroid\trajectory.csv")

# Read with utf-16-le
df = pd.read_csv(path, encoding="utf-16-le")

# Write column names to file
with open("csv_cols.txt", "w") as f:
    f.write("ENCODING: utf-16-le\n")
    f.write("COLUMNS: " + str(list(df.columns)) + "\n")
    f.write("NUM COLUMNS: " + str(len(df.columns)) + "\n")
    f.write("SHAPE: " + str(df.shape) + "\n")
    # Write first 3 rows
    f.write("FIRST 3 ROWS:\n")
    for _, row in df.head(3).iterrows():
        f.write("  " + str(row.values) + "\n")