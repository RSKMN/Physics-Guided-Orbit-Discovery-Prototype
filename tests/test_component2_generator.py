"""Focused tests for the migrated Component 2 observation generator.

These tests use temporary directories and synthetic trajectory/config fixtures
only. They never write into the repository's tracked data, results, or plots
directories. They are written with the standard-library ``unittest`` framework
because pytest is not installed in the development environment.

Run directly with::

    python tests/test_component2_generator.py -v
"""

from __future__ import annotations

import ast
import csv
import inspect
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_DIR = _REPO_ROOT / "src"
for _path in (_REPO_ROOT, _SRC_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from orbit_discovery.component2_observations import generator
from src.observation_generator import (
    DAYS_PER_YEAR as old_days_per_year,
    PROJECT_ROOT as old_project_root,
    generate_observations as old_generate_observations,
    load_config as old_load_config,
    main as old_main,
)


TRAJECTORY_COLUMNS = [
    "time_years",
    "time_days",
    "x_au",
    "y_au",
    "z_au",
    "vx_au_per_year",
    "vy_au_per_year",
    "vz_au_per_year",
]

EXPECTED_COLUMNS = [
    "time_years",
    "time_days",
    "ra_deg",
    "dec_deg",
    "sigma_ra_cosdec_arcsec",
    "sigma_dec_arcsec",
    "true_ra_deg",
    "true_dec_deg",
]

METADATA_KEYS = [
    "observation_name",
    "input_trajectory",
    "configuration_file",
    "state_type",
    "number_of_observations",
    "observation_schedule",
    "observer",
    "coordinates",
    "measurement_noise",
    "coordinate_units",
    "assumptions",
    "output_file",
    "ground_truth",
]

# Reference values produced by the pre-migration implementation for the
# synthetic fixture below. They are intentionally exact characterisation
# values, not tolerance-based scientific assertions.
EXPECTED_TIME_DAYS = [
    0.0,
    2.0,
    4.0,
    6.0,
    8.0,
    10.0,
]
EXPECTED_TIME_YEARS = [
    0.0,
    0.0054757015742642025,
    0.010951403148528405,
    0.01642710472279261,
    0.02190280629705681,
    0.02737850787132101,
]
EXPECTED_RA = [
    333.5029262589353,
    336.262743008174,
    338.9050865625134,
    341.43134084671516,
    343.84450256605487,
    346.1495493536276,
]
EXPECTED_DEC = [
    -5.477095985513918,
    -4.2447157449868635,
    -3.0522066276507283,
    -1.9036134151413933,
    -0.8008087127746286,
    0.2543953745488727,
]
EXPECTED_TRUE_RA = [
    333.5028837430081,
    336.2628878476953,
    338.90498218511453,
    341.43121014060205,
    343.84477356964226,
    346.14973021367365,
]
EXPECTED_TRUE_DEC = [
    -5.477113741125469,
    -4.244671822404594,
    -3.0522042941566303,
    -1.903494936818119,
    -0.8009308513822485,
    0.2542873478911742,
]


class _GeneratorTestCase(unittest.TestCase):
    """Provide a disposable trajectory, config, and output directory."""

    def setUp(self):
        self._temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary_directory.cleanup)
        self.tmp_path = Path(self._temporary_directory.name)

    def write_trajectory(self, path):
        rows = []
        for day in range(0, 11):
            rows.append(
                {
                    "time_years": day / generator.DAYS_PER_YEAR,
                    "time_days": float(day),
                    "x_au": 1.0 + 0.01 * day,
                    "y_au": 0.5 + 0.02 * day,
                    "z_au": 0.1 + 0.003 * day,
                    "vx_au_per_year": 0.01,
                    "vy_au_per_year": 0.02,
                    "vz_au_per_year": 0.003,
                }
            )

        with path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=TRAJECTORY_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)

    def make_config(self, trajectory_path, output_directory, **overrides):
        config = {
            "observation_name": "temp_observations",
            "input_trajectory": str(trajectory_path),
            "observer": {
                "model": "idealized_circular",
                "orbital_radius_au": 1.0,
                "orbital_period_years": 1.0,
                "initial_phase_deg": 90.0,
            },
            "coordinates": {
                "input_frame": "heliocentric_ecliptic",
                "output_frame": "equatorial",
                "obliquity_deg": 23.43928,
                "ra_unit": "degrees",
                "dec_unit": "degrees",
            },
            "observation_schedule": {
                "cadence_days": 2.0,
                "start_day": 0.0,
                "end_day": 10.0,
            },
            "measurement_noise": {
                "model": "gaussian",
                "sigma_ra_cosdec_arcsec": 0.5,
                "sigma_dec_arcsec": 0.5,
                "random_seed": 42,
            },
            "output": {
                "directory": str(output_directory),
                "save_noise_free_coordinates": True,
                "save_metadata": True,
            },
        }
        config.update(overrides)
        return config

    def write_config(self, path, config):
        path.write_text(json.dumps(config, indent=4), encoding="utf-8")
        return path

    def make_fixture(self):
        trajectory_path = self.tmp_path / "trajectory.csv"
        config_path = self.tmp_path / "observations.json"
        output_directory = self.tmp_path / "output"
        self.write_trajectory(trajectory_path)
        config = self.make_config(trajectory_path, output_directory)
        self.write_config(config_path, config)
        self.trajectory_path = trajectory_path
        self.config_path = config_path
        self.config = config
        self.output_directory = output_directory
        return config_path

    def run_generator(self, config_path):
        output = io.StringIO()
        with redirect_stdout(output):
            observations, metadata = generator.generate_observations(config_path)
        return observations, metadata, output.getvalue()

    def output_paths(self, observation_name="temp_observations"):
        directory = self.output_directory / observation_name
        return directory, directory / "observations.csv", directory / "metadata.json"


