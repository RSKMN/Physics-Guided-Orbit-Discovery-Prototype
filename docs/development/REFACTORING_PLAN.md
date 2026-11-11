# Refactoring Plan — Physics-Guided Orbit Discovery Prototype

**Project version:** 0.2.0  
**Plan date:** 2026-11-11  
**Repository root:** `<repository-root>`  
**Status:** Proposal only — **no refactoring has been implemented.**  
**Companion analysis:** `docs/development/CODEBASE_ANALYSIS.md`

> **Scope note**
>
> This document is a prioritised engineering and scientific plan. It does not modify source code, configuration files, datasets or dependencies. Every schema, interface and directory shown below is a **proposal** unless explicitly marked “existing”. The current implemented behaviour is documented in `CODEBASE_ANALYSIS.md`; it should be treated as the baseline to preserve, not as a design to assume.

---

## A. Executive Summary

### A.1 Why refactoring is necessary

The 0.2.0 prototype successfully demonstrates the first half of the project:

- a configurable REBOUND/IAS15 N-body simulator;
- a synthetic observation generator producing RA/Dec with seeded Gaussian noise;
- three reproducible scenarios and comparative figures;
- useful scientific validation (Kepler period, tolerance sensitivity, repeatability, Eros/Horizons comparisons).

However, the pipeline works **by construction for the current fixtures**, not through enforced contracts:

1. Component 2 never reads Component 1 metadata. Frame, units, epoch and state type are assumed.
2. Noise-free `true_ra_deg`/`true_dec_deg` are written into the same `observations.csv` that an estimator would consume, so the ground truth is not hidden.
3. There is no propagation interface for arbitrary candidate states/times, no absolute epoch and no future observation window.
4. Linear interpolation introduces 0.22″ median / 1.73″ maximum angular error, comparable to or larger than the 0.5″ noise.
5. Light-time (≈20″ at the current geometry), aberration, topocentric parallax and observability are not modelled.
6. The test suite is script-style, writes artefacts, and cannot be run as a normal automated suite because `pytest` is not installed.
7. The repository has no Git history, no packaging metadata, no version declaration and no CI.
8. `.gitignore` excludes all `*.json` and `*.csv`, including the scientific configurations that define the experiments.

These are not cosmetic issues. Components 3 (orbit estimation) and 4 (active observation selection) will consume these outputs, propagate candidate orbits and compare predictions with observations. If the contracts remain implicit, every integration will be built on assumptions that can silently change the scientific result.

### A.2 Desired outcome

A **0.3.0-ready foundation** in which:

- Component 1 and Component 2 are importable, packaged and runnable from a documented CLI;
- every dataset carries versioned metadata, frame/unit/time provenance and integrity checks;
- noisy observations and noise-free truth are stored separately;
- a shared propagation service can evaluate arbitrary states at arbitrary epochs;
- observation epochs can extend beyond the original simulation interval using documented dynamics;
- interpolation and missing physical effects are either corrected or explicitly modelled and recorded;
- automated tests run without writing into the repository or using the network;
- Components 3 and 4 can be developed against stable, documented contracts rather than ad hoc CSV assumptions.

### A.3 Guiding principles

1. **Preserve the science before improving it.** Keep a reproducible v0.2.0 baseline; make scientific changes opt-in and versioned.
2. **Additive, versioned contracts.** Prefer new fields/files over silently changing existing meanings.
3. **Fail fast at boundaries.** Validate schemas, units, frames and metadata when data enters a component.
4. **Separate truth from measurement.** An estimator must never see truth columns by accident.
5. **One propagation authority.** Candidate-orbit prediction, observation prediction and simulation must share the same dynamics implementation.
6. **Reproducibility is a feature.** Record seeds, versions, configuration hashes and code revision with every run.
7. **No silent assumptions.** Every approximation must be named, documented and measured.

### A.4 Scope and non-goals

**In scope for this plan:** packaging, contracts, metadata, validation, testing, scientific hardening, documentation and interface preparation.

**Not in scope now:** implementing Component 3, implementing Component 4, changing the default scientific scenario without approval, regenerating the existing datasets, or deleting legacy artefacts.

## B. Critical Issues

These issues can change the scientific result, make a result unreproducible, or block Component 3/4 integration. They should be resolved or explicitly accepted before new science code is layered on top.

### B.1 Issue register

| ID | Issue | Evidence in 0.2.0 | Consequence | Required action |
|---|---|---|---|---|
| CR-01 | Ground truth is stored with measurements | `src/observation_generator.py` writes `true_ra_deg` and `true_dec_deg` into `observations.csv` when `save_noise_free_coordinates` is true | An estimator or evaluation can accidentally use truth as input; “blind” tests are not blind | Write truth to a separate `ground_truth.csv`; make `observations.csv` contain only model inputs |
| CR-02 | Component 2 does not validate Component 1 metadata | `src/trajectory_loader.py` validates columns only; `src/observation_generator.py` reads `input_trajectory` and assumes frame/units | A frame, unit or epoch change in Component 1 passes silently | Require and validate a versioned run manifest; fail with a precise error when absent |
| CR-03 | No general propagation interface | Component 1 writes a fixed trajectory; no API accepts an arbitrary state and epoch | Component 3 cannot predict candidate orbits; Component 4 cannot score schedules | Extract a propagation service used by simulation and prediction |
| CR-04 | Linear interpolation is used for observations | `src/observation_schedule.py::interpolate_positions` performs linear interpolation | 0.22″ median / 1.73″ maximum error, comparable to the 0.5″ noise; biases residuals | Use dynamics-aware interpolation (Hermite first) or integrate at observation epochs; measure and version the change |
| CR-05 | Light-time and aberration are absent | `src/observation_generator.py` computes instantaneous geometry only | ≈20″ light-time offset at current geometry; RA/Dec are not what a real observer would measure | Add light-time correction and document aberration/topocentric status; version the output |
| CR-06 | Frame, epoch and units are implicit | CSV columns such as `x_au`; no `frame`, `time_scale`, `epoch_jd_tdb` in trajectory data | Consumers must guess; future absolute-time work will mix conventions | Add explicit provenance; keep elapsed-time runs explicit and nullable absolute epochs |
| CR-07 | No future observation window | All observation schedules end at 1826.25 d, inside the 5-year simulation | Component 4 cannot ask “what if we observe later?”; active selection is impossible | Define a propagation-backed future window and a request/reveal contract |
| CR-08 | Script entry point is broken | `python src/observation_generator.py --help` raises `ModuleNotFoundError: No module named 'src...'` | Documented or intuitive invocation fails; automation is brittle | Add package install and console scripts; support `python -m` and installed entry points |
| CR-09 | No automated test suite | 19 scripts are run manually; `python -m pytest` fails because pytest is absent | Regressions are likely during refactoring; no CI gate | Introduce pytest, fixtures, markers and CI; keep scripts as thin wrappers |
| CR-10 | No version control or packaging metadata | `.git` absent; no `pyproject.toml`; version 0.2.0 is only a label | Changes cannot be diffed, bisected or released reproducibly | Initialise Git, add `pyproject.toml`, tag the baseline |
| CR-11 | `.gitignore` excludes scientific configs | `.gitignore` ignores `*.json` and `*.csv`; configs are JSON | A clone would not contain the experiments | Whitelist `configs/`, schemas and small fixtures; ignore only generated artefacts |
| CR-12 | No schema versioning | CSV and metadata have no `schema_version` | A future column/unit change is indistinguishable from the old format | Version every artefact and validate supported versions |
| CR-13 | Identical noise realisations across scenarios | All three observation configs use the same seed and produce correlated noise patterns | Cross-scenario comparisons are not independent; uncertainty estimates can be optimistic | Use per-scenario seeds and support multi-seed ensembles |
| CR-14 | Reproducibility depends on working directory | Paths are resolved relative to `PROJECT_ROOT` and scripts assume repository CWD | Runs from another directory can fail or mix outputs | Resolve paths from an explicit project/config root; test from a temporary CWD |

