# Phase 1 — C3.5.1: Observation Generator Orchestration Assessment

**Status:** Read-only assessment. No migration was implemented.

**Repository:** `E:\rskmn\Npersonal\projects\yr4\final\prototype-1\physics-guided-orbit-discovery-prototype`

**Scope:** Assess moving `src/observation_generator.py` to
`src/orbit_discovery/component2_observations/generator.py`, retaining the old
path as a compatibility shim, without changing scientific behaviour, outputs,
configurations, datasets, or CLI behaviour.

**Out of scope for this checkpoint:** implementing the migration, creating
`orbit_discovery.cli.observe`, adding a console entry point, integrating
`core.paths` into the generator, changing metadata or truth columns, moving
configs, regenerating data, committing, tagging, or pushing.

---

## 1. Existing generator architecture

### 1.1 File and entry point

| Item | Current value |
|---|---|
| File | `src/observation_generator.py` |
| Lines | 285 (including blank lines) |
| Public functions | `load_config(config_path)`, `generate_observations(config_path)`, `main()` |
| Module constants | `PROJECT_ROOT`, `DAYS_PER_YEAR = 365.25` |
| CLI | `argparse` with one option: `--config` |
| Default config | `configs/synthetic_observations.json` |
| `__main__` behaviour | Calls `main()` |
| Documented command | `python -m src.observation_generator --config configs\synthetic_observations.json` |

The generator is a linear orchestrator. It contains no numerical model of its
own beyond the `365.25` days-per-year conversion; each scientific step is
delegated to one of the five Component 2 helper modules.

### 1.2 Pipeline sequence

`generate_observations()` performs the following sequence:

| Step | Activity | Delegate |
|---:|---|---|
| 1 | Read the JSON config and resolve its path | `load_config()` in the generator |
| 2 | Resolve `input_trajectory` against `PROJECT_ROOT` | generator |
| 3 | Load and validate the trajectory CSV | `loader.load_trajectory` |
| 4 | Generate observation times | `schedule.generate_observation_times` |
| 5 | Convert observation days to years | generator (`DAYS_PER_YEAR`) |
| 6 | Interpolate asteroid positions | `schedule.interpolate_positions` |
| 7 | Calculate observer positions | `observer.calculate_observer_positions` |
| 8 | Calculate observer-relative vectors | `observer.calculate_relative_positions` |
| 9 | Rotate ecliptic to equatorial | `frames.ecliptic_to_equatorial` |
| 10 | Calculate true RA/Dec | `frames.calculate_ra_dec` |
| 11 | Add seeded Gaussian noise | `noise.add_measurement_noise` |
| 12 | Build the observations DataFrame | generator |
| 13 | Optionally append truth columns | generator |
| 14 | Create the output directory and write `observations.csv` | generator |
| 15 | Build and optionally write `metadata.json` | generator |
| 16 | Print the success summary and first observation | generator |

The comments in the current source number these as eleven stages; the table
above separates file writing and printing for clarity. The implementation is a
single pass with no retries, logging, caching, or intermediate files.

### 1.3 Current invocation behaviour (verified without generation)

The following probes were run read-only. No observation generation was
executed.

| Command | Working directory | Result |
|---|---|---|
| `python -m src.observation_generator --help` | repository root | Exit `0`; usage printed |
| `python src\observation_generator.py --help` | repository root | Exit `1`; `ModuleNotFoundError: No module named 'src.trajectory_loader'` |
| `python -m src.observation_generator --help` | outside repository | Exit `1`; `No module named src.observation_generator` |
| `python -m src.observation_generator --help` with the repository root on `PYTHONPATH` | outside repository | Exit `0`; usage printed |
| `python -c "import src.observation_generator"` | repository root | Exit `0`; no stdout/stderr output |

The direct-script failure is caused by the absolute `from src...` imports at
lines 9–22. Running the file directly puts `src/` on `sys.path` instead of the
repository root, so `src.trajectory_loader` is not importable. The README
already documents that the `-m` form is required.

### 1.4 Import-time behaviour

Importing `src.observation_generator` currently:

- imports `argparse`, `json`, and `pathlib` from the standard library;
- imports `numpy` and `pandas`;
- imports the five `src.*` compatibility shims, which in turn import the five
  package helper modules;
- computes `PROJECT_ROOT` from `Path(__file__).resolve().parents[1]`;
- defines `DAYS_PER_YEAR = 365.25`;
- defines three functions;
- does **not** read a config, load a trajectory, create directories, write
  files, print, or draw random numbers.

The package’s editable installation is present:

```text
Name: orbit-discovery
Version: 0.2.0
Editable project location: ...\physics-guided-orbit-discovery-prototype
```

`orbit_discovery` resolves to `src/orbit_discovery/__init__.py`, so package
module imports are available in this environment.

---

## 2. Function and responsibility inventory

### 2.1 Public functions

| Function | Exact signature | Current behaviour | Return |
|---|---|---|---|
| `load_config` | `load_config(config_path)` | Resolves relative paths against `PROJECT_ROOT`, checks existence, reads UTF-8 JSON | `(config_dict, resolved_config_path)` |
| `generate_observations` | `generate_observations(config_path)` | Runs the complete pipeline, writes outputs, prints summary | `(observations_DataFrame, metadata_dict)` |
| `main` | `main()` | Parses `--config`; calls `generate_observations(args.config)` | `None` on success |

There is no `__all__` in the current module. `PROJECT_ROOT` and `DAYS_PER_YEAR`
are module attributes that current or external code could read even though they
are not functions.

### 2.2 Responsibility matrix

