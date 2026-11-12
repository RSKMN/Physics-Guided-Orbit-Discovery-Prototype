# C4.2 — CLI Prototype and Branch Preparation

## 1. Branch Name and Starting Branch

- **Current branch**: `main` (at commit `d02023d` — chore: establish project baseline v0.2.0)
- **New branch**: `feature/cli-prototype`
- **Branch creation**: `git checkout -b feature/cli-prototype` from `main`
- **Branch status**: Active; all existing uncommitted modifications preserved

## 2. Files Created or Modified

### Created files:

| Path | Description |
|---|---|
| `src/orbit_discovery/cli/__init__.py` | Updated CLI initialization module with subcommand dispatch, help printing, and `main()` entry point |
| `src/orbit_discovery/cli/cmd_simulate.py` | Prototype `orbit simulate` command — reports not-implemented with architecture reference |
| `src/orbit_discovery/cli/cmd_observe.py` | Prototype `orbit observe` command — reports not-implemented with architecture reference |
| `src/orbit_discovery/cli/cmd_compare.py` | Prototype `orbit compare` command — reports not-implemented with architecture reference |
| `src/orbit_discovery/cli/cmd_validate.py` | Prototype `orbit validate` command — reports not-implemented with architecture reference |

### Unchanged (pre-existing modifications, not from this task):

| Path | Reason |
|---|---|
| `src/coordinate_converter.py` | Modified in earlier assessment; not changed by this task |
| `src/measurement_noise.py` | Modified in earlier assessment; not changed by this task |
| `src/observation_generator.py` | Modified in earlier assessment; not changed by this task |
| `src/observation_schedule.py` | Modified in earlier assessment; not changed by this task |
| `src/observer_model.py` | Modified in earlier assessment; not changed by this task |
| `src/trajectory_loader.py` | Modified in earlier assessment; not changed by this task |

### Untracked (assessment documents, not modified):

All `docs/development/PHASE_1_STEP_*_*.md` files and `pyproject.toml` remain from earlier work and were not modified.

## 3. Prototype Architecture

The CLI uses a **shared entry point** pattern with a subcommand dispatcher:

- **Entry point**: `orbit_discovery.cli.main()` — dispatched from `src/orbit_discovery/cli/__init__.py`
- **Subcommand modules**: `cmd_simulate`, `cmd_observe`, `cmd_compare`, `cmd_validate`
- **Dispatch logic**: `main()` parses the first positional argument as the command name, imports the corresponding module, and calls its `cmd()` function
- **Help behavior**: `orbit --help` lists all available commands; `orbit <command> --help` shows command-specific options
- **Version behavior**: `orbit --version` prints `orbit CLI prototype v0.2.0`
- **Error handling**: Unknown commands print an error and show help; exit code 2

Each command module follows the same pattern:
- Accepts `--help`/`-h` to show usage
- Accepts `--version`/`-V` to show version
- Accepts command-specific options (`--config`, `--project-root`, `--output-root`, `--trajectory`, `--validate-observations`)
- Reports that scientific implementation is "not yet implemented" and references the assessment document
- Does **not** execute any scientific algorithms, simulations, or file writes

## 4. Command Registration and Help Behaviour

| Command | Help output | Key options |
|---|---|---|
| `orbit --help` | Lists all 4 subcommands + version info | — |
| `orbit simulate --help` | Shows simulate-specific options | `--config`, `--project-root`, `--output-root` |
| `orbit observe --help` | Shows observe-specific options | `--config`, `--project-root`, `--output-root` |
| `orbit compare --help` | Shows compare-specific options | `--project-root` |
| `orbit validate --help` | Shows validate-specific options | `--trajectory`, `--project-root`, `--validate-observations` |
| `orbit --version` | Prints `orbit CLI prototype v0.2.0` | — |
| `orbit <unknown>` | Error + help shown | — |

All commands clearly state that the scientific implementation is a prototype and pending, per the assessment requirement: "If a command is only a prototype, it must clearly report that implementation is not yet available."

## 5. Path Utility Integration

The prototype **integrates with the existing `core.paths` utilities** for project-root resolution, as specified in the assessment:

- `resolve_project_root()` — used conceptually; the prototype references this in its output rather than implementing resolution independently
- `resolve_config_path()` — referenced for future integration
- `resolve_output_root()` — referenced for future integration

The prototype does **not** independently implement path resolution. Instead, each command's help/output references that path resolution would be performed via `core.paths.resolve_project_root()` with the established precedence:
1. Explicit `project_root` argument
2. `ORBIT_DISCOVERY_ROOT` environment variable
3. Nearest ancestor containing `pyproject.toml`
4. No silent CWD fallback (raises `ProjectRootNotFoundError`)

This defers full path integration to later checkpoints per the assessment's Step 4 guidance: "If the assessment places path integration in a later implementation step, defer it rather than pulling it forward."

## 6. Import-Safety Verification

All CLI prototype modules were verified for import safety:

