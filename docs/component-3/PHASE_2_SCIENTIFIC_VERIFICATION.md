# Component 3 — Phase 2 Scientific Verification Audit

**Component:** Component 3 — Orbit Estimation and Candidate Orbit Generation
**Phase:** Phase 2 — Trial-Orbit Propagation and Observation Prediction
**Date:** 2026-11-13
**Status:** Awaiting Phase 3 gate decision
**Constraint:** READ-ONLY audit. No production source files, tests, or datasets were modified.

---

## 1. Scope and read-only boundary

This audit is a scientific verification of the Component 3 forward model
(trial-orbit propagation + apparent RA/Dec prediction) performed before
approving progression to Phase 3 (orbit fitting / candidate generation).

**What was inspected (source-code reading only):**

| Item | Source | Method |
|------|--------|--------|
| Component 1 simulation builder and planetary constants | `src/configurable_simulator.py` (`build_simulation`, `BODY_DATA`) | Read-only source inspection |
| Component 3 dynamics module | `src/orbit_discovery/component3/dynamics.py` (`build_trial_simulation`, `propagate_trial_state`, `_set_asteroid_state_heliocentric`, `_get_asteroid_state_heliocentric`) | Read-only source inspection |
| Component 3 observation model | `src/orbit_discovery/component3/observation_model.py` (`predict_apparent_coordinates`, `predict_from_orbit_state`, `reconstruct_observer_config`, `get_obliquity_deg`) | Read-only source inspection |
| Component 2 observer geometry and frame conversion | `src/orbit_discovery/component2_observations/observer.py` (`calculate_sky_coordinates`, `calculate_observer_positions`, `calculate_line_of_sight`) | Read-only source inspection |
| Component 2 frames module | `src/orbit_discovery/component2_observations/frames.py` (`ecliptic_to_equatorial`, `calculate_ra_dec`) | Read-only source inspection |
| Component 3 Phase 1 models and loader | `src/orbit_discovery/component3/models.py`, `src/orbit_discovery/component3/loader.py` | Read-only source inspection |
| Focused test suites | `tests/test_component3_phase1.py`, `tests/test_component3_phase2.py` | Read-only source inspection + documented execution results |

**What was NOT done:**
- No execution of diagnostic Python scripts.
- No modification of `src/`, `tests/`, `data/`, `configs/`, or any generated dataset.
- No corrections applied to the declination bug or any other finding.

The distinction below marks each finding as either **(source inspection)** — derived from reading source code — or **(executed tests)** — derived from the documented test runs.

---

## 2. C1/C3 planetary initialization consistency — CONDITIONAL PASS

### 2.1 Component 1 initialization (source inspection)

`src/configurable_simulator.py:42` — `build_simulation(config)`:

- `sim.units = ("yr", "AU", "Msun")`; Sun added first at origin (`m=1.0`).
- Planets added from `BODY_DATA` (`configurable_simulator.py:17-26`) with `m=body["mass"]`, `a=body["a"]`, `e=0.0`, `inc=0.0`. Remaining orbital-element angles (`Omega`, `omega`, `M`) default to 0 in REBOUND, placing planets at perihelion on the +x axis.
- The massless asteroid is then added from `config["initial_conditions"]` orbital elements, which may be non-circular or inclined depending on the config.
- `sim.move_to_com()` is called after all particles (Sun, planets, asteroid) are added.
- IAS15 integrator, epsilon from config `simulation.integrator_epsilon`.

`BODY_DATA` (configurable_simulator.py:17-26):

| Body | Mass (Msun) | Semi-major axis (AU) |
|------|-------------|----------------------|
| Mercury | 1.6601e-7 | 0.3871 |
| Venus | 2.4478e-6 | 0.7233 |
| Earth | 3.0035e-6 | 1.0000 |
| Mars | 3.2272e-7 | 1.5237 |
| Jupiter | 9.5458e-4 | 5.2028 |
| Saturn | 2.8581e-4 | 9.5388 |
| Uranus | 4.3662e-5 | 19.1914 |
| Neptune | 5.1514e-5 | 30.0611 |

### 2.2 Component 3 initialization (source inspection)

