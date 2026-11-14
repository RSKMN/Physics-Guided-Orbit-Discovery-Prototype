"""Component 3 Phase 3C: NumPy-only Levenberg–Marquardt least-squares optimizer.

Provides a reusable, robust least-squares optimizer for orbit estimation,
using Levenberg–Marquardt optimization with parameter scaling and
numerical forward-difference Jacobians.
"""

from __future__ import annotations

import math
from typing import Any, Callable, Dict, Optional

import numpy as np


class EvaluationLimitReached(Exception):
    """Exception raised when maximum function evaluations are exceeded."""
    pass


class EvaluationError(Exception):
    """Exception raised when function evaluation fails."""
    pass


# Explicitly supported numerical/domain exceptions. Unexpected programming
# errors such as TypeError and AttributeError must propagate rather than be
# swallowed and wrapped as EvaluationError.
_NUMERICAL_EXCEPTIONS = (
    ValueError,
    RuntimeError,
    FloatingPointError,
    ArithmeticError,
    OverflowError,
)


def least_squares_lm(
    x0: np.ndarray,
    s: np.ndarray,
    fun: Callable[[np.ndarray], np.ndarray],
    jac: Optional[Callable[[np.ndarray], np.ndarray]] = None,
    ftol: float = 1e-10,
    xtol: float = 1e-10,
    gtol: float = 1e-8,
    max_iter: int = 100,
    max_nfev: int = 1000,
    initial_lambda: float = 1e-3,
) -> Dict[str, Any]:
    """Levenberg–Marquardt nonlinear least-squares optimizer.

    Solves minimize 0.5 * ||r(x)||^2 in scaled parameter space.
    """
    # 1. Validation
    x = np.asarray(x0, dtype=float)
    s = np.asarray(s, dtype=float)
    if x.ndim != 1 or s.ndim != 1:
        raise ValueError("x0 and s must be 1D arrays.")
    if x.shape != s.shape:
        raise ValueError("x0 and s must have the same shape.")
    if x.size == 0 or s.size == 0:
        raise ValueError("x0 and s must not be empty.")
    if np.any(s <= 0) or not np.all(np.isfinite(s)):
        raise ValueError("Scales 's' must be strictly positive and finite.")
    if not np.all(np.isfinite(x)):
        raise ValueError("x0 must be finite.")
    if ftol < 0 or xtol < 0 or gtol < 0 or not np.isfinite(ftol) or not np.isfinite(xtol) or not np.isfinite(gtol):
        raise ValueError("Tolerances must be non-negative finite.")
    # max_iter and max_nfev must be positive integers; reject bool and float.
    for name, value in (("max_iter", max_iter), ("max_nfev", max_nfev)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} must be a positive integer.")
        if value <= 0:
            raise ValueError(f"{name} must be a positive integer.")
    if initial_lambda <= 0 or not np.isfinite(initial_lambda):
        raise ValueError("initial_lambda must be positive finite.")

    n_iter = 0
    nfev = [0]      # mutable container so _finalize sees updates from fun_wrapped
    njev = [0]      # mutable container so _finalize sees its own increments
    m = None        # initial residual dimension, set on first evaluation

    def fun_wrapped(x_val: np.ndarray) -> np.ndarray:
        nonlocal m
        if nfev[0] >= max_nfev:
            raise EvaluationLimitReached("Max function evaluations reached.")
        nfev[0] += 1
        try:
            r = np.asarray(fun(x_val), dtype=float)
        except _NUMERICAL_EXCEPTIONS as e:
            raise EvaluationError(f"Evaluation failed: {e}") from e
        if r.ndim != 1:
            raise EvaluationError("Residual function must return a 1D array.")
        if r.size == 0:
            raise EvaluationError("Residual function must return a non-empty array.")
        if m is None:
            m = r.shape[0]
        elif r.shape[0] != m:
            raise EvaluationError(
                f"Residual dimension {r.shape[0]} does not match initial dimension {m}."
            )
        if not np.all(np.isfinite(r)):
            raise EvaluationError("Residuals contain non-finite values.")
        return r

    # Initial evaluation
    try:
        r = fun_wrapped(x)
        m = len(r)
    except EvaluationLimitReached:
        return _result(x, None, np.nan, None, None, False, "Initial evaluation hit limit.", n_iter, int(nfev[0]), int(njev[0]), np.nan)
    except EvaluationError as e:
        return _result(x, None, np.nan, None, None, False, str(e), n_iter, int(nfev[0]), int(njev[0]), np.nan)

    chi2 = np.sum(r**2)
    if not np.isfinite(chi2):
        return _result(x, r, chi2, None, None, False, "Initial chi-square is non-finite.", n_iter, nfev[0], njev[0], np.nan)
    if chi2 == 0:
        return _result(x, r, chi2, None, None, True, "Initial solution is exact.", n_iter, nfev[0], njev[0], 0.0)

    # Initial gradient check when analytic Jacobian is supplied
    if jac is not None:
        try:
            J_phys = _validate_jacobian(jac(x), m, len(x))
            njev[0] += 1
            optimality = np.linalg.norm(J_phys.T @ r, ord=np.inf)
            if optimality < gtol:
                return _result(x, r, chi2, J_phys, J_phys @ np.diag(s), True, "Initial gradient below tolerance.", n_iter, nfev[0], njev[0], optimality)
        except (ValueError, EvaluationError) as e:
            return _result(x, r, chi2, None, None, False, str(e), n_iter, nfev[0], njev[0], np.nan)

    lam = initial_lambda
    u = x / s

    for iteration in range(1, max_iter + 1):
        n_iter = iteration

        # Jacobian computation
        if jac is None:
            try:
                J_scaled, J_phys = _numerical_jacobian_scaled(fun_wrapped, x, s, r)
                njev[0] += 1
            except EvaluationLimitReached:
                return _result(x, r, chi2, None, None, False, "Max evaluations during Jacobian.", n_iter, nfev[0], njev[0], np.nan)
            except EvaluationError as e:
                return _result(x, r, chi2, None, None, False, str(e), n_iter, nfev[0], njev[0], np.nan)
        else:
            try:
                J_phys = _validate_jacobian(jac(x), m, len(x))
                njev[0] += 1
                J_scaled = J_phys @ np.diag(s)
            except (ValueError, EvaluationError) as e:
                return _result(x, r, chi2, None, None, False, str(e), n_iter, nfev[0], njev[0], np.nan)

        optimality = np.linalg.norm(J_phys.T @ r, ord=np.inf)
        if optimality < gtol:
            return _result(x, r, chi2, J_phys, J_scaled, True, "Gradient norm below tolerance.", n_iter, nfev[0], njev[0], optimality)

        JTJ = J_scaled.T @ J_scaled
        diag_JTJ = np.diag(JTJ)
        damping = lam * np.maximum(diag_JTJ, 1e-16)

        try:
            delta_u = np.linalg.solve(JTJ + np.diag(damping), -J_scaled.T @ r)
        except np.linalg.LinAlgError:
            lam = min(lam * 10.0, 1e16)  # Bound damping
            continue

        delta_x = s * delta_u
        x_trial = x + delta_x
        u_trial = x_trial / s

        # Trial evaluation
        try:
            r_trial = fun_wrapped(x_trial)
        except EvaluationLimitReached:
            return _result(x, r, chi2, J_phys, J_scaled, False, "Max evaluations during trial.", n_iter, nfev[0], njev[0], optimality)
        except EvaluationError:
            lam = min(lam * 10.0, 1e16)
            continue

        chi2_trial = np.sum(r_trial**2)
        if not np.isfinite(chi2_trial):
            # Non-finite trial chi-square (overflow): recoverable rejected step.
            lam = min(lam * 10.0, 1e16)
            continue

        pred_reduction = -2 * (J_scaled.T @ r).T @ delta_u - delta_u.T @ (JTJ) @ delta_u

        if not np.isfinite(pred_reduction) or pred_reduction <= 0:
            lam = min(lam * 10.0, 1e16)
            continue

        actual_reduction = chi2 - chi2_trial
        if not np.isfinite(actual_reduction):
            lam = min(lam * 10.0, 1e16)
            continue

        rho = actual_reduction / pred_reduction
        if not np.isfinite(rho):
            lam = min(lam * 10.0, 1e16)
            continue

        if rho > 0:
            chi2_prev = chi2
            x, u, r, chi2 = x_trial, u_trial, r_trial, chi2_trial
            lam = max(lam * max(1 / 3, 1 - (2 * rho - 1) ** 3), 1e-16)  # Bounded damping decrease

            if abs(chi2 - chi2_prev) / max(chi2_prev, np.finfo(float).tiny) < ftol:
                return _finalize(x, r, chi2, fun_wrapped, jac, s, n_iter, nfev, njev, True, "Chi-square change below tolerance.")
            if np.linalg.norm(delta_u) / max(np.linalg.norm(u), np.finfo(float).tiny) < xtol:
                return _finalize(x, r, chi2, fun_wrapped, jac, s, n_iter, nfev, njev, True, "Scaled step size below tolerance.")
        else:
            lam = min(lam * 10.0, 1e16)

    return _finalize(x, r, chi2, fun_wrapped, jac, s, n_iter, nfev, njev, False, "Max iterations.")


