# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). This project does not yet use semantic-release automation or a machine-readable package version.

## [0.4.1] - 2026-11-14

### Added

- Component 3 Phase 3C — Levenberg–Marquardt optimizer (`src/orbit_discovery/component3/optimizer.py`): NumPy-only weighted nonlinear least-squares fit with parameter scaling (`s = [1, 1, 1, 2π, 2π, 2π]`), numerical forward-difference Jacobian in scaled coordinates, adaptive damping, overflow/non-finite handling, residual-dimension validation, parameter validation, Jacobian accounting, and exception propagation (TypeError/AttributeError propagate; numerical exceptions wrapped as recoverable `EvaluationError`). No new dependencies; SciPy not used. `tests/test_component3_optimizer.py`: 29 tests covering convergence, scaling, Jacobian accounting, damping escalation, invalid input rejection, termination diagnostics, and numerical robustness.
- Component 3 Phase 3D — Best-fit orbit estimation integration (`src/orbit_discovery/component3/estimation.py`): `build_residual_function()` and `run_estimation()` orchestrating the C3 forward model (propagation → prediction → residuals) with the LM optimizer; dataset validation (nonempty, finite, nonnegative epochs, compatible array lengths) before propagation; physical-coordinate contract (res["x"] is physical, no scaling applied); final-prediction efficiency (propagate once, predict once); numerical-exception-only handlers; result model mapping (residuals dict with ndarrays only, fit_metrics dict with floats only, diagnostics in `OrbitCandidate.metadata`). `tests/test_component3_estimation.py`: 13 tests covering dataset validation before propagation, negative epoch rejection, invalid initial state, residual dimension consistency, failed trial propagation, non-converged result handling, valid synthetic dataset, orbit recovery from perturbed guess, scaled Jacobian analysis (rank 6/6), final-prediction failure handling (via propagation and via prediction), source dataset metadata passthrough, and absence of truth-related metadata keys.
- Focused test result: 40 passed (optimizer 29 + estimation 13), 0 failed.

### Changed

- `pyproject.toml`, `README.md` and `CHANGELOG.md`: project version updated from 0.4.0 to 0.4.1.
- Component 3 phase status: Phase 3C optimizer moved from "not started" to implemented/tested/released; Phase 3D estimator added as implemented/tested/released; autonomous initial-guess generation, candidate generation, covariance reporting, and Components 4–5 remain pending.

### Documentation

- `docs/component-3/PHASE_3_DESIGN.md`: Phase 3C and Phase 3D status updated to implemented/tested/released; implementation paths, test files, test counts, Jacobian rank/condition number recorded.
- `docs/BUILD_ROADMAP.md`: version history (Section 13) append-only row added for project version 0.4.1; Component 3 Phase 3C/3D status rows updated.

## [0.4.0] - 2026-11-13

### Added

- Component 3 Phase 3B — Residual calculation: `src/orbit_discovery/component3/residuals.py` implementing wrapped right-ascension residuals (branch-cut at RA = 0/360), declination residuals (no wrapping), tangent-plane RA weighting with cos(dec) applied exactly once using the observed declination as the fixed reference, degrees-to-arcseconds conversion, normalization by `sigma_ra_cosdec_arcsec` / `sigma_dec_arcsec`, fixed residual-vector structure over pole-retained observations, pole screening (`|cos(dec)| >= 1e-12`), and the chi-square objective `chi2 = r^T r`. NumPy-only; no optimizer, no estimator, no forward-model change, no new dependencies, no ground-truth access.
- Focused tests `tests/test_component3_residuals.py`: 57 tests covering RA wraparound, declination difference, pole screening, residual weighting, arcsec conversion, cos(dec)-not-double-applied, chi-square, angular-input validation, declination bounds, invalid pole thresholds, all-observations-excluded rejection, empty/NaN/infinite chi-square rejection, hand-calculated chi-square cross-check, and an integration test combining RA wraparound with the observed-dec cosine correction.

### Changed

- `pyproject.toml`, `README.md` and `CHANGELOG.md`: project version updated from 0.3.0 to 0.4.0.
- Component 3 phase status: Phase 1 (observation loader and state model) and Phase 2 (trial-orbit propagation and observation prediction) complete; Phase 3 design (Phase 3A) approved; Phase 3B (residual calculation) implemented, hardened, tested and approved; Phase 3C (optimizer implementation) not started; Phases 4–8 pending.

### Documentation

