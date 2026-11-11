
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import rebound
from astroquery.jplhorizons import Horizons


# ==================================================
# 1. Configuration
# ==================================================

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from horizons_loader import load_horizons_states

EPOCH_JD = 2460676.5       # 2025-01-01 00:00 TDB
DAYS_PER_YEAR = 365.25
AU_KM = 149597870.7

# Short intervals reveal whether the error starts early.
CHECK_DAYS = [0, 1, 7, 30, 90, 180, 365]

# Existing model and expanded model.
FIVE_PLANETS = [
    "Mercury", "Venus", "Earth", "Mars", "Jupiter"
]

EIGHT_PLANETS = [
    "Mercury", "Venus", "Earth", "Mars",
    "Jupiter", "Saturn", "Uranus", "Neptune"
]

BODY_CONFIG = {
    "Mercury": {"id": "199", "mass": 1.6601e-7},
    "Venus":   {"id": "299", "mass": 2.4478e-6},
    "Earth":   {"id": "399", "mass": 3.0035e-6},
    "Mars":    {"id": "499", "mass": 3.2272e-7},
    "Jupiter": {"id": "599", "mass": 9.5458e-4},
    "Saturn":  {"id": "699", "mass": 2.8581e-4},
    "Uranus":  {"id": "799", "mass": 4.3662e-5},
    "Neptune": {"id": "899", "mass": 5.1514e-5},
    "Eros":    {"id": "433", "mass": 0.0},
}


# ==================================================
# 2. Query one body's Horizons state
# ==================================================

def query_horizons_state(body_name, epoch_jd):
    """Return heliocentric ecliptic state at a specified JD."""

    body = BODY_CONFIG[body_name]

    result = Horizons(
        id=body["id"],
        location="@sun",
        epochs=float(epoch_jd),
    ).vectors(refplane="ecliptic")

    row = result[0]

    return np.array([
        float(row["x"]),
        float(row["y"]),
        float(row["z"]),
        float(row["vx"]) * DAYS_PER_YEAR,
        float(row["vy"]) * DAYS_PER_YEAR,
        float(row["vz"]) * DAYS_PER_YEAR,
    ])


# ==================================================
# 3. Initial-state consistency
# ==================================================

print("\nTEST 1: Initial-state consistency")

initial_states = load_horizons_states(
    EPOCH_JD,
    EIGHT_PLANETS + ["Eros"],
)

initial_errors = []

for name in EIGHT_PLANETS + ["Eros"]:
    expected = query_horizons_state(name, EPOCH_JD)
    loaded = initial_states[name]

    actual = np.array([
        loaded["x"], loaded["y"], loaded["z"],
        loaded["vx"], loaded["vy"], loaded["vz"],
    ])

    error = np.linalg.norm(actual - expected)
    initial_errors.append(error)

    print(f"{name:8s}: state-vector difference = {error:.3e}")

print("Maximum initial state difference:",
      f"{max(initial_errors):.3e}")


# ==================================================
# 4. Build a REBOUND simulation from real states
# ==================================================

def build_simulation(planet_names, epsilon=1e-12):
    sim = rebound.Simulation()
    sim.units = ("yr", "AU", "Msun")

    # States are heliocentric: Sun is initially at origin.
    sim.add(m=1.0)

    for name in planet_names + ["Eros"]:
        s = initial_states[name]

        sim.add(
            m=BODY_CONFIG[name]["mass"],
            x=s["x"],
            y=s["y"],
            z=s["z"],
            vx=s["vx"],
            vy=s["vy"],
            vz=s["vz"],
        )

    # Translate all bodies consistently into the COM frame.
    sim.move_to_com()

    sim.integrator = "ias15"
    sim.integrator.epsilon = epsilon

    return sim


# ==================================================
# 5. Propagate to each requested time
# ==================================================

def propagate_model(planet_names, epsilon=1e-12):
    sim = build_simulation(planet_names, epsilon)
    asteroid_index = 1 + len(planet_names)

    results = []

    for day in CHECK_DAYS:
        # REBOUND uses years; Horizons epoch is in JD.
        sim.integrate(day / DAYS_PER_YEAR)

        sun = sim.particles[0]
        asteroid = sim.particles[asteroid_index]

        simulated = np.array([
            asteroid.x - sun.x,
            asteroid.y - sun.y,
            asteroid.z - sun.z,
            asteroid.vx - sun.vx,
            asteroid.vy - sun.vy,
            asteroid.vz - sun.vz,
        ])

        # Request a reference state at the matching epoch.
        jd = EPOCH_JD + day
        reference = query_horizons_state("Eros", jd)

        position_error = np.linalg.norm(
            simulated[:3] - reference[:3]
        )
        velocity_error = np.linalg.norm(
            simulated[3:] - reference[3:]
        )

        results.append({
            "model": ",".join(planet_names),
            "epsilon": epsilon,
            "days_after_epoch": day,
            "epoch_jd_tdb": jd,
            "position_error_AU": position_error,
            "position_error_km": position_error * AU_KM,
            "velocity_error_AU_per_year": velocity_error,
        })

    return results


# ==================================================
# 6. Compare five-planet and eight-planet models
# ==================================================

print("\nTEST 2: Five planets versus eight planets")

results = []

for model_name, planets in [
    ("five_planets", FIVE_PLANETS),
    ("eight_planets", EIGHT_PLANETS),
]:
    print(f"\nRunning model: {model_name}")

    model_results = propagate_model(planets)
    results.extend(model_results)

    for row in model_results:
        print(
            f"Day {row['days_after_epoch']:3d}: "
            f"position error = "
            f"{row['position_error_AU']:.6e} AU "
            f"({row['position_error_km']:,.1f} km)"
        )


# ==================================================
# 7. Numerical convergence
# ==================================================

print("\nTEST 3: IAS15 convergence")

# Compare the eight-planet model with two tolerances.
tight_results = propagate_model(EIGHT_PLANETS, epsilon=1e-13)

results.extend(tight_results)

base_results = [
    r for r in results
    if r["model"] == ",".join(EIGHT_PLANETS)
    and r["epsilon"] == 1e-12
]

for base, tight in zip(base_results, tight_results):
    print(
        f"Day {base['days_after_epoch']:3d}: "
        f"epsilon 1e-12 vs 1e-13, "
        f"reference errors = "
        f"{base['position_error_AU']:.6e} vs "
        f"{tight['position_error_AU']:.6e} AU"
    )


# ==================================================
# 8. Save all diagnostics
# ==================================================

output = ROOT / "data" / "eros_diagnostics.csv"
pd.DataFrame(results).to_csv(output, index=False)

print("\nDiagnostics finished.")
print(f"Results saved to: {output}")
