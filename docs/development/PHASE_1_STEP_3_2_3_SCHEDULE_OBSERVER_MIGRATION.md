# Phase 1 — C3.2.3: Schedule and Observer Module Migration

**Status:** Migration complete. The two implementations were moved verbatim, the old paths were replaced with thin compatibility shims, and all focused and existing read-only checks passed.

**Repository:** `E:\rskmn\Npersonal\projects\yr4\final\prototype-1\physics-guided-orbit-discovery-prototype`

**Scope:** Migrate `src/observation_schedule.py` and `src/observer_model.py` into `orbit_discovery.component2_observations`, preserving scientific behaviour and old import paths.

No scientific algorithm, configuration, dataset, result, plot, or orchestration file was changed.

## 1. Files changed and created

| Path | Change |
|---|---|
| `src/orbit_discovery/component2_observations/schedule.py` | Created; contains the moved `observation_schedule` implementation. |
| `src/orbit_discovery/component2_observations/observer.py` | Created; contains the moved `observer_model` implementation. |
| `src/observation_schedule.py` | Replaced with a thin compatibility shim. |
| `src/observer_model.py` | Replaced with a thin compatibility shim. |
| `tests/test_component2_schedule.py` | Created; 20 focused hermetic tests. |
| `tests/test_component2_observer.py` | Created; 18 focused hermetic tests. |
| `src/orbit_discovery/component2_observations/__init__.py` | Unchanged. |
| `src/observation_generator.py` | Unchanged. |

The editable installation already exposes `orbit_discovery` from the repository `src` directory, so no packaging configuration change or reinstall was required for the new modules.

## 2. Implementation fidelity

Both new modules are exact source copies of the old implementations, ignoring only line-ending style:

| Original | New implementation | Comparison |
|---|---|---|
| `src/observation_schedule.py` (Git `HEAD`) | `src/orbit_discovery/component2_observations/schedule.py` | Exact match ignoring EOL. |
| `src/observer_model.py` (Git `HEAD`) | `src/orbit_discovery/component2_observations/observer.py` | Exact match ignoring EOL. |

The following were preserved:

- public function names;
- parameter names, order, and kinds;
- default values;
- docstrings and meaningful comments;
- NumPy conversions and dtype handling;
- validation order;
- exception types and exact messages;
- return shapes, tuple order, and array ordering;
- endpoint-inclusion and interpolation behaviour;
- observer geometry and relative-position subtraction order.

No new annotations, validation rules, algorithms, observer terms, or unrelated refactoring were added.

## 3. Compatibility shims

`src/observation_schedule.py` now contains only:

```python
"""Compatibility shim for the old ``src.observation_schedule`` path."""

from orbit_discovery.component2_observations.schedule import (
    generate_observation_times,
    interpolate_positions,
)

__all__ = [
    "generate_observation_times",
    "interpolate_positions",
]
```

`src/observer_model.py` now contains only:

```python
"""Compatibility shim for the old ``src.observer_model`` path."""

from orbit_discovery.component2_observations.observer import (
    calculate_observer_positions,
    calculate_relative_positions,
)

__all__ = [
    "calculate_observer_positions",
    "calculate_relative_positions",
]
```

The shims:

- contain no scientific logic or duplicate formulas;
- use the approved editable installation and absolute `orbit_discovery` imports;
- do not manipulate `sys.path`;
- explicitly re-export only the documented public names;
- do not re-export incidental `numpy` module names;
- preserve the old `from src.* import ...` imports.

An AST check confirmed that both old files contain no function or class definitions and are therefore thin shims.

## 4. Package exports

`src/orbit_discovery/component2_observations/__init__.py` remains the existing minimal module docstring:

```python
"""Synthetic observation generation component (skeleton)."""
```

No eager re-exports were added. There is no clear need for them at this checkpoint, and keeping the initializer minimal avoids circular-import and import-time side effects. Modules not yet migrated were not exported.

## 5. Tests and validation

### 5.1 New focused tests

Run from the repository root:

```powershell
& .venv\Scripts\python.exe tests\test_component2_schedule.py -v
& .venv\Scripts\python.exe tests\test_component2_observer.py -v
```

Results:

```text
test_component2_schedule.py: 20 tests passed
test_component2_observer.py: 18 tests passed
```

The tests cover:

- exact public signatures and default values;
- safe import of both old and new paths;
- old/new function object identity, proving no duplicate implementation;
- exact old/new array equality;
- standard schedule producing 262 values, starting at `0.0`, ending at `1826.25`, with the existing shorter final gap;
- exact endpoint inclusion and cadence-larger-than-interval behaviour;
- schedule validation order and exact error messages;
- linear interpolation shape, values, endpoint positions, and input non-mutation;
- interpolation error paths and exact messages;
- observer defaults producing `[0, 1, 0]` at `t=0`;
- quarter-period motion, radius scaling, and period scaling;
- relative-position subtraction order, shape, and input non-mutation;
- observer and relative-position error paths and validation order;
- exact error messages for all tested invalid inputs.

The new tests use in-memory NumPy arrays only. They do not write into `configs/`, `data/`, `results/`, or `plots/`.

