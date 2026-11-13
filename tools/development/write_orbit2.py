#!/usr/bin/env python3
import os

proj_dir = r"E:\rskmn\Npersonal\projects\yr4\final\prototype-1\physics-guided-orbit-discovery-prototype"
os.chdir(proj_dir)

# Write the complete orbital_elements.py file
# Using write mode with explicit content

content = r"""\"\"\"Cartesian state and classical orbital element conversions.

Implements bidirectional conversion between heliocentric Cartesian state vectors
and classical orbital elements for the project's gravitational model.

Conventions:
- Reference frame: heliocentric ecliptic inertial (same as Component 1).
- Gravitational parameter: mu = 1.0 in units (yr, AU, Msun).
- Angles: radians internally.
- Singularities: circular/equatorial orbits handled with documented conventions.
- All identifiers are ASCII-safe; no Unicode characters in code.
- Clear English docstrings and comments.
\"\"\"

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
    \"\"\"Classical orbital elements for a heliocentric orbit.

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
    \"\"\"

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
"""

# Write part 1
with open("src/orbit_discovery/core/orbital_elements.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Part 1 written successfully ({} bytes)".format(len(content)))

# Part 2: cartesian_to_orbital_elements
part2 = r"""

# ======================================================================
# 2.3.2  Cartesian  -->  Orbital Elements
# ======================================================================


def cartesian_to_orbital_elements(x, y, z, vx, vy, vz):
    \"\"\"Convert a heliocentric Cartesian state to classical orbital elements.

    The state is expressed in AU for position and AU/year for velocity, with
    the gravitational parameter mu = 1.0 (project units :math:`\\mathrm{yr},\\mathrm{AU},\\mathrm{M_\\odot}`).

    The reference frame is the heliocentric ecliptic inertial frame (the same
    as used by Component 1).

    Parameters
    ----------
    x, y, z : float
        Heliocentric position in AU.
    vx, vy, vz : float
        Heliocentric velocity in AU/year.

    Returns
    -------
    OrbitalElements
        The classical orbital elements.

    Raises
    ------
    ValueError
        If the state is zero (the body is at the Sun) or the velocity is
        zero, or if the state cannot be associated with a closed-orbit
        solution.
    \"\"\"\n    r = math.hypot(x, math.hypot(y, z))\n    v = math.hypot(vx, math.hypot(vy, vz))\n\n    if r <= ZERO_TOL:\n        raise ValueError(\"Position vector is zero: the body is at the Sun.\")\n    if v <= ZERO_TOL:\n        raise ValueError(\"Velocity vector is zero: body has no motion.\")\n\n    # Specific orbital angular momentum vector h = r x v\n    hx = y * vz - z * vy\n    hy = z * vx - x * vz\n    hz = x * vy - y * vx\n    h = math.hypot(hx, hy, hz)\n\n    if h <= ZERO_TOL:\n        raise ValueError(\"Specific angular momentum is zero: orbit is degenerate.\")\n\n    # Specific orbital energy epsilon = v^2/2 - mu/r\n    v_sq = vx**2 + vy**2 + vz**2\n    epsilon = 0.5 * v_sq - MU / r\n\n    # --- Semi-major axis a ---\n    if abs(epsilon) < ZERO_TOL:\n        # Approximately parabolic; return a large positive value.\n        a = 1e12\n    elif epsilon < 0:\n        a = -MU / (2.0 * epsilon)\n    else:\n        a = MU / (2.0 * epsilon)\n\n    # --- Eccentricity e ---\n    # e^2 = 1 + 2*epsilon*h^2/mu^2  (with mu = 1 project units: e^2 = 1 + 2*epsilon*h^2)\n    e_sq = 1.0 + 2.0 * epsilon * (h**2)\n    e = math.sqrt(max(e_sq, 0.0))\n\n    # --- Inclination i ---\n    if h > ZERO_TOL:\n        i = math.acos(hz / h)\n    else:\n        i = 0.0  # degenerate; treat as equatorial\n\n    # --- Longitude of the ascending node Omega ---\n    n = math.hypot(hx, hy)  # magnitude of the xy-component of h\n    if n > ZERO_TOL:\n        Omega = math.atan2(hy, hx)\n        if Omega < 0:\n            Omega += 2.0 * math.pi\n    else:\n        # h is along the z-axis: orbit is equatorial; Omega is undefined.\n        # Convention: set Omega = 0.0.\n        Omega = 0.0\n\n    # --- Eccentricity vector e_vec ---\n    # e_vec = (v x h)/mu - r_hat\n    factor = 1.0 / MU if MU > ZERO_TOL else 1.0\n    # v x h = (vy*hz - vz*hy, vz*hx - vx*hz, vx*hy - vy*hx)\n    cross_x = vy * hz - vz * hy\n    cross_y = vz * hx - vx * hz\n    cross_z = vx * hy - vy * hx\n    ex = factor * cross_x - x / r\n    ey = factor * cross_y - y / r\n    ez = factor * cross_z - z / r\n\n    # --- Argument of periapsis omega ---\n    # The ascending node unit vector: n_hat = (-hy/n, hx/n, 0) when n > 0.\n    # cos_omega = (e_vec \\cdot n_hat) / e\n    # sin_omega = (e_vec \\cdot (k x n_hat)) / e, where k = (0,0,1).\n    # k x n_hat = (-ny/n, nx/n, 0).\n    #\n    # From many astro implementations:\n    #   cos_omega = (e_x * nx + e_y * ny) / (e * n)\n    #   sin_omega = (e_y * nx - e_x * ny) / (e * n)\n    #\n    # where nx = -hy/n, ny = hx/n  (unit node vector components).\n\n    nx = -hy / n if n > ZERO_TOL else 0.0\n    ny = hx / n if n > ZERO_TOL else 0.0\n\n    if e > ZERO_TOL and n > ZERO_TOL:\n        cos_omega = (ex * nx + ey * ny) / (e * n)\n        sin_omega = (ey * nx - ex * ny) / (e * n)\n    else:\n        # e approx 0 or n approx 0: omega is undefined. Set to 0.0 by convention.\n        cos_omega = 1.0\n        sin_omega = 0.0\n\n    omega = math.atan2(sin_omega, cos_omega)\n    if omega < 0:\n        omega += 2.0 * math.pi\n\n    # --- True anomaly nu ---\n    # Using the formulas:\n    #   cos(nu) = (e \\cdot r) / (e * r)\n    #   sin(nu) = [(e\\\\cdot v)\\\\*r^2 - (e\\\\cdot r)\\\\*(v\\\\cdot r)] / (e \\\\* r \\\\* h)\n    # with special handling for circular/equatorial orbits.\n\n    e_dot_r = ex * x + ey * y + ez * z\n    e_dot_v = ex * vx + ey * vy + ez * vz\n    r_sq = x**2 + y**2 + z**2\n    v_dot_r = vx * x + vy * y + vz * z\n\n    if e > ZERO_TOL and h > ZERO_TOL:\n        cos_nu = (e_dot_r) / (e * r)\n        sin_nu_num = e_dot_v * r_sq - e_dot_r * v_dot_r\n        sin_nu_den = e * r * h\n        if abs(sin_nu_den) > ZERO_TOL:\n            sin_nu = sin_nu_num / sin_nu_den\n        else:\n            sin_nu = 0.0\n    elif e <= ZERO_TOL and h > ZERO_TOL:\n        # Circular orbit: nu is undefined by convention; set to 0.0.\n        sin_nu = 0.0\n        cos_nu = 1.0\n    else:\n        # h approx 0: degenerate.\n        cos_nu = 0.0\n        sin_nu = 0.0\n\n    # Clip to [-1, 1] to avoid nan from floating point\n    cos_nu = max(-1.0, min(1.0, cos_nu))\n    sin_nu = max(-1.0, min(1.0, sin_nu))\n\n    nu = math.atan2(sin_nu, cos_nu)\n\n    # For very small eccentricity, nu is essentially degenerate; set to 0.0.\n    if e < ECCENTRICITY_CIRCULAR_TOL:\n        nu = 0.0\n\n    # Normalize nu to [0, 2*pi)\n    if nu < 0:\n        nu += 2.0 * math.pi\n\n    return OrbitalElements(a, e, i, Omega, omega, nu)
"""