- `docs/component-3/PHASE_3_DESIGN.md`: Phase 3A design status updated to approved; Phase 3B residual implementation recorded.
- `docs/BUILD_ROADMAP.md`: version history (Section 13) append-only row added for project version 0.4.0.

## [0.3.0] - 2026-11-13

### Added

- Component 3 Phase 1 — Observation loader and state model: `src/orbit_discovery/component3/` package with `models.py`, `loader.py`, `__init__.py`, focused tests `tests/test_component3_phase1.py` (18 tests).
- Component 3 Phase 2 — Trial-orbit propagation and observation prediction: `dynamics.py` (`build_trial_simulation`, `propagate_trial_state`, `propagate_trial_state_single`), `observation_model.py` (`predict_apparent_coordinates`, `predict_from_orbit_state`, `reconstruct_observer_config`, `get_obliquity_deg`), focused tests `tests/test_component3_phase2.py` (23 tests).
- Docs: `docs/component-3/` with Phase 1, Phase 2, scientific verification, and Diagnostics 1–4 (C2 vs C3 prediction, C1 vs C3 planetary state, initial-state preservation, long-span stability).
- Declination denominator fix in `src/orbit_discovery/component2_observations/observer.py`: `calculate_sky_coordinates` now uses `sqrt(x_eq^2 + y_eq^2)` (equatorial denominator) instead of `sqrt(x^2 + y^2)` (ecliptic denominator).
- `tests/test_component2_observer.py`: added `CalculateSkyCoordinatesRegressionTests` validating declination against `frames.calculate_ra_dec`.

### Changed

- `pyproject.toml`, `README.md` and `CHANGELOG.md`: project version updated from 0.2.2 to 0.3.0.
- `README.md`: rewritten to reflect v0.3.0 state — C1/C2 implemented and integrated, C3 Phase 1–2 implemented and verified, Component 3 Phase 3 not started, Components 4–5 not implemented.

### Fixed

- `src/orbit_discovery/component2_observations/observer.py`: `calculate_sky_coordinates()` declination now uses the equatorial denominator `sqrt(x_eq^2 + y_eq^2)`, matching `frames.calculate_ra_dec`. RA was already correct.

### Documentation

- `docs/component-3/PHASE_1_IMPLEMENTATION.md`, `PHASE_2_IMPLEMENTATION.md`, `PHASE_2_SCIENTIFIC_VERIFICATION.md`: C3 implementation status and verification records.
- `docs/component-3/DIAGNOSTIC_1_C2_VS_C3_PREDICTION_COMPARISON.md`: C3 forward model matches C2 `calculate_sky_coordinates` and C2 frames reference at floating-point tolerance (32 samples).
- `docs/component-3/DIAGNOSTIC_2_C1_VS_C3_PLANETARY_STATE_COMPARISON.md`: C3 planetary initial conditions and propagated states match C1 numerically for the standard circular-coplanar configuration.
- `docs/component-3/DIAGNOSTIC_3_INITIAL_STATE_PRESERVATION.md`: C3 preserves supplied 6D heliocentric asteroid states at tolerance 1e-12 AU / 1e-12 AU/yr for all 5 test states; short propagation to 0.001 yr remains finite.
- `docs/component-3/DIAGNOSTIC_4_LONG_SPAN_STABILITY.md`: 10-year C3 REBOUND/IAS15 integration stable; energy max relative drift ≤ 9.24e-16, angular momentum max relative drift ≤ 3.80e-16; all states finite; cross-run consistency within round-off.

## [0.2.2] - 2026-11-13

### Added

- Added `tests/test_end_to_end_integration.py` covering all 8 required C1→C2 end-to-end scenarios plus 2 extras (propagate_state single epoch, orbital element round trip): 10/10 pass.
- Added `docs/STAGE_2.7_COMPLETION_REPORT.md` documenting the verified Stage 2.7 end-to-end integration results.
- Added `docs/STAGE_2.7.1_VERIFICATION_REPORT.md` documenting the Stage 2.7.1 physical-consistency audit and defect remediation.

### Changed

- `pyproject.toml`, `README.md` and `CHANGELOG.md`: project version updated from 0.2.0 to 0.2.2.
- `README.md`: rewritten to reflect the current actual state — C1/C2 implemented and integrated, Stage 2.7.1 physical-consistency correction documented, Components 3–5 not implemented.

### Fixed