### B.2 Critical-path interpretation

CR-01, CR-02, CR-03 and CR-07 are the gating items for Components 3 and 4. CR-04 and CR-05 determine whether the synthetic measurements are scientifically credible at the stated noise level. CR-08 to CR-14 determine whether the work can be maintained and reproduced. None of these requires deleting the existing prototype: the safe pattern is to keep v0.2.0 artefacts as a frozen baseline, introduce v2 contracts, and regenerate new datasets under new names.

---

## C. High-Priority Improvements

These should be completed **before** Component 3 implementation begins. Each item has a concrete acceptance test.

### C.1 Package and entry points

- [ ] Add `pyproject.toml` with a `src` layout, project metadata, Python requirement and optional dependency groups (`sim`, `analysis`, `network`, `test`).
- [ ] Add console entry points for simulation, observation generation and validation.
- [ ] Make `python -m src.observation_generator` and the installed command behave identically.
- [ ] Remove implicit repository-CWD and import-path assumptions.
- [ ] Document the supported Python version and a clean installation procedure.

**Acceptance:** a fresh environment can install the package and run `--help` for all entry points; no `ModuleNotFoundError`; the commands work from a directory outside the repository.

### C.2 Define versioned data contracts

- [ ] Write schema documents for trajectory, observations, ground truth, run metadata and observation metadata.
- [ ] Add `schema_version` and `producer_version` to every artefact.
- [ ] Add field-level units, frame, time scale and nullability.
- [ ] Add validators that reject unknown critical fields and malformed rows.
- [ ] Keep a compatibility table for v1 → v2.

**Acceptance:** malformed fixtures fail with actionable errors; valid v1 files remain readable through an explicit compatibility path; v2 files declare their contract.

### C.3 Separate observations from ground truth

- [ ] Stop writing `true_*` columns into the estimator-facing `observations.csv`.
- [ ] Write `ground_truth.csv` (or `truth/` dataset) containing the noise-free RA/Dec and the true state used to generate each epoch.
- [ ] Record in metadata that truth is evaluation-only.
- [ ] Provide a migration note for consumers of the current combined CSV.

**Acceptance:** an estimator can be pointed at `observations.csv` without any truth column being present; evaluation code requires an explicit truth path.

### C.4 Make Component 2 consume Component 1 metadata

- [ ] Define the required run-manifest fields: frame, position/velocity units, time convention, epoch, integrator, bodies, state type and schema version.
- [ ] Validate the manifest before loading the trajectory.
- [ ] Reject mismatched frame/unit/time declarations instead of assuming defaults.
- [ ] Record the input manifest hash in the observation metadata.

**Acceptance:** changing a declared frame or unit causes a deterministic validation failure; a matching manifest passes and is recorded in the output provenance.

### C.5 Provide a shared propagation service

- [ ] Extract simulation setup and state propagation from `src/configurable_simulator.py` into a reusable module.
- [ ] Support “propagate this state to these epochs” without writing a full trajectory CSV.
- [ ] Support both the current synthetic planetary setup and a documented real-ephemeris backend.
- [ ] Use the same service for Component 1 output and future candidate-orbit prediction.
- [ ] Define behaviour outside the original time span (error, extend, or explicit extrapolation).

**Acceptance:** a candidate state can be propagated to a requested epoch in a unit test; the result matches the simulator at shared epochs within a stated tolerance; out-of-range requests have defined behaviour.

### C.6 Harden the observation geometry

- [ ] Replace linear interpolation with cubic Hermite using position and velocity, or integrate at observation epochs.
- [ ] Quantify the old and new interpolation error against the same reference.
- [ ] Add light-time correction as an explicit, recorded option.
- [ ] Document the status of aberration, topocentric parallax, precession/nutation and relativistic deflection.
- [ ] Store per-epoch observer position, range and solar elongation.
- [ ] Mark or exclude epochs below a configurable elongation limit; do not silently drop them.

**Acceptance:** a new observation dataset records the interpolation method, light-time flag and visibility flags; the measured error is below the noise budget or explicitly reported as a bias.

### C.7 Reproducibility and provenance

- [ ] Record Python and package versions, run timestamp, configuration hash, input hashes and code revision.
- [ ] Support distinct seeds per scenario and multi-seed ensembles.
- [ ] Make output directories collision-safe and explicit.
- [ ] Keep generated data out of version control but keep configs and schemas in it.

**Acceptance:** rerunning the same config with the same seed reproduces byte-identical measurements; changing the seed changes the noise but not the truth.

### C.8 Automated validation before Component 3

- [ ] Install and pin `pytest` in the test dependency group.
- [ ] Convert read-only checks into pytest tests with temporary output directories.
- [ ] Separate unit, integration, network and slow markers.
- [ ] Add CI for lint, unit tests and contract validation.
- [ ] Keep data-writing scripts as opt-in integration tests.

**Acceptance:** `pytest -m "not network and not slow"` passes in a clean checkout without writing into `data/`; contract tests fail on a deliberately corrupted fixture.

## D. Medium-Priority Improvements

These improve maintainability, modularity, naming, testing and organisation after the critical contracts are in place.

### D.1 Modularity and code organisation

- [ ] Split `src/` into a real package (`src/orbit_discovery/`) with `core/`, component packages and `cli/`.
- [ ] Move shared constants (`DAYS_PER_YEAR`, `ARCSEC_TO_DEG`, `AU_KM`, `OBLIQUITY_DEG`) into one module.
- [ ] Extract one configuration loader with schema validation; replace the duplicated `load_config` functions in Component 1 and Component 2.
- [ ] Extract one path-resolution policy that takes an explicit project root instead of relying on module import location.
- [ ] Extract one atomic CSV/JSON writer with hashing and manifest support.
- [ ] Replace the duplicated ecliptic-to-equatorial math in analysis scripts with the library function.
- [ ] Separate libraries from executable scripts: `cli/` should be thin wrappers, not the only API.
- [ ] Remove hardcoded dataset name lists from `src/compare_observation_datasets.py`; discover datasets from a manifest or CLI arguments.
- [ ] Move legacy diagnostics and one-off validation scripts into `scripts/legacy/` or `archive/`.

**Acceptance:** no component imports another component’s private module; shared helpers have one implementation; scripts contain no scientific formulas beyond argument parsing.

### D.2 Naming and interfaces

- [ ] Use consistent scientific names: `epoch`, `time_days`, `jd_tdb`, `frame`, `sigma_arcsec`, `elongation_deg`.
- [ ] Avoid ambiguous names such as `time_years` without a stated time scale; keep it only as a derived convenience field.
- [ ] Use `snake_case` for columns and functions; use unit suffixes consistently.
- [ ] Add type hints to public functions and dataclasses for states, epochs, observations and solutions.
- [ ] Document whether arrays are `(3,)`, `(N, 3)` or `(3, N)`; standardise on `(N, 3)` for time series.
- [ ] Define public `__all__` exports for each package.

**Acceptance:** a new contributor can infer units and array shapes from signatures and schema docs without reading implementation details.

### D.3 Testing and validation

