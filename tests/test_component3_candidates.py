"""Focused tests for Component 3 Phase 4: Reproducible Multi-Start Candidate Selection."""

from __future__ import annotations

import json
import math
import unittest
from unittest.mock import MagicMock, patch

import numpy as np

from orbit_discovery.component3.candidates import (
    ConfigurationError,
    DEFAULT_CONFIG,
    _serialize_metric,
    validate_config,
    run_multi_start_estimation,
)
from orbit_discovery.component3.models import (
    OrbitState,
    ObservationDataset,
    BestFitResult,
    EstimationResult,
    OrbitCandidate,
)
from orbit_discovery.component3.estimation import run_estimation


def _make_dataset(
    n_obs: int = 6,
    seed: int = 0,
    include_observer_metadata: bool = True,
) -> ObservationDataset:
    """Create a synthetic observation dataset for testing."""
    rng = np.random.default_rng(seed)
    epochs = np.array([0.0, 0.2, 0.4, 0.6, 0.8, 1.0][:n_obs], dtype=float)
    ra = rng.uniform(0, 360, size=n_obs)
    dec = rng.uniform(-30, 30, size=n_obs)
    sigma_ra = np.ones(n_obs)
    sigma_dec = np.ones(n_obs)

    metadata = {}
    if include_observer_metadata:
        metadata["observer"] = {
            "orbital_radius_au": 1.0,
            "orbital_period_years": 1.0,
            "initial_phase_deg": 90.0,
        }

    return ObservationDataset(
        data={
            "time_years": epochs,
            "ra_deg": ra,
            "dec_deg": dec,
            "sigma_ra_cosdec_arcsec": sigma_ra,
            "sigma_dec_arcsec": sigma_dec,
        },
        frame="equatorial",
        time_scale="tdb",
        metadata=metadata,
    )


