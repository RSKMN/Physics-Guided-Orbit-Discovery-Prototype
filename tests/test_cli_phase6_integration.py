"""Integration tests for the ``orbit estimate`` CLI subcommand.

Covers CLI dispatch, failure paths, and a successful end-to-end pipeline run.
"""

from __future__ import annotations

import json
import math
from unittest.mock import patch
from pathlib import Path

import numpy as np
import pytest
from orbit_discovery.cli import main
from orbit_discovery.cli.cmd_estimate import _compute_jac_scaled, _STATE_SCALES
from orbit_discovery.component3.estimation import build_residual_function
from orbit_discovery.component3.models import (
    OrbitState,
    OrbitCandidate,
    ObservationDataset,
    BestFitResult,
    EstimationResult,
)


def _write_valid_observation_csv(tmp_path: Path, num_points: int = 5) -> tuple[Path, Path]:
    """Write a small valid observation CSV + metadata.json, return (csv, metadata) paths."""
    rows = []
    for i in range(num_points):
        t_years = i * 0.05
        t_days = t_years * 365.25
        ra = (100.0 + i * 10.0) % 360.0
        dec = 5.0 + i * 2.0
        rows.append(
            f"{i},{t_days},{t_years},{ra},{dec},0.5,0.5,equatorial,TT"
        )
    csv_path = tmp_path / "observations.csv"
    csv_path.write_text(
        "obs_id,time_days,time_years,ra_deg,dec_deg,sigma_ra_cosdec_arcsec,sigma_dec_arcsec,frame,time_scale\n"
        + "\n".join(rows) + "\n",
        encoding="utf-8",
    )
    metadata_path = tmp_path / "metadata.json"
    metadata_path.write_text(
        json.dumps({
            "observation_name": "synthetic_test",
            "observer": {
                "orbital_radius_au": 1.0,
                "orbital_period_years": 1.0,
                "initial_phase_deg": 90.0,
            },
            "coordinates": {
                "obliquity_deg": 23.43928,
            },
        }),
        encoding="utf-8",
    )
    return csv_path, metadata_path


def _write_estimate_config(tmp_path: Path, observations_path: Path, initial_state: dict) -> Path:
    config = {
        "observations": str(observations_path),
        "initial_state": initial_state,
        "bodies": ["Sun"],
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return config_path


def _make_estimation_result(state: OrbitState, converged: bool = True) -> EstimationResult:
    best_fit = BestFitResult(
        state=state,
        epoch_years=0.0,
        residuals={
            "residual_vector": np.zeros(6),
            "ra_arcsec": np.zeros(3),
            "dec_arcsec": np.zeros(3),
            "valid_mask": np.ones(3, dtype=bool),
            "ra_normalized": np.zeros(3),
            "dec_normalized": np.zeros(3),
        },
        fit_metrics={
            "chi2": 1.0,
            "optimality": 1e-9,
            "jacobian_rank": 6,
            "n_valid_scalar_residuals": 6,
        },
    )
    candidate = OrbitCandidate(
        state=state,
        epoch_years=0.0,
        metadata={
            "converged": converged,
            "termination_reason": "converged",
            "n_iter": 5,
            "nfev": 50,
            "njev": 10,
            "optimizer": "least_squares_lm",
            "jacobian_rank": 6,
            "n_valid_scalar_residuals": 6,
            "chi2_reduced": 1.0,
            "chi2": 6.0,
            "start_index": 0,
            "epoch_years": 0.0,
            "coordinate_frame": "heliocentric ecliptic inertial",
            "position_unit": "AU",
            "velocity_unit": "AU/year",
        },
    )
    return EstimationResult(
        candidates=[candidate],
        best_fit=best_fit,
        source_dataset_metadata={},
    )


# ── Existing failure-path tests ──────────────────────────────────────────

def test_estimate_requires_observations(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({}), encoding="utf-8")

    exit_code = main(["estimate", "--config", str(config_path)])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "No observations path specified" in captured.err


def test_estimate_config_missing_initial_state(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    obs_file, metadata_file = _write_valid_observation_csv(tmp_path)
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"observations": str(obs_file)}), encoding="utf-8")

    exit_code = main(["estimate", "--config", str(config_path)])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Config missing 'initial_state'" in captured.err