- [ ] Create `tests/conftest.py` with fixtures for a tiny trajectory, a tiny observation set and a temporary output root.
- [ ] Split tests into `unit/`, `integration/`, `regression/` and `scientific/`.
- [ ] Add regression tests against frozen v0.2.0 summary values (period, interpolation error, count, noise statistics).
- [ ] Add property tests for coordinate round-trips, time conversion and frame rotation.
- [ ] Add contract tests that corrupt a required field and assert a clear failure.
- [ ] Add a test that the estimator-facing file contains no `true_*` columns.
- [ ] Add a test that all entry points run from a temporary working directory.
- [ ] Mark network and slow tests; never require them for the default suite.

**Acceptance:** the default test suite is hermetic, fast and deterministic; scientific regression thresholds are documented.

### D.4 Configuration and reproducibility

- [ ] Define a JSON Schema for simulation, observation, estimation and selection configs.
- [ ] Validate configs before execution; reject unknown critical keys and missing required keys.
- [ ] Support relative paths resolved against the config file or an explicit `--project-root`.
- [ ] Record a copy of the effective config and its SHA-256 in every output manifest.
- [ ] Add a `--dry-run` mode that validates inputs and prints planned outputs without writing.
- [ ] Add `--seed` override and per-scenario seed fields.
- [ ] Add `--output-dir` so tests and experiments do not write into `data/`.

**Acceptance:** a config and seed fully determine the measurement file; output location is independent of the current working directory.

### D.5 Performance and numerical hygiene

- [ ] Avoid recomputing the full N-body simulation when only observation geometry changes; cache trajectory plus metadata.
- [ ] Vectorise interpolation and coordinate conversion where profiling shows benefit.
- [ ] Use `np.searchsorted` with explicit bounds and tests at the first/last epoch.
- [ ] Record integrator tolerance and test convergence at a second tolerance.
- [ ] Add finite-value and monotonic-time checks at load time.
- [ ] Handle RA wraparound explicitly in residuals and plots.

**Acceptance:** performance changes do not alter results beyond documented tolerances; edge epochs are covered by tests.

### D.6 Documentation for maintainers

- [ ] Add `README.md` with implemented/not-implemented status, quickstart and data layout.
- [ ] Add `docs/development/architecture.md` with component boundaries and data flow.
- [ ] Add `docs/development/testing.md` describing markers, fixtures and how to run each suite.
- [ ] Add `docs/schemas/` for every versioned artefact.
- [ ] Add Architecture Decision Records for frame, time, units, interpolation, light-time and truth separation.
- [ ] Add a changelog and a release checklist.

**Acceptance:** the documented quickstart works in a clean environment; each scientific approximation links to an ADR.

---

## E. Low-Priority Improvements

Optional work that improves polish, ergonomics or long-term cost without blocking Component 3.

- [ ] Add `ruff`/`black`/`isort` configuration and pre-commit hooks.
- [ ] Add docstring coverage checks and a documentation build.
- [ ] Add `LICENSE`, `CITATION.cff` and `CONTRIBUTING.md`.
- [ ] Add issue/PR templates and a code of conduct.
- [ ] Replace repetitive matplotlib styling with shared helpers.
- [ ] Add a small dashboard or notebook index for scenario comparison.
- [ ] Add optional Parquet output for large ensembles; keep CSV as the interchange format.
- [ ] Add benchmark scripts for propagation and interpolation throughput.
- [ ] Add a `--quiet`/`--verbose` logging switch and structured logs.
- [ ] Add shell completion for CLI commands.
- [ ] Add a generated API reference.
- [ ] Add archived examples for the legacy Eros/Horizons workflow.
- [ ] Improve plot labels, colour-blind-safe palettes and consistent figure sizes.
- [ ] Add a `make`/`tox`/`nox` task runner if it reduces command duplication.

**Acceptance:** none of these changes alter scientific outputs; they are safe to defer.

---

## F. Proposed Directory Structure

The structure below is a **proposal**. It preserves the current top-level separation while giving each component a package boundary, separating generated artefacts from curated data, and making contracts discoverable.

```text
physics-guided-orbit-discovery-prototype/
├── README.md
├── LICENSE
├── CITATION.cff
├── CHANGELOG.md
├── CONTRIBUTING.md
├── pyproject.toml
├── .gitignore
├── .pre-commit-config.yaml
├── .github/
│   └── workflows/ci.yml
├── configs/
│   ├── simulation/
│   │   ├── synthetic_asteroid.json
│   │   ├── synthetic_asteroid_eccentric.json
│   │   └── synthetic_asteroid_inclined.json
│   ├── observations/
│   │   ├── synthetic_asteroid.json
│   │   ├── synthetic_asteroid_eccentric.json
│   │   └── synthetic_asteroid_inclined.json
│   ├── estimation/
│   ├── selection/
│   └── experiments/
├── src/
│   └── orbit_discovery/
│       ├── __init__.py
│       ├── version.py
│       ├── core/
│       │   ├── constants.py
│       │   ├── time.py
│       │   ├── units.py
│       │   ├── frames.py
│       │   ├── io.py
│       │   ├── validation.py
│       │   ├── logging.py
│       │   └── errors.py
│       ├── propagation/
│       │   ├── bodies.py
│       │   ├── initial_conditions.py
│       │   ├── simulator.py
│       │   └── service.py
│       ├── component1_simulation/
│       │   ├── trajectory.py
│       │   ├── metadata.py
│       │   └── plotting.py
│       ├── component2_observations/
│       │   ├── loader.py
│       │   ├── schedule.py
│       │   ├── observer.py
│       │   ├── geometry.py
│       │   ├── noise.py
│       │   ├── truth.py
│       │   ├── generator.py
│       │   └── plotting.py
│       ├── component3_estimation/
│       │   ├── model.py
│       │   ├── fitter.py
│       │   ├── candidates.py
│       │   └── uncertainty.py
│       ├── component4_selection/
│       │   ├── scoring.py
│       │   ├── selector.py
│       │   └── schedules.py
│       ├── evaluation/
│       │   ├── metrics.py
│       │   ├── baselines.py
│       │   └── report.py
│       └── cli/
│           ├── simulate.py
│           ├── observe.py
│           ├── estimate.py
│           ├── select.py
│           └── evaluate.py
├── tests/
│   ├── conftest.py
│   ├── unit/
│   ├── integration/
│   ├── regression/
│   ├── scientific/
│   └── fixtures/
├── data/
│   ├── curated/                      # small, versioned reference data
│   └── README.md
├── artifacts/                        # generated, gitignored
│   ├── runs/
│   ├── observations/
│   ├── truth/
│   ├── estimates/
│   └── evaluation/
├── experiments/
│   ├── 001_baseline/
│   └── notebooks/
├── results/                          # curated tables/figures for reports
├── docs/
│   ├── index.md
│   ├── user/
│   ├── components/
│   ├── schemas/
│   ├── development/
│   │   ├── architecture.md
│   │   ├── CODEBASE_ANALYSIS.md
│   │   ├── REFACTORING_PLAN.md
│   │   ├── testing.md
│   │   └── release-process.md
│   ├── experiments/
│   └── adr/
└── scripts/
    └── legacy/                       # frozen one-off diagnostics
```

