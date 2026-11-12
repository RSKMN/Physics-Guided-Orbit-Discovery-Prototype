# C4.5.1 — Component 1/2 Comparison Command Assessment

## 1. Inspect Existing Functionality

### 1.1 Existing Comparison Modules
No dedicated comparison modules exist in the repository. The following comparison-related files were checked:
- `src/orbit_discovery/cli/cmd_compare.py` — does not exist (would be the comparison command implementation)
- No existing comparison scripts or analysis functions found in `src/`
- The repository focus has been on CLI prototype development (C4.1-C4.4.2), not on comparison functionality

### 1.2 Component 1 Trajectory Outputs
**Location**: `data/runs/synthetic_asteroid/` (and `synthetic_asteroid_eccentric/`, `synthetic_asteroid_inclined/`)

**Files per simulation run**:
- `trajectory.csv` — numeric trajectory data
- `config.json` — simulation configuration snapshot
- `metadata.json` — metadata including `run_utc` timestamp

**Trajectory CSV format** (UTF-16 LE encoded):
- **Columns**: `time_years`, `time_days`, `x_au`, `y_au`, `z_au`, `vx_au_per_year`, `vy_au_per_year`, `vz_au_per_year`
- **Shape**: 1001 rows × 8 columns (1001 sample points over 5.0 years)
- **Units**: 
  - time: years/days (relative to simulation start)
  - position: AU (Astronomical Units), Sun-relative
  - velocity: AU/year
- **Coordinate frame**: Heliocentric ecliptic (as specified in config `coordinate_frame`)
- **Initial conditions**: Orbital elements (semi-major axis, eccentricity, inclination, etc.)

**Baseline trajectory** (from commit `d02023d`):
- 1001 rows, 8 columns, identical column names
- Verified numerically identical when re-running the default config from repository root

### 1.3 Component 2 Observation Outputs
**Location**: `data/runs/synthetic_observations/` (various configurations: `synthetic_observations`, `synthetic_observations_eccentric`, `synthetic_observations_inclined`)

**Files per observation run**:
- `trajectory.csv` — observation data
- `metadata.json` — metadata
- `config.json` — configuration

**Observation CSV format** (UTF-16 LE encoded, based on `test_observation_output.py` expectations):
- **Expected columns**: `time_years`, `ra_deg`, `dec_deg`, `true_ra_deg`, `true_dec_deg`, `sigma_ra_cosdec_arcsec`, `sigma_dec_arcsec`, `number_of_observations`
- **Typical shape**: 6 observations × 8 columns
- **Units**: angles in degrees, angular velocities in arcseconds

**Note**: Component 2 observation generation is a separate functionality from Component 1 trajectory generation. The two use different simulators and output formats.

### 1.4 Existing Configuration Files and Metadata Formats

**Configuration files** (all under `data/runs/*/`):
- `config.json` — simulation configuration with fields:
  - `simulation.name`, `simulation.duration_years`
  - `integrator` (e.g., `ias15`), `integrator_epsilon`
  - `output.directory`, `output_interval_days`
  - `coordinate_frame`, `position_unit`, `velocity_unit`, `time_unit`
  - `initial_conditions` (orbital elements mode)
  - `massless_asteroid` flag
  - `position_reference` (e.g., "Sun-relative")

**Metadata files** (UTF-16 LE encoded):
- `metadata.json` — contains:
  - `simulation_name`, `run_utc` (ISO 8601 timestamp)
  - `python_version`, `rebound_version`
  - `number_of_samples`, `duration_years`
  - `output_interval_days`, `integrator`, `integrator_epsilon`
  - `position_reference`, `position_unit`, `velocity_unit`, `time_unit`
  - `coordinate_frame`, `state_type`, `massless_asteroid`
  - `initial_conditions` (orbital element parameters)
  - `final_time_years`, `output_interval_days_requested`

**Key metadata for comparison**:
- `simulation_name` / `simulation_name`: Identifies which simulation/run generated the data
- `run_utc`: Timestamp of when the run occurred (used for ordering, not as regression oracle)
- `position_reference`, `coordinate_frame`: Define the reference frame for positions
- `number_of_samples` / `number_of_observations`: Count of data points