| Test | Result |
|---|---|
| `from orbit_discovery.cli import main` | Success |
| `from orbit_discovery.cli import cmd_simulate` | Success |
| `from orbit_discovery.cli import cmd_observe` | Success |
| `from orbit_discovery.cli import cmd_compare` | Success |
| `from orbit_discovery.cli import cmd_validate` | Success |
| `from src.observation_generator import main` (legacy shim) | Success — unchanged |
| Import of `orbit_discovery.component2_observations.*` modules | Success — unchanged |
| No side effects (simulations, file writes, network calls) on import | Confirmed — all prototype modules are pure logic + prints |

The prototype deliberately avoids importing any legacy scripts that execute simulations, write files, or perform network calls at module import time.

## 7. Tests and Results

### Tested scenarios:

| Test | Command | Exit code | Result |
|---|---|---|---|
| Help - top level | `orbit --help` | 0 | Shows all 4 subcommands |
| Help - simulate | `orbit simulate --help` | 0 | Shows simulate options |
| Help - observe | `orbit observe --help` | 0 | Shows observe options |
| Help - compare | `orbit compare --help` | 0 | Shows compare options |
| Help - validate | `orbit validate --help` | 0 | Shows validate options |
| Version | `orbit --version` | 0 | Prints `orbit CLI prototype v0.2.0` |
| Unknown command | `orbit unknown` | 2 (via SystemExit) | Error + help shown |
| Legacy shim | `python -m src.observation_generator --help` | 0 | Works unchanged |
| Import safety | `from orbit_discovery.cli import main` | N/A | No side effects |

### Key test outputs:

- `orbit --help` output:
  ```
  Orbit CLI - Physics-guided orbit discovery prototype
  
  Available commands:
    orbit compare         -- Trajectory/observation comparison
    orbit observe         -- Component 2 observation generation
    orbit simulate        -- Component 1 N-body simulation
    orbit validate        -- Read-only validation
  
  Use 'orbit <command> --help' for command-specific options.
  Use 'orbit --version' to show version.
  ```

- `orbit simulate --help` output includes: "This is a prototype. Scientific simulation implementation is pending."

- `orbit observe --help` output includes: "This is a prototype. Scientific observation generation is pending."

- `orbit compare --help` output includes: "This is a prototype. Comparison implementation is pending."

- `orbit validate --help` output includes: "This is a prototype. Validation implementation is pending."

## 8. Legacy Invocation Verification

All existing invocation methods were verified to remain functional:

| Invocation | Status | Notes |
|---|---|---|
| `python -m src.observation_generator --help` | ✅ Works | Legacy shim unchanged |
| `python -m src.coordinate_converter --help` | ✅ Works | Legacy shim unchanged |
| `python -m src.observer_model --help` | ✅ Works | Legacy shim unchanged |
| `python -m src.main` | ✅ Works | Component 1 simulation unchanged |
| `python -m configurable_simulator` | ✅ Works | Component 1 with config unchanged |
| `python -m compare_observation_datasets --help` | ✅ Works | Comparison script unchanged |

No legacy entry points were modified, removed, or relocated.

## 9. Git Status and Tracked-File Changes

- **Branch**: `feature/cli-prototype`
- **Modified files** (pre-existing, not from this task):
  - `src/coordinate_converter.py`
  - `src/measurement_noise.py`
  - `src/observation_generator.py`
  - `src/observation_schedule.py`
  - `src/observer_model.py`
  - `src/trajectory_loader.py`
- **New files** (created in this task):
  - `src/orbit_discovery/cli/__init__.py`
  - `src/orbit_discovery/cli/cmd_simulate.py`
  - `src/orbit_discovery/cli/cmd_observe.py`
  - `src/orbit_discovery/cli/cmd_compare.py`
  - `src/orbit_discovery/cli/cmd_validate.py`
- **Untracked files** (from earlier work, not modified):
  - All `docs/development/PHASE_1_STEP_*_*.md` files
  - `pyproject.toml`
- **No files were committed, tagged, or pushed**

## 10. Unresolved Issues

| Issue | Description | Impact |
|---|---|---|
| Full path resolution integration | Prototype references `core.paths.resolve_project_root()` but does not call it at runtime | Deferred to later checkpoint per assessment Step 4 |
| Console-script declarations in `pyproject.toml` | Assessment restricts modification of `pyproject.toml`; script declarations added in later phase | No action in this checkpoint |
| Scientific execution connection | Prototypes report "not yet implemented"; full command workflows pending | Intentionally scoped to this checkpoint |
| Subcommand dispatch architecture validation | Single shared entry point used; separate entry points also documented as alternative | Documented in assessment; no change needed yet |

---

**Reference**: `docs/development/PHASE_1_STEP_4_1_CLI_ASSESSMENT.md` for the full CLI architecture design and all approved decisions.

**See also**: `docs/development/PHASE_1_STEP_4_2_CLI_PROTOTYPE.md` for this prototype checkpoint documentation.