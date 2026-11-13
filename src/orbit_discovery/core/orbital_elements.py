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

import numpy as np

#: Gravitational parameter mu = G*M_sun. In project units (yr, AU, Msun), mu = 1.0.
#: NOTE: REBOUND with sim.units = ("yr", "AU", "Msun") sets sim.G = 39.4769 (~4*pi^2),
#: so the *actual* gravitational parameter is 39.4769, not 1.0.  This declaration is
#: retained for documentation only; downstream analytic computations that must agree
#: with C1's REBOUND propagation should use the value from REBOUND's sim.G instead.
MU = 1.0

#: Actual gravitational parameter used by REBOUND with sim.units = ("yr", "AU", "Msun").
#: Measured as sim.G = 39.476926421373 with M_sun = 1.0 Msun.
#: Use this value for analytic computations (vis-viva, eccentricity vector, observer
#: velocity) that must be consistent with C1's N-body propagation.
MU_REBOUND = 39.476926421373

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


# ---------------------------------------------------------------------------
# Conversion helpers
# ---------------------------------------------------------------------------

def cartesian_to_orbital_elements(
    x: float,
    y: float,
    z: float,
    vx: float,
    vy: float,
    vz: float,
) -> OrbitalElements:
    """Convert a heliocentric Cartesian state to classical orbital elements.

    Parameters
    ----------
    x, y, z : float
        Position in AU (heliocentric ecliptic).
    vx, vy, vz : float
        Velocity in AU/year.

    Returns
    -------
    OrbitalElements
        Classical orbital elements (angles in radians).

    Raises
    ------
    ValueError
        If the state is degenerate (zero position, zero velocity, or zero
        angular momentum).
    """
    r_vec = np.array([x, y, z], dtype=float)
    v_vec = np.array([vx, vy, vz], dtype=float)

    r = float(np.linalg.norm(r_vec))
    v = float(np.linalg.norm(v_vec))

    if r <= ZERO_TOL:
        raise ValueError("Position vector is zero: the body is at the Sun.")
    if v <= ZERO_TOL:
        raise ValueError("Velocity vector is zero: body has no motion.")

    # Specific angular momentum vector h = r x v.
    h_vec = np.cross(r_vec, v_vec)
    h = float(np.linalg.norm(h_vec))
    if h <= ZERO_TOL:
        raise ValueError("Specific angular momentum is zero: orbit is degenerate.")

    # Eccentricity vector: e = (v x h)/mu - r_vec/r.
    e_vec = np.cross(v_vec, h_vec) / MU_REBOUND - r_vec / r
    e = float(np.linalg.norm(e_vec))

    # Semi-major axis from vis-viva energy: energy = v^2/2 - mu/r; a = -mu/(2E).
    energy = 0.5 * v * v - MU_REBOUND / r
    if abs(energy) <= ZERO_TOL:
        a = 1.0e12  # parabolic approximation
    else:
        a = -MU_REBOUND / (2.0 * energy)

    # Inclination: i = acos(h_z / h).
    i = math.acos(max(-1.0, min(1.0, h_vec[2] / h)))

    # Node vector: n = k x h.
    k_vec = np.array([0.0, 0.0, 1.0])
    n_vec = np.cross(k_vec, h_vec)
    n = float(np.linalg.norm(n_vec))

    # Longitude of ascending node.
    if n <= ZERO_TOL:
        Omega = 0.0  # equatorial: node undefined, convention 0.
    else:
        Omega = math.acos(max(-1.0, min(1.0, n_vec[0] / n)))
        if n_vec[1] < 0.0:
            Omega = 2.0 * math.pi - Omega

    # Argument of periapsis.
    if e <= ECCENTRICITY_CIRCULAR_TOL or n <= ZERO_TOL:
        omega = 0.0  # circular or equatorial: convention.
    else:
        omega = math.acos(
            max(-1.0, min(1.0, float(np.dot(n_vec, e_vec)) / (n * e)))
        )
        if e_vec[2] < 0.0:
            omega = 2.0 * math.pi - omega

    # True anomaly.
    if e <= ECCENTRICITY_CIRCULAR_TOL:
        nu = 0.0  # circular: anomaly undefined, convention 0.
    else:
        nu = math.acos(
            max(-1.0, min(1.0, float(np.dot(e_vec, r_vec)) / (e * r)))
        )
        if float(np.dot(r_vec, v_vec)) < 0.0:
            nu = 2.0 * math.pi - nu

    return OrbitalElements(a=a, e=e, i=i, Omega=Omega, omega=omega, nu=nu)