def test_estimate_invalid_config_path(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["estimate", "--config", "nonexistent.json"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Error" in captured.err


# ── Correction 1: focused Jacobian scaling test ──────────────────────────

def test_estimate_jacobian_scaling_matches_optimizer_convention(tmp_path: Path) -> None:
    """Verify that ``_compute_jac_scaled`` produces ``J_phys @ diag(s)``.

    Matches the convention used by ``least_squares_lm`` in
    ``_numerical_jacobian_scaled`` (scaled forward differences in u = x/s space).
    """
    # Build a simple residual function r(x) = x (identity, m=n=6) for a clean check.
    def identity_residual(x: np.ndarray) -> np.ndarray:
        return np.asarray(x, dtype=float).copy()

    x = np.array([1.0, 2.0, 3.0, 0.1, 0.2, 0.3], dtype=float)
    jac_scaled = _compute_jac_scaled(identity_residual, x, _STATE_SCALES)

    # For r(x) = x, J_phys = I, so J_scaled = I @ diag(s) = diag(s).
    expected = np.diag(_STATE_SCALES)
    np.testing.assert_allclose(jac_scaled, expected, rtol=1e-6, atol=1e-8)


# ── Correction 4: successful CLI integration test ────────────────────────

@patch("orbit_discovery.cli.cmd_estimate.run_multi_start_estimation")
@patch("orbit_discovery.cli.cmd_estimate.run_estimation")
def test_estimate_successful_pipeline(
    mock_run_estimation,
    mock_run_multi_start,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """End-to-end success path: valid observations → structured JSON output."""
    obs_file, _ = _write_valid_observation_csv(tmp_path)

    initial_state = {
        "rx": 1.0, "ry": 0.0, "rz": 0.0,
        "vx": 0.0, "vy": 2.0 * math.pi, "vz": 0.0,
    }
    state = OrbitState(**initial_state)

    mock_run_estimation.return_value = _make_estimation_result(state, converged=True)
    mock_run_multi_start.return_value = (
        _make_estimation_result(state, converged=True),
        [{"start_index": 0, "outcome": "retained"}],
    )

    config_path = _write_estimate_config(tmp_path, obs_file, initial_state)

    exit_code = main(["estimate", "--config", str(config_path)])
    captured = capsys.readouterr()

    assert exit_code == 0, captured.err

    output = json.loads(captured.out)

    # Top-level structure
    assert output["command"] == "estimate"
    assert output["status"] == "success"
    assert "configuration" in output
    assert "caveats" in output

    # Best-fit present and structured
    best_fit = output["best_fit"]
    assert "state" in best_fit
    assert "epoch_years" in best_fit
    assert "fit_metrics" in best_fit
    assert best_fit["epoch_years"] == 0.0

    # Candidates present and structured
    candidates = output["candidates"]
    assert len(candidates) == 1
    cand = candidates[0]
    assert "state" in cand
    assert "epoch_years" in cand
    assert "metadata" in cand

    # Uncertainty status represented correctly
    uncertainty = output["uncertainty"]
    assert "covariance_valid" in uncertainty
    assert "failure_reason" in uncertainty
    assert "degrees_of_freedom" in uncertainty

    # Diagnostics status represented correctly (not null)
    diagnostics = output["diagnostics"]
    assert diagnostics["status"] == "success"
    assert diagnostics["failure_reason"] is None
    assert diagnostics["data"] is not None

    # No NaN or Infinity in serialized JSON (allow_nan=False already enforced)
    assert "NaN" not in captured.out
    assert "Infinity" not in captured.out

    mock_run_estimation.assert_called_once()
    mock_run_multi_start.assert_called_once()


@patch("orbit_discovery.cli.cmd_estimate.run_multi_start_estimation")
@patch("orbit_discovery.cli.cmd_estimate.run_estimation")
def test_estimate_no_retained_candidates_returns_failure(
    mock_run_estimation,
    mock_run_multi_start,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Zero retained candidates → structured failure with best_fit and audit_log preserved."""
    obs_file, _ = _write_valid_observation_csv(tmp_path)

    initial_state = {
        "rx": 1.0, "ry": 0.0, "rz": 0.0,
        "vx": 0.0, "vy": 2.0 * math.pi, "vz": 0.0,
    }
    state = OrbitState(**initial_state)

    mock_run_estimation.return_value = _make_estimation_result(state, converged=True)
    # Multi-start returns empty candidate list
    empty_result = EstimationResult(
        candidates=[],
        best_fit=mock_run_estimation.return_value.best_fit,
        source_dataset_metadata={},
    )
    mock_run_multi_start.return_value = (empty_result, [{"start_index": 0, "outcome": "rejected"}])

    config_path = _write_estimate_config(tmp_path, obs_file, initial_state)

    exit_code = main(["estimate", "--config", str(config_path)])
    captured = capsys.readouterr()

    assert exit_code == 1, captured.err

    output = json.loads(captured.out)
    assert output["status"] == "failed"
    assert output["failure"] == "no_retained_candidates"
    assert "best_fit" in output
    assert "audit_log" in output

    # No NaN or Infinity in serialized JSON
    assert "NaN" not in captured.out
    assert "Infinity" not in captured.out


@patch("orbit_discovery.cli.cmd_estimate.run_multi_start_estimation")
@patch("orbit_discovery.cli.cmd_estimate.run_estimation")
@patch("orbit_discovery.cli.cmd_estimate._print_json", return_value=2)
def test_estimate_zero_retained_candidates_serialization_failure(
    mock_print_json,
    mock_run_estimation,
    mock_run_multi_start,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Zero retained candidates with serialization failure → exit code 2."""
    obs_file, _ = _write_valid_observation_csv(tmp_path)

    initial_state = {
        "rx": 1.0, "ry": 0.0, "rz": 0.0,
        "vx": 0.0, "vy": 2.0 * math.pi, "vz": 0.0,
    }
    state = OrbitState(**initial_state)

    mock_run_estimation.return_value = _make_estimation_result(state, converged=True)
    empty_result = EstimationResult(
        candidates=[],
        best_fit=mock_run_estimation.return_value.best_fit,
        source_dataset_metadata={},
    )
    mock_run_multi_start.return_value = (empty_result, [{"start_index": 0, "outcome": "rejected"}])

    config_path = _write_estimate_config(tmp_path, obs_file, initial_state)

    exit_code = main(["estimate", "--config", str(config_path)])
    captured = capsys.readouterr()

    assert exit_code == 2, captured.err
    mock_print_json.assert_called_once()


@patch("orbit_discovery.cli.cmd_estimate.run_multi_start_estimation")
@patch("orbit_discovery.cli.cmd_estimate.run_estimation")
def test_estimate_candidate_generation_exception_returns_failure(
    mock_run_estimation,
    mock_run_multi_start,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Candidate-generation exception → structured failure with best_fit preserved, distinct from no_retained_candidates."""
    obs_file, _ = _write_valid_observation_csv(tmp_path)

    initial_state = {
        "rx": 1.0, "ry": 0.0, "rz": 0.0,
        "vx": 0.0, "vy": 2.0 * math.pi, "vz": 0.0,
    }
    state = OrbitState(**initial_state)

    mock_run_estimation.return_value = _make_estimation_result(state, converged=True)
    mock_run_multi_start.side_effect = RuntimeError("optimizer blew up")

    config_path = _write_estimate_config(tmp_path, obs_file, initial_state)

    exit_code = main(["estimate", "--config", str(config_path)])
    captured = capsys.readouterr()

    assert exit_code == 1, captured.err

    output = json.loads(captured.out)
    assert output["status"] == "failed"
    assert output["failure"] == "candidate_generation_failed"
    assert "optimizer blew up" in output["failure_reason"]
    assert "best_fit" in output
    assert best_fit_preserved(output)

    # No NaN or Infinity in serialized JSON
    assert "NaN" not in captured.out
    assert "Infinity" not in captured.out


def best_fit_preserved(output: dict) -> bool:
    """Check that best_fit contains state, epoch_years, and fit_metrics."""
    best_fit = output.get("best_fit", {})
    return all(key in best_fit for key in ("state", "epoch_years", "fit_metrics"))


@patch("orbit_discovery.cli.cmd_estimate.run_multi_start_estimation")
@patch("orbit_discovery.cli.cmd_estimate.run_estimation")
def test_estimate_diagnostics_failure_preserves_reason(
    mock_run_estimation,
    mock_run_multi_start,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Diagnostics failure → status preserved with explicit failure_reason, not null."""
    obs_file, _ = _write_valid_observation_csv(tmp_path)

    initial_state = {
        "rx": 1.0, "ry": 0.0, "rz": 0.0,
        "vx": 0.0, "vy": 2.0 * math.pi, "vz": 0.0,
    }
    state = OrbitState(**initial_state)

    mock_run_estimation.return_value = _make_estimation_result(state, converged=True)
    mock_run_multi_start.return_value = (
        _make_estimation_result(state, converged=True),
        [{"start_index": 0, "outcome": "retained"}],
    )

    # Force diagnostics to fail by making compute_candidate_diagnostics raise
    with patch(
        "orbit_discovery.cli.cmd_estimate.compute_candidate_diagnostics",
        side_effect=ValueError("candidate state invalid"),
    ):
        config_path = _write_estimate_config(tmp_path, obs_file, initial_state)
        exit_code = main(["estimate", "--config", str(config_path)])
        captured = capsys.readouterr()

    assert exit_code == 0, captured.err
    output = json.loads(captured.out)

    diagnostics = output["diagnostics"]
    assert diagnostics["status"] == "failed"
    assert diagnostics["failure_reason"] == "candidate state invalid"
    assert diagnostics["data"] is None

    # No NaN or Infinity in serialized JSON
    assert "NaN" not in captured.out
    assert "Infinity" not in captured.out
