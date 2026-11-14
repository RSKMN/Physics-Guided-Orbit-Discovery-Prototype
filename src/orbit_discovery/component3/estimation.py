"""Component 3: Estimation integration entry point."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional
import numpy as np

from orbit_discovery.component3.models import (
    OrbitState, ObservationDataset, BestFitResult, EstimationResult, OrbitCandidate
)
from orbit_discovery.component3.dynamics import propagate_trial_state
from orbit_discovery.component3.observation_model import (
    predict_apparent_coordinates, ObserverConfig, OBLIQUITY_DEFAULT
)
from orbit_discovery.component3.residuals import compute_residuals
from orbit_discovery.component3.optimizer import least_squares_lm

def _validate_dataset(dataset: ObservationDataset) -> None:
    """Validate dataset consistency."""
    time_years = dataset.data["time_years"]
    if time_years.size == 0:
        raise ValueError("Observation dataset must be non-empty.")
    if not np.all(np.isfinite(time_years)):
        raise ValueError("All observation epochs must be finite.")
    if np.any(time_years < 0.0):
        raise ValueError("Dataset contains observations with negative epochs.")

    required_keys = ["ra_deg", "dec_deg", "sigma_ra_cosdec_arcsec", "sigma_dec_arcsec"]
    for key in required_keys:
        if key not in dataset.data:
            raise ValueError(f"Missing required dataset key: {key}")
        if dataset.data[key].size != time_years.size:
            raise ValueError(f"Dataset key {key} has incompatible length {dataset.data[key].size}, expected {time_years.size}")

def build_residual_function(
    dataset: ObservationDataset,
    observer_config: Optional[ObserverConfig] = None,
    obliquity_deg: float = OBLIQUITY_DEFAULT,
    bodies: Optional[List[str]] = None,
) -> Callable[[np.ndarray], np.ndarray]:
    """Build the residual function for the optimizer."""
    _validate_dataset(dataset)
    time_years = dataset.data["time_years"]

    def fun(x_physical: np.ndarray) -> np.ndarray:
        # Construct OrbitState directly from physical array (physical=scaled_internal)
        state = OrbitState(
            rx=float(x_physical[0]), ry=float(x_physical[1]), rz=float(x_physical[2]),
            vx=float(x_physical[3]), vy=float(x_physical[4]), vz=float(x_physical[5])
        )

        # 1. Propagate
        # Caught numerical exceptions wrapped into ValueError for optimizer recovery
        try:
            states = propagate_trial_state(state, time_years.tolist(), bodies=bodies)

            # 2. Predict
            predictions = predict_apparent_coordinates(
                states, time_years.tolist(), observer_config, obliquity_deg
            )

            ra_pred = np.array([p["ra_deg"] for p in predictions])
            dec_pred = np.array([p["dec_deg"] for p in predictions])

            # 3. Residuals
            residuals = compute_residuals(
                dataset.data["ra_deg"], dataset.data["dec_deg"],
                ra_pred, dec_pred,
                dataset.data["sigma_ra_cosdec_arcsec"],
                dataset.data["sigma_dec_arcsec"]
            )

            return residuals["residual_vector"]

        except (ValueError, RuntimeError, FloatingPointError, ArithmeticError, OverflowError) as e:
            # Wrap into ValueError to trigger optimizer's recoverable trial rejection
            raise ValueError(f"Estimation evaluation failed: {e}") from e

    return fun

def run_estimation(
    dataset: ObservationDataset,
    initial_state: OrbitState,
    observer_config: Optional[ObserverConfig] = None,
    obliquity_deg: float = OBLIQUITY_DEFAULT,
    bodies: Optional[List[str]] = None,
    max_iter: int = 100,
    max_nfev: int = 1000,
    initial_lambda: float = 1e-3,
) -> EstimationResult:
    """Run best-fit orbit estimation."""
    # Pre-validation
    initial_state.validate()

    # Validate dataset before any propagation
    _validate_dataset(dataset)

    # Initial manual propagation check (fail-fast)
    time_years = dataset.data["time_years"]
    try:
        propagate_trial_state(initial_state, time_years.tolist(), bodies=bodies)
    except (ValueError, RuntimeError, FloatingPointError, ArithmeticError, OverflowError) as e:
        raise ValueError(f"Initial propagation failure: {e}") from e

    # Coordinate contract: res["x"] is physical
    x0 = initial_state.to_array()
    scales = np.array([1.0, 1.0, 1.0, 2 * np.pi, 2 * np.pi, 2 * np.pi])

    residual_fn = build_residual_function(dataset, observer_config, obliquity_deg, bodies)

    # Optimize
    res = least_squares_lm(
        x0, scales, residual_fn,
        max_iter=max_iter, max_nfev=max_nfev, initial_lambda=initial_lambda
    )

    # Finalize
    best_state_arr = res["x"] # Physical coordinates
    best_state = OrbitState(
        rx=float(best_state_arr[0]), ry=float(best_state_arr[1]), rz=float(best_state_arr[2]),
        vx=float(best_state_arr[3]), vy=float(best_state_arr[4]), vz=float(best_state_arr[5])
    )

    # Final prediction exactly once
    try:
        final_states = propagate_trial_state(best_state, time_years.tolist(), bodies=bodies)
        final_preds = predict_apparent_coordinates(
            final_states, time_years.tolist(), observer_config, obliquity_deg
        )

        final_residuals_dict = compute_residuals(
            dataset.data["ra_deg"], dataset.data["dec_deg"],
            np.array([p["ra_deg"] for p in final_preds]),
            np.array([p["dec_deg"] for p in final_preds]),
            dataset.data["sigma_ra_cosdec_arcsec"],
            dataset.data["sigma_dec_arcsec"]
        )
    except (ValueError, RuntimeError, FloatingPointError, ArithmeticError, OverflowError) as e:
        raise ValueError(f"Final prediction/residual failure: {e}") from e

    # Calculate Jacobian rank from optimizer's final scaled Jacobian
    jacobian_rank = None
    jac_scaled = res.get("jac_scaled")
    n_valid_scalar_residuals = int(final_residuals_dict["n_valid_scalar_residuals"])

    if jac_scaled is not None:
        try:
            # 1. Finite 2D array
            jac_scaled = np.asarray(jac_scaled, dtype=float)
            if jac_scaled.ndim == 2 and jac_scaled.shape[1] == 6 and jac_scaled.shape[0] == n_valid_scalar_residuals:
                if np.all(np.isfinite(jac_scaled)):
                    # 4. SVD singular values
                    s = np.linalg.svd(jac_scaled, compute_uv=False)
                    if s.size > 0 and np.all(np.isfinite(s)):
                        # 6. Relative tolerance 1e-8 * s_max
                        s_max = s[0]
                        tol = 1e-8 * s_max
                        jacobian_rank = int(np.sum(s > tol))
                    elif s.size == 0:
                        jacobian_rank = 0
        except (ValueError, TypeError, np.linalg.LinAlgError):
            jacobian_rank = None

    best_fit = BestFitResult(
        state=best_state,
        epoch_years=0.0,
        residuals={
            "residual_vector": final_residuals_dict["residual_vector"],
            "ra_arcsec": final_residuals_dict["ra_arcsec"],
            "dec_arcsec": final_residuals_dict["dec_arcsec"],
            "valid_mask": final_residuals_dict["valid_mask"],
            "ra_normalized": final_residuals_dict["ra_normalized"],
            "dec_normalized": final_residuals_dict["dec_normalized"],
        },
        fit_metrics={
            "chi2": float(res["chi2"]),
            "optimality": float(res["optimality"]),
            "jacobian_rank": jacobian_rank,
            "n_valid_scalar_residuals": n_valid_scalar_residuals,
        }
    )

    candidate = OrbitCandidate(
        state=best_state,
        epoch_years=0.0,
        metadata={
            "converged": bool(res["converged"]),
            "termination_reason": str(res["termination_reason"]),
            "n_iter": int(res["n_iter"]),
            "nfev": int(res["nfev"]),
            "njev": int(res["njev"]),
            "optimizer": "least_squares_lm",
            "jacobian_rank": jacobian_rank,
            "n_valid_scalar_residuals": n_valid_scalar_residuals,
        }
    )

    return EstimationResult(
        candidates=[candidate],
        best_fit=best_fit,
        source_dataset_metadata=dataset.metadata
    )