| Directory | Purpose | Rule |
|---|---|---|
| `src/orbit_discovery/` | Importable library and component boundaries | All reusable code lives here |
| `src/orbit_discovery/core/` | Shared constants, time, units, frames, I/O, validation | No component-specific science |
| `src/orbit_discovery/propagation/` | One dynamics/propagation authority | Used by Components 1, 3 and 4 |
| `src/orbit_discovery/component1_simulation/` | Scenario setup and trajectory output | Writes run manifests and trajectories |
| `src/orbit_discovery/component2_observations/` | Observation scheduling, geometry, noise, truth | Reads run manifests; writes separate truth |
| `src/orbit_discovery/component3_estimation/` | Planned orbit fitting and candidate generation | Not implemented in 0.2.0 |
| `src/orbit_discovery/component4_selection/` | Planned active scheduling | Not implemented in 0.2.0 |
| `src/orbit_discovery/evaluation/` | Metrics, baselines, reports | Evaluation may read truth; estimators may not |
| `src/orbit_discovery/cli/` | Thin command-line wrappers | No science logic |
| `configs/` | Versioned experiment definitions | Tracked in Git |
| `data/curated/` | Small reference data needed for tests/docs | Tracked; no large generated runs |
| `artifacts/` | Generated runs, observations, truth, estimates | Gitignored; reproducible from configs |
| `results/` | Curated figures/tables cited in reports | Tracked selectively |
| `tests/` | Hermetic automated tests and tiny fixtures | No network by default |
| `docs/` | User, component, schema, development and ADR docs | Contracts live here |
| `scripts/legacy/` | Frozen one-off diagnostics | Not part of the supported API |

## G. Component-Level Refactoring

### G.1 Component 1 — N-body Simulator

**Current implementation:** `src/configurable_simulator.py` builds a REBOUND simulation from a JSON config, integrates with IAS15, writes `trajectory.csv`, `metadata.json` and a plot. `src/trajectory_loader.py` validates the trajectory columns. `src/horizons_loader.py` and the Eros scripts provide external-state and validation workflows.

**Why it needs work:** the simulator is a script, not a reusable service. It writes a fixed time series rather than exposing “propagate this state to these epochs”. Metadata is rich but not validated by downstream code. The planetary setup, constants and output schema are embedded in one module.

**Refactoring checklist:**

- [ ] Define `BodySpec`, `SystemSpec` and `SimulationSpec` dataclasses with explicit units.
- [ ] Extract `build_system()` and `propagate_states()` into `propagation/`.
- [ ] Keep `simulator.py` as the scenario orchestrator; it should call the service, not duplicate dynamics.
- [ ] Support propagation of an arbitrary state vector to an arbitrary epoch array without writing a full run.
- [ ] Add a run manifest with `schema_version`, `producer_version`, frame, units, time convention, epoch, integrator, tolerance, bodies, masses, initial state and config hash.
- [ ] Record whether the trajectory is synthetic elapsed time or tied to an absolute `jd_tdb`.
- [ ] Save the full initial planetary system state so a run can be reproduced without re-reading the config.
- [ ] Add finite-value, monotonic-time and duplicate-epoch validation.
- [ ] Use atomic writes so a failed run does not leave a partial `trajectory.csv`.
- [ ] Move one-off Eros/Horizons diagnostics to `scripts/legacy/`.
- [ ] Add unit tests for two-body period/energy and regression tests for the three synthetic scenarios.

**Acceptance:** a test can build the standard system, propagate one state to five epochs, and match the full-run trajectory at those epochs within a documented tolerance. A missing or inconsistent manifest field fails before integration.

**Do not change silently:** the current planetary setup, IAS15 tolerance, AU/year velocity convention or 365.25-day year. Any change must be a new scenario or a versioned contract change with before/after validation.

### G.2 Component 2 — Synthetic Observation Generator

**Current implementation:** `src/observation_generator.py` loads a trajectory, generates observation times, interpolates positions, computes an idealized circular observer, converts ecliptic to equatorial, computes RA/Dec, adds seeded Gaussian noise and writes observations plus metadata. Supporting modules are `observation_schedule.py`, `observer_model.py`, `coordinate_converter.py`, `measurement_noise.py` and `trajectory_loader.py`.

**Why it needs work:** it is the boundary between simulation and estimation, yet it assumes the trajectory contract, mixes truth with measurements, uses interpolation that is coarser than the noise, omits light-time, and cannot produce future observations for active selection.

**Refactoring checklist:**

- [ ] Fix the entry point: package-relative imports, console script and `python -m` support.
- [ ] Read and validate the Component 1 manifest before loading the trajectory.
- [ ] Refuse frame/unit/time mismatches; no silent defaults for critical fields.
- [ ] Replace linear interpolation with cubic Hermite using position and velocity, or integrate at observation epochs.
- [ ] Record the interpolation method and measured accuracy in metadata.
- [ ] Add optional light-time correction with an explicit flag and documented iteration/convergence.
- [ ] Document aberration, topocentric parallax, precession/nutation and relativistic deflection as modelled or not modelled.
- [ ] Persist per-epoch observer position, observer velocity, range, phase angle and solar elongation.
- [ ] Add a `visible` flag with a configurable elongation threshold; never drop rows silently.
- [ ] Split `observations.csv` (measurements only) from `ground_truth.csv` (noise-free RA/Dec, true state, true range).
- [ ] Add a documented `predict_sky()` function that can be reused by Component 3 and Component 4.
- [ ] Use per-scenario seeds and support `seed` override and multi-seed ensembles.
- [ ] Record the effective config, input hashes and code revision in metadata.
- [ ] Make output directory and dataset name explicit; avoid CWD-dependent paths.
- [ ] Keep a v1 compatibility reader for the current three datasets.
- [ ] Add tests for column separation, interpolation accuracy, light-time flag, elongation flags and reproducibility.

**Acceptance:** a new dataset has separate measurement/truth files, a validated manifest, recorded geometry and method flags, and measurements reproducible from the config and seed. The estimator-facing file contains no truth columns.

**Scientific caution:** changing interpolation or adding light-time changes the measurements. Do not overwrite v0.2.0 datasets. Create `*_v2` datasets, report the difference, and keep the old ones for regression.

### G.3 Component 3 — Orbit Estimation (planned; not implemented)

**Current state:** no estimator, no candidate-orbit model, no fitting code, no covariance implementation and no orbit-solution schema exist in 0.2.0.

This section defines readiness requirements, not an implementation. Component 3 should not begin until the contracts in H are accepted.

**Proposed scope:**

- Ingest measurement-only observations plus observer geometry/epoch metadata.
- Model a candidate orbit with explicit parameterisation (initial Keplerian elements or Cartesian state at a reference epoch).
- Propagate candidates with the shared propagation service.
- Predict sky coordinates including observer geometry and light-time policy.
- Fit parameters, report residuals, covariance and convergence diagnostics.
- Generate and rank multiple candidates when the fit is multimodal.
- Never read `ground_truth.csv` during fitting.

**Readiness checklist:**

- [ ] A stable observation contract with epochs, observer states and uncertainties exists.
- [ ] A shared propagation service can evaluate a candidate at arbitrary observation epochs.
- [ ] A candidate/orbit-solution schema is agreed.
- [ ] The residual convention is defined (RA·cosDec, Dec; arcseconds; wrap handling).
- [ ] The noise/covariance model is documented, including correlations.
- [ ] A synthetic self-consistency test can recover a known orbit from noiseless data.
- [ ] A noisy recovery test reports bias and coverage over multiple seeds.
- [ ] The estimator cannot access truth through its input path.

**Open design decisions requiring approval:** parameterisation, optimizer, priors/regularisation, outlier policy, covariance method, candidate-generation strategy and whether the fit uses Keplerian or N-body dynamics. Each choice changes the scientific meaning of the result and should be recorded in an ADR.

**Acceptance for starting Component 3:** the first seven readiness items are satisfied; the eighth is enforced by a test.

