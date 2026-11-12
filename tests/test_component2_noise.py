"""Focused tests for the migrated Component 2 measurement-noise module.

These tests are hermetic: they use in-memory NumPy arrays only and never write
into the repository. They are written with the standard-library ``unittest``
framework because pytest is not installed in the development environment.

Run directly with::

    python tests/test_component2_noise.py -v
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

from orbit_discovery.component2_observations import noise
from orbit_discovery.core import constants
from src.measurement_noise import (
    ARCSEC_TO_DEG as old_arcsec_to_deg,
    add_measurement_noise as old_add_measurement_noise,
)


class _NoiseTestCase(unittest.TestCase):
    """Shared exact-message assertion helper."""

    def assert_value_error(self, message, function, *args, **kwargs):
        with self.assertRaises(ValueError) as context:
            function(*args, **kwargs)
        self.assertEqual(str(context.exception), message)


class NoiseSignatureAndConstantTests(unittest.TestCase):
    """The migrated signature, defaults, and shared constant must not change."""

    def test_add_measurement_noise_signature_is_unchanged(self):
        signature = inspect.signature(noise.add_measurement_noise)
        parameters = list(signature.parameters.values())

        self.assertEqual(
            [parameter.name for parameter in parameters],
            [
                "ra_deg",
                "dec_deg",
                "sigma_ra_cosdec_arcsec",
                "sigma_dec_arcsec",
                "random_seed",
            ],
        )
        self.assertEqual(parameters[0].default, inspect.Parameter.empty)
        self.assertEqual(parameters[1].default, inspect.Parameter.empty)
        self.assertEqual(parameters[2].default, 0.5)
        self.assertEqual(parameters[3].default, 0.5)
        self.assertEqual(parameters[4].default, 42)
        for parameter in parameters:
            self.assertEqual(
                parameter.kind,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )

    def test_arcsec_to_deg_is_the_shared_constant(self):
        self.assertEqual(noise.ARCSEC_TO_DEG, 1.0 / 3600.0)
        self.assertEqual(noise.ARCSEC_TO_DEG, constants.ARCSEC_TO_DEG)
        self.assertEqual(old_arcsec_to_deg, noise.ARCSEC_TO_DEG)
        self.assertIs(old_arcsec_to_deg, noise.ARCSEC_TO_DEG)

    def test_noise_module_imports_the_shared_constant(self):
        source = Path(noise.__file__).read_text(encoding="utf-8")

        self.assertIn(
            "from orbit_discovery.core.constants import ARCSEC_TO_DEG",
            source,
        )
        self.assertNotIn("ARCSEC_TO_DEG = 1.0 / 3600.0", source)


class AddMeasurementNoiseTests(_NoiseTestCase):
    """Characterisation tests for the existing seeded noise behaviour."""

    def test_seeded_outputs_match_pre_migration_values(self):
        ra_deg = np.array([10.0, 200.0])
        dec_deg = np.array([0.0, 45.0])

        result = noise.add_measurement_noise(
            ra_deg,
            dec_deg,
            sigma_ra_cosdec_arcsec=0.5,
            sigma_dec_arcsec=0.5,
            random_seed=42,
        )

        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 4)
        for array in result:
            self.assertIsInstance(array, np.ndarray)
            self.assertEqual(array.shape, (2,))
            self.assertEqual(array.dtype, np.dtype(float))

        np.testing.assert_array_equal(
            result[0],
            np.array([10.000042321816633, 199.99979572782948]),
        )
        np.testing.assert_array_equal(
            result[1],
            np.array([0.00010422933275089684, 45.00013063398839]),
        )
        np.testing.assert_array_equal(
            result[2],
            np.array([0.15235853987721568, -0.5199920531202478]),
        )
        np.testing.assert_array_equal(
            result[3],
            np.array([0.3752255979032286, 0.47028235819560693]),
        )

    def test_repeated_seed_is_deterministic(self):
        ra_deg = np.array([10.0, 200.0])
        dec_deg = np.array([0.0, 45.0])

        first = noise.add_measurement_noise(
            ra_deg,
            dec_deg,
            random_seed=42,
        )
        second = noise.add_measurement_noise(
            ra_deg,
            dec_deg,
            random_seed=42,
        )

        for first_array, second_array in zip(first, second):
            np.testing.assert_array_equal(first_array, second_array)

    def test_zero_sigma_leaves_coordinates_unchanged(self):
        ra_deg = np.array([10.0, 200.0])
        dec_deg = np.array([0.0, 45.0])

        result = noise.add_measurement_noise(
            ra_deg,
            dec_deg,
            sigma_ra_cosdec_arcsec=0.0,
            sigma_dec_arcsec=0.0,
            random_seed=42,
        )

        np.testing.assert_array_equal(result[0], ra_deg)
        np.testing.assert_array_equal(result[1], dec_deg)
        np.testing.assert_array_equal(result[2], np.zeros(2))
        np.testing.assert_array_equal(result[3], np.zeros(2))

    def test_ra_wrap_is_preserved(self):
        result = noise.add_measurement_noise(
            np.array([360.0]),
            np.array([0.0]),
            sigma_ra_cosdec_arcsec=0.0,
            sigma_dec_arcsec=0.0,
            random_seed=42,
        )

        np.testing.assert_array_equal(result[0], np.array([0.0]))

    def test_inputs_are_not_mutated(self):
        ra_deg = np.array([10.0, 200.0])
        dec_deg = np.array([0.0, 45.0])
        original_ra = ra_deg.copy()
        original_dec = dec_deg.copy()

        noise.add_measurement_noise(ra_deg, dec_deg, random_seed=42)

        np.testing.assert_array_equal(ra_deg, original_ra)
        np.testing.assert_array_equal(dec_deg, original_dec)

    def test_mismatched_shapes_message_is_unchanged(self):
        self.assert_value_error(
            "RA and Dec arrays must have matching shapes.",
            noise.add_measurement_noise,
            np.array([10.0, 20.0]),
            np.array([0.0]),
        )

    def test_non_finite_coordinates_message_is_unchanged(self):
        self.assert_value_error(
            "Coordinates must contain finite values.",
            noise.add_measurement_noise,
            np.array([10.0, np.inf]),
            np.array([0.0, 0.0]),
        )

    def test_declination_range_message_is_unchanged(self):
        self.assert_value_error(
            "Declination must be between -90 and +90 degrees.",
            noise.add_measurement_noise,
            np.array([10.0]),
            np.array([90.1]),
        )

    def test_negative_sigma_message_is_unchanged(self):
        self.assert_value_error(
            "Noise uncertainties cannot be negative.",
            noise.add_measurement_noise,
            np.array([10.0]),
            np.array([0.0]),
            sigma_ra_cosdec_arcsec=-0.1,
        )
        self.assert_value_error(
            "Noise uncertainties cannot be negative.",
            noise.add_measurement_noise,
            np.array([10.0]),
            np.array([0.0]),
            sigma_dec_arcsec=-0.1,
        )

    def test_pole_singularity_message_is_unchanged(self):
        self.assert_value_error(
            "RA noise conversion is singular at the celestial poles.",
            noise.add_measurement_noise,
            np.array([10.0]),
            np.array([90.0]),
            sigma_ra_cosdec_arcsec=0.5,
        )

    def test_noisy_declination_range_message_is_unchanged(self):
        self.assert_value_error(
            "Noise produced declination outside the valid range.",
            noise.add_measurement_noise,
            np.array([10.0]),
            np.array([89.9]),
            sigma_ra_cosdec_arcsec=0.0,
            sigma_dec_arcsec=1000.0,
            random_seed=1,
        )

    def test_validation_order_is_unchanged(self):
        self.assert_value_error(
            "Declination must be between -90 and +90 degrees.",
            noise.add_measurement_noise,
            np.array([10.0]),
            np.array([91.0]),
            sigma_ra_cosdec_arcsec=-1.0,
            sigma_dec_arcsec=-1.0,
        )
        self.assert_value_error(
            "RA and Dec arrays must have matching shapes.",
            noise.add_measurement_noise,
            np.array([10.0, 20.0]),
            np.array([0.0]),
            sigma_ra_cosdec_arcsec=-1.0,
        )


class NoiseCompatibilityTests(unittest.TestCase):
    """The old path must re-export the new implementation, not duplicate it."""

    def test_old_path_reexports_new_function(self):
        self.assertIs(
            old_add_measurement_noise,
            noise.add_measurement_noise,
        )

    def test_old_and_new_paths_return_identical_values(self):
        ra_deg = np.array([10.0, 200.0])
        dec_deg = np.array([0.0, 45.0])

        old_result = old_add_measurement_noise(
            ra_deg,
            dec_deg,
            sigma_ra_cosdec_arcsec=0.5,
            sigma_dec_arcsec=0.5,
            random_seed=42,
        )
        new_result = noise.add_measurement_noise(
            ra_deg,
            dec_deg,
            sigma_ra_cosdec_arcsec=0.5,
            sigma_dec_arcsec=0.5,
            random_seed=42,
        )

        for old_array, new_array in zip(old_result, new_result):
            np.testing.assert_array_equal(old_array, new_array)


if __name__ == "__main__":
    unittest.main(verbosity=2)
