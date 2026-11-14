"""Component 3 Phase 5B: Uncertainty estimation and diagnostics.

This module computes the Cartesian covariance and conditioning diagnostics
for an orbit fit, based on the Levenberg–Marquardt Jacobian.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np

#: Scale factors applied to the six Cartesian state variables.
#: The first three are position (AU), the last three are velocity (AU/year).
#: Velocities are scaled by 2*pi to map orbital frequency to a comparable
#   numerical magnitude as positions.
_STATE_SCALES: np.ndarray = np.array(
    [1.0, 1.0, 1.0, 2.0 * np.pi, 2.0 * np.pi, 2.0 * np.pi], dtype=float
)

#: Coordinate ordering for the 6-dimensional Cartesian state.
COORDINATE_ORDER: List[str] = ["rx", "ry", "rz", "vx", "vy", "vz"]

#: Units for the first three (position) coordinates.
POSITION_UNIT: str = "AU"

#: Units for the last three (velocity) coordinates.
VELOCITY_UNIT: str = "AU/year"

#: Relative tolerance for numerical rank determination.
#: Matches the existing estimator tolerance in estimation.py.
_RANK_TOL_FACTOR: float = 1e-8


@dataclass(frozen=True)
class UncertaintyResult:
    """Uncertainty estimation result for a single orbit fit.

    Attributes:
        covariance: Optional 6x6 physical Cartesian covariance matrix.
            ``None`` when covariance is invalid (rank deficiency,
            non-finite Jacobian, non-convergence, etc.).
        covariance_valid: Whether the covariance matrix is valid.
        failure_reason: Human-readable reason when covariance is invalid,
            otherwise ``None``.
        singular_values: Singular values of the scaled Jacobian from SVD.
        condition_number: Ratio of largest to smallest singular value.
        rank: Numerical rank of the scaled Jacobian.
        rank_tolerance: Tolerance used for numerical rank determination.
        degrees_of_freedom: ``n_valid_scalar_residuals - 6``.
        caveats: Human-readable explanation of approximation limitations.
    """

    covariance: Optional[np.ndarray]
    covariance_valid: bool
    failure_reason: Optional[str]
    singular_values: np.ndarray
    condition_number: float
    rank: int
    rank_tolerance: float
    degrees_of_freedom: int
    caveats: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the result to a JSON-safe dictionary."""
        return {
            "covariance": (
                self.covariance.tolist() if self.covariance is not None else None
            ),
            "covariance_valid": self.covariance_valid,
            "failure_reason": self.failure_reason,
            "singular_values": self.singular_values.tolist(),
            "condition_number": self.condition_number,
            "rank": self.rank,
            "rank_tolerance": self.rank_tolerance,
            "degrees_of_freedom": self.degrees_of_freedom,
            "caveats": self.caveats,
        }


def _invalid_result(
    reason: str,
    *,
    singular_values: Optional[np.ndarray] = None,
    condition_number: float = float("inf"),
    rank: int = 0,
    rank_tolerance: float = 0.0,
    degrees_of_freedom: int = 0,
) -> UncertaintyResult:
    """Build a default invalid result with the given failure reason."""
    if singular_values is None:
        singular_values = np.array([], dtype=float)
    return UncertaintyResult(
        covariance=None,
        covariance_valid=False,
        failure_reason=reason,
        singular_values=singular_values,
        condition_number=condition_number,
        rank=rank,
        rank_tolerance=rank_tolerance,
        degrees_of_freedom=degrees_of_freedom,
        caveats=[
            "Local linearized approximation",
            "Not a calibrated confidence region",
        ],
    )