### G.4 Component 4 — Active Observation Selection (planned; not implemented)

**Current state:** no scheduler, no candidate scoring, no future observation window, no reveal mechanism and no equal-budget evaluation harness.

Component 4 depends on Components 1–3 and on a future-observation contract. It cannot be implemented responsibly by extending the current fixed schedule alone.

**Proposed scope:**

- Represent an observation request as a time (and optionally a target/filter), not a hardcoded cadence.
- Propagate the candidate ensemble to candidate times using the shared service.
- Score candidate times by expected information gain, separation of candidates, or uncertainty reduction.
- Respect constraints: solar elongation, observability, cadence, budget, slew/settling and data volume.
- Choose the next observation sequentially from the current history.
- Receive the “revealed” noisy measurement for the chosen time from a simulator/evaluator.
- Compare against fixed-cadence, random and oracle baselines at equal budget.

**Readiness checklist:**

- [ ] A future window exists and is backed by propagation, not extrapolation of a stored CSV.
- [ ] A candidate ensemble with uncertainty is available from Component 3.
- [ ] A scoring function and constraints are specified.
- [ ] A reveal API returns a measurement without exposing truth to the selector.
- [ ] An evaluation harness enforces equal observation budget and multiple seeds.
- [ ] Baselines are defined before the active policy is judged.
- [ ] Counterfactual dynamics (what would have been observed at an unobserved time) are supported by the propagation service.

**Proposed policy interface (proposal, not existing):**

```python
class SchedulePolicy(Protocol):
    def next_observation(
        self,
        history: ObservationSet,
        candidates: CandidateEnsemble,
        constraints: ObservabilityConstraints,
        rng: np.random.Generator,
    ) -> ObservationRequest: ...
```

**Acceptance for starting Component 4:** all seven readiness items are satisfied, and a dry-run selector can choose from a small candidate grid without access to truth.

## H. Integration Contracts

> **Status: proposals, not existing functionality.** The current files use the implicit v1 conventions described in `CODEBASE_ANALYSIS.md`. The v2 contracts below are recommendations for the refactor. They must be reviewed and accepted before Component 3 code is written.

### H.1 Contract principles

1. **Explicit over implicit.** Every file declares its schema, frame, units and time convention.
2. **Separate measurement from truth.** Estimators receive measurements and metadata only; evaluation receives truth through a separate path.
3. **One canonical representation.** Internally use SI-like astronomy units with documented conversions; expose only declared units at file boundaries.
4. **Fail closed.** Unknown schema versions, missing critical metadata or inconsistent units are errors, not warnings.
5. **Atomic and immutable outputs.** Write to a temporary path, validate, then rename. Never mutate a completed dataset in place.
6. **Hash and provenance.** Record config and input hashes so a dataset can be traced to its source.
7. **Backward-compatible readers.** Keep a v1 reader for the current datasets; new writers emit v2.

### H.1.1 Data formats and encoding

- **CSV** is the tabular interchange format: UTF-8, header row, no index column, `.` decimal separator, one record per line, documented null representation.
- **JSON** is the manifest/solution format: UTF-8, ISO-8601 UTC timestamp strings, no comments, explicit `schema_version`.
- **Names** are `snake_case`; unit suffixes are part of the column name (for example, `_au`, `_deg`, `_arcsec`).
- **No implicit conversions** on read. A reader either accepts the declared unit or fails.
- **Parquet** may be added later for large ensembles, but CSV/JSON remain the reference formats for the prototype.

### H.2 Trajectory contract (proposed v2, additive to v1)

**File:** `trajectory.csv` inside a run directory.

| Column | Type | Unit | Required | Meaning |
|---|---|---|---|---|
| `time_days` | float | day | yes | Elapsed time from the run reference epoch |
| `time_years` | float | year | yes | `time_days / 365.25`; derived, retained for compatibility |
| `epoch_jd_tdb` | float or null | JD TDB | no | Absolute epoch; null for synthetic elapsed-time runs |
| `x_au`, `y_au`, `z_au` | float | AU | yes | Heliocentric ecliptic position |
| `vx_au_per_year`, `vy_au_per_year`, `vz_au_per_year` | float | AU/year | yes | Heliocentric ecliptic velocity |

**Required run-manifest fields:** `schema_version`, `producer`, `producer_version`, `created_utc`, `frame`, `position_unit`, `velocity_unit`, `time_scale`, `reference_epoch_jd_tdb` (nullable), `time_zero_definition`, `state_type`, `integrator`, `integrator_epsilon`, `bodies`, `masses`, `initial_state`, `config_sha256`, `trajectory_sha256`.

**Frame definition:** `heliocentric_ecliptic` means Sun-centred Cartesian coordinates with the ecliptic as the xy plane and a stated equinox/epoch. The current prototype does not distinguish J2000 from another equinox; v2 must state it (recommended: J2000/ICRF-aligned ecliptic).

**Invariants:** finite values; strictly increasing `time_days`; no duplicate epochs; `time_years` consistent with `time_days`; velocity unit declared; no silent unit conversion on load.

### H.3 Observation contract (proposed v2, measurement-only)

**File:** `observations.csv` inside an observation dataset directory.

| Column | Type | Unit | Required | Meaning |
|---|---|---|---|---|
| `obs_id` | string | — | yes | Stable identifier, unique within the dataset |
| `time_days` | float | day | yes | Elapsed time from the run reference epoch |
| `time_years` | float | year | yes | Derived convenience field |
| `epoch_jd_tdb` | float or null | JD TDB | no | Absolute epoch; null for synthetic runs |
| `ra_deg` | float | degree | yes | Noisy right ascension; [0, 360) |
| `dec_deg` | float | degree | yes | Noisy declination; [−90, 90] |
| `sigma_ra_cosdec_arcsec` | float | arcsec | yes | 1σ uncertainty on RA·cos(Dec), tangent-plane convention |
| `sigma_dec_arcsec` | float | arcsec | yes | 1σ uncertainty on Dec |
| `correlation_radec` | float or null | — | no | Correlation coefficient, if modelled; null means independent |
| `observer_x_au`, `observer_y_au`, `observer_z_au` | float | AU | yes | Observer position at the observation epoch |
| `observer_vx_au_per_year`, `observer_vy_au_per_year`, `observer_vz_au_per_year` | float | AU/year | proposed | Observer velocity, needed for aberration/light-time |
| `range_au` | float | AU | proposed | Observer–target distance |
| `elongation_deg` | float | degree | proposed | Solar elongation at the epoch |
| `phase_angle_deg` | float | degree | proposed | Sun–target–observer phase angle |
| `visible` | bool | — | proposed | Whether the epoch passes configured observability constraints |
| `filter` | string or null | — | no | Photometric band, if applicable |

**Forbidden columns:** `true_ra_deg`, `true_dec_deg`, `true_x_au`, `true_*` of any kind. Truth belongs in `ground_truth.csv`.

**Required observation-manifest fields:** `schema_version`, `producer`, `producer_version`, `created_utc`, `input_run_manifest`, `input_trajectory_sha256`, `config_sha256`, `observation_model`, `observer_model`, `frame`, `units`, `time_scale`, `interpolation_method`, `light_time_correction` (bool plus model), `aberration` (bool/model), `topocentric` (bool/model), `noise_model`, `random_seed`, `number_of_observations`, `truth_file`, `truth_schema_version`.

### H.4 Ground-truth contract (proposed v2)

**File:** `ground_truth.csv` inside a separate `truth/` directory, not inside the measurement dataset directory.

