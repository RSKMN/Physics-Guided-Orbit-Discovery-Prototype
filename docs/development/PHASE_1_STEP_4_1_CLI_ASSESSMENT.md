# C4.1 — CLI Architecture Assessment

## 1. Current Entry-Point Inventory

| Command/Invocation | Source File | Status |
|---|---|---|
| `python -m src.observation_generator` | `src/observation_generator.py` (compatibility shim) | Active; re-exports from `orbit_discovery.component2_observations.generator` |
| `python -m src.coordinate_converter` | `src/coordinate_converter.py` (compatibility shim) | Active; re-exports from `orbit_discovery.component2_observations.frames` |
| `python -m src.observer_model` | `src/observer_model.py` (compatibility shim) | Active; re-exports from `orbit_discovery.component2_observations.observer` |
| `python -m src.trajectory_loader` | `src/trajectory_loader.py` (likely shim or direct) | Needs verification |
| `python -m src.main` | `src/main.py` | Runs Component 1 simulation |
| `python -m configurable_simulator` | `src/configurable_simulator.py` | Runs Component 1 with JSON config; `argparse` in `if __name__ == "__main__"` block |
| `python -m compare_observation_datasets` | `src/compare_observation_datasets.py` | Standalone comparison script |
| `orbit-simulate` (proposed) | — | Not yet implemented |
| `orbit-observe` (proposed) | — | Not yet implemented |
| `orbit-compare` (proposed) | — | Not yet implemented |
| `orbit-validate` (proposed) | — | Not yet implemented |

### `pyproject.toml` console_scripts
No console-script declarations currently exist. The `[tool.setuptools]` section uses `package-dir = {"" = "src"}` and package discovery `include = ["orbit_discovery*"]`.

---

## 2. Proposed CLI Architecture

### 2.1 Shared CLI Entry Point vs Separate Entry Points

**Recommendation**: Use a **shared entry point** (`orbit`) with subcommands (`simulate`, `observe`, `compare`, `validate`).

- **Rationale**:
  - All four commands operate on the same project layout and path policy.
  - Shared entry point reduces duplication of common argument handling (`--config`, `--project-root`, `--output-root`, `--version`).
  - Consistent help/version reporting and error handling.
  - Easier to maintain a single `pyproject.toml` console-script definition.

- **Alternative**: Separate entry points (`orbit-simulate`, `orbit-observe`, `orbit-compare`, `orbit-validate`) if commands have fundamentally different argument profiles or zero-overhead requirements. This is not recommended given the shared path policy and the desire for consistent user experience.

### 2.2 Console-Script Declarations

```toml
[project.scripts]
orbit = "orbit_discovery.cli:main"
orbit-simulate = "orbit_discovery.cli:cmd_simulate"
orbit-observe = "orbit_discovery.cli:cmd_observe"
orbit-compare = "orbit_discovery.cli:cmd_compare"
orbit-validate = "orbit_discovery.cli:cmd_validate"
```

Or, if a single entry point is preferred with a subcommand dispatcher:

```toml
[project.scripts]
orbit = "orbit_discovery.cli:main"
```

### 2.3 Module Separation

| Command | Module | Key Functions/Modules Delegated To |
|---|---|---|
| `orbit-simulate` | `orbit_discovery.cli.cmd_simulate` | `configurable_simulator.build_simulation`, `configurable_simulator.generate_trajectory`, `main.py` simulation logic |
| `orbit-observe` | `orbit_discovery.cli.cmd_observe` | `generator.generate_observations`, `loader.load_trajectory`, `schedule.generate_observation_times`, `observer.calculate_observer_positions`, `frames.calculate_ra_dec`, `noise.add_measurement_noise` |
| `orbit-compare` | `orbit_discovery.cli.cmd_compare` | `compare_observation_datasets.load_datasets`, `compare_observation_datasets.plot_*` |
| `orbit-validate` | `orbit_discovery.cli.cmd_validate` | `validate_ground_truth.validate_trajectory`, `validate_baseline` test logic, `test_observation_output.validate_observation_output` |

---