| Responsibility | Current location | Recommendation after migration | Notes |
|---|---|---|---|
| Config file path resolution | `load_config()` | Remain in `generator.py` initially | Depends on `PROJECT_ROOT`; later candidate for `core.paths` |
| Config existence check and JSON read | `load_config()` | Remain in `generator.py` initially | Error message must remain exact |
| Config schema validation | None | Remain absent in the pure move | Do not add validation in this checkpoint |
| Project-root resolution | Module constant | Remain in `generator.py`, with a corrected depth | See Section 4.8 |
| Input trajectory path resolution | `generate_observations()` | Remain in `generator.py` | Relative paths use the module root |
| Trajectory loading and validation | `loader.load_trajectory` | Delegate | No change |
| Observation-time generation | `schedule.generate_observation_times` | Delegate | No change |
| Position interpolation | `schedule.interpolate_positions` | Delegate | No change |
| Observer position | `observer.calculate_observer_positions` | Delegate | No change |
| Relative position | `observer.calculate_relative_positions` | Delegate | No change |
| Ecliptic-to-equatorial rotation | `frames.ecliptic_to_equatorial` | Delegate | No change |
| RA/Dec calculation | `frames.calculate_ra_dec` | Delegate | No change |
| Measurement noise | `noise.add_measurement_noise` | Delegate | No change |
| Days-to-years conversion | Inline `/ DAYS_PER_YEAR` | Remain an inline conversion, using a shared constant if approved | Same numeric value |
| DataFrame construction and column order | `generate_observations()` | Remain in `generator.py` | Column order is an invariant |
| Optional truth columns | `generate_observations()` | Remain in `generator.py` | Do not remove or separate |
| Output directory creation | `generate_observations()` | Remain in `generator.py` | Preserve `mkdir(parents=True, exist_ok=True)` |
| CSV writing | `generate_observations()` | Remain in `generator.py` | preserve `to_csv(..., index=False)` |
| Metadata construction | `generate_observations()` | Remain in `generator.py` | Preserve key order and values |
| Metadata writing | `generate_observations()` | Remain in `generator.py` | Preserve `json.dump(..., indent=4)` |
| Success prints | `generate_observations()` | Remain in `generator.py` | Preserve exact messages |
| CLI parsing | `main()` | Move with the implementation, re-export through shim | Do not add options |
| Error handling | None (propagation) | Remain propagation-only | Do not add catches or new exit codes |

### 2.3 Configuration validation currently performed

`load_config()` only checks that the resolved file exists and that the JSON can
be decoded. It does **not** validate:

- required top-level keys;
- required nested keys;
- value types;
- unknown keys;
- `observer.model` dispatch;
- `coordinates.input_frame` or `coordinates.output_frame`;
- `coordinates.ra_unit` or `coordinates.dec_unit`;
- `measurement_noise.model` dispatch;
- consistency between schedule values and trajectory metadata;
- trajectory frame, units, epoch, or `state_type` against `metadata.json`.

The helper modules perform narrow numerical validation:

- `schedule.generate_observation_times`: cadence positive, end greater than
  start, requested interval inside the trajectory time range;
- `schedule.interpolate_positions`: shape, ordering, finiteness, and range;
- `observer`: positive radius and period, finite times, shape matching;
- `frames`: shape and finiteness, nonzero vectors for RA/Dec;
- `noise`: matching shapes, finite coordinates, declination range, nonnegative
  sigmas, pole singularities, and noisy declination range.

A missing top-level or nested key therefore raises `KeyError`; a malformed type
raises a later `TypeError` or helper `ValueError`. This behaviour is part of the
current contract and should not be changed by the packaging move.

---

## 3. Dependency and import map

### 3.1 Current imports

```python
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.trajectory_loader import load_trajectory
from src.observation_schedule import (
    generate_observation_times,
    interpolate_positions,
)
from src.observer_model import (
    calculate_observer_positions,
    calculate_relative_positions,
)
from src.coordinate_converter import (
    ecliptic_to_equatorial,
    calculate_ra_dec,
)
from src.measurement_noise import add_measurement_noise
```

### 3.2 Calls into the five helper modules

| Caller line(s) | Helper | Called function(s) |
|---|---|---|
| 9, 62 | `trajectory_loader` | `load_trajectory(input_path)` |
| 10–13, 73–79 | `observation_schedule` | `generate_observation_times(...)` |
| 10–13, 89–93 | `observation_schedule` | `interpolate_positions(...)` |
| 14–17, 101–106 | `observer_model` | `calculate_observer_positions(...)` |
| 14–17, 112–115 | `observer_model` | `calculate_relative_positions(...)` |
| 18–21, 123–126 | `coordinate_converter` | `ecliptic_to_equatorial(...)` |
| 18–21, 128–130 | `coordinate_converter` | `calculate_ra_dec(...)` |
| 22, 143–153 | `measurement_noise` | `add_measurement_noise(...)` |

The five helpers are available in the package at:

| Old path | Package path | Public names |
|---|---|---|
| `src/trajectory_loader.py` | `orbit_discovery.component2_observations.loader` | `REQUIRED_COLUMNS`, `load_trajectory` |
| `src/observation_schedule.py` | `orbit_discovery.component2_observations.schedule` | `generate_observation_times`, `interpolate_positions` |
| `src/observer_model.py` | `orbit_discovery.component2_observations.observer` | `calculate_observer_positions`, `calculate_relative_positions` |
| `src/coordinate_converter.py` | `orbit_discovery.component2_observations.frames` | `ecliptic_to_equatorial`, `calculate_ra_dec` |
| `src/measurement_noise.py` | `orbit_discovery.component2_observations.noise` | `ARCSEC_TO_DEG`, `add_measurement_noise` |

### 3.3 Dependency classification

| Dependency | Type | Use |
|---|---|---|
| `argparse` | standard library | CLI parsing |
| `json` | standard library | Config and metadata JSON |
| `pathlib.Path` | standard library | Path resolution and output |
| `numpy` | third party | `np.full`, arrays, DataFrame values |
| `pandas` | third party | `DataFrame`, `to_csv` |
| `orbit_discovery.core.constants` | project package | `DAYS_PER_YEAR` if adopted |
| five Component 2 package modules | project package | Scientific operations |

`rebound`, `matplotlib`, `astroquery`, and other Component 1 or legacy-script
dependencies are not imported by the generator.

### 3.4 Circular import risk

The current graph is a star:

```text
src.observation_generator
    -> src.trajectory_loader
    -> src.observation_schedule
    -> src.observer_model
    -> src.coordinate_converter
    -> src.measurement_noise
```

After migration the intended graph is:

```text
src.observation_generator (shim)
    -> orbit_discovery.component2_observations.generator
        -> loader
        -> schedule
        -> observer
        -> frames
        -> noise
        -> orbit_discovery.core.constants
```

No helper imports the generator, and `core.constants` imports nothing from the
components. There is no cycle provided:

- `component2_observations/__init__.py` remains minimal;
- `orbit_discovery` package initialisers do not eagerly import the generator;
- the shim is a leaf importer;
- a future CLI module may import the generator, but the generator must not
  import the CLI module.

### 3.5 Reliance on the repository root and current working directory

Two separate dependencies exist:

1. **Import dependency.** `from src...` imports require the repository root on
   `sys.path`. This is why `python -m src.observation_generator` works from the
   repository root but fails from another directory, and why direct script
   execution fails.
