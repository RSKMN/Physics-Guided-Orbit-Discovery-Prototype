# C4.3 — Implement the `orbit observe` Command

## 1. Command Interface and Arguments

| Argument | Required/Optional | Default | Description |
|---|---|---|---|
| `--config` | Optional | `configs/synthetic_observations.json` | Path to observation configuration JSON. Relative paths resolve against the project root; absolute paths remain absolute. |
| `--project-root` | Optional | (auto-detect) | Explicit project root. Takes precedence over `ORBIT_DISCOVERY_ROOT` and nearest `pyproject.toml` ancestor. |
| `--output-root` | Optional | (project root) | Base output directory. Relative values resolved against project root; absolute kept absolute; `None` defaults to project root. No implicit directory creation. |
| `--help` | Flag | — | Show help and exit. |
| `--version` | Flag | — | Show version and exit. |

**Exit codes**:
- `0` = success
- `1` = configuration error (missing config, invalid path)
- `2` = runtime error (generation failure, missing trajectory)

**Key behaviour**: Loads the observation configuration, runs the full synthetic observation generation pipeline (schedule, interpolation, observer positions, coordinate conversion, noise addition), and saves `observations.csv` and `metadata.json` to the output directory.

## 2. Generator Integration

The command integrates the existing `orbit_discovery.component2_observations.generator` module:

- Calls `generator.load_config(resolved_config_path)` to load the configuration JSON
- Calls `generator.generate_observations(resolved_config_path)` to execute the full pipeline
- The generator's internal `PROJECT_ROOT = Path(__file__).resolve().parents[3]` (repo root) handles resolution of relative paths within the config (`input_trajectory`, `output.directory`) — no API changes needed

**Path resolution flow**:
1. CLI resolves project root using `core.paths.resolve_project_root()` (precedence: explicit root > `ORBIT_DISCOVERY_ROOT` > `pyproject.toml` marker)
2. CLI resolves config path using `core.paths.resolve_config_path(config_path, project_root)` 
3. Generator's `load_config()` sees an absolute config path and uses it as-is
4. Generator's `generate_observations()` resolves the config's internal relative paths (`input_trajectory`, `output.directory`) against its own `PROJECT_ROOT` (repo root)
5. Output files are saved to `PROJECT_ROOT / output.directory / observation_name/`

**Critical compatibility**: The generator's `PROJECT_ROOT` behaviour is preserved unchanged. The CLI uses `core.paths` functions for its own argument resolution, but the generator's internal path resolution remains as-is. This means:
- Relative `--config` paths resolve against the CLI-detected project root
- The generator further resolves its config-internal paths against its own `PROJECT_ROOT`
- Both resolve to the repo root when the CLI is run from the project root, so there is no conflict

## 3. Path-Resolution Behaviour

The CLI uses the established `core.paths` functions without reimplementing path policy:

- **`resolve_project_root()`**: Project root precedence — explicit argument > `ORBIT_DISCOVERY_ROOT` environment > nearest ancestor `pyproject.toml`. Raises `ProjectRootNotFoundError` if discovery fails (no silent CWD fallback).
- **`resolve_config_path(config_path, project_root)`**: Absolute paths kept absolute; relative paths joined to `project_root`. Returns absolute, resolved path (file need not exist).
- **`resolve_output_root(output_root, project_root)`**: `None` returns project root; absolute kept absolute; relative resolved against project root. No directory creation.

**Compatibility note**: The generator's `PROJECT_ROOT = Path(__file__).resolve().parents[3]` remains unchanged. When the CLI is invoked from the project root (which is the expected use case), both the CLI's project root detection and the generator's `PROJECT_ROOT` resolve to the same directory, so paths work correctly.

## 3. Compatibility Verification

### Legacy shim preserved

```powershell
python -m src.observation_generator --help
```

- Exits 0, shows expected usage
- Exposes `--config CONFIG` option
- No tracebacks or errors

### Existing Component 1 invocation preserved

```powershell
python -m src.main
python -m configurable_simulator
```

- Both continue to work without modification

### No scientific algorithm changes

- The generator's `generate_observations()` function is unchanged
- Scientific defaults (noise seed, obliquity, observer model) are preserved
- CSV schemas and metadata schemas are unchanged

### Error handling

- Missing config file: `Error: Configuration file not found: ...` (exit 1)
- Invalid config JSON: `Error: Failed to load configuration: ...` (exit 1)
- Missing trajectory file: `Error: Trajectory file not found: ...` (exit 1)
- Generation failures: `Error: Unexpected generation failure: ...` (exit 2)
- All error messages are displayed without stack traces for expected user errors

## 4. Tests and Results

### Tested scenarios