`src/orbit_discovery/component3/dynamics.py:36-97` — `build_trial_simulation(bodies=None, integrator_epsilon=1e-12)`:

- Same units (`yr`, `AU`, `Msun`); Sun added first at origin (`m=1.0`).
- Planets added from the **same imported** `configurable_simulator.BODY_DATA` (no duplication) with `m=body["mass"]`, `a=body["a"]`, `e=0.0`, `inc=0.0`. Same default element angles as C1.
- A massless asteroid placeholder (`m=0.0`) is added as the last particle; its state is set afterward by the caller.
- `sim.move_to_com()` called; IAS15 with `epsilon = 1e-12`.
- Default body set: `["Sun", "Mercury", "Venus", "Earth", "Jupiter"]` (dynamics.py:29), matching C1's standard synthetic scenario.

### 2.3 Consistency verdict — CONDITIONAL PASS

**(source inspection)** For the **standard circular-coplanar configuration** (C1 config using `e=0`, `inc=0`, default element angles), C3's planetary initial conditions are **numerically identical** to C1's:
- Same `BODY_DATA` masses and semi-major axes (imported, not duplicated).
- Same `e=0.0, inc=0.0`, same default element angles.
- Same units, same `sim.G` (REBOUND default ≈ 39.476926421373), same integrator (IAS15, ε=1e-12).
- Same heliocentric extraction convention (Sun-relative state).

**(source inspection)** The match is **conditional**:
- C1 reads planetary orbits from a JSON config and supports non-zero `inclination_deg`, `longitude_ascending_node_deg`, `argument_periapsis_deg`, and `mean_anomaly_deg`.
- C3 **hardcodes** `e=0.0, inc=0.0` and does not accept `Omega`, `omega`, or `M` overrides.
- Therefore C3 reproduces C1 exactly only when C1's config uses circular, coplanar, default-angle initial conditions. For a non-circular or inclined C1 config, C3's planetary initial conditions would differ.

**Recommendation:** Treat C1/C3 planetary consistency as CONDITIONAL PASS for the standard synthetic scenario; document the hardcoded-orbit limitation as a known scope boundary for Phase 3.

---

## 3. Heliocentric asteroid insertion and extraction logic (source inspection)

### 3.1 Insertion — `_set_asteroid_state_heliocentric`

`src/orbit_discovery/component3/dynamics.py:100-125`. Called after `sim.move_to_com()`:

```python
sun = sim.particles[sun_index]          # index 0
asteroid = sim.particles[asteroid_index]  # last particle

asteroid.x = sun.x + rx
asteroid.y = sun.y + ry
asteroid.z = sun.z + rz
asteroid.vx = sun.vx + vx
asteroid.vy = sun.vy + vy
asteroid.vz = sun.vz + vz
```

The supplied 6D state `(rx, ry, rz, vx, vy, vz)` is interpreted as **heliocentric (Sun-relative)** Cartesian coordinates at the reference epoch (t = 0.0 yr). The Sun's current COM-frame position/velocity is added to place the particle correctly in the COM frame. Because the asteroid is massless, this placement does not perturb the COM.

### 3.2 Extraction — `_get_asteroid_state_heliocentric`

`src/orbit_discovery/component3/dynamics.py:128-146`:

```python
return {
    "epoch_years": float(epoch_years),
    "x_au": float(asteroid.x - sun.x),
    "y_au": float(asteroid.y - sun.y),
    "z_au": float(asteroid.z - sun.z),
    "vx_au_per_year": float(asteroid.vx - sun.vx),
    "vy_au_per_year": float(asteroid.vy - sun.vy),
    "vz_au_per_year": float(asteroid.vz - sun.vz),
}
```

This mirrors C1's trajectory extraction exactly (`generate_trajectory`, `configurable_simulator.py:197-202`):
`x_au = asteroid.x - sun.x`, etc.

### 3.3 Propagation flow

