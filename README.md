# Physics-Guided Orbit Discovery Prototype

A research prototype for physics-guided asteroid orbit discovery. The project combines N-body simulation, synthetic astrometry and, in later stages, orbit estimation and active observation selection.

**Current version:** 0.5.0
**Status:** Components 1 and 2 implemented and integrated; physical consistency verified (Stage 2.7.1). Component 3 complete: Phases 1–2 (observation loader, state model, trial-orbit propagation and prediction) implemented and verified; Phase 3 (orbit fitting) complete — Phase 3B residual calculation, Phase 3C Levenberg–Marquardt optimizer, Phase 3D best-fit orbit estimation; Phase 4 reproducible multi-start candidate generation; Phase 5 local uncertainty diagnostics and candidate ensemble spread/clustering diagnostics. Components 4–5 are **not implemented**.
**Baseline:** see [`docs/development/BASELINE_0.2.0.md`](docs/development/BASELINE_0.2.0.md) and [`CHANGELOG.md`](CHANGELOG.md).

## Research motivation

Discovering and characterising asteroids from sparse astrometry requires more than fitting a curve to sky positions. The observable measurements depend on the target's dynamics, the observer's motion, the geometry of the Solar System and the times at which observations are taken. A reproducible synthetic testbed makes it possible to study those dependencies before applying a method to real survey data.

This prototype is intended to support experiments in which physical dynamics and candidate-orbit uncertainty guide the choice of the next observation. Version 0.5.0 completes the orbit estimation and candidate-orbit half of that pipeline: Component 1 simulation, Component 2 observation generation, and Component 3 Phases 1–5 (observation loader and state model, trial-orbit propagation and prediction, orbit fitting with Levenberg–Marquardt optimization, reproducible multi-start candidate generation, local uncertainty diagnostics, and candidate ensemble spread/clustering diagnostics). C1/C2 integration and physical-consistency verification are complete. Components 4–5 are **not implemented**.

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
- **Component 2:** fixed-cadence synthetic observation generation using an idealized circular observer, ecliptic-to-equatorial rotation, RA/Dec calculation and seeded Gaussian angular noise, with ground truth stored separately.
- **Component 3 (Phase 1):** strict observation loader and state model — observation dataset validation, truth separation (`true_*` columns rejected), 6D heliocentric `OrbitState`, `ObservationDataset`, `OrbitCandidate`, `BestFitResult`, `EstimationResult`.
- **Component 3 (Phase 2):** trial-orbit propagation and apparent RA/Dec prediction — REBOUND/IAS15 forward propagation matching C1's planetary model, observer geometry reconstruction from metadata, ecliptic-to-equatorial rotation, RA normalized to [0, 360), Dec clipped to [-90, 90].
- **Component 3 (Phase 3B):** wrapped right-ascension residuals (branch-cut at RA = 0/360), declination residuals (no wrapping), tangent-plane RA weighting with cos(dec) applied exactly once using the observed declination as the fixed reference, degrees-to-arcseconds conversion, normalization by `sigma_ra_cosdec_arcsec` / `sigma_dec_arcsec`, fixed residual-vector structure over pole-retained observations, pole screening (`|cos(dec)| >= 1e-12`), and the chi-square objective `chi2 = r^T r`.
- **Component 3 (Phase 3C):** NumPy-only Levenberg–Marquardt weighted nonlinear least-squares optimizer with parameter scaling (`s = [1, 1, 1, 2π, 2π, 2π]`), forward-difference Jacobian in scaled coordinates, adaptive damping, overflow/non-finite handling, residual-dimension validation, parameter validation, Jacobian accounting, and exception propagation.
- **Component 3 (Phase 3D):** best-fit orbit estimation integration orchestrating propagation → prediction → residuals with the LM optimizer; dataset validation before propagation; physical-coordinate contract; final-prediction efficiency; result model mapping with residuals dict (ndarrays only) and fit_metrics dict (floats only); Jacobian rank and valid scalar residual count diagnostics.
- **Component 3 (Phase 4):** reproducible multi-start candidate generation around the Phase 3D best-fit state — seeded Gaussian perturbations, deterministic RNG, candidate validation (finite state, finite metrics, convergence boolean, Jacobian rank exactly 6, positive DOF, reduced chi-square < threshold), deterministic ranking by reduced chi-square / chi-square / start index, duplicate detection and greedy deduplication, retention limit, complete audit record (one per start), JSON-compatible serialization with `allow_nan=False`. Ground-truth isolation enforced.
- **Component 3 (Phase 5B):** local linearized uncertainty estimation via SVD of the scaled Jacobian — physical Cartesian covariance `P_phys = diag(s) @ V diag(1/sigma^2) V.T @ diag(s)`, condition number, numerical rank, degrees of freedom (`n_valid_scalar_residuals - 6`), invalid-result reasons (non-converged, invalid Jacobian, insufficient DOF, rank-deficient, singular-value failure, non-finite covariance).
- **Component 3 (Phase 5C):** candidate ensemble diagnostics — per-coordinate spread, pairwise distances, complete-linkage clustering, cluster representatives and internal distances, assessment (insufficient_candidates / single_compact_group / multiple_separated_groups / broadly_dispersed / no_candidates).
- **CLI:** `orbit estimate` subcommand integrating the full Component 3 pipeline — load observations, best-fit estimation, local uncertainty diagnostics, multi-start candidate generation, candidate ensemble diagnostics, structured JSON output (`allow_nan=False`), exit codes 0 = success / 1 = pipeline failure / 2 = serialization error.
- **Scenarios:** standard (`e = 0.2`, `i = 0°`), eccentric (`e = 0.5`) and inclined (`e = 0.3`, `i = 10°`).
- **Data products:** trajectories, run metadata, observation tables, observation metadata and separate ground-truth files.
- **Validation:** read-only checks for trajectory schema, orbital geometry, Kepler period, integrator tolerance, frame conversion, noise reproducibility, observation-dataset integrity and truth separation; C3 focused test suites (Phase 1: 18 tests, Phase 2: 23 tests, Phase 3B residuals: 57 tests, Phase 3C optimizer: 29 tests, Phase 3D estimation: 13 tests, Phase 4 candidates: ~80 tests, Phase 5B uncertainty: 13 tests, Phase 5C diagnostics: ~40 tests, Phase 6 CLI integration, Phase 7 regression).
- **Analysis:** comparative plots and a summary table for the three observation datasets.
- **Legacy validation:** separate two-body, N-body and Eros/Horizons workflows are retained as historical evidence.
- **Integration:** C1/C2 end-to-end pipeline verified (Stage 2.7); gravitational-parameter consistency between C1 and downstream analytic modules verified and corrected (Stage 2.7.1); C2 vs C3 forward-model prediction match verified (Diagnostic 1); C1 vs C3 planetary-state match verified (Diagnostic 2); C3 initial-state preservation verified at tolerance 1e-12 AU / 1e-12 AU/yr (Diagnostic 3); C3 10-year long-span stability and conservation verified (Diagnostic 4); Phase 7 end-to-end perturbed-start orbit recovery verified to machine precision (~1e-13 AU).

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

