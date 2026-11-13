"""Quick test script for the orbit compare command."""
import sys
import os
import pathlib

# Add src to path
src_dir = pathlib.Path("src").resolve()
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from orbit_discovery.cli.cmd_compare import cmd

# Use absolute Windows paths
REPO_ROOT = pathlib.Path(r"E:\rskmn\Npersonal\projects\yr4\final\prototype-1\physics-guided-orbit-discovery-prototype").resolve()
TRAJECTORY_CSV = REPO_ROOT / "data/runs/synthetic_asteroid/trajectory.csv"
OBSERVATION_CSV = REPO_ROOT / "data/runs/synthetic_observations/trajectory.csv"  # may not exist

print(f"REPO_ROOT: {REPO_ROOT}")
print(f"TRAJECTORY_CSV exists: {TRAJECTORY_CSV.exists()}")
print()

# Test 1: Help
print("=== Test 1: Help ===")
result = cmd(["--help"])
print(f"Exit code: {result}\n")

# Test 2: Version
print("=== Test 2: Version ===")
result = cmd(["--version"])
print(f"Exit code: {result}\n")

# Test 3: No args (default to showing help info)
print("=== Test 3: No args ===")
result = cmd([])
print(f"Exit code: {result}\n")

# Test 4: --simulation with absolute path to existing file
print("=== Test 4: --simulation with absolute path ===")
result = cmd(["--simulation", str(TRAJECTORY_CSV)])
print(f"Exit code: {result}\n")

# Test 5: --observation (file may not exist - that's OK, we'll get a proper error)
print("=== Test 5: --observation ===")
result = cmd(["--observation", str(OBSERVATION_CSV)])
print(f"Exit code: {result}\n")

# Test 6: Both --simulation and --observation (should error)
print("=== Test 6: Both --simulation and --observation ===")
result = cmd(["--simulation", str(TRAJECTORY_CSV), "--observation", str(OBSERVATION_CSV)])
print(f"Exit code: {result}\n")

# Test 7: --mode summary
print("=== Test 7: --mode summary ===")
result = cmd(["--simulation", str(TRAJECTORY_CSV), "--mode", "summary"])
print(f"Exit code: {result}\n")

# Test 8: --mode residuals
print("=== Test 8: --mode residuals ===")
result = cmd(["--simulation", str(TRAJECTORY_CSV), "--mode", "residuals"])
print(f"Exit code: {result}\n")

# Test 9: --mode overlay
print("=== Test 9: --mode overlay ===")
result = cmd(["--simulation", str(TRAJECTORY_CSV), "--mode", "overlay"])
print(f"Exit code: {result}\n")

# Test 10: --project-root
print("=== Test 10: --project-root ===")
result = cmd(["--simulation", str(TRAJECTORY_CSV), "--project-root", str(REPO_ROOT), "--mode", "summary"])
print(f"Exit code: {result}\n")

# Test 11: --output-dir
print("=== Test 11: --output-dir ===")
result = cmd(["--simulation", str(TRAJECTORY_CSV), "--mode", "summary", "--output-dir", str(REPO_ROOT / "test_output")])
print(f"Exit code: {result}\n")