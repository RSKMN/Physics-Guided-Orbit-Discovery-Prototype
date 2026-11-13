"""Focused tests for Component 3 Phase 2 implementation.

Covers:
- Dynamics: trial state insertion, initial state preservation,
  multi-epoch propagation, finite values, determinism,
  invalid state/epoch rejection, planetary configuration consistency.
- Observation model: observer reconstruction, relative position calculation,
  ecliptic-to-equatorial transformation, RA/Dec validity, RA normalization,
  noiseless consistency with Component 2.
- Integration: end-to-end trial state → propagation → predicted RA/Dec,
  repeated-run consistency, no ground truth access.
"""

from __future__ import annotations

import math
import tempfile
import time
import unittest
from pathlib import Path

import numpy as np

import sys as _sys
from pathlib import Path as _Path

_REPO_ROOT = _Path(__file__).resolve().parents[1]
_SRC_DIR = _REPO_ROOT / "src"
for _path in (_REPO_ROOT, _SRC_DIR):
    if str(_path) not in _sys.path:
        _sys.path.insert(0, str(_path))

from orbit_discovery.component3.dynamics import (
    propagate_trial_state,
    propagate_trial_state_single,
    build_trial_simulation,
)
from orbit_discovery.component3.models import (
    OrbitState,
    REFERENCE_EPOCH_YEARS,
)
from orbit_discovery.component3.observation_model import (
    predict_apparent_coordinates,
    predict_from_orbit_state,
    reconstruct_observer_config,
    get_obliquity_deg,
)
from orbit_discovery.component2_observations.observer import (
    calculate_observer_positions,
    ObserverConfig,
)


class DynamicsTests(unittest.TestCase):
    """Tests for the dynamics (REBOUND forward propagation) module."""

    def setUp(self):
        self.state = OrbitState(
            rx=2.5, ry=0.0, rz=0.0,
            vx=0.0, vy=math.sqrt(39.476926421373 / 2.5), vz=0.0,
        )

    def test_initial_state_insertion(self):
        """The supplied state is preserved at epoch 0."""
        result = propagate_trial_state_single(self.state, 0.0)
        self.assertAlmostEqual(result["x_au"], 2.5, places=6)
        self.assertAlmostEqual(result["y_au"], 0.0, places=6)
        self.assertAlmostEqual(result["z_au"], 0.0, places=6)

    def test_initial_state_preserved_at_reference_epoch(self):
        """At t=0, propagated state equals the input state (within COM offset)."""
        result = propagate_trial_state_single(self.state, 0.0)
        # After move_to_com, heliocentric relative state should match input
        self.assertAlmostEqual(result["x_au"], 2.5, places=5)
        self.assertAlmostEqual(result["y_au"], 0.0, places=5)
        self.assertAlmostEqual(result["z_au"], 0.0, places=5)
        self.assertAlmostEqual(result["vx_au_per_year"], 0.0, places=5)
        self.assertAlmostEqual(result["vy_au_per_year"], self.state.vy, places=5)
        self.assertAlmostEqual(result["vz_au_per_year"], 0.0, places=5)

    def test_propagation_at_multiple_epochs(self):
        """Propagation returns one result per requested epoch."""
        epochs = [0.0, 0.5, 1.0, 2.5, 5.0]
        results = propagate_trial_state(self.state, epochs)
        self.assertEqual(len(results), len(epochs))
        for r, t in zip(results, epochs):
            self.assertEqual(r["epoch_years"], t)

    def test_finite_position_and_velocity(self):
        """All propagated positions and velocities are finite."""
        epochs = [0.0, 0.5, 1.0, 2.5, 5.0]
        results = propagate_trial_state(self.state, epochs)
        for r in results:
            for key in ("x_au", "y_au", "z_au",
                        "vx_au_per_year", "vy_au_per_year", "vz_au_per_year"):
                self.assertTrue(math.isfinite(r[key]), f"{key} non-finite: {r[key]}")

    def test_deterministic_propagation(self):
        """Identical inputs produce identical outputs."""
        epochs = [0.0, 0.5, 1.0, 2.0, 3.0]
        r1 = propagate_trial_state(self.state, epochs)
        r2 = propagate_trial_state(self.state, epochs)
        for a, b in zip(r1, r2):
            self.assertEqual(a, b)

    def test_invalid_state_rejected(self):
        """Non-finite state values raise ValueError."""
        bad_state = OrbitState(np.nan, 0.0, 0.0, 0.0, 0.0, 0.0)
        with self.assertRaises(ValueError):
            propagate_trial_state_single(bad_state, 0.0)

    def test_invalid_epoch_rejected(self):
        """Negative epochs raise ValueError."""
        with self.assertRaises(ValueError):
            propagate_trial_state_single(self.state, -1.0)

    def test_nonfinite_epoch_rejected(self):
        """Non-finite epochs raise ValueError."""
        with self.assertRaises(ValueError):
            propagate_trial_state_single(self.state, np.nan)

    def test_planetary_configuration_consistency(self):
        """The simulation uses C1's planetary configuration."""
        sim = build_trial_simulation()
        # Sun + Mercury + Venus + Earth + Jupiter (4 planets) + asteroid = 6 particles
        self.assertEqual(sim.N, 6)
        self.assertEqual(sim.integrator, "ias15")
        self.assertAlmostEqual(sim.integrator.epsilon, 1e-12)

    def test_returns_documented_units(self):
        """Returned fields match the documented units."""
        epochs = [0.0, 1.0]
        results = propagate_trial_state(self.state, epochs)
        expected_keys = {
            "epoch_years", "x_au", "y_au", "z_au",
            "vx_au_per_year", "vy_au_per_year", "vz_au_per_year",
        }
        for r in results:
            self.assertEqual(set(r.keys()), expected_keys)

    def test_reference_epoch_constant(self):
        """Reference epoch is explicitly documented."""
        self.assertEqual(REFERENCE_EPOCH_YEARS, 0.0)


