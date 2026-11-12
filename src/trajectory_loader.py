"""Compatibility shim for the old ``src.trajectory_loader`` path."""

from orbit_discovery.component2_observations.loader import (
    REQUIRED_COLUMNS,
    load_trajectory,
)

__all__ = [
    "REQUIRED_COLUMNS",
    "load_trajectory",
]