`propagate_trial_state` (dynamics.py:149-238):
- Builds a fresh simulation via `build_trial_simulation`.
- Sets the asteroid state heliocentrically at t = 0.
- Integrates sequentially through sorted epochs with `sim.integrate(t)`.
- Returns results in original input order, each entry containing `epoch_years`, `x_au`, `y_au`, `z_au`, `vx_au_per_year`, `vy_au_per_year`, `vz_au_per_year`.
- Validates input state (`OrbitState.validate()`: six finite components) and epochs (`t >= 0`, finite).

### 3.4 Verdict

**(source inspection)** PASS — the heliocentric insertion/extraction pair is internally consistent, matches C1's extraction convention, correctly handles the massless-asteroid COM semantics, and uses validated inputs.

---

## 4. COM transformation ordering (source inspection)

### 4.1 Component 1

`build_simulation` (configurable_simulator.py:96): Sun + planets + asteroid are all added, then `sim.move_to_com()` is called once. Trajectory output subsequently converts COM-frame states to heliocentric by subtracting the Sun's COM-frame state at each epoch.

### 4.2 Component 3

`build_trial_simulation` (dynamics.py:93): Sun + planets + massless asteroid placeholder are added, then `sim.move_to_com()` is called. The asteroid state is set afterward via `_set_asteroid_state_heliocentric`.

### 4.3 Why the massless asteroid does not affect the COM

**(source inspection)** In both components the asteroid has `m = 0.0`. REBOUND's `move_to_com()` computes the COM as the mass-weighted mean of particle positions and velocities. A massless particle contributes zero to the mass-weighted sums, so:
- Calling `move_to_com()` before or after setting the massless asteroid's state yields the same COM for the Sun + planets.
- Setting a massless particle's position/velocity does not shift the COM.

**(source inspection)** PASS — the COM ordering is correct in both components, and the massless-asteroid handling is physically sound.

---

## 5. Coordinate transformation assessment — FAIL/BLOCKER (declination denominator bug)

### 5.1 The bug (source inspection)

`src/orbit_discovery/component2_observations/observer.py:328-329` — `calculate_sky_coordinates()`:

```python
# Equatorial Cartesian components (correct)
x_eq = x
y_eq = y * math.cos(obliquity) - z * math.sin(obliquity)
z_eq = y * math.sin(obliquity) + z * math.cos(obliquity)

# RA uses equatorial components — correct
ra_rad = np.arctan2(y_eq, x_eq)

# Declination uses ECLIPTIC denominator — BUG
dec_rad = np.arctan2(z_eq, np.sqrt(x**2 + y**2))
```

Line 328 computes declination as `atan2(z_eq, sqrt(x**2 + y**2))`. The numerator `z_eq` is the **equatorial** Z component, but the denominator `sqrt(x**2 + y**2)` uses the **ecliptic** X and Y components (unrotated), not the equatorial radial distance `sqrt(x_eq**2 + y_eq**2)`.

### 5.2 Correct equatorial declination formula

**(source inspection)** The correct formula, as implemented in C2's own `frames.calculate_ra_dec` (`src/orbit_discovery/component2_observations/frames.py:64`):

```python
dec_rad = np.arctan2(z, np.sqrt(x**2 + y**2))
```

where `x, y, z` are the **equatorial** components (i.e., `x_eq, y_eq, z_eq` after rotation). Equivalently, within `calculate_sky_coordinates`:

```python
dec_rad = np.arctan2(z_eq, np.sqrt(x_eq**2 + y_eq**2))
```

### 5.3 Impact on Component 3

**(source inspection)** Component 3's `predict_apparent_coordinates` (observation_model.py:227-229) calls Component 2's `calculate_sky_coordinates`, so C3 inherits this bug directly:

- **RA is unaffected**: `ra_rad = np.arctan2(y_eq, x_eq)` uses equatorial components correctly (observer.py:324).
- **Declination is wrong**: the ecliptic denominator introduces an error that grows with ecliptic latitude. Prior analysis in this session estimated Dec errors of up to ~1.748° in affected geometries, while RA matches to within ~5.7e-14°.

### 5.4 Verdict — FAIL / BLOCKER

**(source inspection)** FAIL. The declination computation in `observer.py:328-329` is scientifically incorrect. Because Component 3's forward model depends on this function, predicted Dec values are unreliable and cannot be used for orbit estimation without correction.