class GeneratorSignatureAndConstantTests(_GeneratorTestCase):
    """The migrated public contract must remain unchanged."""

    def test_load_config_signature_is_unchanged(self):
        signature = inspect.signature(generator.load_config)
        self.assertEqual(list(signature.parameters), ["config_path"])
        self.assertEqual(
            signature.parameters["config_path"].kind,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        )
        self.assertEqual(
            signature.parameters["config_path"].default,
            inspect.Parameter.empty,
        )

    def test_generate_observations_signature_is_unchanged(self):
        signature = inspect.signature(generator.generate_observations)
        self.assertEqual(list(signature.parameters), ["config_path"])
        self.assertEqual(
            signature.parameters["config_path"].kind,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        )
        self.assertEqual(
            signature.parameters["config_path"].default,
            inspect.Parameter.empty,
        )

    def test_main_signature_is_unchanged(self):
        signature = inspect.signature(generator.main)
        self.assertEqual(list(signature.parameters), [])

    def test_public_constants_are_preserved(self):
        self.assertEqual(generator.DAYS_PER_YEAR, 365.25)
        self.assertEqual(generator.PROJECT_ROOT, _REPO_ROOT.resolve())

    def test_old_and_new_paths_reexport_identical_objects(self):
        self.assertIs(old_load_config, generator.load_config)
        self.assertIs(old_generate_observations, generator.generate_observations)
        self.assertIs(old_main, generator.main)
        self.assertEqual(old_project_root, generator.PROJECT_ROOT)
        self.assertEqual(old_days_per_year, generator.DAYS_PER_YEAR)

    def test_legacy_file_contains_no_duplicate_implementation(self):
        source = (_REPO_ROOT / "src" / "observation_generator.py").read_text(
            encoding="utf-8"
        )
        tree = ast.parse(source)
        definitions = [
            node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        ]
        self.assertEqual(definitions, [])


    def test_default_config_selection_is_unchanged(self):
        with mock.patch.object(generator, "generate_observations") as mocked:
            with mock.patch(
                "sys.argv", ["observation_generator.py"]
            ):
                result = generator.main()

        self.assertIsNone(result)
        mocked.assert_called_once_with("configs/synthetic_observations.json")

    def test_explicit_config_selection_is_unchanged(self):
        with mock.patch.object(generator, "generate_observations") as mocked:
            with mock.patch(
                "sys.argv",
                ["observation_generator.py", "--config", "custom.json"],
            ):
                result = generator.main()

        self.assertIsNone(result)
        mocked.assert_called_once_with("custom.json")

    def test_relative_config_path_resolves_against_project_root(self):
        project_root = self.tmp_path / "project"
        configs = project_root / "configs"
        configs.mkdir(parents=True)
        config_path = configs / "relative.json"
        self.write_config(config_path, {"marker": True})

        with mock.patch.object(generator, "PROJECT_ROOT", project_root):
            config, resolved_path = generator.load_config(
                "configs/relative.json"
            )

        self.assertEqual(config, {"marker": True})
        self.assertEqual(resolved_path, config_path)

    def test_absolute_config_path_is_preserved(self):
        config_path = self.tmp_path / "absolute.json"
        self.write_config(config_path, {"marker": True})

        config, resolved_path = generator.load_config(config_path)

        self.assertEqual(config, {"marker": True})
        self.assertEqual(resolved_path, config_path)

    def test_missing_config_message_is_unchanged(self):
        missing_path = self.tmp_path / "missing.json"

        with self.assertRaises(FileNotFoundError) as context:
            generator.load_config(missing_path)

        self.assertEqual(
            str(context.exception),
            f"Configuration file not found: {missing_path}",
        )

    def test_malformed_config_raises_json_decode_error(self):
        config_path = self.tmp_path / "malformed.json"
        config_path.write_text("{not valid json", encoding="utf-8")

        with self.assertRaises(json.JSONDecodeError):
            generator.load_config(config_path)

    def test_missing_required_key_raises_key_error(self):
        config_path = self.make_fixture()
        config = json.loads(config_path.read_text(encoding="utf-8"))
        del config["observer"]
        self.write_config(config_path, config)

        with self.assertRaises(KeyError) as context:
            self.run_generator(config_path)

        self.assertEqual(str(context.exception), "'observer'")

    def test_missing_trajectory_message_is_unchanged(self):
        missing_trajectory = self.tmp_path / "missing.csv"
        config_path = self.tmp_path / "missing_trajectory.json"
        config = self.make_config(missing_trajectory, self.tmp_path / "out")
        self.write_config(config_path, config)

        with self.assertRaises(FileNotFoundError) as context:
            self.run_generator(config_path)

        self.assertEqual(
            str(context.exception),
            f"Trajectory file not found: {missing_trajectory}",
        )

    def test_invalid_schedule_error_is_unchanged(self):
        config_path = self.make_fixture()
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config["observation_schedule"]["cadence_days"] = 0.0
        self.write_config(config_path, config)

        with self.assertRaises(ValueError) as context:
            self.run_generator(config_path)

        self.assertEqual(
            str(context.exception),
            "Cadence must be greater than zero.",
        )