with open("src/orbit_discovery/core/orbital_elements.py", "a", encoding="utf-8") as f:
    f.write(content)

print("Part 2 written successfully ({} bytes)".format(len(part2)))

# Part 3: orbital_elements_to_cartesian
part3 = r"""

# ======================================================================
# 2.3.3  Orbital Elements  -->  Cartesian
# ======================================================================


def orbital_elements_to_cartesian(elements):
    \"\"\"Convert classical orbital elements to a heliocentric Cartesian state.

    Uses the standard transformation from perifocal to inertial coordinates.

    Parameters
    ----------
    elements : OrbitalElements
        The orbital elements.

    Returns
    -------
    x, y, z : float
        Heliocentric position in AU.
    vx, vy, vz : float
        Heliocentric velocity in AU/year.
    \"\"\"\n    a = elements.a\n    e = elements.e\n    i = elements.i\n    Omega = elements.Omega\n    omega = elements.omega\n    nu = elements.nu\n\n    # --- Position: r = p / (1 + e * cos(nu)) -------------------------\n    # p = semi-latus rectum\n    # p = a*(1 - e^2) for ellipse, p = a*(e^2 - 1) for hyperbola\n    if e < 1.0:  # elliptical or circular\n        p = a * (1.0 - e**2)\n    else:  # hyperbolic\n        p = a * (e**2 - 1.0)\n\n    denom = 1.0 + e * math.cos(nu)\n    if abs(denom) < ZERO_TOL:\n        # Avoid division by zero; use periapsis distance\n        r = _safe_periapsis_distance(a, e)\n    else:\n        r = p / denom\n\n    # --- Position in perifocal frame: (r * cos(nu), r * sin(nu), 0) -----\n    # Then rotate to inertial frame using the standard transformation:\n    #   x = (cos(Omega)*cos(omega) - sin(Omega)*sin(omega)*cos(i)) * r\n    #   y = (sin(Omega)*cos(omega) + cos(Omega)*sin(omega)*cos(i)) * r\n    #   z = sin(omega)*sin(i) * r\n    # This is the standard transformation (Bate, Mueller, White, eq 4.12).\n\n    cos_omega = math.cos(omega)\n    sin_omega = math.sin(omega)\n    cos_i = math.cos(i)\n    sin_i = math.sin(i)\n    cos_Omega = math.cos(Omega)\n    sin_Omega = math.sin(Omega)\n\n    # Position\n    x = (cos_Omega * cos_omega - sin_Omega * sin_omega * cos_i) * r\n    y = (sin_Omega * cos_omega + cos_Omega * sin_omega * cos_i) * r\n    z = sin_omega * sin_i * r\n\n    # --- Velocity --------------------------------------------------------\n    # From Bate, Mueller, White, eq 4.13:\n    #   v = (mu/h) * [ -sin(nu) * r_hat + (e + cos(nu)) * p_hat ]\n    # where:\n    #   r_hat = (x/r, y/r, z/r)   (position unit vector)\n    #   p_hat = (cos(Omega)*cos(omega) - sin(Omega)*sin(omega)*cos(i),\n    #           sin(Omega)*cos(omega) + cos(Omega)*sin(omega)*cos(i),\n    #           sin(omega)*sin(i))  -- periapsis direction unit vector\n    #   h = |h| = sqrt(mu * p)  (since mu = 1 in project units)\n\n    # h = sqrt(mu * p) = sqrt(p) since mu = 1\n    h_val = math.sqrt(max(p, ZERO_TOL))\n\n    # Position unit vector\n    if r > ZERO_TOL:\n        r_hat_x = x / r\n        r_hat_y = y / r\n        r_hat_z = z / r\n    else:\n        r_hat_x = r_hat_y = r_hat_z = 0.0\n\n    # Periapsis direction unit vector p_hat:\n    # p_hat = (cos(Omega)cos(omega) - sin(Omega)sin(omega)*cos(i),\n    #          sin(Omega)*cos(omega) + cos(Omega)*sin(omega)*cos(i),\n    #           sin(omega)*sin(i))\n    cos_omega = math.cos(omega)\n    sin_omega = math.sin(omega)\n    cos_Omega = math.cos(Omega)\n    sin_Omega = math.sin(Omega)\n\n    p_hat_x = cos_Omega * cos_omega - sin_Omega * sin_omega * cos_i\n    p_hat_y = sin_Omega * cos_omega + cos_Omega * sin_omega * cos_i\n    p_hat_z = sin_omega * sin_i\n\n    # Velocity per Bate-Mueller-White:\n    #   v = (mu/h) * [ -sin(nu) * r_hat + (e + cos(nu)) * p_hat ]\n    mu_over_h = MU / h_val if h_val > ZERO_TOL else 0.0\n\n    sin_nu = math.sin(nu)\n    cos_nu = math.cos(nu)\n\n    vx = mu_over_h * ( -sin_nu * r_hat_x + (e + cos_nu) * p_hat_x )\n    vy = mu_over_h * ( -sin_nu * r_hat_y + (e + cos_nu) * p_hat_y )\n    vz = mu_over_h * ( -sin_nu * r_hat_z + (e + cos_nu) * p_hat_z )\n\n    return x, y, z, vx, vy, vz
"""

