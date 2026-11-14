"""Focused tests for Component 3 Phase 3D estimation integration."""

import unittest
import numpy as np
from typing import Dict, Any
from unittest.mock import patch

from orbit_discovery.component3.models import OrbitState, ObservationDataset, EstimationResult
from orbit_discovery.component3.estimation import run_estimation, build_residual_function
from orbit_discovery.component3.observation_model import ObserverConfig


class TestEstimation(unittest.TestCase):

    def setUp(self):
        # Circular Sun-centred orbit at r = 2 AU:
        #   v = sqrt(mu_sun / r) = sqrt(4*pi^2 / 2) = pi*sqrt(2) ≈ 4.44288 AU/year
        #   period = 2*pi * sqrt(r^3 / mu_sun) = 2*pi * sqrt(8 / 4*pi^2) = 2*sqrt(2) ≈ 2.828 years
        self.true_state = OrbitState(rx=2.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)

        # Six observation epochs to ensure overdetermined system (>= 6D state)
        self.epochs = np.array([0.0, 0.2, 0.4, 0.6, 0.8, 1.0])

        # Generate synthetic observations through the production pipeline
        from orbit_discovery.component3.dynamics import propagate_trial_state
        from orbit_discovery.component3.observation_model import predict_apparent_coordinates

        bodies = ["Sun"]
        states = propagate_trial_state(self.true_state, self.epochs.tolist(), bodies=bodies)
        preds = predict_apparent_coordinates(states, self.epochs.tolist())

        ra_obs = np.array([p["ra_deg"] for p in preds])
        dec_obs = np.array([p["dec_deg"] for p in preds])

        self.dataset = ObservationDataset(
            data={
                "time_years": self.epochs,
                "ra_deg": ra_obs,
                "dec_deg": dec_obs,
                "sigma_ra_cosdec_arcsec": np.ones_like(ra_obs),
                "sigma_dec_arcsec": np.ones_like(dec_obs),
            },
            frame="equatorial",
            time_scale="tdb",
            metadata={"source": "test", "bodies": bodies}
        )

    def test_dataset_validation_rejects_invalid_dataset_before_propagation(self):
        # Invalid dataset (empty time_years) must raise before any propagation call.
        bad_data = self.dataset.data.copy()
        bad_data["time_years"] = np.array([])
        bad_ds = ObservationDataset(bad_data, "equatorial", "tdb", {})

        with patch('orbit_discovery.component3.estimation.propagate_trial_state') as mock_propagate:
            with self.assertRaises(ValueError):
                run_estimation(bad_ds, self.true_state, bodies=["Sun"])
            mock_propagate.assert_not_called()

    def test_dataset_validation_rejects_negative_epochs_before_propagation(self):
        bad_data = self.dataset.data.copy()
        bad_data["time_years"] = np.array([-1.0, 0.2, 0.4, 0.6, 0.8, 1.0])
        bad_ds = ObservationDataset(bad_data, "equatorial", "tdb", {})

        with patch('orbit_discovery.component3.estimation.propagate_trial_state') as mock_propagate:
            with self.assertRaises(ValueError):
                run_estimation(bad_ds, self.true_state, bodies=["Sun"])
            mock_propagate.assert_not_called()

    def test_invalid_initial_state(self):
        bad_state = OrbitState(rx=np.nan, ry=0, rz=0, vx=0, vy=0, vz=0)
        with self.assertRaises(ValueError):
            run_estimation(self.dataset, bad_state, bodies=["Sun"])

    def test_residual_dimension_consistency(self):
        res_fn = build_residual_function(self.dataset, bodies=["Sun"])
        x = self.true_state.to_array()
        r1 = res_fn(x)
        r2 = res_fn(x + 0.01)
        self.assertEqual(r1.shape, r2.shape)
        self.assertEqual(r1.shape[0], len(self.epochs) * 2)

    def test_failed_trial_propagation_optimizer_callback(self):
        res_fn = build_residual_function(self.dataset, bodies=["Sun"])

        res_fn(self.true_state.to_array())

        crazy_x = np.array([1.0, 1.0, 1.0, np.inf, 0.0, 0.0])
        with self.assertRaises(ValueError) as cm:
            res_fn(crazy_x)
        self.assertIn("Estimation evaluation failed", str(cm.exception))

    def test_non_converged_result_handled(self):
        x_perturbed = self.true_state.to_array() * 1.5
        perturbed_state = OrbitState(
            rx=x_perturbed[0], ry=x_perturbed[1], rz=x_perturbed[2],
            vx=x_perturbed[3], vy=x_perturbed[4], vz=x_perturbed[5]
        )
        res = run_estimation(self.dataset, perturbed_state, max_iter=1, bodies=["Sun"])
        self.assertIsInstance(res, EstimationResult)
        self.assertFalse(res.candidates[0].metadata["converged"])
        self.assertIn("Max iterations", res.candidates[0].metadata["termination_reason"])

    def test_valid_synthetic_dataset(self):
        res = run_estimation(self.dataset, self.true_state, max_iter=2, bodies=["Sun"])
        self.assertIsInstance(res, EstimationResult)
        self.assertEqual(len(res.candidates), 1)
        self.assertIsInstance(res.best_fit.residuals["ra_arcsec"], np.ndarray)
        self.assertIsInstance(res.best_fit.fit_metrics["chi2"], float)
        self.assertIsInstance(res.candidates[0].metadata["n_iter"], int)

    def test_orbit_recovery_from_perturbed_guess(self):
        x_perturbed = self.true_state.to_array() * 1.05
        perturbed_state = OrbitState(
            rx=x_perturbed[0], ry=x_perturbed[1], rz=x_perturbed[2],
            vx=x_perturbed[3], vy=x_perturbed[4], vz=x_perturbed[5]
        )
        res = run_estimation(self.dataset, perturbed_state, max_iter=20, bodies=["Sun"])
        self.assertTrue(res.best_fit.fit_metrics["chi2"] < 10.0)
        np.testing.assert_allclose(res.best_fit.state.to_array(), self.true_state.to_array(), atol=1e-1)

    def test_source_dataset_metadata_passthrough(self):
        # source_dataset_metadata should be exactly what was passed in.
        res = run_estimation(self.dataset, self.true_state, bodies=["Sun"])
        self.assertEqual(res.source_dataset_metadata, self.dataset.metadata)

    def test_no_truth_related_metadata_keys(self):
        # Verify no ground-truth / true-trajectory keys leak into metadata.
        res = run_estimation(self.dataset, self.true_state, bodies=["Sun"])
        for key in res.source_dataset_metadata:
            self.assertNotIn("true", key.lower())
            self.assertNotIn("ground_truth", key.lower())

    def test_final_prediction_failure_via_propagation(self):
        # Initial propagation succeeds, optimization mocked to return valid result,
        # final propagate_trial_state raises ValueError.
        fake_result = {
            "x": self.true_state.to_array(),
            "chi2": 0.0,
            "optimality": 0.0,
            "converged": True,
            "termination_reason": "Mock converged",
            "n_iter": 0,
            "nfev": 0,
            "njev": 0,
        }
        mock_prop_states = [
            {"epoch_years": 0.0, "x_au": 2.0, "y_au": 0.0, "z_au": 0.0,
             "vx_au_per_year": 0.0, "vy_au_per_year": 4.4428829, "vz_au_per_year": 0.0}
        ]

        with patch('orbit_discovery.component3.estimation.propagate_trial_state') as mock_propagate, \
             patch('orbit_discovery.component3.estimation.least_squares_lm') as mock_lm:
            # Initial validation call succeeds; final prediction call fails
            mock_propagate.side_effect = [
                mock_prop_states,
                ValueError("Simulated final prediction failure"),
            ]
            mock_lm.return_value = fake_result

            with self.assertRaisesRegex(ValueError, "Final prediction/residual failure"):
                run_estimation(self.dataset, self.true_state, bodies=["Sun"])

    def test_final_prediction_failure_via_prediction(self):
        # Initial propagation and optimization succeed; final propagation succeeds;
        # predict_apparent_coordinates raises ValueError.
        fake_result = {
            "x": self.true_state.to_array(),
            "chi2": 0.0,
            "optimality": 0.0,
            "converged": True,
            "termination_reason": "Mock converged",
            "n_iter": 0,
            "nfev": 0,
            "njev": 0,
        }
        mock_prop_states = [
            {"epoch_years": 0.0, "x_au": 2.0, "y_au": 0.0, "z_au": 0.0,
             "vx_au_per_year": 0.0, "vy_au_per_year": 4.4428829, "vz_au_per_year": 0.0}
        ]

        with patch('orbit_discovery.component3.estimation.propagate_trial_state') as mock_propagate, \
             patch('orbit_discovery.component3.estimation.predict_apparent_coordinates') as mock_predict, \
             patch('orbit_discovery.component3.estimation.least_squares_lm') as mock_lm:
            # Initial validation succeeds; final propagation succeeds; final prediction fails
            mock_propagate.side_effect = [mock_prop_states, mock_prop_states]
            mock_predict.side_effect = ValueError("Simulated prediction failure")
            mock_lm.return_value = fake_result

            with self.assertRaisesRegex(ValueError, "Final prediction/residual failure"):
                run_estimation(self.dataset, self.true_state, bodies=["Sun"])

    def test_orbit_recovery_with_scaled_jacobian_analysis(self):
        # Build residual function at the true state and numerically
        # evaluate the Jacobian with respect to SCALED coordinates u, where
        # x = scales * u and scales = [1, 1, 1, 2*pi, 2*pi, 2*pi].
        bodies = ["Sun"]
        res_fn = build_residual_function(self.dataset, bodies=bodies)

        scales = np.array([1.0, 1.0, 1.0, 2 * np.pi, 2 * np.pi, 2 * np.pi])
        u_true = self.true_state.to_array() / scales

        eps = 1e-6
        jac = np.zeros((len(self.epochs) * 2, 6))
        for k in range(6):
            u_plus = u_true.copy()
            u_plus[k] += eps
            x_plus = u_plus * scales
            r_plus = res_fn(x_plus)

            u_minus = u_true.copy()
            u_minus[k] -= eps
            x_minus = u_minus * scales
            r_minus = res_fn(x_minus)

            jac[:, k] = (r_plus - r_minus) / (2 * eps)

        rank = int(np.linalg.matrix_rank(jac, tol=1e-8))
        cond = float(np.linalg.cond(jac))

        self.assertEqual(rank, 6,
                         f"Scaled Jacobian rank {rank} != 6: orbit not locally identifiable")
        self.assertTrue(np.isfinite(cond),
                        f"Condition number {cond} is not finite")
        self.assertLess(cond, 1e12,
                        f"Scaled Jacobian ill-conditioned: cond={cond:.3e}")

        print(f"\n  Scaled Jacobian rank: {rank}/6")
        print(f"  Condition number: {cond:.6e}")
        print(f"  Scales: {scales}")

if __name__ == "__main__":
    unittest.main()
