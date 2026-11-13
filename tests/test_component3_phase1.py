"""Focused tests for Component 3 Phase 1 implementation.

Covers:
- Valid observation loading
- Missing required columns
- Invalid numerical values
- Invalid uncertainties
- Invalid RA/Dec ranges
- Timestamp validation
- Ground-truth column rejection
- Six-dimensional OrbitState validation
- Result-model serialization and deserialization
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

# Ensure source tree importable
import sys as _sys
from pathlib import Path as _Path

_REPO_ROOT = _Path(__file__).resolve().parents[1]
_SRC_DIR = _REPO_ROOT / "src"
for _path in (_REPO_ROOT, _SRC_DIR):
    if str(_path) not in _sys.path:
        _sys.path.insert(0, str(_path))

from orbit_discovery.component3.models import (
    REFERENCE_EPOCH_YEARS,
    BestFitResult,
    EstimationResult,
    ObservationDataset,
    OrbitCandidate,
    OrbitState,
)
from orbit_discovery.component3.loader import load_dataset_for_estimation


class _TempFileFixture:
    """Create temporary observation CSV + metadata.json files."""

    def __init__(self, root: Path, name: str = "temp_obs"):
        self.dir = root / name
        self.dir.mkdir(parents=True, exist_ok=True)
        self.csv_path = self.dir / "observations.csv"
        self.meta_path = self.dir / "metadata.json"

    def write(self, columns: list[str], rows: list[list], metadata: dict | None = None):
        import csv as _csv

        with self.csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = _csv.writer(f)
            writer.writerow(columns)
            writer.writerows(rows)

        if metadata is None:
            metadata = {
                "observation_name": "temp_obs",
                "input_trajectory": "tests/temp/trajectory.csv",
                "observer": {
                    "orbital_radius_au": 1.0,
                    "orbital_period_years": 1.0,
                    "initial_phase_deg": 90.0,
                },
                "measurement_noise": {
                    "sigma_ra_cosdec_arcsec": 0.5,
                    "sigma_dec_arcsec": 0.5,
                    "random_seed": 42,
                },
                "frame": "equatorial",
                "time_scale": "TT",
            }
        self.meta_path.write_text(
            json.dumps(metadata, indent=2), encoding="utf-8"
        )


def _make_obs_dirs(n_rows: int = 5) -> tuple[list[str], list[list], dict]:
    columns = [
        "obs_id",
        "time_years",
        "time_days",
        "ra_deg",
        "dec_deg",
        "sigma_ra_cosdec_arcsec",
        "sigma_dec_arcsec",
        "frame",
        "time_scale",
    ]
    rows = []
    for i in range(n_rows):
        days = i * 7.0
        years = days / 365.25
        rows.append(
            [
                i,
                years,
                days,
                335.0 + i,
                -10.0 + i * 0.5,
                0.5,
                0.5,
                "equatorial",
                "TT",
            ]
        )
    metadata = {
        "observation_name": "temp_obs",
        "input_trajectory": "tests/temp/trajectory.csv",
        "observer": {
            "orbital_radius_au": 1.0,
            "orbital_period_years": 1.0,
            "initial_phase_deg": 90.0,
        },
        "measurement_noise": {
            "sigma_ra_cosdec_arcsec": 0.5,
            "sigma_dec_arcsec": 0.5,
            "random_seed": 42,
        },
        "frame": "equatorial",
        "time_scale": "TT",
    }
    return columns, rows, metadata


class ObservationLoadingTests(unittest.TestCase):
    """Tests for the observation loader."""

    def test_valid_observation_loading(self):
        """A valid observation CSV loads cleanly through the C3 loader."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            columns, rows, metadata = _make_obs_dirs(5)
            fixture = _TempFileFixture(root)
            fixture.write(columns, rows, metadata)

            dataset = load_dataset_for_estimation(fixture.csv_path)

            self.assertEqual(len(dataset.data["obs_id"]), 5)
            self.assertEqual(len(dataset.data["time_days"]), 5)
            self.assertEqual(len(dataset.data["ra_deg"]), 5)
            self.assertEqual(len(dataset.data["dec_deg"]), 5)
            self.assertEqual(len(dataset.data["sigma_ra_cosdec_arcsec"]), 5)
            self.assertEqual(len(dataset.data["sigma_dec_arcsec"]), 5)

    def test_metadata_preserved(self):
        """Dataset identity and source metadata are preserved."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            columns, rows, metadata = _make_obs_dirs(3)
            fixture = _TempFileFixture(root)
            fixture.write(columns, rows, metadata)

            dataset = load_dataset_for_estimation(fixture.csv_path)
            self.assertEqual(dataset.metadata["observation_name"], "temp_obs")
            self.assertEqual(dataset.metadata["frame"], "equatorial")
            self.assertEqual(dataset.metadata["time_scale"], "TT")


class ValidationFailureTests(unittest.TestCase):
    """Tests for various validation failures."""

    def test_missing_required_column(self):
        """Missing a required column raises ValueError."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = _TempFileFixture(root)

            columns = [
                "obs_id",
                "time_years",
                "time_days",
                "ra_deg",
                "dec_deg",
                "sigma_ra_cosdec_arcsec",
                "frame",
                "time_scale",
            ]  # missing sigma_dec_arcsec
            rows = [
                [0, 0.0, 0.0, 335.0, -10.0, 0.5, "equatorial", "TT"],
            ]
            fixture.write(columns, rows)

            with self.assertRaises(ValueError):
                load_dataset_for_estimation(fixture.csv_path)

    def test_infinite_value(self):
        """Non-finite values are rejected."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = _TempFileFixture(root)

            columns = [
                "obs_id",
                "time_years",
                "time_days",
                "ra_deg",
                "dec_deg",
                "sigma_ra_cosdec_arcsec",
                "sigma_dec_arcsec",
                "frame",
                "time_scale",
            ]
            rows = [
                [0, np.inf, 0.0, 335.0, -10.0, 0.5, 0.5, "equatorial", "TT"],
            ]
            fixture.write(columns, rows)

            with self.assertRaises(ValueError):
                load_dataset_for_estimation(fixture.csv_path)

    def test_zero_uncertainty(self):
        """Zero or negative uncertainties are rejected."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = _TempFileFixture(root)

            columns = [
                "obs_id",
                "time_years",
                "time_days",
                "ra_deg",
                "dec_deg",
                "sigma_ra_cosdec_arcsec",
                "sigma_dec_arcsec",
                "frame",
                "time_scale",
            ]
            rows = [
                [0, 0.0, 0.0, 335.0, -10.0, 0.0, 0.5, "equatorial", "TT"],
            ]
            fixture.write(columns, rows)

            with self.assertRaises(ValueError):
                load_dataset_for_estimation(fixture.csv_path)

    def test_invalid_ra_range(self):
        """RA outside [0, 360] is rejected."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = _TempFileFixture(root)

            columns = [
                "obs_id",
                "time_years",
                "time_days",
                "ra_deg",
                "dec_deg",
                "sigma_ra_cosdec_arcsec",
                "sigma_dec_arcsec",
                "frame",
                "time_scale",
            ]
            rows = [
                [0, 0.0, 0.0, 361.0, -10.0, 0.5, 0.5, "equatorial", "TT"],
            ]
            fixture.write(columns, rows)

            with self.assertRaises(ValueError):
                load_dataset_for_estimation(fixture.csv_path)

    def test_invalid_dec_range(self):
        """Dec outside [-90, 90] is rejected."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = _TempFileFixture(root)

            columns = [
                "obs_id",
                "time_years",
                "time_days",
                "ra_deg",
                "dec_deg",
                "sigma_ra_cosdec_arcsec",
                "sigma_dec_arcsec",
                "frame",
                "time_scale",
            ]
            rows = [
                [0, 0.0, 0.0, 335.0, 95.0, 0.5, 0.5, "equatorial", "TT"],
            ]
            fixture.write(columns, rows)

            with self.assertRaises(ValueError):
                load_dataset_for_estimation(fixture.csv_path)

    def test_inconsistent_time_columns(self):
        """time_days and time_years inconsistency is rejected."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = _TempFileFixture(root)

            columns = [
                "obs_id",
                "time_years",
                "time_days",
                "ra_deg",
                "dec_deg",
                "sigma_ra_cosdec_arcsec",
                "sigma_dec_arcsec",
                "frame",
                "time_scale",
            ]
            rows = [
                [0, 0.0, 100.0, 335.0, -10.0, 0.5, 0.5, "equatorial", "TT"],
            ]
            fixture.write(columns, rows)

            with self.assertRaises(ValueError):
                load_dataset_for_estimation(fixture.csv_path)

    def test_ground_truth_column_rejected(self):
        """true_* columns cause ValueError rejection."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = _TempFileFixture(root)

            columns = [
                "obs_id",
                "time_years",
                "time_days",
                "ra_deg",
                "dec_deg",
                "sigma_ra_cosdec_arcsec",
                "sigma_dec_arcsec",
                "true_ra_deg",
                "true_dec_deg",
                "frame",
                "time_scale",
            ]
            rows = [
                [
                    0,
                    0.0,
                    0.0,
                    335.0,
                    -10.0,
                    0.5,
                    0.5,
                    335.0,
                    -10.0,
                    "equatorial",
                    "TT",
                ],
            ]
            fixture.write(columns, rows)

            with self.assertRaises(ValueError):
                load_dataset_for_estimation(fixture.csv_path)


