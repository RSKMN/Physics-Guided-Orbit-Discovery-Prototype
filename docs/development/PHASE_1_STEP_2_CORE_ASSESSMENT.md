# Phase 1 — Step 2.1: Core Paths and Constants Assessment

**Project:** Physics-Guided Orbit Discovery Prototype  
**Version:** 0.2.0  
**Branch:** `main`  
**Baseline commit:** `d02023d9820fd2b1a58731345d5d66384adad120`  
**Assessment date:** 2026-11-11  
**Mode:** read-only assessment; the only file created is this report  
**Status:** assessment complete; C2 has not been implemented

This report assesses which shared path, constant and configuration utilities
genuinely belong in `src/orbit_discovery/core/` before checkpoint C2. It follows
the approved decisions in
`docs/development/PHASE_1_STEP_1_ASSESSMENT.md`, including the architecture
addendum. Where the older `REFACTORING_PLAN.md` conflicts with that addendum, the
addendum is treated as authoritative.

No source module, test, configuration, dependency file, dataset or scientific
output was modified. No directory or package module was created.

---

## Executive summary

The proposed `core` package should **not** be filled with every shared-looking
piece of code. The evidence supports:

1. **`core/paths.py` — justified.**
   Project-root construction and relative path resolution are repeated across
   Component 1, Component 2, the comparison script, legacy scripts and tests.
   The current `Path(__file__).resolve().parents[1]` model cannot support an
   installed package or a non-repository CWD. A small explicit path policy is
   needed before Component code is moved.

2. **`core/constants.py` — justified, but narrowly.**
   `DAYS_PER_YEAR = 365.25` is duplicated as a literal across four source
   modules and many tests. `ARCSEC_TO_DEG = 1/3600` is the unit conversion used
   by the noise module and the inverse used by comparison code. These are
   project-wide unit conventions, not simulation settings.
   `OBLIQUITY_DEG = 23.43928` is an observation/frame model default and should
   remain with the Component 2 frame code, not move into general constants.

3. **`core/config.py` — not justified for C2.**
   There are two `load_config` functions, but they have different return
   contracts, different error handling and different caller needs. No shared
   implementation exists yet, and creating one now would either duplicate the
   differences or silently change behaviour during migration. Config loading
   should be revisited in C4/C5 when both component loaders move.

4. **Existing modules must remain unchanged in C2.**
   C2 should add new core modules and focused tests only. The current entry
   points, imports, output paths, metadata formatting and scientific behaviour
   must remain untouched until their own checkpoints.

The recommended path policy is:

```text
--project-root PATH
    > ORBIT_DISCOVERY_ROOT
    > nearest ancestor of the current directory containing pyproject.toml
    > actionable error for data-reading/writing commands
```

`--help` and `--version` must not require a root. Relative configuration paths
and relative paths inside configuration files resolve against the project root,
preserving the current 0.2.0 behaviour. Absolute paths remain absolute.
`--output-root` affects relative output directories only. Core path functions do
not create directories.

---

## 1. Existing path and constant implementations

### 1.1 Path and project-root construction

| File | Current implementation | Resolution behaviour | Side effects | Notes |
|---|---|---|---|---|
| `src/configurable_simulator.py` | `ROOT = Path(__file__).resolve().parents[1]` at line 14 | Relative config paths resolve as `ROOT / path` in `load_config()` (lines 29–39). Output directories resolve as `ROOT / config["output"]["directory"]` (lines 210–212). | Creates output directories; writes CSV/config/metadata; optionally plots. | Direct script works from any CWD **in a source checkout** because root comes from `__file__`. Installing the module would point `ROOT` into `site-packages`. |
| `src/observation_generator.py` | `PROJECT_ROOT = Path(__file__).resolve().parents[1]` at line 25 | Relative config path resolves against `PROJECT_ROOT` (lines 29–45). `input_trajectory` resolves against `PROJECT_ROOT` (lines 57–60). Output directory resolves against `PROJECT_ROOT` (lines 186–194). | Creates output directory; writes observations and metadata. | Uses `from src.*` imports, so the module form works only when the repository root is importable. Direct script invocation fails. |
| `src/compare_observation_datasets.py` | `PROJECT_ROOT = Path(__file__).resolve().parents[1]` at line 10 | Data paths are hardcoded as `PROJECT_ROOT / "data" / ...`; output is `PROJECT_ROOT / "results" / "component-2"`. | Creates `results/component-2/figures/` at module import (line 27); writes figures and summary. | Import-time directory creation is an existing side effect and must not be copied into the package. |
| `src/main.py` | `PROJECT_ROOT = Path(__file__).resolve().parent.parent` at line 14 | Uses `PROJECT_ROOT / "data"` and `PROJECT_ROOT / "plots"`. | Creates directories at import and writes legacy output. | Legacy script; unsafe to import. Keep unchanged in Phase 1. |
| `src/nbody_simulator.py` | `PROJECT_ROOT = Path(__file__).resolve().parent.parent` at line 14 | Uses `PROJECT_ROOT / "data"` and `PROJECT_ROOT / "plots"`. | Creates directories at import and writes legacy output. | Legacy script; unsafe to import. Keep unchanged in Phase 1. |
| `src/nbody_realistic.py` | `ROOT = Path(__file__).resolve().parents[1]` at line 12 | Uses `ROOT / "data"` and `ROOT / "plots"`. | Creates directories at import, performs network work and writes legacy output. | Legacy script; unsafe to import. Keep unchanged in Phase 1. |
| `src/trajectory_loader.py` | No project root. Takes a `csv_path` argument. | The caller supplies the path; the loader does not resolve it. | Prints progress; reads CSV only. | Tests often pass `"data/runs/..."`, making those tests CWD-sensitive. |
| `src/observation_schedule.py` | No path logic. | Pure array inputs. | None. | Arrays only. |
| `src/observer_model.py` | No path logic. | Pure array inputs. | None. | Arrays only. |
| `src/coordinate_converter.py` | No path logic. | Pure array inputs. | None. | Arrays only. |
| `src/measurement_noise.py` | No path logic. | Pure array inputs. | None. | Arrays only. |
| `src/horizons_loader.py` | No project root. | No file paths; network query only. | Network access when called. | Optional `network` dependency. |
| `tests/*.py` | Most tests define `PROJECT_ROOT` or `ROOT` from `Path(__file__).resolve().parents[1]`; several still pass CWD-relative `"data/..."` paths to loaders. | Mixed: some paths are anchored to the repository; some are CWD-relative. | Several tests write into tracked data; those are outside read-only validation. | C2 must not rewrite tests or silently change their path behaviour. |