### 1.5 Existing Tests Related to Comparisons
- `tests/test_component2_generator.py` contains some comparison-related tests:
  - `test_legacy_module_help_exits_successfully` — tests that `src.observation_generator --help` exits with code 0
  - `test_generation_contract_and_reference_values` — tests observation generation output (this is a Component 2 test, not a comparison test)
- No existing comparison-specific tests found
- No tests that compare Component 1 and Component 2 outputs

### 1.6 Reusable Functionality Identified
- **Trajectory CSV reading**: `pandas.read_csv` with `encoding='utf-16-le'` (or `utf-16` auto-detect)
- **Metadata JSON reading**: `json.load` with `encoding='utf-16'` (auto-detects BOM)
- **Column name knowledge**: Both trajectory and observation CSVs have known column structures
- **Config JSON reading**: Same encoding requirement
- **Simulation identification**: `simulation_name` / `config.name` field identifies which simulation generated the data

## 2. Understand the Scientific Data

### 2.1 Component 1 Trajectory Data
- **File**: `data/runs/*/trajectory.csv`
- **Purpose**: Simulated trajectory of a massless asteroid under N-body gravity
- **Time representation**: 
  - `time_years`: Time in years since simulation start
  - `time_days`: Time in days since simulation start
  - Relationship: `time_days = time_years * 365.25` (approximately), with `output_interval_days = 1.82625` as the sampling interval
- **Coordinate frame**: Heliocentric ecliptic (from config `coordinate_frame`)
- **Position units**: AU (Astronomical Units), Sun-relative (from config `position_reference`)
- **Velocity units**: AU/year (from config `velocity_unit`)
- **State type**: `simulated_ground_truth` (from metadata)
- **Integration**: IAS15 integrator with specified epsilon

### 2.2 Component 2 Observation Data
- **File**: `data/runs/synthetic_observations/trajectory.csv` (and variants)
- **Purpose**: Synthetic asteroid observations for comparison with simulation
- **Angular coordinates**: `ra_deg`, `dec_deg` (right ascension/declination in degrees)
- **True coordinates**: `true_ra_deg`, `true_dec_deg` (undisturbed by noise)
- **Noise measurements**: `sigma_ra_cosdec_arcsec`, `sigma_dec_arcsec` (in arcseconds)
- **Number of observations**: Typically 6 observations per run
- **Time representation**: `time_years` (consistent with Component 1 format)

### 2.3 Timestamp Relationship
- **Component 1**: `run_utc` in metadata.json indicates when the simulation was executed
- **Component 2**: `run_utc` in metadata.json indicates when observations were generated
- **Comparison criterion**: Simulated positions at observation times can be interpolated from the trajectory CSV; observation timestamps correspond to the `time_years` column in the trajectory
- **Missing information**: No direct one-to-one mapping specified between observation times and trajectory sample times; interpolation would be required

### 2.3 Identified Incompatibilities / Missing Information
- **Coordinate frame differences**: Component 1 uses heliocentric ecliptic; Component 2 uses different angular coordinates (RA/Dec)
- **No direct mapping**: No explicit mapping between observation times and trajectory sample times
- **Different simulators**: Component 1 uses rebound/IAS15; Component 2 uses different observation generation
- **Different output formats**: Trajectory CSV has 8 columns (position/velocity); observation CSV has different column set (RA/Dec, noise)
- **No shared reference frame documented**: No information on how to transform between the two frames

## 3. Define Comparison Functionality

### 3.1 Direct Comparisons (No Transformation Required)
- **Same simulation run**: Compare `trajectory.csv` with itself (trivial, verifies output consistency)
- **Same column comparison**: Within a single trajectory, compare columns (e.g., `x_au` vs. `y_au` positions)

### 3.2 Comparisons Requiring Interpolation/Transformation
- **Simulated positions at observation times**: Interpolate Component 1 trajectory at times matching Component 2 observation times
- **Angular coordinate comparison**: If both datasets use the same coordinate frame, compare angular positions
- **Residual calculations**: `simulated_position - observed_position` (requires frame alignment)