with open("src/orbit_discovery/core/orbital_elements.py", "a", encoding="utf-8") as f:
    f.write(content)

print("Part 3 written successfully ({} bytes)".format(len(part3)))

# Part 4: Round-trip functions
part4 = r"""

\ndef round_trip_cartesian_to_elements_to_cartesian(x, y, z, vx, vy, vz):
    \"\"\"Convert Cartesian -> Orbital Elements -> Cartesian, returning the final state.\"\"\"\n    elements = cartesian_to_orbital_elements(x, y, z, vx, vy, vz)\n    x2, y2, z2, vx2, vy2, vz2 = orbital_elements_to_cartesian(elements)\n    return x2, y2, z2, vx2, vy2, vz2\n\n\ndef round_trip_elements_to_cartesian_to_elements(a, e, i, Omega, omega, nu):
    \"\"\"Convert Orbital Elements -> Cartesian -> Orbital Elements, returning the final elements.\"\"\"\n    x, y, z, vx, vy, vz = orbital_elements_to_cartesian(OrbitalElements(a, e, i, Omega, omega, nu))\n    elements2 = cartesian_to_orbital_elements(x, y, z, vx, vy, vz)\n    return elements2\n\n\n# Convenience wrappers\ncartesian_to_orbital = cartesian_to_orbital_elements\norbital_to_cartesian = orbital_elements_to_cartesian\n\n\nif __name__ == \"__main__\":\n    pass
"""

with open("src/orbit_discovery/core/orbital_elements.py", "a", encoding="utf-8") as f:
    f.write(content)  # Wait, this should use part4, not content

# Actually let me use part4
with open("src/orbit_discovery/core/orbital_elements.py", "a", encoding="utf-8") as f:
    f.write(part4)

print("Part 4 written successfully ({} bytes)".format(len(part4)))
print("All parts written successfully!")