## 3. Command-by-Command Argument Specification

### 3.1 `orbit-simulate`

| Argument | Required/Optional | Default | Description |
|---|---|---|---|
| `--config` | Optional | `configs/synthetic_asteroid.json` | Path to simulation JSON configuration. Resolved against project root if relative. |
| `--project-root` | Optional | (auto-detect) | Explicit project root. Overrides `ORBIT_DISCOVERY_ROOT` and marker discovery. |
| `--output-root` | Optional | (project root) | Base directory for output. Resolved against project root if relative. No implicit directory creation. |
| `--version` | Flag | — | Show version and exit. |
| `--help` | Flag | — | Show help and exit. |

**Exit codes**: 0 = success, 1 = configuration error, 2 = runtime error (e.g., unsupported body, integration failure).

**Key behaviour**: Load config, build simulation, integrate, save `trajectory.csv`, `config.json`, and optional `trajectory_xy.png` / `trajectory_3d.png` to `output-root/observation_name/`.

**Existing functions that can be called directly**: `configurable_simulator.generate_trajectory(config_path)`, `configurable_simulator.build_simulation(config)`.

**Refactoring needed**: The `configurable_simulator.main()` function uses `argparse` directly and calls `generate_trajectory()`. It should be wrapped into a callable function that accepts parsed args rather than parsing internally. The script currently calls `generate_trajectory(args.config)` at module level when run as `__main__`.

---

### 3.2 `orbit-observe`

| Argument | Required/Optional | Default | Description |
|---|---|---|---|
| `--config` | Optional | `configs/synthetic_observations.json` | Path to observation configuration JSON. Resolved against project root if relative. |
| `--project-root` | Optional | (auto-detect) | Explicit project root. |
| `--output-root` | Optional | (project root) | Base directory for output. Resolved against project root if relative. No implicit directory creation. |
| `--version` | Flag | — | Show version and exit. |
| `--help` | Flag | — | Show help and exit. |

**Exit codes**: 0 = success, 1 = configuration error (missing config, bad values), 2 = runtime error.

**Key behaviour**: Load config, generate observation schedule, interpolate positions, calculate observer positions, convert to equatorial coordinates, add measurement noise, save `observations.csv` and `metadata.json` to `output-root/observation_name/`.

**Existing functions that can be called directly**: `generator.generate_observations(config_path)`, `generator.load_config(config_path)`, `loader.load_trajectory(csv_path)`, `schedule.generate_observation_times(...)`, `observer.calculate_observer_positions(...)`, `frames.calculate_ra_dec(...)`, `noise.add_measurement_noise(...)`.

**Refactoring needed**: The `generator.main()` function currently parses `--config` internally. It should be refactored to accept `config_path` as an explicit argument, or a new `cmd_observe()` wrapper should be created that calls `generator.generate_observations()` after resolving the config path via `core.paths.resolve_config_path`.

---

### 3.3 `orbit-compare`

| Argument | Required/Optional | Default | Description |
|---|---|---|---|
| `--datasets` | Optional | (default datasets from `compare_observation_datasets`) | Comma-separated list of dataset labels to compare. |
| `--config` | Optional | (default from `compare_observation_datasets`) | Path to a configuration file (if needed). |
| `--project-root` | Optional | (auto-detect) | Explicit project root. |
| `--output-root` | Optional | (project root) | Base directory for output figures/summaries. Resolved against project root if relative. No implicit directory creation. |
| `--version` | Flag | — | Show version and exit. |
| `--help` | Flag | — | Show help and exit. |

**Exit codes**: 0 = success, 1 = data error, 2 = runtime error.

**Key behaviour**: Load observation datasets (CSVs + metadata CSVs), generate comparison summary CSV, produce RA-vs-time, Dec-vs-time, sky-track, time-colored sky-track, and noise-distribution plots, save `comparison_summary.csv`.

**Existing scripts**: `tests/compare_trajectories.py` and `src/compare_observation_datasets.py` provide the core logic. The `compare_observation_datasets.main()` function is the natural entry point.

