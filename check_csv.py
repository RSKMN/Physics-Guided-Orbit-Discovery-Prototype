"""Check CSV reading."""
import pandas as pd
from pathlib import Path

# Try utf-16-le first
try:
    df = pd.read_csv(Path("data/runs/synthetic_asteroid/trajectory.csv"), encoding="utf-16-le")
    with open("csv_check_result.txt", "w") as f:
        f.write("utf-16-le: OK\n")
        f.write("Shape: " + str(df.shape) + "\n")
        f.write("Columns: " + str(list(df.columns)) + "\n")
except Exception as e:
    with open("csv_check_result.txt", "w") as f:
        f.write("utf-16-le: Error - " + str(e) + "\n")

# Try utf-16 next
try:
    df = pd.read_csv(Path("data/runs/synthetic_asteroid/trajectory.csv"), encoding="utf-16")
    with open("csv_check_result.txt", "a") as f:
        f.write("utf-16: OK\n")
        f.write("Shape: " + str(df.shape) + "\n")
        f.write("Columns: " + str(list(df.columns)) + "\n")
except Exception as e:
    with open("csv_check_result.txt", "a") as f:
        f.write("utf-16: Error - " + str(e) + "\n")