**Required correction (read-only — documented, not applied):**
Change `observer.py:328` from:
```python
dec_rad = np.arctan2(z_eq, np.sqrt(x**2 + y**2))
```
to:
```python
dec_rad = np.arctan2(z_eq, np.sqrt(x_eq**2 + y_eq**2))
```

This is a Component 2 source-file change, outside Component 3's directory, and is explicitly barred by the read-only constraint of this audit. It must be corrected and re-verified before Phase 3 can proceed.

---

## 6. Truth-data separation findings (source inspection)

### 6.1 Component 3 loader

`src/orbit_discovery/component3/loader.py` — `load_dataset_for_estimation(csv_path)`:
- Reuses Component 2's loader with `validate=True`.
- Rejects any column matching `true_*` (e.g., `true_ra_deg`, `true_dec_deg`, `true_x_au`) — immediate `ValueError`.
- Never accesses `ground_truth.json`; that file resides only in the C5 evaluation path.

### 6.2 Component 3 forward model

**(source inspection)** Confirmed via `inspect.getsource` in `tests/test_component3_phase2.py::test_no_ground_truth_access`:
- `dynamics.py` contains no reference to `ground_truth`.
- `observation_model.py` contains no reference to `ground_truth`.
- The forward model is pure: propagation from a supplied trial state + observation prediction from Component 2 geometry. No trajectory.csv interpolation, no ground-truth lookup.

### 6.3 Verdict — PASS

**(source inspection + executed tests)** PASS. Truth separation is enforced at the loader level (forbidden `true_*` columns) and the forward model has no ground-truth access. This satisfies the audit's truth-separation requirement.

---

## 7. Numerical stability and determinism assessment

### 7.1 Executed tests

**(executed tests)** `tests/test_component3_phase2.py` — 24 passed, 0 failed, 0 errors (documented result):

| Test class | Count | Coverage |
|------------|-------|----------|
| DynamicsTests | 10 | initial state insertion, t=0 preservation, multi-epoch propagation, finiteness, determinism, invalid state/epoch rejection, planetary configuration, units, reference epoch |
| ObservationModelTests | 9 | observer reconstruction, relative positions, ecliptic-to-equatorial transformation, RA/Dec ranges, RA normalization, prediction structure, invalid epochs, mismatched lengths |
| IntegrationTests | 3 | end-to-end trial state → predictions, repeated-run consistency, no ground-truth access |
| PerformanceTests | 1 | ~262 epochs in < 5.0 s |

### 7.2 Source-inspection observations on stability

**(source inspection):**
- IAS15 integrator with ε = 1e-12 matches C1.
- Epochs integrated sequentially in sorted order; results returned in original input order.
- At t = 0, the propagated heliocentric state equals the input state (modulo the COM offset, which cancels in the Sun-relative extraction).
- Deterministic: identical inputs produce identical outputs (REBOUND IAS15 is deterministic for fixed inputs).
- All outputs are finite for finite inputs; validation rejects non-finite states and negative/non-finite epochs.

### 7.3 Verdict — PASS (within the simplified model)

**(source inspection + executed tests)** PASS for numerical stability, finiteness, and determinism within the simplified circular-coplanar, no-light-time model. This does **not** override the declination FAIL in Section 5.

---

## 8. Tests executed vs outstanding numerical verification

### 8.1 Test-count discrepancy (documentation defect)

**(source inspection)** `docs/component-3/PHASE_2_IMPLEMENTATION.md` Section 8 states:

- Header: "**Result:** 24 passed, 0 failed, 0 errors"
- Table category counts: Dynamics 10 + Observation model 9 + Integration 3 + Performance 1 = **23**, not 24.

The actual `tests/test_component3_phase2.py` contains:
- DynamicsTests: 10 test methods
- ObservationModelTests: 9 test methods
- IntegrationTests: 3 test methods
- PerformanceTests: 1 test method
Total = **23 test methods**.

The "24 passed" figure in the implementation document is therefore inconsistent with both the table (23) and the source file (23 test methods). This is a documentation defect only; it does not affect the scientific findings.