### 1.2 Configuration loading

There is no shared configuration loader.

| Location | Function | Behaviour |
|---|---|---|
| `src/configurable_simulator.py:29–39` | `load_config(config_path)` | Resolves relative paths against `ROOT`; opens UTF-8 JSON; returns the configuration dictionary only. Missing files surface as the built-in `FileNotFoundError` from `open()`. No schema validation. |
| `src/observation_generator.py:29–45` | `load_config(config_path)` | Resolves relative paths against `PROJECT_ROOT`; checks existence and raises a custom-message `FileNotFoundError`; opens UTF-8 JSON; returns `(config, resolved_config_path)`. No schema validation. |
| `src/compare_observation_datasets.py:52–55` | inline metadata loading | Opens each dataset `metadata.json` with UTF-8 and returns it unchanged. Not a configuration loader. |

The two loaders are structurally similar but not interchangeable:

- one returns a dictionary, the other returns a tuple;
- one relies on the default `open()` error, the other supplies an explicit path in the error;
- both assume a module-derived project root;
- neither validates required keys or types.

A shared `core/config.py` would therefore need a deliberate contract. That is not
a C2 task.

### 1.3 Constants and repeated literals

| Constant / literal | Current locations | Nature | Proposed treatment |
|---|---|---|---|
| `365.25` days per year | `src/configurable_simulator.py:174,196`; `src/observation_generator.py:26`; `src/trajectory_loader.py:82`; `src/horizons_loader.py:62`; many tests | Unit/time convention shared by trajectory schema, observation schedule and Horizons conversion | Move to `core/constants.py` as `DAYS_PER_YEAR`; callers adopt it in their migration checkpoints. |
| `ARCSEC_TO_DEG = 1/3600` | `src/measurement_noise.py:5`; inverse `* 3600` in `src/compare_observation_datasets.py` and tests | Angle unit conversion | Move to `core/constants.py`; Component 2 noise and comparison code import it. |
| `23.43928` obliquity | `src/coordinate_converter.py:7` default; observation configs; tests | Scientific frame/observation-model default | Do **not** move to general constants. Keep with the Component 2 frame module. Configs remain authoritative. |
| `149597870.7` AU in km | Tests and legacy validation scripts only; not in `src/*.py` | Unit conversion used by external validation | Defer. Add only when a package module needs it. |
| `2460676.5` epoch JD | `src/nbody_realistic.py`; network tests | Scientific epoch for a legacy/Horizons scenario | Keep with the legacy/network workflow. Not a general constant. |
| `BODY_DATA`, `BODY_CONFIG`, `PLANETS` | `configurable_simulator.py`, `horizons_loader.py`, `nbody_simulator.py`, tests | Scientific body masses, orbits and IDs | Keep component-specific. Do not centralise in core in Phase 1. |
| `REQUIRED_COLUMNS` | `trajectory_loader.py` | Trajectory schema contract | Keep with Component 2 loader until a shared validation module exists. |
| `DATASET_NAMES`, `DATASET_COLORS`, comparison dimensions | `compare_observation_datasets.py` | Analysis-specific configuration | Keep in the future comparison module. |
| `DURATION_YR`, `NUMBER_OF_SAMPLES`, `SEMI_MAJOR_AXIS`, etc. | Legacy simulation scripts | Scientific simulation settings | Keep in the legacy scripts. |
| Output subpaths such as `data/runs/<name>`, `data/observations/<name>` and `results/component-2` | Modern scripts and configs | Component/output conventions | Keep component-specific. Core resolves a root; it does not own output layouts. |

