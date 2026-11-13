# Physics-Guided Orbit Discovery Prototype

A research prototype for physics-guided asteroid orbit discovery. The project combines N-body simulation, synthetic astrometry and, in later stages, orbit estimation and active observation selection.

**Current version:** 0.2.0  
**Status:** Components 1 and 2 implemented; Components 3–5 planned and **not implemented**.  
**Baseline:** see [`docs/development/BASELINE_0.2.0.md`](docs/development/BASELINE_0.2.0.md) and [`CHANGELOG.md`](CHANGELOG.md).

## Research motivation

Discovering and characterising asteroids from sparse astrometry requires more than fitting a curve to sky positions. The observable measurements depend on the target's dynamics, the observer's motion, the geometry of the Solar System and the times at which observations are taken. A reproducible synthetic testbed makes it possible to study those dependencies before applying a method to real survey data.

This prototype is intended to support experiments in which physical dynamics and candidate-orbit uncertainty guide the choice of the next observation. Version 0.2.0 provides the simulation and observation-generation half of that pipeline. It does not yet estimate orbits or select observations.

## Problem statement

Given a set of noisy angular observations of a Solar System body, together with the observer geometry and an observation budget, the long-term problem is to:

1. infer plausible orbits consistent with the measurements;
2. represent the remaining uncertainty honestly;
3. choose future observation times that discriminate between candidates or reduce uncertainty;
4. evaluate the resulting strategy against fixed and random schedules at equal cost.

The current prototype addresses the data-generation preconditions for that problem, not the problem itself.

## Research objectives

- Build a configurable, reproducible N-body simulation of asteroid motion.
- Generate synthetic right-ascension and declination measurements with explicit observer and noise assumptions.
- Preserve a clear separation between simulated truth and noisy measurements in future versions.
- Provide stable data contracts that a future orbit estimator and active scheduler can consume.
- Validate the numerical and geometric pipeline before adding estimation and selection.
- Keep scientific assumptions visible, measurable and versioned.

## Current prototype capabilities

- **Component 1:** configurable REBOUND/IAS15 simulation of a massless asteroid under the gravity of the Sun, Mercury, Venus, Earth and Jupiter.
- **Component 2:** fixed-cadence synthetic observation generation using an idealized circular observer, ecliptic-to-equatorial rotation, RA/Dec calculation and seeded Gaussian angular noise.
- **Scenarios:** standard (`e = 0.2`, `i = 0°`), eccentric (`e = 0.5`) and inclined (`e = 0.3`, `i = 10°`).
- **Data products:** trajectories, run metadata, observation tables and observation metadata.
- **Validation:** read-only checks for trajectory schema, orbital geometry, Kepler period, integrator tolerance, frame conversion, noise reproducibility and observation-dataset integrity.
- **Analysis:** comparative plots and a summary table for the three observation datasets.
- **Legacy validation:** separate two-body, N-body and Eros/Horizons workflows are retained as historical evidence.

## Component architecture

```text
configs/synthetic_asteroid*.json
        |
        v
Component 1: N-body simulator (REBOUND / IAS15)
        |
        +--> data/runs/<run>/trajectory.csv
        +--> data/runs/<run>/metadata.json
        +--> data/runs/<run>/config.json
        |
        v
configs/synthetic_observations*.json
        |
        v
Component 2: observation generator
  schedule -> interpolation -> observer -> frame conversion -> RA/Dec -> noise
        |
        +--> data/observations/<dataset>/observations.csv
        +--> data/observations/<dataset>/metadata.json

Planned, not implemented:
Component 3: orbit estimation and candidate generation
Component 4: active observation selection
Component 5: evaluation and schedule comparison
```

## Current implementation status

| Component | Status in 0.2.0 | Notes |
|---|---|---|
| Component 1 — N-body simulator | Implemented | Configurable synthetic scenarios; writes trajectory, config and metadata |
| Component 2 — Synthetic observations | Implemented | Fixed cadence, idealized observer, seeded Gaussian noise |
| Component 3 — Orbit estimation | **Not implemented** | No fitter, candidate model, covariance or orbit-solution schema |
| Component 4 — Active selection | **Not implemented** | No scheduler, candidate scoring or future observation window |
| Component 5 — Evaluation | **Not implemented** | No equal-budget comparison harness or calibration study |

Do not describe Components 3–5 as working features. The analysis in [`docs/development/CODEBASE_ANALYSIS.md`](docs/development/CODEBASE_ANALYSIS.md) records the implemented/not-implemented boundary in detail.

## Repository structure

