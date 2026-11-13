# Diagnostic 4: Long-Span Numerical Stability and Conservation

**Component:** Component 3 — Orbit Estimation and Candidate Orbit Generation
**Phase:** Phase 2 — Trial-Orbit Propagation and Observation Prediction
**Diagnostic:** 4 — Long-Span Numerical Stability and Conservation
**Date:** 2026-11-13
**Constraint:** Read-only. No production source files, generated datasets,
or ground-truth files were modified.

## Objective

Verify that the Component 3 REBOUND/IAS15 trial simulation remains numerically stable over a 10-year integration, conserves total energy and angular momentum of the massive Sun–planet subsystem, produces finite states throughout propagation, and gives consistent results when output sampling cadence and IAS15 tolerance are changed.

## Environment and run configuration

- REBOUND version: 5.2.2
- Integrator: IAS15
- Units: AU, AU/year, years, solar masses
- Gravitational parameter: MU = 39.476926421373 AU^3/yr^2
- Integration duration: 10.0 years
- Gravitational bodies: Sun, Mercury, Venus, Earth, Jupiter
- Planetary initialization: circular, coplanar (e=0, inc=0) from Component 1 BODY_DATA

| Run | IAS15 epsilon | Output sampling interval |
|-----|---------------|--------------------------|
| A | 1e-12 | 0.25 years |
| B | 1e-12 | 0.05 years |
| C | 1e-13 | 0.25 years |

## Asteroid initial state

A single representative finite, non-colliding, massless asteroid test state was used for all three runs:

- Reference frame: heliocentric ecliptic inertial
- Reference epoch: 0.0 years
- Position: (2.5, 0.0, 0.0) AU
- Velocity: (0.0, 3.973760255545, 0.0) AU/yr
- Speed: 3.973760255545 AU/yr
- Heliocentric distance: 2.500000 AU

This is a circular heliocentric orbit at 2.5 AU with tangential velocity sqrt(MU / 2.5).  It is well separated from all planets and avoids collision or singularity configurations.

## Conservation calculations

### Total energy of the massive subsystem

Newtonian kinetic plus pairwise gravitational potential energy using only massive particles (Sun, Mercury, Venus, Earth, Jupiter):

E = (1/2) * sum_i m_i * |v_i|^2  -  G * sum_{i<j} (m_i * m_j / |r_i - r_j|)

The massless asteroid (m = 0) contributes zero kinetic energy and zero potential-energy terms, so REBOUND's sim.energy() returns the massive-subsystem energy as long as the asteroid does not collide with a massive body.  Calculations use the simulation's consistent barycentric (COM-frame) coordinates after sim.move_to_com().

### Total angular momentum of the massive subsystem

L = sum_i m_i * (r_i x v_i)

Again only massive particles are included.  The massless asteroid contributes zero.  The magnitude |L| and its relative change are reported.  Component-wise values are also recorded.

### Relative drift

delta_E(t) = |E(t) - E(0)| / |E(0)|

delta_L(t) = ||L(t)| - |L(0)|| / |L(0)|

Maximum and RMS relative drift are reported over the complete integration interval.  Division by zero is avoided by checking that |E(0)| and |L(0)| are numerically non-negligible.

## Per-run conservation results

### Run A (epsilon=1e-12, interval=0.25 yr)

- Samples: 41
- Reached final epoch: 10.0 years
- All states finite: True

| Quantity | Initial | Final | Max relative drift | RMS relative drift |
|----------|---------|-------|-------------------|--------------------|
| Energy | -3.756071416987e-03 | -3.756071416987e-03 | 4.618e-16 | 2.419e-16 |
| Angular momentum magnitude | 1.370663230317e-02 | 1.370663230317e-02 | 2.531e-16 | 1.439e-16 |

- Minimum massive-body separation: 2.767018e-01 AU

### Run B (epsilon=1e-12, interval=0.05 yr)

- Samples: 201
- Reached final epoch: 10.0 years
- All states finite: True

