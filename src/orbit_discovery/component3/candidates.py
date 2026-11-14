"""Component 3 Phase 4: Reproducible Multi-Start Fitting and Candidate Selection.

This module implements reproducible multi-start candidate generation around an
existing Phase 3D best-fit orbit.  It does not modify the estimator, optimizer,
dynamics, residuals, observation model, or data models; it reuses those
interfaces to generate, validate, rank, deduplicate, and retain candidate
orbits.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from orbit_discovery.component3.models import (
    OrbitCandidate,
    OrbitState,
    ObservationDataset,
    EstimationResult,
    BestFitResult,
)
from orbit_discovery.component3.estimation import run_estimation

#: Default configuration applied when the phase_4_candidates section is absent.
DEFAULT_CONFIG: Dict[str, Any] = {
    "num_starts": 100,
    "random_seed": 42,
    "position_perturbation_scales": [0.01, 0.01, 0.01],
    "velocity_perturbation_scales": [1e-4, 1e-4, 1e-4],
    "duplicate_tolerance_pos": 0.005,
    "duplicate_tolerance_vel": 5e-5,
    "fit_quality_threshold_reduced_chi2": 5.0,
    "max_retained_candidates": 10,
}

#: Numerical exceptions expected during propagation/prediction/estimation.
_NUMERICAL_EXCEPTIONS = (
    ValueError,
    RuntimeError,
    FloatingPointError,
    ArithmeticError,
    OverflowError,
)


class ConfigurationError(ValueError):
    """Raised when Phase 4 configuration is invalid."""


def _reject_boolean(value: Any, field_name: str, expected_type: str) -> None:
    """Reject booleans where integers or numeric values are expected."""
    if isinstance(value, bool):
        raise ConfigurationError(
            f"Configuration field '{field_name}' must be {expected_type}; "
            "got bool."
        )


def validate_config(config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Validate Phase 4 configuration strictly.

    Returns the merged configuration dictionary with defaults applied for any
    missing keys.  Raises :class:`ConfigurationError` for invalid input.
    """
    if config is None:
        return dict(DEFAULT_CONFIG)

    if not isinstance(config, dict):
        raise ConfigurationError(
            f"Configuration must be a dict, got {type(config).__name__}."
        )

    merged: Dict[str, Any] = dict(DEFAULT_CONFIG)

    for key, value in config.items():
        if key not in DEFAULT_CONFIG:
            raise ConfigurationError(
                f"Unknown configuration key: {key}."
            )

    # num_starts
    num_starts = config.get("num_starts", DEFAULT_CONFIG["num_starts"])
    _reject_boolean(num_starts, "num_starts", "a positive integer")
    if not isinstance(num_starts, int) or isinstance(num_starts, bool):
        raise ConfigurationError(
            "Configuration field 'num_starts' must be a positive integer."
        )
    if num_starts < 1:
        raise ConfigurationError(
            "Configuration field 'num_starts' must be >= 1."
        )
    merged["num_starts"] = num_starts

    # random_seed
    random_seed = config.get("random_seed", DEFAULT_CONFIG["random_seed"])
    _reject_boolean(random_seed, "random_seed", "a non-negative integer")
    if not isinstance(random_seed, int) or isinstance(random_seed, bool):
        raise ConfigurationError(
            "Configuration field 'random_seed' must be a non-negative integer."
        )
    if random_seed < 0:
        raise ConfigurationError(
            "Configuration field 'random_seed' must be >= 0."
        )
    merged["random_seed"] = random_seed

    # max_retained_candidates
    max_retained = config.get("max_retained_candidates", DEFAULT_CONFIG["max_retained_candidates"])
    _reject_boolean(max_retained, "max_retained_candidates", "a positive integer")
    if not isinstance(max_retained, int) or isinstance(max_retained, bool):
        raise ConfigurationError(
            "Configuration field 'max_retained_candidates' must be a positive integer."
        )
    if max_retained < 1:
        raise ConfigurationError(
            "Configuration field 'max_retained_candidates' must be >= 1."
        )
    merged["max_retained_candidates"] = max_retained

    # Perturbation scale arrays
    for field in ("position_perturbation_scales", "velocity_perturbation_scales"):
        scales = config.get(field, DEFAULT_CONFIG[field])
        if not isinstance(scales, list):
            raise ConfigurationError(
                f"Configuration field '{field}' must be a list of three values."
            )
        if len(scales) != 3:
            raise ConfigurationError(
                f"Configuration field '{field}' must contain exactly three values."
            )
        validated = []
        for i, scale in enumerate(scales):
            _reject_boolean(scale, f"{field}[{i}]", "a finite positive number")
            if not isinstance(scale, (int, float)):
                raise ConfigurationError(
                    f"Configuration field '{field}[{i}]' must be a finite positive number."
                )
            scale_f = float(scale)
            if not np.isfinite(scale_f) or scale_f <= 0:
                raise ConfigurationError(
                    f"Configuration field '{field}[{i}]' must be finite and positive."
                )
            validated.append(scale_f)
        merged[field] = validated

    # Duplicate tolerances and fit quality threshold
    for field in ("duplicate_tolerance_pos", "duplicate_tolerance_vel", "fit_quality_threshold_reduced_chi2"):
        value = config.get(field, DEFAULT_CONFIG[field])
        _reject_boolean(value, field, "a finite positive number")
        if not isinstance(value, (int, float)):
            raise ConfigurationError(
                f"Configuration field '{field}' must be a finite positive number."
            )
        value_f = float(value)
        if not np.isfinite(value_f) or value_f <= 0:
            raise ConfigurationError(
                f"Configuration field '{field}' must be finite and positive."
            )
        merged[field] = value_f

    return merged