```text
physics-guided-orbit-discovery-prototype/
├── configs/                 # six scientific JSON configurations
├── data/                    # reference trajectories, observations and validation artefacts
├── docs/                    # component documentation and development records
│   ├── BUILD_ROADMAP.md     # authoritative status, plans and contracts
│   ├── COMPONENT_1.md
│   └── development/
│       ├── CODEBASE_ANALYSIS.md
│       ├── REFACTORING_PLAN.md
│       ├── DATA_VERSIONING_POLICY.md
│       └── BASELINE_0.2.0.md
├── plots/                   # legacy generated figures (Git-ignored)
├── results/                 # comparison summary and generated figures
├── src/                     # 12 Python source files
├── tests/                   # 19 script-style validation files
├── .gitignore
├── CHANGELOG.md
├── README.md
├── requirements.txt
└── requirements-lock.txt
```

Generated trajectory plots under `data/runs/`, `plots/` and `results/component-2/figures/` are intentionally ignored. The underlying data tables, metadata and validation CSVs are tracked. See [`docs/development/DATA_VERSIONING_POLICY.md`](docs/development/DATA_VERSIONING_POLICY.md).

## Installation and environment setup

### Verified baseline environment

The repository was verified with the existing local virtual environment on Windows 11:

```powershell
.\.venv\Scripts\python.exe --version
# Python 3.13.9

.\.venv\Scripts\python.exe -c "import rebound, numpy, pandas, matplotlib; print(rebound.__version__, numpy.__version__, pandas.__version__, matplotlib.__version__)"
# 5.2.2 2.5.4 3.1.0 3.11.2
```

The installed environment also contains `astroquery 0.4.11`, which is required by the legacy Horizons validation scripts but is **not** declared in `requirements.txt` or `requirements-lock.txt`. `pytest` is **not installed**; the current validation suite is script-based.

`requirements.txt` lists the top-level runtime packages. `requirements-lock.txt` pins the resolved packages used by the existing environment. It is stored as UTF-16 LE (with BOM), so Git treats it as a binary file; the content was inspected but its encoding was not changed. `astroquery` and `pytest` are missing from the lock file. A fresh environment creation and dependency installation procedure has **not** been verified as part of this baseline; review the dependency files before relying on them for a clean install.

## How to run Component 1

Run from the repository root. The configuration path is positional:

```powershell
.\.venv\Scripts\python.exe src\configurable_simulator.py configs\synthetic_asteroid.json
```

Equivalent configurations:

- `configs\synthetic_asteroid_eccentric.json`
- `configs\synthetic_asteroid_inclined.json`

The CLI syntax was verified with `--help`. The full command was **not executed during baseline preparation** because it writes into the existing reference run directory (`data/runs/<simulation_name>/`) and would regenerate tracked artefacts.

## How to run Component 2

Run from the repository root using the module form:

```powershell
.\.venv\Scripts\python.exe -m src.observation_generator --config configs\synthetic_observations.json
```

Equivalent configurations:

- `configs\synthetic_observations_eccentric.json`
- `configs\synthetic_observations_inclined.json`

The `-m` form is required. Direct invocation with `python src\observation_generator.py` currently fails because the module uses `from src...` imports.

The CLI syntax was verified with `--help`. The full command was **not executed during baseline preparation** because it writes into the existing observation dataset directory and would regenerate tracked artefacts.

## How to run validation

The following read-only checks were executed against the 0.2.0 baseline and all exited with status 0:

```powershell
.\.venv\Scripts\python.exe tests\test_trajectory_loader.py
.\.venv\Scripts\python.exe tests\test_observation_schedule.py
.\.venv\Scripts\python.exe tests\test_observer_model.py
.\.venv\Scripts\python.exe tests\test_coordinate_converter.py
.\.venv\Scripts\python.exe tests\test_measurement_noise.py
.\.venv\Scripts\python.exe tests\test_observation_output.py
.\.venv\Scripts\python.exe tests\test_all_observation_outputs.py
.\.venv\Scripts\python.exe tests\validate_ground_truth.py
.\.venv\Scripts\python.exe tests\check_configurable_runs.py
.\.venv\Scripts\python.exe tests\validate_baseline.py
```

These scripts contain assertions or explicit validation output, but they are not a pytest suite. Some checks print only; `validate_baseline.py`, the observation-output checks and the ground-truth check are the strongest current gates.

**Not part of the read-only baseline check:**