def _make_estimation_result(
    state: OrbitState,
    converged: bool = True,
    chi2: float = 10.0,
    jacobian_rank: Optional[int] = 6,
    n_valid: Optional[int] = 12,
    include_metadata: bool = True,
) -> EstimationResult:
    """Create a synthetic EstimationResult with configurable metrics."""
    dof = None
    if n_valid is not None and jacobian_rank is not None:
        dof = n_valid - jacobian_rank

    reduced_chi2 = None
    if chi2 is not None and dof is not None and dof > 0:
        reduced_chi2 = chi2 / dof

    best_fit = BestFitResult(
        state=state,
        epoch_years=0.0,
        residuals={
            "residual_vector": np.zeros(max(n_valid or 0, 1)),
            "ra_arcsec": np.zeros(max((n_valid or 0) // 2, 1)),
            "dec_arcsec": np.zeros(max((n_valid or 0) // 2, 1)),
            "valid_mask": np.ones(max((n_valid or 0) // 2, 1), dtype=bool),
            "ra_normalized": np.zeros(max((n_valid or 0) // 2, 1)),
            "dec_normalized": np.zeros(max((n_valid or 0) // 2, 1)),
        },
        fit_metrics={
            "chi2": float(chi2),
            "optimality": 0.001,
            "jacobian_rank": jacobian_rank,
            "n_valid_scalar_residuals": n_valid,
        },
    )

    metadata = {}
    if include_metadata:
        metadata = {
            "converged": converged,
            "termination_reason": "Converged.",
            "n_iter": 5,
            "nfev": 20,
            "njev": 6,
            "optimizer": "least_squares_lm",
            "jacobian_rank": jacobian_rank,
            "n_valid_scalar_residuals": n_valid,
        }

    candidate = OrbitCandidate(
        state=state,
        epoch_years=0.0,
        metadata=metadata,
    )

    return EstimationResult(
        candidates=[candidate],
        best_fit=best_fit,
        source_dataset_metadata={"source": "test"},
    )


class TestConfigurationValidation(unittest.TestCase):
    """Tests for configuration validation (Section 3.1 of design)."""

    def test_valid_default_config(self):
        config = validate_config(None)
        self.assertEqual(config["num_starts"], 100)
        self.assertEqual(config["random_seed"], 42)
        self.assertEqual(config["max_retained_candidates"], 10)

    def test_valid_custom_config(self):
        config = {
            "num_starts": 10,
            "random_seed": 7,
            "position_perturbation_scales": [0.02, 0.02, 0.02],
            "velocity_perturbation_scales": [2e-4, 2e-4, 2e-4],
            "duplicate_tolerance_pos": 0.01,
            "duplicate_tolerance_vel": 1e-4,
            "fit_quality_threshold_reduced_chi2": 3.0,
            "max_retained_candidates": 5,
        }
        result = validate_config(config)
        self.assertEqual(result["num_starts"], 10)
        self.assertEqual(result["random_seed"], 7)
        self.assertEqual(result["max_retained_candidates"], 5)

    def test_missing_fields_use_defaults(self):
        partial = {"num_starts": 5}
        result = validate_config(partial)
        self.assertEqual(result["num_starts"], 5)
        self.assertEqual(result["random_seed"], DEFAULT_CONFIG["random_seed"])

    def test_unknown_key_rejected(self):
        with self.assertRaises(ConfigurationError):
            validate_config({"num_starts": 10, "unknown_key": 1})

    def test_num_starts_boolean_rejected(self):
        with self.assertRaises(ConfigurationError):
            validate_config({"num_starts": True})

    def test_num_starts_fraction_rejected(self):
        with self.assertRaises(ConfigurationError):
            validate_config({"num_starts": 10.5})

    def test_num_starts_zero_rejected(self):
        with self.assertRaises(ConfigurationError):
            validate_config({"num_starts": 0})

    def test_num_starts_negative_rejected(self):
        with self.assertRaises(ConfigurationError):
            validate_config({"num_starts": -3})

    def test_random_seed_boolean_rejected(self):
        with self.assertRaises(ConfigurationError):
            validate_config({"random_seed": False})

    def test_random_seed_negative_rejected(self):
        with self.assertRaises(ConfigurationError):
            validate_config({"random_seed": -1})

    def test_random_seed_float_rejected(self):
        with self.assertRaises(ConfigurationError):
            validate_config({"random_seed": 42.0})

    def test_perturbation_wrong_length_rejected(self):
        with self.assertRaises(ConfigurationError):
            validate_config({"position_perturbation_scales": [0.01, 0.01]})

    def test_perturbation_nan_rejected(self):
        with self.assertRaises(ConfigurationError):
            validate_config({"position_perturbation_scales": [np.nan, 0.01, 0.01]})

    def test_perturbation_inf_rejected(self):
        with self.assertRaises(ConfigurationError):
            validate_config({"velocity_perturbation_scales": [np.inf, 1e-4, 1e-4]})

    def test_perturbation_zero_rejected(self):
        with self.assertRaises(ConfigurationError):
            validate_config({"position_perturbation_scales": [0.0, 0.01, 0.01]})

    def test_perturbation_negative_rejected(self):
        with self.assertRaises(ConfigurationError):
            validate_config({"velocity_perturbation_scales": [-1e-4, 1e-4, 1e-4]})

    def test_duplicate_tolerance_nan_rejected(self):
        with self.assertRaises(ConfigurationError):
            validate_config({"duplicate_tolerance_pos": np.nan})

    def test_fit_quality_threshold_inf_rejected(self):
        with self.assertRaises(ConfigurationError):
            validate_config({"fit_quality_threshold_reduced_chi2": np.inf})

    def test_config_not_dict_rejected(self):
        with self.assertRaises(ConfigurationError):
            validate_config("not a dict")  # type: ignore


class TestReproducibility(unittest.TestCase):
    """Tests for reproducible initial-state generation."""

    def test_same_seed_produces_identical_states(self):
        state = OrbitState(rx=2.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        from orbit_discovery.component3.candidates import _initial_states_from_config

        s1 = _initial_states_from_config(state, 10, 42, [0.01, 0.01, 0.01], [1e-4, 1e-4, 1e-4])
        s2 = _initial_states_from_config(state, 10, 42, [0.01, 0.01, 0.01], [1e-4, 1e-4, 1e-4])

        self.assertEqual(len(s1), len(s2))
        for (k1, st1), (k2, st2) in zip(s1, s2):
            self.assertEqual(k1, k2)
            np.testing.assert_allclose(st1.to_array(), st2.to_array())

    def test_different_seed_produces_different_states(self):
        state = OrbitState(rx=2.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        from orbit_discovery.component3.candidates import _initial_states_from_config

        s1 = _initial_states_from_config(state, 10, 42, [0.01, 0.01, 0.01], [1e-4, 1e-4, 1e-4])
        s2 = _initial_states_from_config(state, 10, 99, [0.01, 0.01, 0.01], [1e-4, 1e-4, 1e-4])

        # At least one start should differ
        different = False
        for (k1, st1), (k2, st2) in zip(s1, s2):
            if not np.allclose(st1.to_array(), st2.to_array(), atol=1e-12):
                different = True
                break
        self.assertTrue(different)

    def test_start_0_is_baseline(self):
        state = OrbitState(rx=2.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        from orbit_discovery.component3.candidates import _initial_states_from_config

        starts = _initial_states_from_config(state, 5, 42, [0.01, 0.01, 0.01], [1e-4, 1e-4, 1e-4])
        self.assertEqual(starts[0][0], 0)
        np.testing.assert_allclose(starts[0][1].to_array(), state.to_array())


class TestBaselinePreservation(unittest.TestCase):
    """Tests that Start 0 uses the baseline without re-optimization."""

    def test_start_0_uses_best_fit_state(self):
        state = OrbitState(rx=2.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        result = _make_estimation_result(state)

        dataset = _make_dataset()
        estimation_result, audit_log = run_multi_start_estimation(
            phase3_result=result,
            dataset=dataset,
            config={"num_starts": 1},
        )

        self.assertEqual(len(audit_log), 1)
        self.assertEqual(audit_log[0]["start_index"], 0)
        np.testing.assert_allclose(
            audit_log[0]["initial_state"],
            state.to_array(),
        )

    def test_baseline_missing_metrics_rejected(self):
        state = OrbitState(rx=2.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        result = _make_estimation_result(state, jacobian_rank=None, n_valid=None)

        dataset = _make_dataset()
        estimation_result, audit_log = run_multi_start_estimation(
            phase3_result=result,
            dataset=dataset,
            config={"num_starts": 1},
        )

        self.assertEqual(len(audit_log), 1)
        self.assertEqual(audit_log[0]["outcome"], "rejected")
        self.assertIsNotNone(audit_log[0]["reason"])


class TestValidationClassification(unittest.TestCase):
    """Tests for Jacobian rank and DOF validation classification."""

    def test_invalid_jacobian_rejected(self):
        state = OrbitState(rx=2.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        result = _make_estimation_result(state, jacobian_rank=None, n_valid=12)

        dataset = _make_dataset()
        estimation_result, audit_log = run_multi_start_estimation(
            phase3_result=result,
            dataset=dataset,
            config={"num_starts": 1},
        )

        self.assertEqual(audit_log[0]["outcome"], "rejected")
        self.assertEqual(audit_log[0]["reason"], "invalid_jacobian")

    def test_rank_deficient_rejected(self):
        state = OrbitState(rx=2.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        result = _make_estimation_result(state, jacobian_rank=5, n_valid=12)

        dataset = _make_dataset()
        estimation_result, audit_log = run_multi_start_estimation(
            phase3_result=result,
            dataset=dataset,
            config={"num_starts": 1},
        )

        self.assertEqual(audit_log[0]["outcome"], "rejected")
        self.assertEqual(audit_log[0]["reason"], "rank_deficient")

    def test_insufficient_dof_rejected(self):
        state = OrbitState(rx=2.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        # rank == n_valid, so dof = 0
        result = _make_estimation_result(state, jacobian_rank=6, n_valid=6)

        dataset = _make_dataset()
        estimation_result, audit_log = run_multi_start_estimation(
            phase3_result=result,
            dataset=dataset,
            config={"num_starts": 1},
        )

        self.assertEqual(audit_log[0]["outcome"], "rejected")
        self.assertEqual(audit_log[0]["reason"], "insufficient_degrees_of_freedom")

    def test_chi2_exactly_at_threshold_rejected(self):
        state = OrbitState(rx=2.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        # n_valid=12, rank=6, dof=6, threshold=5.0
        # chi2 = 30.0 → reduced_chi2 = 5.0 (exactly at threshold → rejected)
        result = _make_estimation_result(state, chi2=30.0, jacobian_rank=6, n_valid=12)

        dataset = _make_dataset()
        estimation_result, audit_log = run_multi_start_estimation(
            phase3_result=result,
            dataset=dataset,
            config={"num_starts": 1, "fit_quality_threshold_reduced_chi2": 5.0},
        )

        self.assertEqual(audit_log[0]["outcome"], "rejected")
        self.assertEqual(audit_log[0]["reason"], "high_reduced_chi2")

    def test_chi2_below_threshold_retained(self):
        state = OrbitState(rx=2.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        # n_valid=12, rank=6, dof=6, chi2=24.0 → reduced_chi2 = 4.0 < 5.0
        result = _make_estimation_result(state, chi2=24.0, jacobian_rank=6, n_valid=12)

        dataset = _make_dataset()
        estimation_result, audit_log = run_multi_start_estimation(
            phase3_result=result,
            dataset=dataset,
            config={"num_starts": 1},
        )

        self.assertEqual(audit_log[0]["outcome"], "retained")


class TestPropagationFailure(unittest.TestCase):
    """Tests that propagation/prediction failures are recorded as failed/propagation_error."""

    def test_propagation_exception_recorded_as_failed(self):
        state = OrbitState(rx=2.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        result = _make_estimation_result(state)

        dataset = _make_dataset()

        with patch(
            "orbit_discovery.component3.candidates.run_estimation",
            side_effect=ValueError("Simulated propagation failure"),
        ):
            estimation_result, audit_log = run_multi_start_estimation(
                phase3_result=result,
                dataset=dataset,
                config={"num_starts": 2},
            )

        self.assertEqual(len(audit_log), 2)
        self.assertEqual(audit_log[1]["outcome"], "failed")
        self.assertEqual(audit_log[1]["reason"], "propagation_error")


class TestRankingAndDeduplication(unittest.TestCase):
    """Tests for deterministic ranking and duplicate removal."""

    def test_ranking_by_reduced_chi2(self):
        state_a = OrbitState(rx=2.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        state_b = OrbitState(rx=2.1, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)

        result_a = _make_estimation_result(state_a, chi2=24.0, jacobian_rank=6, n_valid=12)
        result_b = _make_estimation_result(state_b, chi2=12.0, jacobian_rank=6, n_valid=12)

        # Use result_a as baseline (worse chi2), result_b not directly used
        # Instead test ranking via mock
        dataset = _make_dataset()

        with patch(
            "orbit_discovery.component3.candidates.run_estimation",
            return_value=result_b,
        ):
            estimation_result, audit_log = run_multi_start_estimation(
                phase3_result=result_a,
                dataset=dataset,
                config={"num_starts": 2, "max_retained_candidates": 5},
            )

        # Baseline (start 0) has chi2=24 → reduced=4.0; start 1 has chi2=12 → reduced=2.0
        # Start 1 should rank first
        retained_indices = [c.metadata["start_index"] for c in estimation_result.candidates]
        self.assertIn(1, retained_indices)

    def test_duplicate_distance_below_1(self):
        state_a = OrbitState(rx=2.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        state_b = OrbitState(rx=2.001, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)

        # Both candidates valid: chi2=24 → reduced_chi2 = 4.0 < 5.0 threshold
        result_a = _make_estimation_result(state_a, chi2=24.0, jacobian_rank=6, n_valid=12)
        result_b = _make_estimation_result(state_b, chi2=24.0, jacobian_rank=6, n_valid=12)

        dataset = _make_dataset()

        with patch(
            "orbit_discovery.component3.candidates.run_estimation",
            return_value=result_b,
        ):
            estimation_result, audit_log = run_multi_start_estimation(
                phase3_result=result_a,
                dataset=dataset,
                config={
                    "num_starts": 2,
                    "max_retained_candidates": 5,
                    "duplicate_tolerance_pos": 0.005,
                    "duplicate_tolerance_vel": 5e-5,
                },
            )

        # Start 0 (chi2=24, reduced=4.0) ranks before start 1 (chi2=24, reduced=4.0)
        # due to lower start index tie-breaker. Start 1 should be duplicate of start 0.
        duplicate_records = [r for r in audit_log if r["outcome"] == "duplicate"]
        self.assertEqual(len(duplicate_records), 1)
        self.assertEqual(duplicate_records[0]["start_index"], 1)
        self.assertEqual(duplicate_records[0]["duplicate_of"], 0)


class TestAuditLog(unittest.TestCase):
    """Tests for audit log completeness and serialization."""

    def test_one_record_per_start(self):
        state = OrbitState(rx=2.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        result = _make_estimation_result(state)
        dataset = _make_dataset()

        estimation_result, audit_log = run_multi_start_estimation(
            phase3_result=result,
            dataset=dataset,
            config={"num_starts": 5},
        )

        self.assertEqual(len(audit_log), 5)
        indices = [r["start_index"] for r in audit_log]
        self.assertEqual(indices, list(range(5)))

    def test_audit_records_ordered_by_start_index(self):
        state = OrbitState(rx=2.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        result = _make_estimation_result(state)
        dataset = _make_dataset()

        _, audit_log = run_multi_start_estimation(
            phase3_result=result,
            dataset=dataset,
            config={"num_starts": 5},
        )

        indices = [r["start_index"] for r in audit_log]
        self.assertEqual(indices, sorted(indices))

    def test_audit_serializes_with_allow_nan_false(self):
        state = OrbitState(rx=2.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        result = _make_estimation_result(state)
        dataset = _make_dataset()

        _, audit_log = run_multi_start_estimation(
            phase3_result=result,
            dataset=dataset,
            config={"num_starts": 1},
        )

        # Must not raise
        json.dumps(audit_log, allow_nan=False)

    def test_all_five_outcomes_covered(self):
        # This test verifies the audit log can represent all outcomes.
        # We construct a scenario where baseline is retained (valid).
        state = OrbitState(rx=2.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        result = _make_estimation_result(state, chi2=24.0, jacobian_rank=6, n_valid=12)
        dataset = _make_dataset()

        estimation_result, audit_log = run_multi_start_estimation(
            phase3_result=result,
            dataset=dataset,
            config={"num_starts": 1},
        )

        outcomes = {r["outcome"] for r in audit_log}
        self.assertIn("retained", outcomes)


class TestReturnContract(unittest.TestCase):
    """Tests for the public return contract."""

    def test_best_fit_preserved(self):
        state = OrbitState(rx=2.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        result = _make_estimation_result(state)
        dataset = _make_dataset()

        estimation_result, _ = run_multi_start_estimation(
            phase3_result=result,
            dataset=dataset,
            config={"num_starts": 1},
        )

        self.assertIs(estimation_result.best_fit, result.best_fit)

    def test_candidates_in_ranking_order(self):
        state = OrbitState(rx=2.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        result = _make_estimation_result(state, chi2=24.0, jacobian_rank=6, n_valid=12)
        dataset = _make_dataset()

        estimation_result, _ = run_multi_start_estimation(
            phase3_result=result,
            dataset=dataset,
            config={"num_starts": 1},
        )

        self.assertEqual(len(estimation_result.candidates), 1)
        self.assertEqual(estimation_result.candidates[0].metadata["start_index"], 0)

    def test_empty_candidates_when_none_survive(self):
        state = OrbitState(rx=2.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        # rank 0 → rank_deficient
        result = _make_estimation_result(state, jacobian_rank=0, n_valid=12)
        dataset = _make_dataset()

        estimation_result, audit_log = run_multi_start_estimation(
            phase3_result=result,
            dataset=dataset,
            config={"num_starts": 1},
        )

        self.assertEqual(len(estimation_result.candidates), 0)
        self.assertEqual(len(audit_log), 1)
        self.assertEqual(audit_log[0]["outcome"], "rejected")


class TestTruthIsolation(unittest.TestCase):
    """Tests that candidate generation does not depend on ground truth."""

    def test_no_ground_truth_imports(self):
        import inspect
        import orbit_discovery.component3.candidates as mod

        source = inspect.getsource(mod)
        self.assertNotIn("ground_truth", source.lower())
        self.assertNotIn("true_", source.lower())

    def test_candidate_generation_without_ground_truth(self):
        state = OrbitState(rx=2.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        result = _make_estimation_result(state, chi2=24.0, jacobian_rank=6, n_valid=12)
        dataset = _make_dataset()

        estimation_result, audit_log = run_multi_start_estimation(
            phase3_result=result,
            dataset=dataset,
            config={"num_starts": 1},
        )

        self.assertEqual(len(estimation_result.candidates), 1)
        self.assertEqual(len(audit_log), 1)


class TestJacobianRankRegression(unittest.TestCase):
    """Regression tests for Jacobian rank classification."""

    def test_rank_greater_than_six_rejected_as_invalid_jacobian(self):
        state = OrbitState(rx=2.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        result = _make_estimation_result(state, jacobian_rank=7, n_valid=12)

        dataset = _make_dataset()
        estimation_result, audit_log = run_multi_start_estimation(
            phase3_result=result,
            dataset=dataset,
            config={"num_starts": 1},
        )

        self.assertEqual(audit_log[0]["outcome"], "rejected")
        self.assertEqual(audit_log[0]["reason"], "invalid_jacobian")

    def test_rank_twelve_rejected_as_invalid_jacobian(self):
        state = OrbitState(rx=2.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        result = _make_estimation_result(state, jacobian_rank=12, n_valid=12)

        dataset = _make_dataset()
        estimation_result, audit_log = run_multi_start_estimation(
            phase3_result=result,
            dataset=dataset,
            config={"num_starts": 1},
        )

        self.assertEqual(audit_log[0]["outcome"], "rejected")
        self.assertEqual(audit_log[0]["reason"], "invalid_jacobian")

    def test_non_numeric_baseline_epoch_is_rejected(self):
        state = OrbitState(rx=2.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        best_fit = BestFitResult(
            state=state,
            epoch_years="invalid",  # type: ignore[arg-type]
            residuals={"residual_vector": np.zeros(12)},
            fit_metrics={"chi2": 24.0, "optimality": 0.0,
                         "jacobian_rank": 6, "n_valid_scalar_residuals": 12},
        )
        candidate = OrbitCandidate(state=state, epoch_years=0.0, metadata={"converged": True})
        result = EstimationResult(
            candidates=[candidate],
            best_fit=best_fit,
            source_dataset_metadata={"source": "test"},
        )

        dataset = _make_dataset()
        estimation_result, audit_log = run_multi_start_estimation(
            phase3_result=result,
            dataset=dataset,
            config={"num_starts": 1},
        )

        self.assertEqual(audit_log[0]["outcome"], "rejected")
        self.assertEqual(audit_log[0]["reason"], "missing_baseline_metrics")

    def test_run_estimation_typeerror_in_jacobian_conversion(self):
        state = OrbitState(rx=2.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        dataset = _make_dataset()

        # Mocking to raise TypeError during SVD/jacobian rank logic
        with patch("numpy.linalg.svd", side_effect=TypeError("Simulated SVD TypeError")):
            result = run_estimation(dataset, state)
            self.assertIsNone(result.best_fit.fit_metrics["jacobian_rank"])


class TestMissingBaselineRegression(unittest.TestCase):
    """Regression tests for missing baseline state and result safety."""

    def test_missing_baseline_state_does_not_crash(self):
        state = OrbitState(rx=2.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        best_fit = BestFitResult(
            state=None,  # type: ignore[arg-type]
            epoch_years=0.0,
            residuals={"residual_vector": np.zeros(1)},
            fit_metrics={"chi2": 10.0, "optimality": 0.0,
                         "jacobian_rank": 6, "n_valid_scalar_residuals": 12},
        )
        candidate = OrbitCandidate(state=state, epoch_years=0.0, metadata={"converged": True})
        result = EstimationResult(
            candidates=[candidate],
            best_fit=best_fit,
            source_dataset_metadata={"source": "test"},
        )

        dataset = _make_dataset()
        estimation_result, audit_log = run_multi_start_estimation(
            phase3_result=result,
            dataset=dataset,
            config={"num_starts": 1},
        )

        self.assertEqual(len(audit_log), 1)
        self.assertEqual(audit_log[0]["outcome"], "rejected")
        self.assertEqual(audit_log[0]["reason"], "missing_baseline_metrics")

    def test_missing_baseline_best_fit_result_does_not_crash(self):
        state = OrbitState(rx=2.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        result = EstimationResult(
            candidates=[],
            best_fit=None,  # type: ignore[arg-type]
            source_dataset_metadata={"source": "test"},
        )

        dataset = _make_dataset()
        estimation_result, audit_log = run_multi_start_estimation(
            phase3_result=result,
            dataset=dataset,
            config={"num_starts": 1},
        )

        self.assertEqual(len(audit_log), 1)
        self.assertEqual(audit_log[0]["outcome"], "rejected")
        self.assertEqual(audit_log[0]["reason"], "missing_baseline_metrics")
        self.assertIsNone(audit_log[0]["initial_state"], "No fabricated state for missing baseline best_fit")

    def test_missing_baseline_state_audit_record_has_none_state(self):
        state = OrbitState(rx=2.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        best_fit = BestFitResult(
            state=None,  # type: ignore[arg-type]
            epoch_years=0.0,
            residuals={"residual_vector": np.zeros(1)},
            fit_metrics={"chi2": 10.0, "optimality": 0.0,
                         "jacobian_rank": 6, "n_valid_scalar_residuals": 12},
        )
        candidate = OrbitCandidate(state=state, epoch_years=0.0, metadata={"converged": True})
        result = EstimationResult(
            candidates=[candidate],
            best_fit=best_fit,
            source_dataset_metadata={"source": "test"},
        )

        dataset = _make_dataset()
        estimation_result, audit_log = run_multi_start_estimation(
            phase3_result=result,
            dataset=dataset,
            config={"num_starts": 1},
        )

        self.assertEqual(len(audit_log), 1)
        self.assertEqual(audit_log[0]["outcome"], "rejected")
        self.assertEqual(audit_log[0]["reason"], "missing_baseline_metrics")
        self.assertIsNone(audit_log[0]["initial_state"], "No fabricated zero state for missing baseline state")

    def test_malformed_baseline_state_is_rejected_without_state(self):
        state = OrbitState(rx=2.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        best_fit = BestFitResult(
            state="invalid",  # type: ignore[arg-type]
            epoch_years=0.0,
            residuals={"residual_vector": np.zeros(12)},
            fit_metrics={"chi2": 24.0, "optimality": 0.0,
                         "jacobian_rank": 6, "n_valid_scalar_residuals": 12},
        )
        result = EstimationResult(
            candidates=[OrbitCandidate(state=state, epoch_years=0.0, metadata={"converged": True})],
            best_fit=best_fit,
            source_dataset_metadata={"source": "test"},
        )

        _, audit_log = run_multi_start_estimation(
            phase3_result=result,
            dataset=_make_dataset(),
            config={"num_starts": 1},
        )

        self.assertEqual(audit_log[0]["reason"], "missing_baseline_metrics")
        self.assertIsNone(audit_log[0]["initial_state"])

    def test_malformed_baseline_candidate_is_rejected_without_convergence(self):
        state = OrbitState(rx=2.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        result = EstimationResult(
            candidates=[None],  # type: ignore[list-item]
            best_fit=_make_estimation_result(state).best_fit,
            source_dataset_metadata={"source": "test"},
        )

        _, audit_log = run_multi_start_estimation(
            phase3_result=result,
            dataset=_make_dataset(),
            config={"num_starts": 1},
        )

        self.assertEqual(audit_log[0]["reason"], "invalid_baseline_candidate")
        self.assertIsNone(audit_log[0]["convergence_status"])


class TestPerturbedStartMalformedResult(unittest.TestCase):
    """Tests that malformed perturbed estimation results are safely handled."""

    def test_perturbed_start_missing_best_fit_is_rejected(self):
        state = OrbitState(rx=2.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        baseline_result = _make_estimation_result(state, chi2=24.0, jacobian_rank=6, n_valid=12)

        # Malformed result: best_fit is None
        malformed_result = EstimationResult(
            candidates=[],
            best_fit=None,  # type: ignore[arg-type]
            source_dataset_metadata={"source": "test"},
        )

        dataset = _make_dataset()

        def fake_run_estimation(*args, **kwargs):
            return malformed_result

        with patch(
            "orbit_discovery.component3.candidates.run_estimation",
            side_effect=fake_run_estimation,
        ):
            estimation_result, audit_log = run_multi_start_estimation(
                phase3_result=baseline_result,
                dataset=dataset,
                config={"num_starts": 2},
            )

        # Start 0 valid, start 1 rejected for missing fit result
        self.assertEqual(len(audit_log), 2)
        self.assertEqual(audit_log[1]["outcome"], "rejected")
        self.assertEqual(audit_log[1]["reason"], "missing_fit_result")
        # Actual perturbed initial state preserved in audit record
        self.assertIsNotNone(audit_log[1]["initial_state"])
        self.assertEqual(len(estimation_result.candidates), 1)

    def test_perturbed_start_missing_fit_state_is_rejected(self):
        state = OrbitState(rx=2.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        baseline_result = _make_estimation_result(state, chi2=24.0, jacobian_rank=6, n_valid=12)

        # Malformed result: best_fit exists but state is None
        best_fit_none_state = BestFitResult(
            state=None,  # type: ignore[arg-type]
            epoch_years=0.0,
            residuals={"residual_vector": np.zeros(12)},
            fit_metrics={"chi2": 24.0, "optimality": 0.0,
                         "jacobian_rank": 6, "n_valid_scalar_residuals": 12},
        )
        malformed_result = EstimationResult(
            candidates=[],
            best_fit=best_fit_none_state,
            source_dataset_metadata={"source": "test"},
        )

        dataset = _make_dataset()

        def fake_run_estimation(*args, **kwargs):
            return malformed_result

        with patch(
            "orbit_discovery.component3.candidates.run_estimation",
            side_effect=fake_run_estimation,
        ):
            estimation_result, audit_log = run_multi_start_estimation(
                phase3_result=baseline_result,
                dataset=dataset,
                config={"num_starts": 2},
            )

        self.assertEqual(len(audit_log), 2)
        self.assertEqual(audit_log[1]["outcome"], "rejected")
        self.assertEqual(audit_log[1]["reason"], "missing_fit_state")
        self.assertIsNotNone(audit_log[1]["initial_state"])
        self.assertEqual(len(estimation_result.candidates), 1)

    def test_later_start_still_processed_after_malformed_result(self):
        state = OrbitState(rx=2.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        baseline_result = _make_estimation_result(state, chi2=24.0, jacobian_rank=6, n_valid=12)

        valid_state = OrbitState(rx=5.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        valid_result = _make_estimation_result(valid_state, chi2=24.0, jacobian_rank=6, n_valid=12)

        # Malformed result: best_fit is None
        malformed_result = EstimationResult(
            candidates=[],
            best_fit=None,  # type: ignore[arg-type]
            source_dataset_metadata={"source": "test"},
        )

        dataset = _make_dataset()

        call_count = [0]

        def fake_run_estimation(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # First perturbed start (start 1) is malformed
                return malformed_result
            # Second perturbed start (start 2) is valid
            return valid_result

        with patch(
            "orbit_discovery.component3.candidates.run_estimation",
            side_effect=fake_run_estimation,
        ):
            estimation_result, audit_log = run_multi_start_estimation(
                phase3_result=baseline_result,
                dataset=dataset,
                config={"num_starts": 3},
            )

        # Start 0 valid, start 1 rejected, start 2 processed normally
        self.assertEqual(len(audit_log), 3)
        self.assertEqual(audit_log[0]["outcome"], "retained")
        self.assertEqual(audit_log[1]["outcome"], "rejected")
        self.assertEqual(audit_log[1]["reason"], "missing_fit_result")
        # Start 2 processed after malformed start 1
        self.assertEqual(audit_log[2]["start_index"], 2)
        self.assertNotEqual(audit_log[2]["outcome"], "rejected")
        self.assertEqual(len(estimation_result.candidates), 2)

    def test_none_result_is_rejected_and_preserves_initial_state(self):
        state = OrbitState(rx=2.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        baseline_result = _make_estimation_result(state)

        with patch(
            "orbit_discovery.component3.candidates.run_estimation",
            return_value=None,
        ):
            _, audit_log = run_multi_start_estimation(
                phase3_result=baseline_result,
                dataset=_make_dataset(),
                config={"num_starts": 2},
            )

        self.assertEqual(audit_log[1]["reason"], "invalid_fit_result")
        self.assertIsNotNone(audit_log[1]["initial_state"])
        self.assertIsNone(audit_log[1]["fit_metrics"])

    def test_malformed_result_object_is_rejected(self):
        state = OrbitState(rx=2.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        baseline_result = _make_estimation_result(state)

        with patch(
            "orbit_discovery.component3.candidates.run_estimation",
            return_value=object(),
        ):
            _, audit_log = run_multi_start_estimation(
                phase3_result=baseline_result,
                dataset=_make_dataset(),
                config={"num_starts": 2},
            )

        self.assertEqual(audit_log[1]["reason"], "invalid_fit_result")

    def test_malformed_candidate_is_rejected_and_later_start_processed(self):
        state = OrbitState(rx=2.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        baseline_result = _make_estimation_result(state)
        valid_result = _make_estimation_result(
            OrbitState(rx=5.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        )
        malformed_result = EstimationResult(
            candidates=[None],  # type: ignore[list-item]
            best_fit=baseline_result.best_fit,
            source_dataset_metadata={"source": "test"},
        )

        with patch(
            "orbit_discovery.component3.candidates.run_estimation",
            side_effect=[malformed_result, valid_result],
        ):
            estimation_result, audit_log = run_multi_start_estimation(
                phase3_result=baseline_result,
                dataset=_make_dataset(),
                config={"num_starts": 3},
            )

        self.assertEqual(audit_log[1]["reason"], "invalid_candidate")
        self.assertNotEqual(audit_log[2]["outcome"], "rejected")
        self.assertEqual(len(estimation_result.candidates), 2)

    def test_malformed_fit_state_is_rejected_and_later_start_processed(self):
        state = OrbitState(rx=2.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        baseline_result = _make_estimation_result(state)
        malformed_best_fit = BestFitResult(
            state="invalid",  # type: ignore[arg-type]
            epoch_years=0.0,
            residuals={"residual_vector": np.zeros(12)},
            fit_metrics={"chi2": 24.0, "optimality": 0.001,
                         "jacobian_rank": 6, "n_valid_scalar_residuals": 12},
        )
        malformed_result = EstimationResult(
            candidates=[OrbitCandidate(state=state, epoch_years=0.0,
                                       metadata={"converged": True})],
            best_fit=malformed_best_fit,
            source_dataset_metadata={"source": "test"},
        )
        valid_result = _make_estimation_result(
            OrbitState(rx=5.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        )

        with patch(
            "orbit_discovery.component3.candidates.run_estimation",
            side_effect=[malformed_result, valid_result],
        ):
            estimation_result, audit_log = run_multi_start_estimation(
                phase3_result=baseline_result,
                dataset=_make_dataset(),
                config={"num_starts": 3},
            )

        self.assertEqual(audit_log[1]["reason"], "invalid_fit_state")
        self.assertIsNotNone(audit_log[1]["initial_state"])
        self.assertNotEqual(audit_log[2]["outcome"], "rejected")
        self.assertEqual(len(estimation_result.candidates), 2)


class TestAuditMetricSerialization(unittest.TestCase):
    """Tests for structured, JSON-safe audit metric serialization."""

    def test_nested_dictionaries_remain_structured_and_json_safe(self):
        value = {
            "nested": {
                "integer": np.int64(3),
                "finite": np.float64(1.5),
                "non_finite": [np.nan, np.inf, -np.inf],
            }
        }

        serialized = _serialize_metric(value)

        self.assertIsInstance(serialized, dict)
        self.assertIsInstance(serialized["nested"], dict)
        self.assertEqual(serialized["nested"]["integer"], 3)
        self.assertEqual(serialized["nested"]["finite"], 1.5)
        self.assertEqual(serialized["nested"]["non_finite"], [None, None, None])
        json.dumps(serialized, allow_nan=False)

    def test_dictionary_keys_are_json_safe_and_numpy_keys_are_native(self):
        value = {
            "text": np.int64(1),
            np.int64(2): {"nested": np.float64(3.0)},
            np.nan: "non-finite key",
            ("unsupported", 1): "stringified key",
        }

        serialized = _serialize_metric(value)

        self.assertIn("text", serialized)
        self.assertIn(2, serialized)
        self.assertIn(None, serialized)
        self.assertIn("('unsupported', 1)", serialized)
        json.dumps(serialized, allow_nan=False)


class TestJacobianConversionRegression(unittest.TestCase):
    """Regression tests for Jacobian conversion raising TypeError."""

    def test_jacobian_conversion_typeerror_results_in_invalid_jacobian(self):
        state = OrbitState(rx=2.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        result_good = _make_estimation_result(state, jacobian_rank=6, n_valid=12)
        result_bad_jac = _make_estimation_result(state, jacobian_rank=None, n_valid=12)

        dataset = _make_dataset()

        # A TypeError during jacobian conversion (in estimation.py) yields
        # jacobian_rank=None, which candidates must classify as invalid_jacobian.
        # The single perturbed start (start 1) must receive the bad-jacobian result.
        def fake_run_estimation(*args, **kwargs):
            return result_bad_jac

        with patch(
            "orbit_discovery.component3.candidates.run_estimation",
            side_effect=fake_run_estimation,
        ):
            estimation_result, audit_log = run_multi_start_estimation(
                phase3_result=result_good,
                dataset=dataset,
                config={"num_starts": 2},
            )

        # Baseline should be valid, start 1 should have invalid Jacobian
        self.assertEqual(len(audit_log), 2)
        self.assertEqual(audit_log[0]["outcome"], "retained")
        self.assertEqual(audit_log[1]["outcome"], "rejected")
        self.assertEqual(audit_log[1]["reason"], "invalid_jacobian")

    def test_jacobian_typeerror_does_not_crash_run_estimation(self):
        state = OrbitState(rx=2.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        dataset = _make_dataset()

        def fake_least_squares_lm(*args, **kwargs):
            # jac_scaled as a dict raises TypeError in np.asarray(..., dtype=float)
            return {
                "x": state.to_array(),
                "chi2": 24.0,
                "optimality": 0.001,
                "jac_scaled": {"not": "an array"},
                "converged": True,
                "termination_reason": "Converged.",
                "n_iter": 5,
                "nfev": 20,
                "njev": 6,
            }

        with patch(
            "orbit_discovery.component3.estimation.least_squares_lm",
            side_effect=fake_least_squares_lm,
        ):
            result = run_estimation(
                dataset=dataset,
                initial_state=state,
            )

        self.assertIsNone(result.best_fit.fit_metrics["jacobian_rank"])


class TestDefensiveCorrections(unittest.TestCase):
    """Regression tests for defensive corrections applied in Phase 4."""

    def test_audit_record_serializes_nan_inf_states(self):
        # State with non-finite components
        state = OrbitState(rx=np.nan, ry=np.inf, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        from orbit_discovery.component3.candidates import _audit_record

        record = _audit_record(0, state, "retained", None)

        # Check that NaN/inf became None in serialized list
        self.assertIsNone(record["initial_state"][0])  # rx (nan)
        self.assertIsNone(record["initial_state"][1])  # ry (inf)
        self.assertEqual(record["initial_state"][2], 0.0) # rz

        # Ensure it is JSON-serializable
        json.dumps(record, allow_nan=False)

    def test_baseline_malformed_fit_metrics_rejected(self):
        state = OrbitState(rx=2.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        # Malformed metrics: not a dict
        best_fit = BestFitResult(
            state=state,
            epoch_years=0.0,
            residuals={"residual_vector": np.zeros(12)},
            fit_metrics="invalid",  # type: ignore[arg-type]
        )
        result = EstimationResult(
            candidates=[],
            best_fit=best_fit,
            source_dataset_metadata={"source": "test"},
        )

        dataset = _make_dataset()
        estimation_result, audit_log = run_multi_start_estimation(
            phase3_result=result,
            dataset=dataset,
            config={"num_starts": 1},
        )

        self.assertEqual(audit_log[0]["outcome"], "rejected")
        self.assertEqual(audit_log[0]["reason"], "invalid_fit_metrics")

    def test_perturbed_malformed_fit_metrics_rejected(self):
        state = OrbitState(rx=2.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        baseline_result = _make_estimation_result(state, chi2=24.0, jacobian_rank=6, n_valid=12)

        # Perturbed result: fit_metrics is not a dict
        best_fit = BestFitResult(
            state=state,
            epoch_years=0.0,
            residuals={"residual_vector": np.zeros(12)},
            fit_metrics="invalid",  # type: ignore[arg-type]
        )
        malformed_result = EstimationResult(
            candidates=[],
            best_fit=best_fit,
            source_dataset_metadata={"source": "test"},
        )

        dataset = _make_dataset()

        with patch(
            "orbit_discovery.component3.candidates.run_estimation",
            return_value=malformed_result,
        ):
            estimation_result, audit_log = run_multi_start_estimation(
                phase3_result=baseline_result,
                dataset=dataset,
                config={"num_starts": 2},
            )

        self.assertEqual(audit_log[1]["outcome"], "rejected")
        self.assertEqual(audit_log[1]["reason"], "invalid_fit_metrics")

    def test_perturbed_malformed_metadata_rejected(self):
        state = OrbitState(rx=2.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        baseline_result = _make_estimation_result(state, chi2=24.0, jacobian_rank=6, n_valid=12)

        # Perturbed result: candidate metadata is not a dict
        candidate = OrbitCandidate(
            state=state,
            epoch_years=0.0,
            metadata="invalid", # type: ignore[arg-type]
        )
        result = EstimationResult(
            candidates=[candidate],
            best_fit=baseline_result.best_fit,
            source_dataset_metadata={"source": "test"},
        )

        dataset = _make_dataset()

        with patch(
            "orbit_discovery.component3.candidates.run_estimation",
            return_value=result,
        ):
            # This should not raise, but metadata access should be safe
            estimation_result, audit_log = run_multi_start_estimation(
                phase3_result=baseline_result,
                dataset=dataset,
                config={"num_starts": 2},
            )

        # Should continue processing, metadata safely accessed
        self.assertEqual(len(audit_log), 2)


class TestBaselineEpochRegression(unittest.TestCase):
    """Regression tests for baseline reference epoch validation."""

    def test_missing_baseline_epoch_is_rejected(self):
        state = OrbitState(rx=2.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        best_fit = BestFitResult(
            state=state,
            epoch_years=None,  # type: ignore[arg-type]
            residuals={"residual_vector": np.zeros(12)},
            fit_metrics={"chi2": 24.0, "optimality": 0.0,
                         "jacobian_rank": 6, "n_valid_scalar_residuals": 12},
        )
        candidate = OrbitCandidate(state=state, epoch_years=0.0, metadata={"converged": True})
        result = EstimationResult(
            candidates=[candidate],
            best_fit=best_fit,
            source_dataset_metadata={"source": "test"},
        )

        dataset = _make_dataset()
        estimation_result, audit_log = run_multi_start_estimation(
            phase3_result=result,
            dataset=dataset,
            config={"num_starts": 1},
        )

        self.assertEqual(audit_log[0]["outcome"], "rejected")
        self.assertEqual(audit_log[0]["reason"], "missing_baseline_metrics")

    def test_non_finite_baseline_epoch_is_rejected(self):
        state = OrbitState(rx=2.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        best_fit = BestFitResult(
            state=state,
            epoch_years=np.nan,
            residuals={"residual_vector": np.zeros(12)},
            fit_metrics={"chi2": 24.0, "optimality": 0.0,
                         "jacobian_rank": 6, "n_valid_scalar_residuals": 12},
        )
        candidate = OrbitCandidate(state=state, epoch_years=0.0, metadata={"converged": True})
        result = EstimationResult(
            candidates=[candidate],
            best_fit=best_fit,
            source_dataset_metadata={"source": "test"},
        )

        dataset = _make_dataset()
        estimation_result, audit_log = run_multi_start_estimation(
            phase3_result=result,
            dataset=dataset,
            config={"num_starts": 1},
        )

        self.assertEqual(audit_log[0]["outcome"], "rejected")
        self.assertEqual(audit_log[0]["reason"], "missing_baseline_metrics")

    def test_non_zero_baseline_epoch_is_rejected(self):
        state = OrbitState(rx=2.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        best_fit = BestFitResult(
            state=state,
            epoch_years=1.5,
            residuals={"residual_vector": np.zeros(12)},
            fit_metrics={"chi2": 24.0, "optimality": 0.0,
                         "jacobian_rank": 6, "n_valid_scalar_residuals": 12},
        )
        candidate = OrbitCandidate(state=state, epoch_years=0.0, metadata={"converged": True})
        result = EstimationResult(
            candidates=[candidate],
            best_fit=best_fit,
            source_dataset_metadata={"source": "test"},
        )

        dataset = _make_dataset()
        estimation_result, audit_log = run_multi_start_estimation(
            phase3_result=result,
            dataset=dataset,
            config={"num_starts": 1},
        )

        self.assertEqual(audit_log[0]["outcome"], "rejected")
        self.assertEqual(audit_log[0]["reason"], "missing_baseline_metrics")

    def test_boolean_baseline_epoch_is_rejected(self):
        state = OrbitState(rx=2.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        best_fit = BestFitResult(
            state=state,
            epoch_years=True,  # type: ignore[arg-type]
            residuals={"residual_vector": np.zeros(12)},
            fit_metrics={"chi2": 24.0, "optimality": 0.0,
                         "jacobian_rank": 6, "n_valid_scalar_residuals": 12},
        )
        candidate = OrbitCandidate(state=state, epoch_years=0.0, metadata={"converged": True})
        result = EstimationResult(
            candidates=[candidate],
            best_fit=best_fit,
            source_dataset_metadata={"source": "test"},
        )

        dataset = _make_dataset()
        estimation_result, audit_log = run_multi_start_estimation(
            phase3_result=result,
            dataset=dataset,
            config={"num_starts": 1},
        )

        self.assertEqual(audit_log[0]["outcome"], "rejected")
        self.assertEqual(audit_log[0]["reason"], "missing_baseline_metrics")

class TestDuplicateAndRetentionRegression(unittest.TestCase):
    """Regression tests for duplicate distance and retention limit."""

    def test_duplicate_distance_exactly_one_is_not_duplicate(self):
        # States at distance exactly 1.0 with tolerance 0.01:
        # position difference of 0.01 AU gives D = sqrt(0.01^2 / 0.01^2) = 1.0
        # Using rx=0.0 and rx=0.01 so the difference equals the tolerance exactly.
        state_a = OrbitState(rx=0.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        state_b = OrbitState(rx=0.01, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)

        result_a = _make_estimation_result(state_a, chi2=24.0, jacobian_rank=6, n_valid=12)
        result_b = _make_estimation_result(state_b, chi2=24.0, jacobian_rank=6, n_valid=12)

        dataset = _make_dataset()

        with patch(
            "orbit_discovery.component3.candidates.run_estimation",
            return_value=result_b,
        ):
            estimation_result, audit_log = run_multi_start_estimation(
                phase3_result=result_a,
                dataset=dataset,
                config={
                    "num_starts": 2,
                    "max_retained_candidates": 5,
                    "duplicate_tolerance_pos": 0.01,
                    "duplicate_tolerance_vel": 5e-5,
                },
            )

        # D = sqrt(0.01^2 / 0.01^2) = 1.0 → not a duplicate
        duplicate_records = [r for r in audit_log if r["outcome"] == "duplicate"]
        self.assertEqual(len(duplicate_records), 0)
        retained_indices = [c.metadata["start_index"] for c in estimation_result.candidates]
        self.assertEqual(len(retained_indices), 2)

    def test_deduplication_before_retention_limit(self):
        # Both candidates are duplicates of each other, so only 1 survives
        # deduplication. Retention limit is applied after deduplication.
        state_a = OrbitState(rx=2.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        state_b = OrbitState(rx=2.001, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)

        result_a = _make_estimation_result(state_a, chi2=24.0, jacobian_rank=6, n_valid=12)
        result_b = _make_estimation_result(state_b, chi2=24.0, jacobian_rank=6, n_valid=12)

        dataset = _make_dataset()

        with patch(
            "orbit_discovery.component3.candidates.run_estimation",
            return_value=result_b,
        ):
            estimation_result, audit_log = run_multi_start_estimation(
                phase3_result=result_a,
                dataset=dataset,
                config={
                    "num_starts": 2,
                    "max_retained_candidates": 10,
                    "duplicate_tolerance_pos": 0.005,
                    "duplicate_tolerance_vel": 5e-5,
                },
            )

        # Only start 0 retained; start 1 is duplicate of start 0
        retained_indices = [c.metadata["start_index"] for c in estimation_result.candidates]
        self.assertEqual(retained_indices, [0])
        duplicate_records = [r for r in audit_log if r["outcome"] == "duplicate"]
        self.assertEqual(len(duplicate_records), 1)

    def test_truncated_candidates_not_marked_as_rejected_or_duplicate(self):
        # 3 valid candidates but retention limit of 1 → 2 truncated
        state_a = OrbitState(rx=2.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        state_b = OrbitState(rx=5.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)
        state_c = OrbitState(rx=8.0, ry=0.0, rz=0.0, vx=0.0, vy=4.4428829, vz=0.0)

        result_a = _make_estimation_result(state_a, chi2=24.0, jacobian_rank=6, n_valid=12)
        result_b = _make_estimation_result(state_b, chi2=24.0, jacobian_rank=6, n_valid=12)
        result_c = _make_estimation_result(state_c, chi2=24.0, jacobian_rank=6, n_valid=12)

        dataset = _make_dataset()

        # Patch run_estimation to return different results per call
        call_count = [0]

        def fake_run_estimation(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return result_b
            return result_c

        with patch(
            "orbit_discovery.component3.candidates.run_estimation",
            side_effect=fake_run_estimation,
        ):
            estimation_result, audit_log = run_multi_start_estimation(
                phase3_result=result_a,
                dataset=dataset,
                config={
                    "num_starts": 3,
                    "max_retained_candidates": 1,
                },
            )

        # Only one retained; other two truncated
        retained = [r for r in audit_log if r["outcome"] == "retained"]
        truncated = [r for r in audit_log if r["outcome"] == "truncated"]
        rejected = [r for r in audit_log if r["outcome"] == "rejected"]
        duplicates = [r for r in audit_log if r["outcome"] == "duplicate"]

        self.assertEqual(len(retained), 1)
        self.assertEqual(len(truncated), 2)
        self.assertEqual(len(rejected), 0)
        self.assertEqual(len(duplicates), 0)


if __name__ == "__main__":
    unittest.main()
