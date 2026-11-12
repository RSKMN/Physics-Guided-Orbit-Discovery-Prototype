# Phase 1 — Step 3.1: Component 2 Pure Modules Migration Assessment

**Project:** Physics-Guided Orbit Discovery Prototype  
**Version:** 0.2.0  
**Branch:** `main`  
**Baseline commit:** `d02023d9820fd2b1a58731345d5d66384adad120`  
**Assessment date:** 2026-11-12  
**Mode:** read-only assessment  
**Status:** assessment complete; C3 has not been implemented

This report assesses moving the five independent Component 2 helper modules into
`src/orbit_discovery/component2_observations/`. It follows the approved Phase 1
boundaries in `docs/development/PHASE_1_STEP_1_ASSESSMENT.md` (including the
architecture addendum) and the core decisions in
`docs/development/PHASE_1_STEP_2_CORE_ASSESSMENT.md`.

The only file created by this checkpoint is this report. No source module, test,
configuration, dataset, result, plot or other documentation file was modified.
No package module, compatibility shim or directory was created. No dependency
was installed. No simulation, observation-generation or other writing workflow
was run. No commit, tag or push was performed.

---

## Executive summary

The five modules are a good migration candidate. Each is a small, self-contained
scientific helper with no project-internal imports, no configuration loading, no
project-root logic and no import-time side effects. The orchestration module
imports them; none of them imports the orchestration module or another Component 2
helper. The functions are deterministic given their inputs (apart from the
explicitly seeded noise RNG), so an old-versus-new equivalence test can be exact.

The main findings are:

1. **The proposed mapping is technically sound, except for one naming conflict.**
   `coordinate_converter.py` is proposed as `geometry.py` in this checkpoint and
   in `REFACTORING_PLAN.md`, but the Step 1 and Step 2 assessments and the
   `CODEBASE_ANALYSIS.md` target tree call the same destination `frames.py`. A
   name must be approved before any import path depends on it.

2. **The shim strategy is blocked by the current environment unless a decision is
   made.** `orbit_discovery` is not installed and is not importable from the
   repository root in the current `.venv`; only `src.orbit_discovery` is
   importable through the `src` namespace package. Naive shims that import
   `orbit_discovery.*` would break the currently documented
   `python -m src.observation_generator` command and all old `src.*` test imports
   in a plain source checkout. The choices are an editable install, an approved
   shim path bootstrap, or shims that import `src.orbit_discovery.*` with
   relative imports inside the package.

3. **Only two shared-constant substitutions are justified in C3.**
   `trajectory_loader.py` can use `DAYS_PER_YEAR`, and `measurement_noise.py` can
   import `ARCSEC_TO_DEG`. The remaining three modules have no occurrence of
   either constant. `OBLIQUITY_DEG` must remain local to the frame module.

4. **Existing tests are smoke/characterisation scripts, not a migration oracle.**
   The loader and schedule tests contain no assertions; the other three assert
   only happy-path ranges, shapes and one reproducibility property. They depend
   on tracked data and often on the working directory. C3 should add focused,
   hermetic characterisation tests in addition to running the existing scripts
   unchanged.

5. **A three-checkpoint implementation sequence is recommended:**
   `schedule` + `observer`, then `frames` (or `geometry`) + `noise`, then
   `loader`. Each checkpoint creates the package module, replaces the old path
   with a thin shim, and verifies old/new equivalence and tracked-data integrity.

No scientific improvement, contract change, truth separation, configuration
loader, metadata writer, CLI or Component 1 work belongs in C3.

---

## 1. Scope, inputs and method

### 1.1 Documents reviewed

- `docs/development/PHASE_1_STEP_1_ASSESSMENT.md`
- `docs/development/PHASE_1_STEP_2_CORE_ASSESSMENT.md`
- `docs/development/REFACTORING_PLAN.md`
- `docs/development/CODEBASE_ANALYSIS.md`
- `pyproject.toml`

### 1.2 Code and data reviewed

Source modules:

- `src/trajectory_loader.py`
- `src/observation_schedule.py`
- `src/observer_model.py`
- `src/coordinate_converter.py`
- `src/measurement_noise.py`
- `src/observation_generator.py` (caller only)
- `src/compare_observation_datasets.py` (duplicated diagnostics only)
- `src/configurable_simulator.py` (constant context only)

Tests:

- `tests/test_trajectory_loader.py`
- `tests/test_observation_schedule.py`
- `tests/test_observer_model.py`
- `tests/test_coordinate_converter.py`
- `tests/test_measurement_noise.py`
- `tests/test_observation_output.py`
- `tests/test_all_observation_outputs.py`
- `tests/validate_ground_truth.py`
- `tests/validate_baseline.py`
- `tests/check_configurable_runs.py`

Configuration:

- all six `configs/*.json` files

### 1.3 Method

The assessment used source inspection, an AST-only pass to extract imports,
assignments and function signatures, repository-wide searches for callers and
duplicated constants, and read-only import/help probes. No module was imported for
scientific work and no data-writing command was run.

Safe probes established the current import state:

```text
importlib.util.find_spec("orbit_discovery")  -> None
import src.orbit_discovery                    -> OK
"src" on sys.path                             -> False
python -m src.observation_generator --help    -> OK (read-only argparse)
```

`src` is an implicit namespace package. Its resolved path includes the project
`src` directory and the REBOUND `site-packages/src` header directory, as already
recorded in the Step 1 assessment. No `src/__init__.py` exists.

---

## 2. Module-by-module analysis

### 2.1 `src/trajectory_loader.py`

**Role:** Load and validate a modern ground-truth trajectory CSV, then return
time, position and velocity arrays.

**Public API**

```python
REQUIRED_COLUMNS = [
    "time_years",
    "time_days",
    "x_au",
    "y_au",
    "z_au",
    "vx_au_per_year",
    "vy_au_per_year",
    "vz_au_per_year",
]

def load_trajectory(csv_path):
    ...
```

There are no type annotations, return annotations, classes, CLI entry point or
`if __name__ == "__main__"` block.

**Imports and dependencies**

```python
import numpy as np
import pandas as pd
from pathlib import Path
```

Only the standard library and already-declared third-party packages are used.
There are no project imports, no `orbit_discovery` imports and no `src.*`
imports.

**Path and configuration dependencies**

- The only path input is `csv_path`, accepted as a string or path-like value and
  converted with `Path(csv_path)`.
- A relative `csv_path` is resolved by Pandas against the process working
  directory. The function does not resolve it against a project root.
- The orchestrator (`observation_generator.py`) resolves the configured
  `input_trajectory` against its own `PROJECT_ROOT` before calling the loader.
- The loader does not read `metadata.json`, does not read any configuration and
  does not use `ORBIT_DISCOVERY_ROOT` or `core.paths`.

**Callers**

- `src/observation_generator.py` lines 9 and 62.
- `tests/test_trajectory_loader.py` line 9.
- Indirectly through the pipeline in `tests/test_observation_schedule.py`,
  `tests/test_observer_model.py`, `tests/test_coordinate_converter.py` and
  `tests/test_measurement_noise.py`.
- `tests/validate_ground_truth.py` reimplements a subset of the loader checks
  but does not import the module.

No other source module imports it.

**Existing tests and coverage**

- `tests/test_trajectory_loader.py` is a smoke script. It imports the loader with
  `from src.trajectory_loader import load_trajectory`, passes the CWD-relative
  path `data/runs/synthetic_asteroid/trajectory.csv`, and prints array shapes and
  first/last positions. It contains no assertions and no error-path checks.
- The four pipeline tests above exercise the happy path indirectly.
- No test covers missing columns, non-numeric values, NaN/infinite values, fewer
  than two rows, non-increasing timestamps or inconsistent time columns.
