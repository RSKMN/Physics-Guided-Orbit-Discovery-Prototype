# Phase 1 — C3.3.1: Frames and Noise Module Migration

**Status:** Migration complete. Both implementations were moved, the old paths were replaced with thin compatibility shims, the approved shared constant was integrated into noise, and all focused and existing read-only checks passed.

**Repository:** `E:\rskmn\Npersonal\projects\yr4\final\prototype-1\physics-guided-orbit-discovery-prototype`

**Scope:** Migrate `src/coordinate_converter.py` and `src/measurement_noise.py` into `orbit_discovery.component2_observations`, preserving scientific behaviour and old import paths.

No observation generation, simulation, configuration change, dataset change, result change, or plot change was performed.

## 1. Files migrated and created

| Path | Change |
|---|---|
| `src/orbit_discovery/component2_observations/frames.py` | Created; contains the moved `coordinate_converter` implementation. |
| `src/orbit_discovery/component2_observations/noise.py` | Created; contains the moved `measurement_noise` implementation and imports the shared `ARCSEC_TO_DEG`. |
| `src/coordinate_converter.py` | Replaced with a thin compatibility shim. |
| `src/measurement_noise.py` | Replaced with a thin compatibility shim. |
| `tests/test_component2_frames.py` | Created; 18 focused hermetic tests. |
| `tests/test_component2_noise.py` | Created; 17 focused hermetic tests. |
| `src/observation_generator.py` | Unchanged. |
| `src/orbit_discovery/component2_observations/__init__.py` | Unchanged. |
| `pyproject.toml` | Unchanged. |

## 2. API preservation

### 2.1 Frames

The moved public API is:

```python
def ecliptic_to_equatorial(
    relative_positions,
    obliquity_deg=23.43928
):
    ...

def calculate_ra_dec(equatorial_positions):
    ...
```

Preserved:

- exact parameter names, order, and defaults;
- default obliquity `23.43928`;
- input conversion to `float`;
- `(N, 3)` shape validation;
- finite-value validation;
- validation order;
- exact exception messages;
- rotation equations and operation ordering;
- RA/Dec formulas and return order;
- `(N, 3)`, `(N,)`, and tuple return shapes;
- docstrings and comments.

`OBLIQUITY_DEG` was not moved to `core.constants`. The default remains local to `frames.py`.

### 2.2 Noise

The moved public API is:

```python
ARCSEC_TO_DEG

def add_measurement_noise(
    ra_deg,
    dec_deg,
    sigma_ra_cosdec_arcsec=0.5,
    sigma_dec_arcsec=0.5,
    random_seed=42
):
    ...
```

Preserved:

- `ARCSEC_TO_DEG` as a public module attribute;
- exact parameter names, order, and defaults;
- RA/Dec shape equality validation;
- finite-coordinate validation;
- declination range validation;
- non-negative uncertainty validation;
- pole-singularity validation;
- noisy-declination range validation;
- exact exception messages and validation order;
- `np.random.default_rng(random_seed)`;
- RA-first and Dec-second normal draws;
- standard deviations and tangent-plane RA conversion;
- operation ordering and return tuple order;
- docstrings and comments.

## 3. Shared constant substitution

### 3.1 Exact change

The original noise module defined:

```python
ARCSEC_TO_DEG = 1.0 / 3600.0
```

The new module uses the approved shared constant:

```python
from orbit_discovery.core.constants import ARCSEC_TO_DEG
```

No other line in the noise implementation was changed. The function body beginning at `def add_measurement_noise` is an exact source match to the pre-migration file, ignoring line-ending style.

### 3.2 Numerical-equivalence evidence

The local expression and the shared constant are the same IEEE-754 double:

```text
1.0 / 3600.0                  -> 3f323456789abcdf
core.constants.ARCSEC_TO_DEG  -> 3f323456789abcdf
```

Additional evidence:

- `noise.ARCSEC_TO_DEG == 1.0 / 3600.0` is true.
- `noise.ARCSEC_TO_DEG is old_shim.ARCSEC_TO_DEG` is true.
- The old and new seeded outputs are exactly equal.
- The new focused test `test_seeded_outputs_match_pre_migration_values` asserts the exact four output arrays produced by the pre-migration implementation for a fixed input and seed.
- No noise draw was added, removed, reordered, or rescaled.
- Units remain arcseconds for the noise arrays and degrees for the coordinate offsets.

