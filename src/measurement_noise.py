"""Compatibility shim for the old ``src.measurement_noise`` path."""

from orbit_discovery.component2_observations.noise import (
    ARCSEC_TO_DEG,
    add_measurement_noise,
)

__all__ = [
    "ARCSEC_TO_DEG",
    "add_measurement_noise",
]