2. **Data-path dependency.** Relative config, input-trajectory, and output
   paths are resolved against `PROJECT_ROOT`, which is derived from the source
   file location. They do not depend on the process working directory.

After migration, package imports rely on the editable installation (or `src/`
being on `sys.path`). The existing old module command still relies on the
repository root being importable for `src.observation_generator` itself. The
package generator’s file-relative root must be corrected from `parents[1]` to
the repository root depth.

### 3.6 Compatibility requirements for `src.observation_generator`

Any shim must preserve:

- importability of `from src.observation_generator import ...`;
- names `load_config`, `generate_observations`, `main`, `PROJECT_ROOT`, and
  `DAYS_PER_YEAR`;
- signatures `load_config(config_path)`, `generate_observations(config_path)`,
  and `main()`;
- `generate_observations()` return value `(observations, metadata)`;
- `--config` option, default value, help text, and exit behaviour;
- `python -m src.observation_generator --config ...` from the repository root;
- all output paths, columns, metadata, prints, and exception behaviour.

No in-repository test currently imports `src.observation_generator`. The two
observation-output validators read tracked files only:
`tests/test_observation_output.py` and `tests/test_all_observation_outputs.py`.
This is a coverage gap that the implementation checkpoint should close.

### 3.7 Can the old path be re-exported or invoked through a shim?

Yes. A thin shim can re-export the implementation and preserve the CLI. The
recommended shape is:

```python
"""Compatibility shim for the old ``src.observation_generator`` path."""

from orbit_discovery.component2_observations.generator import (
    DAYS_PER_YEAR,
    PROJECT_ROOT,
    generate_observations,
    load_config,
    main,
)

__all__ = [
    "DAYS_PER_YEAR",
    "PROJECT_ROOT",
    "generate_observations",
    "load_config",
    "main",
]

if __name__ == "__main__":
    main()
```

The shim contains no scientific logic, no duplicated formulas, no path policy,
and no extra CLI options. The package generator is the single implementation.

One compatibility nuance: the current direct-script command
`python src\observation_generator.py` fails. After the shim is installed, it
may start working because the shim imports the installed package instead of
`src.*`. That is an incidental improvement, not a requirement, and should not
be used as the primary acceptance gate. The documented `-m` form must be the
gate.

---

## 4. Configuration and path analysis

### 4.1 Component 2 configuration files

There are exactly three Component 2 configurations in `configs/`:

| File | `observation_name` | `input_trajectory` |
|---|---|---|
| `configs/synthetic_observations.json` | `synthetic_asteroid_observations` | `data/runs/synthetic_asteroid/trajectory.csv` |
| `configs/synthetic_observations_eccentric.json` | `synthetic_asteroid_eccentric_observations` | `data/runs/synthetic_asteroid_eccentric/trajectory.csv` |
| `configs/synthetic_observations_inclined.json` | `synthetic_asteroid_inclined_observations` | `data/runs/synthetic_asteroid_inclined/trajectory.csv` |

The other three files in `configs/` (`synthetic_asteroid*.json`) are Component 1
simulation configurations and are not read by the generator.

All three Component 2 configs share these values:

```json
{
  "observer": {
    "model": "idealized_circular",
    "orbital_radius_au": 1.0,
    "orbital_period_years": 1.0,
    "initial_phase_deg": 90.0
  },
  "coordinates": {
    "input_frame": "heliocentric_ecliptic",
    "output_frame": "equatorial",
    "obliquity_deg": 23.43928,
    "ra_unit": "degrees",
    "dec_unit": "degrees"
  },
  "observation_schedule": {
    "cadence_days": 7.0,
    "start_day": 0.0,
    "end_day": 1826.25
  },
  "measurement_noise": {
    "model": "gaussian",
    "sigma_ra_cosdec_arcsec": 0.5,
    "sigma_dec_arcsec": 0.5,
    "random_seed": 42
  },
  "output": {
    "directory": "data/observations",
    "save_noise_free_coordinates": true,
    "save_metadata": true
  }
}
```

Only the observation name and input trajectory differ. The configs are not
moved, renamed, or rewritten by the proposed migration.

### 4.2 Config structure and required keys

The generator reads these top-level keys:

```text
observation_name
input_trajectory
observer
coordinates
observation_schedule
measurement_noise
output
```

Nested keys actually consumed:

```text
observer.orbital_radius_au
observer.orbital_period_years
observer.initial_phase_deg

coordinates.obliquity_deg

observation_schedule.start_day
observation_schedule.end_day
observation_schedule.cadence_days

measurement_noise.sigma_ra_cosdec_arcsec
measurement_noise.sigma_dec_arcsec
measurement_noise.random_seed

output.directory
output.save_noise_free_coordinates
output.save_metadata
```

Nested keys copied into metadata but not used for dispatch:

```text
observer.model
coordinates.input_frame
coordinates.output_frame
coordinates.ra_unit
coordinates.dec_unit
measurement_noise.model
```

This is intentional current behaviour. In particular, changing
`observer.model` to another string would be silently accepted, and changing the
declared input/output frames would not alter the transform. The packaging move
must not start validating or dispatching on these values.

### 4.3 Config loading semantics

`load_config(config_path)`:

1. Converts `config_path` to `Path`.
2. If it is not absolute, joins it to `PROJECT_ROOT`.
3. If the resulting path does not exist, raises:

   ```text
   FileNotFoundError: Configuration file not found: <resolved path>
   ```

4. Opens the file with UTF-8 encoding.
5. Calls `json.load`.
6. Returns `(config, config_file)`.

It does not call `.resolve()` on the config path. This matters for metadata path
formatting: a config inside the repository is reported as a root-relative
string, while a config outside it is reported as an absolute string.

Verified read-only error behaviour:

| Input | Result |
|---|---|
| Missing absolute file | `FileNotFoundError: Configuration file not found: <path>` |
| Malformed JSON | `json.JSONDecodeError` with the standard JSON decoder message |
| Valid absolute JSON | Returns `dict` and the same absolute `Path` |

### 4.4 Default configuration selection

`main()` defines:

```python
parser.add_argument(
    "--config",
    default="configs/synthetic_observations.json",
    help="Path to observation configuration JSON.",
)
```

There is no environment-variable selection, no search path, and no alternate
default. The default is resolved against `PROJECT_ROOT`, so it currently works
from any working directory once the module can be imported.

