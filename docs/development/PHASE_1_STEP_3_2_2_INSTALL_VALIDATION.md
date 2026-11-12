# Phase 1 — C3.2.2: Editable Installation and Validation

**Status:** Editable installation succeeded and all required validations passed. No rollback was performed.

**Repository:** `E:\rskmn\Npersonal\projects\yr4\final\prototype-1\physics-guided-orbit-discovery-prototype`

**Interpreter:** `.venv\Scripts\python.exe` (Python 3.13.9)

**Approved command used:**

```powershell
& .venv\Scripts\python.exe -m pip install --no-deps -e .
```

The command was run from the repository root exactly as approved. `--no-deps` was retained, no runtime dependency was installed or upgraded, and `pyproject.toml` was not modified.

## 1. Pre-installation checks

| Check | Result |
|---|---|
| Current directory | Repository root confirmed. |
| `.venv\Scripts\python.exe` exists | `True` |
| Python executable | `...\physics-guided-orbit-discovery-prototype\.venv\Scripts\python.exe` |
| Python version | 3.13.9 (Anaconda-packaged build) |
| pip version | 26.2.2 |
| `pip check` | `No broken requirements found.` |
| `orbit_discovery` importable | No. `importlib.util.find_spec("orbit_discovery")` returned `None`; origin and locations were `None`. |
| Tracked-file modifications | None. `git diff --stat` and `git ls-files -m` were empty. |
| Changes under `data`, `configs`, `results`, `plots` | None. |

The pre-install runtime dependency baseline was recorded outside the repository at:

```text
C:\Users\pc\AppData\Local\Temp\opencode\c3_2_2_pip_before.txt
```

Recorded versions:

| Package | Pre-install version |
|---|---|
| `rebound` | 5.2.2 |
| `numpy` | 2.5.4 |
| `pandas` | 3.1.0 |
| `matplotlib` | 3.11.2 |
| `astroquery` | 0.4.11 |
| `astropy` | 8.0.2 |

## 2. Editable installation

The approved command completed successfully:

```text
Obtaining file:///E:/rskmn/Npersonal/projects/yr4/final/prototype-1/physics-guided-orbit-discovery-prototype
  Installing build dependencies: finished with status 'done'
  Checking if build backend supports build_editable: finished with status 'done'
  Preparing editable metadata (pyproject.toml): finished with status 'done'
  Building editable for orbit-discovery (pyproject.toml): finished with status 'done'
  Created wheel for orbit-discovery: filename=orbit_discovery-0.2.0-0.editable-py3-none-any.whl
  Successfully built orbit-discovery
  Installing collected packages: orbit-discovery
  Successfully installed orbit-discovery-0.2.0
```

pip also printed its routine notice that a newer pip version is available. No pip upgrade was performed.

Build isolation supplied the build requirements in its temporary environment. The runtime `.venv` still does not have `setuptools` or `wheel` installed, confirming they were not added to the runtime environment.

## 3. Package import validation

### 3.1 Import from the repository root

```powershell
Set-Location $repo
& .venv\Scripts\python.exe -c "import orbit_discovery; ..."
```

Results:

```text
ORBIT_FILE=...\src\orbit_discovery\__init__.py
ORBIT_PATH=['...\src\orbit_discovery']
ORBIT_SPEC_ORIGIN='...\src\orbit_discovery\__init__.py'
```

The package resolves to this repository's `src/orbit_discovery`, not to another installation.

### 3.2 Subpackage imports

All four current subpackages imported successfully:

| Import | Resolved file |
|---|---|
| `orbit_discovery.core` | `...\src\orbit_discovery\core\__init__.py` |
| `orbit_discovery.component1_simulation` | `...\src\orbit_discovery\component1_simulation\__init__.py` |
| `orbit_discovery.component2_observations` | `...\src\orbit_discovery\component2_observations\__init__.py` |
| `orbit_discovery.cli` | `...\src\orbit_discovery\cli\__init__.py` |

Result: `SUBPACKAGES_IMPORT_OK`.

### 3.3 Import from an unrelated working directory

With `PYTHONPATH` cleared and the working directory set to:

```text
C:\Users\pc\AppData\Local\Temp\opencode
```

the import still resolved correctly:

```text
CWD=C:\Users\pc\AppData\Local\Temp\opencode
ORBIT_FILE=...\src\orbit_discovery\__init__.py
ORBIT_PATH=['...\src\orbit_discovery']
UNRELATED_CWD_IMPORT_OK
```

This confirms the import is provided by the editable installation rather than by the current directory.

## 4. Legacy compatibility

### 4.1 Observation generator help

```powershell
& .venv\Scripts\python.exe -m src.observation_generator --help
```

Exit code: `0`

Output began with:

```text
usage: observation_generator.py [-h] [--config CONFIG]

Generate synthetic astronomical observations.
```

No observation generation or scientific workflow was executed.

### 4.2 Representative existing `src.*` imports

The following imports were tested from the repository root:

```python
from src.trajectory_loader import load_trajectory
from src.observation_schedule import generate_observation_times, interpolate_positions
from src.measurement_noise import ARCSEC_TO_DEG, add_measurement_noise
import src.observer_model
import src.coordinate_converter
import src.orbit_discovery.core.paths
import src.orbit_discovery.core.constants
```