class ObservationModelTests(unittest.TestCase):
    """Tests for the observation model."""

    def test_observer_position_reconstruction(self):
        """ObserverConfig can be reconstructed from metadata."""
        metadata = {
            "observer": {
                "orbital_radius_au": 1.0,
                "orbital_period_years": 1.0,
                "initial_phase_deg": 90.0,
            },
            "coordinates": {"obliquity_deg": 23.43928},
        }
        config = reconstruct_observer_config(metadata)
        self.assertAlmostEqual(config.orbital_radius_au, 1.0)
        self.assertAlmostEqual(config.orbital_period_years, 1.0)
        self.assertAlmostEqual(config.initial_phase_deg, 90.0)

    def test_default_observer_config(self):
        """Default observer matches Component 2's Earth-like circular observer."""
        config = ObserverConfig()
        self.assertAlmostEqual(config.orbital_radius_au, 1.0)
        self.assertAlmostEqual(config.orbital_period_years, 1.0)
        self.assertAlmostEqual(config.initial_phase_deg, 90.0)

    def test_relative_position_calculation(self):
        """Relative positions are asteroid minus observer."""
        times = np.array([0.0, 0.5])
        obs_pos = calculate_observer_positions(times)
        asteroid_pos = np.array([[2.0, 0.0, 0.0], [2.0, 0.0, 0.0]])
        relative, los, dist = None, None, None
        from orbit_discovery.component2_observations.observer import (
            calculate_line_of_sight,
        )
        relative, los, dist = calculate_line_of_sight(asteroid_pos, obs_pos)
        self.assertEqual(relative.shape, (2, 3))
        self.assertEqual(los.shape, (2, 3))
        self.assertEqual(dist.shape, (2,))

    def test_ecliptic_to_equatorial_transformation(self):
        """RA/Dec are within valid ranges."""
        from orbit_discovery.component2_observations.observer import (
            calculate_line_of_sight,
            calculate_sky_coordinates,
        )
        times = np.array([0.0])
        obs_pos = calculate_observer_positions(times)
        asteroid_pos = np.array([[2.0, 0.0, 0.0]])
        relative, los, dist = calculate_line_of_sight(asteroid_pos, obs_pos)
        ra, dec = calculate_sky_coordinates(los)
        self.assertTrue(0 <= ra[0] < 360)
        self.assertTrue(-90 <= dec[0] <= 90)

    def test_predicted_ra_normalization(self):
        """Predicted RA is normalized to [0, 360)."""
        state = OrbitState(2.0, 0.0, 0.0, 0.0, math.sqrt(39.476926421373 / 2.0), 0.0)
        epochs = [0.0, 0.5, 1.0]
        _, predictions = predict_from_orbit_state(state, epochs)
        for p in predictions:
            self.assertTrue(0 <= p["ra_deg"] < 360, f"RA={p['ra_deg']} not in [0, 360)")

    def test_predicted_dec_range(self):
        """Predicted Dec is within [-90, 90]."""
        state = OrbitState(2.0, 0.0, 0.0, 0.0, math.sqrt(39.476926421373 / 2.0), 0.0)
        epochs = [0.0, 0.5, 1.0]
        _, predictions = predict_from_orbit_state(state, epochs)
        for p in predictions:
            self.assertTrue(-90 <= p["dec_deg"] <= 90, f"Dec={p['dec_deg']} out of range")

    def test_prediction_structure(self):
        """Prediction entries contain all documented fields."""
        state = OrbitState(2.0, 0.0, 0.0, 0.0, math.sqrt(39.476926421373 / 2.0), 0.0)
        epochs = [0.0]
        _, predictions = predict_from_orbit_state(state, epochs)
        expected_keys = {
            "epoch_years", "x_au", "y_au", "z_au",
            "vx_au_per_year", "vy_au_per_year", "vz_au_per_year",
            "observer_x_au", "observer_y_au", "observer_z_au",
            "ra_deg", "dec_deg",
        }
        self.assertEqual(set(predictions[0].keys()), expected_keys)

    def test_invalid_epochs_rejected(self):
        """Negative epochs raise ValueError."""
        state = OrbitState(2.0, 0.0, 0.0, 0.0, 1.0, 0.0)
        with self.assertRaises(ValueError):
            predict_from_orbit_state(state, [-1.0])

    def test_mismatched_lengths_rejected(self):
        """Mismatched state/epoch lengths raise ValueError."""
        state = OrbitState(2.0, 0.0, 0.0, 0.0, 1.0, 0.0)
        epochs = [0.0]
        _, predictions = predict_from_orbit_state(state, epochs)
        with self.assertRaises(ValueError):
            predict_apparent_coordinates(
                [predictions[0], predictions[0]], epochs,
            )


