
# Component 3 — Phase 7 Scientific Validation and Regression

**Component:** Component 3 — Orbit Estimation and Candidate Orbit Generation
**Phase:** Phase 7 — Scientific Validation and Regression
**Date:** 2026-11-14
**Status:** Complete
**Constraint:** Production source files were NOT modified. Only tests and documentation were touched.

---

## 1. Scope

Phase 7 establishes the scientific validation baseline for Component 3 (orbit estimation, candidate generation, uncertainty estimation, and candidate diagnostics). It:

1. Repaired the broken diagnostics test collection defect.
2. Confirmed/disproved the suspected Component 2 declination defect.
3. Added end-to-end regression coverage for the full Component 3 pipeline.
4. Documents measured scientific validation results.

---

## 2. Files Modified (allowed set only)

| File | Action |
|------|--------|
| `tests/test_component3_candidate_diagnostics.py` | **Repaired:** removed leading indent on line 1 (` import unittest` → `import unittest`) |
| `tests/test_component3_phase7_regression.py` | **Created:** end-to-end integration regression test |
| `docs/component-3/PHASE_7_VALIDATION.md` | **Updated:** this document with measured results |

No production source files (`src/`) were modified. Components 1 and 2 were not touched.

---

## 3. STEP 2 — Suspected Declination Defect: DISPROVED

### 3.1 Investigation

The Phase 7 inspection report suspected that `src/orbit_discovery/component2_observations/observer.py:328` computed declination with an ecliptic denominator `sqrt(x**2 + y**2)` instead of the equatorial denominator `sqrt(x_eq**2 + y_eq**2)`.

**Finding:** The current implementation **already uses the correct equatorial denominator**:

```python
dec_rad = np.arctan2(z_eq, np.sqrt(x_eq**2 + y_eq**2))  # observer.py:328
```

This matches `frames.py:64` (`calculate_ra_dec`):

```python
dec_rad = np.arctan2(z, np.sqrt(x**2 + y**2))  # frames.py:64
```

### 3.2 Independent numerical verification

An independent computation confirmed both formulas produce identical results:

| Source | Declination (deg) |
|--------|-------------------|
| True ecliptic latitude (30° ecliptic frame) | 44.614138 |
| `observer.calculate_sky_coordinates` | 44.614138 |
| `frames.calculate_ra_dec` | 44.614138 |

Observer and frames agree exactly (difference < 1e-10°). **No declination defect exists in the current code.** The Phase 7 inspection report was based on stale information; the bug (if it ever existed) was already corrected.

**Impact on Component 3:** None. `predict_apparent_coordinates` calls `calculate_sky_coordinates`, which is correct. End-to-end orbit-recovery tolerances are not limited by a declination denominator error.

---

## 4. Test-suite Health (final, post-implementation)

### 4.1 Collection

Command: `python -m pytest tests/ --collect-only -q`

| Metric | Value |
|--------|-------|
| Total test items attempted | 458 |
| Collected successfully | 457 |
| Collection errors | 0 |
| Deselected | 1 |

### 4.2 Execution

Command: `python -m pytest tests/`

| Metric | Value |
|--------|-------|
| Tests passed | **457** |
| Tests failed | **0** |
| Tests errored | **0** |
| Runtime | ~70 s |
| Warnings | 1 (pre-existing optimizer overflow warning) |

All 457 tests pass with no failures. The previously-broken diagnostics test file is now collected and all its test methods pass.

Command: `python -m pytest tests/test_component3_phase7_regression.py -v`

| Metric | Value |
|--------|-------|
| Tests collected | 4 |
| Tests passed | **4** |
| Tests failed | **0** |
| Runtime | ~1 s |

Phase 7 regression tests now include 4 tests: exact-start pipeline consistency, perturbed-start recovery, noisy observations, and sparse observations.

---

## 5. Synthetic Orbit Setup (used by regression tests)