### 1.4 Cross-component imports

- Component 1 (`configurable_simulator.py`) has no project-internal imports.
- Component 2 (`observation_generator.py`) imports five helper modules using
  absolute `src.*` imports:
  - `trajectory_loader`
  - `observation_schedule`
  - `observer_model`
  - `coordinate_converter`
  - `measurement_noise`
- Component 1 and Component 2 do not import each other.
- `nbody_realistic.py` uses a top-level `from horizons_loader import ...`.
- Tests import Component 2 helpers through `src.*`; network tests insert
  `ROOT / "src"` into `sys.path`.

This matters for `core` design:

1. A shared core can remain free of `rebound`, `numpy`, `pandas`, `matplotlib`
   and `astroquery`.
2. Core must not import either component package.
3. Component packages may depend on core, but core must not depend on them.

---

## 2. Proposed core modules and responsibilities

### 2.1 `src/orbit_discovery/core/paths.py`

**Verdict: justified.**

Evidence:

- Five source modules construct a project root from `__file__`, with two
  spellings and different parent counts.
- Two modern entry points independently resolve configuration, input and output
  paths against that root.
- The comparison script hardcodes data and results paths under the root.
- Tests repeat the same root construction and mix it with CWD-relative data
  paths.
- The approved policy requires explicit root selection and installed-command
  support, which cannot be implemented with a module-global `__file__` root.

**Responsibilities**

- Discover or resolve the project root from an explicit argument, environment
  variable or source-checkout marker.
- Resolve explicit configuration/input paths against that root.
- Resolve relative output directories against the project root or an explicit
  output root.
- Fail with an actionable error when a data command has no resolvable root.
- Remain path-only: no reading, no writing, no directory creation, no schema
  validation, no component output naming.

**Non-responsibilities**

- Do not own `data/runs`, `data/observations` or `results/component-2` naming.
- Do not create directories. Runners and CLI commands remain responsible for
  that.
- Do not rewrite configuration files.
- Do not normalise metadata path strings.
- Do not import component or scientific modules.
- Do not define a permanent global `PROJECT_ROOT`.

**Recommended minimal interface**

```python
# All functions operate on pathlib.Path and the standard library only.

def resolve_project_root(
    explicit: str | Path | None = None,
    *,
    env: Mapping[str, str] | None = None,
    cwd: str | Path | None = None,
) -> Path:
    """Resolve and validate the project root using the approved precedence."""


def resolve_project_path(
    value: str | Path,
    *,
    project_root: str | Path,
) -> Path:
    """Return an absolute path; relative values join the project root."""


def resolve_output_path(
    value: str | Path,
    *,
    project_root: str | Path,
    output_root: str | Path | None = None,
) -> Path:
    """Resolve an output path; output_root applies only to relative values."""
```

`find_project_root()` may exist as a private helper. A public function is only
needed if tests or CLI code must inspect discovery separately.

The function should use `Path` joins and preserve the current lexical behaviour
of `ROOT / relative_path`. It should not call `.resolve()` on configuration or
output values during Phase 1, because resolving `..` components can change
metadata strings produced by `Path.relative_to()`.

The error type needs a decision:

- a small `ProjectRootNotFoundError` in `core/errors.py`, or
- the same exception defined only in `paths.py` if C2 is limited to the three
  modules proposed in this task.

The full exception hierarchy proposed in `REFACTORING_PLAN.md` is premature.

### 2.2 `src/orbit_discovery/core/constants.py`

**Verdict: justified, but only for genuinely shared unit conventions.**

Recommended contents:

```python
DAYS_PER_YEAR = 365.25
ARCSEC_TO_DEG = 1.0 / 3600.0
```

Rationale:

- `DAYS_PER_YEAR` is used by Component 1 output construction, Component 2 time
  conversion, the trajectory loader consistency check and the Horizons velocity
  conversion. It is a project-wide time convention, not a scenario setting.
- `ARCSEC_TO_DEG` is the inverse of the arcseconds-per-degree conversion used by
  the comparison summary. It is a unit conversion shared across noise and
  analysis code.

Do **not** include:

- `OBLIQUITY_DEG` — a scientific frame default currently owned by
  `coordinate_converter.py` and supplied explicitly by every observation
  configuration. Moving it into general constants would blur the component
  boundary.
- `AU_KM` — not used by any current source module.
- `EPOCH_JD` — a legacy/network scenario epoch.
- `BODY_DATA`, `BODY_CONFIG`, `PLANETS` — scientific model data.
- seeds, durations, sample counts, uncertainty values or output directory names
  — scenario or component policy.

This is a proposed amendment to the shorthand in the Step 1.1 checkpoint list,
which names `OBLIQUITY_DEG` alongside the other constants. The C2.1 criterion is
more specific: scientific model parameters should stay with their component.