The substitution is therefore numerically exact, not merely approximate.

## 4. Compatibility shims

### 4.1 `src/coordinate_converter.py`

```python
"""Compatibility shim for the old ``src.coordinate_converter`` path."""

from orbit_discovery.component2_observations.frames import (
    ecliptic_to_equatorial,
    calculate_ra_dec,
)

__all__ = [
    "ecliptic_to_equatorial",
    "calculate_ra_dec",
]
```

### 4.2 `src/measurement_noise.py`

```python
"""Compatibility shim for the old ``src.measurement_noise`` path."""

from orbit_discovery.component2_observations.noise import (
    ARCSEC_TO_DEG,
    add_measurement_noise,
)

__all__ = [
    "ARCSEC_TO_DEG",
    "add_measurement_noise",
]
```

The shims:

- contain no scientific logic or duplicate formulas;
- use the approved editable installation and absolute `orbit_discovery` imports;
- do not manipulate `sys.path`;
- explicitly re-export only documented public names;
- re-export `ARCSEC_TO_DEG` through the old noise path;
- preserve old `from src.* import ...` imports;
- reference identical function objects to the new modules.

An AST check confirmed that both old files contain no function or class definitions and are thin shims.

## 5. Tests

### 5.1 New focused tests

```powershell
& .venv\Scripts\python.exe tests\test_component2_frames.py -v
& .venv\Scripts\python.exe tests\test_component2_noise.py -v
```

Results:

```text
test_component2_frames.py: 18 tests passed
test_component2_noise.py: 17 tests passed
```

Coverage includes:

- exact public signatures and defaults;
- old/new import identity;
- exact old/new output equality;
- default obliquity and default noise parameters;
- identity rotation at zero obliquity;
- 90-degree obliquity axis mapping;
- known default-obliquity rotation;
- RA/Dec cardinal directions, RA normalization, and pole boundaries;
- zero-vector, shape, and finite-value errors;
- seeded deterministic noise outputs;
- zero-sigma behaviour;
- RA wrap;
- noise units and `ARCSEC_TO_DEG` equality with `core.constants`;
- mismatched shape, non-finite input, declination range, negative sigma, pole singularity, and noisy-declination errors;
- input non-mutation;
- return shapes, dtypes, and tuple order.

The tests use in-memory NumPy arrays only and do not write into `configs/`, `data/`, `results/`, or `plots/`.

### 5.2 Existing regression checks

```powershell
& .venv\Scripts\python.exe tests\test_coordinate_converter.py
& .venv\Scripts\python.exe tests\test_measurement_noise.py
& .venv\Scripts\python.exe tests\test_observation_schedule.py
& .venv\Scripts\python.exe tests\test_observer_model.py
```

All exited successfully.

Observed unchanged results:

- coordinate conversion produced 262 coordinates;
- first RA/Dec values were unchanged;
- measurement noise produced 262 observations;
- first noisy RA/Dec values were unchanged;
- noise reproducibility check passed;
- schedule still produced 262 observations;
- observer initial position remained `[6.123234e-17, 1.0, 0.0]` AU, equivalent to `[0, 1, 0]` within tolerance.

### 5.3 Import, entry point, and environment checks

```powershell
& .venv\Scripts\python.exe -c "...old/new import identity..."
& .venv\Scripts\python.exe -m src.observation_generator --help
& .venv\Scripts\python.exe -m pip check
git diff --check
```

Results:

- `OLD_NEW_IMPORT_IDENTITY_OK`
- observation-generator help exit code `0`
- `pip check`: `No broken requirements found.`
- `git diff --check`: no whitespace errors

No observation generator run, simulation, or data-writing workflow was executed.

## 6. Scientific invariants checked

### Frames

