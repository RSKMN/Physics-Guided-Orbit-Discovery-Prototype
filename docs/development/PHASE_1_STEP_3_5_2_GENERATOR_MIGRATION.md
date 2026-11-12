# Phase 1 — C3.5.2: Observation Generator Migration

**Status:** Migration complete. The implementation moved to the package, the old
path is a thin compatibility shim, and all focused, regression, and temporary
fixture equivalence checks passed.

**Repository:** `E:\rskmn\Npersonal\projects\yr4\final\prototype-1\physics-guided-orbit-discovery-prototype`

**Scope:** Move `src/observation_generator.py` into
`orbit_discovery.component2_observations.generator`, preserve the old module
entry point, correct the file-relative repository root, and prove equivalent
behaviour without regenerating tracked datasets.

No observation generation was run against the tracked project configurations or
datasets. No Component 1, CLI, dependency, configuration, dataset, result, or
plot change was made. No commit, tag, or push was made.

---

## 1. Files changed

| Path | Change |
|---|---|
| `src/orbit_discovery/component2_observations/generator.py` | Created; contains the moved orchestration implementation. |
| `src/observation_generator.py` | Replaced with a thin compatibility shim. |
| `tests/test_component2_generator.py` | Created; 23 focused temporary-fixture tests. |
| `docs/development/PHASE_1_STEP_3_5_2_GENERATOR_MIGRATION.md` | This report. |
| `src/orbit_discovery/component2_observations/__init__.py` | Unchanged; no broad exports were added. |
| `pyproject.toml`, five helper modules/shims, configs, data, results, plots | Unchanged. |

The new package module imports the five migrated helpers directly. It does not
import any old `src.*` compatibility shim.

---

## 2. Public API preservation

The new module preserves the original public names:

| Name | New location | Signature / value |
|---|---|---|
| `load_config` | `generator.py` | `load_config(config_path)` |
| `generate_observations` | `generator.py` | `generate_observations(config_path)` |
| `main` | `generator.py` | `main()` |
| `PROJECT_ROOT` | `generator.py` | Repository root (`Path`) |
| `DAYS_PER_YEAR` | `generator.py` | `365.25` |

Preserved:

- exact function parameter names, ordering, kinds, and defaults;
- `load_config()` return tuple `(config, config_path)`;
- `generate_observations()` return tuple `(observations, metadata)`;
- `main()` return of `None` on success;
- module constants and their values;
- all existing output, metadata, print, and exception behaviour.

`DAYS_PER_YEAR` remains the local `365.25` constant. It was not replaced with
`core.constants.DAYS_PER_YEAR` in this checkpoint; the value is identical and the
move was limited to import and package-location adaptations.

An AST comparison against the pre-migration source from Git showed that the
`load_config`, `generate_observations`, and `main` function definitions are
identical after the move. Only module imports and the `PROJECT_ROOT` expression
changed.

---

## 3. Import changes

The old imports were:

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

The new package module uses:

```python
from orbit_discovery.component2_observations.loader import load_trajectory
from orbit_discovery.component2_observations.schedule import (
    generate_observation_times,
    interpolate_positions,
)
from orbit_discovery.component2_observations.observer import (
    calculate_observer_positions,
    calculate_relative_positions,
)
from orbit_discovery.component2_observations.frames import (
    ecliptic_to_equatorial,
    calculate_ra_dec,
)
from orbit_discovery.component2_observations.noise import add_measurement_noise
```

There are no imports from the old shims in the new generator and no
`core.paths` import.

Standard-library and third-party imports are unchanged:

```python
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
```

---

## 4. Repository-root verification

The original expression was:

```python
PROJECT_ROOT = Path(__file__).resolve().parents[1]
```

The new package module uses:

```python
PROJECT_ROOT = Path(__file__).resolve().parents[3]
```

Verified in the actual checkout:

```text
generator: ...\src\orbit_discovery\component2_observations\generator.py
calculated root: ...\physics-guided-orbit-discovery-prototype
repository root: ...\physics-guided-orbit-discovery-prototype
root matches: True
```

The parent chain is:

```text
parents[0] = ...\src\orbit_discovery\component2_observations
parents[1] = ...\src\orbit_discovery
parents[2] = ...\src
parents[3] = ...\physics-guided-orbit-discovery-prototype
```

No current-working-directory fallback was introduced. `core.paths` was not
integrated. Default config selection, relative config paths, relative input
trajectory paths, relative output directories, absolute path handling, and
metadata path strings are unchanged.

---

## 5. Compatibility entry point

`src/observation_generator.py` now contains only:

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

The shim:

- contains no function or class definitions;
- contains no scientific logic or duplicated implementation;
- explicitly re-exports the five public names;
- preserves `python -m src.observation_generator`;
- uses the standard `if __name__ == "__main__":` guard;
- relies on the existing editable package installation;
- does not manipulate `sys.path`;
- does not attempt to change the separately documented direct-script
  invocation behaviour.

