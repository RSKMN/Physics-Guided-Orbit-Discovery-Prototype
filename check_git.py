import subprocess
result = subprocess.run(
    ['git', 'diff', '--stat'],
    cwd='E:\\rskmn\\Npersonal\\projects\\yr4\\final\\prototype-1\\physics-guided-orbit-discovery-prototype',
    capture_output=True, text=True
)
print('Git diff stat:')
print(result.stdout)
if result.stderr:
    print('Stderr:', result.stderr)