- The test is CWD-sensitive and fails outside the repository root, as recorded in
  the Step 1 assessment.

**Independence from orchestration**

Genuinely independent. It has no imports from the orchestrator or from the other
four helpers, and it exposes no mutable module state other than
`REQUIRED_COLUMNS`.

**Migration risks**

- Pandas parsing and dtype/coercion behaviour must not change.
- `REQUIRED_COLUMNS` order and contents are part of the effective contract.
- Error types and exact messages must be preserved.
- The progress `print()` calls are observable behaviour; removing them would
  change console output even though it would not change science.
- The time-consistency tolerance (`rtol=0`, `atol=1e-6`) must not be tightened or
  loosened while migrating.
- Keeping the relative-path handling in the caller preserves current behaviour.
- Replacing `365.25` with `DAYS_PER_YEAR` is numerically exact, but the import and
  shim must preserve `REQUIRED_COLUMNS` and the function signature.

### 2.2 `src/observation_schedule.py`

**Role:** Generate fixed-cadence observation timestamps and linearly interpolate
ground-truth positions onto those timestamps.

**Public API**

```python
def generate_observation_times(
    start_day,
    end_day,
    cadence_days,
    available_start_day,
    available_end_day,
):
    ...

def interpolate_positions(
    ground_truth_times_days,
    ground_truth_positions,
    observation_times_days,
):
    ...
```

No defaults, annotations, classes or CLI entry point.

**Imports and dependencies**

```python
import numpy as np
```

NumPy only. No project imports, path handling, configuration access or file I/O.

**Path and configuration dependencies**

None. All time bounds and arrays are supplied by the caller.

**Callers**

- `src/observation_generator.py` lines 10–13, 73 and 89.
- `tests/test_observation_schedule.py` lines 9–11.
- Indirectly in `tests/test_observer_model.py`,
  `tests/test_coordinate_converter.py` and `tests/test_measurement_noise.py`.

No other source module imports it.

**Existing tests and coverage**

- `tests/test_observation_schedule.py` loads the tracked trajectory, requests
  0.0–1826.25 days at 7.0-day cadence, interpolates, and prints the count, first
  and last times and array shapes. It contains no assertions.
- No test covers invalid cadence, invalid interval, out-of-range requests,
  endpoint inclusion edge cases, wrong position shape, insufficient samples,
  non-increasing times, non-finite values or out-of-range observation times.
- The script depends on the tracked trajectory and is CWD-sensitive through the
  loader path.

**Independence from orchestration**

Genuinely independent. It depends only on NumPy and has no component-internal
imports.

**Migration risks**

- Endpoint inclusion is intentional and must remain unchanged. With
  `start_day=0`, `end_day=1826.25`, `cadence_days=7`, the documented result is
  262 observations with a shorter final gap (6.25 days). This is a known
  limitation, not a bug to fix in C3.
- Validation order and exact `ValueError` messages matter.
- `np.arange` start-inclusive/end-exclusive semantics and the
  `np.isclose(..., atol=1e-9)` endpoint check must be preserved exactly.
- `np.interp` linear interpolation, per-axis ordering and `(N, 3)` output shape
  must not change. Velocities remain unused in C3.

### 2.3 `src/observer_model.py`

**Role:** Compute idealized circular observer positions in the heliocentric
ecliptic plane and form asteroid-minus-observer vectors.

**Public API**

```python
def calculate_observer_positions(
    time_years,
    orbital_radius_au=1.0,
    orbital_period_years=1.0,
    initial_phase_deg=90.0,
):
    ...

def calculate_relative_positions(
    asteroid_positions,
    observer_positions,
):
    ...
```

No annotations, classes or CLI entry point.

**Imports and dependencies**

```python
import numpy as np
```

NumPy only. No project imports, path handling or configuration access.

**Path and configuration dependencies**

None. The orchestrator passes the observer parameters from the observation config.

**Callers**

- `src/observation_generator.py` lines 14–17, 101 and 112.
- `tests/test_observer_model.py` lines 15–18.
- Indirectly in `tests/test_coordinate_converter.py` and
  `tests/test_measurement_noise.py`.

No other source module imports it.

**Existing tests and coverage**

- `tests/test_observer_model.py` runs the pipeline through relative positions and
  asserts:
  - the initial observer position is `[0.0, 1.0, 0.0]` AU within `1e-10`;
  - asteroid, observer and relative arrays have matching shapes.
- It does not check later epochs, scalar input, default values separately,
  invalid radius/period/time values or relative-position error paths.
- It depends on the tracked trajectory and is CWD-sensitive through the loader.

**Independence from orchestration**

Genuinely independent. It depends only on NumPy.

**Migration risks**

- The default `initial_phase_deg=90.0` is part of the public behaviour and is
  exercised by `[0, 1, 0]` at `t=0`.
- The formula `theta = 2*pi*t/T + phase` and the z=0 plane must not change.
- `calculate_relative_positions` returns `asteroid - observer`, in that order.
- Shape validation order matters: equality of shapes is checked before the
  `(N, 3)` check.
- No new observer model, ephemeris, light-time, aberration or topocentric term
  may be introduced.

### 2.4 `src/coordinate_converter.py`

**Role:** Rotate heliocentric ecliptic Cartesian vectors into equatorial
Cartesian vectors and compute right ascension and declination.

**Public API**

```python
def ecliptic_to_equatorial(
    relative_positions,
    obliquity_deg=23.43928,
):
    ...

def calculate_ra_dec(equatorial_positions):
    ...
```

No annotations, classes or CLI entry point.

**Imports and dependencies**

```python
import numpy as np
```

NumPy only. No project imports, path handling or configuration access.

**Path and configuration dependencies**

None. The orchestrator passes `obliquity_deg` from the observation config. Every
current config supplies `23.43928`, which equals the function default.

**Callers**

- `src/observation_generator.py` lines 18–21, 123 and 128.
- `tests/test_coordinate_converter.py` lines 19–22.
- Indirectly in `tests/test_measurement_noise.py`.

No other source module imports it. `src/compare_observation_datasets.py` applies
the same residual mathematics but does not import this module.

**Existing tests and coverage**

- `tests/test_coordinate_converter.py` runs the pipeline through RA/Dec and
  asserts:
  - 262 RA and Dec values;
  - RA in `[0, 360)`;
  - Dec in `[-90, 90]`;
  - all values finite.
- It does not assert exact rotation values, RA/Dec cardinal directions, the
  default obliquity independently, zero-vector rejection, wrong shapes or
  non-finite inputs.
- The test hardcodes 262 and depends on the tracked trajectory and CWD.

**Independence from orchestration**

Genuinely independent. It depends only on NumPy.

**Migration risks**

- The destination name is unresolved: `geometry.py` versus `frames.py`.
- The default obliquity `23.43928` must stay with this component module. It must
  not move to `core/constants.py`.
- The rotation equations must remain unchanged:
  `x_eq = x`, `y_eq = y*cos(eps) - z*sin(eps)`,
  `z_eq = y*sin(eps) + z*cos(eps)`.
- RA uses `atan2(y, x)` and modulo 360; Dec uses `atan2(z, hypot(x, y))`.
- Zero-vector rejection must remain exact (`distance == 0`).
- The return shape/order `(ra_deg, dec_deg)` must remain unchanged.

### 2.5 `src/measurement_noise.py`

**Role:** Add seeded independent Gaussian angular noise in the RA tangent-plane
and Dec directions.

**Public API**

```python
ARCSEC_TO_DEG = 1.0 / 3600.0

def add_measurement_noise(
    ra_deg,
    dec_deg,
    sigma_ra_cosdec_arcsec=0.5,
    sigma_dec_arcsec=0.5,
    random_seed=42,
):
    ...
```

