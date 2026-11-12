# Phase 1 — C3.2.1: Editable Installation Readiness Assessment

**Status:** Read-only assessment complete. No installation, upgrade, downgrade, or uninstall was performed. No source, test, configuration, dependency, dataset, result, or plot files were modified.

**Repository:** `E:\rskmn\Npersonal\projects\yr4\final\prototype-1\physics-guided-orbit-discovery-prototype`

**Scope:** Assess whether `python -m pip install -e .` can later be used to install this project into the existing `.venv` safely, and define the validation and rollback steps for that checkpoint.

## 1. Packaging readiness

### 1.1 Configuration inspected

`pyproject.toml` is present and contains:

| Item | Value | Assessment |
|---|---|---|
| Build backend | `setuptools.build_meta` | Valid PEP 517 backend. |
| Build requirements | `setuptools>=64`, `wheel` | Valid, but not installed in the current `.venv`; see §2. |
| Distribution name | `orbit-discovery` | Matches the project name. |
| Import package name | `orbit_discovery` | Correctly distinct from the distribution name. |
| Version | `0.2.0` | Valid. |
| Python requirement | `>=3.12` | Current interpreter is 3.13.9, which satisfies it. |
| Readme | `README.md` | File exists and is non-empty. |
| Runtime dependencies | `rebound`, `numpy`, `pandas`, `matplotlib` | All installed and within the declared ranges; see §2.4. |
| Optional dependencies | `network`, `test` | Not installed by a plain editable install. `pytest` is absent, which is expected. |
| Package directory | `src` | Correct src-layout configuration. |
| Discovery | `where = ["src"]`, `include = ["orbit_discovery*"]`, `namespaces = false` | Consistent with the actual package tree. |

### 1.2 Package tree and discovery

The following packages exist and each contains an `__init__.py`:

- `src/orbit_discovery/`
- `src/orbit_discovery/core/`
- `src/orbit_discovery/component1_simulation/`
- `src/orbit_discovery/component2_observations/`
- `src/orbit_discovery/cli/`

`src/` itself has no `__init__.py`, which is correct: it is the package root configured by `package-dir`, not an importable package that discovery needs to include. With `namespaces = false`, every discovered package must have an `__init__.py`, and all current packages do.

`include = ["orbit_discovery*"]` covers the root package and all current subpackages. No package discovery conflict was found, and no intended package is excluded.

### 1.3 Packaging conclusion

The project is structurally ready for an editable install. No concrete packaging defect was found, so `pyproject.toml` should not be changed for this checkpoint.

The only readiness gap is environmental: the current `.venv` does not have the declared build backend (`setuptools`) or `wheel`. A normal editable install with build isolation can supply those temporarily, but that requires access to a package index or a local wheel cache.

Non-blocking observations:

- `orbit_discovery/__init__.py` does not define `__version__`. The version remains available through the installed distribution metadata (`importlib.metadata.version("orbit-discovery")`). This is not an editable-install blocker.
- There is no `[project.scripts]` entry yet. A plain editable install therefore adds no console command. This is expected at this checkpoint.
- No package data files are declared or required by the current package. This is not a blocker.

## 2. Environment details

### 2.1 Interpreter and virtual environment

| Item | Observed value |
|---|---|
| Executable | `E:\rskmn\Npersonal\projects\yr4\final\prototype-1\physics-guided-orbit-discovery-prototype\.venv\Scripts\python.exe` |
| Python version | 3.13.9 (Anaconda-packaged build) |
| `sys.prefix` | Current repository `.venv` |
| Base interpreter | `C:\Users\pc\anaconda3\python.exe` |
| `include-system-site-packages` | `false` |
| pip | 26.2.2, installed inside the `.venv` |

The venv was originally created at an older path:

```text
E:\rskmn\Npersonal\projects\yr4\final\prototype-1\code\.venv
```

The current repository path is different. `pyvenv.cfg` retains that stale `command` line, but `sys.executable`, `sys.prefix`, and pip all resolve to the current `.venv` and work correctly. This is an environment-provenance note, not a demonstrated blocker. Use `.venv\Scripts\python.exe -m pip` rather than relying on generated console-script launchers whose embedded paths were not assessed.

### 2.2 Build backend availability

| Package | In `.venv` | In global Anaconda `site-packages` |
|---|---|---|
| `setuptools` | **Not found** | 80.9.0 |
| `wheel` | **Not found** | 0.45.1 |

The global Anaconda copies are not visible inside the venv because `include-system-site-packages = false`. They must not be used by invoking global Python, and adding them through `PYTHONPATH` is not proposed.

Consequences:

