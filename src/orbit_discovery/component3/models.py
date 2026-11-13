"""Component 3 foundational data structures and models.

These models define the Cartesian asteroid state representation and the containers
for orbit estimation results. They are intended for use by downstream fitting and
propagation algorithms.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List

import numpy as np


#: Reference epoch for all prototype time representations (elapsed simulation time).
REFERENCE_EPOCH_YEARS = 0.0


@dataclass(frozen=True)
class OrbitState:
    """Six-dimensional Cartesian asteroid state (Heliocentric ecliptic inertial)."""

    rx: float
    ry: float
    rz: float
    vx: float
    vy: float
    vz: float

    def validate(self) -> None:
        """Validate state dimensions and finite numerical values."""
        state = self.to_array()
        if not np.isfinite(state).all():
            raise ValueError("OrbitState contains non-finite values.")

    def to_array(self) -> np.ndarray:
        """Return state as a 6D numpy array [rx, ry, rz, vx, vy, vz]."""
        return np.array([self.rx, self.ry, self.rz, self.vx, self.vy, self.vz])

    def to_dict(self) -> Dict[str, float]:
        """Convert state to a dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> OrbitState:
        """Create OrbitState from a dictionary."""
        return cls(**data)


@dataclass(frozen=True)
class ObservationDataset:
    """Validated observation measurement dataset."""

    data: Dict[str, np.ndarray]
    frame: str
    time_scale: str
    metadata: Dict[str, Any]

    def validate(self) -> None:
        """Validate dataset finite values and timestamp ordering."""
        # Validate time_years ordering
        time_years = self.data["time_years"]
        if not np.all(np.diff(time_years) >= 0):
            raise ValueError("Observation time_years are not non-decreasing.")

        # Validate finite values for all numeric arrays
        for key, arr in self.data.items():
            if not isinstance(arr, np.ndarray):
                continue  # skip scalar metadata (e.g. frame, time_scale)
            arr_float = np.asarray(arr, dtype=float)
            if not np.isfinite(arr_float).all():
                raise ValueError(f"Observation dataset contains non-finite values in {key}.")


@dataclass(frozen=True)
class OrbitCandidate:
    """A single candidate orbit solution."""

    state: OrbitState
    epoch_years: float
    metadata: Dict[str, Any]


@dataclass(frozen=True)
class BestFitResult:
    """Result of an orbit determination fit."""

    state: OrbitState
    epoch_years: float
    residuals: Dict[str, np.ndarray]
    fit_metrics: Dict[str, float]


@dataclass(frozen=True)
class EstimationResult:
    """Overall orbit estimation result."""

    candidates: List[OrbitCandidate]
    best_fit: BestFitResult
    source_dataset_metadata: Dict[str, Any]
