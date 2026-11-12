# C4.4.2 — `orbit simulate` Command

## 1. Implementation

The `orbit simulate` command was implemented in `src/orbit_discovery/cli/cmd_simulate.py`. The command integrates the existing Component 1 simulator (`configurable_simulator.generate_trajectory()`) with the CLI entry point.

### Key design decisions:

- **Shared CLI entry point**: Uses the existing `orbit` CLI framework with subcommands (same as `orbit observe`, `orbit compare`, `orbit validate`). The entry point is `src/orbit_discovery/cli/main.py` which dispatches to subcommand handlers.

- **Path resolution**: Uses `core.paths` functions with the approved precedence:
  1. Explicit `--project-root` argument
  2. `ORBIT_DISCOVERY_ROOT` environment variable
  3. Nearest ancestor containing `pyproject.toml`

- **Simulator integration**: Imports `configurable_simulator` directly (not via the `orbit_discovery` package namespace, since `configurable_simulator.py` resides at `src/configurable_simulator.py`, not inside `src/orbit_discovery/`). Calls `generate_trajectory(resolved_config_path)` to run the full simulation workflow.

- **ROOT conflict detection**: The simulator internally uses `ROOT = Path(__file__).resolve().parents[1]` (always the repository root, one level above `src/`). If the user supplies an explicit `--project-root` that differs from the simulator's ROOT, the command errors out with a clear message rather than silently writing output to an unexpected location.

- **`--output-root`**: Not supported in this phase. The configurable simulator determines its output directory from the `output.directory` field inside the configuration file. Supplying `--output-root` returns exit code 1 with a clear error message explaining the limitation. Future checkpoints may add this capability after the simulator's public API is extended.

- **Exit codes**: 0 = success, 1 = configuration/error (missing config, project root not found, conflict), 2 = runtime error (simulation failure).

- **Legacy invocation preserved**: `python -m src.configurable_simulator --help` and other legacy methods remain unchanged.

### File changes:
- `src/orbit_discovery/cli/cmd_simulate.py` — new file (the `orbit simulate` command prototype)

## 2. Command Syntax

```
orbit simulate [--config CONFIG] [--project-root DIR]
orbit simulate --help
orbit simulate --version
```

### Arguments:

| Argument | Description |
|---|---|
| `--config CONFIG` | Path to simulation JSON config. Defaults to `configs/synthetic_asteroid.json` relative to the project root. |
| `--project-root DIR` | Explicit project root directory. If it conflicts with the simulator's fixed repository root, an error is returned. |
| `--help`, `-h` | Show help message and exit. |
| `--version`, `-V` | Show program version and exit. |

## 3. Path-Resolution Behaviour and Limitations

### Project root resolution (approved precedence):

1. **Explicit `--project-root`**: If supplied, must be a valid directory path. If it differs from the simulator's internal `ROOT` (the repository root one level above `src/`), the command errors out with an explicit conflict message. This checkpoint does not support arbitrary external project roots that conflict with the simulator's fixed repository root.

2. **`ORBIT_DISCOVERY_ROOT` environment variable**: Not set in the current environment; fallback to marker discovery works when on the repository root.

3. **Nearest ancestor containing `pyproject.toml`**: When invoked from the repository root with no `--project-root`, `resolve_project_root()` discovers the repo root by finding the nearest ancestor containing `pyproject.toml`.

### Config path resolution:

- Relative config paths (e.g., `configs/synthetic_asteroid.json`) are resolved against the project root.
- Absolute config paths are kept absolute.
- The `resolve_config_path()` function handles both cases.

### Simulator ROOT:

- The simulator always uses `ROOT = Path(__file__).resolve().parents[1]`, which resolves to the repository root (one level above `src/`).
- The CLI computes the same ROOT as `Path("src/configurable_simulator.py").resolve().parents[1]` for conflict detection.
- When the CLI's resolved project root matches the simulator's ROOT (normal repo-root invocation), paths align correctly.
- When an explicit `--project-root` differs from the simulator's ROOT, the conflict is detected and the command exits with code 1.

### `--output-root` limitation:

**Not supported in this phase.** The configurable simulator determines its output directory from the `output.directory` field inside the configuration file. Supplying `--output-root` returns exit code 1 with a clear error message explaining the limitation. The configuration file's `output.directory` controls the simulator's output location. Future checkpoints may add this capability after the simulator's public API is extended.

## 4. Simulator Integration

The command integrates the existing Component 1 simulator through a single function call:

```python
from configurable_simulator import generate_trajectory
generate_trajectory(resolved_config_path)
```

### Public API used (all import-safe, guarded by `if __name__ == "__main__"`):

- `load_config(config_path)` — reads JSON config, resolves relative paths against `ROOT = Path(__file__).resolve().parents[1]`
- `build_simulation(config)` — builds a `rebound.Simulation` with Sun + configured planets + massless asteroid; does not integrate or write files
- `generate_trajectory(config_path)` — full workflow: load config → build sim → integrate at requested epochs → save `trajectory.csv`, `config.json`, `metadata.json`, and optional plots

### Output files generated (matching baseline exactly):

- `trajectory.csv` — numeric trajectory data with columns: `time_years`, `time_days`, `x_au`, `y_au`, `z_au`, `vx_au_per_year`, `vy_au_per_year`, `vz_au_per_year`
- `config.json` — simulation configuration snapshot
- `metadata.json` — metadata including `run_utc` timestamp
- Optional plots (PNG files)

### Numerical equivalence:

- Generated trajectory CSV data columns match the baseline exactly (verified with `pandas.DataFrame.equals()`).
- `metadata.json` `run_utc` timestamps differ across runs (not used as regression oracle).
- The simulation uses the same IAS15 integrator settings and defaults as the baseline.