### 4.5 Input trajectory resolution

```python
input_path = Path(config["input_trajectory"])

if not input_path.is_absolute():
    input_path = PROJECT_ROOT / input_path

trajectory = load_trajectory(input_path)
```

Consequences:

- relative trajectory paths resolve against `PROJECT_ROOT`, not the config
  file’s directory and not the process working directory;
- absolute paths are used unchanged;
- existence is not checked here; `load_trajectory` raises
  `FileNotFoundError: Trajectory file not found: <path>` if missing;
- the path is not `.resolve()`d, so lexical `..` components and symlinks are
  not canonicalised before loading;
- Component 1 `metadata.json` is not read; only the CSV columns are validated.

The tracked run metadata confirms the intended input frame and units
(`coordinate_frame: heliocentric_ecliptic`, position in AU, time in years), but
the generator does not verify those metadata fields.

### 4.6 Output directory resolution

```python
output_directory = Path(output_config["directory"])

if not output_directory.is_absolute():
    output_directory = PROJECT_ROOT / output_directory

observation_name = config["observation_name"]
output_directory = output_directory / observation_name
output_directory.mkdir(parents=True, exist_ok=True)

csv_path = output_directory / "observations.csv"
observations.to_csv(csv_path, index=False)
```

Consequences:

- default output root is `PROJECT_ROOT / "data/observations"`;
- the final directory is `.../data/observations/<observation_name>`;
- an absolute `output.directory` is used unchanged;
- the directory is created recursively, and existing directories are reused;
- filenames are exactly `observations.csv` and (when enabled)
  `metadata.json`;
- the output path is not `.resolve()`d and is not stored in metadata (only the
  basename `output_file: "observations.csv"` is stored);
- `save_metadata` controls only the metadata file, not the CSV.

### 4.7 Missing or malformed configuration values

Because there is no schema validation, the failure mode depends on where the
missing value is first used:

| Condition | Likely result |
|---|---|
| Missing config file | `FileNotFoundError` from `load_config` |
| Invalid JSON | `json.JSONDecodeError` |
| Missing top-level key | `KeyError` when indexed |
| Missing nested key | `KeyError` when indexed |
| Non-numeric schedule/observer/noise values | `TypeError` or helper `ValueError` |
| `cadence_days <= 0` | `ValueError: Cadence must be greater than zero.` |
| `end_day <= start_day` | `ValueError: End day must be greater than start day.` |
| Schedule outside trajectory range | `ValueError: Start day is outside trajectory range.` or `ValueError: End day is outside trajectory range.` |
| Missing/invalid trajectory file | `FileNotFoundError` or `ValueError` from `load_trajectory` |
| Invalid observer radius/period | `ValueError` from `calculate_observer_positions` |
| Negative noise sigma | `ValueError: Noise uncertainties cannot be negative.` |
| `save_noise_free_coordinates` absent | `KeyError` |
| `save_metadata` absent | `KeyError` |

These behaviours are not changed by packaging. Adding validation or defaults
would be a separate, behaviour-changing decision.

### 4.8 `core.paths` integration assessment (not integrated)

The approved path policy in `orbit_discovery.core.paths` is:

1. explicit project root;
2. `ORBIT_DISCOVERY_ROOT`;
3. nearest ancestor containing `pyproject.toml`.

The current generator implements a fourth, narrower policy: a source-file
relative root (`Path(__file__).resolve().parents[1]`), with no environment or
marker discovery.

A naive move of the file to
`src/orbit_discovery/component2_observations/generator.py` would make
`parents[1]` equal to `src/orbit_discovery`, not the repository root. That would
break every relative config/input/output path and change metadata path
formatting. The correct pure-move expression is:

```python
PROJECT_ROOT = Path(__file__).resolve().parents[3]
```

because:

```text
.../src/orbit_discovery/component2_observations/generator.py
parents[0] = component2_observations
parents[1] = orbit_discovery
parents[2] = src
parents[3] = repository root
```

#### Exact integration changes to consider later

| Current code | Potential `core.paths` use | Risk |
|---|---|---|
| `PROJECT_ROOT` constant | `resolve_project_root(project_root=...)` or `resolve_project_root(search_from=Path(__file__))` | Env and marker discovery can select a different root; wheel installs may not contain `pyproject.toml`; explicit-root precedence needs an API/CLI decision |
| `load_config` relative join | `resolve_config_path(config_path, root)` | `.resolve()` canonicalises `..`, symlinks, and case; metadata path strings can change |
| input trajectory relative join | `resolve_config_path` or a generic resolver | Same canonicalisation; metadata `input_trajectory` string can change |
| output directory relative join | `resolve_output_root(output_root, project_root)` | `.resolve()` may change the actual output directory; `None` would default to root, which differs from the required `output.directory` key |
| metadata relative strings | keep `relative_to(root)` / absolute fallback | Must not normalise separators or change Windows backslash output |

#### Why integration should wait

- `resolve_project_root()` honours `ORBIT_DISCOVERY_ROOT`. If that variable is
  set in a developer shell, existing configs would resolve from a different
  root and could read or write outside the repository.
- Marker discovery from the generator file works in the editable checkout but
  is not guaranteed for a future wheel installation.
- `.resolve()` changes lexical path identities. The current metadata records
  `str(path.relative_to(PROJECT_ROOT))` without resolving, and the current
  output directory is not resolved. Preserving exact metadata strings is easier
  before path-policy integration.
- The current `generate_observations(config_path)` signature has no
  `project_root` parameter. Adding one is an API change that needs approval.

**Recommendation:** perform the pure packaging move with an explicit
source-root expression first. Defer `core.paths` integration to a separate
checkpoint that adds an explicit root parameter, tests environment and marker
precedence, and proves that the default source-checkout behaviour is unchanged.

---

## 5. Scientific and output invariants

### 5.1 Observation cadence and time range

- Schedule values come from the config; all three current configs use
  `start_day = 0.0`, `end_day = 1826.25`, `cadence_days = 7.0`.
- `generate_observation_times` uses `np.arange(start_day, end_day, cadence_days)`
  and appends `end_day` when the last cadence step is not within `atol=1e-9`.
- Result: 261 cadence samples from 0 through 1820 days plus 1826.25 days = 262
  observations. The final interval is 6.25 days, not 7 days.
- `time_years = observation_times_days / DAYS_PER_YEAR`, with
  `DAYS_PER_YEAR = 365.25`.
- Endpoint inclusion and the short final interval must remain unchanged.

