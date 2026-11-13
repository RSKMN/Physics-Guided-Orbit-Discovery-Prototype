"""Focused tests for Component 3 Phase 3B residuals module.

Covers:
- RA wraparound (branch cut at RA = 0/360)
- Declination difference (no wrapping)
- Pole screening (|cos(dec)| threshold)
- Residual computation (cos(dec) applied once, arcsec conversion, normalization)
- Chi-square objective
- Module constants
"""

from __future__ import annotations

import math
import unittest

import numpy as np

import sys as _sys
from pathlib import Path as _Path

_REPO_ROOT = _Path(__file__).resolve().parents[1]
_SRC_DIR = _REPO_ROOT / "src"
for _path in (_REPO_ROOT, _SRC_DIR):
    if str(_path) not in _sys.path:
        _sys.path.insert(0, str(_path))

from orbit_discovery.component3.residuals import (
    ARCCSEC_PER_DEGREE,
    POLE_COS_DEC_THRESHOLD,
    chi_square,
    compute_residuals,
    declination_difference,
    pole_screen_mask,
    wrap_ra_difference,
)


class WrapRADifferenceTests(unittest.TestCase):
    """Tests for wrap_ra_difference: branch-cut handling at RA = 0/360."""

    def test_small_positive_difference_unchanged(self):
        self.assertAlmostEqual(wrap_ra_difference(10.0), 10.0)

    def test_small_negative_difference_unchanged(self):
        self.assertAlmostEqual(wrap_ra_difference(-10.0), -10.0)

    def test_wrap_positive_above_180(self):
        # 200 deg should wrap to -160 deg (shortest angular distance).
        self.assertAlmostEqual(wrap_ra_difference(200.0), -160.0)

    def test_wrap_negative_below_minus_180(self):
        # -200 deg should wrap to +160 deg.
        self.assertAlmostEqual(wrap_ra_difference(-200.0), 160.0)

    def test_exactly_plus_180_maps_to_minus_180(self):
        # Range is [-180, 180): +180 maps to -180.
        self.assertAlmostEqual(wrap_ra_difference(180.0), -180.0)

    def test_branch_cut_ra_0_360(self):
        # Observed 1 deg, predicted 359 deg: raw diff = -358, wrap to +2 deg.
        self.assertAlmostEqual(wrap_ra_difference(1.0 - 359.0), 2.0)

    def test_branch_cut_ra_360_0(self):
        # Observed 359 deg, predicted 1 deg: raw diff = +358, wrap to -2 deg.
        self.assertAlmostEqual(wrap_ra_difference(359.0 - 1.0), -2.0)

    def test_identity_returns_zero(self):
        self.assertAlmostEqual(wrap_ra_difference(0.0), 0.0)

    def test_array_input(self):
        result = wrap_ra_difference(np.array([10.0, 200.0, -200.0, 180.0]))
        expected = np.array([10.0, -160.0, 160.0, -180.0])
        np.testing.assert_allclose(result, expected)


class DeclinationDifferenceTests(unittest.TestCase):
    """Tests for declination_difference: dec_obs - dec_pred, no wrapping."""

    def test_simple_difference(self):
        self.assertAlmostEqual(declination_difference(30.0, 20.0), 10.0)

    def test_negative_difference(self):
        self.assertAlmostEqual(declination_difference(20.0, 30.0), -10.0)

    def test_bounds(self):
        # Both in [-90, 90], difference bounded by [-180, 180].
        self.assertAlmostEqual(declination_difference(90.0, -90.0), 180.0)
        self.assertAlmostEqual(declination_difference(-90.0, 90.0), -180.0)

    def test_array_input(self):
        result = declination_difference(
            np.array([30.0, 45.0]), np.array([20.0, 50.0])
        )
        expected = np.array([10.0, -5.0])
        np.testing.assert_allclose(result, expected)