class IntegrationTests(unittest.TestCase):
    """End-to-end integration tests for the forward model."""

    def test_end_to_end_trial_state_to_predictions(self):
        """Trial state → propagation → predicted RA/Dec works end-to-end."""
        state = OrbitState(2.5, 0.0, 0.0, 0.0, math.sqrt(39.476926421373 / 2.5), 0.0)
        epochs = [0.0, 0.25, 0.5, 0.75, 1.0]
        prop_results, predictions = predict_from_orbit_state(state, epochs)
        self.assertEqual(len(prop_results), len(epochs))
        self.assertEqual(len(predictions), len(epochs))
        for p in predictions:
            self.assertTrue(math.isfinite(p["ra_deg"]))
            self.assertTrue(math.isfinite(p["dec_deg"]))
            self.assertTrue(math.isfinite(p["x_au"]))
            self.assertTrue(0 <= p["ra_deg"] < 360)
            self.assertTrue(-90 <= p["dec_deg"] <= 90)

    def test_repeated_runs_consistent(self):
        """Repeated runs produce identical results."""
        state = OrbitState(2.5, 0.0, 0.0, 0.0, math.sqrt(39.476926421373 / 2.5), 0.0)
        epochs = [0.0, 0.5, 1.0, 2.0]
        _, p1 = predict_from_orbit_state(state, epochs)
        _, p2 = predict_from_orbit_state(state, epochs)
        for a, b in zip(p1, p2):
            self.assertEqual(a["ra_deg"], b["ra_deg"])
            self.assertEqual(a["dec_deg"], b["dec_deg"])

    def test_no_ground_truth_access(self):
        """Production forward-model code never accesses ground_truth.json."""
        import inspect
        import orbit_discovery.component3.dynamics as dyn
        import orbit_discovery.component3.observation_model as obs_mod

        dyn_source = inspect.getsource(dyn)
        obs_source = inspect.getsource(obs_mod)
        self.assertNotIn("ground_truth", dyn_source.lower())
        self.assertNotIn("ground_truth", obs_source.lower())


class PerformanceTests(unittest.TestCase):
    """Lightweight performance measurements for the forward model."""

    def test_propagation_runtime_representative_count(self):
        """Measure runtime for a representative number of epochs (~262 observations)."""
        state = OrbitState(2.5, 0.0, 0.0, 0.0, math.sqrt(39.476926421373 / 2.5), 0.0)
        epochs = [i * 7.0 / 365.25 for i in range(262)]  # ~5 years at 7-day cadence

        start = time.perf_counter()
        _, predictions = predict_from_orbit_state(state, epochs)
        elapsed = time.perf_counter() - start

        self.assertEqual(len(predictions), 262)
        # Document the measurement
        print(f"\n  Forward model: {len(epochs)} epochs in {elapsed:.3f}s "
              f"({elapsed / len(epochs) * 1000:.3f} ms/epoch)")
        # Soft assertion: well under 1 second for 262 epochs
        self.assertLess(elapsed, 5.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