### 5.2 Existing read-only checks

The existing scripts were run from the repository root with `PYTHONDONTWRITEBYTECODE=1`:

```powershell
& .venv\Scripts\python.exe tests\test_observation_schedule.py
& .venv\Scripts\python.exe tests\test_observer_model.py
& .venv\Scripts\python.exe tests\test_coordinate_converter.py
& .venv\Scripts\python.exe tests\test_measurement_noise.py
```

All exited successfully.

Observed results:

- trajectory loaded with 1001 samples;
- observation schedule produced 262 observations;
- first observation day `0.0`, last observation day `1826.25`;
- interpolated positions shape `(262, 3)`;
- observer initial position was `[6.123234e-17, 1.0, 0.0]` AU, equivalent to the expected `[0, 1, 0]` within tolerance;
- coordinate conversion still produced 262 coordinates;
- measurement noise reproducibility check passed.

### 5.3 Import and entry-point checks

```powershell
& .venv\Scripts\python.exe -m src.observation_generator --help
```

Exit code: `0`. The help output was unchanged.

The old and new imports were also checked directly:

```python
from src.observation_schedule import (
    generate_observation_times,
    interpolate_positions,
)
from src.observer_model import (
    calculate_observer_positions,
    calculate_relative_positions,
)
from orbit_discovery.component2_observations.schedule import (
    generate_observation_times as new_generate,
    interpolate_positions as new_interpolate,
)
from orbit_discovery.component2_observations.observer import (
    calculate_observer_positions as new_observer,
    calculate_relative_positions as new_relative,
)
```

The corresponding old and new functions are the same objects:

```text
OLD_NEW_IMPORT_IDENTITY_OK
```

This confirms that the old paths re-export the new implementations rather than retaining duplicates.

### 5.4 Repository integrity

```powershell
git diff --check
```

No whitespace errors.

No changes were made under `data`, `configs`, `results`, or `plots`. No observation generation, simulation, or data-writing workflow was run.

## 6. Scientific invariants preserved

### Schedule

- `generate_observation_times` validation order is unchanged: cadence, end-versus-start, start range, end range.
- `np.arange(..., dtype=float)` and the exact `np.isclose(..., atol=1e-9)` endpoint append are unchanged.
- The standard scenario remains 262 observations with a 6.25-day final gap.
- `interpolate_positions` remains linear per axis via `np.interp`.
- The output remains `(M, 3)` in input row order.
- Extrapolation is still rejected.
- All existing error messages and validation order are unchanged.

### Observer

- The observer remains an idealized circular, coplanar, heliocentric model.
- The formula `2*pi*t/T + phase` is unchanged.
- Defaults remain `orbital_radius_au=1.0`, `orbital_period_years=1.0`, `initial_phase_deg=90.0`.
- The default initial position remains `[0, 1, 0]` AU within floating tolerance.
- `calculate_relative_positions` still returns `asteroid_positions - observer_positions`.
- Shape validation order and all existing error messages are unchanged.

No light-time, aberration, topocentric, ephemeris, precession, or other scientific change was introduced.

## 7. Git status

Immediately after validation and before creating this report:

```text
 M src/observation_schedule.py
 M src/observer_model.py
?? docs/development/PHASE_1_STEP_1_ASSESSMENT.md
?? docs/development/PHASE_1_STEP_2_CORE_ASSESSMENT.md
?? docs/development/PHASE_1_STEP_3_2_1_INSTALL_ASSESSMENT.md
?? docs/development/PHASE_1_STEP_3_2_2_INSTALL_VALIDATION.md
?? docs/development/PHASE_1_STEP_3_COMPONENT2_ASSESSMENT.md
?? pyproject.toml
?? src/orbit_discovery/
?? tests/test_component2_observer.py
?? tests/test_component2_schedule.py
?? tests/test_core_constants.py
?? tests/test_core_paths.py
```

`git diff --stat` shows only the two intended shim replacements. `git ls-files -m` lists only:

```text
src/observation_schedule.py
src/observer_model.py
```

`git diff --name-only -- data configs results plots` is empty. No tracked data, configuration, result, or plot file was modified.

This report is the only additional documentation file created by C3.2.3.

## 8. Rollback procedure

If rollback is required:

```powershell
git restore src/observation_schedule.py src/observer_model.py
Remove-Item src\orbit_discovery\component2_observations\schedule.py
Remove-Item src\orbit_discovery\component2_observations\observer.py
Remove-Item tests\test_component2_schedule.py
Remove-Item tests\test_component2_observer.py
```

This restores the original implementations from Git and removes the new modules and focused tests. No data rollback is needed. Do not remove other files under `src/orbit_discovery/`.

No rollback was performed.

## 9. Result

C3.2.3 passed:

- both implementations were moved verbatim;
- both old paths remain usable through thin shims;
- no duplicate implementations remain;
- public signatures, defaults, return shapes, and exceptions are preserved;
- 38 new focused tests pass;
- existing schedule, observer, coordinate, and noise read-only checks pass;
- `python -m src.observation_generator --help` still succeeds;
- no dependency, configuration, dataset, result, or plot change occurred;
- no commit, tag, or push was made.
