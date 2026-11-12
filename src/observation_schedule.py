"""Compatibility shim for the old ``src.observation_schedule`` path."""

from orbit_discovery.component2_observations.schedule import (
    generate_observation_times,
    interpolate_positions,
)

__all__ = [
    "generate_observation_times",
    "interpolate_positions",
]