class ObservationGenerationTests(_GeneratorTestCase):
    """Temporary-fixture generation behaviour and reference values."""

    def test_generation_contract_and_reference_values(self):
        """v2 observation schema: measurements only, no truth columns.

        The observation CSV contains only measurement data (no ground truth).
        True coordinates are written to a separate ground_truth.json file.
        """
        config_path = self.make_fixture()
        observations, metadata, output = self.run_generator(config_path)

        directory, csv_path, metadata_path = self.output_paths()

        self.assertTrue(csv_path.exists())
        self.assertTrue(metadata_path.exists())
        self.assertTrue(directory.is_dir())

        csv_observations = pd.read_csv(csv_path)

        # v2 observation schema: no truth columns in the measurement CSV.
        # true_ra_deg and true_dec_deg are NOT present in the CSV;
        # they are in the separate ground_truth.json file instead.
        # The generator produces columns in this order (obs_id first):
        expected_v2_columns = [
            "obs_id",
            "time_years",
            "time_days",
            "ra_deg",
            "dec_deg",
            "sigma_ra_cosdec_arcsec",
            "sigma_dec_arcsec",
        ]
        self.assertEqual(list(csv_observations.columns), expected_v2_columns)
        self.assertEqual(list(observations.columns), expected_v2_columns)
        # 7 columns: the 6 measurement columns + obs_id (was 8 with truth)
        self.assertEqual(csv_observations.shape, (6, 7))
        self.assertEqual(metadata["number_of_observations"], 6)
        self.assertEqual(len(observations), 6)

        for column in expected_v2_columns:
            if column == "obs_id":
                # obs_id is integer type; tolerate that
                self.assertTrue(
                    pd.api.types.is_integer_dtype(csv_observations[column].dtype),
                    f"obs_id should be integer dtype, got {csv_observations[column].dtype}",
                )
            else:
                self.assertEqual(
                    csv_observations[column].dtype,
                    np.dtype("float64"),
                )

        np.testing.assert_array_equal(
            csv_observations["time_days"].to_numpy(),
            np.asarray(EXPECTED_TIME_DAYS),
        )
        for column, expected in [
            ("time_years", EXPECTED_TIME_YEARS),
            ("ra_deg", EXPECTED_RA),
            ("dec_deg", EXPECTED_DEC),
        ]:
            np.testing.assert_allclose(
                csv_observations[column].to_numpy(),
                np.asarray(expected),
                rtol=0,
                atol=1e-12,
            )

        # obs_id should be integer 0..5
        obs_ids = csv_observations["obs_id"].to_numpy()
        self.assertTrue(
            all(isinstance(x, (int, np.integer)) for x in obs_ids),
            f"obs_id should be integer, got {obs_ids.dtype}"
        )
        self.assertTrue(
            np.array_equal(obs_ids, np.arange(6)),
            f"obs_id should be 0..5, got {obs_ids.tolist()}"
        )

        np.testing.assert_array_equal(
            csv_observations["sigma_ra_cosdec_arcsec"].to_numpy(),
            np.full(6, 0.5),
        )
        np.testing.assert_array_equal(
            csv_observations["sigma_dec_arcsec"].to_numpy(),
            np.full(6, 0.5),
        )

        # Observations returned by the generator should match the CSV
        pd.testing.assert_frame_equal(
            observations,
            csv_observations,
            check_exact=False,
            rtol=0,
            atol=1e-12,
        )

        self.assertIn(
            "Synthetic observation generation successful.",
            output,
        )

    def test_noise_free_coordinates_can_be_disabled(self):
        config_path = self.make_fixture()
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config["observation_name"] = "temp_no_truth"
        config["output"]["save_noise_free_coordinates"] = False
        self.write_config(config_path, config)

        observations, metadata, output = self.run_generator(config_path)
        directory, csv_path, metadata_path = self.output_paths(
            "temp_no_truth"
        )
        csv_observations = pd.read_csv(csv_path)

        # When save_noise_free_coordinates is False, observation CSV has 7 columns
        # (no truth columns). Truth columns must NOT be present in the CSV.
        # Column order matches the generator output: obs_id first, then measurements.
        expected_columns = [
            "obs_id",
            "time_years",
            "time_days",
            "ra_deg",
            "dec_deg",
            "sigma_ra_cosdec_arcsec",
            "sigma_dec_arcsec",
        ]
        self.assertEqual(list(csv_observations.columns), expected_columns)
        self.assertEqual(list(observations.columns), expected_columns)
        # Truth columns must NOT be in the observation CSV when disabled;
        # they should be in the separate ground_truth.json file instead.
        self.assertNotIn("true_ra_deg", csv_observations.columns)
        self.assertNotIn("true_dec_deg", csv_observations.columns)
        # Ground truth should be written only when save_noise_free_coordinates is True
        ground_truth_path = directory / "ground_truth.json"
        self.assertFalse(ground_truth_path.exists())
        self.assertEqual(metadata["number_of_observations"], 6)
        self.assertTrue(metadata_path.exists())
        self.assertIn(f"CSV file: {csv_path}", output)
        self.assertIn(f"Metadata file: {metadata_path}", output)
        self.assertIn("First observation:", output)

    def test_metadata_output_can_be_disabled(self):
        config_path = self.make_fixture()
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config["observation_name"] = "temp_no_metadata"
        config["output"]["save_metadata"] = False
        self.write_config(config_path, config)

        observations, metadata, output = self.run_generator(config_path)
        directory, csv_path, metadata_path = self.output_paths(
            "temp_no_metadata"
        )

        self.assertTrue(csv_path.exists())
        self.assertFalse(metadata_path.exists())
        # v2 schema: observation CSV has 7 columns without truth columns.
        # The generator produces columns in this order (obs_id first):
        expected_columns = [
            "obs_id",
            "time_years",
            "time_days",
            "ra_deg",
            "dec_deg",
            "sigma_ra_cosdec_arcsec",
            "sigma_dec_arcsec",
        ]
        self.assertEqual(list(observations.columns), expected_columns)
        self.assertEqual(metadata["observation_name"], "temp_no_metadata")
        self.assertIn(f"CSV file: {csv_path}", output)
        self.assertNotIn("Metadata file:", output)

    def test_output_directory_is_reused(self):
        config_path = self.make_fixture()
        first_observations, _, _ = self.run_generator(config_path)
        second_observations, _, _ = self.run_generator(config_path)

        pd.testing.assert_frame_equal(
            first_observations,
            second_observations,
            check_exact=False,
            rtol=0,
            atol=1e-12,
        )

    def test_seeded_noise_is_deterministic(self):
        config_path = self.make_fixture()
        first_observations, _, _ = self.run_generator(config_path)
        second_observations, _, _ = self.run_generator(config_path)

        for column in ("ra_deg", "dec_deg"):
            np.testing.assert_array_equal(
                first_observations[column].to_numpy(),
                second_observations[column].to_numpy(),
            )

        pd.testing.assert_frame_equal(
            first_observations,
            second_observations,
            check_exact=False,
            rtol=0,
            atol=1e-12,
        )


