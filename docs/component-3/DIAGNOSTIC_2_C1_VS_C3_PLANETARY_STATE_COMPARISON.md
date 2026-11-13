# Diagnostic 2: C1 vs C3 Planetary-State Numerical Comparison

**Component:** Component 3 — Orbit Estimation and Candidate Orbit Generation
**Phase:** Phase 2 — Trial-Orbit Propagation and Observation Prediction
**Diagnostic:** 2 — C1 vs C3 planetary-state numerical comparison
**Date:** 2026-11-13
**Constraint:** Read-only. No production source files, generated datasets,
or ground-truth files were modified.

## Objective

Determine whether the planetary initial conditions and propagated planetary states in the C3 trial simulation numerically match the authoritative C1 simulator.

## Configuration

| Parameter | Value |
|-----------|-------|
| Bodies | Sun, Mercury, Venus, Earth, Jupiter |
| Planets compared | Mercury, Venus, Earth, Jupiter |
| Units | yr, AU, Msun |
| Integrator | IAS15 |
| Integrator epsilon | 1e-12 |
| Epochs (yr) | [0.0, 0.25, 0.5, 1.0, 2.0, 5.0] |

### C1 config (in-memory)
```json
{"simulation_name": "c1_vs_c3_comparison", "gravitational_bodies": ["Sun", "Mercury", "Venus", "Earth", "Jupiter"], "initial_conditions": {"mode": "orbital_elements", "semi_major_axis_au": 2.5, "eccentricity": 0.2, "inclination_deg": 0.0, "longitude_ascending_node_deg": 0.0, "argument_periapsis_deg": 0.0, "mean_anomaly_deg": 0.0}, "simulation": {"integrator": "ias15", "integrator_epsilon": 1e-12}}
```

Note: Both C1 and C3 initialize planets as circular, coplanar (e=0, inc=0) using masses and semi-major axes from the shared BODY_DATA, with remaining angular elements defaulting to 0 in REBOUND. Only C1's asteroid has configurable orbital elements (via config['initial_conditions']); C3 sets the asteroid state programmatically via _set_asteroid_state_heliocentric. There is no configuration-driven discrepancy between C1 and C3 for the planets.

## Initial-condition comparison at t=0

## Initial conditions at t=0 (C1 − C3, heliocentric)

| Planet | Epoch (yr) | Max |pos|diff| (AU) | RMS |pos|diff| (AU) | Max |vel|diff| (AU/yr) | RMS |vel|diff| (AU/yr) |
|--------|------------|---------------------|---------------------|-------------------------|-------------------------|
| Mercury | 0.0 | 0.000e+00 | 0.000e+00 | 0.000e+00 | 0.000e+00 |
| Venus | 0.0 | 0.000e+00 | 0.000e+00 | 0.000e+00 | 0.000e+00 |
| Earth | 0.0 | 0.000e+00 | 0.000e+00 | 0.000e+00 | 0.000e+00 |
| Jupiter | 0.0 | 0.000e+00 | 0.000e+00 | 0.000e+00 | 0.000e+00 |

## Propagation comparison at t>0

## Propagation at t>0 (C1 − C3, heliocentric)

| Planet | Epoch (yr) | Max |pos|diff| (AU) | RMS |pos|diff| (AU) | Max |vel|diff| (AU/yr) | RMS |vel|diff| (AU/yr) |
|--------|------------|---------------------|---------------------|-------------------------|-------------------------|
| Mercury | 0.25 | 0.000e+00 | 0.000e+00 | 0.000e+00 | 0.000e+00 |
| Mercury | 0.5 | 0.000e+00 | 0.000e+00 | 0.000e+00 | 0.000e+00 |
| Mercury | 1.0 | 0.000e+00 | 0.000e+00 | 0.000e+00 | 0.000e+00 |
| Mercury | 2.0 | 0.000e+00 | 0.000e+00 | 0.000e+00 | 0.000e+00 |
| Mercury | 5.0 | 0.000e+00 | 0.000e+00 | 0.000e+00 | 0.000e+00 |
| Venus | 0.25 | 0.000e+00 | 0.000e+00 | 0.000e+00 | 0.000e+00 |
| Venus | 0.5 | 0.000e+00 | 0.000e+00 | 0.000e+00 | 0.000e+00 |
| Venus | 1.0 | 0.000e+00 | 0.000e+00 | 0.000e+00 | 0.000e+00 |
| Venus | 2.0 | 0.000e+00 | 0.000e+00 | 0.000e+00 | 0.000e+00 |
| Venus | 5.0 | 0.000e+00 | 0.000e+00 | 0.000e+00 | 0.000e+00 |
| Earth | 0.25 | 0.000e+00 | 0.000e+00 | 0.000e+00 | 0.000e+00 |
| Earth | 0.5 | 0.000e+00 | 0.000e+00 | 0.000e+00 | 0.000e+00 |
| Earth | 1.0 | 0.000e+00 | 0.000e+00 | 0.000e+00 | 0.000e+00 |
| Earth | 2.0 | 0.000e+00 | 0.000e+00 | 0.000e+00 | 0.000e+00 |
| Earth | 5.0 | 0.000e+00 | 0.000e+00 | 0.000e+00 | 0.000e+00 |
| Jupiter | 0.25 | 0.000e+00 | 0.000e+00 | 0.000e+00 | 0.000e+00 |
| Jupiter | 0.5 | 0.000e+00 | 0.000e+00 | 0.000e+00 | 0.000e+00 |
| Jupiter | 1.0 | 0.000e+00 | 0.000e+00 | 0.000e+00 | 0.000e+00 |
| Jupiter | 2.0 | 0.000e+00 | 0.000e+00 | 0.000e+00 | 0.000e+00 |
| Jupiter | 5.0 | 0.000e+00 | 0.000e+00 | 0.000e+00 | 0.000e+00 |

## Aggregate results

| Phase | Quantity | Max |diff| | RMS |
|-------|----------|---------|---------|
| Initial conditions (t=0) | Position (AU) | 0.000e+00 | 0.000e+00 |
| Initial conditions (t=0) | Velocity (AU/yr) | 0.000e+00 | 0.000e+00 |
| Propagation (t>0) | Position (AU) | 0.000e+00 | 0.000e+00 |
| Propagation (t>0) | Velocity (AU/yr) | 0.000e+00 | 0.000e+00 |

## Configuration-limitation check

- Both C1 `build_simulation()` and C3 `build_trial_simulation()` initialize planets identically: masses and semi-major axes from the shared `BODY_DATA`, `e=0.0`, `inc=0.0`, with remaining angular elements defaulting to 0 in REBOUND.
- C1's `config['initial_conditions']` configures the **asteroid's** orbital elements (semi-major axis, eccentricity, inclination, longitude of ascending node, argument of periapsis, mean anomaly), not the planets'. C3 sets the asteroid state programmatically via `_set_asteroid_state_heliocentric`.
- There is no configuration-driven discrepancy between C1 and C3 for the planets; their initialization is numerically identical.

## Truth separation

- trajectory.csv interpolation used: NO
- ground_truth.json accessed: NO
- Inputs: C1 config + C3 default bodies only

## Conclusion

- Initial conditions match C1 (tol 1e-09): True
- Propagated states match C1 (tol 1e-09): True
PASS: C3 planetary initial conditions and propagated states match C1 numerically within floating-point tolerance for the standard circular-coplanar configuration.
