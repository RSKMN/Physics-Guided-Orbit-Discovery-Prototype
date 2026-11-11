# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). This project does not yet use semantic-release automation or a machine-readable package version.

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
