"""Debug _detect_file_type and _read_trajectory_csv."""
import sys
import os
import pandas as pd
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from orbit_discovery.cli.cmd_compare import _read_trajectory_csv, _detect_file_type

# Read the trajectory CSV
path = Path(r"E:\rskmn\Npersonal\projects\yr4\final\prototype-1\physics-guided-orbit-discovery-prototype\data\runs\synthetic_asteroid\trajectory.csv")
df = _read_trajectory_csv(path)

# Write results to file directly
with open("debug_results.txt", "w") as f:
    f.write("Columns: " + str(list(df.columns)) + "\n")
    
    file_type = _detect_file_type(df)
    f.write("Detected file type: " + str(file_type) + "\n")
    
    col_set = set(df.columns)
    f.write("col_set: " + str(col_set) + "\n")
    
    f.write("'time_years' in col_set: " + str("time_years" in col_set) + "\n")
    f.write("'x_au' in col_set: " + str("x_au" in col_set) + "\n")
    f.write("'vx_au_per_year' in col_set: " + str("vx_au_per_year" in col_set) + "\n")
    f.write("'y_au' in col_set: " + str("y_au" in col_set) + "\n")
    f.write("'z_au' in col_set: " + str("z_au" in col_set) + "\n")
    f.write("'ra_deg' in col_set: " + str("ra_deg" in col_set) + "\n")
    f.write("'dec_deg' in col_set: " + str("dec_deg" in col_set) + "\n")
    
    intersection = {"x_au", "y_au", "z_au"}.intersection(col_set)
    f.write("intersection: " + str(intersection) + "\n")
    f.write("bool(intersection): " + str(bool(intersection)) + "\n")
    
    has_c1 = (
        "time_years" in col_set
        and (
            "x_au" in col_set
            or "vx_au_per_year" in col_set
            or {"x_au", "y_au", "z_au"}.intersection(col_set)
        )
    )
    has_c2 = (
        "time_years" in col_set
        and (
            "ra_deg" in col_set
            or "dec_deg" in col_set
            or {"ra_deg", "dec_deg"}.intersection(col_set)
        )
    )
    f.write("has_component1_cols: " + str(has_c1) + "\n")
    f.write("has_component2_cols: " + str(has_c2) + "\n")