def orbital_elements_to_cartesian(
    elements: OrbitalElements,
) -> tuple[float, float, float, float, float, float]:
    """Convert classical orbital elements to a heliocentric Cartesian state.

    Parameters
    ----------
    elements : OrbitalElements
        Classical orbital elements (angles in radians).

    Returns
    -------
    tuple of float
        ``(x, y, z, vx, vy, vz)`` in AU and AU/year.
    """
    a = elements.a
    e = elements.e
    i = elements.i
    Omega = elements.Omega
    omega = elements.omega
    nu = elements.nu

    # Orbital-plane position/velocity (perifocal frame).
    if abs(energy_from_elements(a, e)) <= ZERO_TOL:
        # Parabolic approximation: large semi-major axis.
        r_mag = 1.0e12
    else:
        r_mag = a * (1.0 - e * e) / (1.0 + e * math.cos(nu))

    # Speed from vis-viva: v^2 = mu * (2/r - 1/a).
    if a > 0:
        v_mag = math.sqrt(MU_REBOUND * (2.0 / r_mag - 1.0 / a))
    else:
        v_mag = math.sqrt(2.0 * MU_REBOUND / r_mag)

    # Perifocal position and velocity vectors.
    cos_nu = math.cos(nu)
    sin_nu = math.sin(nu)
    p_x = r_mag * cos_nu
    p_y = r_mag * sin_nu
    p_z = 0.0

    # Flight-path angle from perifocal velocity components.
    # v_perifocal = (mu/h) * [-sin(nu), e + cos(nu), 0]
    h = math.sqrt(MU_REBOUND * a * (1.0 - e * e)) if a > 0 and e < 1.0 else math.sqrt(MU_REBOUND * r_mag * (1.0 + e * cos_nu))
    v_p_x = -MU_REBOUND / h * sin_nu
    v_p_y = MU_REBOUND / h * (e + cos_nu)
    v_p_z = 0.0

    # Rotation matrix from perifocal to inertial frame (3-1-3 Euler: Omega, i, omega).
    cos_O = math.cos(Omega)
    sin_O = math.sin(Omega)
    cos_i = math.cos(i)
    sin_i = math.sin(i)
    cos_w = math.cos(omega)
    sin_w = math.sin(omega)

    # r_inertial = R3(Omega) * R1(i) * R3(omega) * r_perifocal
    r_x = (
        (cos_O * cos_w - sin_O * sin_w * cos_i) * p_x
        + (-cos_O * sin_w - sin_O * cos_w * cos_i) * p_y
    )
    r_y = (
        (sin_O * cos_w + cos_O * sin_w * cos_i) * p_x
        + (-sin_O * sin_w + cos_O * cos_w * cos_i) * p_y
    )
    r_z = (sin_i * sin_w) * p_x + (sin_i * cos_w) * p_y

    v_x = (
        (cos_O * cos_w - sin_O * sin_w * cos_i) * v_p_x
        + (-cos_O * sin_w - sin_O * cos_w * cos_i) * v_p_y
    )
    v_y = (
        (sin_O * cos_w + cos_O * sin_w * cos_i) * v_p_x
        + (-sin_O * sin_w + cos_O * cos_w * cos_i) * v_p_y
    )
    v_z = (sin_i * sin_w) * v_p_x + (sin_i * cos_w) * v_p_y

    return (float(r_x), float(r_y), float(r_z), float(v_x), float(v_y), float(v_z))


def energy_from_elements(a: float, e: float) -> float:
    """Specific orbital energy from semi-major axis: E = -mu / (2a)."""
    if a <= 0:
        return 0.0  # parabolic / hyperbolic approximation
    return -MU_REBOUND / (2.0 * a)


def round_trip_cartesian_to_elements_to_cartesian(
    x: float, y: float, z: float, vx: float, vy: float, vz: float
) -> tuple[float, float, float, float, float, float]:
    """Round-trip: Cartesian -> elements -> Cartesian."""
    elements = cartesian_to_orbital_elements(x, y, z, vx, vy, vz)
    return orbital_elements_to_cartesian(elements)


def round_trip_elements_to_cartesian_to_elements(
    elements: OrbitalElements,
) -> OrbitalElements:
    """Round-trip: elements -> Cartesian -> elements."""
    x, y, z, vx, vy, vz = orbital_elements_to_cartesian(elements)
    return cartesian_to_orbital_elements(x, y, z, vx, vy, vz)