# Diagnostic 1: C2 vs C3 Prediction Comparison

**Component:** Component 3 — Orbit Estimation and Candidate Orbit Generation
**Phase:** Phase 2 — Trial-Orbit Propagation and Observation Prediction
**Diagnostic:** 1 — C2 vs C3 prediction comparison
**Date:** 2026-11-13
**Constraint:** Read-only. No production source files, generated datasets,
or ground-truth files were modified.

## Objective

Compare the Component 3 forward-model observation prediction against the established Component 2 observation-coordinate implementation using identical inputs (same heliocentric asteroid states, epochs, observer configuration, and obliquity).

## Methodology

1. Constructed several trial heliocentric asteroid states (Cartesian, AU/AU/yr), including states that yield non-zero ecliptic latitudes.
2. Defined observation epochs in elapsed simulation years.
3. Ran C3 end-to-end: propagate_trial_state -> predict_apparent_coordinates (predict_from_orbit_state) to obtain C3 predicted RA/Dec.
4. Ran C2 manual pipeline using the C3-propagated asteroid heliocentric positions: calculate_observer_positions -> calculate_line_of_sight -> calculate_sky_coordinates to obtain C2 predicted RA/Dec.
5. Computed the independent C2 frames reference: ecliptic_to_equatorial -> calculate_ra_dec.
6. Compared RA using wrapped angular differences in [-180, 180) degrees, and Dec directly. Reported max absolute and RMS differences in degrees and arcseconds.

## Inputs

| Parameter | Value |
|-----------|-------|
| Observer orbital radius (AU) | 1.0 (C3 default) |
| Observer orbital period (yr) | 1.0 (C3 default) |
| Observer initial phase (deg) | 90.0 (C3 default) |
| Ecliptic obliquity (deg) | 23.43928 |
| Observer velocity | Not used (matches C2 simplified model) |
| Number of trial states | 4 |
| Number of epochs | 8 |
| Epochs (yr) | [0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0] |

## Results

### C3 forward model vs C2 calculate_sky_coordinates

| Quantity | Max |diff| (deg) | Max |diff| (arcsec) | RMS (deg) | RMS (arcsec) |
|----------|----------------|---------------------|-------------|---------------|
| RA (wrapped) | 0.000e+00 | 0.000e+00 | 0.000e+00 | 0.000e+00 |
| Dec | 0.000e+00 | 0.000e+00 | 0.000e+00 | 0.000e+00 |
| Samples compared | 32 |

### C3 forward model vs C2 frames reference

| Quantity | Max |diff| (deg) | Max |diff| (arcsec) | RMS (deg) | RMS (arcsec) |
|----------|----------------|---------------------|-------------|---------------|
| RA (wrapped) | 0.000e+00 | 0.000e+00 | 0.000e+00 | 0.000e+00 |
| Dec | 0.000e+00 | 0.000e+00 | 0.000e+00 | 0.000e+00 |
| Samples compared | 32 |

## Assessment

- C3 matches C2 calculate_sky_coordinates (tol 1e-09 deg): True
- C3 matches C2 frames reference (tol 1e-09 deg): True

## Truth separation

- ground_truth.json accessed: NO
- True trajectory data used: NO
- Inputs: C3-propagated trial states + C2 observer geometry only

## Conclusion

PASS: The C3 forward model produces RA/Dec predictions consistent with Component 2's calculate_sky_coordinates and the C2 frames reference within floating-point tolerance, for both ecliptic-plane and non-zero-ecliptic-latitude geometries. The declination denominator fix (observer.py line 328) is confirmed effective end-to-end.