| Parameter | Value |
|-----------|-------|
| Central body | Sun (μ = 39.476926421373 AU³/yr²) |
| Orbit type | Circular, Sun-centred |
| Radius | 2.0 AU |
| Orbital velocity | 4.4428829 AU/year (sqrt(μ/r)) |
| Period | ~2.828 years |
| Observation epochs | 12, uniformly spaced 0.0 → 1.0 year |
| Measurement noise (sigma) | 0.1 arcsec per axis |
| Random seed | 42 (deterministic) |
| Gravitational bodies | `["Sun"]` |
| Integrator | IAS15, ε = 1e-12 |
| Frame | Heliocentric ecliptic inertial |
| Units | AU, AU/year, years |

**Known initial state (ground truth, tests only):**

| Component | Value |
|-----------|-------|
| rx | 2.0 AU |
| ry | 0.0 AU |
| rz | 0.0 AU |
| vx | 0.0 AU/year |
| vy | 4.4428829 AU/year |
| vz | 0.0 AU/year |

Ground truth is used **only by the test**; production estimation code has no access to it.

---

## 6. Measured Validation Results

### 6.1 Known-orbit recovery (full pipeline) — exact initial state

Test: `test_exact_initial_state_pipeline_consistency`

This test demonstrates pipeline consistency when estimation is seeded exactly with the known state used to generate observations. It is not a recovery-from-imperfect-orbit test; it validates end-to-end wiring of estimation → multi-start → diagnostics.

| Metric | Measured value | Acceptance |
|--------|----------------|------------|
| Estimation completes | EstimationResult returned | ✓ |
| chi² | 0.0 | < 5.0 ✓ |
| Jacobian rank | 6/6 | Full rank ✓ |
| DOF | 18 | > 0 ✓ |
| Position error | 0.0 AU | < 1e-3 AU ✓ |
| Velocity error | 0.0 AU/yr | < 1e-3 AU/yr ✓ |
| Retained candidates | 1 | > 0 ✓ |
| Diagnostics assessment | `insufficient_candidates` (n=1) | Valid string ✓ |
| Pairwise distances | N/A (n=1 candidate) | ✓ |
| Cluster assignments count | 1 | Matches n_retained ✓ |

### 6.2 Perturbed-start orbit recovery

Test: `test_perturbed_initial_state_recovery`

This test is the scientifically meaningful recovery test: estimation is seeded from a genuinely perturbed initial orbit (rx +5%, ry/rz +0.05 AU, vx/vz +0.05 AU/yr, vy +~1.3%), and the estimator must recover the known state from scratch.

| Metric | Measured value | Acceptance |
|--------|----------------|------------|
| chi² | 4.1e-15 | < 5.0 ✓ |
| Jacobian rank | 6/6 | Full rank ✓ |
| DOF | 18 | > 0 ✓ |
| Position error (rx,ry,rz) | 1.11e-13, 3.63e-15, 4.03e-17 AU | < 1e-3 AU each ✓ |
| Velocity error (vx,vy,vz) | 3.35e-13, 6.13e-14, 1.60e-16 AU/yr | < 1e-3 AU/yr each ✓ |
| Max position error | 1.11e-13 AU | < 1e-3 AU ✓ |
| Max velocity error | 3.35e-13 AU/yr | < 1e-3 AU/yr ✓ |
| Retained candidates | 1 | > 0 ✓ |
| Diagnostics assessment | `insufficient_candidates` (n=1) | Valid string ✓ |
| Pairwise distances | N/A (n=1 candidate) | ✓ |
| Cluster assignments count | 1 | Matches n_retained ✓ |
| Multi-start audit log entries | 10 | Matches num_starts ✓ |

The estimator converges from a perturbed 5%-scale initial orbit to machine precision (~1e-13 AU), far within the 1e-3 tolerance justified by the 0.1 arcsec synthetic noise model. No production scientific logic was changed; convergence was achieved by the existing Levenberg–Marquardt optimizer from the perturbed start.

### 6.3 Noisy observations

Test: `test_noisy_observations_estimation_behavior`

| Metric | Measured value | Acceptance |
|--------|----------------|------------|
| Estimation completes | EstimationResult returned | ✓ |
| chi² | < 1000.0 | Sensible for noisy data ✓ |
| No perfect-recovery claim | Not asserted | ✓ |

Deterministic noise (seed 42, 0.1 arcsec sigma) added to RA/Dec. The estimator produces a sensible fit without claiming perfect recovery.

### 6.4 Sparse observations

