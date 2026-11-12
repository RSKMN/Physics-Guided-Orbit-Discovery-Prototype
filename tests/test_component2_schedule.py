"""Focused tests for the migrated Component 2 schedule module.

These tests are hermetic: they use in-memory NumPy arrays only and never write
into the repository. They are written with the standard-library ``unittest``
framework because pytest is not installed in the development environment.

Run directly with::

    python tests/test_component2_schedule.py -v
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

from orbit_discovery.component2_observations import schedule
from src.observation_schedule import (
    generate_observation_times as old_generate_observation_times,
    interpolate_positions as old_interpolate_positions,
)


class _ScheduleTestCase(unittest.TestCase):
    """Shared exact-message assertion helper."""

    def assert_value_error(self, message, function, *args, **kwargs):
        with self.assertRaises(ValueError) as context:
            function(*args, **kwargs)
        self.assertEqual(str(context.exception), message)


class ScheduleSignatureTests(unittest.TestCase):
    """The migrated public signatures and defaults must not change."""

    def test_generate_observation_times_signature_is_unchanged(self):
        signature = inspect.signature(schedule.generate_observation_times)

        self.assertEqual(
            list(signature.parameters),
            [
                "start_day",
                "end_day",
                "cadence_days",
                "available_start_day",
                "available_end_day",
            ],
        )
        for parameter in signature.parameters.values():
            self.assertEqual(
                parameter.kind,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )
            self.assertIs(parameter.default, inspect.Parameter.empty)

    def test_interpolate_positions_signature_is_unchanged(self):
        signature = inspect.signature(schedule.interpolate_positions)

        self.assertEqual(
            list(signature.parameters),
            [
                "ground_truth_times_days",
                "ground_truth_positions",
                "observation_times_days",
            ],
        )
        for parameter in signature.parameters.values():
            self.assertEqual(
                parameter.kind,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )
            self.assertIs(parameter.default, inspect.Parameter.empty)


class GenerateObservationTimesTests(_ScheduleTestCase):
    """Characterisation tests for the existing scheduling behaviour."""

    def test_standard_scenario_produces_262_values_and_exact_endpoint(self):
        times = schedule.generate_observation_times(
            0.0,
            1826.25,
            7.0,
            0.0,
            1826.25,
        )

        self.assertEqual(times.shape, (262,))
        self.assertEqual(times.dtype, np.dtype(float))
        self.assertEqual(times[0], 0.0)
        self.assertEqual(times[-1], 1826.25)
        self.assertEqual(times[-2], 1820.0)
        self.assertEqual(times[-1] - times[-2], 6.25)
        self.assertTrue(np.all(np.diff(times) > 0))

    def test_exact_endpoint_is_not_duplicated(self):
        times = schedule.generate_observation_times(
            0.0,
            14.0,
            7.0,
            0.0,
            14.0,
        )

        np.testing.assert_array_equal(times, np.array([0.0, 7.0, 14.0]))

    def test_cadence_larger_than_interval_includes_start_and_end(self):
        times = schedule.generate_observation_times(
            0.0,
            5.0,
            10.0,
            0.0,
            10.0,
        )

        np.testing.assert_array_equal(times, np.array([0.0, 5.0]))

    def test_invalid_cadence_message_is_unchanged(self):
        self.assert_value_error(
            "Cadence must be greater than zero.",
            schedule.generate_observation_times,
            0.0,
            10.0,
            0.0,
            0.0,
            10.0,
        )

    def test_invalid_interval_message_is_unchanged(self):
        self.assert_value_error(
            "End day must be greater than start day.",
            schedule.generate_observation_times,
            10.0,
            10.0,
            1.0,
            0.0,
            10.0,
        )

    def test_start_outside_range_message_is_unchanged(self):
        self.assert_value_error(
            "Start day is outside trajectory range.",
            schedule.generate_observation_times,
            -1.0,
            10.0,
            1.0,
            0.0,
            10.0,
        )

    def test_end_outside_range_message_is_unchanged(self):
        self.assert_value_error(
            "End day is outside trajectory range.",
            schedule.generate_observation_times,
            0.0,
            11.0,
            1.0,
            0.0,
            10.0,
        )

    def test_validation_order_is_unchanged(self):
        self.assert_value_error(
            "Cadence must be greater than zero.",
            schedule.generate_observation_times,
            10.0,
            0.0,
            0.0,
            20.0,
            5.0,
        )
        self.assert_value_error(
            "End day must be greater than start day.",
            schedule.generate_observation_times,
            10.0,
            5.0,
            1.0,
            20.0,
            0.0,
        )
        self.assert_value_error(
            "Start day is outside trajectory range.",
            schedule.generate_observation_times,
            5.0,
            15.0,
            1.0,
            10.0,
            12.0,
        )


class InterpolatePositionsTests(_ScheduleTestCase):
    """Characterisation tests for the existing linear interpolation."""

    def test_linear_ramp_returns_expected_values_and_shape(self):
        ground_truth_times = np.array([0.0, 10.0, 20.0])
        ground_truth_positions = np.column_stack(
            (
                ground_truth_times,
                2.0 * ground_truth_times,
                -ground_truth_times,
            )
        )
        observation_times = np.array([0.0, 5.0, 10.0, 15.0, 20.0])

        original_times = ground_truth_times.copy()
        original_positions = ground_truth_positions.copy()
        original_observations = observation_times.copy()

        interpolated = schedule.interpolate_positions(
            ground_truth_times,
            ground_truth_positions,
            observation_times,
        )

        expected = np.column_stack(
            (
                observation_times,
                2.0 * observation_times,
                -observation_times,
            )
        )

        self.assertEqual(interpolated.shape, (5, 3))
        self.assertEqual(interpolated.dtype, np.dtype(float))
        np.testing.assert_allclose(interpolated, expected, rtol=0, atol=1e-12)

        np.testing.assert_array_equal(ground_truth_times, original_times)
        np.testing.assert_array_equal(
            ground_truth_positions,
            original_positions,
        )
        np.testing.assert_array_equal(
            observation_times,
            original_observations,
        )

    def test_endpoint_interpolation_returns_endpoint_positions(self):
        ground_truth_times = np.array([0.0, 10.0, 20.0])
        ground_truth_positions = np.array(
            [
                [1.0, 2.0, 3.0],
                [4.0, 5.0, 6.0],
                [7.0, 8.0, 9.0],
            ]
        )
        observation_times = np.array([0.0, 20.0])

        interpolated = schedule.interpolate_positions(
            ground_truth_times,
            ground_truth_positions,
            observation_times,
        )

        np.testing.assert_array_equal(
            interpolated[0],
            ground_truth_positions[0],
        )
        np.testing.assert_array_equal(
            interpolated[-1],
            ground_truth_positions[-1],
        )

    def test_wrong_position_shape_message_is_unchanged(self):
        self.assert_value_error(
            "Ground-truth positions must have shape (N, 3).",
            schedule.interpolate_positions,
            np.array([0.0, 10.0, 20.0]),
            np.zeros((2, 3)),
            np.array([0.0]),
        )

    def test_too_few_samples_message_is_unchanged(self):
        self.assert_value_error(
            "At least two ground-truth samples are required.",
            schedule.interpolate_positions,
            np.array([0.0]),
            np.zeros((1, 3)),
            np.array([0.0]),
        )

    def test_non_increasing_times_message_is_unchanged(self):
        self.assert_value_error(
            "Ground-truth timestamps must be strictly increasing.",
            schedule.interpolate_positions,
            np.array([0.0, 10.0, 10.0]),
            np.zeros((3, 3)),
            np.array([0.0]),
        )

    def test_non_finite_positions_message_is_unchanged(self):
        positions = np.zeros((3, 3))
        positions[1, 1] = np.nan

        self.assert_value_error(
            "Ground-truth positions contain invalid values.",
            schedule.interpolate_positions,
            np.array([0.0, 10.0, 20.0]),
            positions,
            np.array([0.0]),
        )

    def test_non_finite_observation_times_message_is_unchanged(self):
        self.assert_value_error(
            "Observation times contain invalid values.",
            schedule.interpolate_positions,
            np.array([0.0, 10.0, 20.0]),
            np.zeros((3, 3)),
            np.array([0.0, np.inf]),
        )

    def test_observation_times_outside_range_message_is_unchanged(self):
        self.assert_value_error(
            "Observation time falls outside ground-truth range.",
            schedule.interpolate_positions,
            np.array([0.0, 10.0, 20.0]),
            np.zeros((3, 3)),
            np.array([-1.0]),
        )
        self.assert_value_error(
            "Observation time falls outside ground-truth range.",
            schedule.interpolate_positions,
            np.array([0.0, 10.0, 20.0]),
            np.zeros((3, 3)),
            np.array([21.0]),
        )


class ScheduleCompatibilityTests(unittest.TestCase):
    """The old path must re-export the new implementation, not duplicate it."""

    def test_old_path_reexports_new_functions(self):
        self.assertIs(
            old_generate_observation_times,
            schedule.generate_observation_times,
        )
        self.assertIs(
            old_interpolate_positions,
            schedule.interpolate_positions,
        )

    def test_old_and_new_paths_return_identical_arrays(self):
        arguments = (0.0, 1826.25, 7.0, 0.0, 1826.25)

        old_times = old_generate_observation_times(*arguments)
        new_times = schedule.generate_observation_times(*arguments)

        np.testing.assert_array_equal(old_times, new_times)

        ground_truth_times = np.array([0.0, 10.0, 20.0])
        ground_truth_positions = np.column_stack(
            (
                ground_truth_times,
                2.0 * ground_truth_times,
                -ground_truth_times,
            )
        )
        observation_times = np.array([0.0, 5.0, 10.0, 15.0, 20.0])

        old_positions = old_interpolate_positions(
            ground_truth_times,
            ground_truth_positions,
            observation_times,
        )
        new_positions = schedule.interpolate_positions(
            ground_truth_times,
            ground_truth_positions,
            observation_times,
        )

        np.testing.assert_array_equal(old_positions, new_positions)


if __name__ == "__main__":
    unittest.main(verbosity=2)
