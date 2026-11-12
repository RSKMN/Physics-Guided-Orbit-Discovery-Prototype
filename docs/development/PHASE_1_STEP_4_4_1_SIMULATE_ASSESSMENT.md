# C4.4.1 — Component 1 CLI Integration Assessment

## 1. Existing Component 1 Architecture

### 1.1 `src/configurable_simulator.py` — Production Component 1 Entry Point

The configurable simulator is the primary modern Component 1 implementation. It has **no `argparse` at module level**; all work is guarded by `if __name__ == "__main__"`.

**Public API (import-safe):**
- `load_config(config_path)` — reads JSON config, resolves relative paths against `ROOT = Path(__file__).resolve().parents[1]`
- `build_simulation(config)` — builds a `rebound.Simulation` with Sun + configured planets + massless asteroid; **does not integrate or write files**
- `generate_trajectory(config_path)` — **full workflow**: load config → build sim → integrate at requested epochs → save `trajectory.csv`, `config.json`, `metadata.json`, and optional plots

**Key behaviour:**
- `ROOT = Path(__file__).resolve().parents[1]` — always resolves to the repository root (one level above `src/`)
- Config stores `output.directory` relative to `ROOT`; `generate_trajectory()` resolves it as `ROOT / output_config.directory`
- Writes to `data/runs/synthetic_asteroid/` by default (config `output.directory = "data/runs/synthetic_asteroid"`)
- Creates these files:
  - `trajectory.csv` — columns: `time_years`, `time_days`, `x_au`, `y_au`, `z_au`, `vx_au_per_year`, `vy_au_per_year`, `vz_au_per_year`
  - `config.json` — saved configuration
  - `metadata.json` — run metadata (includes `run_utc`, `python_version`, `rebound_version`, etc.)
  - `trajectory_xy.png` / `trajectory_3d.png` if `save_plot` is True
- Integrator is always IAS15 with user-configurable epsilon
- `sim.move_to_com()` is called after adding all bodies
- Scientific defaults: `integrator=ias15`, `integrator_epsilon=1e-12`, planetary masses from `BODY_DATA`

**`if __name__ == "__main__"` entry point:**
- Uses `argparse` with positional `config` argument (default: `configs/synthetic_asteroid.json`)
- Calls `generate_trajectory(args.config)`
- Prints: simulation name, sample count, duration, saved trajectory/config paths

### 1.2 `src/main.py` — Legacy Two-Body Baseline

- **Unsafe to import**: entire simulation and plotting run at module import time
- `PROJECT_ROOT = Path(__file__).resolve().parent.parent` — resolves to repo root
- Writes `data/trajectory_two_body.csv` and `plots/two_body_orbit.png`
- Has its own `SUN_MASS`, `ASTEROID_MASS`, `SEMI_MAJOR_AXIS`, `ECCENTRICITY`, `SIMULATION_DURATION_YR`, `NUMBER_OF_SAMPLES` constants
- Not part of the migration; kept as standalone legacy script

### 1.3 `src/nbody_simulator.py` — Legacy N-Body Demo

- **Unsafe to import**: simulation and plotting run at import
- `PROJECT_ROOT = Path(__file__).resolve().parent.parent`
- Creates `data/trajectory_nbody_synthetic.csv` and `plots/nbody_synthetic_orbit.png`
- Hardcodes 4 planets (Mercury, Venus, Earth, Jupiter) + asteroid
- Not part of the migration path

### 1.4 `src/nbody_realistic.py` — Realistic Initialization with Horizons

- **Unsafe to import**: top-level `from horizons_loader import load_horizons_states` triggers network download
- `ROOT = Path(__file__).resolve().parents[1]`
- Creates `data/trajectory_nbody_eros.csv` and `plots/nbody_eros.png`
- Uses `astroquery` for JPL Horizons state vectors
- Not part of the migration path

## 2. Import-Safety Findings