class PoleScreenTests(unittest.TestCase):
    """Tests for pole_screen_mask: |cos(dec)| threshold at the poles."""

    def test_equator_retained(self):
        # cos(0) = 1 >= threshold, retained.
        self.assertTrue(pole_screen_mask(0.0))

    def test_mid_latitude_retained(self):
        self.assertTrue(pole_screen_mask(45.0))

    def test_near_pole_excluded(self):
        # cos(89.9999999 deg) ~ 1.7e-9... actually let's use closer to pole.
        # cos(89.999999999 deg) ~ 1.7e-11 < 1e-12? Let's check at exactly 90.
        self.assertFalse(pole_screen_mask(90.0))
        self.assertFalse(pole_screen_mask(-90.0))

    def test_just_inside_threshold_retained(self):
        # cos(dec) clearly above the threshold (2e-12 >> 1e-12): retained.
        # Using 2x the threshold gives headroom against floating-point round-trip
        # error in degrees <-> radians conversion.
        dec = math.degrees(math.acos(2.0 * POLE_COS_DEC_THRESHOLD))
        self.assertTrue(pole_screen_mask(dec))

    def test_array_input(self):
        result = pole_screen_mask(np.array([0.0, 90.0, -90.0, 45.0]))
        expected = np.array([True, False, False, True])
        np.testing.assert_array_equal(result, expected)

    def test_custom_threshold(self):
        # Threshold 0.5: dec=60 -> cos=0.5 retained; dec=70 -> cos~0.34 excluded.
        self.assertTrue(pole_screen_mask(60.0, threshold=0.5))
        self.assertFalse(pole_screen_mask(70.0, threshold=0.5))