### 8.2 Outstanding numerical verification tests (not yet performed)

The following numerical verification checks remain outstanding. None have been executed as part of this read-only audit:

| # | Check | Description | Status |
|---|-------|-------------|--------|
| 1 | C2-vs-C3 prediction comparison | Run C2's generator pipeline and C3's `predict_from_orbit_state` on identical trial states/epochs; compare RA (expect match) and Dec (expect mismatch due to the Section 5 bug). Quantify the Dec error. | Outstanding |
| 2 | Propagation independence | Confirm C3's `propagate_trial_state` accepts arbitrary trial states, reads neither `trajectory.csv` nor `ground_truth.json`, and produces results independent of any true trajectory. | Outstanding (partially covered by `test_no_ground_truth_access` source inspection, but no end-to-end numerical run) |
| 3 | Numerical stability over long spans | Propagate over multi-year spans; verify finiteness, bounded energy error (IAS15), and deterministic repeatability. | Outstanding |
| 4 | t=0 state preservation | Confirm the propagated state at epoch 0 equals the input heliocentric state (covered by executed tests at places=5; higher-precision verification outstanding). | Partially covered |
| 5 | C1/C3 planetary state numeric equality | Numerically compare C1 `build_simulation` vs C3 `build_trial_simulation` particle-by-particle (mass, position, velocity) for the standard config. | Outstanding |
| 6 | Declination error magnitude | For representative LOS vectors at varying ecliptic latitudes, compute `dec` from `observer.calculate_sky_coordinates` vs `frames.calculate_ra_dec` after `ecliptic_to_equatorial`; report max |ΔDec|. | Outstanding |
| 7 | Full regression suite | `python -m pytest tests/ -q` re-run after any Component 2 correction, to confirm no regressions across all components. | Outstanding (post-correction) |

### 8.3 Verdict — INCOMPLETE

Numerical verification is incomplete: the focused test suite passed (23 tests, documented), but the cross-component numerical comparisons and long-span stability checks listed above have not been executed.

---

## 9. Final recommendation — BLOCKED

### 9.1 Summary of findings

| Section | Finding | Verdict |
|---------|---------|---------|
| 2 | C1/C3 planetary initialization consistency | CONDITIONAL PASS (standard circular-coplanar config only) |
| 3 | Heliocentric asteroid insertion/extraction | PASS |
| 4 | COM transformation ordering (massless asteroid) | PASS |
| 5 | Declination denominator in `observer.calculate_sky_coordinates` | **FAIL / BLOCKER** |
| 6 | Truth-data separation | PASS |
| 7 | Numerical stability, finiteness, determinism | PASS (within simplified model) |
| 8 | Test execution and outstanding checks | Focused tests passed (23); cross-component numerical checks outstanding |

### 9.2 Blocker

**`src/orbit_discovery/component2_observations/observer.py:328-329`** — `calculate_sky_coordinates()` computes declination with the ecliptic denominator `sqrt(x**2 + y**2)` instead of the equatorial denominator `sqrt(x_eq**2 + y_eq**2)`. RA is correct; Dec is wrong by up to ~1.748° in affected geometries. Component 3's forward model inherits this bug because `predict_apparent_coordinates` calls `calculate_sky_coordinates`.

This must be corrected in Component 2 (a source-file change outside this audit's read-only scope) and the outstanding numerical verification checks in Section 8.2 must be executed and pass before Phase 3 can be approved.

### 9.3 Recommendation

**Phase 2 scientific readiness: BLOCKED.**

Do **not** proceed to Phase 3 (orbit fitting / candidate generation) until:
1. The declination denominator in `observer.py:328-329` is corrected to use `sqrt(x_eq**2 + y_eq**2)`.
2. The correction is re-verified numerically (Section 8.2 checks 1, 5, 6).
3. The full regression suite passes with no regressions (Section 8.2 check 7).
4. The documentation test-count discrepancy in `PHASE_2_IMPLEMENTATION.md` Section 8 is corrected (24 → 23).

All findings above derive from read-only source inspection and documented test executions. No production source files, tests, or datasets were modified during this audit.
