
import json
from pathlib import Path

import numpy as np
import pandas as pd
import rebound

import platform
from datetime import datetime, timezone
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]

# Approximate planetary masses in solar masses.
BODY_DATA = {
    "Mercury": {"mass": 1.6601e-7, "a": 0.3871},
    "Venus":   {"mass": 2.4478e-6, "a": 0.7233},
    "Earth":   {"mass": 3.0035e-6, "a": 1.0000},
    "Mars":    {"mass": 3.2272e-7, "a": 1.5237},
    "Jupiter": {"mass": 9.5458e-4, "a": 5.2028},
    "Saturn":  {"mass": 2.8581e-4, "a": 9.5388},
    "Uranus":  {"mass": 4.3662e-5, "a": 19.1914},
    "Neptune": {"mass": 5.1514e-5, "a": 30.0611},
}


def load_config(config_path):
    """Load a JSON configuration."""
    path = Path(config_path)

    if not path.is_absolute():
        path = ROOT / path

    with path.open("r", encoding="utf-8") as file:
        config = json.load(file)

    return config


def build_simulation(config):
    """Build a synthetic Sun-planet-asteroid simulation."""
    sim = rebound.Simulation()
    sim.units = ("yr", "AU", "Msun")

    sim.add(m=1.0)  # Sun at the origin

    requested_bodies = config["gravitational_bodies"]

    if "Sun" not in requested_bodies:
        raise ValueError("'Sun' must be included in gravitational_bodies.")

    for name in requested_bodies:
        if name == "Sun":
            continue

        if name not in BODY_DATA:
            raise ValueError(
                f"Unsupported gravitational body: {name}"
            )

        body = BODY_DATA[name]

        # Simplified circular, coplanar planetary initial conditions.
        sim.add(
            m=body["mass"],
            a=body["a"],
            e=0.0,
            inc=0.0,
        )

    # Add the massless asteroid using configured orbital elements.
    orbit = config["initial_conditions"]

    if orbit["mode"] != "orbital_elements":
        raise ValueError(
            "This version supports only orbital_elements mode. "
            "Horizons initialization will be added separately."
        )

    sim.add(
        m=0.0,
        a=float(orbit["semi_major_axis_au"]),
        e=float(orbit["eccentricity"]),
        inc=np.deg2rad(float(orbit["inclination_deg"])),
        Omega=np.deg2rad(
            float(orbit["longitude_ascending_node_deg"])
        ),
        omega=np.deg2rad(
            float(orbit["argument_periapsis_deg"])
        ),
        M=np.deg2rad(float(orbit["mean_anomaly_deg"])),
    )

    sim.move_to_com()

    settings = config["simulation"]

    if settings["integrator"].lower() != "ias15":
        raise ValueError("This version supports the IAS15 integrator.")

    sim.integrator = "ias15"
    sim.integrator.epsilon = float(settings["integrator_epsilon"])

    return sim


