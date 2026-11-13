# Diagnostic 3: Initial-State Preservation

**Component:** Component 3 — Orbit Estimation and Candidate Orbit Generation
**Phase:** Phase 2 — Trial-Orbit Propagation and Observation Prediction
**Diagnostic:** 3 — Initial-State Preservation
**Date:** 2026-11-13
**Constraint:** Read-only. No production source files, generated datasets,
or ground-truth files were modified.

## Objective

Verify that C3 preserves a supplied six-dimensional heliocentric asteroid state (position and velocity in AU/AU/year, heliocentric ecliptic inertial frame, reference epoch 0.0 years) when inserting it into the trial REBOUND simulation.

## Methodology

1. Built a fresh C3 trial simulation via build_trial_simulation().
2. Inserted the supplied asteroid state using _set_asteroid_state_heliocentric().
3. Extracted the heliocentric asteroid state immediately, before integration, using _get_asteroid_state_heliocentric().
4. Compared the extracted state with the supplied state.
5. Reported position and velocity errors independently.
6. Tested through the public propagate_trial_state() API at epoch 0.0.
7. Performed a short propagation to 0.001 years (finite check only, not exact-state preservation).

## Implementation under test

- `build_trial_simulation()` — src/orbit_discovery/component3/dynamics.py
- `_set_asteroid_state_heliocentric()` — src/orbit_discovery/component3/dynamics.py
- `_get_asteroid_state_heliocentric()` — src/orbit_discovery/component3/dynamics.py
- `propagate_trial_state()` — src/orbit_discovery/component3/dynamics.py
- `propagate_trial_state_single()` — src/orbit_discovery/component3/dynamics.py

The simulation is built with the Sun (particle index 0), planets from Component 1's BODY_DATA, and a massless asteroid placeholder as the last particle. After sim.move_to_com(), the supplied heliocentric state is applied as Sun-position + offset and Sun-velocity + offset. Extraction subtracts the Sun's COM-frame state to recover heliocentric coordinates.

## Test states

| State | Position (AU) | Velocity (AU/yr) | Heliocentric distance (AU) |
|-------|---------------|------------------|----------------------------|
| 0 | (+2.500000, +0.000000, +0.000000) | (+0.000000, +3.973760, +0.000000) | 2.500000 |
| 1 | (+2.000000, +0.000000, +0.300000) | (+0.000000, +4.442799, +0.050000) | 2.022375 |
| 2 | (+1.800000, +0.600000, -0.250000) | (-0.100000, +4.558216, +0.080000) | 1.913766 |
| 3 | (+3.000000, -1.200000, +0.400000) | (+0.050000, +3.512341, -0.060000) | 3.255764 |
| 4 | (-2.000000, +1.500000, +0.000000) | (+0.100000, -3.973760, +0.000000) | 2.500000 |

States include: z=0 and vz=0; non-zero z and vz; different positions and velocity directions; different heliocentric distances; negative coordinate and velocity components. All values are finite and avoid collision or singularity configurations.

## Tolerances

- Position max absolute error tolerance: 1.000e-12 AU
- Velocity max absolute error tolerance: 1.000e-12 AU/yr

## Test 1: Insertion round-trip (extract before integration)

| State | Pos max |err| (AU) | Pos norm (AU) | Pos PASS | Vel max |err| (AU/yr) | Vel norm (AU/yr) | Vel PASS |
|-------|----------------|----------------|----------|-------------------|------------------|----------|
| 0 | 0.000e+00 | 0.000e+00 | Yes | 0.000e+00 | 0.000e+00 | Yes |
| 1 | 0.000e+00 | 0.000e+00 | Yes | 0.000e+00 | 0.000e+00 | Yes |
| 2 | 0.000e+00 | 0.000e+00 | Yes | 0.000e+00 | 0.000e+00 | Yes |
| 3 | 0.000e+00 | 0.000e+00 | Yes | 0.000e+00 | 0.000e+00 | Yes |
| 4 | 0.000e+00 | 0.000e+00 | Yes | 0.000e+00 | 0.000e+00 | Yes |

### Detailed state-by-state results (Test 1)

#### State 0

- Input position:  (2.500000000000, 0.000000000000, 0.000000000000) AU
- Input velocity:  (0.000000000000, 3.973760255545, 0.000000000000) AU/yr
- Extracted position:  (2.500000000000, 0.000000000000, 0.000000000000) AU
- Extracted velocity:  (0.000000000000, 3.973760255545, 0.000000000000) AU/yr
- Position max |err|: 0.000e+00 AU (tolerance 1.000e-12)
- Position error norm: 0.000e+00 AU
- Velocity max |err|: 0.000e+00 AU/yr (tolerance 1.000e-12)
- Velocity error norm: 0.000e+00 AU/yr

#### State 1