### 3.3 Summary Statistics
- **Mean residual**: Average difference between simulated and observed values
- **RMS residual**: Root-mean-square of residuals
- **Maximum deviation**: Largest single-point difference
- **Correlation coefficient**: Pearson correlation between simulated and observed values

### 3.4 Optional Plots
- **Position time-series overlaid**: Simulated vs. observed positions over time
- **Residual plots**: Residuals vs. time or vs. simulated values
- **Coordinate frame comparison**: If frames can be aligned, plot the differences

### 3.3 Comparison Prioritization
Given the identified incompatibilities, the following comparisons are **recommended** for C4.5.1:
1. **Within-same-type comparison**: Compare Component 1 trajectory with itself (verification)
2. **Same-type summary statistics**: Mean/RMS of trajectory columns
3. **Future work**: Interpolated comparison between Component 1 and Component 2 (requires frame alignment study)

Comparisons that are **not recommended** for C4.5.1 without additional work:
- Direct Component 1 vs. Component 2 comparison (different frames, no mapping)
- Angular coordinate comparison (different coordinate systems)
- Residual calculations (no common reference frame)

## 4. CLI Interface Proposal

### 4.1 `orbit compare --help`
```
orbit compare -- Comparison of simulation and observation data
orbit compare --help
```

### 4.2 Proposed Arguments
```
orbit compare [--simulation SIM] [--observation OBS] [--project-root DIR] [--output-dir DIR] [--mode MODE]
```

| Argument | Description |
|---|---|
| `--simulation SIM` | Path to Component 1 trajectory CSV (default: `data/runs/synthetic_asteroid/trajectory.csv`) |
| `--observation OBS` | Path to Component 2 observation CSV (default: `data/runs/synthetic_observations/trajectory.csv`) |
| `--project-root DIR` | Project root directory (defaults to Git repo root or cwd) |
| `--output-dir DIR` | Output directory for comparison results and plots (optional) |
| `--mode MODE` | Comparison mode: `summary`, `residuals`, `overlay` (default: `summary`) |
| `--help`, `-h` | Show help message and exit |

### 4.3 Comparison Modes (proposed)
- `--mode summary`: Display summary statistics (mean, std, min, max, RMS) for shared columns
- `--mode residuals`: Calculate and display residual statistics (mean, std, max residual)
- `--mode overlay`: Overlay time-series plot of simulated vs. observed positions (requires matplotlib)

### 4.4 Default Behavior (no arguments)
- Compare the default synthetic_asteroid simulation with the default synthetic_observations run
- Display basic summary statistics (mean, std, min, max for each shared column)
- No plotting by default (plotting optional, requires matplotlib)

## 4. Architecture and Implementation Plan

### 4.1 Recommended Modules
**Existing modules to reuse**:
- `src/orbit_discovery/cli/cmd_observe.py` — observation generation command (for understanding output format)
- `src/orbit_discovery/cli/cmd_simulate.py` — simulation command (for understanding trajectory output format)
- Existing CSV reading utilities (encoding handling)
- Existing metadata parsing functions

**New module necessary**: 
- `src/orbit_discovery/compare.py` — comparison logic module
  - Functions for reading trajectory and observation CSVs
  - Functions for computing summary statistics
  - Functions for interpolation (if needed)
  - Functions for generating comparison reports

### 5.2 Module Location
- **Recommended**: `src/orbit_discovery/compare.py`
- **Rationale**: 
  - Consistent with package structure (`cli/`, `core/`, `component1_simulation/`, `component2_observations/`)
  - Separates comparison logic from CLI invocation
  - Allows import by the CLI entry point and potentially other scripts

### 5.3 CLI Invocation
```
python -m orbit_compare
# or via the main CLI:
orbit compare --simulation ... --observation ...
```

### 5.4 Tests Needed
- Readability tests for CSV/JSON files with correct encoding
- Statistic calculation tests (mean, std, min, max, RMS)
- Interpolation accuracy tests (if implementing time-based comparison)
- Comparison report format verification
- Encoding handling tests (utf-16-le vs. utf-16 vs. utf-8)

