"""Debug script to check CSV column names."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import pandas as pd
from pathlib import Path

# Test reading the synthetic_asteroid trajectory
path = Path("data/runs/synthetic_asteroid/trajectory.csv")

# Try different encodings
for encoding in ["utf-16-le", "utf-16", "utf-8"]:
    try:
        df = pd.read_csv(path, encoding=encoding)
        print(f"Encoding: {encoding}")
        print(f"Columns: {list(df.columns)}")
        print(f"Shape: {df.shape}")
        print(f"First 2 rows:")
        print(df.head(2))
        print()
    except Exception as e:
        print(f"Encoding {encoding}: Error - {e}")
        print()