- `ecliptic_to_equatorial` returns `(N, 3)` float arrays.
- Obliquity `0` is an identity rotation within floating tolerance.
- Obliquity `90` maps `(0, 1, 0)` to `(0, 0, 1)` and `(0, 0, 1)` to `(0, -1, 0)`.
- Default obliquity remains exactly `23.43928`.
- RA is normalized to `[0, 360)`.
- Dec remains within `[-90, 90]` for finite non-zero vectors.
- Zero vectors are rejected.
- Shape validation precedes finite-value validation.
- Inputs are not mutated.

### Noise

- `ARCSEC_TO_DEG` is exactly `1.0 / 3600.0`.
- The RNG constructor remains `np.random.default_rng(random_seed)`.
- RA noise is drawn before Dec noise.
- Defaults remain `0.5`, `0.5`, and `42`.
- Zero sigma produces zero offsets and unchanged coordinates.
- RA offsets use the tangent-plane `sigma_RA * cos(Dec)` conversion.
- RA remains modulo 360.
- Pole singularity is rejected when RA sigma is positive.
- Noisy declination outside `[-90, 90]` is rejected.
- Return order remains `(noisy_ra_deg, noisy_dec_deg, ra_noise_arcsec, dec_noise_arcsec)`.
- Inputs are not mutated.

## 7. Limitations and deviations

No scientific limitation or behavioural deviation was introduced.

The only intentional implementation change is the approved shared-constant import in `noise.py`. The frames module is an exact source copy of the original implementation, ignoring line-ending style. New package files use LF line endings consistent with the existing package modules; the old shims retain their original CRLF line endings.

`trajectory_loader.py` and `observation_generator.py` were not migrated or modified. No Component 1, CLI, configuration, metadata, dataset, result, plot, dependency, or `pyproject.toml` change was made.

## 8. Git status

Immediately after validation and before creating this report:

```text
 M src/coordinate_converter.py
 M src/measurement_noise.py
 M src/observation_schedule.py
 M src/observer_model.py
?? docs/development/PHASE_1_STEP_1_ASSESSMENT.md
?? docs/development/PHASE_1_STEP_2_CORE_ASSESSMENT.md
?? docs/development/PHASE_1_STEP_3_2_1_INSTALL_ASSESSMENT.md
?? docs/development/PHASE_1_STEP_3_2_2_INSTALL_VALIDATION.md
?? docs/development/PHASE_1_STEP_3_2_3_SCHEDULE_OBSERVER_MIGRATION.md
?? docs/development/PHASE_1_STEP_3_COMPONENT2_ASSESSMENT.md
?? pyproject.toml
?? src/orbit_discovery/
?? tests/test_component2_frames.py
?? tests/test_component2_noise.py
?? tests/test_component2_observer.py
?? tests/test_component2_schedule.py
?? tests/test_core_constants.py
?? tests/test_core_paths.py
```

The C3.3.1 tracked modifications are:

```text
src/coordinate_converter.py
src/measurement_noise.py
```

The other two tracked modifications, `src/observation_schedule.py` and `src/observer_model.py`, are inherited from C3.2.3. `git diff --stat` shows only those four intended shim replacements.

`git diff --name-only -- data configs results plots` is empty. No tracked data, configuration, result, or plot file was modified. This report is the only additional documentation file created by C3.3.1.

## 9. Rollback procedure

If rollback is required for this checkpoint only:

```powershell
git restore src/coordinate_converter.py src/measurement_noise.py
Remove-Item src\orbit_discovery\component2_observations\frames.py
Remove-Item src\orbit_discovery\component2_observations\noise.py
Remove-Item tests\test_component2_frames.py
Remove-Item tests\test_component2_noise.py
```

Do not restore or delete the C3.2.3 schedule/observer migration files as part of this rollback. No data rollback is needed. No rollback was performed.

## 10. Result

C3.3.1 passed:

- `coordinate_converter` moved verbatim to `frames.py`;
- `measurement_noise` moved to `noise.py` with only the approved shared-constant substitution;
- old paths remain usable through thin shims;
- old and new imports reference identical function objects;
- 35 new focused tests pass;
- all requested existing read-only regression checks pass;
- the observation-generator help command still succeeds;
- `pip check` and `git diff --check` pass;
- no scientific behaviour, dependency, configuration, dataset, result, or plot changed;
- no commit, tag, or push was made.