| Column | Type | Unit | Required | Meaning |
|---|---|---|---|---|
| `obs_id` | string | — | yes | Matches `observations.csv` |
| `epoch_jd_tdb` | float or null | JD TDB | no | Absolute epoch |
| `true_ra_deg`, `true_dec_deg` | float | degree | yes | Noise-free model coordinates |
| `true_x_au`, `true_y_au`, `true_z_au` | float | AU | yes | True target position |
| `true_vx_au_per_year`, `true_vy_au_per_year`, `true_vz_au_per_year` | float | AU/year | yes | True target velocity |
| `true_range_au` | float | AU | yes | True observer–target distance |
| `true_elongation_deg` | float | degree | proposed | True geometry |

**Access rule:** only evaluation, validation and reporting code may read truth. Estimators and selectors must reject paths containing a truth file. The observation manifest must state `truth_separation: true` and name the truth file.

### H.5 Metadata and provenance contract (proposed v2)

Every run or dataset directory must contain a manifest with at least:

| Group | Fields |
|---|---|
| Identity | `schema_version`, `producer`, `producer_version`, `created_utc`, `dataset_id` |
| Source | `config_path` (relative), `config_sha256`, `input_files` with hashes, `code_revision` |
| Environment | Python version, package versions, platform, integrator version |
| Science | `frame`, `position_unit`, `velocity_unit`, `time_scale`, `reference_epoch_jd_tdb`, `state_type`, `dynamics_model`, `observer_model`, `noise_model` |
| Approximations | `interpolation_method`, `light_time_correction`, `aberration`, `topocentric`, `relativity`, `precession_nutation` |
| Contents | row count, column list, file sizes, `trajectory_sha256`/`observations_sha256`, truth separation flag |
| Quality | validation status, warnings, known limitations |

**Example (illustrative only, not a real file):**

```json
{
  "schema_version": "2.0",
  "producer": "orbit_discovery.component2_observations",
  "producer_version": "0.3.0",
  "created_utc": "2026-11-11T00:00:00Z",
  "frame": "heliocentric_ecliptic",
  "time_scale": "elapsed",
  "reference_epoch_jd_tdb": null,
  "interpolation_method": "cubic_hermite",
  "light_time_correction": true,
  "truth_separation": true,
  "truth_file": "ground_truth.csv",
  "random_seed": 20261111
}
```

### H.6 Orbit-solution contract (proposed; Component 3 not implemented)

**File:** `orbit_solution.json` (plus optional `candidates.csv` for ensembles).

| Field | Type | Meaning |
|---|---|---|
| `schema_version` | string | Contract version |
| `solution_id` | string | Stable identifier |
| `input_observations` | string + hash | Dataset used |
| `reference_epoch_jd_tdb` | float or null | Epoch of the fitted state/elements |
| `parameterisation` | string | `keplerian` or `cartesian` |
| `elements` | object | `a_au`, `e`, `i_deg`, `raan_deg`, `argp_deg`, `mean_anomaly_deg`, `epoch_jd_tdb` |
| `state` | object | Cartesian position/velocity at the reference epoch, if used |
| `covariance` | array | 6×6 covariance with documented parameter order and units |
| `residuals` | array/object | Per-observation residuals and weights |
| `chi2`, `dof`, `rms_arcsec` | float | Fit quality |
| `converged` | bool | Optimizer status |
| `candidates` | array | Alternative solutions, each with a score and provenance |
| `model` | object | Dynamics, light-time and noise assumptions |
| `created_utc`, `producer_version` | string | Provenance |

**Rule:** the solution must state which observations and which model produced it. A solution without covariance and residual diagnostics is not sufficient for Component 4.

### H.7 Observation request and reveal contract (proposed; Component 4 not implemented)

Component 4 needs a way to ask for a future observation and receive a measurement without seeing truth. Proposed flow:

```text
Selector -> ObservationRequest -> Simulator/Evaluator -> Measurement -> Selector
                                     |
                                     +-> TruthRecord (withheld from selector)
```

**`ObservationRequest` (proposal):**

| Field | Type | Meaning |
|---|---|---|
| `request_id` | string | Unique request identifier |
| `earliest_epoch_jd_tdb` | float | Earliest allowed epoch |
| `latest_epoch_jd_tdb` | float | Latest allowed epoch |
| `target_id` | string | Target identifier |
| `filter` | string or null | Optional band |
| `priority` | float | Optional scheduling priority |
| `constraints` | object | Elongation, cadence, slew/settling, budget |

**`Measurement` (proposal):** a row conforming to H.3, returned only after the request is executed. The corresponding truth row is written to a truth store that the selector cannot read.

**Rules:** equal-budget evaluation counts executed requests, not candidate evaluations; failed or infeasible requests are recorded; the selector receives no truth and no noise realisation before committing to the request.

### H.8 Frames, units and time conventions

**Frames:**

| Name | Definition | Current status | Proposed use |
|---|---|---|---|
| `heliocentric_ecliptic` | Sun-centred Cartesian, ecliptic xy plane, stated equinox | Implicit in current CSV | Canonical dynamical frame; state equinox/J2000 explicitly |
| `equatorial_j2000` | Equatorial Cartesian or spherical, J2000/ICRS-aligned | Used for RA/Dec via obliquity rotation | Canonical sky frame for observations |
| `observer_heliocentric_ecliptic` | Observer position in the dynamical frame | Implicit idealized model | Store per epoch |
| `topocentric` | Observer-site frame | Not modelled | Future option; document if added |

**Units (file boundary):**

| Quantity | Unit | Notes |
|---|---|---|
| Position/range | AU | No km in CSV unless a column says so |
| Velocity | AU/year | Preserve current convention; add AU/day only as a versioned option |
| Time interval | day | `time_days` is canonical; `time_years = time_days / 365.25` |
| Angle | degree | RA in [0, 360), Dec in [−90, 90] |
| Uncertainty | arcsec | RA uncertainty is `sigma_ra_cosdec_arcsec` |
| Epoch | JD TDB or null | Never silently substitute UTC or TT |

**Time conventions:**

- **Synthetic elapsed time:** `time_days` measured from the run’s t=0; no calendar date is implied. `epoch_jd_tdb` is null.
- **Absolute time:** if a real ephemeris is used, every component uses JD TDB and records `time_scale: TDB`. Conversion from UTC/TT happens once at the boundary and is recorded.
- **Do not mix:** a dataset must not combine elapsed and absolute epochs without an explicit mapping. Do not invent a calendar epoch for the existing synthetic runs.
- **Beyond the integrated span:** observation requests after the simulation end must use the propagation service (or an explicitly labelled extrapolation mode), never linear extrapolation of a stored CSV.
- **Year length:** 365.25 days is the current convention. Changing it is a contract change and requires regenerated data.

### H.9 Error handling and validation

**Proposed exception hierarchy:**

```text
OrbitDiscoveryError
├── ConfigurationError
├── ValidationError
├── ContractError
├── PropagationError
├── ObservationError
└── TruthLeakError
```

**Rules:**

- Validate at every boundary: config load, manifest load, CSV load, propagation request, solution load.
- Unknown `schema_version` → error, not a warning.
- Missing critical metadata → error with the missing field names.
- Non-finite values, duplicate epochs, non-monotonic times → error.
- Estimator/selector input containing `true_*` columns or a truth path → `TruthLeakError`.
- A failed run must not leave a partial output directory; use temporary paths and atomic rename.
- Warnings are reserved for non-critical, documented issues and must be recorded in metadata.
- CLI exit codes: `0` success, `2` invalid usage/config, `3` validation/contract failure, `4` runtime/propagation failure.