- `--no-build-isolation` would be expected to fail in the current venv because `setuptools.build_meta` is unavailable there.
- A normal `pip install -e .` uses build isolation and can install `setuptools>=64` and `wheel` in a temporary build environment.
- There is no custom pip index configured and no `PIP_*` environment variable set. The default index would be used.
- `pip cache list setuptools` and `pip cache list wheel` report no locally built wheels. Do not assume the build can complete offline; the HTTP cache was not audited.

### 2.3 Existing installation state

| Check | Result |
|---|---|
| `importlib.util.find_spec("orbit_discovery")` | `None` (not installed/importable from the venv) |
| `pip show orbit-discovery` | `WARNING: Package(s) not found: orbit-discovery` |
| Existing `orbit_discovery` distribution or editable finder in `site-packages` | None found |
| `pip check` | `No broken requirements found.` |

No conflicting installation of this project was found. The existing `src.*` modules are a separate source-tree namespace and are not installed as a distribution.

### 2.4 Declared dependencies versus installed versions

| Requirement | Installed | Status |
|---|---|---|
| `rebound>=5.2,<6` | 5.2.2 | Satisfied |
| `numpy>=2.5,<3` | 2.5.4 | Satisfied |
| `pandas>=3.1,<4` | 3.1.0 | Satisfied |
| `matplotlib>=3.11,<4` | 3.11.2 | Satisfied |
| `astroquery>=0.4.11,<0.5` (optional `network` extra) | 0.4.11 | Satisfied, but not required by a plain install |

The environment also contains `astropy`, `pyvo`, and related packages that are not base project dependencies. They are not a conflict: `pip check` passes, and the proposed install uses `--no-deps` so it will not resolve, upgrade, or remove them.

## 3. Potential conflicts and risks

| Risk | Evidence | Impact | Mitigation |
|---|---|---|---|
| Build isolation cannot obtain build tools | No `setuptools`/`wheel` in `.venv`; no local built-wheel cache; no custom index configured. | Editable install fails if the default index/network is unavailable. | Run the approved command with build isolation and index access, or use an approved local wheelhouse. Do not use global Python. |
| Unpinned build requirements | `setuptools>=64` and `wheel` have no upper bounds. | Build isolation may fetch newer build-tool versions over time, reducing reproducibility. | Accept for this checkpoint; pinning build requirements would be a separate approved change, not a packaging defect. |
| `--no-deps` hides missing runtime dependencies | `--no-deps` skips dependency resolution. | Install can succeed even if a runtime dependency is missing. | All four base dependencies are currently installed and satisfy their ranges; run `pip check` and the import validations in §5. |
| Editable install leaves build metadata in the source tree | Setuptools may create `src/orbit_discovery.egg-info/`. | Untracked build artifact, though ignored by `.gitignore`. | Verify with `git status --short`; remove the ignored artifact during rollback if desired. Do not commit it. |
| Existing `src` namespace collides with a site-packages `src` | REBOUND currently exposes `site-packages/src`; the repository also uses `src/`. | Pre-existing namespace behavior, not introduced by installing `orbit_discovery`. | Do not change it here. Validate that `src.*` imports and `python -m src.observation_generator --help` still work. |
| Stale venv creation path | `pyvenv.cfg` refers to an older `...\code\.venv` path. | Cosmetic environment-provenance issue; current interpreter and pip resolve correctly. | Use `python.exe -m pip`; do not rely on unassessed generated launchers. Recreating the venv is a separate decision. |
| Global build tools are not visible | `include-system-site-packages = false`; global Anaconda has `setuptools`/`wheel`. | `--no-build-isolation` is not currently viable. | Use build isolation, or separately approve installing build tools into `.venv`. |
| No `__version__` attribute | `orbit_discovery/__init__.py` is a docstring only. | Does not affect installation or imports; metadata version is still available. | No action in this checkpoint. |
| No console scripts | No `[project.scripts]` in `pyproject.toml`. | Expected; no command is installed. | No action; CLI packaging is later work. |
| Dependency drift if `--no-deps` is omitted | Current versions satisfy all ranges, but a resolver run could still touch packages. | Unnecessary risk to scientific dependencies. | Use `--no-deps` for the approved install. |

No conflict was found between the distribution name `orbit-discovery` and the import name `orbit_discovery`. No existing top-level `orbit_discovery` installation is present.

## 4. Exact proposed installation command

All commands use the existing `.venv` explicitly. Global Python and global pip are not used.

### Primary proposal

