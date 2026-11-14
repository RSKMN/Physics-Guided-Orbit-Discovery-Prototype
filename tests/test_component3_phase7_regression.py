
import unittest
import numpy as np
import json
from pathlib import Path
from typing import Dict, Any

from orbit_discovery.component3.models import OrbitState, ObservationDataset, EstimationResult
from orbit_discovery.component3.estimation import run_estimation
from orbit_discovery.component3.candidates import run_multi_start_estimation
from orbit_discovery.component3.candidate_diagnostics import compute_candidate_diagnostics

# Production dynamics/obs model for synthetic data generation
from orbit_discovery.component3.dynamics import propagate_trial_state
from orbit_discovery.component3.observation_model import predict_apparent_coordinates

class TestComponent3Phase7Regression(unittest.TestCase):

    def setUp(self):
        # Known orbit from production tests (circular Sun-centred at r=2)
        self.true_state = OrbitState(rx=2.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        self.epochs = np.linspace(0.0, 1.0, 12) # 12 observation epochs

        bodies = ["Sun"]
        states = propagate_trial_state(self.true_state, self.epochs.tolist(), bodies=bodies)
        preds = predict_apparent_coordinates(states, self.epochs.tolist())

        ra_obs = np.array([p["ra_deg"] for p in preds])
        dec_obs = np.array([p["dec_deg"] for p in preds])

        # Define dataset metadata
        self.dataset = ObservationDataset(
            data={
                "time_years": self.epochs,
                "ra_deg": ra_obs,
                "dec_deg": dec_obs,
                "sigma_ra_cosdec_arcsec": np.ones_like(ra_obs) * 0.1,
                "sigma_dec_arcsec": np.ones_like(dec_obs) * 0.1,
            },
            frame="equatorial",
            time_scale="tdb",
            metadata={"source": "regression_test", "bodies": bodies}
        )

    def test_exact_initial_state_pipeline_consistency(self):
        # 1. Run Estimation (baseline Phase 3D fit)
        res = run_estimation(self.dataset, self.true_state, max_iter=20, bodies=["Sun"])
        self.assertTrue(res.best_fit.fit_metrics["chi2"] < 5.0)

        # 2. Run Multi-Start Candidate Generation
        cand_res, audit_log = run_multi_start_estimation(
            res, self.dataset, bodies=["Sun"], config={"num_starts": 10}
        )
        self.assertTrue(len(cand_res.candidates) > 0)

        # 3. Run Candidate Diagnostics on retained candidates
        diagnostics = compute_candidate_diagnostics(cand_res.candidates)

        # Verify valid diagnostics output
        self.assertTrue(diagnostics.n_retained_candidates > 0)
        self.assertTrue(np.all(np.isfinite(diagnostics.pairwise_distances)))
        # Valid assessments depend on candidate count (n=1 -> insufficient_candidates)
        self.assertIn(
            diagnostics.assessment,
            ["single_compact_group", "multiple_separated_groups", "insufficient_candidates"],
        )
        self.assertEqual(len(diagnostics.cluster_assignments), diagnostics.n_retained_candidates)

        # 4. Verify Recovery Tolerances (Justified by low-noise synthetic setup)
        # Multi-start retained candidates converge to the known initial state
        best_state = cand_res.best_fit.state.to_array()
        np.testing.assert_allclose(best_state, self.true_state.to_array(), atol=1e-3)

    def test_perturbed_initial_state_recovery(self):
        # Perturb initial state (5% position, ~1% velocity)
        perturbed_state = OrbitState(
            rx=2.1, ry=0.05, rz=0.05,
            vx=0.05, vy=4.5, vz=0.05
        )

        # 1. Run Estimation from perturbed state
        res = run_estimation(self.dataset, perturbed_state, max_iter=20, bodies=["Sun"])
        fit_metrics = res.best_fit.fit_metrics
        self.assertTrue(fit_metrics["chi2"] < 5.0)
        self.assertTrue(np.isfinite(fit_metrics["chi2"]))
        self.assertTrue(fit_metrics["jacobian_rank"] == 6)
        self.assertTrue(fit_metrics["n_valid_scalar_residuals"] > 6, "positive degrees of freedom")

        # Explicit optimizer convergence flag from candidate metadata
        best_candidate = res.candidates[0]
        self.assertTrue(best_candidate.metadata.get("converged", False), "optimizer did not converge")

        # 2. Run Multi-Start Candidate Generation
        cand_res, audit_log = run_multi_start_estimation(
            res, self.dataset, bodies=["Sun"], config={"num_starts": 10}
        )
        self.assertTrue(len(cand_res.candidates) > 0)

        # 3. Run Candidate Diagnostics
        diagnostics = compute_candidate_diagnostics(cand_res.candidates)
        self.assertTrue(diagnostics.n_retained_candidates > 0)

        # Pairwise-distance validation is only meaningful when >1 candidate is retained.
        # With n=1 the diagnostics path is single-candidate (insufficient_candidates);
        # pairwise_distances is empty and vacuously finite.
        if diagnostics.n_retained_candidates > 1:
            self.assertTrue(np.all(np.isfinite(diagnostics.pairwise_distances)))
        self.assertEqual(len(diagnostics.cluster_assignments), diagnostics.n_retained_candidates)

        # Reduced chi-square where available on retained candidates
        for cand in cand_res.candidates:
            meta = cand.metadata
            if "chi2" in meta:
                self.assertTrue(np.isfinite(meta["chi2"]), "chi2 not finite")
            if "chi2_reduced" in meta:
                self.assertTrue(np.isfinite(meta["chi2_reduced"]), "chi2_reduced not finite")

        # 4. Verify Recovery Tolerances
        best_state = cand_res.best_fit.state.to_array()
        true_arr = self.true_state.to_array()

        # Position (rx, ry, rz)
        np.testing.assert_allclose(best_state[:3], true_arr[:3], atol=1e-3)
        # Velocity (vx, vy, vz)
        np.testing.assert_allclose(best_state[3:], true_arr[3:], atol=1e-3)

    def test_noisy_observations_estimation_behavior(self):
        # deterministic noise consistent with measurement uncertainties (0.1 arcsec)
        rng = np.random.default_rng(42)
        noise_ra = rng.normal(0, 0.1, len(self.epochs))
        noise_dec = rng.normal(0, 0.1, len(self.epochs))

        noisy_dataset = ObservationDataset(
            data={
                "time_years": self.dataset.data["time_years"],
                "ra_deg": self.dataset.data["ra_deg"] + noise_ra / 3600.0,
                "dec_deg": self.dataset.data["dec_deg"] + noise_dec / 3600.0,
                "sigma_ra_cosdec_arcsec": self.dataset.data["sigma_ra_cosdec_arcsec"],
                "sigma_dec_arcsec": self.dataset.data["sigma_dec_arcsec"],
            },
            frame="equatorial",
            time_scale="tdb",
            metadata=self.dataset.metadata
        )

        res = run_estimation(noisy_dataset, self.true_state, bodies=["Sun"])
        self.assertIsInstance(res, EstimationResult)
        # Fit metric should be sensible (chi2 scaled by noise in arcsec -> radians)
        self.assertTrue(res.best_fit.fit_metrics["chi2"] < 1000.0)

    def test_sparse_observations_diagnostics(self):
        # Sparse observations: only 3 epochs (insufficient to constrain 6D state)
        sparse_epochs = self.epochs[:3]

        sparse_ds = ObservationDataset(
            data={
                "time_years": sparse_epochs,
                "ra_deg": self.dataset.data["ra_deg"][:3],
                "dec_deg": self.dataset.data["dec_deg"][:3],
                "sigma_ra_cosdec_arcsec": self.dataset.data["sigma_ra_cosdec_arcsec"][:3],
                "sigma_dec_arcsec": self.dataset.data["sigma_dec_arcsec"][:3],
            },
            frame="equatorial",
            time_scale="tdb",
            metadata=self.dataset.metadata
        )

        # Estimation runs but observations under-constrain the 6D state
        res = run_estimation(sparse_ds, self.true_state, bodies=["Sun"])
        self.assertIsInstance(res, EstimationResult)

        # Pass through multi-start to get Phase 4-complete candidate metadata,
        # then verify diagnostics handles the resulting candidate set gracefully.
        cand_res, audit_log = run_multi_start_estimation(
            res, sparse_ds, bodies=["Sun"], config={"num_starts": 3}
        )
        self.assertEqual(len(audit_log), 3)

        # Diagnostics should handle any candidate set gracefully (including empty)
        diagnostics = compute_candidate_diagnostics(cand_res.candidates)
        self.assertTrue(diagnostics.n_retained_candidates >= 0)

if __name__ == "__main__":
    unittest.main()