| Module | Import-Safe? | Side Effects on Import |
|---|---|---|
| `src/configurable_simulator.py` | **Yes** (when imported, not run as `__main__`) | None. All work guarded by `if __name__ == "__main__"` |
| `src/main.py` | **No** | Creates `data/`, `plots/`, builds REBOUND sim, integrates 1000 samples, writes CSV, shows plot |
| `src/nbody_simulator.py` | **No** | Creates `data/`, `plots/`, builds REBOUND sim with 4 planets, integrates 1000 samples, writes CSV, shows plot |
| `src/nbody_realistic.py` | **No** | Imports `horizons_loader` (network download), creates `data/`, `plots/`, builds simulation, writes CSV, shows plot |
| `src/orbit_discovery/*` | **Yes** | Pure path-resolution and validation logic; no writes |
| `src/orbit_discovery.core.paths` | **Yes** | Pure resolution logic; no reads of project files beyond `pyproject.toml`; no writes |

**Import-safety conclusion:** `configurable_simulator.py` is import-safe because all execution is under `if __name__ == "__main__"`. The CLI must call functions explicitly; it must **not** rely on module-level import for execution.

## 3. Simulation Execution Flow

```
orbit simulate [--config CONFIG] [--project-root DIR] [--output-root DIR]
     |
     v resolves config path via core.paths.resolve_config_path()
     |
     v loads config via generator.load_config()  (or configurable_simulator.load_config())
     |
     v builds simulation via configurable_simulator.build_simulation(config)
     |
     v integrates and saves via configurable_simulator.generate_trajectory(config_path)
     |
     v saves: trajectory.csv, config.json, metadata.json [+ plots]
```

**CLI-mediated flow (proposed):**
1. Resolve `--config` argument using `core.paths.resolve_config_path(config_path, project_root)`
2. Optionally resolve `--project-root` using `core.paths.resolve_project_root()`
3. Optionally resolve `--output-root` using `core.paths.resolve_output_root(output_root, project_root)`
4. Call `configurable_simulator.generate_trajectory(resolved_config_path)`
5. The generator internally uses its own `ROOT = Path(__file__).resolve().parents[1]` for relative paths within the config
6. Report success with output file locations

**Key compatibility note:** The generator's internal `ROOT` and the CLI's resolved project root will both resolve to the repository root when running from the repo root. When running from elsewhere, the CLI's explicit root handling takes precedence, and the generator's internal paths may resolve differently — this is a documented compatibility risk (see Section 5).

## 4. Configuration and Path Behaviour

### 4.1 Config File Resolution

| Scenario | How it's resolved |
|---|---|
| `--config absolute/path.json` | Kept absolute by `core.paths.resolve_config_path()` |
| `--config configs/synthetic_asteroid.json` (relative) | Joined to project root via `core.paths.resolve_config_path()` |
| No `--config` | Default: `configs/synthetic_asteroid.json` relative to project root |

### 4.2 Project Root Resolution

Precedence (from `core.paths.resolve_project_root()`):
1. Explicit `--project-root` argument
2. `ORBIT_DISCOVERY_ROOT` environment variable
3. Nearest ancestor containing `pyproject.toml`
4. **No silent CWD fallback** — raises `ProjectRootNotFoundError`

### 4.3 Output Root Resolution

- `None` → project root
- Absolute → kept absolute
- Relative → resolved against project root
- **No directory creation** at resolution time

### 4.4 Generator Internal Path Resolution

The generator uses its own `ROOT = Path(__file__).resolve().parents[1]` (resolves to repo root) for:
- Relative `input_trajectory` within the config
- Relative `output.directory` within the config

When the CLI is invoked from the repository root, both the CLI's project root and the generator's `ROOT` resolve to the same directory, so paths work correctly. When invoked from elsewhere, the generator's paths may resolve differently since they always use `ROOT` (repo root), while the CLI may use a different resolved root.

