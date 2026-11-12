# Phase 1 Step C4.6: `orbit validate` Command

## Overview

The `orbit validate` command provides read-only validation of trajectory CSVs and
observation CSVs + metadata pairs. All validation is read-only: no files are
modified, no repairs are attempted, and no scientific assumptions are introduced
beyond what the existing validation logic already checks.

## Supported Validation Types

### `--trajectory <csv>`

Validates a Component 1 trajectory CSV file. Checks:

- **Required columns** format detection (supports both synthetic asteroid and
  two-body formats)
- **Finite values**: no NaN or infinite values in numeric columns
- **Strictly increasing timestamps**: time column must be strictly monotonically
  increasing
- **Time consistency**: `time_days` should approximately equal `time_years * 365.25`

**Default:** `data/trajectory_two_body.csv`

**Supported formats:**

| Format | Column names |
|---|---|
| Synthetic asteroid | `time_years`, `time_days`, `x_au`, `y_au`, `z_au`, `vx_au_per_year`, `vy_au_per_year`, `vz_au_per_year` |
| Two-body | `time_yr`, `x_AU`, `y_AU`, `z_AU`, `vx_AU_per_yr`, `vy_AU_per_yr`, `vz_AU_per_yr`, `distance_AU` |

### `--validate-observations`

Also validates the Component 2 observation CSV + metadata.json pair. Checks:

- **Required columns**: `time_years`, `time_days`, `ra_deg`, `dec_deg`,
  `sigma_ra_cosdec_arcsec`, `sigma_dec_arcsec`, `true_ra_deg`, `true_dec_deg`
- **Finite values**: no NaN or infinite values
- **Strictly increasing timestamps**: `time_years` must be strictly monotonically increasing
- **Time consistency**: `time_days ≈ time_years * 365.25`
- **Coordinate ranges**: RA in [0, 360] degrees, Dec in [-90, 90] degrees

### Mutual exclusivity

- `--trajectory` and `--validate-observations` can be combined (validates both)
- If neither is specified, only the trajectory (default) is validated

## Command-Line Usage

```bash
orbit validate [--trajectory CSV] [--project-root DIR] [--validate-observations] [--help] [--version]
```

### Arguments

| Argument | Required | Default | Description |
|---|---|---|---|
| `--trajectory CSV` | Optional | `data/trajectory_two_body.csv` | Path to trajectory CSV to validate. Resolved against project root if relative. |
| `--project-root DIR` | Optional | (auto-detect) | Explicit project root directory. |
| `--validate-observations` | Flag | `False` | If set, also validate observation CSV + metadata pair. |
| `--help, -h` | Flag | — | Show this help message and exit. |
| `--version, -V` | Flag | — | Show version and exit. |

## Exit Codes

| Code | Meaning |
|---|---|
| `0` | All validations passed. |
| `1` | One or more validations failed. See stderr for detailed issue descriptions. |
| `2` | Configuration error (missing file, project root not found). |

## Error Messages

Error messages are printed to **stderr** and are designed to be actionable:

- **Missing file**: `Error: Trajectory file not found: <path>`
- **Unknown format**: `Error: Unknown trajectory format: could not detect required columns. Expected ...`
- **Missing columns**: `Missing required columns: <comma-separated list>` or `Missing required observation columns: <comma-separated list>`
- **NaN/infinite values**: `Trajectory contains NaN or infinite values.` or `Observation data contains NaN or infinite values.`
- **Non-increasing timestamps**: `time_years are not strictly increasing.` or `time_yr are not strictly increasing.`
- **Time inconsistency**: `time_years and time_days are inconsistent.` or `time_yr and time_days are inconsistent.`
- **Coordinate out of range**: `RA values outside expected range [0, 360] degrees.` or `Dec values outside expected range [-90, 90] degrees.`
- **Project root not found**: `Error: <message>` (with exit code 1)

## Read-Only Guarantee

The command **never** modifies the files being validated. It only reads them and
reports issues. No automatic repairs, no file writes, no changes to configuration
or data.

## Integration with CLI

- Dispatches through the shared `orbit` CLI entry point (same as `simulate`, `observe`, `compare`)
- Project root resolved via `core.paths.resolve_project_root()` with proper precedence:
  1. Explicit `--project-root` argument
  2. `ORBIT_DISCOVERY_ROOT` environment variable
  3. Nearest ancestor containing `pyproject.toml`
- No silent CWD fallback — raises `ProjectRootNotFoundError` if discovery fails

## Example Usages

### Validate default two-body trajectory

```bash
orbit validate
```

Output: `Validation passed for: data\trajectory_two_body.csv` (exit code 0)

### Validate synthetic asteroid trajectory

```bash
orbit validate --trajectory data/runs/synthetic_asteroid/trajectory.csv
```

Output: `Validation passed for: data\runs\synthetic_asteroid\trajectory.csv` (exit code 0)

### Validate with observation check

```bash
orbit validate --validate-observations
```

Output: Validates both trajectory and observation files; reports any issues on stderr.

### Validate with explicit project root

```bash
orbit validate --project-root /path/to/project --trajectory data/my_trajectory.csv
```

### Validate both trajectory and observations, report errors

```bash
orbit validate --trajectory data/broken.csv --validate-observations
```

- Stderr will list trajectory issues first, then observation issues
- Exit code 1

## Limitations

- Only validates the column formats and structural constraints described above;
  does not perform orbital mechanics validation (e.g., does not check if orbital
  elements are physically consistent)
- Observation coordinate range checks (RA/Dec limits) are basic; does not
  validate against astronomical catalogs or Horizons ephemerides
- Cross-format validation (e.g., two-body trajectory vs. synthetic format) is
  supported via format auto-detection, but if neither format's columns are
  present, an "Unknown trajectory format" error is raised
- Does not validate metadata.json content beyond its existence

## See Also

- `PHASE_1_STEP_4_1_CLI_ASSESSMENT.md` — CLI architecture assessment that
  documented the validate command design
- `orbit compare` — Same-type trajectory/observation comparison command
- `orbit simulate` — Component 1 N-body simulation command
- `orbit observe` — Component 2 observation generation command
- `tests/validate_ground_truth.py` — Existing trajectory validation logic
- `tests/validate_baseline.py` — Baseline orbital geometry validation