import os

# The project directory
base = r'E:\users\pc\AppData\Local\Programs\Python\Python313\python313.zip'

# Actually, let me just use absolute paths without raw strings
# Since we know the path from earlier

base = r'E:\rskmn\Npersonal\projects\yr4\final\physics-guided-orbit-discovery-prototype'

# Check parent directories
parents = [
    r'E:\rskmn\Npersonal\projects',
    r'E:\rskmn',
]

for parent in parents:
    # Check various backup names
    for suffix in ['-git', '-backup', '.git-bak', 'git']:
        alt = os.path.join(parent, 'physics-guided-orbit-discovery-prototype' + suffix)
        if os.path.exists(alt):
            print(f'Alternative backup at: {alt}')
    
    # Also just check if the project folder itself has a .git or git metadata
    git_dir = os.path.join(parent, '.git')
    if os.path.exists(git_dir):
        print(f'.git found at parent: {git_dir}')

# Check the /tmp directory for any git-related backups
import tempfile
tmp_dir = tempfile.gettempdir()
if os.path.exists(tmp_dir):
    for item in os.listdir(tmp_dir):
        item_lower = item.lower()
        if 'git' in item_lower or 'backup' in item_lower or 'physics' in item_lower or 'proj' in item_lower:
            full_path = os.path.join(tmp_dir, item)
            print(f'Temp item: {full_path}')
            # Check if it's a directory with .git
            if os.path.isdir(full_path):
                git_path = os.path.join(full_path, '.git')
                if os.path.exists(git_path):
                    print(f'  .git found in temp: {git_path}')

# Also check the current repo's possible backup locations
print()
print('Checking current repo structure:')
# List top-level items
for item in os.listdir(base):
    full = os.path.join(base, item)
    if os.path.isdir(full):
        # Check if it has .git
        git_path = os.path.join(full, '.git')
        if os.path.exists(git_path):
            print(f'  {item} has .git')

# Check if there's a .git in the root of the drive or common locations
for drive in ['E:', 'D:', 'C:']:
    git_dir = os.path.join(drive, '.git')
    if os.path.exists(git_dir):
        print(f'.git found at drive root: {git_dir}')