def _initial_states_from_config(
    baseline_state: OrbitState,
    num_starts: int,
    random_seed: int,
    position_scales: List[float],
    velocity_scales: List[float],
) -> List[Tuple[int, OrbitState]]:
    """Generate the initial states for all starts.

    Start 0 is the baseline state itself (not regenerated).  Starts 1..K-1 are
    independent Gaussian perturbations of the baseline state.
    """
    rng = np.random.default_rng(random_seed)

    states: List[Tuple[int, OrbitState]] = [(0, baseline_state)]

    scales = np.array(position_scales + velocity_scales, dtype=float)
    for k in range(1, num_starts):
        perturbation = rng.normal(loc=0.0, scale=scales, size=6)
        x0 = baseline_state.to_array()
        perturbed = x0 + perturbation
        states.append((k, OrbitState(
            rx=float(perturbed[0]), ry=float(perturbed[1]), rz=float(perturbed[2]),
            vx=float(perturbed[3]), vy=float(perturbed[4]), vz=float(perturbed[5]),
        )))

    return states


def _serialize_metric(value: Any) -> Any:
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
        return _serialize_metric(value.tolist())
    if isinstance(value, list):
        return [_serialize_metric(item) for item in value]
    if isinstance(value, tuple):
        return [_serialize_metric(item) for item in value]
    if isinstance(value, dict):
        return {
            _serialize_metric_key(key): _serialize_metric(item)
            for key, item in value.items()
        }
    if isinstance(value, str):
        return value
    return str(value)


def _serialize_metric_key(key: Any) -> Any:
    """Convert a dictionary key to a JSON-compatible scalar."""
    if isinstance(key, str):
        return key
    if isinstance(key, (bool, np.bool_)):
        return bool(key)
    if isinstance(key, np.integer):
        return int(key)
    if isinstance(key, np.floating):
        value = float(key)
        return value if np.isfinite(value) else None
    if isinstance(key, float):
        return key if np.isfinite(key) else None
    if isinstance(key, int):
        return key
    return str(key)


def _audit_record(
    start_index: int,
    initial_state: Optional[OrbitState],
    outcome: str,
    reason: Optional[str],
    convergence_status: Optional[bool] = None,
    valid: Optional[bool] = None,
    fit_metrics: Optional[Dict[str, Any]] = None,
    duplicate_of: Optional[int] = None,
) -> Dict[str, Any]:
    """Build a single audit record."""
    if initial_state is None:
        initial_state_serialized: Optional[List[float]] = None
    else:
        initial_state_serialized = [
            _serialize_metric(initial_state.rx),
            _serialize_metric(initial_state.ry),
            _serialize_metric(initial_state.rz),
            _serialize_metric(initial_state.vx),
            _serialize_metric(initial_state.vy),
            _serialize_metric(initial_state.vz),
        ]
    return {
        "start_index": int(start_index),
        "initial_state": initial_state_serialized,
        "outcome": outcome,
        "convergence_status": convergence_status,
        "valid": valid,
        "fit_metrics": _serialize_metric(fit_metrics) if fit_metrics is not None else None,
        "reason": reason,
        "duplicate_of": None if duplicate_of is None else int(duplicate_of),
    }