### 2.3 `src/orbit_discovery/core/config.py`

**Verdict: not justified for C2.**

Reasons:

1. Only two real config loaders exist, and they are not behaviourally identical.
2. No shared caller currently needs a common return type.
3. Config validation belongs to the later contract/validation phase.
4. Introducing a loader now would either:
   - expose a new API that existing callers do not use, or
   - require changing `load_config` behaviour during C2, which the checkpoint
     forbids.
5. The path-resolution portion of both loaders belongs in `paths.py`; the JSON
   read itself is a two-line operation and does not yet justify a module.

Recommended timing: revisit in C4/C5, when both component loaders are being
moved. At that point a shared function can be designed deliberately, for
example:

```python
def load_json_config(
    path: str | Path,
    *,
    project_root: str | Path,
) -> tuple[dict, Path]:
    """Resolve, read and return a JSON configuration plus its resolved path."""
```

Component wrappers can then preserve their existing public names, return shapes
and error messages.

### 2.4 Adjacent modules proposed by the migration plan

| Module | C2 status | Reason |
|---|---|---|
| `core/errors.py` | Optional, minimal only | The C2 checkpoint names it. A single `ProjectRootNotFoundError` may be useful for CLI error handling. A full `ConfigurationError`/`ValidationError` hierarchy is not justified yet. |
| `core/io.py` | Not in C2 | CSV/JSON writers are still embedded in component code; no shared implementation exists. |
| `core/validation.py` | Not in C2 | Trajectory validation is currently a Component 2 loader responsibility; shared validation contracts belong to Phase 2. |
| `core/logging.py` | Not in C2 | No logging abstraction exists; all code uses `print()`. |
| `core/time.py`, `core/units.py` | Not in C2 | No concrete shared implementation beyond the two constants above. |

---

## 3. Exact source-to-destination migration mapping

C2 itself must **not** apply these changes. The table records where the
behaviour will be extracted in later checkpoints and what must remain
compatible.

### 3.1 Path behaviour

| Current source | Current behaviour | Proposed destination | Future caller / checkpoint | Compatibility requirement |
|---|---|---|---|---|
| `src/configurable_simulator.py:14` — `ROOT = Path(__file__).resolve().parents[1]` | Module-global source-checkout root | `core/paths.py::resolve_project_root` | C5 Component 1 runner | Old script keeps working through a shim that supplies its legacy root explicitly. New CLI uses the policy. |
| `src/configurable_simulator.py:29–39` — `load_config()` relative join | `ROOT / relative_config`; absolute config unchanged | `core/paths.py::resolve_project_path` plus future config loader | C5 | Resolve relative config against project root, not CWD. Preserve absolute paths. |
| `src/configurable_simulator.py:210–212` — output directory | `ROOT / config["output"]["directory"]`; `mkdir` in runner | `core/paths.py::resolve_output_path`; directory creation stays in runner | C5 | Same default output path when run from the repository root. `--output-root` is a new opt-in. |
| `src/observation_generator.py:25` — `PROJECT_ROOT` | Module-global source-checkout root | `core/paths.py::resolve_project_root` | C4 | Old module form remains available through the old path/shim. |
| `src/observation_generator.py:29–45` — `load_config()` | Returns `(config, resolved_path)`; relative config against root; custom missing-file message | `core/paths.py::resolve_project_path` plus future shared config loader | C4 | Preserve the tuple return and error message in the component wrapper. |
| `src/observation_generator.py:57–60` — input trajectory | Relative path against `PROJECT_ROOT`; absolute unchanged | `core/paths.py::resolve_project_path` | C4 | Same path for existing configs. No metadata formatting change. |
| `src/observation_generator.py:186–194` — output directory | `PROJECT_ROOT / output.directory / observation_name`; `mkdir` | `core/paths.py::resolve_output_path`; component keeps `observation_name` join and `mkdir` | C4 | Preserve `data/observations/<observation_name>` exactly by default. |
| `src/observation_generator.py:206–211` — metadata path strings | `str(path.relative_to(PROJECT_ROOT))` when inside root; otherwise absolute string | No core move in Phase 1 | C4 | Preserve host separators and the existing `relative_to`/absolute fallback. Do not add normalisation. |
| `src/compare_observation_datasets.py:10` — `PROJECT_ROOT` | Source-checkout root | `core/paths.py::resolve_project_root` | C6 | New comparison module receives root explicitly. |
| `src/compare_observation_datasets.py:24–27` — output/figures | `results/component-2/figures`; created at import | `core/paths.py::resolve_output_path`; directory creation moves to runner | C6 | No import-time directory creation in the package. Preserve figure filenames and summary columns. |
| `src/main.py:14–19`, `src/nbody_simulator.py:14–19`, `src/nbody_realistic.py:12–17` — legacy roots/directories | `__file__`-derived roots; import-time directory creation | **No move in Phase 1** | Future archive decision | Keep unchanged. Do not import from the package. |
| `tests/*.py` — root variables and CWD-relative data paths | Mixed anchored/CWD-relative paths | **No move in C2** | C3/C8 test migration | Keep existing scripts runnable. Do not silently rewrite their path semantics. |

