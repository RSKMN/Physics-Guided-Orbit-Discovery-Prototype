# Codebase Analysis — Physics-Guided Orbit Discovery Prototype

**Version assessed:** 0.2.0 (project label; the repository does not declare a machine-readable version — see §10)  
**Analysis date:** 2026-11-11 (updated after repository rename)  
**Repository root:** `<repository-root>`  
**Review type:** Read-only architectural, scientific and code-quality review.  
**Document revision:** Post-rename verification. Technical findings are unchanged; paths, file counts and rename status were corrected.

> **Evidence standard used in this report**
>
> - **Confirmed defect** — observed directly in the source, in generated artefacts, or by executing a command during this review.
> - **Confirmed limitation** — an intentional or documented simplification whose consequences are observable.
> - **Risk** — plausible failure mode inferred from code and contracts, not necessarily triggered by the current three datasets.
> - **Suggestion / Optional** — improvement that is not required to make the current pipeline work.
>
> No source file, configuration file or dataset was modified during the original review or this update. The repository was renamed from `code` to `physics-guided-orbit-discovery-prototype` after the original analysis; this revision corrects paths, file counts and rename status and re-confirms the read-only checks in §0. Tests that regenerate datasets, write plots or perform network queries were **not** executed; their existing artefacts were inspected instead. Every test result quoted below was actually executed and observed unless explicitly marked otherwise.

---

## 0. Verification Performed (Original Review and Post-Rename Re-Verification)

| Check | Command / method | Observed result | Writes? |
|---|---|---|---|
| Python / library versions | `.venv\Scripts\python.exe --version` and imports | Python 3.13.9; REBOUND 5.2.2; NumPy 2.5.4; Pandas 3.1.0; Matplotlib 3.11.2; astroquery 0.4.11 installed | No |
| Test runner available | `python -m pytest --version` | `No module named pytest` (exit 1) | No |
| Component 2 script entry point | `python src\observation_generator.py --help` | `ModuleNotFoundError: No module named 'src.trajectory_loader'` (exit 1) | No |
| Component 2 module entry point | `python -m src.observation_generator --help` | Usage printed correctly | No |
| Component 1 entry point | `python src\configurable_simulator.py --help` | Usage printed correctly | No |
| Trajectory loader | `python tests\test_trajectory_loader.py` | Exit 0; 1001 samples; positions `(1001, 3)` | No |
| Observation schedule | `python tests\test_observation_schedule.py` | Exit 0; 262 observations, 0.0–1826.25 days | No |
| Observer model | `python tests\test_observer_model.py` | Exit 0; initial observer `[0, 1, 0]` AU | No |
| Coordinate conversion | `python tests\test_coordinate_converter.py` | Exit 0; RA 3.1375°–359.9210°, Dec −23.4385°–23.4388° | No |
| Noise and reproducibility | `python tests\test_measurement_noise.py` | Exit 0; RA σ 0.4660″, Dec σ 0.5017″; repeated seed identical | No |
| Ground-truth schema | `python tests\validate_ground_truth.py` | Exit 0; both scenarios 1001 samples, 5.000000 years | No |
| Scenario sensitivity | `python tests\check_configurable_runs.py` | Exit 0; max pointwise difference 1.805711 AU (eccentric vs standard) | No |
| Single observation dataset | `python tests\test_observation_output.py` | Exit 0; all assertions passed | No |
| All observation datasets | `python tests\test_all_observation_outputs.py` | Exit 0; 3 × 262 observations validated | No |
| Baseline physics | `python tests\validate_baseline.py` | Exit 0; Kepler period error 0.0039%; ε 1e-9 vs 1e-12 difference printed as `0.0` AU | No |
| Pipeline reproducibility | In-memory recomputation of all three observation datasets from current configs/trajectories | Standard: max ΔRA `1.7e-13°`, ΔDec `2.5e-14°`; inclined/eccentric: exactly 0.0; times exact | No |
| Interpolation accuracy diagnostic | Linear (current) vs cubic Hermite using the same trajectory grid and velocities | Median 0.223″, p95 1.048″, max 1.731″ angular difference; range 1.15–4.00 AU | No |
| Observation geometry diagnostic | Solar elongation and angular rate from existing observation/trajectory files | Min elongation 0.50°; 25.6% of epochs <30°, 37.4% <45°; median angular rate 0.3545°/day | No |
| Repository metadata | File inspection | No `.git` directory; `configs/*.json` covered by `*.json` in `.gitignore`; no `README.md`, `pyproject.toml`, `__init__.py` or CI config | No |

**Not executed:** `tests/test_component1_integration.py`, `tests/test_repeatability.py`, `tests/test_tolerance_sensitivity.py`, `tests/compare_trajectories.py`, `tests/test_horizons_loader.py`, `tests/check_horizons_epoch.py`, `tests/validate_eros_horizons.py`, `tests/validate_eros_8planets.py`, `tests/diagnose_eros_horizons.py`. These regenerate datasets/plots or require network access. Their existing outputs were inspected (§3.9, §8.8). The report does **not** claim those runs passed during this review.

**Post-rename re-verification (2026-11-11):** the read-only functional checks (trajectory loader through baseline physics), plus the in-memory recomputation and the interpolation/geometry diagnostics, were re-run against the renamed repository. All functional checks exited with status 0 and produced the same values reported above (≤1.7×10⁻¹³° recomputation difference; 0.223″ median / 1.731″ maximum interpolation difference; 0.50° minimum elongation; 25.6% of epochs <30°). The data-writing and network checks were not re-run.

---

## 1. Executive Summary

The repository contains a **working but narrow synthetic pipeline**:

1. **Component 1** (`src/configurable_simulator.py`) generates heliocentric ecliptic asteroid trajectories with REBOUND/IAS15, driven by JSON configuration, and writes `trajectory.csv`, `config.json`, `metadata.json` and two plots.
2. **Component 2** (`src/observation_generator.py` plus five helper modules) loads one such trajectory, interpolates it onto a fixed cadence, computes an idealized circular observer's position, forms observer-relative vectors, rotates from ecliptic to equatorial coordinates, computes RA/Dec, adds seeded Gaussian angular noise, and writes `observations.csv` and `metadata.json`.
3. A comparison script produces five publication-style figure pairs and a numerical summary for three synthetic scenarios.
4. A collection of script-style checks provides meaningful scientific validation (Kepler period, tolerance sensitivity, repeatability, JPL Horizons comparisons for Eros).

For the three current datasets, the pipeline is **internally consistent**: recomputing Component 2 in memory from the current Component 1 trajectories and current configs reproduces the saved observations to floating-point precision (≤1.7×10⁻¹³ degrees). That is genuine evidence that Component 2 currently interprets Component 1 output correctly **for the exact schema and conventions it was written against**.

However, the pipeline is **not robustly compatible**, and version 0.2.0 is **not a complete implementation of the stated project**. The main findings are:

| # | Finding | Severity | Status |
|---|---|---|---|
| 1 | Component 2 cannot be launched as `python src/observation_generator.py` because of absolute `src.*` imports; only `python -m src.observation_generator` works | Critical | Confirmed defect |
| 2 | Component 2 never reads Component 1 metadata; frame, units, epoch and state type are assumed rather than validated | Critical | Confirmed defect |
| 3 | True/noise-free RA/Dec are written into the same `observations.csv` that Component 3 will consume (`save_noise_free_coordinates: true`), violating the planned separation of model inputs and hidden ground truth | Critical | Confirmed defect |
| 4 | `.gitignore` ignores `*.json` and `*.csv`, which would exclude **all six scientific configuration files** if Git is initialised | Critical | Confirmed defect |
| 5 | Several configuration keys (`units`, `observer.model`, `measurement_noise.model`, `coordinates.input_frame/output_frame/ra_unit/dec_unit`) are recorded but never used or enforced | High | Confirmed defect |
| 6 | No propagation interface exists for arbitrary candidate states/times; no absolute epoch; the observation window ends exactly at the trajectory end | Critical (for Components 3–4) | Confirmed limitation |
| 7 | Linear interpolation of positions ignores the available velocities; measured error is 0.22″ median / 1.73″ maximum, comparable to or larger than the 0.5″ measurement noise | High (scientific) | Confirmed defect/limitation |
| 8 | No light-time correction; at the median range of 2.76 AU and 0.3545°/day angular rate, the induced error is ≈20″, ~40× the noise σ | High (scientific) | Confirmed limitation |
| 9 | No observability constraints; 25.6% of generated epochs have solar elongation <30°, including a 0.50° minimum, which is not physically observable | High (for Component 4) | Confirmed limitation |
| 10 | The test suite is not a test suite in the pytest sense: pytest is not installed; several modules execute simulations or network calls at import; one `test_*` function requires an undefined fixture; several “tests” contain no assertions | Critical | Confirmed defect |
| 11 | `astroquery` is imported by `horizons_loader.py`, `nbody_realistic.py` and four test scripts but is absent from both requirements files | High | Confirmed defect |
| 12 | Component 2 uses the same random seed and array length for all three scenarios, so the “comparative” noise distributions are the same realisation, not independent samples | Medium | Confirmed defect |
| 13 | No `README.md`, no package `__init__.py`, no `pyproject.toml`, no version declaration, no CI, and only one component document | High | Confirmed gap |

**Overall assessment:** Component 1 is a usable research prototype; Component 2 is a usable synthetic-observation prototype with good modular decomposition but fragile contracts. The repository is **not ready** to support Components 3 and 4 without a contract, provenance and testing refactor. The scientific foundation is sound for a synthetic demonstration, but the current observation model is too idealized and the interpolation error too large to support claims of realistic astrometric accuracy.

**Recommended immediate action:** freeze 0.2.0 as a labelled snapshot, fix the critical contractual and test issues **without changing scientific behaviour**, then build Components 3–4 on versioned schemas rather than on the current implicit CSV contract.

---

## 2. Existing Repository Structure

### 2.1 Directory tree

```text
physics-guided-orbit-discovery-prototype/   # verified repository root (renamed from code/)
├── .venv/                                # local virtual environment (excluded from analysis)
├── .gitignore
├── requirements.txt                      # 4 top-level packages, unpinned
├── requirements-lock.txt                 # 14 pinned packages (astroquery missing)
├── configs/
│   ├── synthetic_asteroid.json
│   ├── synthetic_asteroid_eccentric.json
│   ├── synthetic_asteroid_inclined.json
│   ├── synthetic_observations.json
│   ├── synthetic_observations_eccentric.json
│   └── synthetic_observations_inclined.json
├── data/
│   ├── trajectory_two_body.csv           # legacy two-body output (legacy schema)
│   ├── trajectory_nbody_synthetic.csv    # legacy N-body demo (legacy schema)
│   ├── trajectory_nbody_eros.csv         # legacy Horizons/Eros run (legacy schema)
│   ├── eros_diagnostics.csv
│   ├── eros_horizons_validation.csv
│   ├── eros_horizons_8planets_validation.csv
│   ├── runs/
│   │   ├── synthetic_asteroid/{trajectory.csv, config.json, metadata.json, trajectory_xy.png, trajectory_3d.png}
│   │   ├── synthetic_asteroid_eccentric/{...same...}
│   │   └── synthetic_asteroid_inclined/{...same...}
│   ├── observations/
│   │   ├── synthetic_asteroid_observations/{observations.csv, metadata.json}
│   │   ├── synthetic_asteroid_eccentric_observations/{...}
│   │   └── synthetic_asteroid_inclined_observations/{...}
│   ├── repeatability/{run_a,run_b}/{trajectory.csv, config.json, metadata.json}
│   └── tolerance_tests/
│       ├── eps_1e9/{trajectory.csv, config.json, metadata.json}
│       ├── eps_1e12/{...}
│       ├── eps_1e13/{...}
│       └── tolerance_summary.csv
├── docs/
│   ├── COMPONENT_1.md
│   └── development/
│       ├── CODEBASE_ANALYSIS.md
│       └── REFACTORING_PLAN.md
├── plots/
│   ├── two_body_orbit.png
│   ├── nbody_synthetic_orbit.png
│   ├── nbody_eros.png
│   ├── two_body_vs_nbody.png
│   └── trajectory_difference.png
├── results/
│   └── component-2/
│       ├── comparison_summary.csv
│       └── figures/{ra_vs_time, dec_vs_time, sky_track, time_colored_sky_tracks, noise_distribution}.{png,pdf}
├── src/                                  # 12 Python files, no package __init__.py
│   ├── main.py
│   ├── nbody_simulator.py
│   ├── nbody_realistic.py
│   ├── horizons_loader.py
│   ├── configurable_simulator.py
│   ├── trajectory_loader.py
│   ├── observation_schedule.py
│   ├── observer_model.py
│   ├── coordinate_converter.py
│   ├── measurement_noise.py
│   ├── observation_generator.py
│   └── compare_observation_datasets.py
└── tests/                                # 19 Python files + validation_report.md
    ├── check_configurable_runs.py
    ├── check_horizons_epoch.py
    ├── compare_trajectories.py
    ├── diagnose_eros_horizons.py
    ├── test_all_observation_outputs.py
    ├── test_component1_integration.py
    ├── test_coordinate_converter.py
    ├── test_horizons_loader.py
    ├── test_measurement_noise.py
    ├── test_observation_output.py
    ├── test_observation_schedule.py
    ├── test_observer_model.py
    ├── test_repeatability.py
    ├── test_tolerance_sensitivity.py
    ├── test_trajectory_loader.py
    ├── validate_baseline.py
    ├── validate_eros_8planets.py
    ├── validate_eros_horizons.py
    ├── validate_ground_truth.py
    └── validation_report.md
```

Excluded from counts: `.venv/` and `__pycache__/`. Excluding those, the repository currently contains **103 files and 25 directories** (about 4.69 MB), including this report and `REFACTORING_PLAN.md`. Before either development document was added it contained 101 files, 24 directories and 4,501,098 bytes.

### 2.2 Python file inventory and responsibilities

#### Component 1 and legacy simulation code