No annotations, classes or CLI entry point. `ARCSEC_TO_DEG` is an existing public
module attribute, not merely a private helper.

**Imports and dependencies**

```python
import numpy as np
```

NumPy only. No project imports, path handling or configuration access.

**Path and configuration dependencies**

None. The orchestrator passes the configured sigmas and seed.

**Callers**

- `src/observation_generator.py` lines 22 and 143.
- `tests/test_measurement_noise.py` line 23.

No other source module imports it.

**Existing tests and coverage**

- `tests/test_measurement_noise.py` runs the pipeline through noise and asserts:
  - 262 RA and Dec values;
  - RA in `[0, 360)`;
  - Dec in `[-90, 90]`;
  - all values finite;
  - calling again with seed 42 reproduces the same arrays.
- It does not assert exact first offsets, zero-noise behaviour, RA wrap,
  negative sigmas, mismatched shapes, non-finite inputs, pole singularity or
  out-of-range noisy Dec.
- The test hardcodes 262 and depends on the tracked trajectory and CWD.

**Independence from orchestration**

Genuinely independent. It depends only on NumPy.

**Migration risks**

- Random draw order is part of the scientific contract. The code draws RA noise
  first and Dec noise second. Any reordering, combination or change of array
  shape changes all seeded outputs.
- The RNG constructor `np.random.default_rng(random_seed)` must remain exactly
  the same.
- `sigma_ra_cosdec_arcsec` is a tangent-plane uncertainty; the division by
  `cos(dec)` must remain.
- The local `ARCSEC_TO_DEG` must either remain available at the new module path
  or be imported from `core.constants` and re-exported through the shim.
- Validation order, exact messages, RA wrapping and the final Dec range rejection
  must be preserved.
- Known limitations (same seed across scenarios, no covariance, batch-level pole
  rejection) must not be "fixed" in C3.

---

## 3. Exact migration mapping

### 3.1 Recommended mapping

| Existing path | Proposed destination | Public names to preserve | Internal change | Recommendation |
|---|---|---|---|---|
| `src/trajectory_loader.py` | `src/orbit_discovery/component2_observations/loader.py` | `REQUIRED_COLUMNS`, `load_trajectory` | Replace `365.25` with `DAYS_PER_YEAR` | Approve; migrate last |
| `src/observation_schedule.py` | `src/orbit_discovery/component2_observations/schedule.py` | `generate_observation_times`, `interpolate_positions` | None | Approve; migrate first |
| `src/observer_model.py` | `src/orbit_discovery/component2_observations/observer.py` | `calculate_observer_positions`, `calculate_relative_positions` | None | Approve; migrate first |
| `src/coordinate_converter.py` | `src/orbit_discovery/component2_observations/frames.py` **or** `geometry.py` | `ecliptic_to_equatorial`, `calculate_ra_dec` | None; keep `obliquity_deg=23.43928` local | Approve destination name first |
| `src/measurement_noise.py` | `src/orbit_discovery/component2_observations/noise.py` | `ARCSEC_TO_DEG`, `add_measurement_noise` | Import `ARCSEC_TO_DEG` from core constants | Approve; migrate with frames/geometry |

### 3.2 Naming conflict for the frame module

The destination name is inconsistent across the approved/planning documents:

| Document | Destination name |
|---|---|
| `REFACTORING_PLAN.md` target tree | `component2_observations/geometry.py` |
| `PHASE_1_STEP_1_ASSESSMENT.md` target tree | `component2_observations/frames.py` |
| `PHASE_1_STEP_2_CORE_ASSESSMENT.md` migration mapping | `component2_observations/frames.py` |
| `CODEBASE_ANALYSIS.md` target tree | `component2_observations/frames.py` |
| This checkpoint's proposed table | `component2_observations/geometry.py` |

**Recommendation:** use `frames.py`. It matches the most recent Phase 1
assessments and the analysis tree, and it names the scientific responsibility
precisely (ecliptic-to-equatorial frame rotation plus RA/Dec). If `geometry.py` is
preferred, record it as an explicit amendment before implementation; renaming
after callers and tests import it is more expensive.

### 3.3 What does not move in C3

- `src/observation_generator.py` remains unchanged.
- `src/compare_observation_datasets.py` remains unchanged.
- Configuration loading and metadata writing remain in the orchestrator.
- `configs/`, `data/`, `results/` and `plots/` remain at their current paths.
- No CLI module, argument parser, propagation service or future component
  directory is created.
- No compatibility shim for `src/observation_generator.py` is created in C3.

### 3.4 Expected end state after C3

```text
src/
├── trajectory_loader.py          # thin shim -> package loader
├── observation_schedule.py       # thin shim -> package schedule
├── observer_model.py             # thin shim -> package observer
├── coordinate_converter.py       # thin shim -> package frames (or geometry)
├── measurement_noise.py          # thin shim -> package noise
├── observation_generator.py      # unchanged; still imports src.* shims
└── orbit_discovery/
    └── component2_observations/
        ├── __init__.py           # minimal; no eager re-exports
        ├── loader.py             # moved implementation
        ├── schedule.py           # moved implementation
        ├── observer.py           # moved implementation
        ├── frames.py             # moved implementation (name subject to D-01)
        ├── noise.py              # moved implementation
        └── ...                   # no generator/config/metadata/CLI in C3
```

The old files remain importable only in a source checkout where the repository
root is on `sys.path`; they are not installed package modules. See Section 5.

---

## 4. Public API inventory

The following is the complete public API of the five existing modules. No
classes, exceptions or CLI functions are defined in them.

| Module | Public name | Exact signature / value | Return / notes |
|---|---|---|---|
| `trajectory_loader` | `REQUIRED_COLUMNS` | list of eight strings in the order below | Schema order matters |
| `trajectory_loader` | `load_trajectory` | `load_trajectory(csv_path)` | dict with `time_years`, `time_days`, `positions`, `velocities`, `number_of_samples` |
| `observation_schedule` | `generate_observation_times` | `generate_observation_times(start_day, end_day, cadence_days, available_start_day, available_end_day)` | 1-D `float` ndarray; start inclusive, exact end appended |
| `observation_schedule` | `interpolate_positions` | `interpolate_positions(ground_truth_times_days, ground_truth_positions, observation_times_days)` | `(M, 3)` `float` ndarray |
| `observer_model` | `calculate_observer_positions` | `calculate_observer_positions(time_years, orbital_radius_au=1.0, orbital_period_years=1.0, initial_phase_deg=90.0)` | `(N, 3)` `float` ndarray; AU |
| `observer_model` | `calculate_relative_positions` | `calculate_relative_positions(asteroid_positions, observer_positions)` | `(N, 3)` `float` ndarray; AU |
| `coordinate_converter` | `ecliptic_to_equatorial` | `ecliptic_to_equatorial(relative_positions, obliquity_deg=23.43928)` | `(N, 3)` `float` ndarray; same distance unit |
| `coordinate_converter` | `calculate_ra_dec` | `calculate_ra_dec(equatorial_positions)` | tuple `(ra_deg, dec_deg)`; degrees |
| `measurement_noise` | `ARCSEC_TO_DEG` | `1.0 / 3600.0` | degrees per arcsecond |
| `measurement_noise` | `add_measurement_noise` | `add_measurement_noise(ra_deg, dec_deg, sigma_ra_cosdec_arcsec=0.5, sigma_dec_arcsec=0.5, random_seed=42)` | tuple of four arrays: noisy RA, noisy Dec, RA noise, Dec noise |

`REQUIRED_COLUMNS` in exact order:

```python
[
    "time_years",
    "time_days",
    "x_au",
    "y_au",
    "z_au",
    "vx_au_per_year",
    "vy_au_per_year",
    "vz_au_per_year",
]
```

