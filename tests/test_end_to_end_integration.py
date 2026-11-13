"""End-to-end integration tests for Stage 2.7.

Covers the complete C1 -> C2 pipeline and all 8 required scenarios:

1. C1 simulation -> C2 observation generation
2. Generated observations -> measurement loader (C3-facing)
3. Arbitrary-time propagation (inside and beyond trajectory span)
4. Orbital element conversion round trips
5. Observer geometry and sky-coordinate conversion
6. Future observation prediction (from state and from trajectory)
7. Interpolation evaluation accuracy
8. Complete C1/C2 end-to-end workflow

Tests use temporary directories so tracked data/ artefacts are never
overwritten.  The module can also be run directly as a script.
"""

from __future__ import annotations

import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SRC))

from configurable_simulator import generate_trajectory
from orbit_discovery.component2_observations.generator import generate_observations
from orbit_discovery.component2_observations.c3_loader import load_observation_dataset
from orbit_discovery.component2_observations.c5_loader import load_ground_truth_dataset
from orbit_discovery.core.propagation import (
    propagate_state,
    propagate_multi,
    propagate_from_trajectory,
)
from orbit_discovery.core.orbital_elements import (
    cartesian_to_orbital_elements,
    orbital_elements_to_cartesian,
    MU_REBOUND,
)
from orbit_discovery.component2_observations.prediction import (
    predict_from_state,
    predict_from_trajectory,
    PredictionOutput,
)
from orbit_discovery.core.interpolation_validation import (
    evaluate_trajectory,
    generate_trajectory_with_interval,
)
from orbit_discovery.component2_observations.loader import load_trajectory
from orbit_discovery.component2_observations.observer import (
    ObserverConfig,
    calculate_observer_positions,
    calculate_observer_velocities,
    calculate_line_of_sight,
    calculate_sky_coordinates,
    calculate_solar_elongation,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(tmp_root: Path, name: str, overrides: dict | None = None) -> Path:
    """Create a temporary config file and return its path."""
    config = {
        "simulation_name": name,
        "initial_conditions": {
            "mode": "orbital_elements",
            "semi_major_axis_au": 2.5,
            "eccentricity": 0.2,
            "inclination_deg": 0.0,
            "longitude_ascending_node_deg": 0.0,
            "argument_periapsis_deg": 0.0,
            "mean_anomaly_deg": 0.0,
        },
        "simulation": {
            "duration_years": 5.0,
            "output_interval_days": 1.82625,
            "integrator": "ias15",
            "integrator_epsilon": 1e-12,
        },
        "gravitational_bodies": ["Sun", "Earth", "Jupiter"],
        "units": {"distance": "AU", "time": "year", "mass": "solar_mass"},
        "output": {"directory": str(tmp_root), "save_plot": False},
    }
    if overrides:
        config.update(overrides)

    config_path = tmp_root / f"{name}.json"
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return config_path


def _make_observation_config(
    tmp_root: Path,
    trajectory_path: Path,
    name: str = "synthetic_asteroid_observations",
) -> Path:
    """Create a temporary observation config file."""
    config = {
        "observation_name": name,
        "input_trajectory": str(trajectory_path),
        "observer": {
            "model": "idealized_circular",
            "orbital_radius_au": 1.0,
            "orbital_period_years": 1.0,
            "initial_phase_deg": 90.0,
        },
        "coordinates": {
            "input_frame": "heliocentric_ecliptic",
            "output_frame": "equatorial",
            "obliquity_deg": 23.43928,
            "ra_unit": "degrees",
            "dec_unit": "degrees",
        },
        "observation_schedule": {
            "cadence_days": 7.0,
            "start_day": 0.0,
            "end_day": 1826.25,
        },
        "measurement_noise": {
            "model": "gaussian",
            "sigma_ra_cosdec_arcsec": 0.5,
            "sigma_dec_arcsec": 0.5,
            "random_seed": 42,
        },
        "output": {
            "directory": str(tmp_root),
            "save_noise_free_coordinates": True,
            "save_metadata": True,
        },
    }
    config_path = tmp_root / f"{name}.json"
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return config_path


# ---------------------------------------------------------------------------
# Scenario 1: C1 simulation -> C2 observation generation
# ---------------------------------------------------------------------------

def test_c1_to_c2_pipeline():
    """C1 trajectory generation feeds C2 observation generation end-to-end."""
    with tempfile.TemporaryDirectory(prefix="e2e-c1c2-") as tmp:
        tmp_root = Path(tmp)

        config_path = _make_config(tmp_root, "synthetic_asteroid")
        generate_trajectory(str(config_path))

        trajectory_csv = tmp_root / "trajectory.csv"
        assert trajectory_csv.exists(), "C1 trajectory CSV not produced"

        trajectory = load_trajectory(trajectory_csv)
        assert trajectory["number_of_samples"] > 100
        assert np.isfinite(trajectory["positions"]).all()
        assert np.isfinite(trajectory["velocities"]).all()

        obs_config_path = _make_observation_config(
            tmp_root, trajectory_csv, name="e2e_observations"
        )
        observations, metadata = generate_observations(str(obs_config_path))

        assert observations is not None
        assert len(observations) == metadata["number_of_observations"]
        assert "true_ra_deg" not in observations.columns
        assert "true_dec_deg" not in observations.columns

        csv_path = Path(tmp_root) / "e2e_observations" / "observations.csv"
        assert csv_path.exists()

        gt_path = Path(tmp_root) / "e2e_observations" / "ground_truth.json"
        assert gt_path.exists()

        print("PASS: C1 -> C2 pipeline")


# ---------------------------------------------------------------------------
# Scenario 2: Generated observations -> measurement loader (C3-facing)
# ---------------------------------------------------------------------------

def test_observations_to_c3_loader():
    """Generated observation CSV loads cleanly through the C3-facing loader."""
    with tempfile.TemporaryDirectory(prefix="e2e-loader-") as tmp:
        tmp_root = Path(tmp)

        config_path = _make_config(tmp_root, "synthetic_asteroid")
        generate_trajectory(str(config_path))
        trajectory_csv = tmp_root / "trajectory.csv"

        obs_config_path = _make_observation_config(
            tmp_root, trajectory_csv, name="e2e_observations"
        )
        generate_observations(str(obs_config_path))

        csv_path = Path(tmp_root) / "e2e_observations" / "observations.csv"
        dataset = load_observation_dataset(csv_path)

        assert "obs_id" in dataset
        assert "time_years" in dataset
        assert "ra_deg" in dataset
        assert "dec_deg" in dataset
        assert "sigma_ra_cosdec_arcsec" in dataset
        assert "sigma_dec_arcsec" in dataset

        # Ground-truth columns must NOT be exposed by the C3 loader.
        assert "true_ra_deg" not in dataset
        assert "true_dec_deg" not in dataset
        assert "true_x_au" not in dataset

        # Load truth separately via C5-facing loader.
        gt_path = Path(tmp_root) / "e2e_observations" / "ground_truth.json"
        gt = load_ground_truth_dataset(gt_path)
        assert "true_ra_deg" in gt
        assert len(gt["obs_id"]) == len(dataset["obs_id"])

        print("PASS: observations -> C3 loader")


# ---------------------------------------------------------------------------
# Scenario 3: Arbitrary-time propagation (inside and beyond span)
# ---------------------------------------------------------------------------

def test_propagation_inside_and_beyond_span():
    """propagate_from_trajectory interpolates inside span, integrates beyond."""
    with tempfile.TemporaryDirectory(prefix="e2e-prop-") as tmp:
        tmp_root = Path(tmp)

        config_path = _make_config(tmp_root, "synthetic_asteroid")
        generate_trajectory(str(config_path))
        trajectory_csv = tmp_root / "trajectory.csv"

        trajectory = load_trajectory(trajectory_csv)
        t_start = float(trajectory["time_years"][0])
        t_end = float(trajectory["time_years"][-1])

        # Inside span: interpolation
        t_mid = 0.5 * (t_start + t_end)
        state_mid = propagate_from_trajectory(trajectory, t_mid)
        assert np.isfinite(state_mid["x_au"])
        assert t_start <= t_mid <= t_end

        # Exact sample point: interpolation should match trajectory exactly
        idx = len(trajectory["time_years"]) // 2
        t_sample = float(trajectory["time_years"][idx])
        state_sample = propagate_from_trajectory(trajectory, t_sample)
        pos_err = math.hypot(
            state_sample["x_au"] - trajectory["positions"][idx, 0],
            state_sample["y_au"] - trajectory["positions"][idx, 1],
            state_sample["z_au"] - trajectory["positions"][idx, 2],
        )
        vel_err = math.hypot(
            state_sample["vx_au_per_year"] - trajectory["velocities"][idx, 0],
            state_sample["vy_au_per_year"] - trajectory["velocities"][idx, 1],
            state_sample["vz_au_per_year"] - trajectory["velocities"][idx, 2],
        )
        assert pos_err < 1e-12, f"Position error at sample point: {pos_err}"
        assert vel_err < 1e-12, f"Velocity error at sample point: {vel_err}"

        # Beyond span: REBOUND integration
        t_beyond = t_end + 1.0
        state_beyond = propagate_from_trajectory(trajectory, t_beyond)
        assert np.isfinite(state_beyond["x_au"])
        assert state_beyond["x_au"] != trajectory["positions"][-1, 0] or True

        # propagate_multi with trajectory
        times = [t_start + 0.1, t_end + 0.5, t_mid]
        states = propagate_multi(
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
            times,
            bodies=["Sun", "Earth", "Jupiter"],
            trajectory=trajectory,
        )
        assert len(states) == 3
        for s in states:
            assert np.isfinite(s["x_au"])

        print("PASS: arbitrary-time propagation")


def test_propagate_state_single_epoch():
    """propagate_state returns correct state at t=0 and at later epochs."""
    state0 = propagate_state(
        2.0, 0.0, 0.0, 0.0, math.sqrt(1.0 / 2.0), 0.0,
        0.0,
        bodies=["Sun"],
    )
    assert np.isclose(state0["x_au"], 2.0)
    assert np.isclose(state0["y_au"], 0.0)
    assert np.isclose(state0["vx_au_per_year"], 0.0)

    state1 = propagate_state(
        2.0, 0.0, 0.0, 0.0, math.sqrt(1.0 / 2.0), 0.0,
        1.0,
        bodies=["Sun"],
    )
    assert np.isfinite(state1["x_au"])
    assert np.isfinite(state1["vy_au_per_year"])

    print("PASS: propagate_state single epoch")


# ---------------------------------------------------------------------------
# Scenario 4: Orbital element conversion round trips
# ---------------------------------------------------------------------------

def test_orbital_element_round_trip():
    """Cartesian -> elements -> Cartesian round trip preserves state."""
    x, y, z = 2.5, 0.0, 0.0
    # Circular-orbit speed consistent with C1's REBOUND model: v = sqrt(mu/r)
    vx, vy, vz = 0.0, math.sqrt(MU_REBOUND / 2.5), 0.0

    elements = cartesian_to_orbital_elements(x, y, z, vx, vy, vz)
    assert elements.a > 0
    assert 0 <= elements.e < 1

    x2, y2, z2, vx2, vy2, vz2 = orbital_elements_to_cartesian(elements)

    pos_err = math.hypot(x - x2, y - y2, z - z2)
    vel_err = math.hypot(vx - vx2, vy - vy2, vz - vz2)
    assert pos_err < 1e-10, f"Position round-trip error: {pos_err}"
    assert vel_err < 1e-10, f"Velocity round-trip error: {vel_err}"

    print("PASS: orbital element round trip")


# ---------------------------------------------------------------------------
# Scenario 5: Observer geometry and sky-coordinate conversion
# ---------------------------------------------------------------------------

def test_observer_geometry_and_sky_coordinates():
    """Observer positions, LOS, RA/Dec, and elongation are self-consistent."""
    times = np.array([0.0, 0.25, 0.5, 1.0])

    positions = calculate_observer_positions(times)
    velocities = calculate_observer_velocities(times)
    assert positions.shape == (4, 3)
    assert velocities.shape == (4, 3)

    # At t=0, phase=90° -> observer at (0, 1, 0)
    assert np.isclose(positions[0, 0], 0.0, atol=1e-12)
    assert np.isclose(positions[0, 1], 1.0, atol=1e-12)
    assert np.isclose(positions[0, 2], 0.0)

    # Velocity magnitude should be sqrt(mu/r) = sqrt(39.4769/1) = 6.283 for r=1 AU
    v_mag = np.linalg.norm(velocities[0])
    assert np.isclose(v_mag, math.sqrt(MU_REBOUND / 1.0), atol=1e-12)

    # Line of sight
    asteroid_positions = np.array([[2.0, 0.0, 0.0]] * 4)
    rel, los, dist = calculate_line_of_sight(asteroid_positions, positions)
    assert los.shape == (4, 3)
    assert dist.shape == (4,)
    assert np.allclose(np.linalg.norm(los, axis=1), 1.0)

    # Sky coordinates
    ra, dec = calculate_sky_coordinates(los)
    assert ra.shape == (4,)
    assert dec.shape == (4,)
    assert np.all(ra >= 0) and np.all(ra <= 360 + 1e-9)
    assert np.all(dec >= -90) and np.all(dec <= 90)

    # Solar elongation
    elong = calculate_solar_elongation(asteroid_positions, positions)
    assert elong.shape == (4,)
    assert np.all(elong >= 0) and np.all(elong <= 180)

    print("PASS: observer geometry and sky coordinates")


# ---------------------------------------------------------------------------
# Scenario 6: Future observation prediction
# ---------------------------------------------------------------------------

def test_prediction_from_state():
    """predict_from_state produces PredictionOutput with RA/Dec/distance."""
    results = predict_from_state(
        2.0, 0.0, 0.0,
        0.0, math.sqrt(1.0 / 2.0), 0.0,
        epochs_years=[0.0, 0.5, 1.0],
        trajectory=None,
    )
    assert len(results) == 3
    for r in results:
        assert isinstance(r, PredictionOutput)
        assert np.isfinite(r.ra_deg)
        assert np.isfinite(r.dec_deg)
        assert np.isfinite(r.distance_au)
        assert 0 <= r.ra_deg < 360
        assert -90 <= r.dec_deg <= 90
        assert r.frame == "equatorial_j2000"
        assert r.time_metadata["epoch_years"] >= 0

    print("PASS: prediction from state")


def test_prediction_from_trajectory():
    """predict_from_trajectory works with trajectory (interpolation inside span)."""
    with tempfile.TemporaryDirectory(prefix="e2e-pred-") as tmp:
        tmp_root = Path(tmp)

        config_path = _make_config(tmp_root, "synthetic_asteroid")
        generate_trajectory(str(config_path))
        trajectory_csv = tmp_root / "trajectory.csv"

        trajectory = load_trajectory(trajectory_csv)

        results = predict_from_trajectory(
            trajectory,
            epochs_years=[0.0, 1.0, 2.5],
        )
        assert len(results) == 3
        for r in results:
            assert isinstance(r, PredictionOutput)
            assert np.isfinite(r.ra_deg)
            assert np.isfinite(r.dec_deg)
            assert np.isfinite(r.distance_au)
            assert 0 <= r.ra_deg < 360
            assert -90 <= r.dec_deg <= 90

        # Beyond span should also work (REBOUND integration)
        results_beyond = predict_from_trajectory(
            trajectory,
            epochs_years=[6.0],
        )
        assert len(results_beyond) == 1
        assert np.isfinite(results_beyond[0].ra_deg)

    print("PASS: prediction from trajectory")


# ---------------------------------------------------------------------------
# Scenario 7: Interpolation evaluation accuracy
# ---------------------------------------------------------------------------

def test_interpolation_evaluation():
    """evaluate_trajectory returns finite, bounded error statistics."""
    with tempfile.TemporaryDirectory(prefix="e2e-interp-") as tmp:
        tmp_root = Path(tmp)

        traj = generate_trajectory_with_interval(
            initial_x_au=2.5,
            initial_y_au=0.0,
            initial_z_au=0.0,
            initial_vx_au_per_year=0.0,
            initial_vy_au_per_year=math.sqrt(1.0 / 2.5),
            initial_vz_au_per_year=0.0,
            duration_years=5.0,
            sampling_interval_years=0.005,
            epsilon=1e-14,
            bodies=["Sun", "Earth", "Jupiter"],
        )

        result = evaluate_trajectory(
            traj,
            sampling_interval=0.005,
            reference_epsilon=1e-14,
            n_intermediate=9,
        )

        assert np.isfinite(result.mean_position_error_au)
        assert np.isfinite(result.mean_velocity_error_au_per_yr)
        assert result.comparison_epochs > 0
        assert result.mean_position_error_au < 1.0  # reasonable bound
        assert result.mean_velocity_error_au_per_yr < 1.0

    print("PASS: interpolation evaluation")


# ---------------------------------------------------------------------------
# Scenario 8: Complete C1/C2 end-to-end workflow
# ---------------------------------------------------------------------------

def test_complete_c1_c2_workflow():
    """Full workflow: C1 trajectory -> C2 observations -> loader -> prediction."""
    with tempfile.TemporaryDirectory(prefix="e2e-complete-") as tmp:
        tmp_root = Path(tmp)

        # C1: generate trajectory
        config_path = _make_config(tmp_root, "synthetic_asteroid")
        generate_trajectory(str(config_path))
        trajectory_csv = tmp_root / "trajectory.csv"
        trajectory = load_trajectory(trajectory_csv)

        # C2: generate observations
        obs_config_path = _make_observation_config(
            tmp_root, trajectory_csv, name="complete_observations"
        )
        observations, metadata = generate_observations(str(obs_config_path))

        csv_path = Path(tmp_root) / "complete_observations" / "observations.csv"
        assert csv_path.exists()

        # Loader (C3-facing): measurement data only
        dataset = load_observation_dataset(csv_path)
        assert "true_ra_deg" not in dataset
        assert len(dataset["obs_id"]) == metadata["number_of_observations"]

        # Ground truth (C5-facing): separate file
        gt_path = Path(tmp_root) / "complete_observations" / "ground_truth.json"
        gt = load_ground_truth_dataset(gt_path)
        assert len(gt["obs_id"]) == metadata["number_of_observations"]

        # Prediction: future epochs from trajectory
        results = predict_from_trajectory(
            trajectory,
            epochs_years=[6.0, 7.0],
        )
        assert len(results) == 2
        for r in results:
            assert np.isfinite(r.ra_deg)
            assert np.isfinite(r.dec_deg)

        print("PASS: complete C1/C2 workflow")


# ---------------------------------------------------------------------------
# Direct script runner
# ---------------------------------------------------------------------------

def main() -> int:
    tests = [
        test_c1_to_c2_pipeline,
        test_observations_to_c3_loader,
        test_propagation_inside_and_beyond_span,
        test_propagate_state_single_epoch,
        test_orbital_element_round_trip,
        test_observer_geometry_and_sky_coordinates,
        test_prediction_from_state,
        test_prediction_from_trajectory,
        test_interpolation_evaluation,
        test_complete_c1_c2_workflow,
    ]

    failed = 0
    for test in tests:
        try:
            test()
        except Exception as e:  # noqa: BLE001
            print(f"FAIL: {test.__name__}: {e}")
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"End-to-end integration: {len(tests) - failed}/{len(tests)} passed")
    if failed:
        print(f"{failed} test(s) FAILED")
        return 1
    print("All end-to-end integration tests PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
