"""Compatibility shim for the old ``src.coordinate_converter`` path."""

from orbit_discovery.component2_observations.frames import (
    ecliptic_to_equatorial,
    calculate_ra_dec,
)

__all__ = [
    "ecliptic_to_equatorial",
    "calculate_ra_dec",
]