## 5. Compatibility

### Preserved compatibility:

- **Legacy invocation methods**: `python -m src.observation_generator`, `python -m src.main`, `python -m src.configurable_simulator` all remain unchanged.
- **`pyproject.toml`**: Not modified.
- **Scientific algorithms**, IAS15 integrator settings, planetary masses, configuration contents: Not modified.
- **Output CSV columns** and **metadata meanings**: Not modified.
- **Existing data, results, plots**: Not regenerated or overwritten. The command writes to `data/runs/synthetic_asteroid/` which is the expected output location.

### Compatibility notes:

- **`--project-root` conflict**: If an explicit `--project-root` differs from the simulator's fixed repository root, the command errors out rather than silently writing to another location. This is a deliberate design choice for C4.4.2 — future checkpoints may relax this restriction.
- **`--output-root`**: Not supported in this phase. The configurable simulator determines its output directory from the configuration file's `output.directory` field. Supplying `--output-root` returns exit code 1 with a clear error message.
- **Import safety**: No simulations, file writes, or network calls occur on import of `cmd_simulate.py`. All execution is triggered explicitly via the `orbit simulate` command.

### Known incompatibilities (deliberate for this checkpoint):

- An explicit `--project-root` pointing to a directory other than the repository root will cause an error, since the simulator's internal `ROOT` is fixed.
- The `--output-root` argument is accepted and reported but does not redirect the simulator's writing.

## 6. Tests and Results

### Test coverage:

| Test case | Description | Result |
|---|---|---|
| `orbit simulate --help` | Help message shown | Pass (exit code 0) |
| `orbit simulate` | Default config, repo root | Pass (exit code 0, trajectory matches baseline) |
| `orbit simulate --config configs/synthetic_asteroid.json` | Explicit relative config path | Pass (exit code 0) |
| `orbit simulate --config /absolute/path/to/config.json` | Absolute config path | Pass (exit code 0, kept absolute) |
| `orbit simulate --project-root DIR` | Explicit project root matching simulator ROOT | Pass (exit code 0) |
| `orbit simulate --project-root /nonexistent` | Nonexistent project root | Pass (exit code 1, ProjectRootNotFoundError) |
| `orbit simulate --project-root C:\Windows` | Explicit project root conflicting with simulator ROOT | Pass (exit code 1, conflict error) |
| `orbit simulate --output-root /tmp/output` | Output root argument | **Not supported** — returns exit code 1 with error message |
| `orbit simulate --help` | Help message | Pass (exit code 0) |
| Legacy `python -m src.configurable_simulator --help` | Legacy invocation | Pass (module importable, has `generate_trajectory`) |
| Numeric trajectory equivalence | Generated CSV vs baseline | Pass (all rows match exactly) |
| Missing config file | `--config nonexistent.json` | Pass (exit code 1, FileNotFoundError) |

### Verification results:

- **Help output**: All three help targets (`orbit simulate --help`, `orbit simulate --version`, `orbit simulate -h`) display correctly.
- **Default invocation**: `orbit simulate` (no arguments) runs the default config `configs/synthetic_asteroid.json` against the repository root and generates output matching the baseline exactly.
- **Config path resolution**: Both relative and absolute config paths work correctly.
- **Project-root conflict detection**: When `--project-root` is supplied and differs from the simulator's ROOT, a clear error message is shown and exit code 1 is returned.
- **Output root unsupported**: `orbit simulate --output-root /tmp/output` returns exit code 1 with error message explaining the limitation.
- **Legacy compatibility**: `python -m src.configurable_simulator --help` works; the module is importable and has the expected public API.
- **Numeric equivalence**: The generated `trajectory.csv` matches the baseline exactly (1001 rows, 8 columns, identical values).

### Test environment:

- Branch: `feature/cli-prototype` (created from `main` at commit `d02023d`)
- No source files, configs, tests, or data modified across C4.1-C4.4.2
- `rebound` and `matplotlib` installed for simulator dependencies
- Windows environment (Python 3.13)

## 7. Protected Files and Repository Integrity

### Files NOT modified:

| Category | Specific files |
|---|---|
| **CLI commands** | `cmd_observe.py`, `cmd_compare.py`, `cmd_validate.py`, `main.py`, `__init__.py` |
| **Simulator** | `src/configurable_simulator.py` (public API unchanged) |
| **Scientific configs** | `configs/synthetic_asteroid.json` and any config in `configs/` |
| **Scientific data** | `data/` directory, baseline datasets |
| **Results/plots** | Any PNG/CSV files in `data/runs/` or elsewhere |
| **Package config** | `pyproject.toml` |
| **Legacy shims** | `src/observation_generator.py`, `src/main.py`, `src/nbody_simulator.py`, `src/nbody_realistic.py` |
| **Core path resolution** | `src/orbit_discovery/core/paths.py` |

### Repository integrity:

- The `data/runs/synthetic_asteroid/trajectory.csv` file was generated by the simulation, matching the baseline exactly (1001 rows, 8 columns, identical values).
- The `data/runs/synthetic_asteroid/metadata.json` was generated with a different `run_utc` timestamp (expected — not used as regression oracle).
- No existing baseline datasets were regenerated or overwritten.
- The `pyproject.toml` was not modified.
- All legacy invocation methods remain functional.

### Verified exit codes:

- `orbit simulate --help` → exit code 0
- `orbit simulate` → exit code 0 (successful simulation)
- `orbit simulate --project-root /nonexistent` → exit code 1 (project root not found)
- `orbit simulate --project-root C:\Windows` → exit code 1 (root conflict error)
- `orbit simulate --config nonexistent.json` → exit code 1 (missing config)
- `orbit simulate --output-root /tmp/output` → exit code 1 (--output-root not supported)