class ResidualsComputationTests(unittest.TestCase):
    """Tests for compute_residuals: weighting, cos(dec) once, arcsec conversion."""

    def test_perfect_match_zero_residuals(self):
        ra_obs = np.array([10.0, 200.0])
        dec_obs = np.array([30.0, -20.0])
        res = compute_residuals(
            ra_obs, dec_obs, ra_obs.copy(), dec_obs.copy(),
            np.array([1.0, 1.0]), np.array([1.0, 1.0]),
        )
        self.assertEqual(res["n_retained"], 2)
        self.assertEqual(res["n_excluded"], 0)
        np.testing.assert_allclose(res["ra_arcsec"], [0.0, 0.0])
        np.testing.assert_allclose(res["dec_arcsec"], [0.0, 0.0])
        np.testing.assert_allclose(res["residual_vector"], [0.0, 0.0, 0.0, 0.0])
        self.assertEqual(res["n_valid_scalar_residuals"], 4)

    def test_ra_wraparound_and_cos_dec_applied_once(self):
        # Known: dra_wrap = 1 deg at dec_obs = 60 deg -> cos=0.5
        # dra_tan_arcsec = 1 * 0.5 * 3600 = 1800 arcsec; sigma = 1 arcsec -> w_ra = 1800.
        ra_obs = np.array([1.0])
        ra_pred = np.array([359.0])  # raw diff -358 -> wrap +2? No: 1 - 359 = -358 -> wrap 2
        # Let's instead pick values giving dra_wrap exactly 1 deg:
        ra_pred = np.array([0.0])  # 1 - 0 = 1 deg, already wrapped
        dec_obs = np.array([60.0])
        dec_pred = np.array([60.0])
        sigma_ra = np.array([1.0])
        sigma_dec = np.array([1.0])
        res = compute_residuals(
            ra_obs, dec_obs, ra_pred, dec_pred, sigma_ra, sigma_dec,
        )
        expected_ra_arcsec = 1.0 * math.cos(math.radians(60.0)) * 3600.0  # 1800.0
        self.assertAlmostEqual(res["ra_arcsec"][0], expected_ra_arcsec)
        self.assertAlmostEqual(res["ra_normalized"][0], expected_ra_arcsec / 1.0)
        # Dec residual zero.
        self.assertAlmostEqual(res["dec_arcsec"][0], 0.0)

    def test_arcsec_conversion(self):
        # 1 deg residual = 3600 arcsec; sigma = 3600 arcsec -> normalized = 1.
        ra_obs = np.array([1.0])
        ra_pred = np.array([0.0])
        dec_obs = np.array([0.0])  # cos(0) = 1
        dec_pred = np.array([0.0])
        sigma_ra = np.array([3600.0])
        sigma_dec = np.array([3600.0])
        res = compute_residuals(
            ra_obs, dec_obs, ra_pred, dec_pred, sigma_ra, sigma_dec,
        )
        self.assertAlmostEqual(res["ra_arcsec"][0], 3600.0)
        self.assertAlmostEqual(res["ra_normalized"][0], 1.0)

    def test_cos_dec_not_double_applied(self):
        # Verify residual = dra_wrap * cos(dec_obs) * 3600 / sigma, i.e. exactly
        # one factor of cos(dec). At dec_obs = 60 deg, cos = 0.5.
        ra_obs = np.array([2.0])
        ra_pred = np.array([0.0])
        dec_obs = np.array([60.0])
        dec_pred = np.array([0.0])
        sigma_ra = np.array([1.0])
        sigma_dec = np.array([1.0])
        res = compute_residuals(
            ra_obs, dec_obs, ra_pred, dec_pred, sigma_ra, sigma_dec,
        )
        expected = 2.0 * math.cos(math.radians(60.0)) * 3600.0  # = 3600.0
        self.assertAlmostEqual(res["ra_arcsec"][0], expected)
        # If cos(dec) were applied twice it would be 2 * 0.5 * 0.5 * 3600 = 1800.
        self.assertNotAlmostEqual(res["ra_arcsec"][0], 1800.0)

    def test_pole_exclusion_removes_both_components(self):
        ra_obs = np.array([10.0, 20.0])
        dec_obs = np.array([0.0, 90.0])  # second observation at pole
        ra_pred = np.array([0.0, 0.0])
        dec_pred = np.array([0.0, 0.0])
        sigma_ra = np.array([1.0, 1.0])
        sigma_dec = np.array([1.0, 1.0])
        res = compute_residuals(
            ra_obs, dec_obs, ra_pred, dec_pred, sigma_ra, sigma_dec,
        )
        self.assertEqual(res["n_retained"], 1)
        self.assertEqual(res["n_excluded"], 1)
        self.assertEqual(res["n_observations"], 2)
        self.assertEqual(res["n_valid_scalar_residuals"], 2)
        # Only the first observation's residuals appear.
        np.testing.assert_allclose(res["valid_mask"], [True, False])

    def test_mismatched_shapes_raise(self):
        with self.assertRaises(ValueError):
            compute_residuals(
                np.array([10.0, 20.0]), np.array([0.0]),
                np.array([0.0, 0.0]), np.array([0.0]),
                np.array([1.0, 1.0]), np.array([1.0, 1.0]),
            )

    def test_nonpositive_uncertainty_raises(self):
        with self.assertRaises(ValueError):
            compute_residuals(
                np.array([10.0]), np.array([0.0]),
                np.array([0.0]), np.array([0.0]),
                np.array([0.0]), np.array([1.0]),
            )

    def test_empty_input_raises(self):
        with self.assertRaises(ValueError):
            compute_residuals(
                np.array([]), np.array([]),
                np.array([]), np.array([]),
                np.array([]), np.array([]),
            )


class ChiSquareTests(unittest.TestCase):
    """Tests for chi_square: chi2 = r^T r."""

    def test_zero_residual_zero_chi2(self):
        self.assertAlmostEqual(chi_square(np.array([0.0, 0.0])), 0.0)

    def test_unit_residuals(self):
        # r = [3, 4] -> chi2 = 9 + 16 = 25.
        self.assertAlmostEqual(chi_square(np.array([3.0, 4.0])), 25.0)

    def test_scalar_input(self):
        self.assertAlmostEqual(chi_square(5.0), 25.0)

    def test_negative_residuals_same_chi2(self):
        self.assertAlmostEqual(chi_square(np.array([-3.0, -4.0])), 25.0)

    def test_empty_vector_raises(self):
        # Chi-square requires a non-empty residual vector.
        with self.assertRaises(ValueError):
            chi_square(np.array([]))

    def test_nan_residual_raises(self):
        with self.assertRaises(ValueError):
            chi_square(np.array([1.0, np.nan, 3.0]))

    def test_infinite_residual_raises(self):
        with self.assertRaises(ValueError):
            chi_square(np.array([1.0, np.inf, -3.0]))