Incidental module attributes created by the current imports (`np`, `pd`,
`Path`) are not part of the supported API. Shims should explicitly re-export the
documented public names above, not use a blanket `import *`.

The current modules define no `__all__`. Adding one is optional; if added, it
must not remove or rename any existing public name.

---

## 5. Import and compatibility strategy

### 5.1 Current import topology

`src/observation_generator.py` imports all five helpers with absolute imports:

```python
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

The five tests use the same `src.*` paths. None of the five helpers imports
another project module, so the dependency graph is a star:

```text
src.observation_generator
    -> src.trajectory_loader
    -> src.observation_schedule
    -> src.observer_model
    -> src.coordinate_converter
    -> src.measurement_noise
```

This makes a per-module move low-risk and gives an easy equivalence strategy:
import both the old and new functions against the same in-memory inputs.

### 5.2 Shim rules

The approved shim strategy should remain:

1. The old `src/*.py` path becomes a thin module that imports and re-exports the
   new package names.
2. It contains no scientific logic, no path policy, no configuration handling and
   no duplicated formulas.
3. It preserves the exact public names, signatures and return shapes listed in
   Section 4.
4. It does not emit a deprecation warning in Phase 1. A warning on stderr could
   break scripts that treat stderr as failure; the Step 1 addendum already makes
   this explicit.
5. The new package module contains the implementation; the old module is not
   retained as a second implementation.
6. No `src/__init__.py` is added. `src` remains a namespace container, not the
   package identity.
7. The package `component2_observations/__init__.py` stays minimal. It should not
   eagerly import every submodule; eager imports make package import heavier and
   increase circular-import risk.

Illustrative shim shape (not implemented in this checkpoint):

```python
"""Compatibility shim for the old src.trajectory_loader path."""

from orbit_discovery.component2_observations.loader import (
    REQUIRED_COLUMNS,
    load_trajectory,
)

__all__ = ["REQUIRED_COLUMNS", "load_trajectory"]
```

The noise shim must also include `ARCSEC_TO_DEG`:

```python
from orbit_discovery.component2_observations.noise import (
    ARCSEC_TO_DEG,
    add_measurement_noise,
)
```

### 5.3 Direct script execution

Direct script execution is not relevant for any of the five modules:

- none has a `main()` function;
- none has an `argparse` parser;
- none has an `if __name__ == "__main__"` block;
- executing any of them directly currently only defines functions and exits.

The relevant documented entry point is
`python -m src.observation_generator --config ...`, which imports the five helper
paths and must keep working during C3. The orchestrator itself is not moved in
C3.

### 5.4 Circular import risk

There is no circular-import risk in the proposed move:

- The five new modules import only NumPy, Pandas and (for two modules) the pure
  `orbit_discovery.core.constants` module.
- `core` does not import any component module.
- The new modules do not import each other.
- The orchestrator remains the only importer, and it is not moved in C3.

The only way to introduce a cycle would be to make
`component2_observations/__init__.py` import the submodules while a submodule also
imports the package initialiser. Keeping `__init__.py` minimal avoids this.

### 5.5 Critical environment issue: package importability

The current `.venv` does **not** have the `orbit-discovery` distribution
installed. Safe probes show:

```text
importlib.util.find_spec("orbit_discovery")  -> None
import orbit_discovery                        -> ModuleNotFoundError
import src.orbit_discovery                    -> succeeds
```

`src` is not on `sys.path`; it is only a namespace package reachable from the
repository root. Therefore a shim such as:

```python
from orbit_discovery.component2_observations.schedule import ...
```

would fail when the old command is run in a plain source checkout:

```powershell
python -m src.observation_generator --help
```

The command currently works because the old modules are present at `src/*.py`.
Replacing them with naive `orbit_discovery.*` shims would introduce a regression
that is unrelated to the science move.

There are three viable resolutions:

| Option | Mechanism | Advantages | Disadvantages | Recommendation |
|---|---|---|---|---|
| A. Editable install | `pip install -e .` in the development environment, then shims use `orbit_discovery.*` | Correct package identity; old and new imports both work; aligns with C1 packaging | Requires build backend (`setuptools`, `wheel`); the current `.venv` does not list them, so it may require a build-dependency install/network | **Preferred**, as a pre-C3 readiness step |
| B. Shim path bootstrap | Each shim (or a small compatibility helper) inserts the repository `src/` directory into `sys.path`, then imports `orbit_discovery.*` | Works from a plain source checkout; keeps correct `orbit_discovery` identity | Mutates global `sys.path`; must be repeated or centralised; can shadow an installed distribution | Acceptable fallback only with explicit approval |
| C. Shim imports `src.orbit_discovery.*` | New package modules use relative imports internally; old shims import the package through the `src` namespace | No install or path mutation; works from a plain checkout | Creates a second module identity (`src.orbit_discovery` vs `orbit_discovery`); `__module__` and module object identity differ; must be tested carefully | Least desirable fallback |

The assessment recommends **Option A** if the implementation checkpoint permits an
editable install, or **Option B** with a small, documented compatibility
bootstrap if installation is prohibited. Option C should be used only if both A
and B are rejected.

This is an environment/readiness decision, not a scientific change. It must be
resolved before the first shim replaces an existing module.

### 5.6 Installed-package compatibility

`pyproject.toml` declares:

```toml
[tool.setuptools.packages.find]
where = ["src"]
include = ["orbit_discovery*"]
namespaces = false
```

The future installed distribution contains `orbit_discovery` and its subpackages;
it does not declare the top-level `src/*.py` shims as `py-modules`. Therefore:

- old `src.*` imports are a source-checkout compatibility path, not an installed
  package API;
- installed users must use `orbit_discovery` (and, after later checkpoints, the
  `orbit-*` commands);
- no attempt should be made to install a top-level `src` package.

### 5.7 Signature and return preservation

Every migrated function should be copied without semantic edits:

- keep the exact parameter names, order and defaults;
- keep the same positional/keyword calling behaviour;
- keep return types, tuple order and array shapes;
- keep the same `ValueError`/`FileNotFoundError` types and messages;
- keep the same validation order;
- keep the loader's `print()` calls;
- keep the noise RNG draw order;
- do not add new validation, new fields, new defaults or type annotations in C3.

Type annotations could be added in a later, separately reviewed cleanup, but they
are not needed for migration and would make the diff larger.

---

## 6. Scientific invariants that must remain unchanged

This section records the behaviour that a pure move must preserve. It is a
characterisation target, not a proposal to improve any algorithm.

### 6.1 Trajectory loader contract

Required columns, in this order:

```text
time_years
time_days
x_au
y_au
z_au
vx_au_per_year
vy_au_per_year
vz_au_per_year
```

Validation sequence and outcomes:

| Condition | Result |
|---|---|
| File does not exist | `FileNotFoundError("Trajectory file not found: {csv_path}")` |
| Any required column missing | `ValueError("Missing required columns: {missing_columns}")` |
| Non-numeric or missing value after coercion | `ValueError("Trajectory contains missing or invalid numerical values.")` |
| Infinite or non-finite value | `ValueError("Trajectory contains infinite or non-finite values.")` |
| Fewer than two rows | `ValueError("Trajectory must contain at least two samples.")` |
| `time_years` not strictly increasing | `ValueError("Trajectory timestamps must be strictly increasing.")` |
| `time_days` not `allclose` to `time_years * 365.25` with `rtol=0`, `atol=1e-6` | `ValueError("Time columns are inconsistent.")` |

Additional invariants:

- Extra CSV columns are ignored; the returned arrays use only
  `REQUIRED_COLUMNS`.
- The returned dictionary key order is `time_years`, `time_days`, `positions`,
  `velocities`, `number_of_samples`.
- `positions` and `velocities` have shape `(N, 3)`.
- `number_of_samples == len(data)` after the required-column selection.
- The function prints exactly the existing three progress lines:
  `Trajectory loaded successfully.`, `Number of samples: N`, and
  `Duration: ... to ... years`.
- No metadata is read or validated.
- No velocity-position consistency check exists.
- Legacy schemas such as `time_yr`/`x_AU` remain rejected.

### 6.2 Observation scheduling and interpolation

`generate_observation_times` invariants:

- Validation order: cadence, end-versus-start, start range, end range.
- `cadence_days <= 0` raises `ValueError("Cadence must be greater than zero.")`.
- `end_day <= start_day` raises
  `ValueError("End day must be greater than start day.")`.
- `start_day < available_start_day` raises
  `ValueError("Start day is outside trajectory range.")`.
- `end_day > available_end_day` raises
  `ValueError("End day is outside trajectory range.")`.
- `np.arange(start_day, end_day, cadence_days, dtype=float)` is used.
- The exact `end_day` is appended when the array is empty or the last value is
  not `np.isclose(..., end_day, atol=1e-9)`.
- The result is a sorted 1-D float array beginning at `start_day` and ending at
  `end_day`.
- The final interval can be shorter than the cadence; this is intentional and
  must not be "fixed" in C3.
- The documented standard scenario produces 262 observations; that count must
  remain unchanged.

`interpolate_positions` invariants:

- All three inputs are converted with `np.asarray(..., dtype=float)`.
- Ground-truth positions must have exactly shape `(len(times), 3)`, otherwise
  `ValueError("Ground-truth positions must have shape (N, 3).")`.
- At least two ground-truth samples are required.
- Ground-truth times must be strictly increasing.
- Ground-truth positions and observation times must be finite.
- Observation times must lie inside the inclusive ground-truth range.
- Exactly one error message exists for each of those conditions, as follows:

```text
Ground-truth positions must have shape (N, 3).
At least two ground-truth samples are required.
Ground-truth timestamps must be strictly increasing.
Ground-truth positions contain invalid values.
Observation times contain invalid values.
Observation time falls outside ground-truth range.
```

- Interpolation is linear per axis with `np.interp`.
- The result is `(M, 3)` float, in input row order.
- Interpolation at the ground-truth endpoints returns the endpoint positions.
- Extrapolation is rejected; it is never silently performed.
- Velocities remain unused.

### 6.3 Observer geometry

`calculate_observer_positions` invariants:

- Input times are converted to a float array and must be finite.
- `orbital_radius_au > 0` and `orbital_period_years > 0`.
- `phase_rad = np.deg2rad(initial_phase_deg)`.
- `angle = 2*pi*time_years/orbital_period_years + phase_rad`.
- `x = R*cos(angle)`, `y = R*sin(angle)`, `z = 0`.
- Output is `(N, 3)` in AU.
- With the defaults (`R=1`, `T=1`, phase=90°), the first position at `t=0` is
  `[0, 1, 0]` AU.
- The model remains circular, coplanar and heliocentric. No ephemeris, eccentric
  Earth, light-time, aberration or topocentric term may be added.

Errors:

```text
Time values must be finite.
Orbital radius must be positive.
Orbital period must be positive.
```

`calculate_relative_positions` invariants:

- Both inputs are converted to float arrays.
- Shapes must be equal, otherwise
  `ValueError("Asteroid and observer position arrays must have the same shape.")`.
- Both must then have shape `(N, 3)`, otherwise
  `ValueError("Position arrays must have shape (N, 3).")`.
- Both must be finite.
- The returned array is exactly `asteroid_positions - observer_positions`, shape
  `(N, 3)`, AU, same row order.
- No range, light-time or observer-velocity computation is added.

Exact errors:

```text
Asteroid and observer position arrays must have the same shape.
Position arrays must have shape (N, 3).
Asteroid positions contain invalid values.
Observer positions contain invalid values.
```

### 6.4 Frame rotation and RA/Dec

`ecliptic_to_equatorial` invariants:

- Input must be `(N, 3)` and finite.
- `obliquity = np.deg2rad(obliquity_deg)`.
- `x_eq = x`.
- `y_eq = y*cos(obliquity) - z*sin(obliquity)`.
- `z_eq = y*sin(obliquity) + z*cos(obliquity)`.
- Output is `(N, 3)` in the same distance unit, same row order.
- Default `obliquity_deg=23.43928` is retained in this component module. Every
  current config explicitly supplies the same value, but the default remains part
  of the function contract.
- No precession, nutation, epoch-dependent obliquity or frame dispatch is added.

`calculate_ra_dec` invariants:

- Input must be `(N, 3)` and finite.
- `distance = ||position||`; any exactly zero distance raises
  `ValueError("Cannot calculate coordinates for zero vectors.")`.
- `ra_rad = arctan2(y, x)`.
- `dec_rad = arctan2(z, sqrt(x**2 + y**2))`.
- `ra_deg = mod(rad2deg(ra_rad), 360.0)`, so RA is in `[0, 360)`.
- `dec_deg = rad2deg(dec_rad)`, in `[-90, 90]` for finite non-zero vectors.
- Return order is exactly `(ra_deg, dec_deg)`.
- No special RA-wrap branch is added; `atan2` plus modulo is the existing
  behaviour.

Shared errors:

```text
Positions must have shape (N, 3).
Positions contain invalid values.
Cannot calculate coordinates for zero vectors.
```

### 6.5 Measurement noise

`add_measurement_noise` invariants:

- Inputs are converted to float arrays and must have matching shapes.
- RA/Dec must be finite and Dec within `[-90, 90]`.
- Both sigma values must be non-negative.
- RNG is exactly `np.random.default_rng(random_seed)`.
- Draw order is RA first, then Dec, each with
  `rng.normal(0.0, sigma, size=shape)`.
- `sigma_ra_cosdec_arcsec` is a tangent-plane `sigma_RA*cos(Dec)` value.
- `cos_dec = cos(deg2rad(dec_deg))`.
- If any `abs(cos_dec) < 1e-12` and `sigma_ra_cosdec_arcsec > 0`, raise
  `ValueError("RA noise conversion is singular at the celestial poles.")`.
- `ra_offset_deg = ra_noise_arcsec * ARCSEC_TO_DEG / cos_dec`.
- `dec_offset_deg = dec_noise_arcsec * ARCSEC_TO_DEG`.
- `noisy_ra_deg = mod(ra_deg + ra_offset_deg, 360.0)`.
- `noisy_dec_deg = dec_deg + dec_offset_deg`.
- Any noisy Dec outside `[-90, 90]` raises
  `ValueError("Noise produced declination outside the valid range.")`.
- Return order is `(noisy_ra_deg, noisy_dec_deg, ra_noise_arcsec,
  dec_noise_arcsec)`.
- Defaults remain `sigma_ra_cosdec_arcsec=0.5`,
  `sigma_dec_arcsec=0.5`, `random_seed=42`.
- No covariance, clipping, resampling, per-epoch sigma or independent per-scenario
  seed is introduced.

Exact errors:

```text
RA and Dec arrays must have matching shapes.
Coordinates must contain finite values.
Declination must be between -90 and +90 degrees.
Noise uncertainties cannot be negative.
RA noise conversion is singular at the celestial poles.
Noise produced declination outside the valid range.
```

### 6.6 Cross-cutting invariants

- Units remain AU for positions/distances, years/days for elapsed time, degrees
  for RA/Dec and arcseconds for angular uncertainties.
- All array ordering remains input-order, with positions shape `(N, 3)`.
- Functions remain vectorised and do not mutate their inputs.
- The five modules do not read configs, metadata, project roots or scientific
  files. The loader only reads the CSV path it is given.
- The old `print()` side effect in the loader remains for Phase 1.
- No logging framework, schema version, truth separation or metadata change is
  introduced.

### 6.7 Known limitations to record separately, not fix

These are existing limitations documented in `CODEBASE_ANALYSIS.md` and
`REFACTORING_PLAN.md`. They must survive C3 unchanged:

- The loader does not read or validate Component 1 metadata.
- The loader rejects the legacy CSV schema without a migration adapter.
- The loader has `print()` side effects.
- Scheduling appends the exact endpoint, so the final cadence is shorter and the
  schedule is not perfectly uniform.
- Interpolation is linear and ignores the loaded velocity columns; documented
  error is 0.22″ median and 1.73″ maximum, comparable to the 0.5″ noise.
- The observer is an idealized circular, coplanar, heliocentric point with an
  arbitrary phase; it is not an ephemeris.
- No light-time, aberration, topocentric parallax or observability model exists.
- The frame rotation uses a fixed J2000 mean obliquity and no precession or
  nutation.
- All three scenarios reuse seed 42 and the same array length, so their noise
  realisations are not independent.
- Noise has no RA/Dec covariance and rejects an entire batch if one noisy Dec
  leaves `[-90, 90]`.
- No test covers these limitations, and C3 must not silently change them.

---

## 7. Shared constants integration

### 7.1 Approved constants

`src/orbit_discovery/core/constants.py` currently contains only:

```python
DAYS_PER_YEAR = 365.25
ARCSEC_TO_DEG = 1.0 / 3600.0
```

`OBLIQUITY_DEG` is intentionally absent. It remains a Component 2 frame default.

### 7.2 Exact occurrences in the five modules

| Module | Occurrence | Current form | Safe substitution |
|---|---|---|---|
| `trajectory_loader.py` | line 82, inside `np.allclose` | `time_years * 365.25` | `time_years * DAYS_PER_YEAR` |
| `measurement_noise.py` | line 5 | `ARCSEC_TO_DEG = 1.0 / 3600.0` | import `ARCSEC_TO_DEG` from `orbit_discovery.core.constants` |
| `measurement_noise.py` | lines 63 and 67 | `ra_noise_arcsec * ARCSEC_TO_DEG ...` | unchanged expression using the imported name |
| `observation_schedule.py` | none | — | no change |
| `observer_model.py` | none | — | no change |
| `coordinate_converter.py` | line 7 | `obliquity_deg=23.43928` | **do not move**; keep local |

Numerically both substitutions are exact:

- `365.25` is exactly representable in binary floating point, and the imported
  value is the same literal.
- `1.0 / 3600.0` is the same expression, so the imported value is identical.

No tolerance, formula, rounding or array dtype may change.

### 7.3 Compatibility requirements for the substitutions

- The new `loader.py` imports `DAYS_PER_YEAR` explicitly. The old
  `src/trajectory_loader.py` shim re-exports only `REQUIRED_COLUMNS` and
  `load_trajectory`; `DAYS_PER_YEAR` was not a public name of the old loader, so
  it need not be re-exported there.
- The new `noise.py` imports `ARCSEC_TO_DEG`. Because the old
  `src/measurement_noise.py` exposed `ARCSEC_TO_DEG` as a public module attribute,
  the old shim must explicitly re-export it.
- No test or caller should be changed merely to accommodate the constant. Old
  tests may continue to use literals.
- `OBLIQUITY_DEG` must not be added to `core/constants.py` in C3.
- `DAYS_PER_YEAR` in `src/observation_generator.py:26` is out of scope for C3
  and will be handled with the orchestrator migration (C4).
- The inverse `* 3600` expressions in `src/compare_observation_datasets.py` and
  the observation-output tests are out of scope; they belong to the comparison
  and test-migration checkpoints.
- `365.25` literals in `horizons_loader.py`, `configurable_simulator.py` and
  tests remain untouched in C3.

### 7.4 Recommended application order

1. In the `noise` migration checkpoint, import `ARCSEC_TO_DEG` and update the
   shim to re-export it.
2. In the `loader` migration checkpoint, import `DAYS_PER_YEAR` and replace the
   single literal.
3. Leave the other three modules and all tests/configs unchanged.

This keeps each constant change reviewable alongside the module move that uses
it.

---

## 8. Test and regression requirements

### 8.1 Existing test coverage

| Test file | Direct imports | Assertions | Data dependency | Notes |
|---|---|---|---|---|
| `tests/test_trajectory_loader.py` | `load_trajectory` | None | Tracked trajectory, CWD-relative | Smoke/print only |
| `tests/test_observation_schedule.py` | loader, schedule | None | Tracked trajectory, CWD-relative | Smoke/print only |
| `tests/test_observer_model.py` | loader, schedule, observer | Initial `[0,1,0]`; matching shapes | Tracked trajectory, CWD-relative | Happy path only |
| `tests/test_coordinate_converter.py` | loader, schedule, observer, geometry/coordinate | 262 rows; RA/Dec ranges; finite | Tracked trajectory, CWD-relative | Happy path only |
| `tests/test_measurement_noise.py` | all five | 262 rows; ranges; finite; seed reproducibility | Tracked trajectory, CWD-relative | Happy path and one reproducibility check |
| `tests/test_observation_output.py` | none | Full output schema/ranges/residuals | Tracked observations | Read-only output validation |
| `tests/test_all_observation_outputs.py` | none | Three datasets, 262 each, residuals | Tracked observations | Read-only |
| `tests/validate_ground_truth.py` | none | Loader-equivalent checks | Tracked trajectories | Duplicates loader logic |
| `tests/validate_baseline.py` | none | REBOUND/Kepler checks | Legacy two-body CSV | Unrelated to Component 2 helpers |
| `tests/check_configurable_runs.py` | none | Trajectory shape/difference | Tracked runs | No helper imports |

There is no pytest suite in the current environment; pytest is not installed. The
existing tests are script-style and were not run during this read-only assessment.

### 8.2 Coverage gaps that C3 should address

The existing tests do not provide a safe migration oracle for:

- loader validation errors and exact messages;
- loader return keys, shapes and extra-column handling;
- schedule validation order, endpoint edge cases and exact 262-value schedule;
- interpolation exactness, endpoint behaviour and out-of-range rejection;
- observer defaults, later epochs and error paths;
- frame rotation exact values at known obliquities;
- RA/Dec cardinal directions, zero vectors and error paths;
- noise exact seeded values, zero sigma, RA wrap, pole singularity and Dec
  rejection;
- old-versus-new import equivalence.

### 8.3 Required new tests per checkpoint

The new tests must use temporary directories or in-memory arrays only. They must
not write into `configs/`, `data/`, `results/` or `plots/`, and they must not
modify the existing scripts.

**Schedule**

- Standard scenario: `start=0`, `end=1826.25`, `cadence=7`, available range
  `0..1826.25` produces 262 values, starts at 0, ends exactly at 1826.25 and is
  strictly increasing.
- Endpoint edge cases: exact endpoint, non-landing endpoint, cadence larger than
  the interval.
- Invalid cadence and invalid interval raise the exact existing messages.
- Out-of-range start/end raise the exact existing messages.
- Interpolation of a linear ramp returns exact linear values at on-grid and
  in-between times.
- Endpoint interpolation returns the endpoint positions.
- Wrong shape, fewer than two samples, non-increasing times, non-finite values
  and out-of-range observation times raise the exact existing messages.
- Output shape is `(M, 3)` and input arrays are not mutated.

**Observer**

- Defaults produce `[0, 1, 0]` at `t=0`.
- Quarter-period motion produces the expected cardinal position within a tight
  tolerance.
- Radius and period scaling behave as before.
- Non-finite times, non-positive radius and non-positive period raise the exact
  messages.
- Relative positions equal `asteroid - observer`, preserve shape and order, and
  reject shape/finite errors in the existing order.

**Frame and RA/Dec**

- Obliquity `0` is an identity rotation within floating tolerance.
- Obliquity `90` maps `(0, 1, 0)` to `(0, 0, 1)` within tolerance.
- A known vector reproduces the exact existing formula.
- Default obliquity is exactly `23.43928`.
- RA/Dec cardinal vectors return the expected values within tolerance.
- RA wraps to `[0, 360)`; Dec remains in range.
- Wrong shapes, non-finite values and zero vectors raise the exact messages.
- Return order is `(ra_deg, dec_deg)`.

**Noise**

- Seed 42 reproduces the exact same four arrays on repeated calls.
- Zero sigma leaves RA/Dec unchanged (subject to existing modulo/range logic).
- RA wrap remains modulo 360.
- Negative sigma, mismatched shapes, non-finite inputs and invalid Dec raise the
  exact messages.
- Pole singularity raises the exact message when RA sigma is positive.
- A noisy Dec outside `[-90, 90]` raises the exact message.
- The draw order is verified indirectly by comparing exact seeded outputs with
  the old module during migration.
- `ARCSEC_TO_DEG` is importable from both old and new paths and has the same
  value.

**Loader**

- A minimal valid CSV with the eight required columns loads with the expected
  keys, shapes and values.
- Extra columns are ignored.
- Missing file raises `FileNotFoundError` with the existing message.
- Missing required columns, non-numeric values, NaN/infinite values, fewer than
  two rows, non-increasing time and inconsistent time columns raise the exact
  existing messages.
- `REQUIRED_COLUMNS` is unchanged in content and order.
- A relative path retains its current caller/CWD semantics; do not silently
  anchor it to the project root in C3.
- The loader's printed output is not asserted as a scientific contract, but its
  presence should not be removed in C3.

**Old/new equivalence**

For each migrated module, compare old and new functions on identical in-memory
inputs:

- deterministic functions: exact array equality where practical;
- noise: exact array equality for the same seed;
- loader: exact key sets, array equality and error type/message equality;
- signatures: compare parameter names, order and defaults;
- old import path and new import path must both work in the supported source
  checkout.

### 8.4 Regression gates

After each checkpoint, run only safe checks:

1. Import smoke checks for the new package module and the old `src.*` path.
2. The relevant existing read-only script(s) from the repository root.
3. New focused characterisation tests.
4. Old-versus-new equivalence checks on fixed inputs or tracked read-only data.
5. `git status --short` and `git diff --name-only -- data configs results plots`.
6. Confirm no dataset, result, plot or config was regenerated.

Do not run:

- `src/observation_generator.py` end-to-end (it writes observations);
- Component 1 simulation or any trajectory writer;
- `tests/test_component1_integration.py`, `tests/test_repeatability.py`,
  `tests/test_tolerance_sensitivity.py` or `tests/compare_trajectories.py`;
- any network/Horizons workflow.

The existing direct tests are read-only, but they depend on tracked data and CWD.
They may be run from the repository root as a smoke check; they are not a
substitute for the new hermetic tests.

---

## 9. Incremental implementation sequence

Each checkpoint is a separate, reviewable change. No checkpoint combines the
module move with a configuration, data, CLI or scientific change. The old
modules remain the fallback until their replacement checkpoint passes.

### 9.1 C3.0 — Environment readiness (no code changes)

**Purpose:** Resolve the package importability decision in Section 5.5 before a
shim imports `orbit_discovery`.

**Actions:**

- Choose Option A, B or C from Section 5.5.
- If Option A: verify an editable install in a disposable/development
  environment and confirm `python -c "import orbit_discovery"` works without
  `PYTHONPATH`. If build dependencies are unavailable, do not silently fall back.
- If Option B: approve and document the shim bootstrap policy.
- If Option C: approve relative imports and the temporary `src.orbit_discovery`
  identity, and add an explicit warning to the compatibility notes.
- Re-confirm `python -m src.observation_generator --help` still works before any
  shim is introduced (it does today).

**Acceptance:** the chosen import mechanism is reproducible from the repository
root; the old command still works; no source or data change.

**Rollback:** none needed; this is an environment/decision checkpoint.

### 9.2 C3.1 — Schedule and observer

**Files:**

- create `component2_observations/schedule.py` (pure move);
- create `component2_observations/observer.py` (pure move);
- replace `src/observation_schedule.py` and `src/observer_model.py` with thin
  shims;
- add focused tests for schedule and observer.

**Acceptance:**

- old and new imports both work under the approved environment mechanism;
- exact signatures/defaults/messages are unchanged;
- old/new arrays are identical on fixed inputs;
- standard schedule still yields 262 values for the documented scenario;
- observer default still yields `[0, 1, 0]`;
- existing `test_observation_schedule.py` and `test_observer_model.py` still
  pass from the repository root;
- `git status` shows no changes under `data/`, `configs/`, `results/` or
  `plots/`.

**Rollback:** restore the two tracked old files from Git, delete the two new
modules and their tests, and remove the shims. No data rollback is needed.

### 9.3 C3.2 — Frame/geometry and noise

**Files:**

- create `component2_observations/frames.py` (recommended name) or `geometry.py`;
- create `component2_observations/noise.py`;
- replace `src/coordinate_converter.py` and `src/measurement_noise.py` with thin
  shims;
- import `ARCSEC_TO_DEG` from `orbit_discovery.core.constants` in `noise.py`;
- re-export `ARCSEC_TO_DEG` through the old noise shim;
- add focused tests for rotation, RA/Dec and noise.

**Acceptance:**

- old and new imports both work;
- exact signatures/defaults/messages are unchanged;
- default obliquity remains `23.43928` and does not enter `core.constants`;
- `ARCSEC_TO_DEG` remains importable from the old path with the same value;
- seeded noise arrays are bitwise identical between old and new for fixed inputs;
- existing `test_coordinate_converter.py` and `test_measurement_noise.py` pass
  from the repository root;
- no tracked data change.

**Rollback:** restore the two tracked old files from Git, delete the new modules
and tests, and remove the shims. No data rollback is needed.

### 9.4 C3.3 — Trajectory loader

**Files:**

- create `component2_observations/loader.py`;
- import `DAYS_PER_YEAR` from `orbit_discovery.core.constants` and replace the
  single literal;
- replace `src/trajectory_loader.py` with a thin shim re-exporting
  `REQUIRED_COLUMNS` and `load_trajectory`;
- add focused loader tests using temporary CSVs.

**Acceptance:**

- old and new imports both work;
- exact signatures, return keys, array shapes, errors and printed progress
  remain;
- `REQUIRED_COLUMNS` is unchanged in content and order;
- old/new loaders return identical arrays for the tracked reference trajectory;
- existing `test_trajectory_loader.py` and the four pipeline tests pass from the
  repository root;
- no tracked data change.

**Rollback:** restore the tracked old loader from Git, delete the new module and
tests, and remove the shim. No data rollback is needed.

### 9.5 C3.4 — Final compatibility gate

**Actions:**

- run all five existing read-only tests from the repository root;
- run all new focused tests;
- run import smoke checks for all old and new paths;
- run `python -m src.observation_generator --help` (no generation);
- confirm the orchestrator still imports the old shim paths and contains no edits;
- inspect `git status` and the tracked-data diff.

**Acceptance:**

- all safe tests pass;
- no scientific output changed;
- no `src/observation_generator.py`, config, data, result or plot change;
- no compatibility shim contains scientific logic;
- no package `__init__` eagerly imports submodules;
- no future component, CLI or configuration module was created.

**Rollback:** revert the C3 checkpoint commit(s); old modules and data remain
available from Git.

---

## 10. Risks and rollback strategy

### 10.1 Risk register

| ID | Risk | Likelihood | Impact | Mitigation | Rollback |
|---|---|---|---|---|---|
| C3-R01 | Wrong destination name (`geometry.py` vs `frames.py`) becomes a public import | Medium | Medium | Approve D-01 before creating imports; rename before any caller adopts it | Rename the module and update only C3 tests/shims |
| C3-R02 | Naive shims break documented `python -m src.observation_generator` because `orbit_discovery` is not installed | High in the current environment | High | Resolve C3.0; use editable install or approved bootstrap; verify old command before/after each shim | Restore old tracked files; postpone shims |
| C3-R03 | Shim contains duplicated science or drifts from the package implementation | Medium | High | Explicit re-exports only; no formulas in shims; review diff | Restore old file and delete shim |
| C3-R04 | Function signature, default or return shape changes during copy | Medium | High | Verbatim copy; signature/default/return tests; old/new equivalence | Revert checkpoint; restore old module |
| C3-R05 | Error type, message or validation order changes | Medium | Medium | Characterisation tests for every documented error; diff review | Revert checkpoint |
| C3-R06 | Noise RNG draw order or seed handling changes | Medium | High | Copy `default_rng`, RA-then-Dec draw order and shape logic exactly; exact seeded equality test | Revert checkpoint |
| C3-R07 | `REQUIRED_COLUMNS` order/content changes | Low | High | Freeze the exact list; re-export it from the shim | Revert checkpoint |
| C3-R08 | Time tolerance or time-column semantics change | Low | High | Keep `rtol=0`, `atol=1e-6` and the exact expression; equivalence test on tracked CSV | Revert checkpoint |
| C3-R09 | Endpoint append or interpolation is "fixed" accidentally | Medium | High | Preserve `np.arange`, `np.isclose(..., atol=1e-9)` and `np.interp`; assert 262 and final gap | Revert checkpoint |
| C3-R10 | Observer defaults or frame default change | Low | High | Keep `1.0`, `1.0`, `90.0`, `23.43928`; assert defaults | Revert checkpoint |
| C3-R11 | `ARCSEC_TO_DEG` disappears from the old import path | Low | Medium | Re-export it explicitly from the noise shim and test it | Restore shim export |
| C3-R12 | `DAYS_PER_YEAR` substitution changes floating behaviour | Very low | Low | Same exact literal; equivalence test | Revert constant import |
| C3-R13 | New tests write into tracked data or depend on CWD | Medium | High | Use temp dirs/in-memory arrays; anchor any tracked-data read explicitly; run from repo root | Remove test side effects; restore data from Git |
| C3-R14 | Existing script tests fail outside the repository root | High | Medium | Do not change their path semantics in C3; run them from the root; fix anchoring in the test-migration checkpoint | Revert test changes, if any |
| C3-R15 | Package `__init__` eager imports create a cycle or import-time cost | Low | Medium | Keep `component2_observations/__init__.py` minimal; no re-exports | Revert `__init__` change |
| C3-R16 | `src` namespace collision with REBOUND headers causes confusion | Low | Medium | Do not create `src/__init__.py`; keep shims checkout-only; use `orbit_discovery` as the final identity | Remove any accidental `src` package |
| C3-R17 | Installed package includes unintended shims or misses subpackages | Low | Medium | Rely on `include = ["orbit_discovery*"]`; inspect a future wheel; do not add shims as `py-modules` | Fix `pyproject.toml`; no source change |
| C3-R18 | Scientific workflow is run accidentally and regenerates tracked data | Low | High | Do not run generator/Component 1/writer tests; check `git status` after every checkpoint | Restore tracked data from Git; never regenerate to "fix" a diff |

### 10.2 Rollback procedure

1. **Code rollback:** revert the C3 checkpoint commit; restore the tracked old
   module files from Git; delete the new package modules, shims and focused tests.
2. **Shim failure:** restore the old implementation file immediately and leave
   the new package module unused; the old command remains authoritative.
3. **Import-identity failure:** if the approved install/bootstrap mechanism does
   not work, revert the shims and postpone C3; do not add a silent path fallback.
4. **Data change:** if any tracked file under `data/`, `configs/`, `results/` or
   `plots/` changes, stop; restore it from Git and verify the baseline hashes.
   Do not regenerate data to repair the diff.
5. **Scientific regression:** if old/new outputs differ, stop at that checkpoint;
   compare the pre-migration source with the new module before proceeding.
6. **No history rewrite:** do not reset or rewrite unrelated commits; no tag or
   push during C3.

---

## 11. Decisions requiring approval

| ID | Decision | Recommendation | Why it needs review |
|---|---|---|---|
| D-01 | Destination name for `coordinate_converter.py`: `geometry.py` or `frames.py` | Use `frames.py`; if `geometry.py` is preferred, record it as an explicit amendment | The documents disagree; this becomes a public import path |
| D-02 | How old `src.*` shims import the package when `orbit_discovery` is not installed | Prefer an editable install; otherwise approve a documented shim bootstrap; avoid relative-import shims unless A and B are rejected | Naive shims break the currently documented old command in this environment |
| D-03 | Shim export policy | Explicitly re-export only the documented public names, including `REQUIRED_COLUMNS` and `ARCSEC_TO_DEG`; do not re-export incidental `np`/`pd`/`Path` | Prevents accidental API expansion and keeps shims thin |
| D-04 | Whether to apply `DAYS_PER_YEAR` and `ARCSEC_TO_DEG` during C3 or defer all constant adoption | Apply the two exact substitutions in their module checkpoints; keep `OBLIQUITY_DEG` local | The constants are approved and numerically identical, but their use changes imports and shim exports |
| D-05 | Whether the loader's `print()` calls remain during C3 | Keep them | Removing them changes observable console behaviour and is not required for packaging |
| D-06 | Whether to add `__all__` to the new modules | Optional; if added, preserve every existing public name; required only in shims if desired | Adding `__all__` can accidentally hide names |
| D-07 | Test file naming/placement for the new hermetic tests | Use flat `tests/test_component2_<module>.py` files consistent with the existing C2 test convention; defer full `tests/unit/` reorganisation to the test-migration checkpoint | Phase 1 does not reorganise the suite |
| D-08 | Checkpoint grouping/order | `schedule` + `observer`, then `frames`/`geometry` + `noise`, then `loader` | Smaller review units and lower-risk ordering |
| D-09 | Permission to run the existing read-only scripts during C3 checkpoints | Yes, from the repository root only; never run writer or network tests | They read tracked data and help detect regressions, but are CWD-sensitive |
| D-10 | Confirmation that `observation_generator.py` stays unchanged in C3 | Yes | It is the compatibility consumer of the shims; changing it belongs to C4 |

---

## 12. Git status and read-only confirmation

At the start of this assessment, `git status --short` showed the inherited
untracked files from C1/C2:

```text
?? docs/development/PHASE_1_STEP_1_ASSESSMENT.md
?? docs/development/PHASE_1_STEP_2_CORE_ASSESSMENT.md
?? pyproject.toml
?? src/orbit_discovery/
?? tests/test_core_constants.py
?? tests/test_core_paths.py
```

After creating this report, the expected additional entry is the report itself:

```text
?? docs/development/PHASE_1_STEP_3_COMPONENT2_ASSESSMENT.md
```

No tracked file was modified. `git diff --stat` and `git ls-files -m` produce no
output. There are no changes under `data/`, `configs/`, `results/` or `plots/`.

This assessment did not:

- modify any source, test, configuration, dataset, result, plot or other
  documentation file;
- create any module, shim or directory;
- install any dependency;
- run a simulation, observation-generation workflow or data-writing test;
- commit, tag or push.

Only safe read-only import/help probes and source/document inspection were
performed. No scientific output was regenerated.

---

*End of Phase 1 Step 3.1 Component 2 pure-modules assessment. No C3 migration
has been implemented.*