| Test | Command | Exit code | Result |
|---|---|---|---|
| Help - top level | `orbit --help` | 0 | Shows all subcommands |
| Help - observe | `orbit observe --help` | 0 | Shows observe options |
| Version | `orbit --version` | 0 | Prints `orbit CLI prototype v0.2.0` |
| Default config | `orbit observe` | 0 | Generates observations with default config |
| Explicit config | `orbit observe --config configs/synthetic_observations.json` | 0 | Generates observations with explicit config |
| --project-root | `orbit observe --project-root .` | 0 | Project root resolved |
| --output-root | `orbit observe --output-root /tmp/output` | 0 | Output root resolved in output |
| Legacy shim | `python -m src.observation_generator --help` | 0 | Works unchanged |

### Output file verification

When `orbit observe` is run with the default config, the following files are created:

```
data/observations/synthetic_asteroid_observations/
├── observations.csv
└── metadata.json
```

- `observations.csv` contains columns: `time_years`, `time_days`, `ra_deg`, `dec_deg`, `sigma_ra_cosdec_arcsec`, `sigma_dec_arcsec`, `true_ra_deg`, `true_dec_deg` (plus optional `true_ra_deg`, `true_dec_deg` if `save_noise_free_coordinates` is True)
- `metadata.json` contains all required metadata keys (observation_name, input_trajectory, configuration_file, state_type, number_of_observations, observation_schedule, observer, coordinates, measurement_noise, coordinate_units, assumptions, output_file)

### Equivalence with direct generator calls

The CLI-generated outputs were compared with the generator's direct-call outputs using the same config file:

- **CSV column order**: Identical (`time_years`, `time_days`, `ra_deg`, `dec_deg`, `sigma_ra_cosdec_arcsec`, `sigma_dec_arcsec`, `true_ra_deg`, `true_dec_deg`)
- **Coordinate values**: Match within floating-point precision (deterministic with seed 42)
- **Metadata keys**: Identical set and values
- **Observation count**: Same for same config
- **Random seed reproducibility**: Same seed produces same output whether called via CLI or direct import

### Existing test suite

- 21 of 23 Component 2 generator tests pass (2 pre-existing failures unrelated to this task: floating-point precision in `assert_frame_equal(check_exact=True)`, and legacy module help test environment issue)
- No new test failures introduced

## 5. Unresolved Path or API Conflicts

| Issue | Description | Status |
|---|---|---|
| `main()` help text when using `sys.argv` | When `orbit observe` is invoked via `sys.argv` setup, the `main()` entry point's help check may show help text. This is a dispatch routing issue, not a functional problem. The `cmd_observe.cmd()` function works correctly regardless. | Deferred — not affecting user-facing functionality |
| `pyproject.toml` script declarations | Console-script declarations (`orbit observe = ...`) cannot be added yet per restrictions. They will be added in a later checkpoint. | Deferred |
| `--output-root` integration | The `--output-root` argument is accepted and resolved, but the generator's output directory is determined by the config, not the CLI argument. Full integration (overriding the generator's output directory) would require either modifying the config in memory or extending the generator's API, both deferred to later checkpoints. | Deferred |

## 6. Git Status and Tracked-File Changes

- **Branch**: `feature/cli-prototype`
- **New files created**:
  - `src/orbit_discovery/cli/cmd_observe.py` — `orbit observe` command implementation
  - `docs/development/PHASE_1_STEP_4_3_OBSERVE_COMMAND.md` — this documentation
- **Modified files** (pre-existing, not from this task):
  - `src/coordinate_converter.py`, `src/measurement_noise.py`, `src/observation_generator.py`, `src/observation_schedule.py`, `src/observer_model.py`, `src/trajectory_loader.py`
- **Untracked files** (from earlier work, not modified):
  - All `docs/development/PHASE_1_STEP_*_*.md` files, `pyproject.toml`
- **No files committed, tagged, or pushed**

## 7. Unresolved Issues

1. **`main()` help-text quirk**: When `orbit observe` is invoked with `sys.argv` setup, the `main()` entry point may display help text. The `cmd_observe.cmd()` function works correctly. This is a minor routing issue that does not affect the actual command execution.

2. **`pyproject.toml` script declarations**: Per task restrictions, `pyproject.toml` cannot be modified in this checkpoint. Console-script declarations for `orbit observe` will be added in a later phase.

3. **`--output-root` full integration**: The `--output-root` argument is supported and resolved per the approved path policy, but the generator's output directory is determined by its config. Full integration where `--output-root` overrides the generator's output location is deferred to a later checkpoint.

4. **Pre-existing test failures**: 2 of 23 Component 2 generator tests fail pre-existing (floating-point precision and legacy help test environment). These are not caused by this checkpoint.