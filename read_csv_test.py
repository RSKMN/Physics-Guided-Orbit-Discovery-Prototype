import pandas as pd
import os

os.chdir('E:\\rskmn\\Npersonal\\projects\\yr4\\final\\prototype-1\\physics-guided-orbit-discovery-prototype')

# Try reading the synthetic asteroid trajectory CSV
df = pd.read_csv('data/runs/synthetic_asteroid/trajectory.csv', encoding='utf-16-le')
print('Columns:', list(df.columns))
print('Shape:', df.shape)
print(df.head())
print()
print('dtypes:', df.dtypes.to_dict())