def compute_uncertainty(
    jac_scaled: np.ndarray,
    n_valid_scalar_residuals: int,
    converged: bool = False,
) -> UncertaintyResult:
    """Compute Cartesian covariance and conditioning diagnostics.

    The scaled Jacobian returned by the optimizer satisfies::

        J_scaled = J_phys @ diag(s)

    where ``s = [1, 1, 1, 2*pi, 2*pi, 2*pi]`` scales positions (AU) and
    velocities (AU/year) to comparable numerical magnitudes.

    Using SVD ``J_scaled = U diag(sigma) Vt``, the physical Cartesian
    covariance is computed without explicitly inverting ``J.T @ J``::

        P_scaled = V diag(1 / sigma^2) V.T
        P_phys   = diag(s) @ P_scaled @ diag(s)

    Parameters:
        jac_scaled: Scaled Jacobian of shape ``(m, 6)`` from the optimizer.
        n_valid_scalar_residuals: Number of valid scalar residuals in the fit.
        converged: Whether the optimizer reported convergence.

    Returns:
        ``UncertaintyResult`` with covariance, conditioning diagnostics, and
        failure information when applicable.
    """
    # --- Preconditions ----------------------------------------------------

    if not converged:
        return _invalid_result("non_converged")

    if jac_scaled is None or not isinstance(jac_scaled, np.ndarray):
        return _invalid_result("invalid_jacobian")

    if jac_scaled.ndim != 2 or jac_scaled.shape[1] != 6:
        return _invalid_result("invalid_jacobian_shape")

    n_residuals = jac_scaled.shape[0]
    if n_residuals == 0 or not np.all(np.isfinite(jac_scaled)):
        return _invalid_result("non_finite_jacobian")

    # --- SVD --------------------------------------------------------------

    try:
        _, singular_values, vt = np.linalg.svd(jac_scaled, full_matrices=False)
    except np.linalg.LinAlgError:
        return _invalid_result("svd_failure")

    if singular_values.size == 0 or not np.all(np.isfinite(singular_values)):
        return _invalid_result(
            "invalid_singular_values",
            singular_values=singular_values,
        )

    # --- Numerical rank and conditioning ----------------------------------

    s_max = float(singular_values[0])
    rank_tol = _RANK_TOL_FACTOR * s_max
    rank = int(np.sum(singular_values > rank_tol))

    if s_max <= 0.0:
        condition_number = float("inf")
    elif float(singular_values[-1]) > 0.0:
        condition_number = float(s_max / float(singular_values[-1]))
    else:
        condition_number = float("inf")

    # --- Degrees of freedom ------------------------------------------------

    degrees_of_freedom = int(n_valid_scalar_residuals) - 6

    if degrees_of_freedom <= 0:
        return _invalid_result(
            "insufficient_dof",
            singular_values=singular_values,
            condition_number=condition_number,
            rank=rank,
            rank_tolerance=rank_tol,
            degrees_of_freedom=degrees_of_freedom,
        )

    # --- Rank deficiency check ---------------------------------------------

    if rank < 6:
        return _invalid_result(
            "rank_deficient",
            singular_values=singular_values,
            condition_number=condition_number,
            rank=rank,
            rank_tolerance=rank_tol,
            degrees_of_freedom=degrees_of_freedom,
        )

    # --- Covariance --------------------------------------------------------

    v = vt.T
    p_scaled = v @ np.diag(1.0 / (singular_values**2)) @ vt

    s_diag = np.diag(_STATE_SCALES)
    p_phys = s_diag @ p_scaled @ s_diag

    if not np.all(np.isfinite(p_phys)):
        return _invalid_result(
            "non_finite_covariance",
            singular_values=singular_values,
            condition_number=condition_number,
            rank=rank,
            rank_tolerance=rank_tol,
            degrees_of_freedom=degrees_of_freedom,
        )

    return UncertaintyResult(
        covariance=p_phys,
        covariance_valid=True,
        failure_reason=None,
        singular_values=singular_values,
        condition_number=condition_number,
        rank=rank,
        rank_tolerance=rank_tol,
        degrees_of_freedom=degrees_of_freedom,
        caveats=[
            "Local linearized approximation around the best-fit state",
            "Residuals are already normalized by supplied absolute measurement "
            "uncertainties; covariance is not multiplied by reduced chi-square",
            "Not a calibrated confidence region",
        ],
    )