class ChiSquareHandCalculatedTests(unittest.TestCase):
    """Hand-calculated chi-square cross-checks against compute_residuals output."""

    def test_chi_square_matches_residual_vector_dot_product(self):
        ra_obs = np.array([10.0, 20.0, 30.0])
        dec_obs = np.array([5.0, -10.0, 15.0])
        ra_pred = np.array([11.0, 19.0, 31.0])
        dec_pred = np.array([6.0, -11.0, 14.0])
        sigma_ra = np.array([1.0, 1.0, 1.0])
        sigma_dec = np.array([1.0, 1.0, 1.0])
        res = compute_residuals(
            ra_obs, dec_obs, ra_pred, dec_pred, sigma_ra, sigma_dec,
        )
        expected = float(np.dot(res["residual_vector"], res["residual_vector"]))
        self.assertAlmostEqual(chi_square(res["residual_vector"]), expected)


class ChiSquareIntegrationTests(unittest.TestCase):
    """Integration: RA wraparound combined with the observed-dec cosine correction."""

    def test_wraparound_plus_observed_dec_cosine(self):
        # RA crosses the 0/360 branch cut; dec_obs = 60 deg so cos(dec_obs)=0.5
        # is applied exactly once to the wrapped RA residual.
        ra_obs = np.array([1.0])   # just past the branch cut
        ra_pred = np.array([359.0])  # just before the branch cut
        # raw diff = -358 -> wrapped = +2 deg
        dec_obs = np.array([60.0])
        dec_pred = np.array([60.0])
        # sigma_ra = 3600 arcsec so the normalized residual is exactly 1.
        sigma_ra = np.array([3600.0])
        sigma_dec = np.array([1.0])
        res = compute_residuals(
            ra_obs, dec_obs, ra_pred, dec_pred, sigma_ra, sigma_dec,
        )
        expected_ra_arcsec = 2.0 * math.cos(math.radians(60.0)) * 3600.0  # 3600.0
        self.assertAlmostEqual(res["ra_arcsec"][0], expected_ra_arcsec)
        # normalized = 3600 arcsec / 3600 arcsec = 1
        self.assertAlmostEqual(res["ra_normalized"][0], 1.0)
        self.assertAlmostEqual(res["dec_arcsec"][0], 0.0)
        # chi-square equals the single squared normalized residual.
        self.assertAlmostEqual(chi_square(res["residual_vector"]), 1.0)


