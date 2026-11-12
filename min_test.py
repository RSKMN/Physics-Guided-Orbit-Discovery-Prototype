"""Minimal test of file type detection."""
import sys
import os

src_dir = os.path.join(os.path.dirname(__file__), 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from pathlib import Path
import pandas as pd

from orbit_discovery.cli.cmd_compare import _read_trajectory_csv, _detect_file_type

path = Path(r"E:\rskmn\Npersonal\projects\yr4\final\prototype-1\physics-guided-orbit-discovery-prototype\data\runs\synthetic_asteroid\trajectory.csv")
df = _read_trajectory_csv(path)
col_set = set(df.columns)

print('time_years in col_set:', 'time_years' in col_set)
print('x_au in col_set:', 'x_au' in col_set)
print('y_au in col_set:', 'y_au' in col_set)
print('z_au in col_set:', 'z_au' in col_set)

c1_cols = {'time_years', 'time_days', 'x_au', 'y_au', 'z_au',
           'vx_au_per_year', 'vy_au_per_year', 'vz_au_per_year'}
c1_score = len(col_set.intersection(c1_cols))
print('C1 score:', c1_score)
print('is_c1:', 'time_years' in col_set and c1_score >= 3)

c2_cols = {'time_years', 'ra_deg', 'dec_deg', 'true_ra_deg',
           'true_dec_deg', 'sigma_ra_cosdec_arcsec', 'sigma_dec_arcsec',
           'number_of_observations'}
c2_score = len(col_set.intersection(c2_cols))
print('C2 score:', c2_score)
print('is_c2:', 'time_years' in col_set and c2_score >= 2)

ft = _detect_file_type(df)
print('File type:', ft)