def _validate_candidate_fit(
    state: OrbitState,
    converged: Optional[bool],
    chi2: Optional[float],
    optimality: Optional[float],
    jacobian_rank: Optional[int],
    n_valid_scalar_residuals: Optional[int],
    dof: Optional[int],
    reduced_chi2: Optional[float],
    config: Dict[str, Any],
) -> Tuple[bool, Optional[str]]:
    """Validate a returned fit against Phase 4 scientific criteria.

    Returns ``(is_valid, reason)`` where ``reason`` is the rejection reason
    when invalid, else ``None``.
    """
    # State finiteness
    if not np.all(np.isfinite(state.to_array())):
        return False, "non_finite_state"

    # Chi-square
    if chi2 is None or not isinstance(chi2, (int, float)) or isinstance(chi2, bool):
        return False, "invalid_fit_metrics"
    if not np.isfinite(float(chi2)) or float(chi2) < 0:
        return False, "invalid_fit_metrics"

    # Optimality
    if optimality is None or not isinstance(optimality, (int, float)) or isinstance(optimality, bool):
        return False, "invalid_fit_metrics"
    if not np.isfinite(float(optimality)) or float(optimality) < 0:
        return False, "invalid_fit_metrics"

    # Convergence boolean (booleans are not integers)
    if converged is None or not isinstance(converged, bool):
        return False, "non_converged"
    if not converged:
        return False, "non_converged"

    # Residual count: positive integer, not boolean
    if n_valid_scalar_residuals is None:
        return False, "invalid_fit_metrics"
    if isinstance(n_valid_scalar_residuals, bool) or not isinstance(n_valid_scalar_residuals, int):
        return False, "invalid_fit_metrics"
    if n_valid_scalar_residuals <= 0:
        return False, "invalid_fit_metrics"

    # Jacobian rank
    if jacobian_rank is None:
        return False, "invalid_jacobian"
    if isinstance(jacobian_rank, bool) or not isinstance(jacobian_rank, int):
        return False, "invalid_jacobian"

    # Rank must be exactly six (a 6-dimensional Cartesian state)
    if jacobian_rank > 6:
        return False, "invalid_jacobian"
    if jacobian_rank < 6:
        return False, "rank_deficient"

    # DOF
    if dof is None:
        return False, "insufficient_degrees_of_freedom"
    if isinstance(dof, bool) or not isinstance(dof, int):
        return False, "insufficient_degrees_of_freedom"
    if dof <= 0:
        return False, "insufficient_degrees_of_freedom"

    # Reduced chi-square threshold (strict inequality)
    if reduced_chi2 is None:
        return False, "invalid_fit_metrics"
    if isinstance(reduced_chi2, bool) or not isinstance(reduced_chi2, (int, float)):
        return False, "invalid_fit_metrics"
    reduced_chi2_f = float(reduced_chi2)
    if not np.isfinite(reduced_chi2_f):
        return False, "invalid_fit_metrics"
    threshold = config["fit_quality_threshold_reduced_chi2"]
    if not (reduced_chi2_f < threshold):
        return False, "high_reduced_chi2"

    return True, None


def _compute_duplicate_distance(
    state_a: OrbitState,
    state_b: OrbitState,
    tol_pos: float,
    tol_vel: float,
) -> float:
    """Compute normalized state-space distance D_ij."""
    r_a = np.array([state_a.rx, state_a.ry, state_a.rz], dtype=float)
    r_b = np.array([state_b.rx, state_b.ry, state_b.rz], dtype=float)
    v_a = np.array([state_a.vx, state_a.vy, state_a.vz], dtype=float)
    v_b = np.array([state_b.vx, state_b.vy, state_b.vz], dtype=float)

    dr_sq = float(np.sum((r_a - r_b) ** 2)) / (tol_pos ** 2)
    dv_sq = float(np.sum((v_a - v_b) ** 2)) / (tol_vel ** 2)
    return float(np.sqrt(dr_sq + dv_sq))


