import os, hashlib

# Inspect /tmp/baseline_sync/
print('=== /tmp/baseline_sync/ contents ===')
baseline_dir = '/tmp/baseline_sync'
if os.path.exists(baseline_dir):
    for item in sorted(os.listdir(baseline_dir)):
        full_path = os.path.join(baseline_dir, item)
        size = os.path.getsize(full_path)
        with open(full_path, 'rb') as f:
            first2 = f.read(2)
        is_utf16 = first2[:2] == b'\xff\xfe'
        is_utf8_bom = first2[:3] == b'\xef\xbb\xbf'
        encoding = 'UTF-16 LE' if is_utf16 else ('UTF-8 BOM' if is_utf8_bom else 'other')
        print(f'  {item}: {size} bytes, {encoding}')

print()

# The 9 restored files and their baseline mappings
restored_files = [
    (r'data/runs/synthetic_asteroid/config.json', 'config.json'),
    (r'data/runs/synthetic_asteroid/metadata.json', 'metadata.json'),
    (r'data/runs/synthetic_asteroid/trajectory.csv', 'trajectory.csv'),
    (r'data/runs/synthetic_asteroid_eccentric/config.json', 'eccentric_config.json'),
    (r'data/runs/synthetic_asteroid_eccentric/metadata.json', 'eccentric_metadata.json'),
    (r'data/runs/synthetic_asteroid_eccentric/trajectory.csv', 'eccentric_trajectory.csv'),
    (r'data/runs/synthetic_asteroid_inclined/config.json', 'inclined_config.json'),
    (r'data/runs/synthetic_asteroid_inclined/metadata.json', 'inclined_metadata.json'),
    (r'data/runs/synthetic_asteroid_inclined/trajectory.csv', 'inclined_trajectory.csv'),
]

print()
print('=== SHA-256 hashes: restored vs baseline ===')

for rpath, bl_name in restored_files:
    # Read restored file
    with open(rpath, 'rb') as fh:
        rdata = fh.read()
    # All files are UTF-16 LE per baseline directory inspection
    rdata = rdata.decode('utf-16-le')
    rhash = hashlib.sha256(rdata.encode()).hexdigest()
    
    # Read baseline file
    bl_path = os.path.join(baseline_dir, bl_name)
    with open(bl_path, 'rb') as fh:
        bdata = fh.read()
    bdata = bdata.decode('utf-16-le')
    bhash = hashlib.sha256(bdata.encode()).hexdigest()
    
    match = rhash == bhash
    
    basename = os.path.basename(rpath)
    print(f'  {basename:30s} restored={rhash[:16]}... baseline={bhash[:16]}... {"MATCH" if match else "MISMATCH"}')