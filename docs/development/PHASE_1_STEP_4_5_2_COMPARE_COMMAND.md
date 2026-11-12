# Phase 1 Step C4.5.2: `orbit compare` Command

## Overview

The `orbit compare` command supports same-type trajectory and observation comparisons
with three modes: `summary`, `residuals`, and `overlay`. Cross-type (Component 1 vs.
Component 2) comparison is intentionally deferred to future work.

## Supported Comparisons

### Component 1: Trajectory Comparison (`--simulation`)

Compares two Component 1 trajectory CSV files in heliocentric ecliptic coordinates.
The first file is user-specified; the second is the default for the selected run.

**Default file:** `data/runs/synthetic_asteroid/trajectory.csv`

**CSV format:**
- 8 columns: `time_years`, `time_days`, `x_au`, `y_au`, `z_au`, `vx_au_per_year`,
  `vy_au_per_year`, `vz_au_per_year`
- UTF-8 encoded (no BOM required)
- 1001 rows typical for a 5-year simulation with 0.01-year sampling

### Component 2: Observation Comparison (`--observation`)

Compares two Component 2 observation CSV files in equatorial coordinates.
The first file is user-specified; the second is the default for synthetic asteroid observations.

**Default file:** `data/observations/synthetic_asteroid_observations/observations.csv`

**CSV format:**
- 8 columns: `time_years`, `time_days`, `ra_deg`, `dec_deg`,
  `sigma_ra_cosdec_arcsec`, `sigma_dec_arcsec`, `true_ra_deg`, `true_dec_deg`
- UTF-8 encoded (no BOM required)
- 262 observation samples typical for a standard scenario

## Command-Line Usage

```bash
orbit compare [--simulation SIM] [--observation OBS]
              [--project-root DIR] [--output-dir DIR] [--mode MODE]
```

### mutually exclusive flags

- `--simulation SIM`: Path to Component 1 trajectory CSV file
- `--observation OBS`: Path to Component 2 observation CSV file
- Exactly one of `--simulation` or `--observation` must be provided

### Other options

- `--project-root DIR`: Project root directory (defaults to CWD search)
- `--output-dir DIR`: Output directory for comparison results
- `--mode MODE`: Comparison mode (`summary`, `residuals`, `overlay`)
  - Default: `summary`

## Comparison Modes

### `--mode summary`

Computes summary statistics for all columns present in both compared files:

- Mean, standard deviation, minimum, maximum, and root-mean-square (RMS)

### `--mode residuals`

Computes residuals (differences) between the two files for shared columns:

- Mean residual, standard deviation of residuals, maximum absolute residual
- Number of residual points and the residuals themselves

### `--mode overlay`

Reports overlay data (time-series) without requiring matplotlib:

- Lists shared columns between the two files
- Shows the first 5 values from each file for each shared column
- Notes that summary/residuals modes provide statistical analysis,
  while overlay provides raw time-series data

## Error Handling

- **Missing file:** Error message with exit code 1
- **Both --simulation and --observation specified:** Error message with exit code 1
- **Unsupported comparison mode:** Error message with exit code 1
- **Invalid CSV/encoding issues:** Error message with exit code 2
- **Project root not found:** Error message with exit code 1

## Implementation Details

- **Encoding:** CSV files are read as UTF-8, with utf-8-sig fallback
- **Column detection:** Type is determined by column presence:
  - Component 1: requires `time_years`, `x_au`, `y_au`, `z_au`
  - Component 2: requires `time_years`, `ra_deg`, `dec_deg`
- **Comparison type:** Same-type only; cross-type deferred
- **Modular design:** Comparison logic separated into `_compute_summary_statistics`
  and `_compute_residuals` helper functions
- **Testable:** All code paths are unit-testable with the provided test data

## Test Results

All comparison modes (summary, residuals, overlay) have been validated for both
Component 1 and Component 2 data with exit code 0. Existing test suite passes
without regressions (2 pre-existing failures and 1 pre-existing error unrelated
to this command).

## See Also

- `PHASE_1_STEP_4_5_1_COMPARE_ASSESSMENT.md` — Assessment documentation for
  the compare command design
- `orbit simulate` — Component 1 simulation command
- `orbit observe` — Component 2 observation command