def _extract_fit_metrics(
    candidate: OrbitCandidate,
    converged: Optional[bool],
    jacobian_rank: Optional[int],
    n_valid_scalar_residuals: Optional[int],
    chi2: Optional[float],
    optimality: Optional[float],
    dof: Optional[int],
    reduced_chi2: Optional[float],
) -> Dict[str, Any]:
    """Assemble fit metrics dict for an audit record."""
    return {
        "chi2": chi2,
        "chi2_reduced": reduced_chi2,
        "jacobian_rank": jacobian_rank,
        "n_valid_scalar_residuals": n_valid_scalar_residuals,
        "degrees_of_freedom": dof,
    }


def run_multi_start_estimation(
    phase3_result: EstimationResult,
    dataset: ObservationDataset,
    config: Optional[Dict[str, Any]] = None,
    bodies: Optional[List[str]] = None,
    observer_config: Optional[Any] = None,
    obliquity_deg: float = 23.43928,
) -> Tuple[EstimationResult, List[Dict[str, Any]]]:
    """Run reproducible multi-start candidate generation.

    Parameters
    ----------
    phase3_result : EstimationResult
        Existing Phase 3D estimation result whose best-fit state is used as
        Start 0 baseline (not re-optimized).
    dataset : ObservationDataset
        Observation dataset used for fitting.
    config : dict, optional
        Phase 4 configuration under ``phase_4_candidates``.  Defaults are
        applied for any missing keys.
    bodies : list of str, optional
        Gravitational bodies passed to ``run_estimation``.
    observer_config : optional
        Observer configuration passed to ``run_estimation``.
    obliquity_deg : float
        Ecliptic obliquity passed to ``run_estimation``.

    Returns
    -------
    estimation_result : EstimationResult
        Result preserving the original Phase 3D ``best_fit`` for provenance,
        with ``candidates`` containing the retained Phase 4 candidates in
        deterministic ranking order.
    audit_log : list of dict
        Exactly one record per attempted start, ordered by start index.
    """
    merged_config = validate_config(config)
    num_starts = merged_config["num_starts"]
    random_seed = merged_config["random_seed"]
    max_retained = merged_config["max_retained_candidates"]
    threshold = merged_config["fit_quality_threshold_reduced_chi2"]

    # --- Baseline (Start 0) ---
    has_baseline_candidate = bool(phase3_result.candidates)
    baseline_candidate = (
        phase3_result.candidates[0] if has_baseline_candidate else None
    )
    baseline_best_fit = phase3_result.best_fit

    audit_log: List[Dict[str, Any]] = []
    eligible: List[Dict[str, Any]] = []  # validated candidates for ranking

    baseline_state: Optional[OrbitState] = None
    baseline_epoch: Optional[float] = None
    baseline_valid = False
    baseline_valid_reason: Optional[str] = None

    if has_baseline_candidate and (
        not isinstance(baseline_candidate, OrbitCandidate)
        or not isinstance(baseline_candidate.metadata, dict)
    ):
        baseline_valid_reason = "invalid_baseline_candidate"
        baseline_candidate = None

    if baseline_best_fit is None:
        if baseline_valid_reason is None:
            baseline_valid_reason = "missing_baseline_metrics"
    elif not isinstance(baseline_best_fit, BestFitResult):
        if baseline_valid_reason is None:
            baseline_valid_reason = "missing_baseline_metrics"
    else:
        if isinstance(baseline_best_fit.state, OrbitState):
            baseline_state = baseline_best_fit.state
        else:
            baseline_state = None
        baseline_epoch = baseline_best_fit.epoch_years

        if baseline_state is None:
            if baseline_valid_reason is None:
                baseline_valid_reason = "missing_baseline_metrics"
        elif not np.all(np.isfinite(baseline_state.to_array())):
            if baseline_valid_reason is None:
                baseline_valid_reason = "non_finite_state"
        elif (
            baseline_epoch is None
            or isinstance(baseline_epoch, bool)
            or not isinstance(baseline_epoch, (int, float))
            or not np.isfinite(float(baseline_epoch))
            or float(baseline_epoch) != 0.0
        ):
            baseline_valid_reason = "missing_baseline_metrics"
        else:
            # Scientific validation is performed below once metrics are extracted.
            pass

    # Extract baseline metrics (safe when best_fit is missing)
    baseline_fit_metrics_raw = (
        baseline_best_fit.fit_metrics
        if isinstance(baseline_best_fit, BestFitResult)
        else None
    )
    if isinstance(baseline_fit_metrics_raw, dict):
        baseline_metrics: Dict[str, Any] = baseline_fit_metrics_raw
    else:
        baseline_metrics = {}
        if baseline_valid_reason is None:
            baseline_valid_reason = "invalid_fit_metrics"

    baseline_chi2 = baseline_metrics.get("chi2")
    baseline_optimality = baseline_metrics.get("optimality")
    baseline_jacobian_rank = baseline_metrics.get("jacobian_rank")
    baseline_n_valid = baseline_metrics.get("n_valid_scalar_residuals")

    baseline_converged = None
    if baseline_candidate is not None:
        baseline_converged = baseline_candidate.metadata.get("converged")

    baseline_dof = None
    if baseline_jacobian_rank is not None and baseline_n_valid is not None:
        try:
            baseline_dof = int(baseline_n_valid) - int(baseline_jacobian_rank)
        except (TypeError, ValueError):
            baseline_dof = None

    baseline_reduced_chi2 = None
    if baseline_chi2 is not None and baseline_dof is not None and baseline_dof > 0:
        try:
            baseline_reduced_chi2 = float(baseline_chi2) / float(baseline_dof)
        except (TypeError, ValueError):
            baseline_reduced_chi2 = None

    # Validate baseline scientific criteria when state and metrics are available
    if baseline_valid_reason is None and baseline_state is not None:
        baseline_valid, baseline_valid_reason = _validate_candidate_fit(
            baseline_state,
            baseline_converged,
            baseline_chi2,
            baseline_optimality,
            baseline_jacobian_rank,
            baseline_n_valid,
            baseline_dof,
            baseline_reduced_chi2,
            merged_config,
        )

    # Baseline audit record (outcome finalized after all validation)
    baseline_fit_metrics = _extract_fit_metrics(
        baseline_candidate if baseline_candidate else None,
        baseline_converged,
        baseline_jacobian_rank,
        baseline_n_valid,
        baseline_chi2,
        baseline_optimality,
        baseline_dof,
        baseline_reduced_chi2,
    )

    # Build initial state safely for audit record — never fabricate a state.
    baseline_initial_state: Optional[OrbitState] = baseline_state

    audit_log.append(
        _audit_record(
            start_index=0,
            initial_state=baseline_initial_state,
            outcome="rejected" if not baseline_valid else "pending",
            reason=baseline_valid_reason,
            convergence_status=baseline_converged,
            valid=baseline_valid,
            fit_metrics=baseline_fit_metrics,
        )
    )

    if baseline_valid:
        eligible.append({
            "start_index": 0,
            "state": baseline_state,
            "chi2": float(baseline_chi2),
            "chi2_reduced": baseline_reduced_chi2,
            "fit_metrics": baseline_fit_metrics,
            "converged": baseline_converged,
        })

    # --- Perturbed starts 1..K-1 ---
    if baseline_state is not None:
        initial_states = _initial_states_from_config(
            baseline_state,
            num_starts,
            random_seed,
            merged_config["position_perturbation_scales"],
            merged_config["velocity_perturbation_scales"],
        )
    else:
        # No baseline state; cannot generate perturbed starts meaningfully.
        initial_states = []

    for k, state in initial_states:
        if k == 0:
            continue  # baseline handled above

        # Check non-finite initial state
        if not np.all(np.isfinite(state.to_array())):
            audit_log.append(
                _audit_record(
                    start_index=k,
                    initial_state=state,
                    outcome="failed",
                    reason="non_finite_initial_state",
                )
            )
            continue

        # Run estimation (non-baseline start)
        try:
            result = run_estimation(
                dataset=dataset,
                initial_state=state,
                observer_config=observer_config,
                obliquity_deg=obliquity_deg,
                bodies=bodies,
            )
        except _NUMERICAL_EXCEPTIONS as e:
            audit_log.append(
                _audit_record(
                    start_index=k,
                    initial_state=state,
                    outcome="failed",
                    reason="propagation_error",
                    convergence_status=None,
                    valid=None,
                    fit_metrics=None,
                )
            )
            continue

        # Validate the result envelope before accessing its fields.
        if not isinstance(result, EstimationResult):
            audit_log.append(
                _audit_record(
                    start_index=k,
                    initial_state=state,
                    outcome="rejected",
                    reason="invalid_fit_result",
                    convergence_status=None,
                    valid=False,
                    fit_metrics=None,
                )
            )
            continue

        # Extract metrics from returned fit
        best_fit = result.best_fit
        if best_fit is not None and not isinstance(best_fit, BestFitResult):
            audit_log.append(
                _audit_record(
                    start_index=k,
                    initial_state=state,
                    outcome="rejected",
                    reason="invalid_fit_result",
                    convergence_status=None,
                    valid=False,
                    fit_metrics=None,
                )
            )
            continue

        if best_fit is None or best_fit.state is None:
            audit_log.append(
                _audit_record(
                    start_index=k,
                    initial_state=state,
                    outcome="rejected",
                    reason=(
                        "missing_fit_state" if best_fit is not None
                        else "missing_fit_result"
                    ),
                    convergence_status=None,
                    valid=False,
                    fit_metrics=None,
                )
            )
            continue

        if not isinstance(best_fit.state, OrbitState):
            audit_log.append(
                _audit_record(
                    start_index=k,
                    initial_state=state,
                    outcome="rejected",
                    reason="invalid_fit_state",
                    convergence_status=None,
                    valid=False,
                    fit_metrics=None,
                )
            )
            continue

        fit_state = best_fit.state
        fit_metrics_dict = best_fit.fit_metrics
        if not isinstance(fit_metrics_dict, dict):
            audit_log.append(
                _audit_record(
                    start_index=k,
                    initial_state=state,
                    outcome="rejected",
                    reason="invalid_fit_metrics",
                    convergence_status=None,
                    valid=False,
                    fit_metrics=None,
                )
            )
            continue

        # A valid fit must include a candidate with dictionary metadata.
        candidates = result.candidates
        if (
            not isinstance(candidates, list)
            or not candidates
            or not isinstance(candidates[0], OrbitCandidate)
            or not isinstance(candidates[0].metadata, dict)
        ):
            audit_log.append(
                _audit_record(
                    start_index=k,
                    initial_state=state,
                    outcome="rejected",
                    reason="invalid_candidate",
                    convergence_status=None,
                    valid=False,
                    fit_metrics=None,
                )
            )
            continue

        fit_chi2 = fit_metrics_dict.get("chi2")
        fit_optimality = fit_metrics_dict.get("optimality")
        fit_jacobian_rank = fit_metrics_dict.get("jacobian_rank")
        fit_n_valid = fit_metrics_dict.get("n_valid_scalar_residuals")

        candidate = candidates[0]
        fit_converged = candidate.metadata.get("converged")

        fit_dof = None
        if fit_jacobian_rank is not None and fit_n_valid is not None:
            try:
                fit_dof = int(fit_n_valid) - int(fit_jacobian_rank)
            except (TypeError, ValueError):
                fit_dof = None

        fit_reduced_chi2 = None
        if fit_chi2 is not None and fit_dof is not None and fit_dof > 0:
            try:
                fit_reduced_chi2 = float(fit_chi2) / float(fit_dof)
            except (TypeError, ValueError):
                fit_reduced_chi2 = None

        fit_metrics_audit = _extract_fit_metrics(
            candidate,
            fit_converged,
            fit_jacobian_rank,
            fit_n_valid,
            fit_chi2,
            fit_optimality,
            fit_dof,
            fit_reduced_chi2,
        )

        # Validate scientific criteria
        fit_valid, fit_valid_reason = _validate_candidate_fit(
            fit_state,
            fit_converged,
            fit_chi2,
            fit_optimality,
            fit_jacobian_rank,
            fit_n_valid,
            fit_dof,
            fit_reduced_chi2,
            merged_config,
        )

        if not fit_valid:
            audit_log.append(
                _audit_record(
                    start_index=k,
                    initial_state=state,
                    outcome="rejected",
                    reason=fit_valid_reason,
                    convergence_status=fit_converged,
                    valid=False,
                    fit_metrics=fit_metrics_audit,
                )
            )
            continue

        # Add valid candidate to eligible list and a placeholder to audit log
        eligible.append({
            "start_index": k,
            "state": fit_state,
            "chi2": float(fit_chi2),
            "chi2_reduced": fit_reduced_chi2,
            "fit_metrics": fit_metrics_audit,
            "converged": fit_converged,
        })

        audit_log.append(
            _audit_record(
                start_index=k,
                initial_state=state,
                outcome="pending",
                reason=None,
                convergence_status=fit_converged,
                valid=True,
                fit_metrics=fit_metrics_audit,
            )
        )

    # --- Deterministic ranking ---
    eligible.sort(key=lambda c: (c["chi2_reduced"], c["chi2"], c["start_index"]))

    # --- Greedy deduplication ---
    retained: List[Dict[str, Any]] = []
    retained_states: List[OrbitState] = []
    retained_start_indices: List[int] = []
    duplicate_map: Dict[int, int] = {}  # start_index -> duplicate_of start_index

    for cand in eligible:
        is_duplicate = False
        dup_of = None
        for j, retained_state in enumerate(retained_states):
            dist = _compute_duplicate_distance(
                cand["state"], retained_state,
                merged_config["duplicate_tolerance_pos"],
                merged_config["duplicate_tolerance_vel"],
            )
            if dist < 1.0:
                is_duplicate = True
                dup_of = retained_start_indices[j]
                break

        if is_duplicate:
            duplicate_map[cand["start_index"]] = dup_of
        else:
            retained.append(cand)
            retained_states.append(cand["state"])
            retained_start_indices.append(cand["start_index"])

    # --- Retention limit ---
    truncated: List[Dict[str, Any]] = []
    if len(retained) > max_retained:
        truncated = retained[max_retained:]
        retained = retained[:max_retained]

    # --- Finalize audit outcomes ---
    # Update baseline outcome
    baseline_entry = audit_log[0]
    if 0 in duplicate_map:
        baseline_entry["outcome"] = "duplicate"
        baseline_entry["reason"] = "duplicate_candidate"
        baseline_entry["duplicate_of"] = duplicate_map[0]
    elif 0 in {c["start_index"] for c in truncated}:
        baseline_entry["outcome"] = "truncated"
        baseline_entry["reason"] = "max_retained_candidates"
        baseline_entry["duplicate_of"] = None
    elif 0 in {c["start_index"] for c in retained}:
        baseline_entry["outcome"] = "retained"
        baseline_entry["reason"] = None
        baseline_entry["duplicate_of"] = None
    # else baseline was failed or rejected already

    # Update outcomes for perturbed starts
    for k in range(1, num_starts):
        # Find existing audit record for this start index
        record = None
        for rec in audit_log:
            if rec["start_index"] == k:
                record = rec
                break

        if record is None:
            continue

        start_index = k
        if start_index in duplicate_map:
            record["outcome"] = "duplicate"
            record["reason"] = "duplicate_candidate"
            record["duplicate_of"] = duplicate_map[start_index]
        elif start_index in {c["start_index"] for c in truncated}:
            record["outcome"] = "truncated"
            record["reason"] = "max_retained_candidates"
            record["duplicate_of"] = None
        elif start_index in {c["start_index"] for c in retained}:
            record["outcome"] = "retained"
            record["reason"] = None
            record["duplicate_of"] = None
        # else record already failed or rejected

    # --- Build EstimationResult ---
    retained_candidates = []
    for cand in retained:
        fit_metrics = cand["fit_metrics"]
        metadata = {
            "start_index": cand["start_index"],
            "converged": cand["converged"],
            "valid": True,
            "chi2": cand["chi2"],
            "chi2_reduced": cand["chi2_reduced"],
            "jacobian_rank": fit_metrics.get("jacobian_rank"),
            "n_valid_scalar_residuals": fit_metrics.get("n_valid_scalar_residuals"),
            "degrees_of_freedom": fit_metrics.get("degrees_of_freedom"),
            "epoch_years": 0.0,
            "coordinate_frame": "heliocentric ecliptic inertial",
            "position_unit": "AU",
            "velocity_unit": "AU/year",
            "time_unit": "years",
            "model_configuration": {
                "gravitational_parameter": 39.476926421373,
                "integrator": "IAS15",
                "integrator_epsilon": 1e-12,
                "planetary_configuration": "C1 BODY_DATA",
                "reference_epoch_years": 0.0,
                "coordinate_frame": "heliocentric ecliptic inertial",
                "position_unit": "AU",
                "velocity_unit": "AU/year",
                "time_unit": "years",
            },
        }
        retained_candidates.append(
            OrbitCandidate(
                state=cand["state"],
                epoch_years=0.0,
                metadata=metadata,
            )
        )

    estimation_result = EstimationResult(
        candidates=retained_candidates,
        best_fit=phase3_result.best_fit,
        source_dataset_metadata=dataset.metadata,
    )

    return estimation_result, audit_log