- Input position:  (2.000000000000, 0.000000000000, 0.300000000000) AU
- Input velocity:  (0.000000000000, 4.442799028843, 0.050000000000) AU/yr
- Extracted position:  (2.000000000000, 0.000000000000, 0.300000000000) AU
- Extracted velocity:  (0.000000000000, 4.442799028843, 0.050000000000) AU/yr
- Position max |err|: 0.000e+00 AU (tolerance 1.000e-12)
- Position error norm: 0.000e+00 AU
- Velocity max |err|: 0.000e+00 AU/yr (tolerance 1.000e-12)
- Velocity error norm: 0.000e+00 AU/yr

#### State 2

- Input position:  (1.800000000000, 0.600000000000, -0.250000000000) AU
- Input velocity:  (-0.100000000000, 4.558215626258, 0.080000000000) AU/yr
- Extracted position:  (1.800000000000, 0.600000000000, -0.250000000000) AU
- Extracted velocity:  (-0.100000000000, 4.558215626258, 0.080000000000) AU/yr
- Position max |err|: 0.000e+00 AU (tolerance 1.000e-12)
- Position error norm: 0.000e+00 AU
- Velocity max |err|: 0.000e+00 AU/yr (tolerance 1.000e-12)
- Velocity error norm: 0.000e+00 AU/yr

#### State 3

- Input position:  (3.000000000000, -1.200000000000, 0.400000000000) AU
- Input velocity:  (0.050000000000, 3.512341029382, -0.060000000000) AU/yr
- Extracted position:  (3.000000000000, -1.200000000000, 0.400000000000) AU
- Extracted velocity:  (0.050000000000, 3.512341029382, -0.060000000000) AU/yr
- Position max |err|: 0.000e+00 AU (tolerance 1.000e-12)
- Position error norm: 0.000e+00 AU
- Velocity max |err|: 0.000e+00 AU/yr (tolerance 1.000e-12)
- Velocity error norm: 0.000e+00 AU/yr

#### State 4

- Input position:  (-2.000000000000, 1.500000000000, 0.000000000000) AU
- Input velocity:  (0.100000000000, -3.973760255545, 0.000000000000) AU/yr
- Extracted position:  (-2.000000000000, 1.500000000000, 0.000000000000) AU
- Extracted velocity:  (0.100000000000, -3.973760255545, 0.000000000000) AU/yr
- Position max |err|: 0.000e+00 AU (tolerance 1.000e-12)
- Position error norm: 0.000e+00 AU
- Velocity max |err|: 0.000e+00 AU/yr (tolerance 1.000e-12)
- Velocity error norm: 0.000e+00 AU/yr

## Test 2: Public API at epoch 0.0 (propagate_trial_state)

| State | Pos max |err| (AU) | Pos PASS | Vel max |err| (AU/yr) | Vel PASS |
|-------|----------------|----------|-------------------|----------|
| 0 | 0.000e+00 | Yes | 0.000e+00 | Yes |
| 1 | 0.000e+00 | Yes | 0.000e+00 | Yes |
| 2 | 0.000e+00 | Yes | 0.000e+00 | Yes |
| 3 | 0.000e+00 | Yes | 0.000e+00 | Yes |
| 4 | 0.000e+00 | Yes | 0.000e+00 | Yes |

## Test 3: Short propagation to 0.001 years (finite check only)

| State | Finite | Position (AU) | Velocity (AU/yr) |
|-------|--------|---------------|------------------|
| 0 | True | (+2.499997, +0.003974, +0.000000) | (-0.006313, +3.973755, +0.000000) |
| 1 | True | (+1.999995, +0.004443, +0.300049) | (-0.009543, +4.442788, +0.048568) |
| 2 | True | (+1.799895, +0.604557, -0.249919) | (-0.110126, +4.554826, +0.081407) |
| 3 | True | (+3.000048, -1.196487, +0.399940) | (+0.046570, +3.513715, -0.060459) |
| 4 | True | (-1.999897, +1.496024, +0.000000) | (+0.105059, -3.977551, +0.000000) |

## Aggregate results

- Aggregate position max |err|: 0.000e+00 AU (tolerance 1.000e-12 AU)
- Aggregate position error norm: 0.000e+00 AU
- Aggregate velocity max |err|: 0.000e+00 AU/yr (tolerance 1.000e-12 AU/yr)
- Aggregate velocity error norm: 0.000e+00 AU/yr
- Aggregate API position max |err|: 0.000e+00 AU (tolerance 1.000e-12 AU)
- Aggregate API velocity max |err|: 0.000e+00 AU/yr (tolerance 1.000e-12 AU/yr)
- All insertion round-trip tests passed: True
- All short-propagation states finite: True

## Truth separation

- ground_truth.json accessed: NO
- True trajectory data used: NO
- trajectory.csv interpolation used: NO
- Inputs: synthetic test states only

## Conclusion

PASS: C3 preserves supplied initial heliocentric asteroid states within tolerance (position 1.000e-12 AU, velocity 1.000e-12 AU/yr) for all test states, and the public propagate_trial_state() API returns the original state at epoch 0.0. Short propagation to 0.001 years remains finite.
