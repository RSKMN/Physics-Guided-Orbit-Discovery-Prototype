"""Focused tests for the migrated Component 2 trajectory loader.

These tests use temporary CSV fixtures only and never write into the
repository. They are written with the standard-library ``unittest`` framework
because pytest is not installed in the development environment.

Run directly with::

    python tests/test_component2_loader.py -v
"""

from __future__ import annotations

import csv
import inspect
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_DIR = _REPO_ROOT / "src"
for _path in (_REPO_ROOT, _SRC_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from orbit_discovery.component2_observations import loader
from orbit_discovery.core import constants
from src.trajectory_loader import (
    REQUIRED_COLUMNS as old_required_columns,
    load_trajectory as old_load_trajectory,
)


class _LoaderTestCase(unittest.TestCase):
    """Provide disposable CSV fixtures and exact error assertions."""

    def setUp(self):
        self._temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary_directory.cleanup)
        self.tmp_path = Path(self._temporary_directory.name)

    def valid_rows(self):
        return [
            {
                "time_years": 0.0,
                "time_days": 0.0,
                "x_au": 1.0,
                "y_au": 2.0,
                "z_au": 3.0,
                "vx_au_per_year": 0.1,
                "vy_au_per_year": 0.2,
                "vz_au_per_year": 0.3,
            },
            {
                "time_years": 1.0,
                "time_days": 365.25,
                "x_au": 4.0,
                "y_au": 5.0,
                "z_au": 6.0,
                "vx_au_per_year": 0.4,
                "vy_au_per_year": 0.5,
                "vz_au_per_year": 0.6,
            },
            {
                "time_years": 2.5,
                "time_days": 913.125,
                "x_au": -1.0,
                "y_au": -2.0,
                "z_au": -3.0,
                "vx_au_per_year": -0.1,
                "vy_au_per_year": -0.2,
                "vz_au_per_year": -0.3,
            },
        ]

    def write_csv(self, rows, columns=None, filename="trajectory.csv"):
        columns = list(
            loader.REQUIRED_COLUMNS if columns is None else columns
        )
        path = self.tmp_path / filename

        with path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=columns)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

        return path

    def rows_for_columns(self, rows, columns):
        return [
            {key: value for key, value in row.items() if key in columns}
            for row in rows
        ]

    def load_with_output(self, path):
        output = io.StringIO()
        with redirect_stdout(output):
            result = loader.load_trajectory(path)
        return result, output.getvalue()

    def assert_value_error(self, message, path):
        with self.assertRaises(ValueError) as context:
            loader.load_trajectory(path)
        self.assertEqual(str(context.exception), message)


class LoaderSignatureAndContractTests(unittest.TestCase):
    """The migrated public contract must not change."""

    def test_required_columns_are_exact_and_ordered(self):
        self.assertEqual(
            loader.REQUIRED_COLUMNS,
            [
                "time_years",
                "time_days",
                "x_au",
                "y_au",
                "z_au",
                "vx_au_per_year",
                "vy_au_per_year",
                "vz_au_per_year",
            ],
        )

    def test_load_trajectory_signature_is_unchanged(self):
        signature = inspect.signature(loader.load_trajectory)
        parameters = list(signature.parameters.values())

        self.assertEqual([parameter.name for parameter in parameters], ["csv_path"])
        self.assertEqual(
            parameters[0].kind,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        )
        self.assertIs(parameters[0].default, inspect.Parameter.empty)


class ValidTrajectoryTests(_LoaderTestCase):
    """Characterisation tests for a valid trajectory fixture."""

    def test_valid_csv_returns_expected_contract(self):
        path = self.write_csv(self.valid_rows())

        result, output = self.load_with_output(path)

        self.assertIsInstance(result, dict)
        self.assertEqual(
            list(result),
            [
                "time_years",
                "time_days",
                "positions",
                "velocities",
                "number_of_samples",
            ],
        )
        self.assertEqual(result["number_of_samples"], 3)

        self.assertEqual(result["time_years"].shape, (3,))
        self.assertEqual(result["time_days"].shape, (3,))
        self.assertEqual(result["positions"].shape, (3, 3))
        self.assertEqual(result["velocities"].shape, (3, 3))
        self.assertTrue(
            np.issubdtype(result["time_years"].dtype, np.floating)
        )
        self.assertTrue(
            np.issubdtype(result["time_days"].dtype, np.floating)
        )
        self.assertTrue(
            np.issubdtype(result["positions"].dtype, np.floating)
        )
        self.assertTrue(
            np.issubdtype(result["velocities"].dtype, np.floating)
        )

        np.testing.assert_array_equal(
            result["time_years"],
            np.array([0.0, 1.0, 2.5]),
        )
        np.testing.assert_array_equal(
            result["time_days"],
            np.array([0.0, 365.25, 913.125]),
        )
        np.testing.assert_array_equal(
            result["positions"],
            np.array(
                [
                    [1.0, 2.0, 3.0],
                    [4.0, 5.0, 6.0],
                    [-1.0, -2.0, -3.0],
                ]
            ),
        )
        np.testing.assert_array_equal(
            result["velocities"],
            np.array(
                [
                    [0.1, 0.2, 0.3],
                    [0.4, 0.5, 0.6],
                    [-0.1, -0.2, -0.3],
                ]
            ),
        )

        self.assertEqual(
            output.splitlines(),
            [
                "Trajectory loaded successfully.",
                "Number of samples: 3",
                "Duration: 0.000 to 2.500 years",
            ],
        )

    def test_extra_columns_are_ignored(self):
        columns = list(loader.REQUIRED_COLUMNS) + ["diagnostic_note"]
        rows = self.valid_rows()
        for index, row in enumerate(rows):
            row["diagnostic_note"] = f"row-{index}"

        path = self.write_csv(rows, columns=columns)
        result, _ = self.load_with_output(path)

        self.assertEqual(len(result), 5)
        self.assertEqual(result["number_of_samples"], 3)
        self.assertEqual(result["positions"].shape, (3, 3))
        self.assertEqual(result["velocities"].shape, (3, 3))

    def test_time_conversion_matches_days_per_year(self):
        path = self.write_csv(self.valid_rows())
        result, _ = self.load_with_output(path)

        np.testing.assert_array_equal(
            result["time_days"],
            result["time_years"] * constants.DAYS_PER_YEAR,
        )

    def test_time_consistency_tolerance_is_preserved(self):
        rows = self.valid_rows()[:2]
        rows[1]["time_days"] = 365.2500005

        path = self.write_csv(rows)
        result, _ = self.load_with_output(path)

        self.assertEqual(result["number_of_samples"], 2)