```powershell
$repo = 'E:\rskmn\Npersonal\projects\yr4\final\prototype-1\physics-guided-orbit-discovery-prototype'
$python = Join-Path $repo '.venv\Scripts\python.exe'

Set-Location $repo
& $python -m pip install --no-deps -e .
```

Why this command:

- `-e .` creates the editable installation from the configured src layout.
- `--no-deps` prevents pip from installing, upgrading, downgrading, or removing the scientific runtime dependencies.
- Build isolation supplies the declared build requirements (`setuptools>=64`, `wheel`) in a temporary environment. This does not add them to the runtime `.venv`.
- No extras are requested, so `astroquery` and `pytest` are not installed or changed.

Limitations:

- Build isolation may need network/index access for `setuptools` and `wheel`; no locally built wheels were found.
- Because `--no-deps` is used, pip does not verify project dependencies. The current environment already satisfies all base requirements, and §5 includes `pip check`.
- Setuptools may leave an ignored `src/orbit_discovery.egg-info/` directory.
- The command does not add console scripts, because none are declared.

### Fallback if the index is unavailable

Only after separate approval, and only if a local wheelhouse is not available, build tools could be installed into the existing `.venv`:

```powershell
& $python -m pip install "setuptools>=64" wheel
& $python -m pip install --no-deps --no-build-isolation -e .
```

This fallback changes the venv by adding build tooling. It does not intentionally change scientific dependencies, but it is not the primary proposal and should not be run without approval. Do not use the global Anaconda `setuptools`/`wheel` through global Python or `PYTHONPATH`.

## 5. Validation commands and expected outcomes

Run these in order at the later approved installation checkpoint. Capture the baseline before installing.

### 5.1 Baseline and install

```powershell
$repo = 'E:\rskmn\Npersonal\projects\yr4\final\prototype-1\physics-guided-orbit-discovery-prototype'
$python = Join-Path $repo '.venv\Scripts\python.exe'

Set-Location $repo
$before = & $python -m pip list --format=freeze

& $python -m pip install --no-deps -e .
```

Expected: editable installation succeeds, and the only new runtime distribution is `orbit-discovery==0.2.0`.

### 5.2 Verify the installed location from the repository root

```powershell
Set-Location $repo
& $python -c "import orbit_discovery; print(orbit_discovery.__file__); print(list(orbit_discovery.__path__))"
```

Expected: the first line is:

```text
E:\rskmn\Npersonal\projects\yr4\final\prototype-1\physics-guided-orbit-discovery-prototype\src\orbit_discovery\__init__.py
```

The `__path__` value should resolve to the repository's `src\orbit_discovery` directory, not to another site-packages copy.

### 5.3 Verify import from an unrelated working directory

```powershell
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
Push-Location 'C:\Users\pc\AppData\Local\Temp\opencode'
& $python -c "import orbit_discovery; print(orbit_discovery.__file__)"
Pop-Location
```

Expected: the same repository `src\orbit_discovery\__init__.py` path. This proves the editable installation, rather than the current directory or `PYTHONPATH`, is providing the import.

### 5.4 Verify distribution metadata and editable status

```powershell
& $python -c "import importlib.metadata as m; d=m.distribution('orbit-discovery'); print(d.version); print(d.read_text('direct_url.json'))"
```

Expected:

- version `0.2.0`;
- `direct_url.json` contains the repository directory URL and `"dir_info": {"editable": true}`.

Also check:

```powershell
& $python -m pip show orbit-discovery
```

Expected: `Name: orbit-discovery`, `Version: 0.2.0`, and an `Editable project location` pointing at the repository root.

### 5.5 Verify existing source-tree behavior is unchanged

```powershell
Set-Location $repo
& $python -m src.observation_generator --help
```

Expected: the existing usage/help output, exit code 0, and no observation generation or data writes.

Check the old module imports:

```powershell
& $python -c "import src.trajectory_loader, src.observation_schedule, src.observer_model, src.coordinate_converter, src.measurement_noise; from src.trajectory_loader import load_trajectory; from src.observation_schedule import generate_observation_times, interpolate_positions; from src.measurement_noise import ARCSEC_TO_DEG, add_measurement_noise; print('old imports ok')"
```

Expected: `old imports ok`. This confirms that the editable installation has not replaced or broken the existing `src.*` namespace.

### 5.6 Verify dependency state

```powershell
& $python -m pip check
```

Expected: `No broken requirements found.`

Compare the post-install package list:

```powershell
$after = & $python -m pip list --format=freeze
Compare-Object $before $after
```

Expected: only `orbit-discovery==0.2.0` is added. Build tools installed in the isolated build environment should not appear in this list. If the fallback in §4 was used, the explicitly installed build tools would also appear and must be accounted for separately.