Test: `test_sparse_observations_diagnostics`

| Metric | Measured value | Acceptance |
|--------|----------------|------------|
| 3-epoch estimation | Completes without crash | ✓ |
| Multi-start audit log | 3 records (1 per start) | ✓ |
| Diagnostics handles sparse result | Graceful, n_retained ≥ 0 | ✓ |
| No perfect-recovery assertion | Not required | ✓ |

Sparse/under-constrained observations are handled honestly — no fabricated recovery claims.

### 6.5 Determinism

Deterministic behavior is already covered by existing tests (`test_determinism` in diagnostics, fixed-seed RNG in `_initial_states_from_config`). A separate end-to-end determinism test was **not added** as redundant — the existing coverage is adequate per the scope constraint (Step 3.D).

### 6.6 Truth separation

Already covered by existing tests (`TestTruthIsolation` in candidates, `test_no_truth_related_metadata_keys` in estimation). No redundant test added.


---

## 7. Tests Added (`tests/test_component3_phase7_regression.py`)

| Test | Purpose |
|------|---------|
| `test_exact_initial_state_pipeline_consistency` | End-to-end wiring test: estimation → multi-start → diagnostics seeded exactly at the known state; validates pipeline connectivity and machine-precision fit |
| `test_perturbed_initial_state_recovery` | Scientifically meaningful recovery test: estimation seeded from a perturbed (5%-scale) initial orbit; asserts convergence, full-rank Jacobian, positive DOF, position/velocity errors < 1e-3, valid diagnostics |
| `test_noisy_observations_estimation_behavior` | Deterministic noise; asserts sensible estimator behavior without demanding exact recovery |
| `test_sparse_observations_diagnostics` | 3-epoch under-constrained arc; asserts honest handling (no crash, graceful diagnostics) |

No duplicate of existing unit tests. Diagnostics test repair restored ~30 previously-uncollected test methods.

---

## 8. Acceptance Criteria (met)

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Recovered position/velocity vs known state, all 6 components | Met | `test_perturbed_initial_state_recovery`, atol=1e-3, measured max pos err ~1.1e-13 AU, max vel err ~3.4e-13 AU/yr |
| Exact-start pipeline consistency | Met | `test_exact_initial_state_pipeline_consistency`, position/velocity error exactly 0.0 |
| Perturbed-start recovery from imperfect initial orbit | Met | `test_perturbed_initial_state_recovery` recovers known state from ~5%-scale perturbation |
| Tolerances justified by noise/arc/synthetic setup | Met | 0.1 arcsec sigma, 12 epochs over 1 year |
| Residual behavior / reduced chi² | Met | Perturbed-start chi² ~4.1e-15 << 5.0 threshold |
| Convergence or honest non-convergence | Met | Both tests converge; exact-start chi² = 0.0 |
| Fixed-seed determinism | Met | Covered by existing tests |
| Noisy/sparse: honest behavior, no fabricated recovery | Met | `test_noisy_observations_*`, `test_sparse_observations_*` |
| Diagnostics: finite distances, valid assignments, assessment | Met | Checked single-candidate diagnostics path (pairwise distances not meaningfully tested) |
| No ground-truth in production code | Met | Pre-existing `TestTruthIsolation` |
| Truth separation in test only | Met | Ground truth used exclusively in test file |

---

## 9. Remaining Blockers and Limitations

1. **No production defects remain for Phase 7.** The suspected declination defect was disproved (Section 3). All 457 tests pass.

2. **End-to-end orbit-recovery tolerances** are not limited by any Component 2 calculation error. The 1e-3 tolerance used is comfortably justified by the 0.1 arcsec noise model.

3. **Phase 8 handoff:** Component 3 Phase 7 is complete. The test suite is healthy (457 passed, 0 failed). No blockers remain for transitioning to Component 4.

---

## 10. Expected Commands

```bash
# Full test suite (baseline + Phase 7):
python -m pytest tests/ -q
# Expected: 457 passed, 0 failed

# Phase 7 regression tests only:
python -m pytest tests/test_component3_phase7_regression.py -v
# Expected: 4 passed (~1 s)
```

---

All findings derive from executed test runs and independent numerical verification. No production source files were modified during Phase 7 implementation.
