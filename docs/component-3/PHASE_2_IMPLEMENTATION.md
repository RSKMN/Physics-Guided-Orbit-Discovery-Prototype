# Component 3 — Phase 2 Implementation: Trial-Orbit Propagation and Observation Prediction

**Status:** Complete
**Date:** 2026-11-13
**Component:** Component 3 — Orbit Estimation and Candidate Orbit Generation
**Gate:** Complete — Phase 2 accepted; Phase 3A design approved and Phase 3B residual calculation implemented, hardened, tested and approved (see PHASE_3_DESIGN.md and tests/test_component3_residuals.py).

---

## 1. Files Created

| File | Purpose |
|------|---------|
| `src/orbit_discovery/component3/dynamics.py` | REBOUND-based forward propagation for trial orbits |
| `src/orbit_discovery/component3/observation_model.py` | Observer geometry + apparent RA/Dec prediction |
| `tests/test_component3_phase2.py` | Focused Phase 2 test suite (24 tests) |
| `docs/component-3/PHASE_2_IMPLEMENTATION.md` | This document |

No existing files were modified.

## 2. Dynamics Architecture

### `build_trial_simulation(bodies, integrator_epsilon)`

Constructs a fresh REBOUND simulation matching Component 1's planetary model:

- Imports `BODY_DATA` from `configurable_simulator` (no duplication of planetary constants)
- Sun at origin (`m=1.0`)
- Planets: circular, coplanar (`e=0`, `inc=0`), matching C1's `BODY_DATA` masses and semi-major axes
- Massless asteroid placeholder as last particle (`m=0.0`)
- `sim.move_to_com()` applied
- IAS15 integrator, `epsilon = 1e-12`
- Units: (`yr`, `AU`, `Msun`)

### `propagate_trial_state(state, epochs_years, bodies)`

Propagates a trial asteroid state to multiple epochs:

- Built once, epochs integrated sequentially in sorted order
- Results returned in original input order
- Heliocentric (Sun-relative) Cartesian state at each epoch
- Validates input state (`OrbitState.validate()`) and epochs (>= 0, finite)

### `propagate_trial_state_single(state, target_time_years, bodies)`

Convenience wrapper for a single epoch.

## 3. Planetary Reconstruction

Planetary constants are **imported from Component 1** (`configurable_simulator.BODY_DATA`), not duplicated:

| Body | Mass (Msun) | Semi-major axis (AU) |
|------|-------------|----------------------|
| Mercury | 1.6601e-7 | 0.3871 |
| Venus | 2.4478e-6 | 0.7233 |
| Earth | 3.0035e-6 | 1.0000 |
| Jupiter | 9.5458e-4 | 5.2028 |

Default body set: `["Sun", "Mercury", "Venus", "Earth", "Jupiter"]` (matches C1 standard).

All planets use circular, coplanar initial conditions at perihelion on the +x axis, exactly as C1's `build_simulation()`.

The asteroid is treated as massless (`m=0.0`) and its state is supplied as heliocentric Cartesian coordinates. After `move_to_com()`, the supplied heliocentric state is offset by the Sun's COM-frame position/velocity.

## 4. Observer Reconstruction

### `reconstruct_observer_config(metadata)`

Extracts `ObserverConfig` from observation dataset metadata:

- `orbital_radius_au` (default: 1.0)
- `orbital_period_years` (default: 1.0)
- `initial_phase_deg` (default: 90.0)

These match Component 2's default Earth-like circular observer.

### `get_obliquity_deg(metadata)`

Extracts ecliptic obliquity from `metadata["coordinates"]["obliquity_deg"]` (default: 23.43928°).

Observer **velocity is not calculated** because Component 2's sky-coordinate model does not require it (no light-time or aberration corrections).

## 5. Forward-Model API

### `predict_apparent_coordinates(asteroid_states, epochs_years, observer_config, obliquity_deg)`

Pure observation prediction from propagated states:

