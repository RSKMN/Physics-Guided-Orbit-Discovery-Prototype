"""Focused tests for the migrated Component 2 frames module.

These tests are hermetic: they use in-memory NumPy arrays only and never write
into the repository. They are written with the standard-library ``unittest``
framework because pytest is not installed in the development environment.

Run directly with::

    python tests/test_component2_frames.py -v
"""

from __future__ import annotations

import inspect
import sys
import unittest
from pathlib import Path

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_DIR = _REPO_ROOT / "src"
for _path in (_REPO_ROOT, _SRC_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from orbit_discovery.component2_observations import frames
from src.coordinate_converter import (
    ecliptic_to_equatorial as old_ecliptic_to_equatorial,
    calculate_ra_dec as old_calculate_ra_dec,
)


class _FramesTestCase(unittest.TestCase):
    """Shared exact-message assertion helper."""

    def assert_value_error(self, message, function, *args, **kwargs):
        with self.assertRaises(ValueError) as context:
            function(*args, **kwargs)
        self.assertEqual(str(context.exception), message)


class FramesSignatureTests(unittest.TestCase):
    """The migrated public signatures and defaults must not change."""

    def test_ecliptic_to_equatorial_signature_is_unchanged(self):
        signature = inspect.signature(frames.ecliptic_to_equatorial)
        parameters = list(signature.parameters.values())

        self.assertEqual(
            [parameter.name for parameter in parameters],
            ["relative_positions", "obliquity_deg"],
        )
        self.assertEqual(parameters[0].default, inspect.Parameter.empty)
        self.assertEqual(parameters[1].default, 23.43928)
        for parameter in parameters:
            self.assertEqual(
                parameter.kind,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )

    def test_calculate_ra_dec_signature_is_unchanged(self):
        signature = inspect.signature(frames.calculate_ra_dec)

        self.assertEqual(
            list(signature.parameters),
            ["equatorial_positions"],
        )
        for parameter in signature.parameters.values():
            self.assertEqual(
                parameter.kind,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )
            self.assertIs(parameter.default, inspect.Parameter.empty)


class EclipticToEquatorialTests(_FramesTestCase):
    """Characterisation tests for the existing frame rotation."""

    def test_default_obliquity_known_rotation(self):
        positions = np.array([[0.0, 1.0, 0.0]])

        rotated = frames.ecliptic_to_equatorial(positions)

        self.assertEqual(rotated.shape, (1, 3))
        self.assertEqual(rotated.dtype, np.dtype(float))
        np.testing.assert_allclose(
            rotated[0],
            np.array([0.0, 0.9174821392082875, 0.3977769780087639]),
            rtol=0,
            atol=1e-15,
        )

    def test_zero_obliquity_is_identity(self):
        positions = np.array(
            [
                [1.0, 2.0, 3.0],
                [-4.0, 5.0, -6.0],
            ]
        )

        rotated = frames.ecliptic_to_equatorial(positions, obliquity_deg=0.0)

        self.assertEqual(rotated.shape, positions.shape)
        np.testing.assert_allclose(rotated, positions, rtol=0, atol=1e-15)

    def test_ninety_degree_obliquity_maps_axes(self):
        positions = np.array(
            [
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 1.0],
            ]
        )

        rotated = frames.ecliptic_to_equatorial(positions, obliquity_deg=90.0)

        np.testing.assert_allclose(
            rotated,
            np.array(
                [
                    [0.0, 0.0, 1.0],
                    [0.0, -1.0, 0.0],
                ]
            ),
            rtol=0,
            atol=1e-15,
        )

    def test_input_is_not_mutated(self):
        positions = np.array([[1.0, 2.0, 3.0]])
        original = positions.copy()

        frames.ecliptic_to_equatorial(positions)

        np.testing.assert_array_equal(positions, original)

    def test_wrong_shape_message_is_unchanged(self):
        self.assert_value_error(
            "Positions must have shape (N, 3).",
            frames.ecliptic_to_equatorial,
            np.zeros((2, 2)),
        )

    def test_non_finite_message_is_unchanged(self):
        positions = np.zeros((2, 3))
        positions[0, 0] = np.nan

        self.assert_value_error(
            "Positions contain invalid values.",
            frames.ecliptic_to_equatorial,
            positions,
        )

    def test_shape_validation_precedes_finite_validation(self):
        positions = np.zeros((2, 2))
        positions[0, 0] = np.nan

        self.assert_value_error(
            "Positions must have shape (N, 3).",
            frames.ecliptic_to_equatorial,
            positions,
        )


