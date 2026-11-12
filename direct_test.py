"""Direct test of file type detection."""
import sys
import os

# Ensure src is on path
src_dir = os.path.join(os.path.dirname(__file__), 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from pathlib import Path
import pandas as pd

from orbit_discovery.cli.cmd_compare import _read_trajectory_csv, _detect_file_type

# Read the trajectory CSV directly
path = Path(r"E:\rskmn\Npersonal\projects\yr4\final\prototype-1\physics-guided-orbit-discovery-prototype\data\runs\synthetic_asteroid\trajectory.csv")
df = _read_trajectory_csv(path)

# Write column info to a file
with open("direct_debug.txt", "w") as f:
    lines = []
    lines.append("COLUMNS:")
    for c in df.columns:
        lines.append(f"  {c}")
    lines.append("")
    lines.append(f"NUM COLUMNS: {len(df.columns)}")
    lines.append("")
    col_set = set(df.columns)
    lines.append(f"'time_years' in col_set: {('time_years' in col_set)}")
    lines.append(f"'x_au' in col_set: {('x_au' in col_set)}")
    lines.append(f"'y_au' in col_set: {('y_au' in col_set)}")
    lines.append(f"'z_au' in col_set: {('z_au' in col_set)}")
    lines.append(f"'vx_au_per_year' in col_set: {('vx_au_per_year' in col_set)}")
    lines.append(f"'vy_au_per_year' in col_set: {('vy_au_per_year' in col_set)}")
    lines.append(f"'vz_au_per_year' in col_set: {('vz_au_per_year' in col_set)}")
    lines.append(f"'ra_deg' in col_set: {('ra_deg' in col_set)}")
    lines.append(f"'dec_deg' in col_set: {('dec_deg' in col_set)}")
    lines.append("")
    # C1 score
    c1_cols = {"time_years", "time_days", "x_au", "y_au", "z_au",
               "vx_au_per_year", "vy_au_per_year", "vz_au_per_year"}
    c1_score = len(col_set.intersection(c1_cols))
    lines.append(f"C1 score (intersection with {len(c1_cols)} cols): {c1_score}")
    lines.append(f"is_c1 (time_years in col and score >= 3): {('time_years' in col_set and c1_score >= 3)}")
    # C2 score
    c2_cols = {"time_years", "ra_deg", "dec_deg", "true_ra_deg",
               "true_dec_deg", "sigma_ra_cosdec_arcsec", "sigma_dec_arcsec",
               "number_of_observations"}
    c2_score = len(col_set.intersection(c2_cols))
    lines.append(f"C2 score (intersection with {len(c2_cols)} cols): {c2_score}")
    lines.append(f"is_c2 (time_years in col and score >= 2): {('time_years' in col_set and c2_score >= 2)}")
    lines.append("")
    # Now detect file type
    ft = _detect_file_type(df)
    lines.append(f"_detect_file_type result: {ft}")
    lines.append("")
    
    f.write("\n".join(lines))