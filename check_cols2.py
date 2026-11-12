"""Check actual CSV column names - write to file."""
import pandas as pd
from pathlib import Path

df = pd.read_csv(Path(r"E:\rskmn\Npersonal\projects\yr4\final\prototype-1\physics-guided-orbit-discovery-prototype\data\runs\synthetic_asteroid\trajectory.csv"), encoding="utf-16-le")

# Write results
with open(r"E:\rskmn\Npersonal\projects\yr4\final\prototype-1\physics-guided-orbit-discovery-prototype\csv_cols_result.txt", "w", encoding="utf-8") as f:
    f.write("COLUMNS:\n")
    for c in df.columns:
        f.write(f"  {c}\n")
    f.write(f"\nNUM COLUMNS: {len(df.columns)}\n")
    f.write(f"SHAPE: {df.shape}\n")
    f.write("\nFIRST 3 ROWS:\n")
    for _, row in df.head(3).iterrows():
        f.write(f"  {list(row.values)}\n")