| File | Responsibility | Relationship / status |
|---|---|---|
| `src/configurable_simulator.py` | Production Component 1. `load_config()` reads JSON; `build_simulation()` constructs Sun + selected planets + massless asteroid; `generate_trajectory()` integrates and writes `trajectory.csv`, `config.json`, `metadata.json`; `save_trajectory_plot()` writes XY and 3D PNGs; CLI accepts a config path. | Primary producer of the modern trajectory schema consumed by Component 2. Reusable functions, but no arbitrary-time/state propagation API. |
| `src/horizons_loader.py` | Library. `BODY_CONFIG` masses/IDs; `load_horizons_states(epoch_jd, bodies)` queries JPL Horizons, converts AU/day → AU/year, validates finite values, returns dict. | Used by `nbody_realistic.py` and four test/validation scripts. Requires `astroquery`, which is not declared. Not used by the configurable pipeline. |
| `src/nbody_simulator.py` | Legacy synthetic N-body demonstration: Sun + Mercury/Venus/Earth/Jupiter + asteroid `a=2.5, e=0.2`; writes `data/trajectory_nbody_synthetic.csv` and a plot. | Module-level script; duplicates planetary constants; **legacy CSV schema** (`time_yr`, `x_AU`, …, `distance_AU`). Not importable without side effects. |
| `src/nbody_realistic.py` | Legacy Horizons-initialised Eros run: Sun + 5 planets + Eros at JD 2460676.5; writes `data/trajectory_nbody_eros.csv` and a plot. | Module-level script; network-dependent; does not set IAS15 epsilon (default used); `from horizons_loader import …` works only when run as a script. Separate from the configurable interface, as documented. |
| `src/main.py` | Original two-body Sun–asteroid baseline (a=2.5, e=0.2, 5 yr, 1000 samples); writes `data/trajectory_two_body.csv` and a plot. | Educational baseline; module-level script; legacy schema; no `if __name__ == "__main__"`. |

#### Component 2 code

| File | Responsibility | Relationship / status |
|---|---|---|
| `src/trajectory_loader.py` | `load_trajectory(csv_path)` validates required modern columns, numeric/finite values, ≥2 rows, strictly increasing time, and `time_days == time_years * 365.25`; returns dict of time/position/velocity arrays. | Input adapter for Component 2. Does not read or validate Component 1 metadata; rejects legacy schema. Prints progress. |
| `src/observation_schedule.py` | `generate_observation_times()` produces a fixed cadence inside the available range and appends the exact end point; `interpolate_positions()` linearly interpolates each position axis with `np.interp`. | Scheduling and interpolation layer. Linear interpolation ignores the velocity columns that are already loaded. |
| `src/observer_model.py` | `calculate_observer_positions()` gives an idealized circular observer in the ecliptic plane; `calculate_relative_positions()` returns asteroid − observer. | Observer geometry layer. Only `orbital_radius_au`, `orbital_period_years`, `initial_phase_deg` are used. |
| `src/coordinate_converter.py` | `ecliptic_to_equatorial()` applies a fixed obliquity rotation about x; `calculate_ra_dec()` computes RA `[0,360)` and Dec `[-90,90]` via `arctan2`. | Frame layer. Correct rotation; no precession/nutation or epoch. |
| `src/measurement_noise.py` | `add_measurement_noise()` draws independent Gaussian RA (tangent-plane `σ_RA cosδ`) and Dec errors, converts RA offset by dividing by `cosδ`, wraps RA, rejects pole singularities and invalid Dec. | Noise layer. Deterministic for a fixed seed. No covariance. |
| `src/observation_generator.py` | Orchestrates the full Component 2 pipeline: config load → trajectory load → schedule → interpolation → observer → relative vector → frame transform → RA/Dec → noise → CSV → metadata. `main()` provides `--config`. | Primary Component 2 entry point. Script invocation currently fails; module invocation works. |
| `src/compare_observation_datasets.py` | Loads three hardcoded datasets, plots RA/Dec vs time, sky tracks, time-coloured tracks and noise histograms, writes PNG/PDF and `comparison_summary.csv`. | Analysis/reporting layer, not part of the generation pipeline. Hardcoded dataset names, labels, colours, 385-day debug row, colour limits and 262/1826.25 assumptions. |

#### Test and validation scripts

| File | What it actually does | Test quality |
|---|---|---|
| `tests/test_trajectory_loader.py` | Calls the loader and prints shapes/positions. | No assertions; smoke test only. |
| `tests/test_observation_schedule.py` | Calls schedule + interpolation and prints shapes. | No assertions; smoke test only. |
| `tests/test_observer_model.py` | Runs the pipeline up to relative positions; asserts initial observer `[0,1,0]` and matching shapes. | Some assertions; depends on a pre-generated dataset. |
| `tests/test_coordinate_converter.py` | Runs the pipeline through RA/Dec; asserts 262 rows and valid ranges. | Assertions, but hardcoded count and data dependency. |
| `tests/test_measurement_noise.py` | Runs the pipeline through noise; asserts ranges and seed reproducibility. | Good reproducibility check; hardcoded count. |
| `tests/test_observation_output.py` | Validates one saved observation dataset: files, columns, count, finiteness, timestamps, ranges, σ columns, recovered noise mean/std. | Strong dataset-level validation; hardcoded 262/1826.25. |
| `tests/test_all_observation_outputs.py` | Same validation for all three datasets via `validate_dataset()`. | Strong; hardcoded 262. |
| `tests/validate_ground_truth.py` | Validates schema/finiteness/order/time consistency for two trajectory files. | Reasonable schema check. |
| `tests/check_configurable_runs.py` | Compares standard vs eccentric trajectories and prints PASS/FAIL. | No assertions; only prints. |
| `tests/validate_baseline.py` | Four-part baseline validation: dataset integrity, perihelion/aphelion, Kepler period, IAS15 convergence. | Strong physics checks; read-only. |
| `tests/test_component1_integration.py` | Runs the configurable simulator twice via `subprocess`, checks output files and metadata. | Regenerates data; `test_configuration(config_path)` is pytest-incompatible. |
| `tests/test_repeatability.py` | Writes two temporary configs, runs the simulator twice, compares trajectories. | Module-level execution; writes `data/repeatability`; pytest collection would run simulations. |
| `tests/test_tolerance_sensitivity.py` | Runs ε = 1e-9, 1e-12, 1e-13 and compares positions/velocities. | Module-level execution; writes `data/tolerance_tests`; no assertions. |
| `tests/compare_trajectories.py` | Compares legacy two-body vs synthetic N-body; writes two plots. | Legacy; writes plots; asserts equal sampling. |
| `tests/validate_eros_horizons.py` | 5-planet Eros vs Horizons at 0–5 yr; writes CSV. | Network-dependent; writes data. |
| `tests/validate_eros_8planets.py` | 8-planet Eros vs Horizons at 0–5 yr; writes CSV. | Network-dependent; writes data. |
| `tests/diagnose_eros_horizons.py` | Initial-state consistency, 5 vs 8 planets, ε convergence; writes diagnostics CSV. | Network-heavy; duplicates `BODY_CONFIG`; writes data. |
| `tests/check_horizons_epoch.py` | Re-queries Eros at the same epoch and prints differences. | Network-dependent; no assertions. |
| `tests/test_horizons_loader.py` | Queries six bodies at module import; asserts state keys and finiteness. | Network at import; pytest would query during collection. |

### 2.3 Configuration files

| File | Purpose | Notable content / issue |
|---|---|---|
| `configs/synthetic_asteroid.json` | Standard scenario: a=2.5 AU, e=0.2, i=0°, Sun+Mercury+Venus+Earth+Jupiter, 5 yr, 1.82625 d output. | `units` block is never read. No planetary phases/elements beyond names. |
| `configs/synthetic_asteroid_eccentric.json` | e=0.5 scenario. | Same structure. |
| `configs/synthetic_asteroid_inclined.json` | e=0.3, i=10° scenario. | Same structure. |
| `configs/synthetic_observations.json` | Cadence 7 d, 0–1826.25 d, 1 AU/1 yr observer at 90°, σ=0.5″ each, seed 42. | `observer.model`, `measurement_noise.model`, `coordinates.input_frame/output_frame/ra_unit/dec_unit` are not used. |
| `configs/synthetic_observations_eccentric.json` | Same observation model for the eccentric run. | Same unused keys. |
| `configs/synthetic_observations_inclined.json` | Same observation model for the inclined run. | Same unused keys. |

### 2.4 Data and generated artefacts

- **Modern trajectories:** 3 runs × 1001 data rows, 8 modern columns, plus `config.json`, `metadata.json`, two PNGs. Standard run metadata `run_utc` 2026-10-24; inclined run `run_utc` 2026-11-11 — the datasets were regenerated at different times.
- **Modern observations:** 3 datasets × 262 rows, 8 columns (`time_years`, `time_days`, `ra_deg`, `dec_deg`, `sigma_ra_cosdec_arcsec`, `sigma_dec_arcsec`, `true_ra_deg`, `true_dec_deg`), plus metadata.
- **Legacy trajectories:** `trajectory_two_body.csv` (1000 rows, `time_yr`, `x_AU`, …, `distance_AU`), `trajectory_nbody_synthetic.csv`, `trajectory_nbody_eros.csv`. These are incompatible with `trajectory_loader.REQUIRED_COLUMNS`.
- **Validation artefacts:** `eros_diagnostics.csv`, `eros_horizons_validation.csv`, `eros_horizons_8planets_validation.csv`, `tolerance_tests/tolerance_summary.csv`, `repeatability/run_a|run_b`, `results/component-2/comparison_summary.csv` and five figure pairs.
- **Duplicated outputs:** the same kinds of plots exist under `data/runs/*/`, `plots/` and `results/component-2/figures/` with no manifest linking them to a run.

### 2.5 Dependencies and environment

`requirements.txt`:

```text
rebound
numpy
pandas
matplotlib
```

`requirements-lock.txt` pins 14 packages, including `rebound==5.2.2`, `numpy==2.5.4`, `pandas==3.1.0`, `matplotlib==3.11.2`, but **does not include `astroquery`** and **does not include `pytest`**. `astroquery` is imported by `src/horizons_loader.py`, `src/nbody_realistic.py`, `tests/test_horizons_loader.py`, `tests/check_horizons_epoch.py`, `tests/diagnose_eros_horizons.py`, `tests/validate_eros_horizons.py` and `tests/validate_eros_8planets.py`. The installed `.venv` happens to contain astroquery 0.4.11, so the environment works by accident, not by declaration.

There is no `pyproject.toml`, `setup.cfg`, `setup.py`, `environment.yml`, `Pipfile`, `tox.ini`, `pytest.ini`, `ruff.toml`, `mypy.ini` or CI workflow.

### 2.6 Unused, duplicated, temporary and obsolete files

| Item | Classification | Evidence / recommendation |
|---|---|---|
| `src/main.py`, `src/nbody_simulator.py`, `src/nbody_realistic.py` | Legacy / largely superseded | They duplicate dynamics and use the legacy schema. Keep as archived examples until a clean replacement exists; do not present them as the Component 1 interface. |
| `data/trajectory_two_body.csv`, `trajectory_nbody_synthetic.csv`, `trajectory_nbody_eros.csv` | Legacy generated data | Not consumable by Component 2. Keep for the historical validation narrative or move to an archive area later. |
| `plots/*.png` | Duplicated legacy figures | Superseded by `data/runs/*/trajectory_*.png` and `results/component-2/figures/`. |
| `data/repeatability/`, `data/tolerance_tests/` | Test artefacts committed/generated into `data/` | Should live under an artifacts directory and be reproducible; only the summary CSVs are useful to keep. |
| `data/eros_*.csv` | Validation artefacts | Useful evidence, but should be documented and regenerable. |
| `results/component-2/` | Generated analysis output | Good content, but no manifest and no link to input dataset versions. |
| `tests/validation_report.md` | Captured stdout | Not a live test result; may be stale. |
| `configs/repeatability_temp/`, `configs/tolerance_temp/` | Temporary config directories | Created and removed by tests at runtime; not present now. |
| Parent-level `schema.json` (5.0 MB), `providers_schema.json` (0 bytes), `temp_script.ps1`, `plan-0.docx`, `Step 1 - Implementation Plan….docx`, `step-1 - phases.txt`, `Component 2 - Complete implementati.txt` | Outside the codebase; planning/scratch | Not part of the inspected repository. `schema.json` and the zero-byte `providers_schema.json` appear unrelated to this project and should be archived outside it. |

### 2.7 Repository hygiene

- **No `.git` directory** was found, so version history cannot be verified.
- `.gitignore` contains `*.csv`, `*.json`, `data/`, `plots/`, which would ignore **the entire configuration set**, all dataset outputs and all metadata. It also duplicates `*.csv` and `*.npy` entries and ignores `lib/` (which can be a source directory in some layouts). This is incompatible with a reproducible scientific repository.
- No `README.md`, `LICENSE`, `CITATION.cff`, `CHANGELOG.md` or `CONTRIBUTING.md`.
- `src/` has no `__init__.py`; `src` is a namespace package only by accident of Python 3.3+ namespace-package rules.

---

## 3. Component 1 — Technical Analysis

### 3.1 Simulation architecture

Component 1 is a linear pipeline:

```text
JSON config
   ↓ load_config()
build_simulation(config)
   ├─ REBOUND Simulation, units = (yr, AU, Msun)
   ├─ Sun (m=1.0)
   ├─ selected planets from hardcoded BODY_DATA
   ├─ massless asteroid from initial_conditions (a, e, i, Ω, ω, M)
   ├─ move_to_com()
   └─ IAS15 + epsilon
   ↓ generate_trajectory()
time grid → sequential sim.integrate(t) → rows → DataFrame
   ↓
trajectory.csv + config.json + metadata.json (+ XY/3D PNGs)
```

The modern implementation is in `src/configurable_simulator.py`; `main.py`, `nbody_simulator.py` and `nbody_realistic.py` are separate historical scripts that do not use `build_simulation()`.

### 3.2 Initial-condition generation and orbital-element handling

The asteroid initial condition is read from `config["initial_conditions"]` and converted with `np.deg2rad` for `inclination_deg`, `longitude_ascending_node_deg`, `argument_periapsis_deg` and `mean_anomaly_deg`. `a` and `e` are passed through `float()`. The mode must be `"orbital_elements"`; the error message says Horizons initialization “will be added separately.”

Planetary initial conditions are **not** configurable. `BODY_DATA` provides only mass and semi-major axis; `build_simulation()` adds every planet with:

```python
sim.add(m=body["mass"], a=body["a"], e=0.0, inc=0.0)
```

No `Omega`, `omega`, `M` or phase is supplied, so REBOUND uses default zeros: **all planets start at perihelion on the +x axis, circular and coplanar**. This is a strong simplification: planetary perturbations are coherent and the planetary geometry is not solar-system-like. The configurable interface therefore supports “different asteroid orbits,” not “different planetary systems.”

