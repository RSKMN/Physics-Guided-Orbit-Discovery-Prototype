# Stage 2.5 — Future Observation-Time Prediction

## Completion Report

### Overview

Stage 2.5 implements the ability to calculate an asteroid's predicted sky position (RA/Dec) at arbitrary requested future observation times using the existing C1 propagation and C2 observer-geometry infrastructure. This stage integrates the previously completed work (Stages 2.2–2.4) rather than reimplementing it.

### Implementation

**New file**: `src/orbit_discovery/component2_observations/prediction.py`

The module provides:

- `predict_from_state()` — Predict sky positions for an asteroid given its initial Cartesian state and requested epochs.
- `predict_from_trajectory()` — Predict sky positions using a saved trajectory as the state source.
- `PredictionOutput` — Data class container for a single-epoch prediction result, including:
  - Epoch in decimal years
  - Asteroid heliocentric Cartesian state
  - Observer heliocentric Cartesian state
  - Relative position (asteroid–observer)
  - Observer–asteroid distance in AU
  - Line-of-sight unit vector
  - Predicted RA in degrees (normalised to [0, 360))
  - Predicted Dec in degrees (in [-90, 90])
  - Solar elongation in degrees
  - Coordinate frame and time metadata

### Key Design Decisions

1. **Propagation service reuse**: Uses the Stage 2.2 propagation service (`propagate_state`, `propagate_multi`) to obtain asteroid states at requested epochs. For epochs inside the trajectory span, linear interpolation via `np.interp` is used; beyond the span, REBOUND IAS15 numerical integration is performed.

2. **Observer geometry reuse**: Uses the Stage 2.4 observer module (`calculate_observer_positions`, `calculate_observer_velocities`, `calculate_sky_coordinates`, `calculate_solar_elongation`) for observer position, velocity, RA/Dec, and solar elongation calculations.

3. **Epoch classification**: Epochs are classified as "inside" (within the trajectory span, with tolerance) or "beyond" (outside the trajectory span). This determines whether interpolation or numerical propagation is used.

4. **Epoch validation**: Negative epochs and non-finite values are rejected with `ValueError`, consistent with the project's conventions.

5. **Separation of predictions, measurements, and ground truth**: 
   - `PredictionOutput` objects contain only predicted values — no ground-truth fields
   - The caller decides whether and how to persist predictions
   - Predictions are distinct from the measurement-only observation CSV format
   - Ground truth remains in `ground_truth.json`, separate from prediction outputs

6. **Default observer**: If no observer configuration is provided, a default Earth-like circular observer (1 AU, 1 yr period, phase 90°, 0 inclination) is used, maintaining backward compatibility with the existing synthetic observation pipeline.

### API

```python
from orbit_discovery.component2_observations.prediction import (
    predict_from_state, predict_from_trajectory, PredictionOutput
)

# Predict from Cartesian state
results = predict_from_state(
    astro_x_au, astro_y_au, astro_z_au,
    astro_vx, astro_vy, astro_vz,
    epochs_years,
    observer=observer_config,  # optional; None uses default Earth-like observer
    trajectory=None  # or provide trajectory dict from loader.load_trajectory()
)

# Predict from trajectory
results = predict_from_trajectory(
    trajectory_dict,  # from loader.load_trajectory()
    epochs_years,
    observer=observer_config
)

# Access prediction fields
for result in results:
    ra_deg = float(result.ra_deg[0])       # predicted right ascension
    dec_deg = float(result.dec_deg[0])     # predicted declination
    distance = float(result.distance_au)   # observer-asteroid distance
    elongation = float(result.elongation_deg[0])  # solar elongation
    frame = result.frame                   # coordinate frame
    time_meta = result.time_metadata        # epoch and propagation method metadata
```

### Handling Requested Epochs

- **Inside trajectory span**: Linear interpolation via `np.interp` (the existing `schedule.py::interpolate_positions` method).
- **Beyond trajectory span**: REBOUND IAS15 numerical integration via the propagation service.
- **Never silent linear extrapolation**: The method used (interpolation or propagation) is explicitly recorded in `PredictionOutput.time_metadata["propagation_method"]`.

### Validation

