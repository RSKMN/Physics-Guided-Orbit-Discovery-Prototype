"""Focused tests for the migrated Component 2 observer module.

These tests are hermetic: they use in-memory NumPy arrays only and never write
into the repository. They are written with the standard-library ``unittest``
framework because pytest is not installed in the development environment.

Run directly with::

    python tests/test_component2_observer.py -v
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

from orbit_discovery.component2_observations import observer
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