def _validate_jacobian(J: np.ndarray, m: int, n: int) -> np.ndarray:
    J = np.asarray(J, dtype=float)
    if J.shape != (m, n):
        raise ValueError(f"Jacobian shape {J.shape} does not match (m, n) = ({m}, {n}).")
    if not np.all(np.isfinite(J)):
        raise EvaluationError("Jacobian contains non-finite values.")
    return J


def _numerical_jacobian_scaled(fun, x, s, r):
    u = x / s
    eps = np.finfo(float).eps
    n = len(u)
    m = len(r)
    J_scaled = np.zeros((m, n))
    for k in range(n):
        h = math.sqrt(eps) * max(abs(u[k]), 1.0)
        u_plus = u.copy()
        u_plus[k] += h
        r_plus = fun(u_plus * s)
        J_scaled[:, k] = (r_plus - r) / h
    J_phys = J_scaled @ np.diag(1.0 / s)
    return J_scaled, J_phys


def _finalize(x, r, chi2, fun_wrapped, jac, s, n_iter, nfev, njev, converged, message):
    """Return final Jacobian at the current x, respecting evaluation budget.

    ``nfev`` and ``njev`` are mutable single-element lists so that updates
    made by ``fun_wrapped`` (via nonlocal) and by this function are visible
    to the caller and reflected in the reported counts.
    """
    if jac is None:
        try:
            J_scaled, J_phys = _numerical_jacobian_scaled(fun_wrapped, x, s, r)
            njev[0] += 1
            optimality = np.linalg.norm(J_phys.T @ r, ord=np.inf)
            return _result(x, r, chi2, J_phys, J_scaled, converged, message, n_iter, nfev[0], njev[0], optimality)
        except (EvaluationLimitReached, EvaluationError):
            return _result(x, r, chi2, None, None, converged, message + " (final Jacobian unavailable: evaluation budget exhausted or failed).", n_iter, nfev[0], njev[0], np.nan)
    else:
        try:
            J_phys = _validate_jacobian(jac(x), len(r), len(x))
            J_scaled = J_phys @ np.diag(s)
            njev[0] += 1  # Count the final analytic Jacobian evaluation.
            optimality = np.linalg.norm(J_phys.T @ r, ord=np.inf)
            return _result(x, r, chi2, J_phys, J_scaled, converged, message, n_iter, nfev[0], njev[0], optimality)
        except (ValueError, EvaluationError):
            return _result(x, r, chi2, None, None, converged, message + " (final Jacobian computation failed).", n_iter, nfev[0], njev[0], np.nan)


def _result(x, r, chi2, jac, jac_scaled, converged, message, n_iter, nfev, njev, optimality):
    return {
        "x": x,
        "fun": r,
        "chi2": chi2,
        "jac": jac,
        "jac_scaled": jac_scaled,
        "success": converged,
        "converged": converged,
        "message": message,
        "termination_reason": message,
        "n_iter": n_iter,
        "nfev": nfev,
        "njev": njev,
        "optimality": optimality,
    }
