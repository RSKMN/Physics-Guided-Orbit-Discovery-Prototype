# Phase 1 — C3.4.1: Trajectory Loader Migration

**Status:** Migration complete. The loader implementation was moved verbatim, the old path was replaced with a thin compatibility shim, the approved `DAYS_PER_YEAR` constant was integrated, and all focused, regression, and pre-migration comparison checks passed.

**Repository:** `E:\rskmn\Npersonal\projects\yr4\final\prototype-1\physics-guided-orbit-discovery-prototype`

**Scope:** Migrate `src/trajectory_loader.py` into `orbit_discovery.component2_observations.loader`, preserving CSV parsing, validation, errors, print output, and return contracts.

No observation generation, simulation, configuration change, dataset change, result change, or plot change was performed.

## 1. Files migrated and created

| Path | Change |
|---|---|
| `src/orbit_discovery/component2_observations/loader.py` | Created; contains the moved trajectory-loader implementation. |
| `src/trajectory_loader.py` | Replaced with a thin compatibility shim. |
| `tests/test_component2_loader.py` | Created; 17 focused hermetic tests. |
| `src/observation_generator.py` | Unchanged. |
| `src/orbit_discovery/component2_observations/__init__.py` | Unchanged. |
| `pyproject.toml` | Unchanged. |

## 2. API preservation

The moved public API is:

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

Preserved:

- exact `REQUIRED_COLUMNS` contents and order;
- exact `load_trajectory(csv_path)` signature;
- `Path(csv_path)` handling;
- exact `FileNotFoundError` message;
- Pandas CSV reading and required-column selection;
- required-column validation order;
- `pd.to_numeric(errors="coerce")` handling;
- missing/non-numeric and non-finite validation;
- at-least-two-samples validation;
- strictly increasing `time_years` validation;
- time-column consistency validation with `rtol=0`, `atol=1e-6`;
- position and velocity column selection and ordering;
- returned dictionary key order;
- array shapes and ordering;
- the three progress `print()` lines;
- docstring and meaningful comments.

The function body beginning at `def load_trajectory` is an exact source match to the pre-migration file after replacing only the `365.25` conversion expression with `DAYS_PER_YEAR`.

## 3. Shared constant substitution

### 3.1 Exact change

The original consistency check used:

```python
time_years * 365.25
```

The new loader uses:

```python
from orbit_discovery.core.constants import DAYS_PER_YEAR
...
time_years * DAYS_PER_YEAR
```

No other expression or operation was changed.

### 3.2 Numerical-equivalence evidence

The original literal and the shared constant are the same IEEE-754 double:

```text
365.25                         -> 4076d40000000000
core.constants.DAYS_PER_YEAR   -> 4076d40000000000
```

Additional evidence:

- `REQUIRED_COLUMNS` is an exact match to the original list.
- The loader function body is an exact source match after the single constant replacement.
- Valid CSV parsing returns the same arrays and values as the pre-migration implementation.
- Time-column consistency uses the same tolerance and comparison order.
- The pre-migration comparison script reported `MATCH` for valid data, missing columns, invalid numeric values, infinite values, too few samples, non-increasing timestamps, inconsistent time columns, and a missing file.
- Printed output and error types/messages matched in every compared case.

The substitution is numerically exact and does not change CSV interpretation or time conversion.

## 4. Compatibility shim

`src/trajectory_loader.py` now contains only:

```python
"""Compatibility shim for the old ``src.trajectory_loader`` path."""

from orbit_discovery.component2_observations.loader import (
    REQUIRED_COLUMNS,
    load_trajectory,
)

__all__ = [
    "REQUIRED_COLUMNS",
    "load_trajectory",
]
```

The shim:

- contains no scientific logic or duplicate implementation;
- uses the approved editable installation and absolute `orbit_discovery` imports;
- does not manipulate `sys.path`;
- explicitly re-exports `REQUIRED_COLUMNS` and `load_trajectory`;
- preserves old `from src.trajectory_loader import ...` imports;
- references the same function and list objects as the new module.

An AST check confirmed that the old file contains no function or class definitions and is a thin shim.

## 5. Tests

### 5.1 New focused loader tests

```powershell
& .venv\Scripts\python.exe tests\test_component2_loader.py -v
```

Result:

```text
17 tests passed
```

Coverage includes:

- `REQUIRED_COLUMNS` content and order;
- exact `load_trajectory(csv_path)` signature;
- valid temporary CSV loading;
- returned dictionary key order;
- `number_of_samples`;
- time, position, and velocity shapes and dtypes;
- position and velocity value/order preservation;
- exact progress output;
- extra-column handling;
- `DAYS_PER_YEAR` time conversion;
- time-consistency tolerance;
- missing-file error type and exact message;
- missing required columns and exact message;
- invalid/non-numeric and empty numeric values;
- infinite/non-finite values;
- too few samples;
- non-increasing timestamps;
- inconsistent time columns;
- validation order;
- old/new import identity and identical output/contract.

The tests use temporary directories and CSV fixtures only. They do not write into `configs/`, `data/`, `results/`, or `plots/`.

### 5.2 Component 2 focused suite

