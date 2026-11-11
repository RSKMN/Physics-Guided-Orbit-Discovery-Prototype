
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import rebound
from astroquery.jplhorizons import Horizons

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from horizons_loader import load_horizons_states

EPOCH_JD = 2460676.5
DAYS_PER_YEAR = 365.25
PLANETS = [
    "Mercury", "Venus", "Earth", "Mars",
    "Jupiter", "Saturn", "Uranus", "Neptune",
]
ASTEROID = "Eros"
CHECK_YEARS = [0, 1, 2, 3, 4, 5]

states = load_horizons_states(EPOCH_JD, PLANETS + [ASTEROID])

sim = rebound.Simulation()
sim.units = ("yr", "AU", "Msun")
sim.add(m=1.0)  # Sun

for name in PLANETS + [ASTEROID]:
    s = states[name]
    sim.add(
        m=s["mass"],
        x=s["x"], y=s["y"], z=s["z"],
        vx=s["vx"], vy=s["vy"], vz=s["vz"],
    )

sim.move_to_com()
sim.integrator = "ias15"
sim.integrator.epsilon = 1e-12

sun_index = 0
eros_index = 1 + len(PLANETS)
results = []

for year in CHECK_YEARS:
    # REBOUND time is in years.
    sim.integrate(float(year))

    sun = sim.particles[sun_index]
    eros = sim.particles[eros_index]

    simulated_position = np.array([
        eros.x - sun.x,
        eros.y - sun.y,
        eros.z - sun.z,
    ])

    target_jd = EPOCH_JD + year * DAYS_PER_YEAR
    reference = Horizons(
        id="433",
        location="@sun",
        epochs=target_jd,
    ).vectors(refplane="ecliptic")[0]

    reference_position = np.array([
        float(reference["x"]),
        float(reference["y"]),
        float(reference["z"]),
    ])

    error_au = np.linalg.norm(simulated_position - reference_position)
    error_km = error_au * 149597870.7

    results.append({
        "years_after_epoch": year,
        "epoch_jd_tdb": target_jd,
        "position_error_au": error_au,
        "position_error_km": error_km,
    })

    print(
        f"Year {year}: {error_au:.8e} AU "
        f"({error_km:,.2f} km)"
    )

output = ROOT / "data" / "eros_horizons_8planets_validation.csv"
pd.DataFrame(results).to_csv(output, index=False)

print(f"\nSaved validation report: {output}")
