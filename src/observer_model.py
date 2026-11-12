"""Compatibility shim for the old ``src.observer_model`` path."""

from orbit_discovery.component2_observations.observer import (
    calculate_observer_positions,
    calculate_relative_positions,
)

__all__ = [
    "calculate_observer_positions",
    "calculate_relative_positions",
]
