# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). This project does not yet use semantic-release automation or a machine-readable package version.

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
