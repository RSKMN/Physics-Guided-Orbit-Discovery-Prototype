import subprocess, hashlib, os

files = [
    'data/runs/synthetic_asteroid/config.json',
    'data/runs/synthetic_asteroid/metadata.json',
    'data/runs/synthetic_asteroid/trajectory.csv',
    'data/runs/synthetic_asteroid_eccentric/config.json',
    'data/runs/synthetic_asteroid_eccentric/metadata.json',
    'data/runs/synthetic_asteroid_eccentric/trajectory.csv',
    'data/runs/synthetic_asteroid_inclined/config.json',
    'data/runs/synthetic_asteroid_inclined/metadata.json',
    'data/runs/synthetic_asteroid_inclined/trajectory.csv',
]

print('Restored file SHA-256 hashes:')
print('=' * 70)

cwd = r'E:\rskmn\Npersonal\projects\yr4\final\physics-guided-orbit-discovery-prototype'

for f in files:
    # Get hash from baseline commit
    result = subprocess.run(
        ['git', 'rev-parse', 'd02023d:' + f],
        capture_output=True, text=True, cwd=cwd
    )
    baseline_hash = hashlib.sha256(result.stdout.encode()).hexdigest()
    
    # Get hash from working tree
    with open(f, 'rb') as fh:
        working_hash = hashlib.sha256(fh.read()).hexdigest()
    
    match = 'MATCH' if baseline_hash == working_hash else 'MISMATCH'
    print(f'{os.path.basename(f):35s} baseline={baseline_hash[:16]}... working={working_hash[:16]}... {match}')

print('=' * 70)