**Refactoring needed**: Minimal. The `compare_observation_datasets.py` script currently uses `PROJECT_ROOT = Path(__file__).resolve().parents[1]` (relative to `src/`) which assumes the script is at `src/compare_observation_datasets.py`. This needs to be updated to accept an explicit project root or use `core.paths.resolve_project_root`. The script also creates `OUTPUT_DIR` and `FIGURE_DIR` with `mkdir(parents=True, exist_ok=True)`, which should respect the `--output-root` argument.

---

### 3.4 `orbit-validate`

| Argument | Required/Optional | Default | Description |
|---|---|---|---|
| `--trajectory` | Optional | (default: `data/trajectory_two_body.csv`) | Path to trajectory CSV to validate. Resolved against project root if relative. |
| `--project-root` | Optional | (auto-detect) | Explicit project root. |
| `--validate-observations` | Flag | `False` | If set, also validate observation CSV + metadata pair. |
| `--version` | Flag | — | Show version and exit. |
| `--help` | Flag | — | Show help and exit. |

**Exit codes**: 0 = all validations pass, 1 = validation failure (missing columns, bad values, etc.), 2 = runtime error.

**Key behaviour**: Validate trajectory CSV columns, timestamps, numerical finiteness, orbital geometry. If `--validate-observations` is set, also validate observation CSV + metadata columns, coordinate ranges, noise statistics, and time consistency.

**Existing scripts**: `tests/validate_baseline.py`, `tests/validate_ground_truth.py`, `tests/test_observation_output.py` provide the core validation logic.

**Refactoring needed**: The validation scripts use `Path(__file__).resolve().parents[1]` to find project root. This needs to be replaced with `core.paths.resolve_project_root()` or an explicit `--project-root` argument. The scripts should not perform silent CWD fallback.

---

## 4. Path-Resolution Design

### 4.1 Integration with `core.paths`

The project already has a well-defined path policy in `src/orbit_discovery/core/paths.py`. The CLI should integrate with these functions:

| Function | Purpose | CLI Usage |
|---|---|---|
| `resolve_project_root(project_root=None, *, search_from=None, env=None, cwd=None)` | Resolve project root using precedence: explicit root > `ORBIT_DISCOVERY_ROOT` > nearest `pyproject.toml` ancestor. | Called at CLI startup to determine project root. |
| `resolve_config_path(config_path, project_root)` | Resolve config path: absolute paths kept absolute; relative paths joined to project root. | Resolve `--config` argument. |
| `resolve_output_root(output_root, project_root)` | Resolve output root: `None` returns project root; absolute kept absolute; relative resolved against project root. No directory creation. | Resolve `--output-root` argument. |

**Precedence policy preservation** (from `core/paths.py` docs):
1. Explicit `project_root` argument takes precedence.
2. Then `ORBIT_DISCOVERY_ROOT` environment variable.
3. Then nearest ancestor containing `pyproject.toml`.
4. **No silent current-working-directory fallback** — raises `ProjectRootNotFoundError` if discovery fails.

### 4.2 Conflicts with Existing Behaviour

| Existing Behaviour | Conflict | Resolution |
|---|---|---|
| `compare_observation_datasets.py` uses `PROJECT_ROOT = Path(__file__).resolve().parents[1]` | Conflict: resolves to parent of `src/`, not the project root marker-based discovery. | Update to use `core.paths.resolve_project_root()`. |
| `validate_baseline.py` and `validate_ground_truth.py` use `ROOT = Path(__file__).resolve().parents[1]` | Same conflict. | Update to use `core.paths.resolve_project_root()`. |
| `generator.py` uses `PROJECT_ROOT = Path(__file__).resolve().parents[3]` (hardcoded 3 levels up from `src/`) | Conflict: brittle, assumes specific layout. | Update to use `core.paths.resolve_project_root()`. The `generator.PROJECT_ROOT` should remain for backward compatibility with tests, but CLI should use the resolver. |
| `main.py` uses `PROJECT_ROOT = Path(__file__).resolve().parent.parent` | Conflict: same hardcoded pattern. | Update to use `core.paths.resolve_project_root()`. |

