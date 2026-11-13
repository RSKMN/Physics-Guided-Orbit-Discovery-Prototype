"""Focused tests for the migrated Component 2 observer module.

These tests are hermetic: they use in-memory NumPy arrays only and never write
into the repository. They are written with the standard-library ``unittest``
framework because pytest is not installed in the development environment.

Run directly with::

    python tests/test_component2_observer.py -v
"""

from __future__ import annotations

import inspect
import math
import sys
import unittest
from pathlib import Path

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_DIR = _REPO_ROOT / "src"
for _path in (_REPO_ROOT, _SRC_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from orbit_discovery.component2_observations import observer
from orbit_discovery.component2_observations import frames
from src.observer_model import (
    calculate_observer_positions as old_calculate_observer_positions,
    calculate_relative_positions as old_calculate_relative_positions,
)


class _ObserverTestCase(unittest.TestCase):
    """Shared exact-message assertion helper."""

    def assert_value_error(self, message, function, *args, **kwargs):
        with self.assertRaises(ValueError) as context:
            function(*args, **kwargs)
        self.assertEqual(str(context.exception), message)


class ObserverSignatureTests(unittest.TestCase):
    """The migrated public signatures and defaults must not change."""

    def test_calculate_observer_positions_signature_is_unchanged(self):
        signature = inspect.signature(observer.calculate_observer_positions)
        parameters = list(signature.parameters.values())

        self.assertEqual(
            [parameter.name for parameter in parameters],
            [
                "time_years",
                "orbital_radius_au",
                "orbital_period_years",
                "initial_phase_deg",
            ],
        )
        self.assertEqual(parameters[0].default, inspect.Parameter.empty)
        self.assertEqual(parameters[1].default, 1.0)
        self.assertEqual(parameters[2].default, 1.0)
        self.assertEqual(parameters[3].default, 90.0)
        for parameter in parameters:
            self.assertEqual(
                parameter.kind,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )

    def test_calculate_relative_positions_signature_is_unchanged(self):
        signature = inspect.signature(observer.calculate_relative_positions)

        self.assertEqual(
            list(signature.parameters),
            ["asteroid_positions", "observer_positions"],
        )
        for parameter in signature.parameters.values():
            self.assertEqual(
                parameter.kind,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )
            self.assertIs(parameter.default, inspect.Parameter.empty)


class CalculateObserverPositionsTests(_ObserverTestCase):
    """Characterisation tests for the existing observer geometry."""

    def test_defaults_produce_expected_initial_position(self):
        positions = observer.calculate_observer_positions([0.0])

        self.assertEqual(positions.shape, (1, 3))
        self.assertEqual(positions.dtype, np.dtype(float))
        np.testing.assert_allclose(
            positions[0],
            np.array([0.0, 1.0, 0.0]),
            rtol=0,
            atol=1e-12,
        )

    def test_default_quarter_period_motion(self):
        positions = observer.calculate_observer_positions([0.0, 0.25])

        np.testing.assert_allclose(
            positions,
            np.array(
                [
                    [0.0, 1.0, 0.0],
                    [-1.0, 0.0, 0.0],
                ]
            ),
            rtol=0,
            atol=1e-12,
        )

    def test_radius_and_period_scaling(self):
        positions = observer.calculate_observer_positions(
            [0.0, 0.5],
            orbital_radius_au=2.0,
            orbital_period_years=2.0,
            initial_phase_deg=0.0,
        )

        np.testing.assert_allclose(
            positions,
            np.array(
                [
                    [2.0, 0.0, 0.0],
                    [0.0, 2.0, 0.0],
                ]
            ),
            rtol=0,
            atol=1e-12,
        )

    def test_input_times_are_not_mutated(self):
        times = np.array([0.0, 0.25, 0.5])
        original = times.copy()

        observer.calculate_observer_positions(times)

        np.testing.assert_array_equal(times, original)

    def test_non_finite_time_message_is_unchanged(self):
        self.assert_value_error(
            "Time values must be finite.",
            observer.calculate_observer_positions,
            np.array([0.0, np.nan]),
        )

    def test_non_positive_radius_message_is_unchanged(self):
        self.assert_value_error(
            "Orbital radius must be positive.",
            observer.calculate_observer_positions,
            np.array([0.0]),
            0.0,
        )

    def test_non_positive_period_message_is_unchanged(self):
        self.assert_value_error(
            "Orbital period must be positive.",
            observer.calculate_observer_positions,
            np.array([0.0]),
            1.0,
            0.0,
        )

    def test_validation_order_is_unchanged(self):
        self.assert_value_error(
            "Time values must be finite.",
            observer.calculate_observer_positions,
            np.array([0.0, np.inf]),
            0.0,
            0.0,
        )


class CalculateRelativePositionsTests(_ObserverTestCase):
    """Characterisation tests for the existing relative-position behaviour."""

    def test_returns_asteroid_minus_observer_and_preserves_inputs(self):
        asteroid_positions = np.array(
            [
                [1.0, 2.0, 3.0],
                [4.0, 5.0, 6.0],
            ]
        )
        observer_positions = np.array(
            [
                [0.5, 0.5, 0.5],
                [1.0, 1.0, 1.0],
            ]
        )

        original_asteroid = asteroid_positions.copy()
        original_observer = observer_positions.copy()

        relative = observer.calculate_relative_positions(
            asteroid_positions,
            observer_positions,
        )

        self.assertEqual(relative.shape, (2, 3))
        self.assertEqual(relative.dtype, np.dtype(float))
        np.testing.assert_array_equal(
            relative,
            asteroid_positions - observer_positions,
        )
        np.testing.assert_array_equal(
            asteroid_positions,
            original_asteroid,
        )
        np.testing.assert_array_equal(
            observer_positions,
            original_observer,
        )

    def test_mismatched_shapes_message_is_unchanged(self):
        self.assert_value_error(
            "Asteroid and observer position arrays must have the same shape.",
            observer.calculate_relative_positions,
            np.zeros((2, 3)),
            np.zeros((3, 3)),
        )

    def test_wrong_position_shape_message_is_unchanged(self):
        self.assert_value_error(
            "Position arrays must have shape (N, 3).",
            observer.calculate_relative_positions,
            np.zeros((2, 2)),
            np.zeros((2, 2)),
        )

    def test_mismatched_shape_check_precedes_dimension_check(self):
        self.assert_value_error(
            "Asteroid and observer position arrays must have the same shape.",
            observer.calculate_relative_positions,
            np.zeros((2, 2)),
            np.zeros((3, 2)),
        )

    def test_non_finite_asteroid_positions_message_is_unchanged(self):
        asteroid_positions = np.zeros((2, 3))
        asteroid_positions[0, 0] = np.nan

        self.assert_value_error(
            "Asteroid positions contain invalid values.",
            observer.calculate_relative_positions,
            asteroid_positions,
            np.zeros((2, 3)),
        )

    def test_non_finite_observer_positions_message_is_unchanged(self):
        observer_positions = np.zeros((2, 3))
        observer_positions[0, 0] = np.inf

        self.assert_value_error(
            "Observer positions contain invalid values.",
            observer.calculate_relative_positions,
            np.zeros((2, 3)),
            observer_positions,
        )


class ObserverCompatibilityTests(unittest.TestCase):
    """The old path must re-export the new implementation, not duplicate it."""

    def test_old_path_reexports_new_functions(self):
        self.assertIs(
            old_calculate_observer_positions,
            observer.calculate_observer_positions,
        )
        self.assertIs(
            old_calculate_relative_positions,
            observer.calculate_relative_positions,
        )

    def test_old_and_new_paths_return_identical_arrays(self):
        times = np.array([0.0, 0.25, 0.5])
        observer_arguments = (times, 2.0, 2.0, 0.0)

        old_positions = old_calculate_observer_positions(*observer_arguments)
        new_positions = observer.calculate_observer_positions(*observer_arguments)

        np.testing.assert_array_equal(old_positions, new_positions)

        asteroid_positions = np.array(
            [
                [1.0, 2.0, 3.0],
                [4.0, 5.0, 6.0],
                [7.0, 8.0, 9.0],
            ]
        )
        relative_arguments = (asteroid_positions, new_positions)

        old_relative = old_calculate_relative_positions(*relative_arguments)
        new_relative = observer.calculate_relative_positions(*relative_arguments)

        np.testing.assert_array_equal(old_relative, new_relative)


class CalculateSkyCoordinatesRegressionTests(unittest.TestCase):
    """Regression tests for calculate_sky_coordinates declination.

    These tests compare observer.calculate_sky_coordinates() against the
    established frames.calculate_ra_dec() implementation (which applies
    ecliptic_to_equatorial first and then computes declination with the
    correct equatorial denominator). They cover representative line-of-sight
    vectors with non-zero ecliptic latitude so the previous declination
    denominator bug (using the ecliptic denominator instead of the
    equatorial denominator) would be detected.
    """

    def setUp(self):
        self.obliquity_deg = 23.43928

    def _reference_ra_dec(self, los_unit_vectors):
        """Compute reference RA/Dec via ecliptic_to_equatorial + frames."""
        equatorial = frames.ecliptic_to_equatorial(
            los_unit_vectors, obliquity_deg=self.obliquity_deg
        )
        return frames.calculate_ra_dec(equatorial)

    def test_matches_frames_calculate_ra_dec_for_cardinal_vectors(self):
        los = np.array(
            [
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [-1.0, 0.0, 0.0],
                [0.0, -1.0, 0.0],
                [0.0, 0.0, 1.0],
                [0.0, 0.0, -1.0],
            ]
        )
        ra, dec = observer.calculate_sky_coordinates(los)
        ref_ra, ref_dec = self._reference_ra_dec(los)

        np.testing.assert_allclose(ra, ref_ra, rtol=0, atol=1e-12)
        np.testing.assert_allclose(dec, ref_dec, rtol=0, atol=1e-12)

    def test_matches_frames_calculate_ra_dec_for_non_zero_ecliptic_latitude(self):
        """Vectors with non-zero ecliptic latitude expose the old bug."""
        los = np.array(
            [
                [0.5, 0.5, 0.7071067811865476],  # high positive ecliptic latitude
                [0.5, -0.5, -0.7071067811865476],  # high negative ecliptic latitude
                [0.8660254037844386, 0.0, 0.5],  # 30 deg ecliptic latitude
                [-0.8660254037844386, 0.0, -0.5],
            ]
        )
        # Normalise so inputs are valid unit vectors.
        los = los / np.linalg.norm(los, axis=1, keepdims=True)

        ra, dec = observer.calculate_sky_coordinates(los)
        ref_ra, ref_dec = self._reference_ra_dec(los)

        np.testing.assert_allclose(ra, ref_ra, rtol=0, atol=1e-12)
        np.testing.assert_allclose(dec, ref_dec, rtol=0, atol=1e-12)

    def test_dec_uses_equatorial_denominator_not_ecliptic(self):
        """Directly assert the equatorial denominator is used for declination.

        With the old (buggy) expression, dec for [0, 1, 0] at default obliquity
        was computed as atan2(z_eq, sqrt(x^2 + y^2)) instead of
        atan2(z_eq, sqrt(x_eq^2 + y_eq^2)). The two differ whenever
        z != 0 and the equatorial rotation changes the x-y radial distance.
        """
        obliquity = math.radians(self.obliquity_deg)
        # Purely ecliptic-Y vector: rotates into equatorial Y and Z.
        los = np.array([[0.0, 1.0, 0.0]])
        x = los[:, 0]
        y = los[:, 1]
        z = los[:, 2]
        x_eq = x
        y_eq = y * math.cos(obliquity) - z * math.sin(obliquity)
        z_eq = y * math.sin(obliquity) + z * math.cos(obliquity)

        expected_dec_rad = math.atan2(z_eq[0], math.sqrt(x_eq[0] ** 2 + y_eq[0] ** 2))
        buggy_dec_rad = math.atan2(z_eq[0], math.sqrt(x[0] ** 2 + y[0] ** 2))

        ra, dec = observer.calculate_sky_coordinates(los)

        # Correct value must match the equatorial-denominator formula.
        np.testing.assert_allclose(
            dec[0],
            math.degrees(expected_dec_rad),
            rtol=0,
            atol=1e-12,
        )
        # And must not match the old buggy ecliptic-denominator formula.
        self.assertNotAlmostEqual(dec[0], math.degrees(buggy_dec_rad), places=10)

    def test_ra_wraparound_and_dec_range(self):
        """RA is normalized to [0, 360) and Dec stays within [-90, 90]."""
        los = np.array(
            [
                [-1.0, -1.0, 0.5],
                [-1.0, -1.0, -0.5],
                [1.0, -1.0, 0.5],
                [1.0, -1.0, -0.5],
            ]
        )
        los = los / np.linalg.norm(los, axis=1, keepdims=True)

        ra, dec = observer.calculate_sky_coordinates(los)

        self.assertTrue(np.all((ra >= 0.0) & (ra < 360.0)), f"RA out of range: {ra}")
        self.assertTrue(np.all((dec >= -90.0) & (dec <= 90.0)), f"Dec out of range: {dec}")

    def test_ra_wraps_at_360_boundary(self):
        """A vector just past the +x axis wraps RA correctly (near 360/0)."""
        los = np.array([[1.0, -1e-9, 0.0]])
        ra, _ = observer.calculate_sky_coordinates(los)
        self.assertTrue(0.0 <= ra[0] < 360.0, f"RA={ra[0]} not in [0, 360)")

    def test_pole_vectors(self):
        """North and south ecliptic poles map to +/- (90 - obliquity) declination.

        Under an ecliptic-to-equatorial rotation by obliquity, the ecliptic
        north pole rotates toward the equatorial pole but only reaches
        declination = 90 - obliquity (since the rotation axis is the x-axis).
        """
        los = np.array([[0.0, 0.0, 1.0], [0.0, 0.0, -1.0]])
        ra, dec = observer.calculate_sky_coordinates(los)

        expected_dec = 90.0 - self.obliquity_deg
        np.testing.assert_allclose(
            dec, [expected_dec, -expected_dec], rtol=0, atol=1e-12
        )
        self.assertTrue(np.all((ra >= 0.0) & (ra < 360.0)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
