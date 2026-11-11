
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import rebound
from astroquery.jplhorizons import Horizons


# Make the src directory importable.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from horizons_loader import load_horizons_states


# ---------------------------------------------
# 1. Configuration
# ---------------------------------------------

EPOCH_JD = 2460676.5  # 2025-01-01 00:00 TDB
DAYS_PER_YEAR = 365.25

PLANETS = ["Mercury", "Venus", "Earth", "Mars", "Jupiter"]
ASTEROID = "Eros"

# Validate at the initial epoch and future epochs.
CHECK_YEARS = [0, 1, 2, 3, 4, 5]


# ---------------------------------------------
# 2. Load the initial Horizons states
# ---------------------------------------------

states = load_horizons_states(
    EPOCH_JD,
    PLANETS + [ASTEROID],
)


# ---------------------------------------------
# 3. Initialize the REBOUND system
# ---------------------------------------------

sim = rebound.Simulation()
sim.units = ("yr", "AU", "Msun")

# The loaded states are Sun-relative.
sim.add(m=1.0)

for name in PLANETS + [ASTEROID]:
    s = states[name]

    sim.add(
        m=s["mass"],
        x=s["x"],
        y=s["y"],
        z=s["z"],
        vx=s["vx"],
        vy=s["vy"],
        vz=s["vz"],
    )

sim.move_to_com()
sim.integrator = "ias15"

sun = sim.particles[0]
asteroid_index = 1 + len(PLANETS)


# ---------------------------------------------
# 4. Propagate and compare with Horizons
# ---------------------------------------------

results = []

for year in CHECK_YEARS:
    # REBOUND time is measured in years.
    sim_time_years = float(year)

    sim.integrate(sim_time_years)

    # Matching Horizons epoch, in Julian Date TDB.
    target_jd = EPOCH_JD + year * DAYS_PER_YEAR

    sun = sim.particles[0]
    asteroid = sim.particles[asteroid_index]

    # REBOUND heliocentric position in AU.
    simulated_position = np.array([
        asteroid.x - sun.x,
        asteroid.y - sun.y,
        asteroid.z - sun.z,
    ])

    

    query = Horizons(
        id="433",
        location="@sun",
        epochs=target_jd,
    )

    reference = query.vectors(refplane="ecliptic")[0]

    reference_position = np.array([
        float(reference["x"]),
        float(reference["y"]),
        float(reference["z"]),
    ])

    error_vector = simulated_position - reference_position
    error_au = np.linalg.norm(error_vector)
    error_km = error_au * 149597870.7

    results.append({
        "years_after_epoch": year,
        "epoch_jd_tdb": target_jd,
        "error_AU": error_au,
        "error_km": error_km,
    })

    print(
        f"Year {year}: "
        f"position error = {error_au:.8e} AU "
        f"({error_km:,.2f} km)"
    )


# ---------------------------------------------
# 5. Save the validation report
# ---------------------------------------------

df = pd.DataFrame(results)

output_path = ROOT / "data" / "eros_horizons_validation.csv"
df.to_csv(output_path, index=False)

print("\nHorizons comparison completed.")
print(df.to_string(index=False))
print(f"\nResults saved to: {output_path}")
