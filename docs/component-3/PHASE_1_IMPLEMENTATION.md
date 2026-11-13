# Component 3 — Phase 1 Implementation: Observation Loader and State Model

**Status:** Complete
**Date:** 2026-11-13
**Component:** Component 3 — Orbit Estimation and Candidate Orbit Generation
**Gate:** Complete — Phase 1 accepted; Phase 2 implemented and verified (see PHASE_2_IMPLEMENTATION.md).

---

## 1. Files Created

| File | Purpose |
|------|---------|
| `src/orbit_discovery/component3/__init__.py` | Component 3 package marker |
| `src/orbit_discovery/component3/models.py` | Core data models (OrbitState, ObservationDataset, OrbitCandidate, BestFitResult, EstimationResult) |
| `src/orbit_discovery/component3/loader.py` | Strict observation-loading service wrapping C2's loader |
| `tests/test_component3_phase1.py` | Focused Phase 1 test suite (18 tests) |
| `docs/component-3/PHASE_1_IMPLEMENTATION.md` | This document |

No existing files were modified.

## 2. Input Schema

The observation-loading service accepts **only** the following columns:

| Column | Unit | Description |
|--------|------|-------------|
| `obs_id` | int | Observation identifier |
| `time_years` | year | Elapsed time from reference epoch |
| `time_days` | day | Elapsed days from reference epoch |
| `ra_deg` | deg | Right ascension |
| `dec_deg` | deg | Declination |
| `sigma_ra_cosdec_arcsec` | arcsec | RA measurement uncertainty |
| `sigma_dec_arcsec` | arcsec | Declination measurement uncertainty |

Optional string columns accepted: `frame`, `time_scale`.

### Forbidden columns

Any column matching `true_*` (e.g. `true_ra_deg`, `true_dec_deg`, `true_x_au`) causes immediate rejection — this enforces truth separation between measurements and ground truth.

## 3. State Representation

### OrbitState (6D Cartesian)

```
x = [rx, ry, rz, vx, vy, vz]
```

| Element | Unit | Description |
|---------|------|-------------|
| `rx, ry, rz` | AU | Heliocentric position |
| `vx, vy, vz` | AU/year | Heliocentric velocity |
| Frame | — | Heliocentric ecliptic inertial |
| Time | years | Elapsed simulation time |
| Reference epoch | — | 0.0 yr (elapsed time since simulation start) |

Reference epoch is explicitly documented via `REFERENCE_EPOCH_YEARS = 0.0`.

## 4. Result Models

### OrbitState
- Six-dimensional Cartesian state
- Validation: dimensions (6), finite values
- Serialization: `to_dict()` / `from_dict()`

### ObservationDataset
- Validated observation measurement container
- Fields: `data` (dict of arrays), `frame`, `time_scale`, `metadata`
- Validation: finite numeric values, non-decreasing timestamps

### OrbitCandidate
- Candidate orbit solution
- Fields: `state` (OrbitState), `epoch_years`, `metadata`

### BestFitResult
- Result of orbit determination fit
- Fields: `state` (OrbitState), `epoch_years`, `residuals`, `fit_metrics`

### EstimationResult
- Overall estimation result
- Fields: `candidates` (List[OrbitCandidate]), `best_fit` (BestFitResult), `source_dataset_metadata`

## 5. Loader Behavior

`load_dataset_for_estimation(csv_path)` performs:

1. **File existence check** — raises `FileNotFoundError` if CSV missing
2. **C2 schema validation** — reuses `c3_loader.load_observation_dataset` with `validate=True`
3. **Metadata loading** — reads sibling `metadata.json` for dataset identity and source metadata
4. **C3-specific validation:**
   - Missing required columns → `ValueError`
   - Non-finite numerical values → `ValueError`
   - Positive measurement uncertainties → `ValueError`
   - Valid RA range [0, 360] degrees → `ValueError`
   - Valid Dec range [-90, 90] degrees → `ValueError`
   - Timestamp consistency (`time_days ≈ time_years × 365.25`) → `ValueError`
   - Timestamp ordering (non-decreasing) → `ValueError`
   - Ground-truth (`true_*`) column rejection → `ValueError` (via C2 loader)

Ground truth is **never** loaded through this loader; it resides only in `ground_truth.json` (C5-evaluation path).

## 6. Validation Rules

| Rule | Detail |
|------|--------|
| Required columns | `obs_id`, `time_years`, `time_days`, `ra_deg`, `dec_deg`, `sigma_ra_cosdec_arcsec`, `sigma_dec_arcsec` |
| Finite values | All numeric columns must be finite (no NaN/Inf) |
| Uncertainties | `sigma_ra_cosdec_arcsec > 0`, `sigma_dec_arcsec > 0` |
| RA range | `0 <= ra_deg <= 360` |
| Dec range | `-90 <= dec_deg <= 90` |
| Time consistency | `time_days ≈ time_years × 365.25` (rtol=0, atol=1e-8) |
| Time ordering | Non-decreasing `time_years` |
| Ground truth | `true_*` columns forbidden |
| Truth separation | `ground_truth.json` never accessed by this loader |

## 7. Test Commands and Results

### Focused Phase 1 tests

```powershell
python tests/test_component3_phase1.py -v
```

**Result:** 18 passed, 0 failed, 0 errors

### Existing full test suite (regression check)

```powershell
python -m pytest tests/ -q
```

**Result:** 193 passed, 1 deselected, 0 failures — no regressions introduced

## 8. Known Limitations

- Component 3 currently does not implement orbit propagation, fitting, candidate generation, or uncertainty estimation (these are Phase 2+ work).
- Observer state (position/velocity) is not yet persisted per observation in `observations.csv`; observer geometry is reconstructed from `metadata.json` parameters.
- No absolute calendar epoch (`epoch_jd_tdb`) exists; time remains elapsed simulation time.
- Planetary masses and initial conditions for downstream propagation remain hardcoded in Component 1 source (`BODY_DATA`); not serialized into observation metadata.
- No REBOUND forward model is included in Component 3 at this stage.

## 9. Remaining Blockers for Phase 2

1. **Observer state persistence:** Component 3 needs observer position/velocity at each observation epoch for light-time and parallax corrections. Currently only observer orbital parameters are stored in metadata; the per-epoch observer state must be recomputed dynamically via Component 2's `observer.py`.
2. **Planetary dynamics serialization:** Component 3's propagation will require planetary masses/initial conditions that currently live only in Component 1's hardcoded `BODY_DATA`.
3. **Absolute epoch:** Future survey-data integration will require an absolute calendar epoch convention; currently only elapsed simulation time is supported.

## 10. Completion Gate Confirmation

- [x] Focused tests pass (18/18)
- [x] Existing test suite passes with no regressions (193 passed, 1 deselected)
- [x] Baseline datasets unchanged (`data/` and `configs/` untouched)
- [x] No Component 1 or Component 2 algorithms modified
- [x] No observer-state CSV columns added
- [x] No REBOUND forward model implemented
- [x] Phase 2 not started

Phase 1 is complete. Awaiting approval to proceed to Phase 2.