class LoaderValidationTests(_LoaderTestCase):
    """Characterisation tests for the existing validation paths."""

    def test_missing_file_message_is_unchanged(self):
        path = self.tmp_path / "missing.csv"

        with self.assertRaises(FileNotFoundError) as context:
            loader.load_trajectory(path)

        self.assertEqual(
            str(context.exception),
            f"Trajectory file not found: {path}",
        )

    def test_missing_required_columns_message_is_unchanged(self):
        columns = [
            column
            for column in loader.REQUIRED_COLUMNS
            if column not in {"time_days", "vz_au_per_year"}
        ]
        rows = self.rows_for_columns(self.valid_rows(), columns)
        path = self.write_csv(rows, columns=columns)

        self.assert_value_error(
            "Missing required columns: ['time_days', 'vz_au_per_year']",
            path,
        )

    def test_invalid_numeric_message_is_unchanged(self):
        rows = self.valid_rows()
        rows[0]["x_au"] = "not-a-number"
        path = self.write_csv(rows)

        self.assert_value_error(
            "Trajectory contains missing or invalid numerical values.",
            path,
        )

    def test_missing_numeric_value_message_is_unchanged(self):
        rows = self.valid_rows()
        rows[0]["x_au"] = ""
        path = self.write_csv(rows)

        self.assert_value_error(
            "Trajectory contains missing or invalid numerical values.",
            path,
        )

    def test_infinite_value_message_is_unchanged(self):
        rows = self.valid_rows()
        rows[0]["x_au"] = "inf"
        path = self.write_csv(rows)

        self.assert_value_error(
            "Trajectory contains infinite or non-finite values.",
            path,
        )

    def test_too_few_samples_message_is_unchanged(self):
        path = self.write_csv(self.valid_rows()[:1])

        self.assert_value_error(
            "Trajectory must contain at least two samples.",
            path,
        )

    def test_non_increasing_timestamps_message_is_unchanged(self):
        rows = self.valid_rows()[:2]
        rows[1]["time_years"] = 0.0
        rows[1]["time_days"] = 0.0
        path = self.write_csv(rows)

        self.assert_value_error(
            "Trajectory timestamps must be strictly increasing.",
            path,
        )

    def test_inconsistent_time_columns_message_is_unchanged(self):
        rows = self.valid_rows()[:2]
        rows[1]["time_days"] = 365.0
        path = self.write_csv(rows)

        self.assert_value_error(
            "Time columns are inconsistent.",
            path,
        )

    def test_validation_order_is_preserved(self):
        missing_columns = [
            column
            for column in loader.REQUIRED_COLUMNS
            if column != "vz_au_per_year"
        ]
        rows = self.rows_for_columns(self.valid_rows()[:2], missing_columns)
        rows[0]["x_au"] = "not-a-number"
        path = self.write_csv(rows, columns=missing_columns)
        self.assert_value_error(
            "Missing required columns: ['vz_au_per_year']",
            path,
        )

        rows = self.valid_rows()[:2]
        rows[0]["x_au"] = "not-a-number"
        rows[1]["y_au"] = "inf"
        path = self.write_csv(rows)
        self.assert_value_error(
            "Trajectory contains missing or invalid numerical values.",
            path,
        )

        rows = self.valid_rows()[:1]
        rows[0]["x_au"] = "inf"
        path = self.write_csv(rows)
        self.assert_value_error(
            "Trajectory contains infinite or non-finite values.",
            path,
        )

        rows = self.valid_rows()[:2]
        rows[1]["time_years"] = 0.0
        rows[1]["time_days"] = 365.0
        path = self.write_csv(rows)
        self.assert_value_error(
            "Trajectory timestamps must be strictly increasing.",
            path,
        )


class LoaderCompatibilityTests(_LoaderTestCase):
    """The old path must re-export the new implementation, not duplicate it."""

    def test_old_path_reexports_new_objects(self):
        self.assertIs(old_required_columns, loader.REQUIRED_COLUMNS)
        self.assertIs(old_load_trajectory, loader.load_trajectory)

    def test_old_and_new_paths_return_identical_contract(self):
        path = self.write_csv(self.valid_rows())

        old_output = io.StringIO()
        with redirect_stdout(old_output):
            old_trajectory = old_load_trajectory(path)

        new_trajectory, new_output = self.load_with_output(path)

        self.assertEqual(list(old_trajectory), list(new_trajectory))
        for key in old_trajectory:
            if isinstance(old_trajectory[key], np.ndarray):
                np.testing.assert_array_equal(
                    old_trajectory[key],
                    new_trajectory[key],
                )
            else:
                self.assertEqual(old_trajectory[key], new_trajectory[key])

        self.assertEqual(old_output.getvalue(), new_output)


if __name__ == "__main__":
    unittest.main(verbosity=2)
