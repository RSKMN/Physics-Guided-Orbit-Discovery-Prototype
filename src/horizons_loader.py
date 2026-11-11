
from astroquery.jplhorizons import Horizons
import numpy as np


# All masses are approximate, in solar masses.
# Horizons supplies state vectors; we supply the masses.
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


def load_horizons_states(epoch_jd, bodies=None):
    """
    Download Sun-relative Cartesian states from JPL Horizons.

    Parameters
    ----------
    epoch_jd : float
        Julian Date in the TDB time scale.
    bodies : list[str] or None
        Names from BODY_CONFIG. Defaults to all configured bodies.

    Returns
    -------
    dict
        Body names mapped to mass, position and velocity.
        Position units: AU.
        Velocity units: AU/year.
        Frame: ecliptic, Sun-centered origin.
    """
    if bodies is None:
        bodies = list(BODY_CONFIG.keys())

    states = {}

    for name in bodies:
        if name not in BODY_CONFIG:
            raise ValueError(f"Unknown body: {name}")

        config = BODY_CONFIG[name]

        query = Horizons(
            id=config["id"],
            location="@sun",
            epochs=epoch_jd,
        )

        vectors = query.vectors(refplane="ecliptic")
        row = vectors[0]

        # Horizons vector velocities are in AU/day.
        # REBOUND uses years, AU and solar masses.
        velocity_conversion = 365.25

        state = {
            "mass": config["mass"],
            "x": float(row["x"]),
            "y": float(row["y"]),
            "z": float(row["z"]),
            "vx": float(row["vx"]) * velocity_conversion,
            "vy": float(row["vy"]) * velocity_conversion,
            "vz": float(row["vz"]) * velocity_conversion,
            "epoch_jd_tdb": float(epoch_jd),
            "origin": "Sun",
            "reference_plane": "ecliptic",
        }

        numeric = [
            state[k]
            for k in ("x", "y", "z", "vx", "vy", "vz")
        ]

        if not np.isfinite(numeric).all():
            raise ValueError(f"Invalid state returned for {name}")

        states[name] = state
        print(
            f"Loaded {name}: "
            f"position=({state['x']:.6f}, "
            f"{state['y']:.6f}, {state['z']:.6f}) AU"
        )

    return states