```powershell
& .venv\Scripts\python.exe -m unittest discover -s tests -p "test_component2_*.py" -q
```

Result:

```text
Ran 90 tests
OK
```

Breakdown:

| Test file | Tests |
|---|---:|
| `tests/test_component2_loader.py` | 17 |
| `tests/test_component2_schedule.py` | 20 |
| `tests/test_component2_observer.py` | 18 |
| `tests/test_component2_frames.py` | 18 |
| `tests/test_component2_noise.py` | 17 |

### 5.3 Existing read-only checks

```powershell
& .venv\Scripts\python.exe tests\test_trajectory_loader.py
& .venv\Scripts\python.exe tests\test_observation_schedule.py
& .venv\Scripts\python.exe tests\test_observer_model.py
& .venv\Scripts\python.exe tests\test_coordinate_converter.py
& .venv\Scripts\python.exe tests\test_measurement_noise.py
```

All exited successfully.

Observed unchanged results:

- trajectory loaded with 1001 samples;
- position and velocity shapes `(1001, 3)`;
- first and last asteroid positions unchanged;
- schedule produced 262 observations from day `0.0` to `1826.25`;
- observer initial position remained equivalent to `[0, 1, 0]` AU;
- coordinate conversion produced 262 coordinates;
- measurement noise produced 262 observations and the reproducibility check passed.

### 5.4 Pre-migration implementation comparison

A separate temporary validation script executed the pre-migration loader source from Git alongside the new package loader.

Compared fixtures:

```text
valid
missing_columns
invalid_numeric
infinite
too_few
non_increasing
inconsistent_time
missing_file
```

Every fixture reported `MATCH`:

```text
PRE_MIGRATION_COMPARISON_OK=True
```

For valid data, this compared dictionary key order, all array values, sample count, and printed output exactly. For invalid data, it compared exception type, message, and captured output exactly.

### 5.5 Import, entry point, and environment checks

```powershell
& .venv\Scripts\python.exe -c "...all old/new import identity..."
& .venv\Scripts\python.exe -m src.observation_generator --help
& .venv\Scripts\python.exe -m pip check
git diff --check
```

Results:

- `ALL_OLD_NEW_IMPORT_IDENTITY_OK`
- observation-generator help exit code `0`
- `pip check`: `No broken requirements found.`
- `git diff --check`: no whitespace errors

The observation generator was not executed.

## 6. Scientific invariants checked

- Required CSV schema is unchanged in content and order.
- Extra columns are ignored.
- CSV values are interpreted through the same Pandas path.
- Time conversion still uses `365.25` days per year, now via `DAYS_PER_YEAR`.
- Time consistency still uses `rtol=0`, `atol=1e-6`.
- `time_years` must be strictly increasing.
- At least two samples are required.
- Positions and velocities remain `(N, 3)` and preserve CSV row order.
- Position columns remain `x_au`, `y_au`, `z_au`.
- Velocity columns remain `vx_au_per_year`, `vy_au_per_year`, `vz_au_per_year`.
- Returned dictionary keys and ordering are unchanged.
- Units remain years, days, AU, and AU/year.
- The three progress print lines remain.
- Error types, messages, and validation order are unchanged.
- No velocity-position consistency check, metadata read, or configuration lookup was added.

## 7. Deviations and limitations

No scientific or behavioural deviation was introduced.

The only intentional implementation change is the approved `DAYS_PER_YEAR` import and expression substitution. The new package module uses LF line endings consistent with the existing package modules; the old shim retains its original CRLF line endings.

`observation_generator.py`, Component 1, CLI, configuration loading, metadata writing, scientific configurations, datasets, results, plots, dependencies, and `pyproject.toml` were not modified.

## 8. Git status

Immediately after validation and before creating this report:

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

The C3.4.1 tracked modification is:

```text
src/trajectory_loader.py
```

The other tracked shim modifications are inherited from C3.2.3 and C3.3.1. `git diff --stat` shows only the five intended shim replacements.

`git diff --name-only -- data configs results plots` is empty. No tracked dataset, configuration, result, or plot file was modified. This report is the only additional documentation file created by C3.4.1.

## 9. Rollback procedure

If rollback is required for this checkpoint only:

```powershell
git restore src/trajectory_loader.py
Remove-Item src\orbit_discovery\component2_observations\loader.py
Remove-Item tests\test_component2_loader.py
```

Do not restore or delete the earlier schedule, observer, frames, or noise migrations as part of this rollback. No data rollback is needed. No rollback was performed.

## 10. Result

C3.4.1 passed:

- the trajectory loader was moved verbatim except for the approved `DAYS_PER_YEAR` substitution;
- the old path remains usable through a thin shim;
- old and new imports reference identical objects;
- 17 new focused loader tests pass;
- all 90 Component 2 focused tests pass;
- all requested existing read-only pipeline checks pass;
- the pre-migration implementation comparison matched for valid and invalid fixtures;
- the observation-generator help command still succeeds;
- `pip check` and `git diff --check` pass;
- no scientific behaviour, configuration, dataset, result, plot, dependency, or orchestration file changed;
- no commit, tag, or push was made.
