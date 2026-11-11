
from pathlib import Path

import numpy as np
import pandas as pd
import rebound


# ---------------------------------------------
# 1. Configuration
# ---------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = PROJECT_ROOT / "data" / "trajectory_two_body.csv"

A = 2.5
E = 0.2
DURATION = 5.0
SAMPLES = 5001

EXPECTED_PERIOD = np.sqrt(A**3)
EXPECTED_PERIHELION = A * (1 - E)
EXPECTED_APHELION = A * (1 + E)


# ---------------------------------------------
# 2. Test the existing saved dataset
# ---------------------------------------------

print("\nTEST 1: Existing dataset integrity")

df = pd.read_csv(CSV_PATH)

required_columns = [
    "time_yr", "x_AU", "y_AU", "z_AU",
    "vx_AU_per_yr", "vy_AU_per_yr", "vz_AU_per_yr"
]

assert all(col in df.columns for col in required_columns), \
    "Missing required columns."

assert len(df) == 1000, \
    f"Expected 1000 rows, got {len(df)}."

assert df[required_columns].notna().all().all(), \
    "Missing values found."

values = df[required_columns].to_numpy(dtype=float)

assert np.isfinite(values).all(), \
    "NaN or infinite values found."

assert np.all(np.diff(df["time_yr"]) > 0), \
    "Timestamps are not strictly increasing."

print("PASS: Required columns, row count, timestamps,")
print("      and numerical values are valid.")


# ---------------------------------------------
# 3. Check orbital shape and distances
# ---------------------------------------------

print("\nTEST 2: Orbital geometry")

radius = np.sqrt(
    df["x_AU"]**2
    + df["y_AU"]**2
    + df["z_AU"]**2
)

r_min = radius.min()
r_max = radius.max()

print(f"Expected perihelion: {EXPECTED_PERIHELION:.4f} AU")
print(f"Measured minimum:    {r_min:.4f} AU")
print(f"Expected aphelion:   {EXPECTED_APHELION:.4f} AU")
print(f"Measured maximum:    {r_max:.4f} AU")

assert abs(r_min - EXPECTED_PERIHELION) < 0.01, \
    "Perihelion is outside the expected tolerance."

assert abs(r_max - EXPECTED_APHELION) < 0.01, \
    "Aphelion is outside the expected tolerance."

print("PASS: Sampled distances match the expected orbit.")


# ---------------------------------------------
# 4. Create a simulation for convergence tests
# ---------------------------------------------

def run_simulation(epsilon, A, E, DURATION, SAMPLES):
    sim = rebound.Simulation()
    sim.units = ("yr", "AU", "Msun")

    # Add the primary star
    sim.add(m=1.0)
    
    # Add the test particle (asteroid)
    sim.add(
        m=0.0,
        a=A,
        e=E,
        inc=0.0,
        primary=sim.particles[0],
    )

    # Configure IAS15 precision
    sim.integrator = "ias15"
    sim.integrator.epsilon = epsilon
    
    # Crucial step: Shift particles to the Center of Mass frame
    sim.move_to_com()

    times = np.linspace(0.0, DURATION, SAMPLES)
    positions = []
    distances = []

    # Store initial state at t=0
    star = sim.particles[0]
    asteroid = sim.particles[1]
    
    positions.append([asteroid.x, asteroid.y, asteroid.z])
    # Relative distance ensures accuracy even if the star wobbles slightly
    distances.append(np.sqrt((asteroid.x - star.x)**2 + 
                             (asteroid.y - star.y)**2 + 
                             (asteroid.z - star.z)**2))

    # Integrate sequentially for remaining timesteps
    for t in times[1:]:
        sim.integrate(t)
        
        # Capture positions relative to the frame
        positions.append([asteroid.x, asteroid.y, asteroid.z])
        
        # Measure distance explicitly relative to the star
        distances.append(np.sqrt((asteroid.x - star.x)**2 + 
                                 (asteroid.y - star.y)**2 + 
                                 (asteroid.z - star.z)**2))

    return times, np.array(positions), np.array(distances)

# ---------------------------------------------
# 5. Estimate the orbital period
# ---------------------------------------------

def estimate_period(times, distances):
    # Find the first local minimum after the initial perihelion.
    # This approximates the time of the next perihelion.
    minima = np.where(
        (distances[1:-1] < distances[:-2])
        & (distances[1:-1] < distances[2:])
    )[0] + 1

    minima = minima[times[minima] > 0.1]

    if len(minima) == 0:
        raise RuntimeError(
            "No subsequent perihelion detected. "
            "Increase the simulation duration."
        )

    return times[minima[0]]


print("\nTEST 3: Kepler's third law")

times, positions, distances = run_simulation(
    1e-9, A, E, DURATION, SAMPLES
)

measured_period = estimate_period(times, distances)
period_error = abs(
    measured_period - EXPECTED_PERIOD
) / EXPECTED_PERIOD * 100

print(f"Theoretical period: {EXPECTED_PERIOD:.6f} years")
print(f"Measured period:    {measured_period:.6f} years")
print(f"Relative error:     {period_error:.4f}%")

# Sampling-based period estimate: 0.1% tolerance.
assert period_error < 0.1, \
    "Measured orbital period differs too much from theory."

print("PASS: The measured period agrees with Kepler's law.")


# ---------------------------------------------
# 6. Compare integration accuracy settings
# ---------------------------------------------

print("\nTEST 4: Numerical convergence")

times_tight, positions_tight, _ = run_simulation(
    1e-12, A, E, DURATION, SAMPLES
)

position_errors = np.linalg.norm(
    positions - positions_tight,
    axis=1,
)

max_position_error = position_errors.max()

print("IAS15 epsilon 1e-9 vs 1e-12")
print(f"Maximum position difference: "
      f"{max_position_error:.16e} AU")

assert np.isfinite(position_errors).all(), \
    "Non-finite position differences found."

assert max_position_error < 1e-5, \
    "Position difference exceeds the chosen tolerance."

print("PASS: The trajectories agree within the chosen tolerance.")


# ---------------------------------------------
# 7. Final result
# ---------------------------------------------

print("\nAll baseline validation tests passed.")