Verified identity:

```text
old.load_config is new.load_config                         -> True
old.generate_observations is new.generate_observations     -> True
old.main is new.main                                       -> True
old.PROJECT_ROOT == new.PROJECT_ROOT                       -> True
old.DAYS_PER_YEAR == new.DAYS_PER_YEAR                     -> True
```

`component2_observations/__init__.py` was not changed. Direct imports from the
generator module remain the preferred package API.

---

## 6. Temporary-fixture test results

New test file:

```text
tests/test_component2_generator.py
```

Run:

```powershell
& .venv\Scripts\python.exe tests\test_component2_generator.py -v
```

Result:

```text
Ran 23 tests in 0.588s
OK
```

Coverage:

### Configuration

- default `--config` value captured through a mocked `generate_observations`;
- explicit `--config` value captured;
- relative config path resolved against `PROJECT_ROOT`;
- absolute config path preserved;
- missing config file and exact error message;
- malformed JSON decoder error;
- missing required top-level key (`KeyError`);
- missing trajectory file and exact error message;
- invalid schedule cadence and exact `ValueError` message.

### Observation generation

- valid synthetic 11-row trajectory;
- 6 generated observations from a 0–10 day, 2-day cadence fixture;
- exact CSV columns and order;
- exact row count and `float64` data types;
- exact reference time values and seeded RA/Dec values;
- sigma columns constant at `0.5` arcsec;
- returned DataFrame equal to the written CSV;
- noise-free truth columns enabled;
- noise-free truth columns disabled;
- metadata writing disabled;
- output directory structure and filenames;
- output directory reuse;
- deterministic seeded noise across repeated runs;
- success-summary print content.

### Metadata

- exact key list and insertion order;
- absolute input/config path strings;
- relative input/config path strings under a patched project root;
- config-derived schedule, observer, coordinates, and noise values;
- coordinate units and assumptions exact values/order;
- `output_file` value;
- no `output` config section in metadata;
- metadata file content equal to the returned metadata dictionary.

### Compatibility

- old/new imports;
- function identity;
- constant equality;
- thin-shim AST check (no function or class definitions);
- legacy module CLI help.

All tests use `tempfile.TemporaryDirectory()` and synthetic CSV/JSON fixtures.
No test writes into `configs/`, `data/`, `results/`, or `plots/`.

### Full focused suite

```powershell
& .venv\Scripts\python.exe -m unittest discover -s tests -p "test_component2_*.py" -q
```

Result:

```text
Ran 113 tests in 0.639s
OK
```

Breakdown:

| Test file | Tests |
|---|---:|
| `tests/test_component2_generator.py` | 23 |
| `tests/test_component2_loader.py` | 17 |
| `tests/test_component2_schedule.py` | 20 |
| `tests/test_component2_observer.py` | 18 |
| `tests/test_component2_frames.py` | 18 |
| `tests/test_component2_noise.py` | 17 |

### Existing read-only Component 2 checks

The following exited successfully with their existing output:

```powershell
& .venv\Scripts\python.exe tests\test_trajectory_loader.py
& .venv\Scripts\python.exe tests\test_observation_schedule.py
& .venv\Scripts\python.exe tests\test_observer_model.py
& .venv\Scripts\python.exe tests\test_coordinate_converter.py
& .venv\Scripts\python.exe tests\test_measurement_noise.py
& .venv\Scripts\python.exe tests\test_observation_output.py
& .venv\Scripts\python.exe tests\test_all_observation_outputs.py
```

Observed unchanged values included:

- 1001 trajectory samples over 0–5 years;
- 262 observations from day 0.0 to 1826.25;
- first true RA/Dec `335.41094451966364`, `-10.226416094059436`;
- noise reproducibility check passed;
- all three tracked observation datasets validated with 262 rows each.

---

## 7. CSV and metadata equivalence results

A separate temporary comparison executed the pre-migration implementation from
Git (`git show HEAD:src/observation_generator.py`) alongside the new package
module. Both used the same synthetic trajectory and the same config file path;
only the output directory differed between the two runs. The output directory is
not included in metadata, so metadata can be compared exactly.

Comparison result:

```text
COLUMNS_EQUAL        True
SHAPE                (6, 8) (6, 8)
FRAME_EQUAL_EXACT    True
CSV_BYTES_EQUAL      True
METADATA_EQUAL       True
METADATA_BYTES_EQUAL True
DTYPES_EQUAL         True
METADATA_KEYS_EQUAL  True
```

The fixtures used:

- 11 trajectory rows from day 0 to 10;
- observation cadence 2 days;
- schedule `start_day=0.0`, `end_day=10.0`;
- observer radius 1.0 AU, period 1.0 year, phase 90°;
- obliquity `23.43928°`;
- noise sigmas `0.5` arcsec and seed `42`;
- 6 generated observations.

