#!/usr/bin/env python3
import os

proj_dir = r"E:\rskmn\Npersonal\projects\yr4\final\prototype-1\physics-guided-orbit-discovery-prototype"
os.chdir(proj_dir)

# Read the current file
with open("src/orbit_discovery/core/orbital_elements.py", "r", encoding="utf-8", errors="replace") as f:
    lines = f.readlines()

# Find where the class definition ends and remove any extra content
# Keep lines from the start through the __hash__ method closing
new_lines = []
in_hash = False
hash_end_found = False

for i, line in enumerate(lines):
    if i >= 85 and i <= 95:  # __hash__ method area
        if 'return hash((' in line:
            in_hash = True
        if in_hash and line.strip() == ')' and i > 85:
            # Check if this is the hash closing by looking for ))
            # Actually, let's just keep lines up to and including line 93
            if i <= 93:
                new_lines.append(line)
            hash_end_found = True
            break
    new_lines.append(line)

# If we didn't find the hash end, just keep all lines
if not hash_end_found:
    new_lines = lines

# Write the cleaned file
with open("src/orbit_discovery/core/orbital_elements.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("Cleaned orbital_elements.py, kept", len(new_lines), "lines")