Result: `LEGACY_IMPORTS_OK`, exit code `0`.

The existing source-tree imports remain usable from the repository root.

### 4.3 Note on the `src` namespace

The editable installation created:

```text
.venv\Lib\site-packages\__editable__.orbit_discovery-0.2.0.pth
```

Its content adds this repository's `src` directory to `sys.path`:

```text
E:\rskmn\Npersonal\projects\yr4\final\prototype-1\physics-guided-orbit-discovery-prototype\src
```

This is expected for a setuptools src-layout editable install and is what makes the fallback `src` path available.

From an unrelated working directory, a bare `import src` still resolved to the pre-existing REBOUND namespace at:

```text
.venv\Lib\site-packages\src
```

rather than to this repository's `src`. This is the pre-existing `src` namespace ambiguity documented earlier, not a new failure. The required `orbit_discovery` import is unaffected. Legacy `src.*` imports remain supported from the repository root, which is the current invocation context for `python -m src.observation_generator`.

## 5. Dependency integrity

### 5.1 `pip check`

```powershell
& .venv\Scripts\python.exe -m pip check
```

Result:

```text
No broken requirements found.
```

Exit code: `0`.

### 5.2 Package-list comparison

`pip list --format=freeze` was compared against the pre-install baseline. The only change was:

```text
orbit-discovery==0.2.0
```

No runtime dependency was installed, upgraded, or downgraded.

Post-install versions:

| Package | Post-install version | Change |
|---|---|---|
| `rebound` | 5.2.2 | None |
| `numpy` | 2.5.4 | None |
| `pandas` | 3.1.0 | None |
| `matplotlib` | 3.11.2 | None |
| `astroquery` | 0.4.11 | None |
| `astropy` | 8.0.2 | None |

`setuptools` and `wheel` remain absent from the runtime `.venv`, confirming build isolation did not alter the runtime environment.

## 6. Installed metadata and rollback readiness

### 6.1 Editable distribution metadata

`pip show orbit-discovery` reported:

```text
Name: orbit-discovery
Version: 0.2.0
Location: ...\physics-guided-orbit-discovery-prototype\.venv\Lib\site-packages
Editable project location: E:\rskmn\Npersonal\projects\yr4\final\prototype-1\physics-guided-orbit-discovery-prototype
Requires: matplotlib, numpy, pandas, rebound
```

`importlib.metadata` reported:

```text
VERSION=0.2.0
DIRECT_URL={"dir_info": {"editable": true}, "url": "file:///E:/rskmn/Npersonal/projects/yr4/final/prototype-1/physics-guided-orbit-discovery-prototype"}
```

Installed metadata files:

```text
.venv\Lib\site-packages\orbit_discovery-0.2.0.dist-info\
.venv\Lib\site-packages\__editable__.orbit_discovery-0.2.0.pth
```

The distribution metadata directory contains:

```text
direct_url.json
INSTALLER
METADATA
RECORD
REQUESTED
top_level.txt
WHEEL
```

The editable project location is the repository root, and the package source location is:

```text
E:\rskmn\Npersonal\projects\yr4\final\prototype-1\physics-guided-orbit-discovery-prototype\src\orbit_discovery
```

### 6.2 Generated source-tree artifact

The installation created:

```text
src\orbit_discovery.egg-info\
```

This directory is ignored by `.gitignore` via the `*.egg-info/` rule. It must not be committed. It is a normal build metadata artifact, not a source change.

### 6.3 Rollback command

If rollback becomes necessary:

```powershell
& .venv\Scripts\python.exe -m pip uninstall orbit-discovery
```

No uninstall was performed because no problem was observed.

Optional cleanup of the generated, ignored metadata after an uninstall:

```powershell
Remove-Item -Recurse -Force src\orbit_discovery.egg-info
```

Do not remove `src/orbit_discovery/` or any scientific source, configuration, dataset, result, or plot file.

## 7. Repository state after validation

Immediately after validation, before creating this report:

```text
?? docs/development/PHASE_1_STEP_1_ASSESSMENT.md
?? docs/development/PHASE_1_STEP_2_CORE_ASSESSMENT.md
?? docs/development/PHASE_1_STEP_3_2_1_INSTALL_ASSESSMENT.md
?? docs/development/PHASE_1_STEP_3_COMPONENT2_ASSESSMENT.md
?? pyproject.toml
?? src/orbit_discovery/
?? tests/test_core_constants.py
?? tests/test_core_paths.py
```

`git diff --stat` was empty, `git ls-files -m` was empty, and there were no changes under `data`, `configs`, `results`, or `plots`. No tracked file was modified. This report is the only additional file created by C3.2.2.

## 8. Result

C3.2.2 passed:

- Editable installation succeeded with the approved command.
- `orbit_discovery` and all four current subpackages import from this repository.
- The package imports correctly from an unrelated working directory.
- `python -m src.observation_generator --help` still exits successfully.
- Representative legacy `src.*` imports still work from the repository root.
- `pip check` passes.
- No runtime dependency was installed, upgraded, or downgraded.
- Installed metadata and rollback command are recorded.
- No rollback is needed.