**Logging:** one configured logger per entry point; include run ID, component, dataset and epoch context; never log truth values into estimator logs.

### H.10 Backward compatibility and migration

- Keep a **v1 reader** for the current three trajectory datasets and three observation datasets.
- New writers emit **v2** artefacts with separate truth and explicit metadata.
- Do not overwrite v0.2.0 files. New outputs use names such as `synthetic_asteroid_observations_v2`.
- Provide a migration note that lists: truth columns moved, new required columns, changed defaults and how to reproduce v1.
- If v1 reproduction is required, expose `--contract v1` with the old interpolation and no light-time; record that choice in metadata.
- Deprecate v1 only after v2 regression tests pass and the report figures are regenerated.

### H.11 Scientific decisions requiring explicit approval

These choices change the measurements or their interpretation. They must not be made silently during refactoring.

| Decision | Options | Recommendation | Consequence if changed |
|---|---|---|---|
| Truth separation | Keep co-located vs separate files | Separate `observations.csv` and `ground_truth.csv` | Existing consumers break; provide v1 reader and migration note |
| Metadata enforcement | Trust CSV vs require manifest | Require manifest for v2; `--allow-unverified` only for legacy | Legacy files need a manifest or an explicit override |
| Interpolation | Linear vs Hermite vs integrate-at-epoch | Hermite first, measure; direct integration for final validation | Measurements change; v2 datasets cannot be compared row-for-row with v1 |
| Light-time | Omit vs correct | Implement and default on for v2; flag off for v1 reproduction | ≈20″ systematic shift; orbit fits and residuals change |
| Aberration | Omit vs model | Model, or explicitly document as not modelled in v2 | Additional arcsecond-to-arcminute systematics if omitted |
| Observer model | Idealized circular vs ephemeris | Keep idealized for baseline; add ephemeris as a separate backend | Replacing the baseline changes every geometry and result |
| Time basis | Elapsed only vs absolute JD TDB | Keep elapsed for synthetic; add nullable absolute epochs | Absolute claims require real ephemerides and a defined time scale |
| Planetary system | Current synthetic system vs realistic masses/elements | Keep current for regression; add realistic scenarios separately | Results are not comparable across systems |
| Noise seeds | One shared seed vs per-scenario/multi-seed | Per-scenario seeds plus ensembles | Cross-scenario comparisons and uncertainty calibration change |
| Observability | No constraint vs elongation/visibility flags | Add flags and threshold; do not drop rows | Row counts and schedulable epochs change; report both filtered and unfiltered |
| Future window | Extrapolate CSV vs propagate | Propagate with the shared service; new run manifest | Extrapolation is not physically justified beyond the integrated span |
| Truth state | RA/Dec only vs full 3D state | Store full true state and range per epoch | Enables range/velocity metrics and better evaluation |

**Approval rule:** each accepted decision should be recorded as an ADR with the date, rationale, affected datasets and validation evidence. Until approved, the refactor must preserve v0.2.0 behaviour.

## I. Implementation Order

### I.1 Dependency graph

```text
Phase 0  Freeze and protect 0.2.0
   |
   +--> Phase 1  Packaging and entry points ----+
   |                                            |
   +--> Phase 2  Contracts and validators ------+--> Phase 4  Observation science hardening
                                                |          |
                    Phase 3  Propagation service +----------+--> Phase 5  Automated tests and CI
                                                                      |
                                                                      --> Phase 6  Documentation and 0.3.0
                                                                                |
                                                                                --> Gate G3
                                                                                |
                                                                                --> Phase 7  Component 3 (future)
                                                                                |
                                                                                --> Gate G4
                                                                                |
                                                                                --> Phase 8  Component 4 (future)
```

Phases 1 and 2 can run in parallel. Phase 3 depends on the state/epoch contract from Phase 2. Phase 4 depends on Phases 2 and 3. Phase 5 should be developed alongside Phases 1–4, not left to the end.

### I.2 Phase 0 — Freeze and protect the 0.2.0 baseline

**Depends on:** nothing.

- [ ] Initialise Git at the repository root.
- [ ] Fix `.gitignore`: track `configs/`, schemas, docs, tests and small fixtures; ignore `.venv/`, `__pycache__/`, generated `artifacts/`, large runs and plots.
- [ ] Commit the current state as the 0.2.0 baseline.
- [ ] Tag it `v0.2.0-baseline`.
- [ ] Record SHA-256 hashes of the current source, configs and datasets in a baseline manifest.
- [ ] Keep the current `data/` and `results/` artefacts untouched; do not regenerate them.
- [ ] Add a short `README.md` that states what is and is not implemented.

**Acceptance:** a fresh clone contains all six configs, the docs and the source; `git status` is clean; the baseline tag exists; no scientific output changed.

### I.3 Phase 1 — Packaging and entry points

**Depends on:** Phase 0.

- [ ] Add `pyproject.toml` with project metadata, Python requirement and optional dependency groups.
- [ ] Create the `src/orbit_discovery/` package with `__init__.py` and `version.py`.
- [ ] Move reusable code behind package imports; keep temporary shims only during migration.
- [ ] Add console entry points for simulate, observe, estimate (stub), select (stub) and evaluate (stub).
- [ ] Make `python -m orbit_discovery.cli.observe` work from any directory.
- [ ] Replace module-global `PROJECT_ROOT` resolution with an explicit project-root/config-root policy.
- [ ] Pin `pytest` and test dependencies in the `test` group.
- [ ] Keep `astroquery` in the `network` group, not the base install.

**Acceptance:** a fresh virtual environment installs the package; every implemented entry point prints help from a temporary working directory; no `ModuleNotFoundError`; the base install does not require network libraries.

### I.4 Phase 2 — Contracts and validators

**Depends on:** Phase 0; can run parallel with Phase 1.

- [ ] Write `docs/schemas/trajectory-v2.md`, `observations-v2.md`, `metadata-v2.md`, `orbit-solution-v2.md` and `schedule-v2.md`.
- [ ] Add `schema_version` and `producer_version` to all writers.
- [ ] Implement a shared manifest loader with required-field validation.
- [ ] Add JSON Schema validation for simulation/observation configs.
- [ ] Add a `TruthLeakError` guard for estimator/selector inputs.
- [ ] Add atomic CSV/JSON writers with hashing.
- [ ] Define the exception hierarchy and CLI exit codes.
- [ ] Add a v1 reader that preserves the current file meanings.

**Acceptance:** deliberately corrupted fixtures fail with field-specific errors; v1 files still load through the compatibility reader; every new output declares its contract version; no writer emits truth columns into the measurement file.

### I.5 Phase 3 — Shared propagation service

**Depends on:** Phase 2.

- [ ] Extract `build_system()` and `propagate_states()` from `src/configurable_simulator.py`.
- [ ] Define `BodySpec`, `SystemSpec`, `StateVector` and `Epoch`.
- [ ] Support arbitrary epochs, including epochs after the original run end.
- [ ] Define out-of-range behaviour: raise, extend, or explicit extrapolation flag.
- [ ] Use the service for Component 1 output and expose it for Components 3 and 4.
- [ ] Add a real-ephemeris backend interface without changing the default synthetic backend.
- [ ] Add two-body and regression tests for the service.

**Acceptance:** a candidate state can be propagated to a requested epoch; results match the full simulation at shared epochs within tolerance; future epochs work and are labelled; no component duplicates the dynamics.

### I.6 Phase 4 — Observation science hardening

**Depends on:** Phases 2 and 3.