### 3.3 Gravitational body configuration

`BODY_DATA` contains eight planets with approximate masses in solar masses and semi-major axes in AU:

| Body | Mass (M☉) | a (AU) | Used in configs? |
|---|---:|---:|---|
| Mercury | 1.6601e-7 | 0.3871 | Yes |
| Venus | 2.4478e-6 | 0.7233 | Yes |
| Earth | 3.0035e-6 | 1.0000 | Yes |
| Mars | 3.2272e-7 | 1.5237 | No (available) |
| Jupiter | 9.5458e-4 | 5.2028 | Yes |
| Saturn | 2.8581e-4 | 9.5388 | No (available) |
| Uranus | 4.3662e-5 | 19.1914 | No (available) |
| Neptune | 5.1514e-5 | 30.0611 | No (available) |

The three scenario configs all use `["Sun", "Mercury", "Venus", "Earth", "Jupiter"]`. Mars is available but omitted without explanation. The mass/axis table is duplicated in `src/nbody_simulator.py` (`PLANETS`), `src/horizons_loader.py` (`BODY_CONFIG`) and `tests/diagnose_eros_horizons.py` (`BODY_CONFIG`), with slightly different rounding.

### 3.4 Integrator configuration

- `sim.integrator = "ias15"`; `sim.integrator.epsilon = float(settings["integrator_epsilon"])`.
- Only IAS15 is accepted; any other string raises `ValueError`.
- No validation that epsilon is positive or within a sensible range. IAS15 epsilon values below ~1e-15 are meaningless in double precision; values above ~1e-6 may be too loose.
- The configuration does not expose a maximum step size or a collision/close-encounter handler.
- The asteroid is massless (`m=0.0`), so there is no asteroid–planet back-reaction and no asteroid–asteroid interaction.

### 3.5 Time-step and output handling

- `duration_years` and `output_interval_days` are read from `config["simulation"]`.
- `interval_years = interval_days / 365.25`.
- Times are built with `np.arange(0.0, duration, interval_years)`, then the exact `duration` is appended if not already present.
- `sim.integrate(float(t))` is called sequentially for each absolute time; REBOUND integrates from the previous time to `t`.
- For the standard config: 5 yr / 0.005 yr = 1000 intervals → 1000 values from `arange` (0 to 4.995) plus endpoint 5.0 → **1001 samples**. Confirmed in the CSV and metadata.
- The output interval is therefore nominal; the final interval may differ if `duration` is not an integer multiple. The metadata records `output_interval_days_requested` and `final_time_years` but not the actual maximum/minimum spacing.
- No output-time vector is stored separately; it is embedded in `trajectory.csv`.

### 3.6 Coordinate frames and units

- `sim.units = ("yr", "AU", "Msun")`; in these units REBOUND uses \(G = 4\pi^2\).
- All recorded positions/velocities are **Sun-relative**: `asteroid.x - sun.x`, etc.
- After `sim.move_to_com()`, the Sun moves; subtracting the Sun recovers heliocentric relative states. This is a correct choice for downstream observation geometry.
- Metadata declares `position_reference: "Sun-relative"`, `position_unit: "AU"`, `velocity_unit: "AU/year"`, `time_unit: "year"`, `coordinate_frame: "heliocentric_ecliptic"`.
- The code does not explicitly document whether “ecliptic” means J2000 ecliptic, mean ecliptic of date, or REBOUND’s default xy plane. For the synthetic runs, the initial conditions are defined in that plane, so the label is a convention rather than an independently verified frame.
- `epoch_jd_tdb` is `null`. This is correct and important: the synthetic runs have **elapsed simulation time, not calendar time**.
- The config’s `units` block is never consulted; units are hardcoded in `build_simulation()` and in the metadata strings.

### 3.7 Trajectory output format

Modern `trajectory.csv` columns:

| Column | Meaning | Unit |
|---|---|---|
| `time_years` | Elapsed simulation time | year |
| `time_days` | Elapsed simulation time | day (365.25 d/yr) |
| `x_au`, `y_au`, `z_au` | Sun-relative position | AU |
| `vx_au_per_year`, `vy_au_per_year`, `vz_au_per_year` | Sun-relative velocity | AU/year |

The format is clean, snake_case and unambiguous. `time_days` is exactly `time_years * 365.25` (confirmed). The DataFrame is checked for non-finite numeric values before writing. There is no schema version, no row ID, no checksum, and no indication of the producing code version.

### 3.8 Metadata generation

`metadata.json` records:

