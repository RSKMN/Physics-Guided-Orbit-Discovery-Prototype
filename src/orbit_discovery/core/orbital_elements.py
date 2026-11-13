"""Cartesian state and classical orbital element conversions.

Implements bidirectional conversion between heliocentric Cartesian state vectors
and classical orbital elements for the project's gravitational model.

Conventions:
- Reference frame: heliocentric ecliptic inertial (same as Component 1).
- Gravitational parameter: mu = 1.0 in units (yr, AU, Msun).
- Angles: radians internally.
- Singularities: circular/equatorial orbits handled with documented conventions.
- All identifiers are ASCII-safe; no Unicode characters in code.
- Clear English docstrings and comments.
"""

from __future__ import annotations

import math

#: Gravitational parameter mu = G*M_sun. In project units (yr, AU, Msun), mu = 1.0.
MU = 1.0

#: Tolerance for treating eccentricity as zero (circular orbit).
ECCENTRICITY_CIRCULAR_TOL = 1e-12

#: Tolerance for treating inclination as zero (equatorial orbit).
INCLINATION_EQUATORIAL_TOL = 1e-12

#: Tolerance for zero angular momentum / node.
ZERO_TOL = 1e-15


class OrbitalElements:
    """Classical orbital elements for a heliocentric orbit.

    All angles are in radians.

    Attributes
    ----------
    a : float
        Semi-major axis in AU. Positive for elliptical and hyperbolic orbits.
    e : float
        Eccentricity. 0 <= e < 1 ellipse, e >= 1 parabola/hyperbola.
    i : float
        Inclination in radians, angle between orbital plane and reference plane.
    Omega : float
        Longitude of ascending node in radians, [0, 2*pi).
    omega : float
        Argument of periapsis in radians, [0, 2*pi).
    nu : float
        True anomaly in radians, [0, 2*pi).
    """

    __slots__ = ("a", "e", "i", "Omega", "omega", "nu")

    def __init__(self, a, e, i, Omega, omega, nu):
        self.a = a
        self.e = e
        self.i = i
        self.Omega = Omega
        self.omega = omega
        self.nu = nu

    def __repr__(self):
        return (
            "OrbitalElements(a={}, e={}, i={:.2f} deg, "
            "Omega={:.2f} deg, omega={:.2f} deg, nu={:.2f} deg)".format(
                self.a,
                self.e,
                math.degrees(self.i),
                math.degrees(self.Omega),
                math.degrees(self.omega),
                math.degrees(self.nu),
            )
        )

    def __eq__(self, other, *args, **kwargs):
        if not isinstance(other, OrbitalElements):
            return NotImplemented
        return (
            math.isclose(self.a, other.a, abs_tol=1e-12)
            and math.isclose(self.e, other.e, abs_tol=1e-12)
            and math.isclose(self.i, other.i, abs_tol=1e-12)
            and math.isclose(self.Omega, other.Omega, abs_tol=1e-12)
            and math.isclose(self.omega, other.omega, abs_tol=1e-12)
            and math.isclose(self.nu, other.nu, abs_tol=1e-12)
        )

    def __hash__(self):
        return hash(
            (
                round(self.a, 9),
                round(self.e, 9),
                round(self.i, 9),
                round(self.Omega, 9),
                round(self.omega, 9),
                round(self.nu, 9),
            )
        )