class MetadataTests(_GeneratorTestCase):
    """Metadata keys, values, path strings, and file representation."""

    def test_metadata_keys_values_and_absolute_paths(self):
        config_path = self.make_fixture()
        _, metadata, _ = self.run_generator(config_path)
        _, _, metadata_path = self.output_paths()

        self.assertEqual(list(metadata.keys()), METADATA_KEYS)
        self.assertEqual(metadata["observation_name"], "temp_observations")
        self.assertEqual(
            metadata["input_trajectory"],
            str(self.trajectory_path),
        )
        self.assertEqual(
            metadata["configuration_file"],
            str(config_path),
        )
        self.assertEqual(
            metadata["state_type"],
            "synthetic_observations",
        )
        self.assertEqual(metadata["number_of_observations"], 6)
        self.assertEqual(
            metadata["observation_schedule"],
            self.config["observation_schedule"],
        )
        self.assertEqual(metadata["observer"], self.config["observer"])
        self.assertEqual(metadata["coordinates"], self.config["coordinates"])
        self.assertEqual(
            metadata["measurement_noise"],
            self.config["measurement_noise"],
        )
        self.assertEqual(
            metadata["coordinate_units"],
            {
                "time": "days and years",
                "right_ascension": "degrees",
                "declination": "degrees",
                "angular_uncertainty": "arcseconds",
                "distance": "AU",
            },
        )
        self.assertEqual(
            metadata["assumptions"],
            [
                "Idealized circular Earth-like observer orbit",
                "Observer orbit lies in the heliocentric ecliptic plane",
                "Asteroid positions are interpolated from simulated ground truth",
                "Ecliptic coordinates are rotated using the configured obliquity",
                "Gaussian angular measurement noise is applied",
                "Observation times are elapsed simulation times, not real calendar dates",
                "Ground truth is stored separately in ground_truth.json; ",
                "observation CSV contains measurements only.",
            ],
        )
        self.assertEqual(metadata["output_file"], "observations.csv")
        self.assertNotIn("output", metadata)

        with metadata_path.open("r", encoding="utf-8") as file:
            loaded_metadata = json.load(file)
        self.assertEqual(loaded_metadata, metadata)

    def test_metadata_uses_relative_paths_under_project_root(self):
        project_root = self.tmp_path / "project"
        configs = project_root / "configs"
        configs.mkdir(parents=True)
        trajectory_path = project_root / "trajectory.csv"
        self.write_trajectory(trajectory_path)

        config = self.make_config(trajectory_path, project_root / "output")
        config["input_trajectory"] = "trajectory.csv"
        config["output"]["directory"] = "output"
        config_path = configs / "observations.json"
        self.write_config(config_path, config)

        with mock.patch.object(generator, "PROJECT_ROOT", project_root):
            _, metadata, _ = self.run_generator(
                Path("configs") / "observations.json"
            )

        self.assertEqual(metadata["input_trajectory"], "trajectory.csv")
        self.assertEqual(
            metadata["configuration_file"],
            str(Path("configs") / "observations.json"),
        )
        self.assertTrue(
            (
                project_root
                / "output"
                / "temp_observations"
                / "observations.csv"
            ).exists()
        )
        self.assertTrue(
            (
                project_root
                / "output"
                / "temp_observations"
                / "metadata.json"
            ).exists()
        )


class CompatibilityTests(unittest.TestCase):
    """The legacy module path must remain usable."""

    def test_legacy_module_help_exits_successfully(self):
        environment = os.environ.copy()
        environment["PYTHONDONTWRITEBYTECODE"] = "1"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.observation_generator",
                "--help",
            ],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            env=environment,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn(
            "Generate synthetic astronomical observations.",
            result.stdout,
        )
        self.assertIn("--config CONFIG", result.stdout)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)