The comparison covered:

- exact column names and order;
- row count and `float64` dtypes;
- exact time arrays;
- exact noisy RA/Dec arrays;
- exact true RA/Dec arrays;
- exact sigma arrays;
- exact CSV bytes;
- complete metadata dictionary equality;
- exact metadata JSON bytes;
- metadata key order.

The new test file hardcodes the reference time and RA/Dec values from this
pre-migration run and compares generated results with a strict
`rtol=0, atol=1e-12` tolerance for floating-point columns.

No environment-dependent metadata difference remained after using the same
config and trajectory paths. The earlier exploratory comparison that used
different config filenames differed only in the expected
`configuration_file` string; that was a fixture difference, not a behaviour
difference, and was eliminated by the controlled comparison above.

The comparison used temporary directories only. It did not read or overwrite the
tracked project observation datasets, results, or plots.

---

## 8. Scientific behaviour preservation

The following were preserved:

- observation cadence and endpoint inclusion (`np.arange` plus exact end
  append);
- days-to-years conversion with `365.25`;
- linear `np.interp` position interpolation;
- circular, coplanar observer model with the same phase convention;
- relative vector `asteroid - observer`;
- ecliptic-to-equatorial rotation and configured obliquity;
- `atan2`-based RA/Dec calculation and RA modulo;
- seeded Gaussian noise using `default_rng`, with RA drawn before Dec;
- tangent-plane RA noise conversion through `cos(Dec)`;
- observation count and time values;
- CSV column names, order, and types;
- optional truth columns `true_ra_deg` and `true_dec_deg`;
- metadata keys, values, ordering, assumptions, and path representations;
- output directory and filenames;
- print messages and exception propagation.

No algorithm, configuration schema, CSV schema, metadata schema, seed, noise
setting, or truth column was changed. Component 1 was not modified.

---

## 9. Limitations and deviations

- `core.paths` integration was deliberately deferred, as approved. The
  generator still uses the file-relative repository root and does not consult
  `ORBIT_DISCOVERY_ROOT` or marker discovery.
- The local `DAYS_PER_YEAR = 365.25` was retained rather than replaced with
  `core.constants.DAYS_PER_YEAR`. The numeric value is identical, and the move
  was limited to import and root adaptations.
- The compatibility shim was rewritten with LF line endings. Git reports the
  usual working-copy warning that LF will be replaced by CRLF when touched
  under the current line-ending configuration. This is a formatting detail, not
  a behaviour change.
- Direct-script invocation (`python src\observation_generator.py`) was not used
  as an acceptance gate and was not changed deliberately. The documented module
  form `python -m src.observation_generator` is verified.
- Equivalence was proven with a controlled synthetic fixture rather than by
  regenerating the tracked observation datasets. This respects the checkpoint
  restriction and avoids modifying scientific outputs. The existing tracked
  datasets were validated read-only and remain unchanged.
- `component2_observations/__init__.py` remains minimal; no broad re-exports
  were added. Callers should import directly from
  `orbit_discovery.component2_observations.generator`.

No scientific or output behaviour deviation was found.

---

## 10. Git status

After validation and report creation:

```text
 M src/coordinate_converter.py
 M src/measurement_noise.py
 M src/observation_generator.py
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
?? docs/development/PHASE_1_STEP_3_5_2_GENERATOR_MIGRATION.md
?? docs/development/PHASE_1_STEP_3_COMPONENT2_ASSESSMENT.md
?? pyproject.toml
?? src/orbit_discovery/
?? tests/test_component2_frames.py
?? tests/test_component2_generator.py
?? tests/test_component2_loader.py
?? tests/test_component2_noise.py
?? tests/test_component2_observer.py
?? tests/test_component2_schedule.py
?? tests/test_core_constants.py
?? tests/test_core_paths.py
```

The C3.5.2 tracked modification is:

```text
src/observation_generator.py
```

The other tracked shim modifications are inherited from C3.2.3, C3.3.1, and
C3.4.1. The new untracked files introduced by this checkpoint are:

```text
src/orbit_discovery/component2_observations/generator.py
tests/test_component2_generator.py
docs/development/PHASE_1_STEP_3_5_2_GENERATOR_MIGRATION.md
```

Validation commands:

```text
tests/test_component2_generator.py                         23 tests, OK
unittest discover test_component2_*.py                    113 tests, OK
existing Component 2 script-style checks                   passed
test_observation_output.py                                 passed
test_all_observation_outputs.py                            passed
python -m src.observation_generator --help                 exit 0
pip check                                                  no broken requirements
git diff --check                                           no whitespace errors
git diff --name-only -- data configs results plots         empty
```

No commit, tag, or push was made.