### 5.7 Verify repository state

```powershell
Set-Location $repo
git status --short
git diff --name-only -- data configs results plots
git ls-files -m
```

Expected:

- `git status --short` shows only the pre-existing untracked assessment files, the new `pyproject.toml` and `src/orbit_discovery/` artifacts under assessment, and this report;
- `git diff --name-only -- data configs results plots` is empty;
- `git ls-files -m` is empty;
- no tracked source, test, configuration, dataset, result, or plot file is modified.

Check for ignored packaging artifacts:

```powershell
Get-ChildItem (Join-Path $repo 'src') -Directory -Filter '*.egg-info' -ErrorAction SilentlyContinue
```

Expected: either no output, or `src\orbit_discovery.egg-info` only. That directory is ignored by `.gitignore`; it must not be committed.

### 5.8 How the installed location is verified

The location is proven by three independent checks:

1. `orbit_discovery.__file__` and `orbit_discovery.__path__` point into the repository's `src/orbit_discovery`.
2. `direct_url.json` records an editable file URL for the repository and `"dir_info": {"editable": true}`.
3. `pip show orbit-discovery` reports the repository root as the editable project location.

The import from `C:\Users\pc\AppData\Local\Temp\opencode`, with `PYTHONPATH` cleared, confirms that the location is not an accident of the current working directory.

## 6. Rollback procedure

If the editable installation causes any unexpected behavior, stop and roll back without touching scientific source or data.

```powershell
$repo = 'E:\rskmn\Npersonal\projects\yr4\final\prototype-1\physics-guided-orbit-discovery-prototype'
$python = Join-Path $repo '.venv\Scripts\python.exe'

Set-Location $repo
& $python -m pip uninstall -y orbit-discovery
```

Then remove only generated, ignored packaging artifacts, if present:

```powershell
Remove-Item -Recurse -Force (Join-Path $repo 'src\orbit_discovery.egg-info') -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force (Join-Path $repo 'build') -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force (Join-Path $repo 'dist') -ErrorAction SilentlyContinue
```

Do not delete `src/orbit_discovery/` or any other source file. Do not uninstall `rebound`, `numpy`, `pandas`, `matplotlib`, `astroquery`, `astropy`, or other scientific packages.

If the fallback installed build tools into `.venv`, record whether they existed beforehand. They were not present in the baseline. If policy requires restoring the exact baseline, remove them only after confirming no other installed package depends on them; otherwise leave them and document the environment change.

Post-rollback checks:

```powershell
& $python -m pip check
& $python -m pip list --format=freeze
Set-Location $repo
& $python -m src.observation_generator --help
git status --short
```

Expected: `pip check` still passes; `orbit-discovery` is absent; the old `src.*` command still works; and no tracked or data files changed. `import orbit_discovery` should no longer resolve from an unrelated directory, returning to the current baseline.

## 7. Decisions requiring approval

| Decision | Recommendation | Notes |
|---|---|---|
| D-01: Approve the primary editable install command with build isolation | Approve `& $python -m pip install --no-deps -e .` | May require index/network access for `setuptools` and `wheel`; does not change scientific dependencies. |
| D-02: Choose the offline fallback if the index is unavailable | Provide a trusted local wheelhouse, or separately approve installing build tools into `.venv` | Do not use global Python or global `site-packages` through `PYTHONPATH`. |
| D-03: Pin build requirements for reproducibility | Defer; no change now | `setuptools>=64` and `wheel` are valid. Pinning is a separate packaging decision, not a defect. |
| D-04: Accept the ignored egg-info artifact | Accept and clean up if desired | `src/orbit_discovery.egg-info/` is ignored; never commit it. |
| D-05: Proceed to C3.2 after successful validation | Approve only after §5 passes | C3.2 remains limited to `observation_schedule.py` and `observer_model.py`. |

No packaging defect was found that requires modifying `pyproject.toml`. No installation or environment change was made during this assessment.

## Git status

At the time of this read-only assessment, before creating this report:

```text
?? docs/development/PHASE_1_STEP_1_ASSESSMENT.md
?? docs/development/PHASE_1_STEP_2_CORE_ASSESSMENT.md
?? docs/development/PHASE_1_STEP_3_COMPONENT2_ASSESSMENT.md
?? pyproject.toml
?? src/orbit_discovery/
?? tests/test_core_constants.py
?? tests/test_core_paths.py
```

No tracked files are modified. `git diff --stat` is empty, `git ls-files -m` is empty, and there are no changes under `data`, `configs`, `results`, or `plots`. This report is the only file created by C3.2.1.