### 3.2 Constants

| Current source | Current behaviour | Proposed destination | Future caller / checkpoint | Compatibility requirement |
|---|---|---|---|---|
| `src/observation_generator.py:26` — `DAYS_PER_YEAR = 365.25` | Observation time conversion | `core/constants.py::DAYS_PER_YEAR` | C4 | Identical numeric value. |
| `src/configurable_simulator.py:174,196` — literal `365.25` | Interval and `time_days` conversion | `core/constants.py::DAYS_PER_YEAR` | C5 | Identical numeric value; no change to time grid. |
| `src/trajectory_loader.py:82` — literal `365.25` | `time_days ≈ time_years * 365.25` check | `core/constants.py::DAYS_PER_YEAR` | C3 | Preserve tolerance and error message. |
| `src/horizons_loader.py:62` — `velocity_conversion = 365.25` | Horizons AU/day → AU/year | `core/constants.py::DAYS_PER_YEAR` | C5/network migration | Preserve numeric conversion exactly. |
| `src/measurement_noise.py:5` — `ARCSEC_TO_DEG` | Arcseconds to degrees | `core/constants.py::ARCSEC_TO_DEG` | C3 | Old module re-exports the same name/value. |
| `src/compare_observation_datasets.py` — inverse `* 3600` | Arcsecond residuals | `core/constants.py::ARCSEC_TO_DEG` (or its inverse) | C6 | Preserve residual calculation, including RA wrap and `cos(dec)`. |
| `src/coordinate_converter.py:7` — `obliquity_deg=23.43928` | Scientific frame default | **No move**; remains Component 2 frame responsibility | C3 | Preserve default. Configs continue to supply the value explicitly. |
| `tests/*.py` — `365.25`, `1826.25`, `23.43928`, `149597870.7`, `2460676.5` | Test expectations and network epochs | **No C2 change** | C8 or later | Do not rewrite tests in C2; defer to test conversion. |
| Legacy simulation constants (`DURATION_YR`, `NUMBER_OF_SAMPLES`, `SEMI_MAJOR_AXIS`, `PLANETS`, etc.) | Legacy scenario definitions | **No move** | Future archive decision | Keep with legacy scripts. |

### 3.3 Configuration loading

| Current source | Current behaviour | Proposed destination | Timing |
|---|---|---|---|
| `src/configurable_simulator.py:29–39` | `load_config()` returns dict; root-relative; default open error | Future `component1_simulation/config.py`; shared JSON read only if a common contract is approved | C5 |
| `src/observation_generator.py:29–45` | `load_config()` returns `(dict, Path)`; root-relative; custom error | Future `component2_observations/config.py`; shared JSON read if approved | C4 |
| `src/compare_observation_datasets.py:52–55` | Inline metadata JSON read | Future comparison module; not a general config loader | C6 |

No `core/config.py` entry is proposed for C2.

---

## 4. Existing callers and required import changes

### 4.1 Current callers

| Caller | What it uses today | C2 impact |
|---|---|---|
| `src/configurable_simulator.generate_trajectory()` | `load_config()`, `ROOT`, output directory construction | None. File remains unchanged. |
| `src/observation_generator.generate_observations()` | `load_config()`, `PROJECT_ROOT`, `input_trajectory`, output directory, Component 2 helpers | None. File remains unchanged. |
| `src/compare_observation_datasets.main()` | `PROJECT_ROOT`, hardcoded data/results paths, import-time `mkdir` | None. File remains unchanged. |
| Tests importing `src.trajectory_loader`, `src.observation_schedule`, `src.observer_model`, `src.coordinate_converter`, `src.measurement_noise` | Old `src.*` import paths | None in C2. Shims preserve these imports in C3. |
| Legacy scripts | `ROOT`/`PROJECT_ROOT` from their own file; `horizons_loader` top-level import | None. Keep unchanged. |
| README commands | `python src\configurable_simulator.py ...` and `python -m src.observation_generator ...` | None. Keep working. |

### 4.2 Future import changes

When the relevant checkpoints occur:

- Component 1 runner:
  - `from orbit_discovery.core.paths import resolve_project_root, resolve_project_path, resolve_output_path`
  - `from orbit_discovery.core.constants import DAYS_PER_YEAR`
- Component 2 generator/loader/noise:
  - `from orbit_discovery.core.paths import ...`
  - `from orbit_discovery.core.constants import DAYS_PER_YEAR, ARCSEC_TO_DEG`
- Old modules:
  - become thin shims that import from the package and re-export the existing
    public names;
  - do not duplicate science or path logic.
- Tests:
  - may continue importing `src.*` through shims until the test migration
    checkpoint.

### 4.3 Import constraints for core

