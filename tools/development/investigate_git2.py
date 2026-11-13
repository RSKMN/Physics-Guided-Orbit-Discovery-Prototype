import os

# Search for git-related files
search_locations = [
    r'E:\',
    r'C:\',
    r'D:\',
    r'C:\Users\pc\Downloads',
    r'C:\Users\pc\Documents',
    r'E:\Documents',
    r'E:\Backup',
]

found = []
for loc in search_locations:
    if not os.path.exists(loc):
        continue
    try:
        for root, dirs, files in os.walk(loc, maxdepth=2):
            for f in files:
                if '.git' in f.lower() or 'bundle' in f.lower() or 'pack' in f.lower() or 'HEAD' in f:
                    full = os.path.join(root, f)
                    found.append(full)
    except:
        pass

print(f'Found {len(found)} git-related files')
for f in found[:20]:
    print(f'  {f}')
"