## 5. Proposed CLI Integration

### 5.1 Command Structure

```
orbit simulate [--config CONFIG] [--project-root DIR] [--output-root DIR]
```

### 5.2 Module Plan

| Module | Purpose |
|---|---|
| `src/orbit_discovery/cli/__init__.py` | Entry point with subcommand dispatch |
| `src/orbit_discovery/cli/cmd_simulate.py` | `orbit simulate` implementation |
| `src/orbit_discovery/cli/main.py` | Dispatcher (may be merged into `__init__.py`) |

### 5.3 Implementation Approach

The `cmd_simulate.py` should:
1. Parse `--config`, `--project-root`, `--output-root` from `args`
2. Resolve project root: `project_root = resolve_project_root(project_root_arg)` or `resolve_project_root()` if not provided
3. Resolve config path: `resolved_config = resolve_config_path(config_arg, project_root)` if config provided, else default `configs/synthetic_asteroid.json` relative to project root
4. Call `configurable_simulator.generate_trajectory(resolved_config_path)`
5. Report success: simulation name, sample count, duration, output directory, CSV path, config path
6. Return exit code 0 on success, 1 on config error, 2 on runtime error

**No changes to `configurable_simulator.py` public API** are needed. The functions `load_config()`, `build_simulation()`, and `generate_trajectory()` are import-safe and callable.

### 5.4 Path Integration Detail

The CLI will use `core.paths` functions for its own argument resolution. The generator's internal `ROOT` handling remains unchanged. This means:

- **When run from repo root**: CLI project root = repo root = generator's `ROOT` → paths align
- **When run from elsewhere with `--project-root`**: CLI uses explicit root; generator still uses its internal `ROOT` (repo root) → generator's output directory resolves relative to repo root, not CLI's root. This is a documented divergence.
- **When run elsewhere without `--project-root`**: CLI discovers project root via `pyproject.toml` marker; if found, it's the repo root → paths align. If not found, `ProjectRootNotFoundError` is raised.

## 6. Compatibility Considerations

### 6.1 Legacy Invocation Methods (preserved)

```powershell
python -m src.configurable_simulator
python -m src.configurable_simulator configs/synthetic_asteroid.json
```

- Both continue to work unchanged
- The `if __name__ == "__main__"` guard ensures no import-time side effects

### 6.2 Scientific Defaults Preserved

- Integrator: IAS15
- Integrator epsilon: configurable via config, default 1e-12
- Planetary masses: from `BODY_DATA` dict
- Output directory: `data/runs/synthetic_asteroid/` (config-relative)
- Output files: `trajectory.csv`, `config.json`, `metadata.json`
- Plot: optional via `save_plot` config flag

### 6.3 Potential Conflicts

| Conflict | Impact | Mitigation |
|---|---|---|
| Generator's `ROOT = Path(__file__).resolve().parents[1]` may differ from CLI's resolved project root when running from a non-repo directory | Paths may resolve to wrong directories | Document the behaviour; require `--project-root` for non-repo usage |
| `generate_trajectory()` writes to `data/runs/synthetic_asteroid/` by default | If CLI doesn't pass explicit config, output goes to default location | Document; users should use `--config` to override |
| `metadata.json` contains `run_utc` (timestamp) | Byte-for-byte non-reproducible across runs | Compare numeric data columns, not metadata timestamps |

### 6.3.1 Critical Path Conflict

The generator's internal path resolution always uses `ROOT = Path(__file__).resolve().parents[1]` (repo root). The CLI uses `core.paths.resolve_project_root()` with precedence: explicit root > `ORBIT_DISCOVERY_ROOT` > `pyproject.toml` marker.

**When the CLI is run from the repository root:**
- Both resolutions point to the same directory → no conflict