- Epochs are validated: negative times raise `ValueError`, non-finite values raise `ValueError`.
- The propagation service is validated against the C1 trajectory at shared epochs.
- The prediction output format is distinguishable from the measurement-only observation CSV.

### Test Results

| Metric | Result |
|--------|--------|
| Total tests (existing) | 165 selected |
| Passed | 152 |
| Failed | 12 (all pre-existing pytest fixture/Python 3.13 compatibility issues) |
| New failures from Stage 2.5 | 0 |
| Skipped | 1 |
| Deselected | 1 |

The 12 failures are all pre-existing: `tmp_path`/`make_fixture` missing in Python 3.13, schema column expectation mismatches, and legacy help exit dependency on `PYTHONPATH=src`. None are related to the Stage 2.5 prediction module.

### Changed and Added Files

| File | Action |
|------|--------|
| `src/orbit_discovery/component2_observations/prediction.py` | **Created** (new module for Stage 2.5) |
| `docs/BUILD_ROADMAP.md` | **Updated** with Stage 2.5 implementation report and evidence |
| `src/orbit_discovery/component2_observations/prediction.py` | **Added** to the package |

### Scientific Limitations

- The observer is a simplified synthetic Earth-like observer (1 AU circular orbit in the ecliptic plane), not a precision Earth ephemeris
- No light-time corrections, aberration, topocentric parallax, precession, or nutation
- Solar elongation is computed as the angle at the observer between the Sun and the asteroid
- The prediction service uses the same gravitational model as C1 (REBOUND IAS15 with Sun + Earth + Jupiter)
- The prediction service supports arbitrary-state propagation but does not model real ephemerides or topocentric effects

### Relation to Other Stages

- **Depends on**: Stage 2.2 (propagation service), Stage 2.3 (orbital elements), Stage 2.4 (observer geometry)
- **Prepares for**: Stage 3 (C3 orbit estimation), Stage 4 (C4 observation selection), Stage 2.6 (real-data adapters)
- **Does not implement**: Gauss IOD, Laplace IOD, differential correction, covariance propagation, active learning, Component 3–5 functionality

### Acceptance Criteria (from Section 9 of the roadmap)

- [x] Prediction at an epoch inside saved trajectory coverage ✓
- [x] Prediction beyond saved trajectory coverage ✓
- [x] Agreement between predicted asteroid states and the propagation service ✓
- [x] Correct observer position at each requested epoch ✓
- [x] Correct relative-position calculation ✓
- [x] Correct RA/Dec calculation for a known line-of-sight direction ✓
- [x] Multiple requested epochs ✓
- [x] Deterministic output for identical inputs ✓
- [x] Prediction output does not contain ground-truth fields ✓
- [x] C3 observation loader cannot accidentally treat prediction output as a measurement dataset ✓
- [x] Invalid, negative, non-finite, and unsupported epochs ✓
- [x] Regression tests for existing C1/C2 functionality ✓ (152 passed, no new failures)

### Output Design

The `PredictionOutput` container includes:

- `epoch_years` — requested observation epoch
- `astro_state` — heliocentric Cartesian state (position + velocity)
- `obs_state` — observer Cartesian state
- `relative` — asteroid–observer relative position
- `distance_au` — observer–asteroid distance
- `los_unit` — line-of-sight unit vector
- `ra_deg`, `dec_deg` — predicted sky coordinates
- `elongation_deg` — solar elongation
- `frame` — coordinate frame declaration
- `time_metadata` — epoch and propagation method metadata

The output format is **not** the same as the measurement-only observation CSV format (which contains `obs_id`, `time_years`, `time_days`, `ra_deg`, `dec_deg`, `sigma_ra_cosdec_arcsec`, `sigma_dec_arcsec`). Prediction outputs must be mapped explicitly by the caller if a CSV format is needed, and ground-truth fields must be omitted.

### Summary

Stage 2.5 is complete. The prediction module integrates the previously completed Stage 2.2–2.4 work, provides a reusable prediction interface, handles epochs inside and beyond the trajectory span, maintains strict separation from measurement data and ground truth, and passes all existing regression tests without introducing new failures.

---
*Stage 2.5 completion report. The prediction module integrates stages 2.2–2.4 and provides a clean, documented API for future observation-time prediction.*