Component 3 (Phase 1-2): observation loader and forward model
  observation CSV -> loader (validate, truth separation) -> OrbitState
  OrbitState -> build_trial_simulation -> propagate_trial_state -> predict_apparent_coordinates -> RA/Dec

Component 3 (Phase 3-5): orbit estimation
  OrbitState -> LM optimizer -> BestFitResult (estimation)
  BestFitResult -> SVD covariance -> local uncertainty (Phase 5B)
  BestFitResult -> multi-start candidates -> diagnostics (Phase 4 + Phase 5C)
  Full pipeline available via `orbit estimate` CLI subcommand

Planned, not implemented:
Component 4: active observation selection
Component 5: evaluation and schedule comparison
```

## Current implementation status

| Component | Status in 0.4.0 | Notes |
|---|---|---|
| Component 1 — N-body simulator | Implemented | Configurable synthetic scenarios; writes trajectory, config and metadata |
| Component 2 — Synthetic observations | Implemented | Fixed cadence, idealized observer, seeded Gaussian noise, truth separated into ground_truth.json |
| C1/C2 integration | Complete | End-to-end pipeline verified (Stage 2.7): 10/10 integration tests pass |
| Physical consistency (Stage 2.7.1) | Complete | Gravitational parameter aligned with C1's REBOUND model (MU_REBOUND = 39.476926421373); C1 physics untouched |
| Component 3 Phase 1 — Observation loader and state model | Implemented | `src/orbit_discovery/component3/models.py`, `loader.py`; truth separation enforced (`true_*` columns rejected) |
| Component 3 Phase 2 — Trial-orbit propagation and observation prediction | Implemented | `dynamics.py` (build_trial_simulation, propagate_trial_state), `observation_model.py` (predict_apparent_coordinates); C2 vs C3 prediction match verified (Diagnostic 1) |
| Component 3 Phase 3 — Orbit fitting | Implemented | All phases (3A-3D) complete: LM optimizer, estimation integration, multi-start candidate generation, local uncertainty diagnostics, ensemble diagnostics, and CLI integration. |
| Component 4 — Active selection | **Not implemented** | No scheduler, candidate scoring or future observation window |
| Component 5 — Evaluation | **Not implemented** | No equal-budget comparison harness or calibration study |

Do not describe Component 3 Phase 3 or Components 4–5 as working features. Component 3 Phase 1–2 are implemented and verified; see `docs/component-3/` for implementation records and Diagnostics 1–4. The analysis in [`docs/development/CODEBASE_ANALYSIS.md`](docs/development/CODEBASE_ANALYSIS.md) records the implemented/not-implemented boundary in detail.

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
├── src/                     # Python source packages (orbit_discovery.cli, orbit_discovery.component3)
├── tests/                   # Comprehensive test suite covering C1-C3 and regression scenarios
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

## How to run Component 3 (CLI)

Run the full Component 3 pipeline via the `orbit` console script installed with the package:

```powershell
orbit estimate --observations data/observations/<dataset>/observations.csv --metadata data/observations/<dataset>/metadata.json --output <output>.json
```

The `orbit estimate` subcommand performs the complete Component 3 flow:
1. Loads and validates the observation dataset (truth separation enforced).
2. Runs best-fit orbit estimation with the Levenberg–Marquardt optimizer (Phase 3D).
3. Runs local linearized uncertainty estimation via SVD of the scaled Jacobian (Phase 5B).
4. Runs reproducible multi-start candidate generation around the best-fit state (Phase 4).
5. Runs candidate ensemble diagnostics — spread, distances, clustering, assessment (Phase 5C).
6. Writes structured JSON output (`allow_nan=False`) and exits with code 0 (success), 1 (pipeline failure), or 2 (serialization error).

## How to run validation

The project uses `pytest`. Run the full suite from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -q
```