class OrbitStateTests(unittest.TestCase):
    """Tests for the OrbitState six-dimensional state model."""

    def test_valid_state(self):
        """A valid state can be created and validated."""
        state = OrbitState(2.5, 0.0, 0.0, 0.0, 3.973, 0.0)
        state.validate()
        self.assertEqual(state.rx, 2.5)
        self.assertEqual(state.vy, 3.973)

    def test_state_to_array(self):
        """to_array returns a 6-element array in correct order."""
        state = OrbitState(1.0, 2.0, 3.0, 0.1, 0.2, 0.3)
        arr = state.to_array()
        self.assertEqual(arr.shape, (6,))
        np.testing.assert_array_equal(arr, np.array([1.0, 2.0, 3.0, 0.1, 0.2, 0.3]))

    def test_nonfinite_state_rejected(self):
        """Non-finite state values are rejected."""
        state = OrbitState(np.nan, 0.0, 0.0, 0.0, 0.0, 0.0)
        with self.assertRaises(ValueError):
            state.validate()

    def test_state_to_dict_and_from_dict(self):
        """State serialization round-trip preserves values."""
        state = OrbitState(1.0, 2.0, 3.0, 0.1, 0.2, 0.3)
        d = state.to_dict()
        self.assertEqual(d, {"rx": 1.0, "ry": 2.0, "rz": 3.0, "vx": 0.1, "vy": 0.2, "vz": 0.3})
        restored = OrbitState.from_dict(d)
        self.assertEqual(restored, state)


