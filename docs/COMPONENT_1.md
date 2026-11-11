# Component 1 — N-Body Trajectory Simulator

## 1. Purpose

Component 1 generates asteroid trajectories using gravitational N-body simulation. It provides physical position and velocity states that downstream components can use for orbit estimation and synthetic observation generation.

## 2. Implementation

- Programming language: Python
- Simulation library: REBOUND
- Integrator: IAS15
- Configuration format: JSON
- Trajectory format: CSV

## 3. Inputs

The configurable simulator reads a JSON configuration containing:

- Simulation name
- Initial asteroid orbital elements
- Simulation duration
- Output interval
- Integrator and tolerance
- Gravitational bodies to include
- Output directory

The current configurable implementation supports synthetic initial conditions specified through orbital elements. Horizons-based initialization remains a separate workflow and has not yet been integrated into this interface.

## 4. Ground-truth trajectory output

The simulator exports `trajectory.csv` with these columns:

| Column | Meaning | Unit |
|---|---|---|
| `time_years` | Elapsed simulation time | year |
| `time_days` | Elapsed simulation time | day |
| `x_au` | Sun-relative x position | AU |
| `y_au` | Sun-relative y position | AU |
| `z_au` | Sun-relative z position | AU |
| `vx_au_per_year` | Sun-relative x velocity | AU/year |
| `vy_au_per_year` | Sun-relative y velocity | AU/year |
| `vz_au_per_year` | Sun-relative z velocity | AU/year |

The trajectory contains simulated physical states, not noisy astronomical observations.

## 5. Run metadata

Each run stores:

- `config.json`: configuration used
- `metadata.json`: run information, software version, units, initial conditions and output conventions
- `trajectory.csv`: simulated physical states

The synthetic configurations currently have no absolute astronomical epoch. Their times are elapsed simulation times.

## 6. Validation performed and evidence status

The checks listed below were performed during earlier development and are evidenced by the validation artefacts retained in the repository. During 0.2.0 baseline preparation, the read-only trajectory checks were re-executed, but the repeatability, IAS15 tolerance-sensitivity and Eros/Horizons checks were not all re-run: their previously generated outputs were inspected instead. The historical results remain valid records of those earlier runs and are not withdrawn.

- Required trajectory columns checked
- Finite numeric values checked
- Timestamp ordering checked
- Time-column consistency checked
- Repeatability tested for identical configurations (historical check; existing repeatability runs inspected, not re-executed during 0.2.0 baseline preparation)
- Sensitivity to IAS15 integration tolerance tested (historical check; saved tolerance summary inspected, not re-executed during 0.2.0 baseline preparation)
- Eros trajectories compared with JPL Horizons for five-planet and eight-planet models (historical check; saved validation CSVs inspected, network workflow not re-executed during 0.2.0 baseline preparation)

## 7. Known limitations

- Synthetic planetary initial conditions are simplified and approximately circular and coplanar.
- Synthetic validation does not establish real-world orbital accuracy.
- The Horizons-based Eros simulation is currently implemented separately from the configurable synthetic simulator.
- The realistic simulation's accuracy depends on the included bodies, initial states and physical assumptions.
- Synthetic ground truth is exact only relative to the numerical model used to generate it.

## 8. Downstream interface

Component 2 should read `trajectory.csv` and its metadata. It must use the saved position and velocity units and coordinate conventions explicitly.

The observation generator is responsible for producing observation times and simulated sky measurements, including right ascension, declination and optional measurement noise. These observations must be stored separately from the true trajectory.