The verified result for 0.5.0: **457 passed, 1 deselected, 0 failures** (Python 3.13.9, `.venv`).

The following read-only validation scripts were also executed and all exited with status 0:

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

**End-to-end integration tests:**

`tests\test_end_to_end_integration.py` covers all 8 required C1→C2 scenarios plus 2 extras (propagate_state single epoch, orbital element round trip). All 10 pass.

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

Ground truth is stored separately from measurements: each observation dataset has a companion `ground_truth.json` with noise-free truth, while `observations.csv` contains measurement-only columns. C3-facing loaders reject any input containing `true_*` columns. This separation is enforced by `test_truth_separation_gap.py`.

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
- **Gravitational parameter:** C1 propagates with REBOUND's actual μ = 39.4769 AU³/yr² (units yr/AU/Msun). Downstream analytic modules (element conversion, observer velocity) now use `MU_REBOUND = 39.476926421373` for consistency with C1; this was corrected in Stage 2.7.1 (previously these modules declared μ = 1.0). C1 simulation physics is unchanged.
- **Current scope:** orbit estimation, candidate orbits and uncertainty quantification are implemented in Component 3 Phases 1–5. Active selection and schedule evaluation remain future work (Components 4–5).

## Planned future components

1. **Component 4 — Active observation selection:** candidate scoring, observability constraints, future observation requests and sequential selection. Not started — blocked by C3.
2. **Component 5 — Evaluation:** equal-budget comparison of active, fixed and random schedules, with calibration over multiple seeds. Not started — blocked by C3/C4.

The authoritative implementation order, contracts and approval gates are in [`docs/BUILD_ROADMAP.md`](docs/BUILD_ROADMAP.md). [`docs/development/REFACTORING_PLAN.md`](docs/development/REFACTORING_PLAN.md) is retained as historical technical evidence. Those components are proposals; they are not present in the current source tree.

## Version information

- Project version: **0.5.0**, declared in `pyproject.toml`.
- Baseline record: [`docs/development/BASELINE_0.2.0.md`](docs/development/BASELINE_0.2.0.md).
- Changelog: [`CHANGELOG.md`](CHANGELOG.md).
- Build roadmap: [`docs/BUILD_ROADMAP.md`](docs/BUILD_ROADMAP.md).
- Codebase analysis: [`docs/development/CODEBASE_ANALYSIS.md`](docs/development/CODEBASE_ANALYSIS.md).
- Refactoring plan (historical): [`docs/development/REFACTORING_PLAN.md`](docs/development/REFACTORING_PLAN.md).
- Data policy: [`docs/development/DATA_VERSIONING_POLICY.md`](docs/development/DATA_VERSIONING_POLICY.md).

## License and citation

No license or citation metadata is declared. Add an explicit license and citation before public distribution if required by the host institution or journal.