def save_trajectory_plot(df, output_dir, simulation_name):
    """Save a 2D orbit plot and a 3D trajectory plot."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 2D projection in the x-y plane
    fig, ax = plt.subplots(figsize=(8, 8))

    ax.plot(
        df["x_au"],
        df["y_au"],
        label="Asteroid trajectory",
        linewidth=1.2,
    )
    ax.scatter(0, 0, color="orange", s=100, label="Sun", zorder=3)

    ax.set_xlabel("Sun-relative X (AU)")
    ax.set_ylabel("Sun-relative Y (AU)")
    ax.set_title(f"{simulation_name} — XY projection")
    ax.set_aspect("equal", adjustable="datalim")
    ax.grid(True, alpha=0.3)
    ax.legend()

    fig.tight_layout()
    fig.savefig(output_dir / "trajectory_xy.png", dpi=160)
    plt.close(fig)

    # 3D trajectory
    fig = plt.figure(figsize=(9, 7))
    ax = fig.add_subplot(111, projection="3d")

    ax.plot(
        df["x_au"],
        df["y_au"],
        df["z_au"],
        label="Asteroid trajectory",
        linewidth=1.0,
    )
    ax.scatter(0, 0, 0, color="orange", s=70, label="Sun")

    ax.set_xlabel("X (AU)")
    ax.set_ylabel("Y (AU)")
    ax.set_zlabel("Z (AU)")
    ax.set_title(f"{simulation_name} — 3D trajectory")
    ax.legend()

    fig.tight_layout()
    fig.savefig(output_dir / "trajectory_3d.png", dpi=160)
    plt.close(fig)

    print(f"Saved plots: {output_dir}")


def generate_trajectory(config_path):
    """Generate and save one configurable asteroid trajectory."""
    config = load_config(config_path)
    sim = build_simulation(config)

    settings = config["simulation"]
    duration = float(settings["duration_years"])
    interval_days = float(settings["output_interval_days"])

    if duration <= 0 or interval_days <= 0:
        raise ValueError("Duration and output interval must be positive.")

    interval_years = interval_days / 365.25

    # Include the initial state and the final endpoint.
    times = list(np.arange(0.0, duration, interval_years))
    if not times or not np.isclose(times[0], 0.0):
        times.insert(0, 0.0)
    if not np.isclose(times[-1], duration):
        times.append(duration)
    else:
        times[-1] = duration

    asteroid_index = sim.N - 1
    rows = []

    for t in times:
        sim.integrate(float(t))

        asteroid = sim.particles[asteroid_index]
        sun = sim.particles[0]

        rows.append({
            "time_years": float(t),
            "time_days": float(t) * 365.25,
            "x_au": asteroid.x - sun.x,
            "y_au": asteroid.y - sun.y,
            "z_au": asteroid.z - sun.z,
            "vx_au_per_year": asteroid.vx - sun.vx,
            "vy_au_per_year": asteroid.vy - sun.vy,
            "vz_au_per_year": asteroid.vz - sun.vz,
        })

    df = pd.DataFrame(rows)

    if not np.isfinite(df.select_dtypes(include="number")).all().all():
        raise ValueError("Trajectory contains non-finite values.")

    output_config = config["output"]
    output_dir = ROOT / output_config["directory"]
    output_dir.mkdir(parents=True, exist_ok=True)

    df.to_csv(output_dir / "trajectory.csv", index=False)

    with (output_dir / "config.json").open(
        "w", encoding="utf-8"
    ) as file:
        json.dump(config, file, indent=4)

    print(f"Simulation: {config['simulation_name']}")
    print(f"Samples: {len(df)}")
    print(f"Duration: {duration} years")
    print(f"Saved trajectory: {output_dir / 'trajectory.csv'}")
    print(f"Saved configuration: {output_dir / 'config.json'}")
    
    if config["output"].get("save_plot", False):
        save_trajectory_plot(
            df,
            output_dir,
            config["simulation_name"],
        )
    metadata = {
        "simulation_name": config["simulation_name"],
        "run_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "rebound_version": rebound.__version__,
        "number_of_samples": len(df),
        "duration_years": duration,
        "output_interval_days": interval_days,
        "integrator": settings["integrator"],
        "integrator_epsilon": settings["integrator_epsilon"],
        "gravitational_bodies": config["gravitational_bodies"],
        "position_reference": "Sun-relative",
        "position_unit": "AU",
        "velocity_unit": "AU/year",
        "time_unit": "year",
        "initial_conditions": config["initial_conditions"],
        "coordinate_frame": "heliocentric_ecliptic",
        "epoch_jd_tdb": None,
        "state_type": "simulated_ground_truth",
        "massless_asteroid": True,
        "output_interval_days_requested": interval_days,
        "final_time_years": float(df["time_years"].iloc[-1]),
    }

    with (output_dir / "metadata.json").open(
        "w", encoding="utf-8"
    ) as file:
        json.dump(metadata, file, indent=4)
    return df


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "config",
        nargs="?",
        default="configs/synthetic_asteroid.json",
        help="Path to the simulation JSON configuration",
    )
    args = parser.parse_args()

    generate_trajectory(args.config)