- `simulation_name`
- `run_utc`, `python_version`, `rebound_version`
- `number_of_samples`, `duration_years`, `output_interval_days`
- `integrator`, `integrator_epsilon`
- `gravitational_bodies`
- `position_reference`, `position_unit`, `velocity_unit`, `time_unit`
- `initial_conditions` (the **asteroid's** elements only)
- `coordinate_frame`, `epoch_jd_tdb`
- `state_type: "simulated_ground_truth"`
- `massless_asteroid`
- `output_interval_days_requested`, `final_time_years`

**Important reproducibility gap:** the metadata does **not** record the planetary masses, semi-major axes, phases, or the fact that planets are circular/coplanar. Those values live only in `BODY_DATA` source code. `config.json` records only body *names*. A saved run therefore cannot be fully reconstructed from its own outputs if `BODY_DATA` changes. The same applies to the asteroid's Cartesian initial state (it can be derived from the elements, but the exact REBOUND conversion is implicit).

Other missing provenance: NumPy/Pandas/Matplotlib versions, operating system, Git commit, config hash, code version, output schema version, and whether plots were generated.

### 3.9 Validation, error handling and scientific checks

**Implemented validation (code):**

- `Sun` must be in `gravitational_bodies` → `ValueError`.
- Unknown body name → `ValueError`.
- Unsupported `initial_conditions.mode` → `ValueError`.
- Unsupported integrator → `ValueError`.
- Non-positive duration or output interval → `ValueError`.
- Non-finite numeric values in the DataFrame → `ValueError`.
- `load_config()` resolves relative paths against `ROOT = parents[1]`.

**Not implemented:**

- No explicit schema validation; missing keys raise `KeyError`, not a clear domain error.
- No validation of `a > 0`, `0 ≤ e < 1`, inclination range, or finite orbital elements before calling REBOUND.
- No validation of epsilon positivity/range.
- No check that the output directory is writable or that existing files will be overwritten.
- No logging; all messages are `print()`.
- No custom exception types.

**Scientific checks outside the core module (existing artefacts):**

- `tests/validate_baseline.py` (executed during this review): dataset integrity PASS; perihelion 2.0000 AU, aphelion 3.0000 AU; measured period 3.953000 yr vs theoretical 3.952847 yr (0.0039% error); ε 1e-9 vs 1e-12 difference printed as `0.0` AU.
- `tests/test_repeatability.py` (not re-run): designed to run the same config twice and compare to `rtol=1e-10, atol=1e-12`.
- `tests/test_tolerance_sensitivity.py` (not re-run): saved `tolerance_summary.csv` shows max position differences 2.96e-13 AU (1e-9 vs 1e-13) and 2.93e-13 AU (1e-12 vs 1e-13). This is consistent with IAS15 being far more accurate than needed at these tolerances.
- Eros validation (not re-run; saved CSVs inspected):
  - 5-planet model: position error grows from 0 at epoch to **14,073.6 km** at 5 years.
  - 8-planet model: error grows from 0 to **6,196.1 km** at 5 years.
  - These are model-vs-ephemeris comparisons, not raw astrometric validation. They show the effect of missing outer planets (especially Saturn/Uranus/Neptune) and approximate masses.

**Documentation inconsistency:** `tests/validation_report.md` says the tolerance difference was “zero at the current display precision,” while `data/tolerance_tests/tolerance_summary.csv` records ~3e-13 AU. These are different tests/quantities, but the report should state which run produced which number.

### 3.10 Reusability by future components

**Reusable:**

- `load_config()`, `build_simulation(config)` and `generate_trajectory(config_path)` are importable if the script is executed as a module or the project root is on `sys.path`.
- The output schema is clean and machine-readable.
- `build_simulation()` returns a configured REBOUND simulation, which is a useful starting point.

**Not reusable enough:**

- There is no function to propagate an arbitrary state vector from an arbitrary epoch to arbitrary times. Component 3 will need to evaluate candidate orbits, not rerun a fixed config from t=0.
- There is no function to return the asteroid index or a structured state (position/velocity) at a requested time.
- `generate_trajectory()` is file-oriented: it always writes CSV/config/metadata/plots and returns only the DataFrame.
- The simulation is destroyed after the call; no archive/interpolator is retained.
- The planetary model is hardcoded; a candidate-orbit fitter cannot vary planet states or initial epoch.

### 3.11 Component 1 findings

| ID | Severity | Type | Location | Finding |
|---|---|---|---|---|
| C1-01 | High | Confirmed defect | `build_simulation()` / `BODY_DATA` | Planetary initial conditions (mass, a, phases) are not in config or metadata; runs are not fully reproducible from saved artefacts. |
| C1-02 | Medium | Confirmed limitation | `build_simulation()` | All planets are circular, coplanar and aligned at +x; perturbations are artificial. Documented only indirectly in `COMPONENT_1.md`. |
| C1-03 | Medium | Confirmed defect | `build_simulation()` | `config["units"]` is ignored; the units block gives a false impression of configurability. |
| C1-04 | Medium | Risk | `build_simulation()` | No validation of `a`, `e`, inclination or epsilon before REBOUND; invalid values produce library errors or unphysical states. |
| C1-05 | Medium | Confirmed defect | `generate_trajectory()` | No schema/version identifier in CSV or metadata; downstream has no way to detect a format change. |
| C1-06 | Low | Confirmed defect | `generate_trajectory()` | Metadata omits NumPy/Pandas versions, OS, code version and config hash. |
| C1-07 | Low | Confirmed limitation | `nbody_realistic.py` | IAS15 epsilon is not set, so the legacy Eros run uses the REBOUND default (1e-9), unlike the 1e-12 validation runs. |
| C1-08 | Low | Confirmed defect | `main.py`, `nbody_simulator.py`, `nbody_realistic.py` | Module-level execution, `plt.show()`, file writes and network calls at import; not importable as libraries. |
| C1-09 | Low | Confirmed defect | `nbody_realistic.py` | `from horizons_loader import …` is script-only; inconsistent with `from src.…` used elsewhere. |
| C1-10 | Low | Confirmed limitation | `BODY_DATA` | Approximate masses and no GR/Yarkovsky/collisions; adequate for a 5-year synthetic prototype, not for high-precision realism. |

---

## 4. Component 2 — Technical Analysis

### 4.1 Pipeline architecture

`generate_observations(config_path)` in `src/observation_generator.py` performs eleven steps:

1. Load and validate config (`load_config`).
2. Resolve `input_trajectory` against `PROJECT_ROOT`.
3. Load trajectory (`trajectory_loader.load_trajectory`).
4. Generate observation times (`observation_schedule.generate_observation_times`).
5. Convert times to years (`/ 365.25`).
6. Interpolate asteroid positions (`observation_schedule.interpolate_positions`).
7. Compute observer positions (`observer_model.calculate_observer_positions`).
8. Compute observer-relative vectors (`observer_model.calculate_relative_positions`).
9. Rotate ecliptic → equatorial (`coordinate_converter.ecliptic_to_equatorial`).
10. Compute true RA/Dec (`coordinate_converter.calculate_ra_dec`).
11. Add noise (`measurement_noise.add_measurement_noise`), build DataFrame, write CSV and metadata.

The decomposition is good: each scientific step is a small pure function in its own module. This is the strongest architectural aspect of the repository.

### 4.2 Trajectory loading and validation

`src/trajectory_loader.py::load_trajectory`:

- Checks file existence → `FileNotFoundError`.
- Requires the eight modern columns; missing columns → `ValueError` listing them.
- Coerces to numeric with `errors="coerce"`; any NaN → `ValueError`.
- Checks `np.isfinite` on all values.
- Requires ≥2 rows.
- Requires strictly increasing `time_years`.
- Requires `time_days ≈ time_years * 365.25` with `rtol=0, atol=1e-6`.

**Strengths:** clear errors, no silent coercion, good time-consistency check.

**Gaps:**

- Does not read `metadata.json`, so it cannot verify units, frame, epoch, `state_type`, integrator or source.
- Does not check that `time_days` is also strictly increasing independently (it follows from the years check plus consistency).
- Does not check velocity consistency with position derivatives, or orbital plausibility.
- Accepts only the modern schema; legacy files with `time_yr`/`x_AU` are rejected without a migration message.
- `print()` side effects in a library function.

### 4.3 Observation scheduling

`src/observation_schedule.py::generate_observation_times`:

- Validates `cadence_days > 0`, `end_day > start_day`, and that the requested interval lies inside the available trajectory range.
- Uses `np.arange(start_day, end_day, cadence_days)`.
- Appends `end_day` if the cadence does not land on it (`atol=1e-9`).

For 0–1826.25 d at 7 d, this produces 261 values (0 … 1820) plus 1826.25 → **262 observations**. The final gap is 6.25 d, not 7 d. This is intentional (“include the exact endpoint”) but not flagged in the output metadata beyond the schedule echo. It slightly breaks the “fixed cadence” assumption that Component 5 will compare against.

No support for:

- Random schedules (needed for the evaluation baseline).
- Active/adaptive schedules (Component 4).
- Observation budgets (number of observations).
- Multiple instruments/sites or per-epoch uncertainties.
- Visibility/observability constraints.
- Gaps, weather, or seasonality.

### 4.4 Observer modelling

`src/observer_model.py::calculate_observer_positions`:

\[
\theta(t) = \frac{2\pi t}{T} + \phi,\qquad
\mathbf{r}_{obs}(t) = R(\cos\theta, \sin\theta, 0)
\]

Defaults: `R = 1.0 AU`, `T = 1.0 yr`, `phi = 90°`. All configs use these defaults. The observer is therefore a **circular, coplanar, heliocentric “Earth-like” point**, not an ephemeris.

Implications:

- No Earth eccentricity (0.0167) or inclination.
- No Earth–Moon barycentre, precession/nutation, polar motion or topocentric displacement.
- No light-time, aberration or solar gravitational deflection.
- No actual calendar epoch; phase is arbitrary relative to the asteroid's initial mean anomaly.
- The Sun is at the origin; the observer is at 1 AU, so this is effectively a geocentric/heliocentric idealisation.

The config key `observer.model: "idealized_circular"` is recorded but never dispatched on; any other value would be silently ignored.

### 4.5 Relative position calculation

`calculate_relative_positions(asteroid, observer)` returns `asteroid - observer`, shape `(N,3)`, with shape/finite validation. This is the correct observer→asteroid vector (the direction of incoming light, ignoring light-time). No range is returned or stored, although it is trivially available and needed for light-time, topocentric corrections and evaluation.

### 4.6 Coordinate transformations

`ecliptic_to_equatorial(relative_positions, obliquity_deg=23.43928)` applies:

\[
x_{eq}=x,\qquad
y_{eq}=y\cos\epsilon-z\sin\epsilon,\qquad
z_{eq}=y\sin\epsilon+z\cos\epsilon
\]

This is the standard rotation about the x-axis from ecliptic to equatorial coordinates. It is correct for the stated fixed obliquity. The default 23.43928° is the J2000 mean obliquity.

Limitations:

- No epoch-dependent obliquity, precession or nutation.
- No explicit statement of the ecliptic equinox (J2000 assumed).
- No handling of barycentric vs heliocentric aberration.
- The code does not read `coordinates.input_frame`/`output_frame`; it always assumes heliocentric ecliptic input.

### 4.7 RA/Dec calculation

`calculate_ra_dec(equatorial_positions)`:

- `ra = atan2(y, x)`, wrapped to `[0, 360)`.
- `dec = atan2(z, sqrt(x² + y²))`.
- Rejects zero vectors.
- Validates shape and finiteness.

This is numerically sound. For the standard i=0 scenario, the relative vector lies in the ecliptic plane, so |Dec| ≤ obliquity; observed Dec range −23.4385° to +23.4388° is a good sanity check. For the inclined scenario, Dec reaches −40.35°/+30.50°, consistent with an inclined orbit.

No special handling is needed for RA wrap because `atan2` + `mod` is used; the plotting code separately detects wrap for line segments.

### 4.8 Measurement noise

`add_measurement_noise`:

- Draws independent Gaussians with `np.random.default_rng(random_seed)`.
- `ra_noise_arcsec` is interpreted as **tangent-plane** `σ_RA cosδ`; the code divides by `cosδ` to obtain a coordinate RA offset.
- Converts arcsec → degrees with `1/3600`.
- Wraps RA; rejects Dec outside ±90°; rejects zero `cosδ` when σ_RA > 0.
- Returns the noise components for diagnostics.

This is the correct treatment of the `σ_RA cosδ` convention and is a strong point. The tests recover RA σ 0.4660″ and Dec σ 0.5017″ for a configured 0.5″ (finite-sample variation), and the seed reproduces exactly.

**Defect in the comparative analysis:** all three configs use `random_seed = 42` and all three datasets have 262 rows, so `rng.normal` produces the **same sequence of offsets** for each dataset. The residuals in `results/component-2/comparison_summary.csv` are identical to ~1e-9 across the three scenarios (RA mean −0.024561, Dec mean 0.012749, etc.). The “Measurement Noise Distribution Across Orbital Scenarios” figure therefore compares the same noise realisation three times, not three independent noise samples. This does not invalidate the generator, but it invalidates the comparative interpretation.

### 4.9 Reproducibility

**Good:**

- Fixed seed; repeated calls identical (verified).
- Deterministic trajectory integration.
- Observations reproduce exactly from current inputs (verified).
- Config is echoed into metadata; input path is recorded.

**Gaps:**

- No `run_utc` in observation metadata.
- No NumPy/Pandas versions.
- No code version/Git commit.
- No input trajectory hash or copy of its metadata.
- No output schema version.
- The config file is referenced, not copied; if `configs/*.json` changes, the metadata no longer describes the generation conditions.
- Windows path separators appear in JSON (`data\\runs\\...`), reducing portability.
- No record of the actual observer ephemeris used per epoch (only model parameters).

### 4.10 Observation output format

`observations.csv` columns:

| Column | Meaning | Unit | Notes |
|---|---|---|---|
| `time_years` | Elapsed time | year | `/365.25` from days |
| `time_days` | Elapsed time | day | Schedule directly |
| `ra_deg` | Noisy right ascension | degree | `[0,360)` |
| `dec_deg` | Noisy declination | degree | `[-90,90]` |
| `sigma_ra_cosdec_arcsec` | RA uncertainty in tangent plane | arcsec | Correct semantics |
| `sigma_dec_arcsec` | Dec uncertainty | arcsec | 1σ |
| `true_ra_deg` | Noise-free RA | degree | Present when `save_noise_free_coordinates` is true |
| `true_dec_deg` | Noise-free Dec | degree | Present when the flag is true |

The `true_*` columns are useful for residual diagnostics but are a **ground-truth leak** if the same file is handed to Component 3. The plan explicitly separates “model inputs” from “hidden ground truth”; this file does not.

Missing for Components 3–4:

- Observation ID and dataset/scenario ID.
- Observer position/velocity at each epoch (or a pointer to an ephemeris file).
- Asteroid–observer range and range-rate.
- True 3D asteroid state at each epoch.
- Solar elongation / phase angle / observability flag.
- Time system/epoch (`epoch_jd_tdb`, TDB/TT/UTC), even as `null`.
- Frame identifier (ICRS/J2000/mean-of-date) and coordinate representation.
- Correlation coefficient or covariance between RA and Dec (currently assumed zero but not stated in the CSV).
- Instrument/site identifier and magnitude/filter (optional for the prototype).

### 4.11 Metadata

`metadata.json` records `observation_name`, `input_trajectory`, `configuration_file`, `state_type`, `number_of_observations`, `observation_schedule`, `observer`, `coordinates`, `measurement_noise`, `coordinate_units`, `assumptions`, `output_file`.

**Good:** the assumptions list is explicit and scientifically honest (“idealized circular Earth-like observer,” “observer orbit lies in the heliocentric ecliptic plane,” “interpolated from simulated ground truth,” “elapsed simulation times, not real calendar dates”).

**Gaps:** no run timestamp, no library versions, no input metadata/hash, no input frame/unit verification, no output schema version, no observer ephemeris, no ground-truth separation flag, no software version. The metadata echoes `observer.model` and `measurement_noise.model` even though those keys do not control behaviour.

### 4.12 Visualization and comparative analysis

`src/compare_observation_datasets.py` produces:

- `ra_vs_time.png/pdf` — RA with wrap-aware segmentation.
- `dec_vs_time.png/pdf` — Dec vs time.
- `sky_track.png/pdf` — RA/Dec tracks, wrap-aware, different line styles.
- `time_colored_sky_tracks.png/pdf` — 3 panels coloured by time.
- `noise_distribution.png/pdf` — RA/Dec residual histograms for three scenarios.
- `comparison_summary.csv` — counts, ranges, residual means/std.

**Strengths:** publication-quality output (PNG+PDF, 300 dpi), sensible RA-wrap handling, explicit residual calculation with `cosδ`, comparison summary.

**Weaknesses:**

- Hardcoded dataset labels, folder names, colours and line styles.
- Hardcoded `time_days == 385.0` debug print in `load_datasets()`.
- Hardcoded `vmin=0, vmax=1826.25` colour scale.
- Hardcoded `xlim(-2, 2)` arcsec noise axis; breaks visually if σ changes.
- Assumes exactly three datasets and three rows in the noise figure.
- The metadata is loaded but only stored, not validated.
- The identical-seed issue (§4.8) makes the noise comparison misleading.
- If `save_noise_free_coordinates` is false, `true_ra_deg`/`true_dec_deg` are absent and the script raises `KeyError`.
- No CLI; paths are fixed relative to `PROJECT_ROOT`.
- `FIGURE_DIR.mkdir()` runs at import time.

### 4.13 Error handling and validation

**Implemented:** missing config file, missing trajectory file, missing columns, non-numeric/NaN/infinite values, insufficient rows, non-increasing time, inconsistent time columns, out-of-range observation times, invalid cadence, zero-vector coordinates, negative σ, pole singularity, invalid Dec after noise.

**Missing:** config schema validation; validation that the trajectory is in the expected frame/units/state type; validation that `end_day` matches the actual last trajectory sample within tolerance (it does now, but it is not checked); validation of `obliquity_deg` range; validation that `save_noise_free_coordinates`/`save_metadata` keys exist; graceful handling of output-directory permission errors; custom exception hierarchy; logging.

### 4.14 Correctness check: does Component 2 interpret Component 1 correctly?

**Yes, for the current contract.** During this review, all three observation datasets were recomputed in memory from the current configs and current `trajectory.csv` files, using the same functions:

- Standard: max |ΔRA| = 1.705e-13°, max |ΔDec| = 2.487e-14°, max |Δtime| = 0.
- Inclined: exactly 0.0 for RA, Dec and time.
- Eccentric: exactly 0.0 for RA, Dec and time.

This confirms that the saved observations are consistent with the current code and inputs, and that the RA/Dec pipeline is deterministic. It does **not** prove that Component 2 would notice a change in Component 1's frame, units or epoch, because it never reads the metadata that declares them.

### 4.15 Component 2 findings

| ID | Severity | Type | Location | Finding |
|---|---|---|---|---|
| C2-01 | Critical | Confirmed defect | `observation_generator.py:9-22` | Script entry point fails with `ModuleNotFoundError`; only `python -m src.observation_generator` works. |
| C2-02 | Critical | Confirmed defect | `generate_observations()` | Never reads/validates trajectory metadata; silent incompatibility if frame/units/epoch differ. |
| C2-03 | Critical | Confirmed defect | `generate_observations()` | `true_ra_deg`/`true_dec_deg` written into the same file as model inputs; ground-truth leakage. |
| C2-04 | High | Confirmed defect | `observation_schedule.py::interpolate_positions` | Linear interpolation ignores velocities; error 0.22″ median / 1.73″ max vs 0.5″ noise. |
| C2-05 | High | Confirmed defect | `compare_observation_datasets.py` | Same seed/length → identical noise residuals across scenarios; comparative noise figure is not independent. |
| C2-06 | High | Confirmed limitation | `observer_model.py` | Idealized circular observer; no ephemeris, light-time, aberration, topocentric or visibility model. |
| C2-07 | High | Confirmed limitation | `generate_observations()` | Observation window ends exactly at trajectory end; no future prediction window for Component 4. |
| C2-08 | High | Confirmed defect | `observation_generator.py` metadata | No run timestamp, versions, input hash, input metadata or schema version. |
| C2-09 | Medium | Confirmed defect | config keys | `observer.model`, `measurement_noise.model`, `coordinates.input_frame/output_frame/ra_unit/dec_unit` are unused/echoed. |
| C2-10 | Medium | Confirmed defect | `observation_schedule.py` | Endpoint is appended, creating a shorter final cadence; not flagged as non-uniform. |
| C2-11 | Medium | Confirmed defect | `generate_observations()` | Does not write a copy of the config; only a path that may later change. |
| C2-12 | Medium | Confirmed defect | metadata paths | Windows backslashes in JSON paths reduce portability. |
| C2-13 | Medium | Confirmed defect | `compare_observation_datasets.py` | Hardcoded dataset names, 385-day row, 1826.25 colour limit, ±2″ axis, three-row layout. |
| C2-14 | Low | Confirmed defect | `trajectory_loader.py` | `print()` side effects; no metadata awareness. |
| C2-15 | Low | Risk | `measurement_noise.py` | Rejecting any noisy Dec outside ±90° can abort a whole batch near the poles; a clip/resample policy may be preferable. |

---

## 5. Cross-Component Compatibility Analysis

### 5.1 The actual input/output contract

| Contract element | Component 1 producer | Component 2 consumer | Verdict |
|---|---|---|---|
| `time_years` | `generate_trajectory()` | `REQUIRED_COLUMNS`; schedule | **Match** |
| `time_days` | `t * 365.25` | consistency check `≈ time_years*365.25` | **Match** |
| `x_au`, `y_au`, `z_au` | Sun-relative | `positions` array | **Match** |
| `vx_au_per_year`, … | Sun-relative | loaded but **unused** | Match structurally; wasted information |
| Position frame | metadata `heliocentric_ecliptic` | assumed, not read | **Unenforced** |
| Units | metadata AU, AU/yr | assumed, not read | **Unenforced** |
| Time system | metadata `time_unit: year`, `epoch_jd_tdb: null` | assumed elapsed time | **Not propagated** |
| `state_type` | `simulated_ground_truth` | not read | **Unenforced** |
| `config.json` | copied into run directory | not read/copied | **Asymmetric** |
| `metadata.json` | full run metadata | not read | **Asymmetric** |
| CSV schema version | absent | absent | **Absent on both sides** |

### 5.2 Confirmed matches

- The modern `trajectory.csv` contains exactly the eight columns required by `trajectory_loader.REQUIRED_COLUMNS`.
- `time_days` is exactly `time_years * 365.25` within the loader's `atol=1e-6`.
- The observation schedule 0–1826.25 d falls exactly within the standard trajectory's 0–1826.25 d range.
- The saved observations reproduce exactly from the current trajectory and configs (§4.14).
- Both components resolve relative paths against `PROJECT_ROOT = Path(__file__).resolve().parents[1]`, so they agree on the project root when invoked from the project layout.
- Both use AU, years/days and a right-handed Cartesian frame; the observer is in the same ecliptic plane.

### 5.3 Actual and potential integration problems

| ID | Severity | Type | Finding | Impact |
|---|---|---|---|---|
| X-01 | Critical | Confirmed defect | Component 2 ignores Component 1 metadata entirely. | If Component 1 changes frame, units, epoch or time convention, Component 2 silently produces wrong sky coordinates. |
| X-02 | Critical | Confirmed defect | Ground truth is co-located with model inputs. | Component 3 could fit `true_ra/dec` directly; evaluation is not blind. |
| X-03 | High | Confirmed defect | Legacy CSV schema coexists with modern schema. | `data/trajectory_two_body.csv` and the two N-body files cannot be loaded by Component 2; users may assume they can. |
| X-04 | High | Confirmed defect | `configs/*.json` are ignored by `.gitignore`. | Scientific configurations would not be versioned; runs become irreproducible. |
| X-05 | High | Confirmed defect | `astroquery` undeclared. | A fresh environment from `requirements*.txt` cannot run the Horizons workflow or several tests. |
| X-06 | High | Risk | No schema version/contract tests. | A future column rename or unit change can pass silently. |
| X-07 | Medium | Confirmed defect | Component 2 does not copy the observation config into its output. | Metadata references a mutable external file. |
| X-08 | Medium | Confirmed defect | Component 1 metadata omits planetary elements/masses. | Saved runs cannot be reconstructed from their own metadata. |
| X-09 | Medium | Confirmed defect | No absolute epoch in either component. | Components 3–4 can only work in elapsed time; real-data or Horizons integration requires an epoch. |
| X-10 | Medium | Confirmed defect | Tests use CWD-relative `data/...` paths. | Running from `tests/` or another directory fails; CI configuration is fragile. |
| X-11 | Medium | Confirmed defect | Naming conventions differ between generations (`time_yr`/`time_years`, `x_AU`/`x_au`). | Documentation and analysis scripts must special-case schemas. |
| X-12 | Low | Risk | `365.25` is duplicated as a literal in several modules (`horizons_loader`, `observation_generator`, `trajectory_loader`, tests). | A change to the year definition would require coordinated edits. |
| X-13 | Low | Risk | Component 2 loads velocities but never uses them. | A velocity-unit regression would not be detected by any test. |

### 5.4 Why “the pipeline runs” is not proof of compatibility

The current three observation datasets are generated from the current three trajectories with the same code. The integration check (§4.14) confirms consistency **for that exact pair**. But compatibility is enforced by:

- exact column-name matching,
- a hardcoded 365.25 assumption,
- a hardcoded heliocentric-ecliptic assumption,
- a fixed observer model,
- and the fact that the last observation time equals the last trajectory time.

None of these is validated against Component 1's metadata. The pipeline therefore works **by construction for the current fixtures**, not by an explicit contract. This is the central cross-component risk for Components 3–4.

### 5.5 Metadata conventions

| Aspect | Component 1 | Component 2 | Consistency |
|---|---|---|---|
| Run timestamp | `run_utc` | absent | Inconsistent |
| Software versions | Python + REBOUND | absent | Inconsistent |
| State type | `simulated_ground_truth` | `synthetic_observations` | Good labels, but C2 doesn't read C1's |
| Units | explicit | explicit in `coordinate_units` | Good, but not validated |
| Frame | `coordinate_frame` | `coordinates.input_frame` | Duplicated, unvalidated |
| Epoch | `epoch_jd_tdb: null` | absent | Inconsistent |
| Input provenance | config copy | path only | Inconsistent |
| Schema version | absent | absent | Absent |

### 5.6 Configuration conventions

Both use JSON, but:

- Component 1 requires `simulation_name`, `initial_conditions`, `simulation`, `gravitational_bodies`, `units`, `output`.
- Component 2 requires `observation_name`, `input_trajectory`, `observer`, `coordinates`, `observation_schedule`, `measurement_noise`, `output`.
- There is no shared schema, no version field, no validation library, and several keys are decorative.
- Component 1 resolves the config relative to `ROOT`; Component 2 also does, but tests bypass this with CWD-relative data paths.
- Output conventions differ: `data/runs/<name>/` vs `data/observations/<name>/`. This is reasonable, but there is no experiment manifest linking the two.

### 5.7 Dependency management

- `requirements.txt` is unpinned and incomplete (`astroquery` missing, `pytest` missing).
- `requirements-lock.txt` is a flat pip freeze-style list, not a true lock with hashes, platform markers or Python version.
- No optional dependency groups (`sim`, `analysis`, `test`, `network`).
- The `.venv` is present but not described; no `python-version` file.

---

## 6. Future Component 3 and Component 4 Compatibility

### 6.1 What Component 3 (Orbit Estimator) will require

| Requirement | Available in 0.2.0? | Gap / action |
|---|---|---|
| Observation timestamps | Yes (`time_years`, `time_days`) | Add time system/epoch, ideally `jd_tdb` as well |
| RA/Dec measurements | Yes | Add observation ID, frame identifier, covariance |
| Measurement uncertainties | Yes (`sigma_ra_cosdec_arcsec`, `sigma_dec_arcsec`) | Document tangent-plane semantics; add covariance/off-diagonal term (currently implicitly zero) |
| Observer geometry per epoch | Only model parameters in metadata | **Persist observer position/velocity per epoch** (or a reconstructible ephemeris with epoch) |
| Range / range-rate | No | Compute and store for light-time, weighting and diagnostics |
| True 3D state at observation epochs | No (only true RA/Dec) | Store in a separate `ground_truth.csv` |
| Hidden ground-truth orbit | Asteroid initial elements in run metadata; no final osculating elements | Store initial and final elements + covariance |
| Candidate orbit representation | None | Define a versioned `OrbitSolution` schema |
| Propagator for arbitrary state/time | Only `build_simulation(config)` from t=0 | **Implement a propagation API** |
| Residual/likelihood utilities | None | Build in Component 3, but standardise observation ingestion |
| Uncertainty quantification | None | Component 3 deliverable; needs covariance conventions |
| Multiple independent datasets | 3 scenarios, one seed each | Add multiple seeds/trajectories for calibration |

### 6.2 What Component 4 (Active Observation Selector) will require

| Requirement | Available in 0.2.0? | Gap / action |
|---|---|---|
| Candidate orbit ensemble | No | Component 3 output |
| Forward propagation to candidate times | No | Propagation API |
| Predicted sky positions + uncertainties | No | Prediction API |
| Feasible future observation times | No; observations end at trajectory end | Extend trajectory or reserve a future window |
| Observability constraints | No | Solar elongation, altitude, weather, lunar separation (at least elongation) |
| Observation budget/interface | No | Define `ObservationRequest` / `Schedule` protocol |
| Fixed-interval baseline | Fixed cadence exists | Formalise as a schedule generator |
| Random baseline | No | Implement random schedule generator |
| Active scoring | No | Component 4 deliverable |
| Reveal simulated measurement at selected time | No | Need a queryable ground-truth trajectory beyond current end |
| Same-budget comparison harness | No | Evaluation framework |

### 6.3 Data that must be preserved, extended or standardised

**Preserve exactly (do not silently change):**

- `time_years`, `time_days`, `x_au`, `y_au`, `z_au`, `vx_au_per_year`, `vy_au_per_year`, `vz_au_per_year` semantics.
- Sun-relative, heliocentric ecliptic frame for trajectories.
- AU / AU-per-year / year units.
- `time_days = time_years * 365.25` for synthetic elapsed time.
- `sigma_ra_cosdec_arcsec` as tangent-plane RA uncertainty.
- Seeded, reproducible noise.

**Extend (additive, versioned):**

- `schema_version` in CSV/metadata.
- `epoch_jd_tdb` (may be `null` for synthetic elapsed-time runs) and `time_scale`.
- `frame` identifier and `obliquity_deg` provenance.
- Per-epoch observer position/velocity and range.
- Per-epoch true asteroid state in a separate truth file.
- `observation_id`, `dataset_id`, `scenario_id`.
- Input trajectory hash and full input metadata copy.
- Run timestamp, library versions, code version.
- Planet masses/elements and full initial system state.
- Covariance/correlation for RA/Dec (even if zero).
- Observability fields (elongation, phase angle, visible flag).
- Final osculating orbital elements for each run.

**Standardise:**

- One `load_config` utility with schema validation.
- One path-resolution policy (`project_root` passed explicitly, not module-global).
- One error hierarchy and logging setup.
- One time/unit constant module (`DAYS_PER_YEAR`, `ARCSEC_TO_DEG`, `AU_KM`, `OBLIQUITY_DEG`).
- One CSV naming convention (snake_case, unit suffix).
- One output directory convention with a manifest.

### 6.4 Proposed interfaces (specification only — not implemented)

These are recommendations for the next phase; no code was added.

```python
# Shared core
@dataclass(frozen=True)
class Epoch:
    jd_tdb: float | None          # None for synthetic elapsed-time runs
    elapsed_days: float
    time_scale: Literal["TDB", "TT", "UTC", "elapsed"]

@dataclass(frozen=True)
class StateVector:
    position_au: np.ndarray        # (3,)
    velocity_au_per_year: np.ndarray  # (3,)
    frame: str = "heliocentric_ecliptic"
    epoch: Epoch | None = None

# Component 1 / shared propagation
def propagate(
    initial_state: StateVector,
    times_days: np.ndarray,
    bodies: list[BodySpec],
    integrator_epsilon: float = 1e-12,
) -> list[StateVector]: ...

# Component 2 / prediction
def predict_sky(
    states: list[StateVector],
    observer_ephemeris: ObserverEphemeris,
    frame: str = "equatorial_j2000",
    light_time: bool = True,
) -> SkyPrediction: ...

# Component 3 output
@dataclass
class OrbitSolution:
    elements: OrbitalElements        # a, e, i, Ω, ω, M, epoch
    covariance: np.ndarray           # 6x6, units documented
    residuals: np.ndarray
    chi2: float
    candidates: list["OrbitSolution"]

# Component 4
class ObservationSchedule(Protocol):
    def next_time(self, history: ObservationSet, candidates: CandidateEnsemble) -> float: ...
```

### 6.5 Identifiability and data-volume considerations

- The current data contain 262 observations over 5 years for a 6-parameter Keplerian orbit (plus possible perturbing parameters). That is ample in count, but the observations are all from one idealized observer and one cadence; the information content is limited by geometry, not by row count.
- RA/Dec give direction only; range is not directly observed. Orbit determination relies on the curvature of the sky track and the observer's motion. The 5-year baseline covers more than one asteroid period (3.95 yr for a=2.5 AU), which helps.
- The current cadence (7 d) is dense relative to the orbital period (~3.95 yr); “sparse” is relative. Component 4 will need to evaluate much sparser subsets (e.g., 10–30 observations) and compare schedules at equal budget.
- There is only one noise realisation per scenario. Uncertainty calibration (a stated evaluation metric) cannot be assessed without multiple seeds and multiple trajectories.
- The current ground truth is the same numerical model used to generate the observations. This is legitimate for a synthetic prototype, but it means “accuracy” is model-relative, not real-world accuracy.

### 6.6 Readiness verdict

| Area | Readiness for Component 3 | Readiness for Component 4 |
|---|---|---|
| Observation ingestion | Medium — clean CSV, but missing observer geometry/epoch | Medium |
| Uncertainty handling | Medium — σ present, covariance absent | Low |
| Propagation | Low — no arbitrary-state API | Low |
| Ground truth | Low — co-located with inputs, no 3D state per epoch | Low |
| Future prediction window | None | None |
| Observability constraints | None | None |
| Evaluation harness | None | None |
| Provenance/schema | Low | Low |

**Conclusion:** Components 1–2 provide a useful **data-generation seed**, not a ready interface. Component 3 can be prototyped against the current CSV with modest adapters, but Component 4 cannot be implemented responsibly until a propagation/prediction interface, a future observation window, and observability constraints exist.

### 6.7 Post-rename readiness check (2026-11-11)

The repository rename did not change any code, configuration or data contract. A fresh inspection of the renamed root confirms:

| Readiness item | Current state after rename | Effect on readiness |
|---|---|---|
| Component 3 estimator code | No files or modules | Not started |
| Component 4 selector code | No files or modules | Not started |
| Candidate-orbit schema | Absent | Must be defined before estimation |
| Propagation API for arbitrary states/times | Absent | Blocks both Components 3 and 4 |
| Observer ephemeris / per-epoch geometry | Absent from observations | Must be added before estimation |
| Future observation window | Absent; observations end at 1826.25 d | Blocks Component 4 |
| Ground-truth separation | Absent; `true_*` columns remain in `observations.csv` | Blocks blind evaluation |
| Observability constraints | Absent | Blocks realistic scheduling |
| Test framework and CI | Absent (`pytest` not installed) | Blocks reliable integration work |
| Data contracts / schema versions | Absent | Blocks stable component interfaces |

**Readiness verdict remains unchanged:** Component 3 is feasible only with adapter work and a new propagation interface; Component 4 is not ready to start until the future window, propagation/prediction interface, observer geometry and observability model exist.

---

## 7. Code Quality Assessment

### 7.1 Modularity

**Strengths:**

- Component 2 is decomposed into five single-purpose modules (`trajectory_loader`, `observation_schedule`, `observer_model`, `coordinate_converter`, `measurement_noise`) plus an orchestrator. This is good scientific software design.
- Functions are small, mostly pure, and easy to test.
- The configurable simulator separates config loading, simulation building, plotting and orchestration.

**Weaknesses:**

- Component 1 has no module boundary between library code and executable scripts; `main.py`, `nbody_simulator.py` and `nbody_realistic.py` execute at import.
- `src/` is a flat directory with no package `__init__.py`; component boundaries are implicit.
- Analysis/plotting code is mixed with data-generation code in `compare_observation_datasets.py`.

### 7.2 Separation of concerns

- Good separation inside Component 2's scientific steps.
- Poor separation between I/O, plotting and physics in `configurable_simulator.generate_trajectory()` (it integrates, writes CSV, writes config, writes metadata and plots in one function).
- Poor separation between model inputs and ground truth in the observation CSV.
- Tests mix validation logic, printing, file writes and simulation execution.

### 7.3 Naming conventions

- Modern schema is consistent snake_case with unit suffixes (`x_au`, `vx_au_per_year`).
- Legacy schema uses mixed case (`x_AU`, `time_yr`, `distance_AU`), creating two vocabularies.
- Function names are clear (`generate_observation_times`, `calculate_relative_positions`).
- Module names are clear, except `main.py` (ambiguous) and `nbody_simulator.py` vs `configurable_simulator.py` vs `nbody_realistic.py` (three “simulators” with different contracts).
- No constants module; magic numbers are scattered.

### 7.4 Function and class design

- No classes or dataclasses; data are passed as dicts and NumPy arrays. This is acceptable for a prototype but weakens schema enforcement.
- Return types are implicit; `load_trajectory` returns a dict whose keys are only documented in a docstring.
- `generate_trajectory` returns a DataFrame but also writes five files; side effects are not obvious from the signature.
- `build_simulation` returns a REBOUND object without exposing the asteroid index or a propagation helper.
- No `Protocol`/ABC for observers or schedules, so extension requires editing dispatch logic.

### 7.5 Repeated code

| Duplication | Locations | Consequence |
|---|---|---|
| Planetary mass/axis constants | `configurable_simulator.BODY_DATA`, `nbody_simulator.PLANETS`, `horizons_loader.BODY_CONFIG`, `tests/diagnose_eros_horizons.BODY_CONFIG` | Drift risk; different rounding |
| Noise residual calculation (`RA wrap`, `cosδ`, `×3600`) | `compare_observation_datasets.py` (twice), `test_observation_output.py`, `test_all_observation_outputs.py` | Four copies of the same statistics |
| Full observation pipeline | `test_coordinate_converter.py`, `test_measurement_noise.py`, `test_observer_model.py`, `test_observation_schedule.py`, `test_trajectory_loader.py` | Test setup duplicated; changes must be replicated |
| JSON config loading | `configurable_simulator.load_config`, `observation_generator.load_config` | Different error behaviour |
| `365.25` | `trajectory_loader`, `observation_generator`, `horizons_loader`, tests | Single source of truth absent |

### 7.6 Hardcoded values

- `1826.25` days (5 yr) and `262` observations in tests and plotting.
- `385.0` debug row in `compare_observation_datasets.load_datasets`.
- `vmin=0, vmax=1826.25` and `xlim(-2, 2)`.
- Dataset names/labels/colours in `DATASET_NAMES`, `DATASET_COLORS`.
- `EPOCH_JD = 2460676.5` in legacy scripts/tests.
- `DAYS_PER_YEAR = 365.25`, `ARCSEC_TO_DEG = 1/3600`, `AU_KM = 149597870.7` in multiple files.
- `BODY_DATA` masses/axes.
- `obliquity_deg=23.43928` defaults in code and config.

### 7.7 Configuration management

- JSON is a reasonable choice for a prototype.
- No schema, no version, no validation, no defaults, no environment overrides.
- Decorative keys create false configurability (§4.4, §4.11).
- No config inheritance or experiment manifest.
- Relative paths are resolved inconsistently (module root vs CWD in tests).

### 7.8 Type hints

- **None** in the source or tests (no function annotations, no `typing` imports).
- Dict returns are untyped.
- NumPy array shapes are documented in docstrings but not encoded.
- This impedes static analysis and future integration.

### 7.9 Documentation and docstrings

- Module docstrings are largely absent (files begin with a blank line).
- Function docstrings are present for the Component 2 helpers and `horizons_loader`, but many are one line and omit parameters, returns, units and exceptions.
- `configurable_simulator.build_simulation` has a one-line docstring; the most complex function (`generate_trajectory`) has one line.
- `docs/COMPONENT_1.md` is useful but overstates validation: it lists “Required trajectory columns checked” and “Timestamp ordering checked,” which are implemented in **Component 2's loader**, not in Component 1. It also says Component 2 “should read trajectory.csv and its metadata,” but Component 2 does not read metadata.
- No Component 2 documentation at all.
- No README, no quickstart, no API reference, no schema reference.

### 7.10 Logging and error handling

- All output is `print()`; no `logging` module, levels, timestamps or file logs.
- Errors are generic `ValueError`/`FileNotFoundError`; no domain-specific exceptions.
- No retry/cleanup for network calls in `horizons_loader`.
- No context in some errors (e.g., which config key is missing).
- `plt.show()` in legacy scripts can block headless runs.
- No warnings for overwriting existing outputs.

### 7.11 Testing quality

**Strengths:**

- Genuine scientific checks exist: Kepler period, perihelion/aphelion, IAS15 tolerance sensitivity, repeatability, Eros vs Horizons, noise statistics, timestamp/schema checks.
- The observation dataset validation is thorough for the current schema (columns, counts, finiteness, ranges, σ, recovered noise).
- The in-memory recomputation performed during this review is a strong reproducibility check.

**Critical weaknesses:**

- `pytest` is not installed; there is no test runner configuration.
- Most files are scripts, not tests; several have **no assertions** (`test_trajectory_loader.py`, `test_observation_schedule.py`, `check_configurable_runs.py`, `check_horizons_epoch.py`, `test_tolerance_sensitivity.py` prints only).
- Several modules execute at import: `test_horizons_loader.py` performs network queries; `test_repeatability.py` and `test_tolerance_sensitivity.py` run simulations and write data. Under pytest collection, this would be destructive and slow.
- `test_component1_integration.py::test_configuration(config_path)` would be collected by pytest and fail with “fixture 'config_path' not found.”
- Tests depend on pre-generated datasets under `data/`; they are not hermetic and cannot run on a clean checkout.
- Several tests hardcode 262 observations and 1826.25 days, so a valid configuration change breaks them.
- No negative tests for invalid configs, invalid cadence, out-of-range times, missing metadata, or frame mismatch.
- No coverage measurement, no CI, no test data fixtures.
- `tests/validation_report.md` is captured stdout, not an automated result.

### 7.12 Performance considerations

- The 1001-sample, 5-body, 5-year simulation is fast; the sequential `sim.integrate(t)` loop is appropriate.
- Component 2 is vectorized except for the `np.interp` per-axis loop (fine).
- The comparison script loads three datasets and creates large figures; acceptable.
- Future Components 3–4 will need many candidate propagations. Re-integrating from t=0 for each candidate would be wasteful. REBOUND simulations should be reused, or a fast two-body/keplerian propagator used for candidate scoring, with N-body refinement only where needed.
- No caching of interpolation or observer ephemerides; no profiling; no memory concerns at current scale.

### 7.13 Scientific numerical correctness

- Two-body Kepler check passes (0.0039% period error).
- IAS15 tolerance differences are ~3e-13 AU in the saved tolerance test; the integrator is more accurate than needed.
- Eros 5-planet vs 8-planet errors (14,074 km vs 6,196 km at 5 yr) are plausible for approximate masses and missing outer planets; they are not a validation of the configurable synthetic model.
- The coordinate rotation and RA/Dec formulas are correct.
- The noise conversion is correct for the stated convention.
- The main numerical weakness is **linear interpolation** (0.22″–1.73″), which is larger than the 0.5″ noise and should be replaced with Hermite/cubic interpolation or exact propagation.
- The main physical omissions are **light-time (~20″)** and **observability constraints** (25.6% of epochs <30° elongation).

### 7.14 Consolidated code-quality findings

| ID | Severity | Type | Finding |
|---|---|---|---|
| Q-01 | Critical | Confirmed defect | Tests are not runnable as a suite; pytest absent; import-time side effects; missing fixture. |
| Q-02 | Critical | Confirmed defect | No packaging (`__init__.py`, `pyproject.toml`) or stable entry points. |
| Q-03 | High | Confirmed defect | No type hints; dict-based implicit schemas. |
| Q-04 | High | Confirmed defect | Duplicated constants and residual calculations. |
| Q-05 | High | Confirmed defect | Hardcoded dataset counts/paths/limits in tests and plots. |
| Q-06 | Medium | Confirmed defect | Print-based logging; generic exceptions. |
| Q-07 | Medium | Confirmed defect | Legacy scripts execute at import and write files. |
| Q-08 | Medium | Confirmed defect | Config keys that do not control behaviour. |
| Q-09 | Medium | Confirmed defect | No CI or lint/type-check configuration. |
| Q-10 | Low | Confirmed defect | Missing module docstrings; inconsistent blank first lines. |
| Q-11 | Low | Confirmed defect | Long lines and ad-hoc section banners; inconsistent formatting. |
| Q-12 | Optional | Suggestion | Add dataclasses/pydantic for contracts, `ruff`/`black`, `mypy`, `pytest-cov`. |

---

## 8. Scientific and Numerical Considerations

### 8.1 Dynamics and units

- REBOUND units `(yr, AU, Msun)` imply \(G = 4\pi^2\); this is internally consistent.
- The asteroid is a massless test particle; planetary back-reaction is absent. For a 5-year integration this is an excellent approximation.
- The Sun is a massive particle at the origin before `move_to_com()`; after the transformation, heliocentric relative states are recovered by subtracting the Sun. Correct.
- Planetary masses are approximate and, in the configurable model, planets are circular/coplanar/aligned. This is a **synthetic planetary system**, not the solar system.
- No general relativity, Yarkovsky, solar radiation pressure, collisions, or non-gravitational forces. For a 5-year prototype at 2.5 AU, these are small but not zero; they should be listed as limitations.
- The Eros comparison shows that adding outer planets reduces the 5-year error from ~14,000 km to ~6,200 km. This is a useful sensitivity result, but it does not establish the accuracy of the synthetic configurable model.

### 8.2 Time, frames and epochs

- There is no absolute epoch. Times are elapsed years/days from the start of the simulation. This is explicitly stated in Component 2 assumptions and is appropriate for synthetic experiments.
- The ecliptic frame is not tied to J2000 or mean-of-date; the fixed obliquity 23.43928° is J2000-like. For a synthetic prototype, this is acceptable if documented as a fixed convention.
- No precession/nutation. Over 5 years, precession is ~250″, far larger than the 0.5″ noise, but it is irrelevant if the frame is defined as fixed and the time is elapsed. It becomes relevant if real epochs are introduced.
- No UTC/TAI/TT/TDB distinction. The Horizons loader labels JD as TDB, but the synthetic pipeline never uses a calendar.

### 8.3 Interpolation error

The pipeline interpolates asteroid positions linearly between samples spaced 1.82625 days (0.005 yr), despite having velocities. Using cubic Hermite interpolation with the same positions and velocities as a reference, the linear interpolation error in **sky direction** is:

- median **0.223″**,
- 95th percentile **1.048″**,
- maximum **1.731″**,
- position error median 1.33×10⁻⁵ AU, max 3.06×10⁻⁵ AU,
- observer–asteroid range 1.15–4.00 AU.

With a measurement σ of 0.5″, the interpolation error is comparable to or larger than the noise for a substantial fraction of epochs. This is a **scientific correctness issue**, not merely an implementation detail. Recommended fixes:

1. Use cubic Hermite interpolation with the available velocity columns (cheap, no new data).
2. Or evaluate the N-body trajectory at the observation times directly.
3. Or propagate a local two-body solution between samples.
4. If linear interpolation is retained, document the error budget and increase the trajectory sampling rate.

### 8.4 Light-time, aberration and topocentric effects

Not modelled. Order-of-magnitude estimates from the current data:

- Median range 2.76 AU → light time ≈ 1377 s ≈ 22.9 min (range 1.15–4.00 AU → 9.6–33.3 min).
- Median angular rate 0.3545°/day → displacement during light time ≈ **0.0057° ≈ 20″**.
- Annual aberration due to the observer's ~30 km/s motion is of order **20″**.
- Geocentric-to-topocentric parallax at 1.5–2.8 AU is of order **3–9″**.
- Solar gravitational deflection is small except near conjunction, but the current data include a 0.50° elongation epoch where it is not negligible.

For a 0.5″ noise model, these are **tens of sigma** systematics. They do not invalidate a synthetic prototype whose purpose is relative schedule comparison, but they must be documented and, ideally, implemented before claiming astrometric realism. At minimum, add a `light_time_correction: false` flag to metadata so downstream users know.

### 8.5 Observer geometry and observability

The observer is a circular 1 AU point in the ecliptic. The generated epochs include:

- minimum solar elongation **0.50°**,
- 25.6% of epochs <30°,
- 37.4% <45°,
- 49.2% <60°.

Real optical observatories cannot observe at 0.5° elongation. Component 4's “informative” times must be filtered by observability, or it will select physically impossible epochs. The current data also include epochs where the asteroid is near the Sun, which would be lost to daylight.

Recommended observability model (minimum viable):

- solar elongation > 45° (or 60°),
- solar altitude constraints at the site (if a site is introduced),
- lunar separation (optional),
- airmass/altitude (optional),
- a `visible` boolean and `elongation_deg` column per epoch.

### 8.6 Noise and statistical validity

- Independent Gaussian noise with σ_RA cosδ = σ_Dec = 0.5″ is a reasonable first model.
- The conversion is correct; the recovered σ values are consistent.
- The same seed/length across scenarios produces identical residuals. For a comparative noise study, use different seeds per scenario or, better, multiple seeds and report distributions.
- No outlier model, no systematic errors, no correlated noise, no magnitude-dependent σ.
- No covariance between RA and Dec; the CSV implies independence but does not state it.
- The noise is added in the tangent plane, which is correct, but the resulting sky positions are not re-normalised; for 0.5″ errors this is negligible.

### 8.7 Identifiability and uncertainty

- The current datasets are dense (262 observations) and span 5 years, so a 6-parameter orbit is likely identifiable in principle.
- Sparse subsets (Component 4) may be much less identifiable, especially with a single observer and a short arc.
- No covariance/uncertainty is produced by Components 1–2, which is expected; Component 3 must produce it.
- Candidate-orbit spread must not be presented as a calibrated uncertainty without evaluation (the project plan explicitly warns about this).
- Multiple independent trajectories and noise seeds are required for calibration and robustness metrics.

### 8.8 Validation evidence and its limits

| Evidence | Result | Interpretation |
|---|---|---|
| Two-body perihelion/aphelion | 2.0000 / 3.0000 AU | Correct for a=2.5, e=0.2 |
| Kepler period | 3.953000 vs 3.952847 yr (0.0039%) | Strong baseline validation |
| IAS15 tolerance | ~3×10⁻¹³ AU between ε 1e-9 and 1e-13 | Integrator far exceeds needs |
| Repeatability | Existing test design compares to 1e-10/1e-12 | Not re-run; design is sound |
| Eros 5 planets | 14,073.6 km at 5 yr | Model-vs-ephemeris, approximate masses |
| Eros 8 planets | 6,196.1 km at 5 yr | Better, still not raw astrometry |
| Observation schema | 3 × 262 rows valid | Strong for current schema |
| Noise recovery | RA 0.466″, Dec 0.503″ for σ=0.5″ | Correct |
| Pipeline reproducibility | Exact recomputation | Strong |

**Limits:** the Eros validation uses Horizons initial states and the same force model; it is a consistency/perturbation sensitivity test, not an independent accuracy claim. The synthetic scenarios have no external truth. The validation_report.md is a captured output, not a live CI result.

### 8.9 Numerical risks

- Linear interpolation error (dominant).
- Light-time/aberration systematics (dominant if realism is claimed).
- `np.arange` floating accumulation for non-round cadences (minor; endpoint handling mitigates).
- RA wrap in plotting (handled) and in residual statistics (handled).
- Pole singularity in RA noise (explicitly rejected).
- No check that `time_days` and `time_years` use the same year length as the observer period (both use 365.25, so consistent).
- No check that the observation times are not duplicated after endpoint append (the `isclose` guard handles the common case).
- Potential mismatch if a future trajectory uses 365.2422 days/year; the loader would reject it.

### 8.10 Scientific recommendations

1. Replace linear interpolation with Hermite/cubic using velocities; quantify the residual in tests.
2. Add optional light-time correction and record the flag.
3. Add solar elongation and a `visible` flag; filter Component 4 candidates.
4. Persist observer ephemerides and range per epoch.
5. Separate ground truth from model inputs.
6. Use multiple noise seeds and multiple trajectories; report distributions, not single realisations.
7. Save the full planetary system state and masses in metadata.
8. Document the frame/epoch conventions explicitly.
9. Keep the idealized observer for the first active-scheduling experiments, but label it clearly and avoid claiming real astrometric accuracy.

---

## 9. Directory Structure Assessment

### 9.1 Assessment of the current structure

**Appropriate for a small prototype:**

- Top-level separation of `src`, `configs`, `data`, `docs`, `tests`, `plots`, `results` is understandable.
- `data/runs/<scenario>/` is a good pattern for per-run outputs.
- `data/observations/<dataset>/` mirrors it well.
- `results/component-2/figures/` is a reasonable analysis output location.

**Not appropriate for a growing scientific Python project:**

- `src/` mixes reusable libraries, CLI scripts, legacy demos and analysis code, with no package boundary.
- Generated data, test artefacts, legacy outputs and modern runs share `data/`; there is no distinction between curated datasets and disposable artefacts.
- `plots/` duplicates `data/runs/*/` and `results/`.
- No `experiments/` directory for configuration-driven studies.
- No `schemas/` or `docs/schemas/` for data contracts.
- No `scripts/` for operational entry points.
- No `tests/fixtures/` or `tests/data/` for hermetic fixtures.
- No `benchmarks/`, `notebooks/` or `archive/` for exploratory work and legacy code.
- No `README.md`, `LICENSE`, `CITATION.cff`, `pyproject.toml`, `CHANGELOG.md`, `.github/workflows/`.
- `docs/` has only one component document; `docs/development/` now contains this analysis and the refactoring plan, but there is no architecture, testing or schema documentation yet.

### 9.2 Recommended structure (do not move files yet)

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
│       │   ├── constants.py          # AU_KM, DAYS_PER_YEAR, ARCSEC_TO_DEG, OBLIQUITY_DEG
│       │   ├── time.py               # Epoch, time scales, JD conversions
│       │   ├── units.py
│       │   ├── io.py                 # atomic CSV/JSON writes, hashing, manifests
│       │   ├── validation.py
│       │   ├── logging.py
│       │   └── errors.py
│       ├── component1_simulation/
│       │   ├── bodies.py             # BodySpec, planetary constants
│       │   ├── initial_conditions.py
│       │   ├── simulator.py          # build/propagate
│       │   ├── trajectory.py         # schema + writer
│       │   └── plotting.py
│       ├── component2_observations/
│       │   ├── loader.py
│       │   ├── schedule.py
│       │   ├── observer.py
│       │   ├── frames.py
│       │   ├── noise.py
│       │   ├── generator.py
│       │   └── plotting.py
│       ├── component3_estimation/
│       │   ├── model.py
│       │   ├── fitter.py
│       │   ├── candidates.py
│       │   ├── propagate.py
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
│   └── fixtures/                     # small versioned CSVs, not full datasets
├── data/
│   ├── curated/                      # small, versioned reference data
│   └── README.md
├── artifacts/                        # generated runs, observations, plots (gitignored)
│   ├── runs/
│   ├── observations/
│   ├── estimates/
│   └── evaluation/
├── experiments/
│   ├── 001_baseline/
│   │   ├── config.yaml
│   │   ├── run.py
│   │   └── README.md
│   └── notebooks/
├── results/                          # curated result tables/figures for reports
├── docs/
│   ├── index.md
│   ├── user/
│   │   ├── installation.md
│   │   ├── quickstart.md
│   │   └── concepts.md
│   ├── components/
│   │   ├── component-1-simulation.md
│   │   ├── component-2-observations.md
│   │   ├── component-3-estimation.md
│   │   ├── component-4-selection.md
│   │   └── component-5-evaluation.md
│   ├── schemas/
│   │   ├── trajectory-v1.md
│   │   ├── observations-v1.md
│   │   ├── metadata-v1.md
│   │   └── orbit-solution-v1.md
│   ├── development/
│   │   ├── architecture.md
│   │   ├── CODEBASE_ANALYSIS.md      # this report
│   │   ├── REFACTORING_PLAN.md       # prioritized checklist and contracts
│   │   ├── testing.md
│   │   ├── release-process.md
│   │   └── contributing.md
│   ├── experiments/
│   └── adr/                          # architecture decision records
├── scripts/                          # operational helpers (not core library)
└── archive/                          # legacy scripts and old datasets
```

### 9.3 Migration principles

1. **Do not move files in this phase.** Freeze 0.2.0 first.
2. Separate **library code** from **executable scripts** and **legacy demos**.
3. Separate **curated datasets** from **generated artefacts**.
4. Version every data contract before adding Components 3–4.
5. Keep small, deterministic fixtures in `tests/fixtures/`; do not commit full generated datasets.
6. Put experiment-specific configs and run scripts under `experiments/`, not in the core `configs/`.
7. Make `artifacts/` disposable and reproducible from configs.
8. Keep `results/` for curated tables/figures referenced by the report.

---

## 10. Version 0.2.0 Implementation Status

### 10.1 Version declaration

There is **no machine-readable version** in the repository:

- no `__version__`,
- no `pyproject.toml`/`setup.cfg`,
- no `CHANGELOG.md`,
- no Git tag (no `.git` at all).

“0.2.0” is therefore a project label, not something the code can report or enforce. Add a version module and tag the snapshot before further work.

### 10.2 Completed functionality

| Capability | Status | Evidence |
|---|---|---|
| Two-body Sun–asteroid simulation | **Implemented** (legacy `main.py`) | `data/trajectory_two_body.csv`, 1000 rows; baseline validation passes |
| Configurable synthetic N-body simulation | **Implemented** | `configurable_simulator.py`; 3 runs × 1001 rows; metadata |
| REBOUND IAS15 integration | **Implemented** | Code and metadata; tolerance artefacts |
| Configurable asteroid orbital elements | **Implemented** | Three configs with different e/i |
| Configurable planetary body selection | **Partially implemented** | Body names selectable; masses/elements hardcoded; all configs use the same 4 planets |
| Trajectory CSV/config/metadata/plots | **Implemented** | Per-run directories |
| Horizons-initialised Eros simulation | **Implemented separately** | `nbody_realistic.py`; not integrated into the configurable interface |
| Ground-truth schema validation | **Implemented** | `trajectory_loader.py`, `validate_ground_truth.py` |
| Fixed-cadence observation scheduling | **Implemented** | 7 d cadence, 262 epochs |
| Idealized circular observer | **Implemented** | `observer_model.py` |
| Ecliptic → equatorial rotation | **Implemented** | `coordinate_converter.py` |
| RA/Dec calculation | **Implemented** | `coordinate_converter.py` |
| Seeded Gaussian angular noise | **Implemented** | `measurement_noise.py`; reproducibility verified |
| Observation CSV/metadata | **Implemented** | 3 datasets × 262 rows |
| Comparative visualization | **Implemented** | 5 PNG/PDF figure pairs + summary |
| Scientific validation scripts | **Partially implemented** | Script-style; not a pytest suite |

### 10.3 Partially completed functionality

| Capability | What exists | What is missing |
|---|---|---|
| Configurable gravitational model | Body list + hardcoded masses/axes | Planetary elements/phases in config; arbitrary epochs; full system state in metadata |
| Observation metadata | Config echo + assumptions + units | Run timestamp, versions, input metadata/hash, schema version, observer ephemeris |
| Reproducibility | Seed, config echo, exact recomputation | Input hash, config copy, code version, multi-seed support |
| Comparative analysis | 3 hardcoded scenarios, 5 figures | Config-driven datasets, independent noise, CLI, manifest |
| Testing | Many useful checks | Pytest structure, fixtures, negative tests, CI, coverage |
| Documentation | `COMPONENT_1.md` | README, Component 2 docs, schemas, API, testing, release docs |

### 10.4 Known limitations (explicit or evident)

- Synthetic planetary system: circular, coplanar, aligned planets; approximate masses.
- No absolute epoch; elapsed simulation time only.
- Idealized circular observer; no real Earth ephemeris.
- No light-time, aberration, topocentric parallax, precession/nutation.
- No observability constraints (25.6% of epochs <30° elongation).
- Linear interpolation of positions; velocities unused.
- Independent Gaussian noise only; one seed per scenario.
- No uncertainty quantification or candidate orbits.
- No held-out future window.
- Eros validation is model-vs-ephemeris, not raw astrometry.
- Legacy and modern schemas coexist.
- No versioning, packaging or CI.

### 10.5 Missing functionality (Components 3–5)

- Orbit estimator: no fitting code, no candidate generation, no covariance/uncertainty.
- Active observation selector: no scoring, no candidate-time evaluation, no observation requests.
- Evaluation: no active/fixed/random comparison, no metrics, no budget accounting, no calibration.
- Counterfactual dynamics: no implementation.
- Dashboard: not implemented (optional in the plan).
- Real-data ingestion: not implemented (only Horizons initial states for Eros).

### 10.6 Features that must not be described as implemented

Do **not** claim any of the following for 0.2.0:

- orbit estimation or orbital-parameter fitting,
- best-fit orbit or plausible candidate orbit solutions,
- uncertainty quantification or calibrated confidence intervals,
- active observation selection or information-gain scoring,
- fixed-vs-random-vs-active schedule comparison,
- observation-efficiency metrics,
- counterfactual dynamics,
- real asteroid astrometric validation,
- light-time/aberration-corrected astrometry,
- physically realistic observability scheduling,
- a calibrated noise model beyond independent Gaussian angular errors,
- a production-ready or fully tested software package.

### 10.7 Test evidence status

| Test area | Status | Notes |
|---|---|---|
| Loader/schedule/observer/coordinates/noise | Executed, pass (re-confirmed after rename) | Read-only scripts |
| Observation dataset validation (3 datasets) | Executed, pass (re-confirmed after rename) | Read-only |
| Ground-truth schema | Executed, pass (re-confirmed after rename) | Read-only |
| Baseline physics | Executed, pass (re-confirmed after rename) | Read-only; 0.0039% period error |
| Pipeline recomputation | Executed, exact (re-confirmed after rename) | In-memory, no writes |
| Component 1 integration | Not executed | Regenerates data |
| Repeatability | Not executed | Regenerates data |
| Tolerance sensitivity | Not executed | Regenerates data; saved summary inspected |
| Eros/Horizons validation | Not executed | Network + writes; saved CSVs inspected |
| Pytest suite | Not executable | pytest not installed |

The read-only checks were re-run against the renamed repository on 2026-11-11 and matched the original results. The data-writing and network checks were inspected through their existing artefacts only.

---

## 11. Prioritized Issues and Recommendations

### 11.1 P0 — Critical, fix before building Components 3–4

| ID | Issue | Location | Recommendation | Acceptance criterion |
|---|---|---|---|---|
| P0-01 | Script entry point fails | `src/observation_generator.py:9-22` | Convert `src` to an installed package and use relative imports or `python -m`; document the command | `python -m orbit_discovery.cli.observe --help` works from any CWD |
| P0-02 | Metadata ignored; implicit contract | `trajectory_loader.py`, `observation_generator.py` | Read Component 1 metadata; validate frame/units/state_type/epoch before use | A mismatched trajectory raises a clear error |
| P0-03 | Ground-truth leakage | `observation_generator.py` output | Write `observations.csv` with model inputs only; write `ground_truth.csv` separately | Estimator can run without seeing truth columns |
| P0-04 | `.gitignore` excludes configs | `.gitignore` | Remove `*.json`, `*.csv`, `data/`, `plots/` broad rules; ignore only `artifacts/` and known generated files | `git status` shows all six configs and schema docs |
| P0-05 | No propagation interface | `configurable_simulator.py` | Add `propagate(initial_state, times, bodies)` and a state/element conversion API | Component 3 can evaluate arbitrary candidates without rewriting files |
| P0-06 | No future observation window | configs/data | Extend simulation horizon or reserve a held-out future interval | Component 4 can request times beyond the last observation |
| P0-07 | Test suite not runnable | `tests/` | Adopt pytest; move scripts to `scripts/`; add fixtures; remove import-time execution | `pytest` passes on a clean checkout |
| P0-08 | Missing `astroquery` dependency | requirements | Add `astroquery` to an optional `network` extra and the lock file | Fresh install can run Horizons scripts |
| P0-09 | CWD-relative test paths | `tests/*.py` | Use `conftest.py` fixtures and `PROJECT_ROOT` | Tests pass from any CWD |
| P0-10 | Interpolation error exceeds noise | `observation_schedule.py` | Use cubic Hermite with velocities or direct propagation | Interpolation residual <0.05″ in tests |

### 11.2 P1 — High priority, needed for scientific credibility

| ID | Issue | Recommendation |
|---|---|---|
| P1-01 | Decorative config keys | Either implement dispatch (`observer.model`, `noise.model`, frames) or remove them and document fixed behaviour |
| P1-02 | No observer ephemeris in output | Store observer position/velocity and range per epoch |
| P1-03 | No light-time/aberration | Add optional light-time correction; record the flag; estimate the bias |
| P1-04 | No observability constraints | Add solar elongation and `visible` flag; filter Component 4 candidates |
| P1-05 | Planetary system not in metadata | Save masses, a, e, i, Ω, ω, M and phases for every body |
| P1-06 | Identical noise realisations | Use distinct seeds per scenario; support multiple seeds for calibration |
| P1-07 | No schema versions | Add `schema_version` to CSV metadata and a `docs/schemas/` page |
| P1-08 | No config copy/hash in observations | Copy the resolved config and hash the input trajectory |
| P1-09 | Windows paths in JSON | Store POSIX-style relative paths; resolve at read time |
| P1-10 | Hardcoded counts/limits in tests/plots | Derive from metadata/config; add explicit expected values in fixtures |
| P1-11 | No README/Component 2 docs | Add README and component docs before further development |
| P1-12 | No version declaration | Add `version.py`, `pyproject.toml`, tag `v0.2.0` |

### 11.3 P2 — Medium priority, quality and maintainability

| ID | Issue | Recommendation |
|---|---|---|
| P2-01 | Duplicate planetary constants | Create a single `core/constants.py` / `bodies.py` |
| P2-02 | Duplicate residual calculation | Extract `sky_residuals()` into `evaluation/metrics.py` |
| P2-03 | No type hints | Add annotations to public functions and dataclasses for contracts |
| P2-04 | Print-based logging | Adopt `logging` with levels; CLI controls verbosity |
| P2-05 | Generic exceptions | Add `ConfigurationError`, `SchemaError`, `DataError` |
| P2-06 | Legacy scripts at import | Move to `archive/` or guard with `if __name__ == "__main__"` |
| P2-07 | No CI | Add GitHub Actions for lint, type-check, pytest on a small fixture |
| P2-08 | No lint/format config | Add `ruff` and `black` (or equivalent) |
| P2-09 | Long analysis script with hardcodes | Split into `load`, `plot`, `summarize`; drive by a manifest |
| P2-10 | No negative tests | Add tests for bad configs, out-of-range times, frame mismatch, missing metadata |

### 11.4 P3 — Low priority / optional

| ID | Issue | Recommendation |
|---|---|---|
| P3-01 | Missing module docstrings | Add one-paragraph module docstrings with units and contracts |
| P3-02 | Inconsistent blank first lines/long lines | Apply formatter |
| P3-03 | `plt.show()` in scripts | Use `--show`/`--no-show`; default to saving only |
| P3-04 | No LICENSE/CITATION | Add MIT/Apache license and `CITATION.cff` |
| P3-05 | No benchmark | Add timing for N-body and candidate propagation |
| P3-06 | No dashboard | Defer; not core |
| P3-07 | Validation report narrative | Regenerate from live tests; remove stale claims |

### 11.5 Confirmed defect vs risk vs suggestion summary

- **Confirmed defects:** P0-01, P0-02, P0-03, P0-04, P0-07, P0-08, P0-09, P0-10, P1-01, P1-06, P1-08, P1-09, P1-10, P2-01…P2-06.
- **Confirmed limitations:** idealized observer, linear interpolation (now quantified), no light-time, no observability, synthetic planetary system, no epoch, single seed.
- **Risks:** future schema drift, silent unit/frame mismatch, REBOUND version behaviour, candidate-orbit non-identifiability, uncertainty miscalibration.
- **Suggestions/optional:** packaging, typing, CI, linting, docs, dashboard, benchmarks.

---

## 12. Proposed Refactoring Strategy

> **Detailed plan:** see `docs/development/REFACTORING_PLAN.md` for the prioritised checklist, proposed contracts, approval gates and acceptance criteria. This section is the summary.

> **Do not execute this refactor yet.** The project owner asked for analysis only. The sequence below is a plan with acceptance criteria.

### Phase 0 — Freeze and protect 0.2.0

1. Initialise Git at the project root.
2. Fix `.gitignore` so configs, schemas, docs and small fixtures are tracked; ignore `.venv/`, `__pycache__/`, `artifacts/`, large generated data.
3. Commit the current state as `v0.2.0` (or a clearly named snapshot).
4. Add a short `README.md` that states exactly what is and is not implemented.
5. Maintain `docs/development/CODEBASE_ANALYSIS.md` and `docs/development/REFACTORING_PLAN.md`, and link both from the README.

**Acceptance:** a clean clone contains all configs and docs; `python -m` commands are documented; no generated datasets are required to read the code.

### Phase 1 — Packaging and entry points

1. Add `pyproject.toml` with package metadata, optional dependency groups (`sim`, `analysis`, `network`, `test`), and a `src` layout.
2. Create `src/orbit_discovery/` with `__init__.py` and `version.py`.
3. Move reusable code into component subpackages; move legacy scripts to `archive/`.
4. Replace module-level execution with `main()` functions and `if __name__ == "__main__"`.
5. Provide CLI entry points: `simulate`, `observe`, `estimate`, `select`, `evaluate`.
6. Fix the Component 2 import/entry-point defect.

**Acceptance:** `pip install -e .[test]` works; every CLI `--help` works from any CWD; no import writes files or opens plots.

### Phase 2 — Data contracts and provenance

1. Define JSON Schemas (or pydantic models) for simulation config, observation config, `trajectory.csv`, `observations.csv`, `metadata.json`.
2. Add `schema_version` to every output.
3. Add `epoch_jd_tdb` (nullable), `time_scale`, `frame`, `units` objects.
4. Save full planetary system state/masses in run metadata.
5. Copy resolved configs into output directories; hash input trajectories.
6. Split model inputs and hidden ground truth:
   - `observations.csv` — times, RA/Dec, σ, observer geometry, range, flags.
   - `ground_truth.csv` — true 3D state, true RA/Dec, true elements.
7. Standardise POSIX relative paths and add a `manifest.json` per experiment.

**Acceptance:** a validator rejects a trajectory whose metadata frame/units/state_type do not match the consumer's expectations; ground truth is never in `observations.csv`.

### Phase 3 — Scientific hardening

1. Implement cubic Hermite interpolation using velocities; add a regression test against direct propagation.
2. Add optional light-time correction and record the flag.
3. Persist observer ephemerides; add solar elongation and `visible`.
4. Extend the trajectory horizon or reserve a future window for Component 4.
5. Support multiple seeds and multiple trajectories; add Monte Carlo utilities.
6. Add orbital-element conversion (state ↔ elements) and final osculating elements.
7. Quantify and document the error budget (interpolation, light-time, aberration, noise).

**Acceptance:** interpolation residual <0.05″; light-time flag documented; at least one held-out future window; multi-seed datasets reproducible.

### Phase 4 — Test and CI

1. Adopt pytest; move script-style checks to `scripts/` or convert to tests.
2. Add `conftest.py` with project-root and fixture helpers.
3. Add unit tests for each helper; integration tests for the pipeline; scientific regression tests for Kepler/tolerance/Eros.
4. Remove hardcoded 262/1826.25; derive from fixtures or assert against explicit expected values.
5. Add negative tests for invalid configs, frame mismatch, out-of-range times, missing metadata, pole noise.
6. Add CI with lint, type-check, pytest and a small end-to-end run.

**Acceptance:** `pytest` passes on a clean checkout; CI is green; no test writes outside `tmp_path`.

### Phase 5 — Documentation

1. README with status, install, quickstart and limitations.
2. Component docs for 1–5.
3. Schema docs for trajectory, observations, metadata, orbit solution.
4. Development docs: architecture, testing, release process, ADRs.
5. Experiment docs with reproduction commands.

**Acceptance:** a new contributor can reproduce the three scenarios from the README without reading source code.

### Phase 6 — Components 3 and 4

Only after Phases 1–5:

1. Implement the propagation/prediction interface.
2. Implement the orbit estimator with candidate generation and uncertainty.
3. Implement fixed/random/active schedule generators behind one protocol.
4. Implement the evaluation harness with equal budgets and hidden truth.
5. Run the comparison experiments and document results.

**Acceptance:** active vs fixed vs random comparison is reproducible, uses held-out truth, and reports uncertainty calibration.

---

## 13. Proposed Documentation Structure

```text
docs/
├── index.md                          # project overview, status, navigation
├── user/
│   ├── installation.md               # Python, venv, optional network deps
│   ├── quickstart.md                 # simulate → observe → estimate → select
│   ├── concepts.md                   # frames, units, time, noise, schedules
│   └── troubleshooting.md
├── components/
│   ├── component-1-simulation.md     # current COMPONENT_1.md, corrected
│   ├── component-2-observations.md   # missing today
│   ├── component-3-estimation.md     # planned
│   ├── component-4-selection.md      # planned
│   └── component-5-evaluation.md     # planned
├── schemas/
│   ├── trajectory-v1.md              # columns, units, frame, invariants
│   ├── observations-v1.md            # columns, σ semantics, truth separation
│   ├── metadata-v1.md                # provenance, versions, hashes
│   ├── orbit-solution-v1.md          # elements, covariance, candidates
│   └── config-v1.md                  # every key, required/optional, behaviour
├── development/
│   ├── architecture.md               # module boundaries and data flow
│   ├── CODEBASE_ANALYSIS.md          # this report
│   ├── REFACTORING_PLAN.md           # prioritized refactoring checklist
│   ├── testing.md                    # pytest layout, fixtures, CI
│   ├── release-process.md            # versioning, tags, changelog
│   ├── contributing.md
│   └── adr/                          # architecture decision records
├── experiments/
│   ├── 001-baseline.md
│   ├── 002-sparse-observations.md
│   └── 003-active-vs-fixed-vs-random.md
└── references.md                     # REBOUND, Horizons, IAU conventions
```

**Documentation priorities:**

1. `README.md` with an honest 0.2.0 status.
2. `docs/components/component-2-observations.md` (currently absent).
3. `docs/schemas/trajectory-v1.md` and `observations-v1.md`.
4. `docs/development/testing.md`.
5. Correct `COMPONENT_1.md` so it does not attribute Component 2 validations to Component 1 and does not claim that Component 2 reads metadata.

---

## Appendix A — Data Schema Snapshots

### A.1 Modern trajectory (`data/runs/synthetic_asteroid/trajectory.csv`)

```text
time_years,time_days,x_au,y_au,z_au,vx_au_per_year,vy_au_per_year,vz_au_per_year
0.0,0.0,2.0049665628240976,0.0,0.0,0.0,4.871845319980116,0.0
0.005,1.82625,2.0048438319721975,0.024358729335035485,0.0,-0.04909153026512701,4.87154696454143,0.0
```

1001 data rows; 0–5.000000 years; 0–1826.25 days.

### A.2 Observations (`data/observations/synthetic_asteroid_observations/observations.csv`)

```text
time_years,time_days,ra_deg,dec_deg,sigma_ra_cosdec_arcsec,sigma_dec_arcsec,true_ra_deg,true_dec_deg
0.0,0.0,335.41098752466377,-10.226383848241433,0.5,0.5,335.41094451966364,-10.226416094059436
0.019164955509924708,7.0,338.7614601644882,-8.92570882262332,0.5,0.5,338.76160637728077,-8.925631693842929
```

262 data rows; 0–1826.25 days.

### A.3 Legacy trajectory (`data/trajectory_two_body.csv`)

```text
time_yr,x_AU,y_AU,z_AU,vx_AU_per_yr,vy_AU_per_yr,vz_AU_per_yr,distance_AU
```

Not loadable by `trajectory_loader.load_trajectory` because the required modern columns are absent.

### A.4 Component 1 metadata keys

`simulation_name`, `run_utc`, `python_version`, `rebound_version`, `number_of_samples`, `duration_years`, `output_interval_days`, `integrator`, `integrator_epsilon`, `gravitational_bodies`, `position_reference`, `position_unit`, `velocity_unit`, `time_unit`, `initial_conditions`, `coordinate_frame`, `epoch_jd_tdb`, `state_type`, `massless_asteroid`, `output_interval_days_requested`, `final_time_years`.

### A.5 Component 2 metadata keys

`observation_name`, `input_trajectory`, `configuration_file`, `state_type`, `number_of_observations`, `observation_schedule`, `observer`, `coordinates`, `measurement_noise`, `coordinate_units`, `assumptions`, `output_file`.

---

## Appendix B — Quantities and Constants

| Quantity | Value used | Locations |
|---|---|---|
| Days per Julian year | 365.25 | `trajectory_loader.py`, `observation_generator.py`, `horizons_loader.py`, tests |
| Arcseconds per degree | 3600 | `measurement_noise.py`, analysis/tests |
| Kilometres per AU | 149,597,870.7 | legacy validation scripts |
| J2000 mean obliquity | 23.43928° | configs, `coordinate_converter.py` default |
| Standard simulation duration | 5.0 yr | configs, legacy scripts |
| Standard output interval | 1.82625 d | configs |
| Standard observation cadence | 7.0 d | observation configs |
| Standard noise | 0.5″ per axis | observation configs |
| Standard seed | 42 | observation configs |
| Eros epoch | JD 2460676.5 (TDB) | legacy scripts/tests |

---

## Appendix C — Glossary

| Term | Meaning in this repository |
|---|---|
| AU | Astronomical unit; distance unit |
| RA / Dec | Right ascension / declination; sky angles in degrees |
| `σ_RA cosδ` | Tangent-plane RA uncertainty in arcseconds |
| IAS15 | 15th-order adaptive integrator in REBOUND |
| Heliocentric ecliptic | Sun-centred Cartesian frame with the ecliptic as the xy plane |
| Equatorial | Frame rotated from ecliptic by the obliquity |
| Elapsed time | Simulation time from t=0, not a calendar date |
| Ground truth | Noise-free simulated state/coordinates used for evaluation |
| Candidate orbit | A plausible orbit solution consistent with observations (not implemented) |
| Active scheduling | Choosing observation times to reduce uncertainty (not implemented) |

---

## Appendix D — Repository Rename Record (Completed)

**Rename status: completed and verified.** The project moved from:

```text
<workspace>/prototype-1/code
```

to the current verified root:

```text
<workspace>/prototype-1/physics-guided-orbit-discovery-prototype
```

Verification performed after the rename:

| Check | Result |
|---|---|
| Former path `<workspace>/prototype-1/code` exists | No |
| Current path `<workspace>/prototype-1/physics-guided-orbit-discovery-prototype` exists | Yes |
| Parent workspace directory unchanged | Yes |
| Files excluding `.venv/` and `__pycache__/` | 103 (including both development documents) |
| Directories excluding `.venv/` and `__pycache__/` | 25 |
| Source Python files | 12 |
| Test/validation Python files | 19 |
| Configuration JSON files | 6 |
| `src/configurable_simulator.py` present | Yes |
| `src/observation_generator.py` present | Yes |
| `docs/development/CODEBASE_ANALYSIS.md` present | Yes |
| `docs/development/REFACTORING_PLAN.md` present | Yes |
| Git repository present | No (`.git` absent) |

The local `.venv/` was created before the rename. Its interpreter still runs from the new location, but recreating the virtual environment is recommended before the next development phase. No source, configuration or dataset content was changed by the rename; the read-only functional checks in §0 were re-run successfully.

Re-verification commands (read-only):

```powershell
Set-Location "<repository-root>"
Test-Path ".\src\configurable_simulator.py"
Test-Path ".\docs\development\CODEBASE_ANALYSIS.md"
(Get-ChildItem -Recurse -File -Force | Where-Object { $_.FullName -notmatch '\\\.venv\\|\\__pycache__\\' }).Count
```

---

*End of report.*