### 5.5 Preserving Existing Output Formats
- **Do not modify**: `data/runs/*/trajectory.csv`, `metadata.json`, `config.json`
- **Do not modify**: Existing `cmd_simulate.py`, `cmd_observe.py` outputs
- **New output**: Comparison results should be written to `--output-dir` (optional) or displayed on stdout
- **No format changes**: Existing CSV column structures and metadata meanings must remain unchanged

## 5. Risks and Unresolved Questions

### 5.1 Key Risks
1. **Coordinate frame mismatch**: Component 1 uses heliocentric ecliptic; Component 2 uses RA/Dec angular coordinates. No documented transformation exists.
2. **No common time base**: Component 1 trajectory has 1001 evenly-spaced samples; Component 2 has typically 6 observations at unspecified times. Interpolation would be required but assumes linear interpolation, which may not be scientifically valid.
3. **No shared metadata key**: While both have `simulation_name`, the values may differ (e.g., "synthetic_asteroid" vs. "synthetic_observations"), making automatic matching difficult.
4. **No existing comparison framework**: No code or tests exist to build upon; this would be a new implementation.

### 5.2 Unresolved Questions
- **Should comparison be between same-type data only?** (Component 1 with Component 1, Component 2 with Component 2)
- **Is interpolation between sample times and observation times valid?** What interpolation method should be used?
- **What coordinate frame transformation, if any, is needed?**
- **What comparison statistics are most scientifically meaningful for this project?**
- **Should the CLI support plotting, and what library should be used (matplotlib, etc.)?**

### 5.3 Recommended Approach for C4.5.1
Given the risks and unresolved questions, the assessment recommends:
1. **Start with same-type comparisons only** (Component 1 trajectory with Component 1 trajectory; Component 2 observation with Component 2 observation)
2. **Implement basic summary statistics** (mean, std, min, max, RMS) for each shared column
3. **Add optional `--mode` flag** to select comparison type
4. **Defer cross-type comparison** to a future checkpoint after frame alignment and time-mapping studies are completed
5. **Make plotting optional** and dependent on matplotlib availability

## 6. Testing Strategy

### 5.1 Required Tests
- **CSV reading tests**: Verify correct encoding handling (utf-16-le/utf-16)
- **Statistic calculation tests**: Verify mean, std, min, max, RMS
- **File not found tests**: Verify graceful error handling for missing files
- **Encoding mismatch tests**: Verify errors are handled when encoding doesn't match

### 5.2 Suggested Test Cases
1. `test_trajectory_csv_reading`: Read `data/runs/synthetic_asteroid/trajectory.csv` and verify shape/columns
2. `test_observation_csv_reading`: Read `data/runs/synthetic_observations/trajectory.csv` and verify expected columns
3. `test_summary_statistics`: Given known trajectory data, verify computed statistics match expected values
4. `test_missing_file_error`: Verify proper error when specified CSV file doesn't exist
5. `test_compare_same_file`: Compare a trajectory with itself; should show zero residuals

### 5.3 Test Environment
- All tests should run without requiring matplotlib (plotting optional)
- Tests should work with the existing `data/runs/` directory structure
- No external dependencies beyond pandas and standard library

## 6. Unresolved Questions (for Future Checkpoints)
1. **Coordinate frame alignment**: Is there a documented transformation between heliocentric ecliptic and the RA/Dec frame used in Component 2?
2. **Time mapping**: Is there a way to map observation times to trajectory sample times, or should observations be compared at their closest trajectory sample?
3. **Cross-type comparison value**: Is there scientific value in comparing Component 1 simulated positions with Component 2 observed positions, or should these remain separate?
4. **Plotting library**: Should matplotlib be added as a dependency, or should comparison plots be deferred?
5. **Output directory**: Is `--output-dir` justified, or should all comparison results be displayed on stdout?

---
**Assessment Level**: Read-only analysis and planning
**Status**: Ready for implementation in subsequent checkpoint
**Key Finding**: Cross-type (Component 1 vs. Component 2) comparison is premature without frame alignment and time-mapping studies. Same-type comparisons are the appropriate starting point for C4.5.1.