| Quantity | Initial | Final | Max relative drift | RMS relative drift |
|----------|---------|-------|-------------------|--------------------|
| Energy | -3.756071416987e-03 | -3.756071416987e-03 | 9.237e-16 | 2.690e-16 |
| Angular momentum magnitude | 1.370663230317e-02 | 1.370663230317e-02 | 3.797e-16 | 1.614e-16 |

- Minimum massive-body separation: 2.767018e-01 AU

### Run C (epsilon=1e-13, interval=0.25 yr)

- Samples: 41
- Reached final epoch: 10.0 years
- All states finite: True

| Quantity | Initial | Final | Max relative drift | RMS relative drift |
|----------|---------|-------|-------------------|--------------------|
| Energy | -3.756071416987e-03 | -3.756071416987e-03 | 6.928e-16 | 2.512e-16 |
| Angular momentum magnitude | 1.370663230317e-02 | 1.370663230317e-02 | 3.797e-16 | 1.812e-16 |

- Minimum massive-body separation: 2.767018e-01 AU

## State stability

All Sun, planet, and asteroid states were checked for finiteness at every output sample.  No non-finite values or integration failures were observed.

| Run | All finite | Integration error | Min separation (AU) |
|-----|------------|-------------------|---------------------|
| A | True | None | 2.767018e-01 |
| B | True | None | 2.767018e-01 |
| C | True | None | 2.767018e-01 |

## Cross-run comparisons at common epochs

### Run A vs Run B (same epsilon=1e-12, different output cadence)

- Common epochs: 5 (0.0 to 10.0 years)
- Heliocentric planetary position: max |diff| = 3.974e-13 AU, RMS = 1.423e-13 AU
- Heliocentric planetary velocity: max |diff| = 1.037e-11 AU/yr, RMS = 2.956e-12 AU/yr
- Heliocentric asteroid position: max |diff| = 1.294e-13 AU, RMS = 7.011e-14 AU
- Heliocentric asteroid velocity: max |diff| = 2.058e-13 AU/yr, RMS = 1.116e-13 AU/yr

### Run A vs Run C (same cadence=0.25 yr, epsilon 1e-12 vs 1e-13)

- Common epochs: 41 (0.0 to 10.0 years)
- Heliocentric planetary position: max |diff| = 4.409e-13 AU, RMS = 1.008e-13 AU
- Heliocentric planetary velocity: max |diff| = 1.151e-11 AU/yr, RMS = 1.956e-12 AU/yr
- Heliocentric asteroid position: max |diff| = 1.576e-13 AU, RMS = 5.543e-14 AU
- Heliocentric asteroid velocity: max |diff| = 2.508e-13 AU/yr, RMS = 8.819e-14 AU/yr

## Scientific interpretation

Energy and angular momentum conservation: IAS15 is a non-symplectic adaptive integrator, so small energy and angular momentum drift over long integrations is expected.  The measured drifts above quantify the numerical behavior of the current model over 10 years.

Output sampling cadence: Changing the output sampling interval from 0.25 years (Run A) to 0.05 years (Run B) does not change the underlying integrated trajectory — REBOUND integrates continuously and only the sampling differs.  The A vs B comparison quantifies this: differences at common epochs should be at round-off level.

IAS15 tolerance: Tightening epsilon from 1e-12 (Run A) to 1e-13 (Run C) reduces the per-step integration error.  The A vs C comparison shows whether the tighter tolerance produces a materially different trajectory.

Limitations: The planets use simplified circular/coplanar initialization (e=0, inc=0 from Component 1 BODY_DATA), not realistic ephemerides.  This diagnostic verifies numerical behavior of the current model, not physical realism of the planetary ephemeris.

## Truth separation

- ground_truth.json accessed: NO
- True trajectory data used: NO
- trajectory.csv interpolation used: NO
- Inputs: synthetic test state only

## Conclusion

PASS: The C3 REBOUND/IAS15 trial simulation remains numerically stable over 10 years, all asteroid and planetary states remain finite, no integration failures occurred, and all runs reached the final epoch.  Energy and angular momentum drifts were measured (see per-run results above).  Cross-run comparisons at common epochs show consistency within numerical tolerance.