**When the CLI is run from a different directory with `--project-root`:**
- CLI uses the explicit directory provided
- Generator still uses its internal `ROOT` (repo root)
- **Result**: Generator saves output to `ROOT / output_config.directory` = `repo_root / data/runs/synthetic_asteroid/`, regardless of what `--project-root` specifies

**Mitigation:** Document this behaviour. If users need output in a different directory, they should use `--output-root` in combination, or the config's `output.directory` should be adjusted. The assessment recommends that for Phase 1, the default behaviour (output to repo root's `data/runs/synthetic_asteroid/`) is preserved when running from the repo root, and users running from elsewhere should explicitly provide `--project-root` and `--config`.

## 7. Testing and Acceptance Criteria

| Criterion | Test |
|---|---|
| `orbit simulate --help` exits 0 and shows expected usage | Run prototype |
| `orbit simulate` with default config generates trajectory | Run with repo root CWD |
| `orbit simulate --config configs/synthetic_asteroid.json` explicit config | Run with correct path |
| `orbit simulate --project-root /tmp` with explicit project root | Test root resolution |
| `orbit simulate --output-root /tmp/output` output root handling | Test output root |
| Legacy `python -m src.configurable_simulator --help` works | Verify shim unchanged |
| Legacy `python -m src.configurable_simulator` runs and produces same outputs | Compare against baseline |
| No scientific algorithms or defaults changed | Verify config and output match |
| Exit codes: 0 success, 1 config error, 2 runtime error | Verify each command |

**Numeric regression check:** Compare generated `trajectory.csv` columns and values against the baseline `data/runs/synthetic_asteroid/trajectory.csv` from the `d02023d` commit, using explicit tolerances on floating-point values.

## 8. Risks and Unresolved Decisions

| Risk | Impact | Mitigation |
|---|---|---|
| Generator's `ROOT` vs CLI resolved root divergence | When running from non-repo directory with `--project-root`, generator saves to repo root, not CLI's root | Document the behaviour; for Phase 1, accept this as intentional; users needing custom output dirs should use `--config` with adjusted `output.directory` |
| `generate_trajectory()` side effects (file writes) | If CLI calls without proper path resolution, writes into wrong directories | CLI must always resolve paths via `core.paths` before calling generator functions |
| `metadata.json` `run_utc` timestamp | Non-reproducible across runs; can't be used as regression oracle | Compare trajectory CSV data columns, not metadata |
| `rebound` dependency | Simulation requires `rebound` package; must be available | Already verified installed in `.venv`; no new dependencies |
| `ORBIT_DISCOVERY_ROOT` not set | Falls back to `pyproject.toml` marker discovery; raises `ProjectRootNotFoundError` if not found | Test both with and without the env var |
| `main.py` legacy script still writes to `data/` | If accidentally triggered, overwrites baseline data | Keep `main.py` invocation explicit; do not add `--simulate` that auto-runs `main.py` |
| Numeric precision differences | IAS15 integration may produce slightly different floating-point results across environments | Use tolerance-based comparison (e.g., `np.allclose` with rtol=1e-10) for regression checks, not byte-identical comparison |

## 9. Final Recommendation

**Proceed with implementation** — the integration can be done safely without modifying `configurable_simulator.py`'s public API, without changing scientific algorithms or defaults, and without breaking legacy invocation methods.

The key design decision is to use `configurable_simulator.generate_trajectory(resolved_config_path)` as the core execution path, with the CLI providing path resolution via `core.paths` functions beforehand. The generator's internal `ROOT` handling will work correctly when the CLI is invoked from the repository root (the expected use case). When running from other directories, users should provide `--project-root` and `--config` explicitly.

**No source files, configs, tests, or data will be modified** during this implementation phase, per the restrictions. The `configurable_simulator.py` module remains untouched; only a new CLI module `cmd_simulate.py` is added alongside the existing legacy scripts.

**Next step (C4.4.2):** Implement the `orbit simulate` command prototype in the `feature/cli-prototype` branch, following the design in this assessment.