### 5.2 Interpolation

- `np.interp` is applied independently to the x, y, and z position columns.
- Interpolation is linear.
- Observation times must lie within the ground-truth time range; no
  extrapolation is permitted.
- Ground-truth timestamps must be strictly increasing and positions must be
  finite `(N, 3)`.
- The helper returns `(M, 3)` in the same row order as the observation times.

### 5.3 Observer model

- Idealised circular observer in the heliocentric ecliptic plane.
- Angle: `2π * time_years / orbital_period_years + initial_phase_deg`.
- Position: `(R cos θ, R sin θ, 0)`.
- Current configs use `R = 1.0 AU`, `T = 1.0 year`, `φ = 90°`, so the initial
  position is `(0, 1, 0)` AU.
- No Earth ephemeris, eccentricity, inclination, light-time, aberration,
  precession, nutation, or topocentric correction is present.
- `observer.model` is recorded in metadata but not dispatched.

### 5.4 Relative position

- `relative_positions = asteroid_positions - observer_positions`.
- Shape `(N, 3)`; both inputs must match in shape and be finite.
- This is the observer-to-asteroid vector, ignoring light-time.
- No range column or additional geometry output is produced.

### 5.5 Coordinate transformation and obliquity

- Fixed rotation about the x-axis from ecliptic to equatorial coordinates:

  ```text
  x_eq = x
  y_eq = y cos ε - z sin ε
  z_eq = y sin ε + z cos ε
  ```

- `ε = coordinates.obliquity_deg`; current value `23.43928°`.
- The helper default is also `23.43928`, but the generator passes the config
  value explicitly.
- No epoch-dependent obliquity, precession, or nutation.
- `coordinates.input_frame` and `coordinates.output_frame` are not used to
  select or validate the transform.

### 5.6 RA/Dec calculation

- `RA = atan2(y, x)`, wrapped with `mod 360` into `[0, 360)`.
- `Dec = atan2(z, sqrt(x² + y²))` in `[-90, 90]`.
- Zero vectors raise `ValueError: Cannot calculate coordinates for zero
  vectors.`
- Shape and finiteness are validated.
- RA wrap-around is handled by the modulo operation, not by unwrapping.

### 5.7 Noise model and random seed

- `numpy.random.default_rng(random_seed)`.
- Independent normal draws for RA and Dec, in that order.
- `sigma_ra_cosdec_arcsec` is interpreted as the tangent-plane
  `σ_RA cos(Dec)`; the code divides by `cos(Dec)` to obtain the coordinate RA
  offset.
- `sigma_dec_arcsec` is applied directly to Dec.
- Arcseconds are converted to degrees with `ARCSEC_TO_DEG = 1/3600`.
- Noisy RA is wrapped into `[0, 360)`.
- Declinations at the poles or outside `[-90, 90]` after noise raise
  `ValueError`.
- The same seed and the same array shape reproduce the same noise sequence.
  The seed is per-call; there is no global RNG state reuse.
- All three current configs use seed `42` and `0.5` arcsec for both axes.
- Actual noise realisations are not written to the CSV; only the two sigma
  columns are written.

### 5.8 CSV columns, order, and types

When `save_noise_free_coordinates` is true (all current configs), the header is
exactly:

```text
time_years,time_days,ra_deg,dec_deg,sigma_ra_cosdec_arcsec,sigma_dec_arcsec,true_ra_deg,true_dec_deg
```

Column order and meaning:

| Column | Type | Meaning |
|---|---|---|
| `time_years` | float | Observation time in years, derived by dividing days by `365.25` |
| `time_days` | float | Observation time in elapsed simulation days |
| `ra_deg` | float | Noisy right ascension in degrees, `[0, 360)` |
| `dec_deg` | float | Noisy declination in degrees, `[-90, 90]` |
| `sigma_ra_cosdec_arcsec` | float | Configured RA tangent-plane uncertainty in arcseconds, constant |
| `sigma_dec_arcsec` | float | Configured Dec uncertainty in arcseconds, constant |
| `true_ra_deg` | float | Noise-free right ascension in degrees |
| `true_dec_deg` | float | Noise-free declination in degrees |

When `save_noise_free_coordinates` is false, only the first six columns are
written. The truth columns are not moved to a separate file in this checkpoint.

All three tracked datasets contain 262 rows and the eight columns above.
`to_csv(..., index=False)` is used; row order is the observation-time order.

### 5.9 Metadata keys and meanings

The metadata dictionary is constructed in this exact insertion order:

| Key | Value / meaning |
|---|---|
| `observation_name` | Config value |
| `input_trajectory` | Input path as a root-relative string when inside `PROJECT_ROOT`, otherwise an absolute string |
| `configuration_file` | Config path as a root-relative string when inside `PROJECT_ROOT`, otherwise an absolute string |
| `state_type` | Literal `"synthetic_observations"` |
| `number_of_observations` | `len(observation_times_days)` |
| `observation_schedule` | The config’s schedule dictionary, unchanged |
| `observer` | The config’s observer dictionary, unchanged |
| `coordinates` | The config’s coordinates dictionary, unchanged |
| `measurement_noise` | The config’s noise dictionary, unchanged |
| `coordinate_units` | Literal dictionary described below |
| `assumptions` | Literal list described below |
| `output_file` | Literal `"observations.csv"` |

`coordinate_units` is:

```json
{
  "time": "days and years",
  "right_ascension": "degrees",
  "declination": "degrees",
  "angular_uncertainty": "arcseconds",
  "distance": "AU"
}
```

`assumptions` is, in order:

```text
Idealized circular Earth-like observer orbit
Observer orbit lies in the heliocentric ecliptic plane
Asteroid positions are interpolated from simulated ground truth
Ecliptic coordinates are rotated using the configured obliquity
Gaussian angular measurement noise is applied
Observation times are elapsed simulation times, not real calendar dates
```

The metadata does **not** include the `output` config section, the output
directory, the save-flag values, input metadata, versions, timestamps, hashes,
or a schema version. It is written with:

```python
with open(metadata_path, "w", encoding="utf-8") as file:
    json.dump(metadata, file, indent=4)
```

No `sort_keys`, no custom separators, and no explicit trailing newline are
added.

### 5.10 Optional outputs

| Config flag | Effect |
|---|---|
| `output.save_noise_free_coordinates = true` | Append `true_ra_deg` and `true_dec_deg` to the CSV |
| `output.save_noise_free_coordinates = false` | Write only the six measurement columns; no truth file is created |
| `output.save_metadata = true` | Write `<output dir>/metadata.json` |
| `output.save_metadata = false` | Do not write metadata, but still return the metadata dictionary from `generate_observations()` |

