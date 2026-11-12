"""Shared unit-conversion constants for the orbit discovery project."""

DAYS_PER_YEAR = 365.25
"""Days in a Julian year.

This is the project-wide time convention used to convert between year- and
day-based time axes. It is a unit convention, not a simulation setting.
"""

ARCSEC_TO_DEG = 1.0 / 3600.0
"""Degrees per arcsecond.

Multiply an angle in arcseconds by this factor to obtain degrees. Its inverse
(3600) converts degrees to arcseconds, as used by angular-residual analysis.
"""