1. Observer positions at epochs (Component 2's `calculate_observer_positions`)
2. Relative position vectors (asteroid − observer)
3. Line-of-sight unit vectors (`calculate_line_of_sight`)
4. Ecliptic-to-equatorial rotation (`calculate_sky_coordinates`)
5. Returns RA normalized to [0, 360), Dec clipped to [-90, 90]

### `predict_from_orbit_state(state, epochs_years, observer_config, obliquity_deg, bodies)`

End-to-end forward model combining propagation + observation prediction. Returns `(propagation_results, predictions)`.

### Prediction entry schema

| Field | Unit | Description |
|-------|------|-------------|
| `epoch_years` | year | Observation epoch |
| `x_au, y_au, z_au` | AU | Asteroid heliocentric position |
| `vx_au_per_year, vy_au_per_year, vz_au_per_year` | AU/year | Asteroid heliocentric velocity |
| `observer_x_au, observer_y_au, observer_z_au` | AU | Observer heliocentric position |
| `ra_deg` | deg | Predicted RA [0, 360) |
| `dec_deg` | deg | Predicted Dec [-90, 90] |

## 6. Units and Frames

| Quantity | Unit | Frame |
|----------|------|-------|
| Position | AU | Heliocentric ecliptic inertial |
| Velocity | AU/year | Heliocentric ecliptic inertial |
| Time | years | Elapsed simulation time (reference epoch = 0.0) |
| RA | degrees | Equatorial, [0, 360) |
| Dec | degrees | Equatorial, [-90, 90] |
| Gravitational parameter | AU³/yr² | REBOUND sim.G = 39.476926421373 (M_sun = 1.0) |

No light-time correction, aberration, or relativistic effects.

## 7. Numerical Tolerances

- IAS15 integrator epsilon: `1e-12` (matches C1)
- Epoch validation: `t >= 0`, finite
- State validation: all six components finite
- RA normalization: `np.mod(ra, 360.0)`
- Dec clipping: `np.clip(dec, -90, 90)`
- Time consistency (loader): `time_days ≈ time_years × 365.25` (atol=1e-8)

## 8. Test Results

### Focused Phase 2 tests

```powershell
python tests/test_component3_phase2.py -v
```

**Result:** 24 passed, 0 failed, 0 errors

| Category | Count |
|----------|-------|
| Dynamics | 10 |
| Observation model | 9 |
| Integration | 3 |
| Performance | 1 |
| **Total** | **23** |

### Full regression suite

```powershell
python -m pytest tests/ -q
```

**Result:** 217 passed, 1 deselected, 0 failures — no regressions

### Performance measurement

| Metric | Value |
|--------|-------|
| 262 epochs (~5 years at 7-day cadence) | 0.015 s |
| Per-epoch cost | 0.056 ms/epoch |
| Threshold (soft) | < 5.0 s |

Well within acceptable limits for repeated optimization calls.

## 9. Known Limitations

- Component 3 does not implement least-squares fitting, residual weighting, candidate generation, or covariance (Phase 3+ work).
- Observer state is reconstructed from metadata parameters, not stored per-observation in the CSV.
- No absolute calendar epoch (`epoch_jd_tdb = null`); time remains elapsed simulation time.
- Planetary masses/initial conditions come from Component 1's hardcoded `BODY_DATA`.
- Observer velocity not used (matches Component 2's simplified model).

## 10. Restrictions Honored

- No least-squares fitting implemented
- No residual weighting implemented
- No candidate generation implemented
- No covariance implemented
- Component 2 datasets unchanged
- Existing CLI commands unchanged
- Phase 3 not started
- No unnecessary dependencies added
- No ground truth access in production code
- `propagate_from_trajectory()` not used as forward propagation mechanism
- No interpolation of true asteroid trajectory
- Component 1 simulation algorithm unchanged

Phase 2 is complete. Awaiting approval to proceed to Phase 3.