- `tests\test_component1_integration.py` — regenerates simulation output;
- `tests\test_repeatability.py` — writes repeatability runs;
- `tests\test_tolerance_sensitivity.py` — writes tolerance runs;
- `tests\compare_trajectories.py` — writes comparison plots;
- `tests\test_horizons_loader.py`, `tests\check_horizons_epoch.py`, `tests\validate_eros_horizons.py`, `tests\validate_eros_8planets.py`, `tests\diagnose_eros_horizons.py` — require network access and/or write validation CSVs.

## Output locations

| Output | Location | Tracked? |
|---|---|---|
| Simulation trajectory | `data/runs/<simulation_name>/trajectory.csv` | Yes |
| Simulation config copy | `data/runs/<simulation_name>/config.json` | Yes |
| Simulation metadata | `data/runs/<simulation_name>/metadata.json` | Yes |
| Simulation plots | `data/runs/<simulation_name>/trajectory_*.png` | No — regenerable |
| Observations | `data/observations/<observation_name>/observations.csv` | Yes |
| Observation metadata | `data/observations/<observation_name>/metadata.json` | Yes |
| Comparison summary | `results/component-2/comparison_summary.csv` | Yes |
| Comparison figures | `results/component-2/figures/` | No — regenerable |
| Legacy plots | `plots/` | No — regenerable |

The current observation tables include both noisy `ra_deg`/`dec_deg` and noise-free `true_ra_deg`/`true_dec_deg` columns. This is a known 0.2.0 limitation and must be corrected before a blind orbit-estimation evaluation.

## Scientific assumptions and limitations

- **Frame:** heliocentric ecliptic for trajectories; equatorial coordinates are produced by a fixed obliquity rotation.
- **Units:** AU for position, AU/year for velocity, years and days for elapsed time, degrees for sky coordinates and arcseconds for angular uncertainty.
- **Time:** elapsed simulation time, not a calendar date. There is no absolute `epoch_jd_tdb` in the current datasets.
- **Year length:** 365.25 days.
- **Dynamics:** the modern scenarios include the Sun, Mercury, Venus, Earth and Jupiter; the asteroid is massless. The planetary initial conditions are simplified and approximately circular/coplanar.
- **Observer:** idealized circular, 1 AU radius, 1-year period, initially at 90° in the ecliptic plane.
- **Observation schedule:** fixed 7-day cadence from 0 to 1826.25 days.
- **Interpolation:** linear interpolation of stored positions; measured angular difference from cubic Hermite is approximately 0.223″ median and 1.731″ maximum.
- **Noise:** independent Gaussian errors, 0.5″ per coordinate, random seed 42. No covariance or correlated noise.
- **Missing physics:** no light-time correction, aberration, topocentric parallax, precession/nutation or relativistic deflection.
- **Observability:** no solar-elongation or visibility filtering. About 25.6% of current epochs have solar elongation below 30°.
- **Ground truth:** the same numerical model generates the observations and the truth; “accuracy” is model-relative, not real-world astrometric accuracy.
- **Current scope:** no orbit estimation, candidate orbits, uncertainty quantification, active selection or schedule evaluation.

## Planned future components

1. **Component 3 — Orbit estimation:** candidate-orbit representation, propagation, fitting, residuals, covariance and multi-modal candidates.
2. **Component 4 — Active observation selection:** candidate scoring, observability constraints, future observation requests and sequential selection.
3. **Component 5 — Evaluation:** equal-budget comparison of active, fixed and random schedules, with calibration over multiple seeds.

The authoritative implementation order, contracts and approval gates are in [`docs/BUILD_ROADMAP.md`](docs/BUILD_ROADMAP.md). [`docs/development/REFACTORING_PLAN.md`](docs/development/REFACTORING_PLAN.md) is retained as historical technical evidence. Those components are proposals; they are not present in the current source tree.

## Version information

- Project version: **0.2.0**, declared in `pyproject.toml`.
- Baseline record: [`docs/development/BASELINE_0.2.0.md`](docs/development/BASELINE_0.2.0.md).
- Changelog: [`CHANGELOG.md`](CHANGELOG.md).
- Build roadmap: [`docs/BUILD_ROADMAP.md`](docs/BUILD_ROADMAP.md).
- Codebase analysis: [`docs/development/CODEBASE_ANALYSIS.md`](docs/development/CODEBASE_ANALYSIS.md).
- Refactoring plan (historical): [`docs/development/REFACTORING_PLAN.md`](docs/development/REFACTORING_PLAN.md).
- Data policy: [`docs/development/DATA_VERSIONING_POLICY.md`](docs/development/DATA_VERSIONING_POLICY.md).

## License and citation

No license or citation metadata is declared in version 0.2.0. Add an explicit license and citation before public distribution if required by the host institution or journal.