### 5.11 Truth columns

The current outputs deliberately include `true_ra_deg` and `true_dec_deg` in
`observations.csv`. This is a known ground-truth leakage concern recorded
elsewhere in the repository documentation, but removing or relocating those
columns is explicitly out of scope here. The migration must leave them
untouched.

### 5.12 Exact regression checks needed

A packaging-equivalent migration should prove:

1. **Columns and order** — exact header list, including optional truth columns.
2. **Row count** — 262 for each current config.
3. **Time grid** — first value `0.0`, last value `1826.25`, monotonic and
   unique, and `time_days == time_years * 365.25` within the established
   tolerance.
4. **Numeric equivalence** — every CSV numeric value identical to the
   pre-migration/reference output.
5. **Coordinate ranges** — RA in `[0, 360)`, Dec in `[-90, 90]`.
6. **Noise reproducibility** — same residuals for the same seed and shape.
7. **Metadata equivalence** — same keys, order, values, assumptions, and path
   formatting; no added or removed keys.
8. **Output layout** — same directory name and filenames.
9. **Toggle behaviour** — truth-free and metadata-free variants.
10. **Print output** — loader and generator messages unchanged.
11. **Error behaviour** — same exception types and messages for missing and
    malformed inputs.
12. **CLI and imports** — old module import, shim identity, and help output.

---

## 6. Proposed package migration

### 6.1 Mapping

| Current path | Proposed path | Action |
|---|---|---|
| `src/observation_generator.py` | `src/orbit_discovery/component2_observations/generator.py` | Move orchestration implementation; update imports and root depth |
| `src/observation_generator.py` | same old path | Replace with a thin compatibility shim |
| `src/orbit_discovery/component2_observations/__init__.py` | unchanged | Keep minimal; no eager re-exports |
| `configs/synthetic_observations*.json` | unchanged | Do not move or rewrite |
| `src/compare_observation_datasets.py` | unchanged | Not part of this checkpoint |
| `src/orbit_discovery/cli/` | unchanged | Do not create a command yet |

### 6.2 Incremental sequence

#### Phase A — preconditions and baseline capture

1. Confirm the editable installation:
   `pip show orbit-discovery`, `pip check`.
2. Confirm the existing focused Component 2 tests and read-only validators
   pass before any move.
3. Record the current generator help output, module import result, and
   reference hashes/checksums for the three tracked observation CSV and
   metadata files **without regenerating them**.
4. Confirm no environment variable such as `ORBIT_DISCOVERY_ROOT` is set that
   would change path resolution later.

#### Phase B — pure packaging move

1. Create `component2_observations/generator.py` by moving the implementation
   without changing its pipeline, comments, DataFrame construction, metadata
   construction, prints, or error propagation.
2. Replace the five `src.*` helper imports with the corresponding
   `orbit_discovery.component2_observations.*` imports.
3. Correct `PROJECT_ROOT` to the repository-root depth
   (`parents[3]`) or an equivalent explicit source-root expression. Do not
   change the relative/absolute semantics of config, input, or output paths.
4. If approved, replace the local `DAYS_PER_YEAR = 365.25` definition with
   `from orbit_discovery.core.constants import DAYS_PER_YEAR`. This is a
   numerically exact substitution; preserve the module attribute.
5. Keep `load_config`, `generate_observations`, `main`, and the
   `if __name__ == "__main__"` guard.
6. Keep the CLI parser exactly as-is: same `--config` option, default, help
   text, and description. Do not add `--project-root`, positional arguments,
   subcommands, or console-script registration.

#### Phase C — compatibility shim

1. Replace `src/observation_generator.py` with the thin shim shown in
   Section 3.7.
2. Re-export the public names explicitly; do not use `import *`.
3. Retain the `__main__` forwarder so `python -m src.observation_generator`
   continues to work.
4. Do not add a deprecation warning in this checkpoint.

#### Phase D — validation without regenerating tracked datasets

1. Run import and CLI-help checks.
2. Run new focused tests using temporary directories and temporary configs.
3. Run the existing read-only Component 2 tests and output validators.
4. Compare temporary generated output against the tracked reference data.
5. Run `pip check` and `git diff --check`.
6. Confirm no changes under `configs/`, `data/`, `results/`, or `plots/`.

#### Phase E — later, separate checkpoint

Only after this packaging move is accepted:

- add a CLI module (`cli/observe.py`) with argument parsing only;
- add an installed console entry point;
- add explicit project-root selection and integrate `core.paths`;
- consider metadata improvements and truth-column separation as separate
  scientific/data-contract changes.

### 6.3 What is pure packaging and what is later

**Pure packaging (this migration):**

- moving the implementation;
- changing imports from `src.*` to package modules;
- correcting the file-relative project-root depth;
- optional exact replacement of the local year constant with the shared
  constant;
- adding the compatibility shim;
- adding equivalence tests.

**Later, separate decisions:**

- any new CLI command or entry point;
- `core.paths` environment/marker/explicit-root integration;
- config schema validation or defaults;
- metadata additions or normalisation;
- truth-column removal or separation;
- changes to the observer, coordinate, interpolation, or noise models.

### 6.4 Non-actions

The migration must not:

- modify `configs/`;
- modify `data/`, `results/`, or `plots/`;
- modify Component 1;
- modify the five helper implementations or their migrations;
- add a new CLI command or package entry point;
- change `pyproject.toml`;
- commit, tag, or push.

---

## 7. Compatibility strategy

### 7.1 Shim identity

The old path should reference the same objects as the new module, not a copied
implementation. Focused tests should assert:

```python
import src.observation_generator as old
import orbit_discovery.component2_observations.generator as new

assert old.generate_observations is new.generate_observations
assert old.load_config is new.load_config
assert old.main is new.main
assert old.PROJECT_ROOT == new.PROJECT_ROOT
assert old.DAYS_PER_YEAR == new.DAYS_PER_YEAR
```

### 7.2 CLI preservation

The old command must remain:

```powershell
.\.venv\Scripts\python.exe -m src.observation_generator `
    --config configs\synthetic_observations.json
