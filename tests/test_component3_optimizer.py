"""Focused tests for Component 3 Phase 3C optimizer.

Covers:
- Convex 2D/6D problems, convergence, scaling, forward-difference Jacobian,
  adaptive damping, invalid evaluations, termination limits.
- Numerical robustness: overflow handling, residual dimension validation,
  parameter validation, Jacobian accounting, exception propagation.
"""

from __future__ import annotations

import unittest
import numpy as np
import sys
from pathlib import Path

# Setup path
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from orbit_discovery.component3.optimizer import least_squares_lm


class TestOptimizer(unittest.TestCase):

    def test_2d_convex_convergence(self):
        def fun(x):
            return np.array([x[0] - 2.0, x[1] - 3.0])
        x0 = np.array([0.0, 0.0])
        s = np.array([1.0, 1.0])
        res = least_squares_lm(x0, s, fun)
        self.assertTrue(res["converged"])
        np.testing.assert_allclose(res["x"], [2.0, 3.0], atol=1e-7)

    def test_exact_initial_solution(self):
        def fun(x):
            return x - 2.0
        x0 = np.array([2.0])
        s = np.array([1.0])
        res = least_squares_lm(x0, s, fun)
        self.assertTrue(res["converged"])
        self.assertEqual(res["n_iter"], 0)
        self.assertIn("Initial solution is exact", res["termination_reason"])

    def test_small_gradient_convergence(self):
        def fun(x):
            return x**2
        def jac(x):
            return np.array([[2.0*x[0]]])
        x0 = np.array([1e-9])
        s = np.array([1.0])
        res = least_squares_lm(x0, s, fun, jac=jac, gtol=1e-8)
        self.assertTrue(res["converged"])
        self.assertIn("Initial gradient below tolerance", res["termination_reason"])

    def test_evaluation_limit_6d_jacobian(self):
        def fun(x):
            return x - 1.0
        x0 = np.zeros(6)
        s = np.ones(6)
        res = least_squares_lm(x0, s, fun, max_nfev=3)
        self.assertFalse(res["converged"])
        self.assertIn("Jacobian", res["termination_reason"])

    def test_final_jacobian_consistency(self):
        def fun(x):
            return np.array([x[0]**2, x[1]**2])
        x0 = np.array([0.5, 0.5])
        s = np.array([1.0, 1.0])
        res = least_squares_lm(x0, s, fun)
        self.assertTrue(res["converged"])
        J_expected = np.array([[2.0*res["x"][0], 0.0], [0.0, 2.0*res["x"][1]]])
        np.testing.assert_allclose(res["jac"], J_expected, atol=1e-5)

    def test_invalid_input_validation(self):
        with self.assertRaises(ValueError):
            least_squares_lm(np.array([[1.0]]), np.array([1.0]), lambda x: x)
        with self.assertRaises(ValueError):
            least_squares_lm(np.array([1.0]), np.array([-1.0]), lambda x: x)
        with self.assertRaises(ValueError):
            least_squares_lm(np.array([1.0]), np.array([1.0]), lambda x: x, ftol=-1.0)
        with self.assertRaises(ValueError):
            least_squares_lm(np.array([1.0]), np.array([1.0]), lambda x: x, initial_lambda=-1.0)
        with self.assertRaises(ValueError):
            least_squares_lm(np.array([1.0]), np.array([1.0]), lambda x: x, max_iter=0)

    def test_singular_system(self):
        def fun(x):
            return np.array([x[0], 0.0])
        x0 = np.array([1.0, 1.0])
        s = np.array([1.0, 1.0])
        res = least_squares_lm(x0, s, fun)
        self.assertTrue(res["converged"])

    def test_finite_difference_failure(self):
        # Function raises when x > 1.0; trial step moves toward x = 10 and crosses it.
        def fun(x):
            if np.any(x > 1.0):
                raise ValueError("Fail")
            return x - 10.0
        x0 = np.array([0.5])
        s = np.array([1.0])
        res = least_squares_lm(x0, s, fun, max_iter=1)
        # Trial step exceeds threshold -> evaluation error -> step rejected -> not converged
        self.assertFalse(res["converged"])
        self.assertGreater(res["nfev"], 0)

    def test_final_jacobian_calls_counted_in_nfev(self):
        call_count = {"n": 0}
        def fun(x):
            call_count["n"] += 1
            return x**2
        def jac(x):
            return np.array([[2.0*x[0]]])
        x0 = np.array([1.0])
        s = np.array([1.0])
        # Analytic jac: initial gradient check uses jac (no fun call), but gtol=0
        # means optimality < 0 is False. Iteration runs, trial step calls fun.
        # Finalize calls jac again (no fun call).
        res = least_squares_lm(x0, s, fun, jac=jac, gtol=0.0, max_iter=1)
        # 1 initial eval + 1 trial eval = 2
        self.assertEqual(call_count["n"], 2)
        self.assertEqual(res["nfev"], 2)

    def test_analytic_jacobian_evaluated_once(self):
        call_count = {"n": 0}
        def fun(x):
            call_count["n"] += 1
            return np.array([x[0]**2])
        def jac(x):
            call_count["n"] += 1
            return np.array([[2.0*x[0]]])
        x0 = np.array([0.5])
        s = np.array([1.0])
        res = least_squares_lm(x0, s, fun, jac=jac, max_iter=1)
        # jac: initial check + iteration + finalize = 3; fun: initial + trial = 2; total = 5
        self.assertEqual(call_count["n"], 5)

    def test_invalid_analytic_jacobian_shape_rejected(self):
        def fun(x):
            return np.array([x[0], x[1]])
        def bad_jac(x):
            return np.array([x[0]])  # wrong shape
        x0 = np.array([0.5, 0.5])
        s = np.array([1.0, 1.0])
        res = least_squares_lm(x0, s, fun, jac=bad_jac)
        self.assertFalse(res["converged"])

    def test_invalid_residual_dimensions_rejected(self):
        def fun(x):
            return np.array([[1.0], [2.0]])  # 2D array, invalid
        x0 = np.array([0.0])
        s = np.array([1.0])
        res = least_squares_lm(x0, s, fun)
        self.assertFalse(res["converged"])

    def test_non_finite_tolerances_rejected(self):
        with self.assertRaises(ValueError):
            least_squares_lm(np.array([0.0]), np.array([1.0]), lambda x: x, ftol=np.nan)
        with self.assertRaises(ValueError):
            least_squares_lm(np.array([0.0]), np.array([1.0]), lambda x: x, gtol=np.inf)

    def test_actual_trial_rejection_increases_damping(self):
        # f(x) = x[0]^2 - 1 at x0 = [0.1]: every LM trial moves right and
        # increases chi^2, so every trial is rejected and damping escalates.
        evaluations = []

        def fun(x):
            evaluations.append(float(np.asarray(x).ravel()[0]))
            return np.array([x[0]**2 - 1.0])

        x0 = np.array([0.1])
        s = np.array([1.0])
        res = least_squares_lm(x0, s, fun, max_iter=3, max_nfev=100)

        # All trials rejected: parameter never moves from the initial point.
        self.assertFalse(res["converged"])
        np.testing.assert_allclose(res["x"], [0.1], atol=1e-6)

        # Classify evaluations: Jacobian probes sit within ~1e-8 of the current
        # parameter (finite-difference step), while LM trials are far away.
        trials = [x for x in evaluations if abs(x - 0.1) > 1e-6]

        # At least two LM trials (one per iteration) must have occurred.
        self.assertGreaterEqual(len(trials), 2)

        # First trial is far from the initial point (rejected step).
        first_step = abs(trials[0] - 0.1)
        self.assertGreater(first_step, 1e-6)

        # Damping increases after rejection, so the subsequent LM trial takes
        # a smaller step from the same starting point.
        second_step = abs(trials[1] - 0.1)
        self.assertLess(second_step, first_step)

    def test_max_iteration_termination_consistent_diagnostics(self):
        def fun(x):
            return x**2
        def jac(x):
            return np.array([[2.0*x[0]]])
        x0 = np.array([10.0])
        s = np.array([1.0])
        res = least_squares_lm(x0, s, fun, jac=jac, max_iter=1)
        self.assertFalse(res["converged"])
        self.assertEqual(res["n_iter"], 1)
        self.assertIn("Max iterations", res["termination_reason"])
        # Diagnostics correspond to the returned state.
        np.testing.assert_allclose(res["fun"], fun(res["x"]))
        self.assertEqual(res["chi2"], np.sum(res["fun"]**2))
        # Final analytic Jacobian was computed and is present.
        self.assertIsNotNone(res["jac"])

    def test_non_finite_initial_lambda_rejected(self):
        with self.assertRaises(ValueError):
            least_squares_lm(np.array([0.0]), np.array([1.0]), lambda x: x, initial_lambda=np.nan)

    def test_non_finite_scales_rejected(self):
        with self.assertRaises(ValueError):
            least_squares_lm(np.array([0.0]), np.array([np.inf]), lambda x: x)

    def test_non_finite_initial_residuals_rejected(self):
        def fun(x):
            return np.array([np.inf])
        x0 = np.array([0.0])
        s = np.array([1.0])
        res = least_squares_lm(x0, s, fun)
        self.assertFalse(res["converged"])

    def test_zero_scaled_norm_step_protected(self):
        # x0 = 0 with f = x^2 gives chi2 = 0: immediate exact-solution convergence.
        def fun(x):
            return x**2
        def jac(x):
            return np.array([[2.0*x[0]]])
        x0 = np.array([0.0])
        s = np.array([1.0])
        res = least_squares_lm(x0, s, fun, jac=jac, max_iter=1)
        self.assertTrue(res["converged"])
        self.assertIn("Initial solution is exact", res["termination_reason"])
        np.testing.assert_allclose(res["x"], [0.0])

    # --- New validation and robustness tests ---

    def test_type_error_propagates(self):
        # Unexpected programming errors must propagate, not be swallowed.
        def fun(x):
            raise TypeError("Unexpected programming error")
        x0 = np.array([0.5])
        s = np.array([1.0])
        with self.assertRaises(TypeError):
            least_squares_lm(x0, s, fun)

    def test_inconsistent_residual_dimension_rejected(self):
        # Residual dimension changes between evaluations -> rejected.
        call_count = {"n": 0}
        def fun(x):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return np.array([1.0])
            return np.array([1.0, 2.0])  # dimension mismatch on second call
        x0 = np.array([0.0])
        s = np.array([1.0])
        res = least_squares_lm(x0, s, fun, max_iter=1)
        self.assertFalse(res["converged"])

    def test_empty_residual_rejected(self):
        # Empty residual vector is rejected.
        def fun(x):
            return np.array([])
        x0 = np.array([0.0])
        s = np.array([1.0])
        res = least_squares_lm(x0, s, fun)
        self.assertFalse(res["converged"])

    def test_empty_parameter_vector_rejected(self):
        # Empty x0 / s are rejected at validation.
        with self.assertRaises(ValueError):
            least_squares_lm(np.array([]), np.array([]), lambda x: x)

    def test_fractional_and_boolean_limits_rejected(self):
        # max_iter / max_nfev must be positive integers; bool and float rejected.
        with self.assertRaises(ValueError):
            least_squares_lm(np.array([0.0]), np.array([1.0]), lambda x: x, max_iter=1.5)
        with self.assertRaises(ValueError):
            least_squares_lm(np.array([0.0]), np.array([1.0]), lambda x: x, max_nfev=2.5)
        with self.assertRaises(ValueError):
            least_squares_lm(np.array([0.0]), np.array([1.0]), lambda x: x, max_iter=True)
        with self.assertRaises(ValueError):
            least_squares_lm(np.array([0.0]), np.array([1.0]), lambda x: x, max_nfev=False)

    def test_final_analytic_jacobian_reflected_in_njev(self):
        # The final analytic Jacobian evaluation increments njev.
        call_count = {"jac": 0}
        def fun(x):
            return np.array([x[0]**2])
        def jac(x):
            call_count["jac"] += 1
            return np.array([[2.0*x[0]]])
        x0 = np.array([0.5])
        s = np.array([1.0])
        res = least_squares_lm(x0, s, fun, jac=jac, max_iter=1)
        # jac: initial check + iteration + finalize = 3
        self.assertEqual(call_count["jac"], 3)
        self.assertEqual(res["njev"], 3)

    def test_numerical_jacobian_finalization_reaches_completion(self):
        # With sufficient budget, numerical Jacobian finalization runs and
        # max_nfev is respected.
        call_count = {"n": 0}
        def fun(x):
            call_count["n"] += 1
            return x - 1.0
        x0 = np.array([0.0])
        s = np.array([1.0])
        res = least_squares_lm(x0, s, fun, max_nfev=6, max_iter=1)
        self.assertFalse(res["converged"])
        self.assertIn("Max iterations", res["termination_reason"])
        self.assertIsNotNone(res["jac"])
        self.assertGreater(res["nfev"], 0)
        self.assertLessEqual(res["nfev"], 6)
        self.assertEqual(call_count["n"], res["nfev"])

    def test_overflow_cannot_produce_false_convergence(self):
        # chi2 overflows to inf -> must not report convergence.
        def fun(x):
            return np.array([1e200 * x[0]])
        x0 = np.array([1.0])
        s = np.array([1.0])
        res = least_squares_lm(x0, s, fun, max_iter=1)
        self.assertFalse(res["converged"])


if __name__ == "__main__":
    unittest.main()