---

## 5. Compatibility Strategy

### 5.1 Preserving Existing Invocation Methods

| Existing Invocation | Preservation Action |
|---|---|
| `python -m src.observation_generator` | Keep `src/observation_generator.py` as a compatibility shim. It must continue to re-export `main`, `generate_observations`, `load_config`, `PROJECT_ROOT`, `DAYS_PER_YEAR` from `orbit_discovery.component2_observations.generator`. Do not modify. |
| `python -m src.coordinate_converter` | Keep `src/coordinate_converter.py` as a compatibility shim. Do not modify. |
| `python -m src.observer_model` | Keep `src/observer_model.py` as a compatibility shim. Do not modify. |
| `python -m src.main` | Keep `src/main.py` as-is. This runs Component 1 simulation and writes to `data/`. Do not modify. |
| `python -m configurable_simulator` | Keep `src/configurable_simulator.py` as-is. The `if __name__ == "__main__"` block uses argparse. Do not modify. |
| `python -m compare_observation_datasets` | Keep `src/compare_observation_datasets.py` as-is. Do not modify. |

**Critical constraint**: The legacy `src/*.py` paths must remain functional. The compatibility shims re-export from the `orbit_discovery` package. The new CLI entry points (`orbit.*`) must not break these.

### 5.2 Ensuring `python -m src.observation_generator --help` Still Works

The `src/observation_generator.py` shim currently works when `PYTHONPATH` includes `src/` or when the package is installed. The `--help` output is:

```
usage: -c [-h] [--config CONFIG]

Generate synthetic astronomical observations.

options:
  -h, --help       show this help message and exit
  --config CONFIG  Path to observation configuration JSON.
```

This must continue to work. The CLI assessment must not alter this shim.

---

## 6. Import-Safety Findings

| Import Target | Side Effects | Safeguard Needed |
|---|---|---|
| `orbit_discovery.component2_observations.generator.load_config` | Reads JSON file. No simulation, no writes. | Safe to call before CLI entry point. |
| `orbit_discovery.component2_observations.generator.generate_observations` | Reads config, trajectory CSV; writes `observations.csv` and `metadata.json` to output directory. **Side effects: file writes.** | Must not be called without explicit config path and output directory control. CLI must resolve paths via `core.paths.resolve_config_path` and `resolve_output_root` before calling. |
| `orbit_discovery.component2_observations.loader.load_trajectory` | Reads CSV file, validates columns. No writes. | Safe. |
| `orbit_discovery.component2_observations.noise.add_measurement_noise` | Adds Gaussian noise using `numpy.random.default_rng`. seed is configurable. | Safe if seed is controlled. CLI should pass through the config seed. |
| `orbit_discovery.component2_observations.frames.calculate_ra_dec` | Calculates RA/Dec from equatorial positions. No writes. | Safe. |
| `orbit_discovery.component2_observations.schedule.generate_observation_times` | Generates arithmetic observation timestamps. No writes. | Safe. |
| `orbit_discovery.component2_observations.observer.calculate_observer_positions` | Calculates circular observer positions. No writes. | Safe. |
| `orbit_discovery.core.paths.resolve_project_root` | Pure resolution logic. No reads of project files (beyond looking for `pyproject.toml`). No writes. | Safe. |
| `orbit_discovery.core.paths.resolve_config_path` | Pure resolution logic. No reads/writes of config file content. | Safe. |
| `orbit_discovery.core.paths.resolve_output_root` | Pure resolution logic. No writes. | Safe. |
| `orbit_discovery.configurable_simulator.generate_trajectory` | Builds rebound Simulation, integrates, writes CSV, JSON, plots. **Side effects: simulation, file writes.** | Must only be called after explicit path resolution. CLI must not call without `--config` and `--output-root`. |
| `src.main` (Component 1) | Runs rebound simulation, writes `data/trajectory_two_body.csv`, `plots/two_body_orbit.png`. **Side effects: simulation, file writes.** | Must not be triggered inadvertently by CLI. Keep as standalone invocation. |
| `src.configurable_simulator` (when `__main__`) | Same as above. | Keep `if __name__ == "__main__"` guard. |