`core/paths.py` and `core/constants.py` should import only the standard library.
They must not import:

- `rebound`, `numpy`, `pandas` or `matplotlib`;
- `astroquery` or any network library;
- `orbit_discovery.component1_simulation` or
  `orbit_discovery.component2_observations`;
- any module that performs filesystem writes or directory creation at import.

This preserves the base-install and import-safety requirements.

---

## 5. Project-root and configuration-path policy

### 5.1 Root precedence

For commands that read or write project data:

| Priority | Source | Required behaviour |
|---:|---|---|
| 1 | `--project-root PATH` | Use exactly this directory after verifying it exists and is a directory. |
| 2 | `ORBIT_DISCOVERY_ROOT` | Use the environment value. If relative, resolve it against the current working directory and emit a warning. |
| 3 | Nearest ancestor of the current directory containing `pyproject.toml` | Use the source-checkout root. This works from the repository root and from subdirectories. |
| 4 | No root found | Fail with an actionable error for data-reading/writing commands. Do not silently use the current directory. |

`--help` and `--version` never require a root.

### 5.2 Path resolution rules

- A relative `--project-root` or `--output-root` argument is resolved against the
  current working directory, following normal CLI expectations, then validated.
- A relative `--config` path resolves against the resolved project root. This
  preserves the current behaviour of both modern entry points.
- An absolute `--config` path is used as supplied.
- Relative `input_trajectory` and `output.directory` values inside a
  configuration resolve against the project root.
- Absolute paths inside a configuration remain absolute.
- When `--output-root` is supplied, relative `output.directory` values resolve
  against it. Absolute output paths remain absolute, even when `--output-root`
  is supplied.
- Directory creation belongs to the component runner or CLI, never to
  `core.paths` and never to module import.
- No configuration file is rewritten to inject a root. Root selection is a
  runtime concern.

### 5.3 Behaviour examples

| Invocation context | Expected result |
|---|---|
| Repository root, `orbit-observe --config configs/synthetic_observations.json` | Root found from `pyproject.toml`; config at `<root>/configs/...`; default outputs under `<root>/data/observations/...`. |
| Repository subdirectory, same command | Root found by walking up to the repository; same paths as from the root. |
| Outside the repository, no root option and no environment variable | Actionable error for a data command. No fallback to the unrelated CWD. |
| Outside the repository, `--project-root E:\repo` | Relative config, input and output paths resolve against `E:\repo`. |
| Outside the repository, `ORBIT_DISCOVERY_ROOT=E:\repo` | Same as explicit root unless overridden by `--project-root`. |
| Absolute `--config E:\tmp\custom.json` with relative input/output paths inside it | Config is read from the absolute path; relative config-internal paths still resolve against the project root. |
| `--output-root E:\tmp\run` with config output directory `data/observations` | Output goes to `E:\tmp\run\data\observations`; absolute config output paths are unaffected. |

### 5.4 Incompatibilities and resolution

| Current behaviour | Policy difference | Handling |
|---|---|---|
| `configurable_simulator.py` uses a `__file__`-derived root, so it works from an arbitrary CWD in a source checkout. | An installed command with no root must fail rather than guess. | The old script shim computes its legacy root and passes it explicitly to the new runner. The installed CLI uses the approved policy and requires `--project-root`/environment outside a source checkout. |
| `observation_generator.py` resolves relative config/input/output against `PROJECT_ROOT`, but imports require the repository root on `sys.path`. | The new package can run from another CWD when the root is resolved. | When installed, use the explicit root policy. The old module form remains available through its own path/shim. |
| Tests pass `"data/runs/..."` directly to the loader. | Core resolution would change those paths if adopted by tests. | Do not change tests in C2. Anchor test paths in the test-migration checkpoint. |
| Metadata records host-separator paths relative to the project root. | A path helper that normalises or resolves `..` could alter metadata. | Preserve lexical joins and existing `relative_to` formatting in Phase 1. Do not use a metadata formatting helper yet. |
| Relative config paths currently mean project-root-relative in both modern entry points. | A generic CLI user might expect CWD-relative paths. | Keep project-root-relative behaviour for compatibility; document that absolute paths should be used when a CWD-relative file is intended. This is a decision requiring approval. |
| `compare_observation_datasets.py` creates its figure directory at import. | The new package must not create directories at import. | Keep the old script unchanged until C6; its new package equivalent creates directories only in the runner. |

---

## 6. Compatibility strategy

1. **C2 is additive only.**
   Add `core/paths.py`, `core/constants.py` and focused tests. Do not edit
   existing source, tests, configs or data.

2. **Existing commands remain authoritative.**
   Until C3–C6, the current `src/*.py` modules continue to provide the
   documented behaviour and paths.

3. **Legacy shims preserve legacy roots.**
   When an old script becomes a shim, it should compute its historical
   source-checkout root from its own location and pass that root explicitly to
   the package runner. This preserves behaviour for users running the old
   script from outside the repository, while the new installed CLI uses the
   explicit root policy.

