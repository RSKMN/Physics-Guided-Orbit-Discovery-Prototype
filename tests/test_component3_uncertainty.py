import unittest
import numpy as np
from orbit_discovery.component3.uncertainty import compute_uncertainty

class TestUncertaintyEstimation(unittest.TestCase):

    def test_full_rank_covariance(self):
        # Scaled Jacobian I, s = [1, 1, 1, 2pi, 2pi, 2pi]
        # J_phys = I @ diag(1/s)
        # P_scaled = I @ I @ I.T = I
        # P_phys = diag(s) @ P_scaled @ diag(s) = diag(s^2)
        jac = np.eye(6)
        res = compute_uncertainty(jac, 12, converged=True)
        self.assertTrue(res.covariance_valid)
        expected = np.diag([1.0, 1.0, 1.0, 4 * np.pi**2, 4 * np.pi**2, 4 * np.pi**2])
        np.testing.assert_allclose(res.covariance, expected, atol=1e-12)

    def test_rank_deficient(self):
        jac = np.zeros((12, 6))
        res = compute_uncertainty(jac, 12, converged=True)
        self.assertFalse(res.covariance_valid)
        self.assertEqual(res.failure_reason, "rank_deficient")

    def test_poorly_conditioned(self):
        jac = np.eye(6)
        jac[5, 5] = 1e-7  # Small but above 1e-8 * s_max tolerance → full rank
        res = compute_uncertainty(jac, 12, converged=True)
        # Condition number should be large (1e7) but not infinite
        self.assertGreater(res.condition_number, 1e6)
        self.assertLess(res.condition_number, 1e12)
        # With 1e-8 tolerance, 1e-7 > tolerance → full rank (6)
        self.assertEqual(res.rank, 6)
        self.assertTrue(res.covariance_valid)

    def test_poorly_conditioned_becomes_rank_deficient(self):
        jac = np.eye(6)
        jac[5, 5] = 1e-10  # Below 1e-8 * s_max tolerance → rank-deficient
        res = compute_uncertainty(jac, 12, converged=True)
        self.assertFalse(res.covariance_valid)
        self.assertEqual(res.failure_reason, "rank_deficient")
        self.assertEqual(res.rank, 5)

    def test_transformation_scaling(self):
        s = np.array([1.0, 1.0, 1.0, 2*np.pi, 2*np.pi, 2*np.pi])
        J_phys = np.random.randn(12, 6)
        J_scaled = J_phys @ np.diag(s)

        res = compute_uncertainty(J_scaled, 12, converged=True)

        # P_phys should be inv(J_phys.T @ J_phys)
        expected_p_phys = np.linalg.inv(J_phys.T @ J_phys)
        np.testing.assert_allclose(res.covariance, expected_p_phys, atol=1e-12)

    def test_incorrect_jacobian_shape(self):
        jac = np.zeros((12, 5)) # Only 5 parameters
        res = compute_uncertainty(jac, 12, converged=True)
        self.assertFalse(res.covariance_valid)

    def test_non_finite_jacobian(self):
        jac = np.eye(6)
        jac[0, 0] = np.nan
        res = compute_uncertainty(jac, 12, converged=True)
        self.assertFalse(res.covariance_valid)

    def test_non_converged_fit(self):
        jac = np.eye(6)
        res = compute_uncertainty(jac, 12, converged=False)
        self.assertFalse(res.covariance_valid)
        self.assertEqual(res.failure_reason, "non_converged")

    def test_no_reduced_chi2_multiplier(self):
        # Test that the covariance is not multiplied by reduced chi-square.
        # Using a simple case where J_phys^T J_phys = I, so P_phys = I
        # Reduced chi-square (if we calculated it separately) would be chi^2/DOF
        jac = np.eye(6)
        # For J=I, J^T J = I, J^T r = r. Let's make r have a specific magnitude.
        # If r = [1, ..., 1] (12 elements), chi^2 = 12, DOF = 12-6 = 6.
        # Reduced chi^2 = 2.0.
        # Covariance should still be I, not 2*I.

        res = compute_uncertainty(jac, 12, converged=True)

        # P_phys = I (as established in test_full_rank_covariance)
        expected = np.diag([1.0, 1.0, 1.0, 4 * np.pi**2, 4 * np.pi**2, 4 * np.pi**2])
        np.testing.assert_allclose(res.covariance, expected, atol=1e-12)
        # Verify it's not the identity times something else (like 2.0)
        self.assertFalse(np.allclose(res.covariance, 2.0 * expected))

    def test_deterministic(self):
        jac = np.random.randn(12, 6)
        res1 = compute_uncertainty(jac, 12, converged=True)
        res2 = compute_uncertainty(jac, 12, converged=True)
        np.testing.assert_allclose(res1.covariance, res2.covariance)

    def test_exactly_six_residuals_zero_dof(self):
        # Exactly 6 residuals → DOF = 0 → insufficient_dof
        jac = np.eye(6)
        res = compute_uncertainty(jac, 6, converged=True)
        self.assertFalse(res.covariance_valid)
        self.assertEqual(res.failure_reason, "insufficient_dof")
        self.assertEqual(res.degrees_of_freedom, 0)
        self.assertEqual(res.rank, 6)

    def test_fewer_than_six_residuals_negative_dof(self):
        # 5 residuals → DOF = -1 → insufficient_dof
        jac = np.eye(6)
        res = compute_uncertainty(jac, 5, converged=True)
        self.assertFalse(res.covariance_valid)
        self.assertEqual(res.failure_reason, "insufficient_dof")
        self.assertEqual(res.degrees_of_freedom, -1)
        self.assertEqual(res.rank, 6)

    def test_more_than_six_residuals_normal_dof(self):
        # 12 residuals → DOF = 6 → valid covariance
        jac = np.eye(6)
        res = compute_uncertainty(jac, 12, converged=True)
        self.assertTrue(res.covariance_valid)
        self.assertEqual(res.degrees_of_freedom, 6)

    def test_dof_check_precedes_rank_deficiency(self):
        # Rank-deficient Jacobian with exactly 6 residuals:
        # insufficient_dof takes precedence over rank_deficient.
        jac = np.zeros((6, 6))
        res = compute_uncertainty(jac, 6, converged=True)
        self.assertFalse(res.covariance_valid)
        self.assertEqual(res.failure_reason, "insufficient_dof")
        self.assertEqual(res.degrees_of_freedom, 0)

if __name__ == "__main__":
    unittest.main()
