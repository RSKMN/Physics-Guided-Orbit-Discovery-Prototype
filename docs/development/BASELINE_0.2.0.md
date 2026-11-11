# Baseline 0.2.0 — Physics-Guided Orbit Discovery Prototype

**Baseline version:** 0.2.0  
**Baseline date:** 2026-11-11  
**Repository:** `physics-guided-orbit-discovery-prototype`  
**Status:** documented prototype baseline; Git repository initialised on `main`, with no commit created during baseline preparation.

This record captures the state of the repository before the first Git publication. It is intended to let a future contributor answer: what was present, what was verified, what was not verified, and how the prototype was executed.

## 1. Environment

| Item | Verified value |
|---|---|
| Operating system | Windows 11 |
| Shell | PowerShell |
| Python | 3.13.9 |
| Virtual environment | Local `.venv/` (Git-ignored) |
| pip | 26.2.2 |
| REBOUND | 5.2.2 |
| NumPy | 2.5.4 |
| Pandas | 3.1.0 |
| Matplotlib | 3.11.2 |
| astroquery | 0.4.11 installed, but **not declared** in either requirements file |
| pytest | **Not installed** |

Verified checks:

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -c "import rebound, numpy, pandas, matplotlib; print(rebound.__version__, numpy.__version__, pandas.__version__, matplotlib.__version__)"
```

No fresh-environment installation was performed or verified during baseline preparation.

## 2. Source inventory

`src/` contains 12 Python files. None were modified during baseline preparation.

| File | Role | Status |
|---|---|---|
| `src/configurable_simulator.py` | Production Component 1: config load, REBOUND/IAS15 build, trajectory/metadata output, plots | Active |
| `src/trajectory_loader.py` | Modern trajectory schema and time/column validation | Active |
| `src/observation_generator.py` | Component 2 orchestrator | Active |
| `src/observation_schedule.py` | Fixed-cadence scheduling and linear interpolation | Active |
| `src/observer_model.py` | Idealized circular observer and relative positions | Active |
| `src/coordinate_converter.py` | Ecliptic-to-equatorial rotation and RA/Dec | Active |
| `src/measurement_noise.py` | Seeded independent Gaussian angular noise | Active |
| `src/compare_observation_datasets.py` | Three-dataset comparison plots and summary | Analysis |
| `src/horizons_loader.py` | JPL Horizons state loader | Legacy/network |
| `src/nbody_simulator.py` | Legacy synthetic N-body demo | Legacy |
| `src/nbody_realistic.py` | Legacy Eros/Horizons simulation | Legacy/network |
| `src/main.py` | Legacy two-body baseline | Legacy |

## 3. Configuration inventory

`configs/` contains six JSON files. Their SHA-256 hashes were computed from the baseline files and are recorded here for reproducibility.

| Configuration | SHA-256 |
|---|---|
| `configs/synthetic_asteroid.json` | `dc02b2473a778d3fd755f4297c77aacb8f0acf4fc8be00ac522d01e3fad59fca` |
| `configs/synthetic_asteroid_eccentric.json` | `7f2c9df645c544d48a0e4af2cc70343bcdead6ed6b0ef0ae3e5e96a522a68279` |
| `configs/synthetic_asteroid_inclined.json` | `10301602d4f437f356852975a61559d5e50186bbb69cdec07b37bdeeafff8754` |
| `configs/synthetic_observations.json` | `c03a3bbf14921a7cbd9c117b874ed21ab46d45752cf06d5f08ce9a867d1b719d` |
| `configs/synthetic_observations_eccentric.json` | `f07361ad4e5402273176854a68eaa909421486fd4100dfb8e6f25f0c14e8ae47` |
| `configs/synthetic_observations_inclined.json` | `d2b4c233639aaebcfb2f847331e46c0a6894a61fc668afe66f82806ee03b472c` |

The three simulation configurations use a 5-year duration, 1.82625-day output interval, IAS15 with `epsilon = 1e-12`, and the Sun, Mercury, Venus, Earth and Jupiter. The three observation configurations use a 7-day cadence, 0–1826.25 days, an idealized 1 AU/1-year observer, 0.5″ Gaussian noise and seed 42.

## 4. Available datasets

### Modern reference data

| Dataset | Rows | Notes |
|---|---:|---|
| `data/runs/synthetic_asteroid/trajectory.csv` | 1001 | Standard: `a = 2.5 AU`, `e = 0.2`, `i = 0°` |
| `data/runs/synthetic_asteroid_eccentric/trajectory.csv` | 1001 | Eccentric: `e = 0.5` |
| `data/runs/synthetic_asteroid_inclined/trajectory.csv` | 1001 | Inclined: `e = 0.3`, `i = 10°` |
| `data/observations/synthetic_asteroid_observations/observations.csv` | 262 | Standard observation set |
| `data/observations/synthetic_asteroid_eccentric_observations/observations.csv` | 262 | Eccentric observation set |
| `data/observations/synthetic_asteroid_inclined_observations/observations.csv` | 262 | Inclined observation set |

Observation columns are `time_years`, `time_days`, `ra_deg`, `dec_deg`, `sigma_ra_cosdec_arcsec`, `sigma_dec_arcsec`, `true_ra_deg` and `true_dec_deg`.

### Legacy and validation data

| Dataset | Rows / files | Notes |
|---|---:|---|
| `data/trajectory_two_body.csv` | 1000 | Legacy schema |
| `data/trajectory_nbody_synthetic.csv` | 1000 | Legacy schema |
| `data/trajectory_nbody_eros.csv` | 1000 | Legacy Eros/Horizons run |
| `data/eros_diagnostics.csv` | 21 | Eros diagnostics |
| `data/eros_horizons_validation.csv` | 6 | Five-planet validation |
| `data/eros_horizons_8planets_validation.csv` | 6 | Eight-planet validation |
| `data/repeatability/run_a|run_b/` | 6 files | Repeatability runs, 1001 rows each |
| `data/tolerance_tests/eps_1e9|1e12|1e13/` | 9 files + summary | Tolerance runs, 1001 rows each |
| `data/tolerance_tests/tolerance_summary.csv` | 3 | Tolerance summary |
| `results/component-2/comparison_summary.csv` | 3 | Cross-scenario summary |
| `results/component-2/figures/` | 10 | Five PNG/PDF figure pairs (Git-ignored) |
| `plots/` | 5 | Legacy figures (Git-ignored) |

The complete classification and Git policy are in `docs/development/DATA_VERSIONING_POLICY.md`.

## 5. Validation status

### Executed and passed

The following read-only scripts were executed against the renamed repository and exited with status 0:

| Command | Result |
|---|---|
| `tests\test_trajectory_loader.py` | Exit 0 |
| `tests\test_observation_schedule.py` | Exit 0 |
| `tests\test_observer_model.py` | Exit 0 |
| `tests\test_coordinate_converter.py` | Exit 0 |
| `tests\test_measurement_noise.py` | Exit 0; reproducibility PASSED |
| `tests\test_observation_output.py` | Exit 0; dataset checks passed |
| `tests\test_all_observation_outputs.py` | Exit 0; three datasets validated |
| `tests\validate_ground_truth.py` | Exit 0 |
| `tests\check_configurable_runs.py` | Exit 0; scenario sensitivity PASS |
| `tests\validate_baseline.py` | Exit 0; all baseline checks passed |

The captured validation output reports:

- required trajectory columns, finite values, timestamps and time consistency: PASS;
- perihelion/aphelion geometry: 2.0000 AU / 3.0000 AU: PASS;
- Kepler period: 3.952847 years theoretical vs 3.953000 years measured; relative error 0.0039%;
- IAS15 tolerance comparison at the current display precision: PASS.

### Inspected but not executed

These scripts regenerate datasets or require network access and were **not** run during baseline preparation:

- `tests/test_component1_integration.py`
- `tests/test_repeatability.py`
- `tests/test_tolerance_sensitivity.py`
- `tests/compare_trajectories.py`
- `tests/test_horizons_loader.py`
- `tests/check_horizons_epoch.py`
- `tests/validate_eros_horizons.py`
- `tests/validate_eros_8planets.py`
- `tests/diagnose_eros_horizons.py`

Their existing artefacts were inspected. The baseline does not claim they passed in this run.

### Test runner

`python -m pytest --version` fails with `No module named pytest`. The current suite is script-based and not a pytest/CI suite.

## 6. Current execution commands

Run from the repository root.

### Component 1

```powershell
.\.venv\Scripts\python.exe src\configurable_simulator.py configs\synthetic_asteroid.json
```

The positional configuration is verified by `--help`. The full command was not executed because it would regenerate the existing reference run.

### Component 2

```powershell
.\.venv\Scripts\python.exe -m src.observation_generator --config configs\synthetic_observations.json
```

The module form is required. Direct `python src\observation_generator.py` currently fails with `ModuleNotFoundError`. The full command was not executed because it would regenerate the existing observation dataset.

### Validation

```powershell
.\.venv\Scripts\python.exe tests\validate_baseline.py
.\.venv\Scripts\python.exe tests\validate_ground_truth.py
.\.venv\Scripts\python.exe tests\test_all_observation_outputs.py
```

Additional read-only validation commands are listed in `README.md`.

## 7. Scientific limitations

- Frame: heliocentric ecliptic, Sun-relative.
- Units: AU, AU/year, days/years, degrees and arcseconds.
- Time: elapsed simulation time; no absolute `epoch_jd_tdb`.
- Year length: 365.25 days.
- Modern dynamics: Sun, Mercury, Venus, Earth and Jupiter; massless asteroid; simplified planetary initial conditions.
- Observer: idealized circular 1 AU/1-year orbit in the ecliptic plane.
- Observations: fixed 7-day cadence, 0.5″ independent Gaussian errors, seed 42.
- Interpolation: linear; measured difference from cubic Hermite is approximately 0.223″ median and 1.731″ maximum.
- Missing physics: light-time, aberration, topocentric parallax, precession/nutation and relativistic deflection.
- Observability: no elongation/visibility filtering; about 25.6% of epochs are below 30° elongation.
- Truth: `true_ra_deg`/`true_dec_deg` are in the same CSV as the noisy measurements.
- No covariance/correlated noise model.
- No orbit estimation, candidate orbits, uncertainty quantification, active selection or schedule evaluation.
- No real-world astrometric accuracy claim; the Eros/Horizons work is a separate consistency/sensitivity exercise.

## 8. Reproducibility information

- Configuration hashes are recorded in §3.
- The three observation configs use the same `random_seed: 42`.
- The dependency lock covers the base simulation/analysis stack but omits `astroquery` and `pytest`.
- `requirements-lock.txt` is UTF-16 LE with a BOM, so Git classifies it as binary. Its content was inspected; the encoding was not changed because dependency files were outside this task's modification scope.
- Current synthetic runs have no calendar epoch and no `schema_version`.
- Output filenames and locations are fixed by the configs; rerunning overwrites the existing run/observation directories.
- The Git baseline has no commit yet. No push has been performed. The recommended first commit message is prepared for review; it is not stored as a release artefact in this file.
- Generated figures are excluded from Git but remain reproducible from tracked source, configs and tables.

## 9. Related documents

- `README.md` — user-facing overview and verified commands.
- `CHANGELOG.md` — 0.2.0 baseline entry.
- `docs/development/CODEBASE_ANALYSIS.md` — full technical analysis.
- `docs/development/REFACTORING_PLAN.md` — proposed next-stage plan.
- `docs/development/DATA_VERSIONING_POLICY.md` — data and Git policy.