4. **No shim duplicates science or path policy.**
   Shims import and delegate. They may supply a compatibility root, but they do
   not reimplement validation, configuration loading or output naming.

5. **No path normalisation in Phase 1.**
   Preserve host separators in metadata and the existing `relative_to`/
   absolute-path fallback.

6. **No config or data movement.**
   The six configs, data tree, results and plots remain at their current paths.

7. **No import-time writes.**
   Core modules are pure. Directory creation remains in component runners and
   CLI commands.

8. **Tests retain their old import paths.**
   The existing `src.*` imports remain valid through the migration. Test
   rewriting and CWD anchoring are separate checkpoints.

---

## 7. Required tests and acceptance criteria

### 7.1 Core path tests

The C2 tests should use only temporary directories and must not write into the
repository. They should cover:

1. Explicit `--project-root` wins over environment and discovery.
2. `ORBIT_DISCOVERY_ROOT` is used when no explicit root is supplied.
3. A relative environment value resolves against the supplied CWD and warns.
4. A `pyproject.toml` ancestor is found from a nested directory.
5. No root produces an actionable `ProjectRootNotFoundError`.
6. A missing or non-directory explicit root is rejected.
7. A relative configuration/input path resolves against the project root.
8. An absolute configuration/input path is returned unchanged.
9. A relative output directory resolves against the project root when no output
   root is supplied.
10. A relative output directory resolves against `--output-root` when supplied.
11. An absolute output directory remains absolute when `--output-root` is
    supplied.
12. Path-resolution functions create no files or directories.
13. Existing repository-root-relative values such as
    `configs/synthetic_asteroid.json` and
    `data/runs/synthetic_asteroid/trajectory.csv` resolve to the same locations
    as the current `ROOT / value` logic.
14. Path resolution does not mutate the supplied `Path` or environment mapping.

Because `pytest` is not installed, the first C2 test can be a standard-library
script or `unittest` module with explicit assertions. It must be safe to run
from a temporary CWD. Full pytest conversion remains C8.

### 7.2 Core constant tests

1. `DAYS_PER_YEAR == 365.25`.
2. `ARCSEC_TO_DEG == 1.0 / 3600.0`.
3. Existing conversion expressions produce the same numeric result when
   rewritten against the constants.
4. No scientific model constants, seeds or body data are exported from
   `core.constants`.

### 7.3 Import and regression checks

1. Importing `orbit_discovery.core.paths` and
   `orbit_discovery.core.constants` performs no filesystem writes, network
   access, plotting or simulation.
2. Import works from a temporary CWD when the package is installed or when
   `src` is on `PYTHONPATH`.
3. The existing legacy help commands still work from the repository root:
   - `python src\configurable_simulator.py --help`
   - `python -m src.observation_generator --help`
4. `git status` shows no changes under `configs/`, `data/`, `results/`,
   `plots/` or existing source/tests.
5. Existing read-only validation scripts still pass when their paths are
   unchanged.
6. No configuration file is rewritten and no output dataset is regenerated.

### 7.4 C2 acceptance criteria

| Requirement | Acceptance |
|---|---|
| Explicit root | Highest priority; validated directory. |
| Environment root | Used when no explicit root; relative value resolved against CWD with warning. |
| Source-checkout discovery | Nearest `pyproject.toml` ancestor is found from a subdirectory. |
| Missing root | Data commands fail with an actionable error; no silent CWD fallback. |
| Config resolution | Relative paths resolve against the project root; absolute paths unchanged. |
| Output resolution | Relative output paths follow project root or output root; absolute output paths unchanged. |
| Import safety | Core import creates no directories and reads no data. |
| Compatibility | No existing module, config, data or output behaviour changes in C2. |
| Scope | Only the approved core modules and focused tests are added. |

---

## 8. Risks and rollback plan