```

The help output must contain the same description, `--config` option, and
default. `main()` must remain callable with no arguments and must not require a
project-root argument.

### 7.3 Direct-script execution

Current direct execution fails with `ModuleNotFoundError`. The shim may make it
work accidentally because the package is installed. This should be documented
and tested only if the reviewer wants it as an additional improvement. The
module form is the compatibility gate.

### 7.4 Source checkout versus installed package

The five helper shims already require the editable installation (or a
repository-root `sys.path`). The generator shim will have the same requirement.
This is an inherited environment condition, not a new generator-specific
dependency.

If the editable installation is absent, `python -m src.observation_generator`
will fail while importing the package generator. That is equivalent in effect
to today’s requirement that the repository root be importable, but the failure
message changes. The acceptance check must therefore either:

- confirm the editable installation is present, as it is now; or
- document that the old module form requires it.

### 7.5 No new CLI command

No `orbit-observe`, `cli/observe.py`, `[project.scripts]` entry, or other new
command is created in this checkpoint. The existing `--config` interface is
preserved unchanged.

---

## 8. Test and regression plan

### 8.1 Import and CLI validation

| Check | Expected result |
|---|---|
| `import orbit_discovery.component2_observations.generator` | Succeeds; no prints or writes |
| `import src.observation_generator` | Succeeds; no prints or writes |
| Old/new public functions are identical objects | Pass |
| `inspect.signature` for the three functions | Unchanged |
| `python -m src.observation_generator --help` from repository root | Exit `0`; same usage text |
| `python -m src.observation_generator --help` with repository root on `PYTHONPATH` from another directory | Exit `0` (environment-dependent, optional) |
| `pip check` | `No broken requirements found.` |

### 8.2 Temporary-fixture output equivalence

All generation tests must write only under a `tempfile.TemporaryDirectory()`.
They must never write into the repository.

Suggested fixture construction:

1. Copy one tracked Component 1 trajectory CSV into the temporary directory, or
   create a small valid trajectory CSV with the required eight columns.
2. Write a temporary observation config with:
   - an absolute `input_trajectory` pointing at the temporary trajectory;
   - the same observer, coordinates, schedule, and noise values as the tracked
     config;
   - an absolute `output.directory` pointing into the temporary directory;
   - `save_noise_free_coordinates` and `save_metadata` set for the case under
     test.
3. Call `generate_observations(temp_config)` directly.
4. Compare the generated CSV against the tracked reference CSV for the same
   scenario. Because the move is intended to be numerically exact, use exact
   DataFrame equality (`check_exact=True`) for values and exact column order.
5. Alternatively, compare the pre-migration implementation (loaded from Git or a
   temporary saved copy) and the new implementation on the same temporary
   config. This avoids reliance on tracked reference files but requires saving
   the old source outside the repository or loading it from Git.

Checks:

- exact CSV columns and order;
- exact row count and time grid;
- exact `ra_deg`, `dec_deg`, `true_ra_deg`, `true_dec_deg`, and sigma values;
- no extra index column;
- no writes outside the temporary output directory;
- first and last observation times unchanged.

### 8.3 Metadata equivalence

For the same path context, compare the complete metadata dictionary:

- key set and insertion order;
- `observation_name`, `state_type`, `number_of_observations`;
- full `observation_schedule`, `observer`, `coordinates`, and
  `measurement_noise` objects;
- `coordinate_units` and `assumptions` exact values and order;
- `output_file`;
- `input_trajectory` and `configuration_file` path strings.

When the config and trajectory are in a temporary directory, the two path
fields are absolute strings. To test relative path formatting, patch the
generator’s `PROJECT_ROOT` to a temporary project root in a unit test and place
the temp config, trajectory, and output beneath it. Then expect
`str(path.relative_to(temp_root))` with host separators (backslashes on
Windows). Do not normalise separators in the implementation.

Also compare the raw `json.dumps(metadata, indent=4)` text when path values are
identical; this catches key-order, indentation, and escaping changes.

### 8.4 Toggle and error tests

| Case | Expected |
|---|---|
| `save_noise_free_coordinates: false` | Six columns only; no truth columns |
| `save_metadata: false` | No `metadata.json`; returned metadata still exists |
| Missing config file | Same `FileNotFoundError` message |
| Malformed JSON | Same decoder exception type |
| Missing trajectory | Same loader `FileNotFoundError` |
| Invalid cadence/range | Same helper `ValueError` messages |
| Invalid observer radius/period | Same helper `ValueError` messages |
| Negative noise sigma | Same helper `ValueError` message |
| Missing top-level/nested key | Same `KeyError` behaviour |
| Output directory absent | Created recursively |
| Existing output directory | Reused without error |

### 8.5 Existing read-only checks

The implementation checkpoint should rerun, without regenerating data:

```powershell
& .venv\Scripts\python.exe tests\test_component2_loader.py
& .venv\Scripts\python.exe tests\test_component2_schedule.py
& .venv\Scripts\python.exe tests\test_component2_observer.py
& .venv\Scripts\python.exe tests\test_component2_frames.py
& .venv\Scripts\python.exe tests\test_component2_noise.py
& .venv\Scripts\python.exe tests\test_observation_output.py
& .venv\Scripts\python.exe tests\test_all_observation_outputs.py
```

The last two validate the tracked reference files and should remain unchanged.
They do not exercise the generator.

### 8.6 What cannot be validated without running the generator

The following cannot be proven by import or static inspection alone:

- exact numeric CSV values after the move;
- metadata path strings and JSON bytes;
- the success summary and first-observation print block;
- output toggle behaviour;
- directory creation and file writing;
- success exit code `0` and uncaught-exception exit code `1`;
- any accidental change in RNG order or pandas formatting.

These must be tested by running the generator only against temporary fixtures,
as described above. They must not be tested by regenerating the tracked
datasets. The assessment itself did not run generation.

---

## 9. Risks and rollback

### 9.1 Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Naive copy keeps `parents[1]`, so `PROJECT_ROOT` points at `src/orbit_discovery` | High if unaddressed | Config/input/output paths break; metadata paths become absolute or wrong | Use `parents[3]` or an explicit source-root expression; test default config resolution |
| Shim imports package but editable install is absent | Medium in a plain checkout | Old `-m` command fails with `ModuleNotFoundError: orbit_discovery` | Confirm editable install; document requirement; keep package shim pattern consistent with earlier C3 migrations |
| Package module imports create a second implementation or drift | Low | Old/new behaviour diverges | Shim re-exports only; no duplicated logic |
| `core.paths` integration changes environment/marker resolution | High if mixed into this move | Existing configs may read/write elsewhere; metadata strings change | Defer integration; use explicit source root now |
| Metadata path formatting changes due to `.resolve()` or separator normalisation | Medium | Output-equivalence failure; tracked metadata mismatch | Preserve `relative_to`/absolute fallback and host separators; compare JSON exactly |
| CSV formatting changes (column order, float formatting, index) | Low if code is moved verbatim | Dataset mismatch | Keep DataFrame construction and `to_csv(index=False)` unchanged; exact DataFrame comparison |
| RNG order or seed semantics change | Low | Noise values differ | Keep `default_rng`, RA-then-Dec draw order, and one call per generation |
| Truth columns removed or altered | Low if out of scope | Existing validators and consumers break | Explicitly preserve `true_ra_deg`/`true_dec_deg` |
| CLI help or default changes | Medium if parser is refactored | Documented command changes | Move `main()` unchanged; compare help output |
| Direct-script behaviour changes unexpectedly | Low | Not a documented command | Do not use as acceptance gate; document observed behaviour |
| Output writes during validation touch tracked data | Medium if tests use real configs | Datasets/results modified | Use temp configs and absolute temp output; assert `git diff --name-only -- data configs results plots` is empty |

### 9.2 Rollback conditions

Roll back the generator migration if any of the following occurs:

- any CSV column, column order, row count, time value, RA/Dec value, sigma
  value, or truth value differs from the reference;
- any metadata key, value, order, path string, or JSON formatting differs;
- the old module import or `python -m src.observation_generator --help` fails;
- the default config no longer resolves to the tracked trajectory;
- output paths differ for an existing config;
- the noise sequence changes for the same seed and shape;
- the generator writes outside the intended output directory in a test;
- an import-time side effect appears;
- the change requires altering configs, data, results, plots, Component 1, or
  dependencies to pass.

### 9.3 Rollback procedure for the future implementation checkpoint

If the move must be reverted:

```powershell
git restore src/observation_generator.py
Remove-Item src\orbit_discovery\component2_observations\generator.py
Remove-Item tests\test_component2_generator.py
```

Do not revert the earlier schedule, observer, frames, noise, or loader
migrations. No data rollback is needed because the migration tests write only
to temporary directories. No rollback was performed during this assessment.

---

## 10. Decisions requiring approval

| ID | Decision | Recommendation |
|---|---|---|
| D-01 | Confirm destination module name and path `component2_observations/generator.py` | Approve as proposed |
| D-02 | Move `main()` and the `if __name__ == "__main__"` guard into the package generator, or leave CLI wiring only in the shim | Move the implementation and re-export it; keep the shim guard so the old `-m` form works |
| D-03 | Replace the local `DAYS_PER_YEAR = 365.25` with `orbit_discovery.core.constants.DAYS_PER_YEAR` now | Approve; numerically exact and consistent with the loader/noise migrations |
| D-04 | Use `Path(__file__).resolve().parents[3]` as the pure-move root, or integrate `core.paths` immediately | Use the source-root expression now; defer `core.paths` to a separate checkpoint |
| D-05 | Which names the shim re-exports | Re-export `load_config`, `generate_observations`, `main`, `PROJECT_ROOT`, and `DAYS_PER_YEAR` |
| D-06 | Whether to require direct-script `--help` as an acceptance criterion | Do not require it; the current direct form fails and the documented module form is the compatibility gate |
| D-07 | Whether to add a new `tests/test_component2_generator.py` using `unittest` and temporary fixtures | Approve; this closes the current gap where no test imports the generator |
| D-08 | Whether to preserve truth columns and the existing metadata schema exactly | Approve; no truth-column or metadata changes in this checkpoint |
| D-09 | Whether to add `--project-root`, a new CLI module, or a console entry point | Defer to a later checkpoint; do not add in this one |
| D-10 | Whether to update `README.md` or `CHANGELOG.md` as part of the move | Defer documentation/entry-point wording until the implementation and later CLI checkpoint |

---

## Appendix A — Verified read-only observations

The following were inspected or probed during this assessment:

- complete `src/observation_generator.py`;
- the five package helper modules and the five old shims;
- the three Component 2 configs;
- the three tracked observation CSV headers and row counts (262 rows each);
- the three tracked metadata key sets;
- one full tracked metadata example;
- the Component 1 trajectory metadata example (not read by the generator);
- `tests/test_observation_output.py`, `tests/test_all_observation_outputs.py`,
  `tests/test_component2_loader.py`, and `tests/test_core_paths.py`;
- the existing Phase 1 reports and the documented `core.paths` policy;
- current Git status and diff scope.

No observation generation, dataset regeneration, result generation, plot
generation, source modification, test modification, configuration
modification, dependency change, commit, tag, or push was performed.

## Appendix B — Git status at report creation

```text
 M src/coordinate_converter.py
 M src/measurement_noise.py
 M src/observation_schedule.py
 M src/observer_model.py
 M src/trajectory_loader.py