class ValidationTests(unittest.TestCase):
    """Input-validation tests for angular inputs, declination bounds, and thresholds."""

    def _base_inputs(self):
        return dict(
            ra_obs_deg=np.array([10.0, 20.0]),
            dec_obs_deg=np.array([30.0, 40.0]),
            ra_pred_deg=np.array([10.0, 20.0]),
            dec_pred_deg=np.array([30.0, 40.0]),
            sigma_ra_cosdec_arcsec=np.array([1.0, 1.0]),
            sigma_dec_arcsec=np.array([1.0, 1.0]),
        )

    def test_nan_ra_obs_raises(self):
        inputs = self._base_inputs()
        inputs["ra_obs_deg"] = np.array([np.nan, 20.0])
        with self.assertRaises(ValueError):
            compute_residuals(**inputs)

    def test_inf_ra_obs_raises(self):
        inputs = self._base_inputs()
        inputs["ra_obs_deg"] = np.array([np.inf, 20.0])
        with self.assertRaises(ValueError):
            compute_residuals(**inputs)

    def test_nan_dec_obs_raises(self):
        inputs = self._base_inputs()
        inputs["dec_obs_deg"] = np.array([np.nan, 40.0])
        with self.assertRaises(ValueError):
            compute_residuals(**inputs)

    def test_inf_dec_pred_raises(self):
        inputs = self._base_inputs()
        inputs["dec_pred_deg"] = np.array([30.0, -np.inf])
        with self.assertRaises(ValueError):
            compute_residuals(**inputs)

    def test_nan_ra_pred_raises(self):
        inputs = self._base_inputs()
        inputs["ra_pred_deg"] = np.array([10.0, np.nan])
        with self.assertRaises(ValueError):
            compute_residuals(**inputs)

    def test_inf_sigma_ra_raises(self):
        inputs = self._base_inputs()
        inputs["sigma_ra_cosdec_arcsec"] = np.array([np.inf, 1.0])
        with self.assertRaises(ValueError):
            compute_residuals(**inputs)

    def test_dec_obs_above_90_raises(self):
        inputs = self._base_inputs()
        inputs["dec_obs_deg"] = np.array([91.0, 40.0])
        with self.assertRaises(ValueError):
            compute_residuals(**inputs)

    def test_dec_obs_below_minus_90_raises(self):
        inputs = self._base_inputs()
        inputs["dec_obs_deg"] = np.array([-91.0, 40.0])
        with self.assertRaises(ValueError):
            compute_residuals(**inputs)

    def test_dec_pred_above_90_raises(self):
        inputs = self._base_inputs()
        inputs["dec_pred_deg"] = np.array([30.0, 91.0])
        with self.assertRaises(ValueError):
            compute_residuals(**inputs)

    def test_dec_pred_below_minus_90_raises(self):
        inputs = self._base_inputs()
        inputs["dec_pred_deg"] = np.array([30.0, -91.0])
        with self.assertRaises(ValueError):
            compute_residuals(**inputs)

    def test_boundary_dec_90_accepted(self):
        inputs = self._base_inputs()
        inputs["dec_obs_deg"] = np.array([90.0, 40.0])
        inputs["dec_pred_deg"] = np.array([90.0, 40.0])
        # Exactly at the pole is accepted as input (then screened by mask).
        res = compute_residuals(**inputs)
        self.assertEqual(res["n_retained"], 1)

    def test_boundary_dec_minus_90_accepted(self):
        inputs = self._base_inputs()
        inputs["dec_obs_deg"] = np.array([-90.0, 40.0])
        inputs["dec_pred_deg"] = np.array([-90.0, 40.0])
        res = compute_residuals(**inputs)
        self.assertEqual(res["n_retained"], 1)

    def test_pole_threshold_nan_raises(self):
        inputs = self._base_inputs()
        with self.assertRaises(ValueError):
            pole_screen_mask(np.array([0.0]), threshold=np.nan)

    def test_pole_threshold_inf_raises(self):
        inputs = self._base_inputs()
        with self.assertRaises(ValueError):
            pole_screen_mask(np.array([0.0]), threshold=np.inf)

    def test_pole_threshold_zero_raises(self):
        inputs = self._base_inputs()
        with self.assertRaises(ValueError):
            pole_screen_mask(np.array([0.0]), threshold=0.0)

    def test_pole_threshold_negative_raises(self):
        inputs = self._base_inputs()
        with self.assertRaises(ValueError):
            pole_screen_mask(np.array([0.0]), threshold=-0.5)

    def test_pole_threshold_above_one_raises(self):
        inputs = self._base_inputs()
        with self.assertRaises(ValueError):
            pole_screen_mask(np.array([0.0]), threshold=1.5)

    def test_compute_residuals_invalid_threshold_raises(self):
        inputs = self._base_inputs()
        with self.assertRaises(ValueError):
            compute_residuals(**inputs, pole_threshold=0.0)

    def test_all_observations_excluded_raises(self):
        # Both observations at the pole: |cos(dec)| = 0 < threshold.
        with self.assertRaises(ValueError):
            compute_residuals(
                np.array([10.0, 20.0]),
                np.array([90.0, -90.0]),
                np.array([10.0, 20.0]),
                np.array([90.0, -90.0]),
                np.array([1.0, 1.0]),
                np.array([1.0, 1.0]),
            )


class ConstantsTests(unittest.TestCase):
    """Tests for module-level constants."""

    def test_pole_threshold_value(self):
        self.assertAlmostEqual(POLE_COS_DEC_THRESHOLD, 1e-12)

    def test_arcsec_per_degree(self):
        self.assertAlmostEqual(ARCCSEC_PER_DEGREE, 3600.0)


if __name__ == "__main__":
    unittest.main()