**Import-safety conclusion**: All component modules are import-safe *if* paths are resolved by the CLI before invoking the core functions. The CLI must use `core.paths.resolve_project_root()`, `resolve_config_path()`, and `resolve_output_root()` to avoid silent CWD fallback and unintended file writes into tracked data.

---

## 7. Required Implementation Sequence

1. **Do not modify any source files, tests, configs, datasets, results, or plots** (per restrictions).
2. **Create the assessment document** `docs/development/PHASE_1_STEP_4_1_CLI_ASSESSMENT.md` (this file).
3. **Add console-script declarations** to `pyproject.toml` (if proceeding to implementation phase; but per restrictions, do not modify `pyproject.toml` in this task).
4. **Develop CLI module prototypes** in a development branch or separate workspace, e.g.:
   - `src/orbit_discovery/cli/cmd_simulate.py`
   - `src/orbit_discovery/cli/cmd_observe.py`
   - `src/orbit_discovery/cli/cmd_compare.py`
   - `src/orbit_discovery/cli/cmd_validate.py`
   - `src/orbit_discovery/cli/main.py` (subcommand dispatcher)
5. **Test each prototype** with `python -m orbit_discovery.cli --help` and subcommand help, ensuring legacy invocations remain intact.
6. **Verify path resolution** using `core.paths.resolve_project_root()`, `resolve_config_path()`, `resolve_output_root()` with various argument combinations.
7. **Confirm that `python -m src.observation_generator --help`** still produces the expected output.
8. **Run existing tests** to ensure no regressions: `python -m pytest tests/` (or unittest runner).
9. **Document any required refactoring** of existing scripts (e.g., updating `PROJECT_ROOT` resolution in `compare_observation_datasets.py`, `validate_baseline.py`, `validate_ground_truth.py`).
10. **Finalize the assessment** and wait for review before proceeding to implementation.

---

## 8. Testing and Acceptance Criteria

| Criterion | Test |
|---|---|
| `python -m src.observation_generator --help` exits 0 and shows expected usage. | Run legacy shim. |
| `orbit-simulate --help`, `orbit-observe --help`, `orbit-compare --help`, `orbit-validate --help` exit 0. | Run new CLI prototypes. |
| Config paths relative to project root are resolved correctly. | Pass `--config configs/synthetic_observations.json` and verify resolution via `core.paths.resolve_config_path`. |
| Absolute config paths remain absolute. | Pass an absolute path and verify it is kept absolute. |
| Output root resolution: relative resolves against project root; absolute kept absolute; `None` defaults to project root. | Test with `--output-root relative_dir`, `--output-root /abs/path`, and `--output-root` omitted. |
| No silent CWD fallback when project root cannot be discovered. | unset `ORBIT_DISCOVERY_ROOT`, cd to a directory without `pyproject.toml`, verify `ProjectRootNotFoundError` is raised. |
| Exit codes: 0 on success, 1 on config/error, 2 on runtime error. | Verify each command's exit code. |
| Scientific algorithms and defaults unchanged. | Compare output of legacy `python -m src.observation_generator` vs new CLI with same config. |
| CSV schemas and column ordering unchanged. | Verify column order in generated `observations.csv` matches expected. |
| Metadata schema and meanings unchanged. | Verify `metadata.json` keys and values match expected. |
| Existing output names and directory structures preserved. | Verify output directory naming matches `observation_name` from config. |
| Random seeds preserved. | Run generation twice with same seed; verify reproducibility. |
| Existing truth columns (`true_ra_deg`, `true_dec_deg`) preserved in output. | Check CSV columns. |

---

## 9. Risks and Unresolved Decisions