class CalculateRaDecTests(_FramesTestCase):
    """Characterisation tests for RA/Dec calculation and boundaries."""

    def test_cardinal_directions(self):
        positions = np.array(
            [
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [-1.0, 0.0, 0.0],
                [0.0, -1.0, 0.0],
                [0.0, 0.0, 1.0],
                [0.0, 0.0, -1.0],
            ]
        )

        ra_deg, dec_deg = frames.calculate_ra_dec(positions)

        np.testing.assert_allclose(
            ra_deg,
            np.array([0.0, 90.0, 180.0, 270.0, 0.0, 0.0]),
            rtol=0,
            atol=1e-12,
        )
        np.testing.assert_allclose(
            dec_deg,
            np.array([0.0, 0.0, 0.0, 0.0, 90.0, -90.0]),
            rtol=0,
            atol=1e-12,
        )

    def test_ra_is_normalized_to_0_360(self):
        positions = np.array(
            [
                [1.0, -1.0, 0.0],
                [1.0, 1.0, 0.0],
                [-1.0, 1.0, 0.0],
                [-1.0, -1.0, 0.0],
            ]
        )

        ra_deg, dec_deg = frames.calculate_ra_dec(positions)

        np.testing.assert_allclose(
            ra_deg,
            np.array([315.0, 45.0, 135.0, 225.0]),
            rtol=0,
            atol=1e-12,
        )
        self.assertTrue(np.all((ra_deg >= 0.0) & (ra_deg < 360.0)))
        np.testing.assert_array_equal(dec_deg, np.zeros(4))

    def test_return_types_shapes_and_input_non_mutation(self):
        positions = np.array(
            [
                [1.0, 2.0, 3.0],
                [4.0, 5.0, 6.0],
            ]
        )
        original = positions.copy()

        result = frames.calculate_ra_dec(positions)

        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        ra_deg, dec_deg = result
        self.assertIsInstance(ra_deg, np.ndarray)
        self.assertIsInstance(dec_deg, np.ndarray)
        self.assertEqual(ra_deg.shape, (2,))
        self.assertEqual(dec_deg.shape, (2,))
        self.assertEqual(ra_deg.dtype, np.dtype(float))
        self.assertEqual(dec_deg.dtype, np.dtype(float))
        self.assertTrue(np.all((ra_deg >= 0.0) & (ra_deg < 360.0)))
        self.assertTrue(np.all((dec_deg >= -90.0) & (dec_deg <= 90.0)))
        np.testing.assert_array_equal(positions, original)

    def test_zero_vector_message_is_unchanged(self):
        self.assert_value_error(
            "Cannot calculate coordinates for zero vectors.",
            frames.calculate_ra_dec,
            np.array([[0.0, 0.0, 0.0]]),
        )

    def test_wrong_shape_message_is_unchanged(self):
        self.assert_value_error(
            "Positions must have shape (N, 3).",
            frames.calculate_ra_dec,
            np.zeros((2, 2)),
        )

    def test_non_finite_message_is_unchanged(self):
        positions = np.zeros((2, 3))
        positions[0, 2] = np.inf

        self.assert_value_error(
            "Positions contain invalid values.",
            frames.calculate_ra_dec,
            positions,
        )

    def test_shape_validation_precedes_finite_validation(self):
        positions = np.zeros((2, 2))
        positions[0, 0] = np.inf

        self.assert_value_error(
            "Positions must have shape (N, 3).",
            frames.calculate_ra_dec,
            positions,
        )


class FramesCompatibilityTests(unittest.TestCase):
    """The old path must re-export the new implementation, not duplicate it."""

    def test_old_path_reexports_new_functions(self):
        self.assertIs(
            old_ecliptic_to_equatorial,
            frames.ecliptic_to_equatorial,
        )
        self.assertIs(
            old_calculate_ra_dec,
            frames.calculate_ra_dec,
        )

    def test_old_and_new_paths_return_identical_values(self):
        positions = np.array(
            [
                [0.0, 1.0, 0.0],
                [1.0, 0.0, 0.0],
            ]
        )

        old_rotated = old_ecliptic_to_equatorial(positions)
        new_rotated = frames.ecliptic_to_equatorial(positions)
        np.testing.assert_array_equal(old_rotated, new_rotated)

        old_ra, old_dec = old_calculate_ra_dec(positions)
        new_ra, new_dec = frames.calculate_ra_dec(positions)
        np.testing.assert_array_equal(old_ra, new_ra)
        np.testing.assert_array_equal(old_dec, new_dec)


if __name__ == "__main__":
    unittest.main(verbosity=2)