| ID | Risk | Likelihood | Impact | Mitigation | Rollback |
|---|---|---:|---|---|---|
| RP-01 | Root discovery selects an unrelated parent `pyproject.toml` when run from another project. | Medium | High | Prefer `--project-root`; document marker semantics; test nested and unrelated directories. | Remove core path discovery and restore the old shim behaviour. |
| RP-02 | A relative `--config` is expected to be CWD-relative but resolves against the project root. | Medium | Medium | Document the rule; use absolute paths for CWD-specific files; test both cases. | Change the policy before callers adopt it; C2 is still additive. |
| RP-03 | Installing the package makes `__file__` point into `site-packages`. | High if installed commands use the old model | High | Never derive the project root from package `__file__`; use explicit root/env/marker policy. | Remove path helper; old source-checkout commands remain. |
| RP-04 | Path normalisation changes metadata strings. | Medium | Medium | Preserve lexical joins and current `relative_to` formatting; no `.resolve()` on config/output values. | Restore the old formatting; metadata remains untouched. |
| RP-05 | `--output-root` unexpectedly overrides an absolute output path. | Low | Medium | Absolute output paths remain absolute; test this explicitly. | Revert output-root handling before any run. |
| RP-06 | Creating `core/config.py` too early changes loader return values or error messages. | Medium | High | Do not create it in C2; defer to C4/C5. | Delete the module; component loaders remain authoritative. |
| RP-07 | Moving `OBLIQUITY_DEG` into core weakens the component boundary. | Medium | Medium | Keep the frame default in Component 2; configs remain authoritative. | Move it back to the frame module. |
| RP-08 | Core imports a scientific or network dependency. | Low | High | Standard-library-only core; import smoke test. | Remove the dependency and restore the pure module. |
| RP-09 | Tests create directories or write into tracked paths. | Medium | High | Use temporary directories; no repository writes; check `git status`. | Remove test side effects; restore data from Git if necessary. |
| RP-10 | The baseline tag is still absent (`git tag --list` is empty). | High | Medium | Resolve C0 before C2 implementation; use the baseline commit as fallback. | Create the tag before proceeding; do not rewrite history. |
| RP-11 | Existing CWD-sensitive tests fail from a temporary directory. | High | Medium | Do not change them in C2; anchor paths in the test-migration checkpoint. | Revert test changes; keep the old script paths. |

### 8.1 Rollback procedure

1. C2 should be a separate commit that adds only new core modules and tests.
   Reverting that commit restores the pre-C2 state without touching source,
   configs or data.
2. If a path policy causes a regression before callers migrate, remove
   `core/paths.py` and its tests; existing modules remain unchanged.
3. If a compatibility shim later breaks, restore the old shim and leave the new
   package code unused; the old path remains functional.
4. If tracked data or configs change accidentally, restore them from Git and
   verify the baseline hashes. Do not regenerate data to “fix” a diff.
5. If the installed-command root policy is rejected, retain the legacy shim
   behaviour and postpone installed-command support rather than adding a silent
   CWD fallback.

---

## 9. Decisions requiring approval

| ID | Decision | Recommendation | Why it needs review |
|---|---|---|---|
| D-01 | `core/constants.py` contents | Include `DAYS_PER_YEAR` and `ARCSEC_TO_DEG`; exclude `OBLIQUITY_DEG`. | The Step 1.1 checkpoint shorthand names `OBLIQUITY_DEG`, but it is a scientific frame default and the C2.1 criterion excludes scientific model parameters from general constants. |
| D-02 | `core/config.py` in C2 | Do not create it; defer to C4/C5. | The two current loaders have different return/error contracts; no shared implementation is needed yet. |
| D-03 | Path error type | Use a single `ProjectRootNotFoundError`; put it in `core/errors.py` if the C2 checkpoint is followed literally, otherwise define it in `paths.py`. | The approved checkpoint mentions `errors.py`, but a full exception hierarchy is not justified. |
| D-04 | Relative `--config` semantics | Resolve against the project root; use absolute paths for CWD-specific files. | This preserves current behaviour but may surprise users expecting standard CWD-relative CLI paths. |
| D-05 | Relative `--project-root` and `--output-root` semantics | Resolve them against the CWD, then validate. | The assessment does not explicitly state how relative root arguments themselves resolve. |
| D-06 | Absolute output paths with `--output-root` | Keep absolute output paths absolute. | Matches the approved policy but should be confirmed before implementation. |
| D-07 | Legacy shim root behaviour | Old scripts pass their `__file__`-derived source root explicitly to the new runner; new installed commands use the policy. | Preserves current direct-script behaviour from an arbitrary CWD without reintroducing a module-global root in the package. |
| D-08 | Root marker | Use only `pyproject.toml` as the source-checkout marker. | A lone marker can select an unrelated parent project; adding a `configs/` or `src/orbit_discovery` check would change the approved rule. |
| D-09 | `AU_KM` | Defer; do not add it in C2. | It is not used by any current `src/*.py` module. |
| D-10 | C0 baseline status | Confirm/create the baseline tag before C2 implementation. | `git tag --list` is still empty, while the approved migration sequence requires a baseline tag before code moves. |

---

## 10. Git status and read-only confirmation

At the start of this assessment, the working tree status was:

```text
## main
?? docs/development/PHASE_1_STEP_1_ASSESSMENT.md
?? pyproject.toml
?? src/orbit_discovery/
```

No tracked files were modified. `git diff --stat` produced no output. The C1
files and the Step 1 assessment remain untracked; that is the state inherited
from the previous checkpoints.

This assessment created only:

```text
docs/development/PHASE_1_STEP_2_CORE_ASSESSMENT.md
```

No source file, test, configuration, dependency file, dataset, plot or result
was changed. No package module was created. No dependency was installed. No
simulation, observation generation, comparison workflow or data-writing test was
run. No commit, tag or push was performed.

After creating this report, `git status --short` is expected to show the new
report in addition to the pre-existing untracked files. The report itself is
the only new artefact from this step.

---

*End of Step 2.1 core assessment. No C2 implementation has been performed.*