?? docs/development/PHASE_1_STEP_1_ASSESSMENT.md
?? docs/development/PHASE_1_STEP_2_CORE_ASSESSMENT.md
?? docs/development/PHASE_1_STEP_3_2_1_INSTALL_ASSESSMENT.md
?? docs/development/PHASE_1_STEP_3_2_2_INSTALL_VALIDATION.md
?? docs/development/PHASE_1_STEP_3_2_3_SCHEDULE_OBSERVER_MIGRATION.md
?? docs/development/PHASE_1_STEP_3_3_1_FRAMES_NOISE_MIGRATION.md
?? docs/development/PHASE_1_STEP_3_4_1_LOADER_MIGRATION.md
?? docs/development/PHASE_1_STEP_3_5_1_GENERATOR_ASSESSMENT.md
?? docs/development/PHASE_1_STEP_3_COMPONENT2_ASSESSMENT.md
?? pyproject.toml
?? src/orbit_discovery/
?? tests/test_component2_frames.py
?? tests/test_component2_loader.py
?? tests/test_component2_noise.py
?? tests/test_component2_observer.py
?? tests/test_component2_schedule.py
?? tests/test_core_constants.py
?? tests/test_core_paths.py
```

The only change introduced by this checkpoint is the new untracked assessment
document. The five tracked shim modifications and the other untracked package,
test, and documentation files are inherited from the earlier C3 work.

`git diff --name-only -- data configs results plots` is empty.
`git diff --check` reports no whitespace errors. No source, test,
configuration, dependency, dataset, result, or plot file was modified by this
assessment.