- [ ] Implement cubic Hermite interpolation using position and velocity.
- [ ] Measure interpolation error against a high-resolution reference; record it in metadata.
- [ ] Add optional light-time correction, default on for v2.
- [ ] Document aberration, topocentric parallax and precession/nutation status.
- [ ] Persist observer state, range, phase angle and elongation per epoch.
- [ ] Add elongation/visibility flags and a configurable threshold.
- [ ] Split measurements and truth into separate files/directories.
- [ ] Add per-scenario seeds and multi-seed support.
- [ ] Write a v2 dataset for each scenario without overwriting v1.
- [ ] Compare v1 vs v2 measurements and publish the differences.

**Acceptance:** v2 measurements have no truth columns, recorded method flags and geometry; the estimator-facing file is truth-free; interpolation error is below the noise budget or explicitly reported; all three scenarios can be regenerated deterministically.

### I.7 Phase 5 — Automated tests and CI

**Depends on:** Phases 1–4 (incremental).

- [ ] Add `tests/conftest.py` and tiny fixtures.
- [ ] Convert read-only validation scripts into pytest tests.
- [ ] Add unit, integration, regression and scientific markers.
- [ ] Add `pytest -m "not network and not slow"` as the default gate.
- [ ] Add CI for lint, default tests and schema validation.
- [ ] Add a regression test for the v0.2.0 summary values.
- [ ] Add a truth-leak test and an entry-point-from-any-directory test.

**Acceptance:** the default suite passes in a clean checkout without network and without writing into `data/`; CI is green; corrupted contracts fail as expected.

### I.8 Phase 6 — Documentation and 0.3.0 release

**Depends on:** Phases 1–5.

- [ ] Write `README.md`, architecture, schema, testing and migration docs.
- [ ] Record ADRs for truth separation, interpolation, light-time, time basis and observer model.
- [ ] Update `CODEBASE_ANALYSIS.md` with the post-refactor state.
- [ ] Regenerate report figures from v2 data, keeping v1 figures for comparison.
- [ ] Add `CHANGELOG.md` and a release checklist.
- [ ] Tag `v0.3.0`.

**Acceptance:** a new contributor can install, run and validate the pipeline from the docs; v1 and v2 datasets are clearly distinguished; the changelog states the scientific changes.

### I.9 Phase 7 — Component 3 (future; requires Gate G3)

**Depends on:** Phases 0–6 and explicit approval.

This phase is **not part of the current refactor**. It is listed to show the intended sequence.

- [ ] Agree the orbit parameterisation and reference epoch.
- [ ] Implement candidate propagation through the shared service.
- [ ] Implement residual calculation with RA wrap and correlation handling.
- [ ] Implement a fitter with convergence diagnostics.
- [ ] Implement covariance/uncertainty estimation.
- [ ] Implement candidate generation for multimodal solutions.
- [ ] Validate noiseless recovery and noisy coverage over multiple seeds.
- [ ] Write `orbit_solution.json` conforming to H.6.

**Acceptance:** a known synthetic orbit is recovered from noiseless data; noisy recovery is unbiased within stated confidence intervals; truth is never read during fitting.

### I.10 Phase 8 — Component 4 and evaluation (future; requires Gate G4)

**Depends on:** Phase 7 and the future-window contract.

- [ ] Implement `ObservationRequest` and the reveal API.
- [ ] Implement candidate-ensemble propagation and scoring.
- [ ] Implement constraints and equal-budget accounting.
- [ ] Implement fixed-cadence, random and oracle baselines.
- [ ] Implement the evaluation harness with multiple seeds and trajectories.
- [ ] Report uncertainty calibration, not only point accuracy.
- [ ] Compare active selection against baselines at equal budget.

**Acceptance:** a selector can choose a future observation without truth access; the evaluator enforces equal budget; results are reported over multiple seeds with uncertainty.

### I.11 Critical path and approval gates

| Gate | Trigger | Required evidence | Decision |
|---|---|---|---|
| G0 | Baseline freeze | Clean Git tag, baseline hashes, configs tracked | Approve refactor start |
| G1 | Contracts accepted | Schema docs, v1/v2 compatibility plan, truth-separation design | Approve implementation |
| G2 | Scientific changes accepted | Interpolation/light-time/time-basis ADRs and v1 vs v2 comparison | Approve new default datasets |
| G3 | Component 3 start | Phases 0–6 complete; propagation, observation and solution contracts stable | Approve estimation work |
| G4 | Component 4 start | Phase 7 complete; future window, candidate ensemble, reveal API and baselines exist | Approve active-selection work |

**Critical path:** Phase 0 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6 → G3. Packaging (Phase 1) is parallel but must finish before Phase 5. Do not start Phase 7 before G3; do not start Phase 8 before G4.

### I.12 Definition of done for the refactor

- [ ] The package installs cleanly and all implemented entry points run from outside the repository.
- [ ] Every artefact declares a schema version, frame, units and time convention.
- [ ] Component 2 reads and validates Component 1 metadata.
- [ ] Measurements and truth are physically and logically separated.
- [ ] A shared propagation service supports arbitrary states and epochs.
- [ ] Interpolation and light-time choices are explicit, measured and versioned.
- [ ] The default test suite is hermetic and passes in CI.
- [ ] v0.2.0 datasets remain reproducible; v2 datasets are documented and distinct.
- [ ] Components 3 and 4 have stable contracts, even though they are not implemented.
- [ ] The analysis, refactoring plan and ADRs are linked from the README.

### I.13 Risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Refactor changes scientific results unnoticed | Medium | High | Freeze v0.2.0, add regression thresholds, compare v1/v2 explicitly |
| Contract work becomes an open-ended redesign | Medium | Medium | Time-box Phase 2; require G1 approval; implement only what C3 needs |
| Truth separation breaks existing scripts | High | Medium | Keep a v1 reader and a migration note; update scripts in one PR |
| Interpolation/light-time changes invalidate old conclusions | High | High | Publish before/after differences; keep both datasets; update report |
| Propagation service becomes a second simulator | Medium | High | One implementation; Component 1 calls it; tests compare shared epochs |
| Future-window extrapolation is physically wrong | Medium | High | Require integrated dynamics or explicit extrapolation flag; never silently extend CSV |
| Test suite remains manual | Medium | High | Make pytest the gate; keep scripts as wrappers |
| Scope creep into Components 3–4 | High | High | Gate G3/G4; no estimation/selection code in the refactor |

### I.14 Open questions requiring manual verification

1. **Legacy Eros/Horizons workflow:** keep it as a supported validation path, or archive it under `scripts/legacy/`?
2. **Ephemeris backend:** use Horizons at runtime, a cached ephemeris file, or a local JPL kernel? This affects reproducibility and network policy.
3. **Absolute epochs:** should v2 synthetic runs define a calendar epoch, or remain elapsed-time only? The current data do not justify a date.
4. **Default scientific scenario:** is the current synthetic planetary system the intended baseline, or should realistic masses/elements become the default?
5. **Noise model:** keep independent Gaussian RA/Dec errors, or add a correlated/covariance model before Component 3?
6. **Observability threshold:** which elongation cut and other constraints should be authoritative for Component 4?
7. **Data retention:** which current `data/` artefacts are curated references and which are disposable?
8. **Component 3 model:** Keplerian two-body fit first, or N-body fitting from the start?
9. **Component 4 objective:** information gain, candidate discrimination, or a declared science metric? The choice defines the evaluation.

**Do not implement the refactor until the owner approves the priority order and the scientific decisions in H.11.** The next action should be a review of this plan, not a source-code change.

---

*End of plan.*






