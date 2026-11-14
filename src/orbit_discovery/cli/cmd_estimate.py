"""``orbit estimate`` — Component 3 orbit estimation and candidate discovery.

Integrates the complete Component 3 pipeline:

    load observations
        -> initial estimate / best-fit estimation (Phase 3)
        -> multi-start candidate generation and ranking (Phase 4)
        -> local uncertainty diagnostics (Phase 5B)
        -> candidate ensemble spread / clustering diagnostics (Phase 5C)
        -> structured JSON output (Phase 6)

The command never accesses ground truth and never fabricates results: every
failure case (invalid observations, failed best-fit, no retained candidates,
invalid uncertainty, serialization failure) is reported explicitly with an
appropriate exit code.
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np

from orbit_discovery.core.paths import (
    ProjectRootNotFoundError,
    resolve_config_path,
    resolve_project_root,
)

from orbit_discovery.component3.loader import load_dataset_for_estimation
from orbit_discovery.component3.estimation import (
    build_residual_function,
    run_estimation,
)
from orbit_discovery.component3.models import OrbitState
from orbit_discovery.component3.candidates import (
    run_multi_start_estimation,
)
from orbit_discovery.component3.uncertainty import compute_uncertainty
from orbit_discovery.component3.candidate_diagnostics import (
    compute_candidate_diagnostics,
)
from orbit_discovery.component3.observation_model import (
    reconstruct_observer_config,
    get_obliquity_deg,
)

#: Scale factors for the scaled parameter space s = [1, 1, 1, 2pi, 2pi, 2pi].
_STATE_SCALES: np.ndarray = np.array(
    [1.0, 1.0, 1.0, 2.0 * np.pi, 2.0 * np.pi, 2.0 * np.pi], dtype=float
)

#: Default number of optimizer iterations when not overridden by config.
_DEFAULT_MAX_ITER = 100


def _state_from_mapping(mapping: dict) -> OrbitState:
    """Build an ``OrbitState`` from a mapping with keys ``rx``..``vz``."""
    return OrbitState(
        rx=float(mapping["rx"]),
        ry=float(mapping["ry"]),
        rz=float(mapping["rz"]),
        vx=float(mapping["vx"]),
        vy=float(mapping["vy"]),
        vz=float(mapping["vz"]),
    )


def _compute_jac_scaled(residual_fn, x: np.ndarray, s: np.ndarray) -> np.ndarray:
    """Compute the scaled Jacobian ``J_scaled = J_phys @ diag(s)``.

    Uses forward differences in scaled parameter space, matching the
    convention used by ``least_squares_lm`` in the optimizer.
    """
    eps = np.finfo(float).eps
    n = x.shape[0]
    r = np.asarray(residual_fn(x), dtype=float)
    m = r.shape[0]
    jac_scaled = np.zeros((m, n), dtype=float)
    u = x / s
    for k in range(n):
        h = math.sqrt(eps) * max(abs(u[k]), 1.0)
        u_plus = u.copy()
        u_plus[k] += h
        r_plus = np.asarray(residual_fn(u_plus * s), dtype=float)
        jac_scaled[:, k] = (r_plus - r) / h
    return jac_scaled


def _serialize_value(value):
    """Convert a value to a JSON-native Python value.

    NumPy scalars become native floats/ints; NumPy arrays become lists;
    non-finite or unavailable values become ``None``.
    """
    if value is None:
        return None
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        v = float(value)
        return v if np.isfinite(v) else None
    if isinstance(value, float):
        return value if np.isfinite(value) else None
    if isinstance(value, int):
        return value
    if isinstance(value, np.ndarray):
        return _serialize_value(value.tolist())
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    if isinstance(value, tuple):
        return [_serialize_value(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _serialize_value(item) for key, item in value.items()
        }
    if isinstance(value, str):
        return value
    return str(value)


def _build_failure_output(status: str, failure: str, reason: str,
                          configuration: dict) -> dict:
    """Build a failure output dict that is always JSON-serializable."""
    return {
        "command": "estimate",
        "status": status,
        "failure": failure,
        "failure_reason": reason,
        "configuration": configuration,
        "caveats": [
            "Descriptive statistics only; not a calibrated statistical confidence region."
        ],
    }


def _print_json(output: dict) -> int:
    """Serialize ``output`` to JSON with ``allow_nan=False`` and print it.

    Returns 0 on success, 2 on serialization failure.
    """
    try:
        print(json.dumps(output, indent=2, allow_nan=False))
    except (ValueError, TypeError) as exc:
        print(
            f"Error: Serialization failure: {exc}",
            file=sys.stderr,
        )
        return 2
    return 0


def cmd(args: list[str] | None = None) -> int:
    """Handle the ``orbit estimate`` subcommand.

    Args:
        args: Remaining command-line arguments after ``orbit estimate``.

    Returns:
        Exit code (0 = success, 1 = pipeline failure, 2 = runtime/serialization error).
    """
    if args is None:
        args = sys.argv[1:]

    # ── Help ──
    if "--help" in args or "-h" in args or args == []:
        print("orbit estimate -- Component 3 orbit estimation and candidate discovery")
        print()
        print("Usage: orbit estimate [--config CONFIG] [--observations CSV] [--project-root DIR]")
        print("       orbit estimate --help          This help message")
        print("       orbit estimate --version       Show version")
        print()
        print("Options:")
        print("  --config CONFIG          Path to estimation JSON config")
        print("  --observations CSV       Path to observations CSV (overrides config)")
        print("  --project-root DIR       Explicit project root directory")
        print("  --help, -h               Show this help message and exit")
        print("  --version, -V            Show program version and exit")
        print()
        print("Runs the Component 3 pipeline: load observations, best-fit estimation,")
        print("multi-start candidate generation, local uncertainty diagnostics, and")
        print("candidate ensemble diagnostics, emitting a structured JSON result.")
        print("Exit codes: 0 = success, 1 = pipeline failure, 2 = runtime error.")
        return 0

    # ── Version ──
    if "--version" in args or "-V" in args:
        print("orbit CLI prototype v0.2.0")
        return 0

    # ── Parse arguments ──
    config_arg: str | None = None
    project_root_arg: str | None = None
    observations_arg: str | None = None

    i = 0
    while i < len(args):
        if args[i] == "--config" and i + 1 < len(args):
            config_arg = args[i + 1]
            i += 2
        elif args[i] == "--observations" and i + 1 < len(args):
            observations_arg = args[i + 1]
            i += 2
        elif args[i] == "--project-root" and i + 1 < len(args):
            project_root_arg = args[i + 1]
            i += 2
        else:
            i += 1

    # ── Resolve project root ──
    try:
        project_root = (
            resolve_project_root(project_root_arg)
            if project_root_arg is not None
            else resolve_project_root()
        )
    except ProjectRootNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    # ── Resolve config path ──
    resolved_config_path: str | Path | None = None
    if config_arg is not None:
        try:
            resolved_config_path = resolve_config_path(config_arg, project_root)
        except (ProjectRootNotFoundError, FileNotFoundError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

    # ── Load config ──
    config: dict = {}
    if resolved_config_path is not None:
        try:
            config = json.loads(
                Path(resolved_config_path).read_text(encoding="utf-8")
            )
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            print(f"Error: Failed to load configuration: {exc}", file=sys.stderr)
            return 1

    if not isinstance(config, dict):
        print(
            "Error: Configuration must be a JSON object.",
            file=sys.stderr,
        )
        return 1

    # ── Determine observations path ──
    observations_path = observations_arg or config.get("observations")
    if not observations_path:
        print(
            "Error: No observations path specified. Use --observations or the "
            "config 'observations' field.",
            file=sys.stderr,
        )
        return 1

    try:
        resolved_obs_path = resolve_config_path(observations_path, project_root)
    except (ProjectRootNotFoundError, FileNotFoundError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    # ── Load dataset ──
    try:
        dataset = load_dataset_for_estimation(resolved_obs_path)
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"Error: Invalid observations: {exc}", file=sys.stderr)
        return 1

    # ── Build initial state ──
    initial_state_cfg = config.get("initial_state")
    if not initial_state_cfg:
        print(
            "Error: Config missing 'initial_state'.",
            file=sys.stderr,
        )
        return 1
    try:
        initial_state = _state_from_mapping(initial_state_cfg)
    except (KeyError, TypeError, ValueError) as exc:
        print(f"Error: Invalid initial_state: {exc}", file=sys.stderr)
        return 1

    # ── Reconstruct observer config and obliquity from metadata ──
    try:
        observer_config = reconstruct_observer_config(dataset.metadata)
    except ValueError:
        observer_config = None
    obliquity_deg = get_obliquity_deg(dataset.metadata)

    # ── Bodies ──
    bodies = config.get("bodies", ["Sun"])
    if not isinstance(bodies, list) or not bodies:
        bodies = ["Sun"]

    # ── Phase 4 candidate configuration ──
    phase4_config = config.get("phase_4_candidates", None)

    # ── Serialized configuration for output ──
    output_configuration = _serialize_value({
        "observations": str(resolved_obs_path),
        "initial_state": initial_state.to_dict(),
        "bodies": list(bodies),
        "phase_4_candidates": phase4_config,
        "max_iter": _DEFAULT_MAX_ITER,
    })

    # ── Step 1: best-fit estimation ──
    try:
        phase3_result = run_estimation(
            dataset=dataset,
            initial_state=initial_state,
            observer_config=observer_config,
            obliquity_deg=obliquity_deg,
            bodies=bodies,
        )
    except ValueError as exc:
        failure_output = _build_failure_output(
            "failed", "best_fit_failed", str(exc), output_configuration
        )
        serialization_exit_code = _print_json(failure_output)
        return serialization_exit_code if serialization_exit_code != 0 else 1
    except Exception as exc:  # noqa: BLE001 — report any unexpected failure
        failure_output = _build_failure_output(
            "failed",
            "best_fit_failed",
            f"Unexpected error: {exc}",
            output_configuration,
        )
        serialization_exit_code = _print_json(failure_output)
        return serialization_exit_code if serialization_exit_code != 0 else 1

    best_state = phase3_result.best_fit.state
    best_fit_metrics = phase3_result.best_fit.fit_metrics
    converged = bool(
        phase3_result.candidates[0].metadata.get("converged", False)
    ) if phase3_result.candidates else False
    n_valid = int(best_fit_metrics.get("n_valid_scalar_residuals", 0))

    # ── Step 2: local uncertainty diagnostics ──
    uncertainty_result = None
    try:
        jac_scaled = _compute_jac_scaled(
            build_residual_function(
                dataset, observer_config, obliquity_deg, bodies
            ),
            best_state.to_array(),
            _STATE_SCALES,
        )
        uncertainty_result = compute_uncertainty(
            jac_scaled, n_valid, converged=converged
        )
    except Exception:  # noqa: BLE001 — uncertainty failure is not fatal
        uncertainty_result = None

    # ── Step 3: multi-start candidate generation ──
    try:
        estimation_result, audit_log = run_multi_start_estimation(
            phase3_result=phase3_result,
            dataset=dataset,
            config=phase4_config,
            bodies=bodies,
            observer_config=observer_config,
            obliquity_deg=obliquity_deg,
        )
    except Exception as exc:  # noqa: BLE001 — report candidate generation failure
        failure_output = _build_failure_output(
            "failed",
            "candidate_generation_failed",
            str(exc),
            output_configuration,
        )
        failure_output["best_fit"] = {
            "state": _serialize_value(best_state.to_dict()),
            "epoch_years": float(phase3_result.best_fit.epoch_years),
            "fit_metrics": _serialize_value(best_fit_metrics),
        }
        serialization_exit_code = _print_json(failure_output)
        return serialization_exit_code if serialization_exit_code != 0 else 1

    # ── Guard: zero retained candidates ──
    retained_candidates = estimation_result.candidates
    if not retained_candidates:
        failure_output = _build_failure_output(
            "failed",
            "no_retained_candidates",
            "Multi-start estimation produced no retained candidates; "
            "cannot produce candidate diagnostics.",
            output_configuration,
        )
        failure_output["best_fit"] = {
            "state": _serialize_value(best_state.to_dict()),
            "epoch_years": float(phase3_result.best_fit.epoch_years),
            "fit_metrics": _serialize_value(best_fit_metrics),
        }
        failure_output["audit_log"] = _serialize_value(audit_log)
        serialization_exit_code = _print_json(failure_output)
        return serialization_exit_code if serialization_exit_code != 0 else 1

    # ── Step 4: candidate ensemble diagnostics ──
    diagnostics_output = None
    diagnostics_status = "success"
    diagnostics_failure_reason = None
    try:
        diagnostics = compute_candidate_diagnostics(retained_candidates)
        diagnostics_output = _serialize_value(asdict(diagnostics))
    except Exception as exc:  # noqa: BLE001 — preserve failure info
        diagnostics_status = "failed"
        diagnostics_failure_reason = str(exc)

    # ── Step 5: assemble structured output ──
    retained_candidate_list = []
    for cand in retained_candidates:
        retained_candidate_list.append({
            "state": _serialize_value(cand.state.to_dict()),
            "epoch_years": float(cand.epoch_years),
            "metadata": _serialize_value(cand.metadata),
        })

    output = {
        "command": "estimate",
        "status": "success",
        "configuration": output_configuration,
        "best_fit": {
            "state": _serialize_value(best_state.to_dict()),
            "epoch_years": float(phase3_result.best_fit.epoch_years),
            "fit_metrics": _serialize_value(best_fit_metrics),
        },
        "uncertainty": _serialize_value(
            uncertainty_result.to_dict() if uncertainty_result is not None else {
                "covariance": None,
                "covariance_valid": False,
                "failure_reason": "uncertainty_computation_failed",
                "singular_values": [],
                "condition_number": None,
                "rank": 0,
                "rank_tolerance": 0.0,
                "degrees_of_freedom": 0,
                "caveats": ["Uncertainty could not be computed."],
            }
        ),
        "candidates": retained_candidate_list,
        "audit_log": _serialize_value(audit_log),
        "diagnostics": {
            "status": diagnostics_status,
            "failure_reason": diagnostics_failure_reason,
            "data": diagnostics_output,
        },
        "caveats": [
            "Descriptive statistics only; not a calibrated statistical confidence region."
        ],
    }

    return _print_json(output)