- Gravitational parameter consistency correction (Defect D-1): downstream analytic modules now use `MU_REBOUND = 39.476926421373`, matching C1's REBOUND `sim.G` with units `(yr, AU, Msun)`; previously these modules declared `MU = 1.0`, which disagreed with C1's actual propagation.
  - `src/orbit_discovery/core/orbital_elements.py`: vis-viva energy, eccentricity vector and perifocal velocity now use `MU_REBOUND`; element-conversion round trip now exact at machine precision (~4.4e-16 AU).
  - `src/orbit_discovery/component2_observations/observer.py`: observer velocity changed from `sqrt(1.0 / r)` to `sqrt(MU_REBOUND / r)`; at r=1 AU this is 6.283 AU/yr (previously 1.000 AU/yr).
  - `src/orbit_discovery/component2_observations/prediction.py`: `MU_REBOUND` declared and documented (computations propagate through REBOUND directly).
  - `src/orbit_discovery/core/interpolation_validation.py`: `MU_REBOUND` declared and documented.
- `src/orbit_discovery/component2_observations/c5_loader.py`: fixed syntax corruption (literal escape sequences in module docstring) that caused `SyntaxError`.
- `src/orbit_discovery/component2_observations/prediction.py`: wrapped trajectory positions/velocities with `np.asarray()` to handle Python-list inputs (Defect 2).
- `src/orbit_discovery/core/propagation.py`: `propagate_multi()` now interpolates inside the trajectory span and integrates beyond it (Defect 3); `propagate_from_trajectory()` integrates from the first trajectory sample at t=0 directly to the target beyond-span time (Defect 4).
- `tests/test_component2_generator.py`: fixed `GeneratorSignatureAndConstantTests` inheritance and column-order assertion.
- `tests/test_observation_output.py`: validates ground truth from the separate `ground_truth.json` instead of `true_*` columns in the observation CSV.

### Documentation

- `docs/BUILD_ROADMAP.md`: Section 2.7 gap table updated to mark truth separation, observation schema, propagation and state↔elements conversion as complete/verified; version history (Section 13) append-only row added for 0.2.2.

## [0.2.0] - Unreleased

Initial documented prototype baseline. No earlier changelog exists, and no dated release event was recorded for this version. This entry describes the repository state at baseline preparation; it does not claim that the listed capabilities were added by the documentation changes in this commit.

### Added

- Documented the existing Component 1 configurable N-body simulator:
  - REBOUND/IAS15 integration with the Sun, Mercury, Venus, Earth and Jupiter;
  - synthetic asteroid initial conditions from orbital elements;
  - trajectory CSV, configuration copy, run metadata and trajectory plots.
- Documented the existing Component 2 synthetic observation generator:
  - fixed-cadence observation scheduling;
  - idealized circular observer model;
  - ecliptic-to-equatorial conversion and RA/Dec calculation;
  - seeded independent Gaussian angular noise;
  - observation CSV and metadata output.
- Documented the three synthetic scenarios: standard, eccentric and inclined.
- Retained reference trajectories, observation datasets and validation artefacts for the 0.2.0 baseline.
- Added `README.md` with verified commands, current status, assumptions and limitations.
- Added `docs/development/DATA_VERSIONING_POLICY.md`.
- Added `docs/development/BASELINE_0.2.0.md`.

### Changed

- Prepared the repository for its first Git publication while preserving the 0.2.0 prototype as a baseline.
- Replaced the broad data ignore rules with path-specific rules for generated figures.
- Clarified that Components 3, 4 and 5 are planned and not implemented.
- Linked the existing codebase analysis and refactoring plan from the project README.

### Fixed

- Corrected `.gitignore` so that scientific JSON configurations, metadata, observation tables, trajectories and validation CSVs are no longer globally ignored.
- Corrected repository documentation paths that referred to the former `prototype-1/code` directory.
- Removed the outdated pending-rename instructions from the codebase analysis.

### Known limitations

- No orbit estimation, candidate-orbit generation or uncertainty quantification.
- No active observation selection or schedule evaluation.
- No absolute astronomical epoch; observation times are elapsed simulation times.
- Linear interpolation is used for observation positions; the measured median/maximum difference from cubic Hermite is approximately 0.223″/1.731″.
- No light-time correction, aberration, topocentric parallax, precession/nutation or relativistic deflection.
- No solar-elongation or visibility filtering; approximately 25.6% of current observation epochs have elongation below 30°.
- Noise-free `true_ra_deg` and `true_dec_deg` remain in the estimator-facing observation CSV.
- No covariance/correlated noise model.
- The observer is an idealized circular model, not a real ephemeris.
- The synthetic planetary initial conditions are simplified and not a real-world accuracy claim.
- The test suite is script-based; `pytest` is not installed.
- No machine-readable version, package metadata, license or citation file is present.
