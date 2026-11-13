#!/usr/bin/env python3
import os

proj_dir = r"E:\rskmn\Npersonal\projects\yr4\final\prototype-1\physics-guided-orbit-discovery-prototype"
os.chdir(proj_dir)

# Read the file
with open("src/orbit_discovery/core/orbital_elements.py", "r", encoding="utf-8", errors="replace") as f:
    content = f.read()

# Remove the circular orbit early return section
# Find the section starting from "# Handle circular orbit special case" to the next "# --- Position:"
start_marker = "# Handle circular orbit special case"
end_marker = "--- Position:"

# Find the start
start_idx = content.find(start_marker)
if start_idx >= 0:
    # Find the end marker after the start
    end_idx = content.find(end_marker, start_idx)
    if end_idx >= 0:
        # Remove the section including the markers
        # Also remove the blank line after if present
        section_end = end_idx + len(end_marker)
        # Check if there's a blank line after
        if section_end < len(content) and content[section_end] == "\n":
            section_end += 1
        # Also skip another blank line if present
        if section_end < len(content) and content[section_end] == "\n":
            section_end += 1
        
        content = content[:start_idx] + content[section_end:]
        print("Removed circular orbit section from", start_idx, "to", section_end)
    else:
        print("Could not find end marker")
else:
    print("Could not find start marker")

# Write the file back
with open("src/orbit_discovery/core/orbital_elements.py", "w", encoding="utf-8") as f:
    f.write(content)

print("File written successfully")