class ResultModelTests(unittest.TestCase):
    """Tests for result data models."""

    def test_orbit_candidate_creation(self):
        """OrbitCandidate can be created and holds a state."""
        state = OrbitState(2.0, 0.0, 0.0, 0.0, 3.0, 0.0)
        candidate = OrbitCandidate(state=state, epoch_years=0.0, metadata={})
        self.assertEqual(candidate.state, state)
        self.assertEqual(candidate.epoch_years, 0.0)

    def test_best_fit_result_creation(self):
        """BestFitResult can be created."""
        state = OrbitState(1.0, 0.0, 0.0, 0.0, 1.0, 0.0)
        residuals = {"ra": np.array([0.1]), "dec": np.array([0.2])}
        metrics = {"chi2": 0.05}
        result = BestFitResult(state=state, epoch_years=0.0, residuals=residuals, fit_metrics=metrics)
        self.assertEqual(result.state, state)
        self.assertEqual(result.fit_metrics["chi2"], 0.05)

    def test_estimation_result_creation(self):
        """EstimationResult can be created."""
        state = OrbitState(2.5, 0.0, 0.0, 0.0, 3.973, 0.0)
        candidate = OrbitCandidate(state=state, epoch_years=0.0, metadata={})
        residuals = {"ra": np.array([0.1]), "dec": np.array([0.2])}
        metrics = {"chi2": 0.05}
        best = BestFitResult(state=state, epoch_years=0.0, residuals=residuals, fit_metrics=metrics)
        result = EstimationResult(
            candidates=[candidate],
            best_fit=best,
            source_dataset_metadata={"name": "temp_obs"},
        )
        self.assertEqual(len(result.candidates), 1)
        self.assertEqual(result.best_fit, best)
        self.assertEqual(result.source_dataset_metadata["name"], "temp_obs")


class ReferenceEpochTests(unittest.TestCase):
    """Tests for reference epoch documentation."""

    def test_reference_epoch_value(self):
        """The reference epoch constant is explicitly documented."""
        self.assertEqual(REFERENCE_EPOCH_YEARS, 0.0)

    def test_observation_dataset_timestamp_consistency(self):
        """ObservationDataset validates non-decreasing timestamps."""
        columns = [
            "obs_id",
            "time_years",
            "time_days",
            "ra_deg",
            "dec_deg",
            "sigma_ra_cosdec_arcsec",
            "sigma_dec_arcsec",
            "frame",
            "time_scale",
        ]
        rows = [
            [0, 0.0, 0.0, 335.0, -10.0, 0.5, 0.5, "equatorial", "TT"],
            [1, 0.01, 3.6525, 335.1, -9.9, 0.5, 0.5, "equatorial", "TT"],
            [2, 0.0, 0.0, 335.2, -9.8, 0.5, 0.5, "equatorial", "TT"],  # not increasing
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = _TempFileFixture(root)
            fixture.write(columns, rows)

            with self.assertRaises(ValueError):
                load_dataset_for_estimation(fixture.csv_path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