| Risk | Impact | Mitigation |
|---|---|---|
| Hardcoded `PROJECT_ROOT = Path(__file__).resolve().parents[3]` in `generator.py` breaks if package layout changes. | The `PROJECT_ROOT` constant used by tests and the legacy shim may point to wrong directory if CLI uses a different resolution. | Keep `generator.PROJECT_ROOT` for test backward compatibility; CLI should use `core.paths.resolve_project_root()` independently. |
| `compare_observation_datasets.py` uses `PROJECT_ROOT = Path(__file__).resolve().parents[1]` (one level up from `src/`). | If CLI calls this script's functions, path resolution may be wrong. | Update CLI to use its own path resolution; or update the script (but per restrictions, cannot modify in this task). |
| `validate_baseline.py` and `validate_ground_truth.py` use `ROOT = Path(__file__).resolve().parents[1]`. | Same as above. | Same mitigation. |
| `main.py` (Component 1) writes to `data/trajectory_two_body.csv` and `plots/two_body_orbit.png` unconditionally. | If CLI inadvertently triggers this (e.g., via misconfigured entry point), existing data could be overwritten. | Keep `main.py` invocation explicit; do not add `--simulate` or similar that auto-runs `main.py`. |
| `configurable_simulator.generate_trajectory()` writes to `data/runs/synthetic_asteroid/` by default. | Same risk. | Ensure CLI always passes explicit `--config` and `--output-root`. |
| `ORBIT_DISCOVERY_ROOT` environment variable not set. | CLI must fall back to marker discovery (`pyproject.toml`). Must test this scenario. | Test with and without the env var. |
| Subcommand dispatch architecture (single entry point vs separate). | Affects `pyproject.toml` `[project.scripts]` design. | Document both options; default to shared entry point with subcommands. |
| Legacy `python -m src.observation_generator` must remain functional. | Constrains refactoring of `generator.main()`. | Do not change the shim; add new CLI modules alongside it. |

---

## 10. Files and Areas That Must Remain Unchanged

**Must not modify**:

| File/Path | Reason |
|---|---|
| `pyproject.toml` | Per restriction; cannot modify. |
| `src/observation_generator.py` | Legacy shim; must remain functional for `python -m src.observation_generator`. |
| `src/coordinate_converter.py` | Legacy shim. |
| `src/observer_model.py` | Legacy shim. |
| `src/main.py` | Component 1 simulation; writing this would change scientific output. |
| `src/configurable_simulator.py` | Component 1 with JSON config; has `if __name__ == "__main__"` guard. |
| `src/compare_observation_datasets.py` | Existing comparison script. |
| `tests/` directory and all test files | Per restriction; must not modify. |
| `configs/` directory and all JSON configs | Per restriction; must not change scientific data. |
| `data/` directory and all CSV/JSON data | Per restriction; must not change. |
| `results/` directory and all outputs | Per restriction; must not change. |
| `src/orbit_discovery/core/paths.py` | Already implements the approved path policy; no changes needed. |
| `src/orbit_discovery/core/constants.py` | Constants; no changes needed. |
| `src/orbit_discovery/__init__.py` | Package docstring; no changes needed. |
| `src/orbit_discovery/component1_simulation/__init__.py` | Skeleton; no changes needed. |
| `src/orbit_discovery/component2_observations/__init__.py` | Skeleton; no changes needed. |
| `src/orbit_discovery/component2_observations/generator.py` | **Do not modify** — the migration has already been done; the file is the source of truth for the observation pipeline. |
| `src/orbit_discovery/component2_observations/loader.py` | Do not modify. |
| `src/orbit_discovery/component2_observations/schedule.py` | Do not modify. |
| `src/orbit_discovery/component2_observations/observer.py` | Do not modify. |
| `src/orbit_discovery/component2_observations/frames.py` | Do not modify. |
| `src/orbit_discovery/component2_observations/noise.py` | Do not modify. |
| `src/orbit_discovery/cli/__init__.py` | Currently just a docstring; can be extended but must not break existing imports. |
| `docs/` directory | Existing docs must not be altered beyond creating the new assessment file. |

**Areas that may be read/inspected but not modified**:

- `src/orbit_discovery/` package structure (read-only in this task).
- `src/orbit_discovery/core/` (read-only; the path resolution policy is already approved).
- Test fixtures and data files (read-only).

---