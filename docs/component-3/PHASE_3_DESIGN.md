# Component 3 — Phase 3 Design: Orbit Estimation

**Component:** Component 3 — Orbit Estimation and Candidate Orbit Generation
**Phase:** 3 — Orbit estimation (design and investigation only)
**Status:** Phase 3A design approved; Phase 3B residual calculation implemented, hardened, tested and approved.
**Baseline:** v0.3.0 (commit `d86bdba`), Phase 1 and Phase 2 complete and accepted
**Date:** 2026-11-13
**Released in:** v0.4.0

---

## 1. Current architecture and interfaces

This section records the exact interfaces the estimator will reuse. No production source file is modified by this design.

### 1.1 Component 1 (authoritative planetary model)

`src/configurable_simulator.py` exports `BODY_DATA`, a dict mapping body name → `{"mass": Msun, "a": AU}` for Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus, Neptune. C1 builds simulations with `sim.units = ("yr", "AU", "Msun")`, the Sun at `m=1.0`, planets circular and coplanar (`e=0`, `inc=0`) at perihelion on the +x axis, IAS15 integrator with `epsilon = 1e-12`. Component 3 must import these constants rather than duplicate them.

### 1.2 Component 2 observation data contract

`src/orbit_discovery/component2_observations/schema.py` (`V2_REQUIRED`, `V2_FORBIDDEN`) and `c3_loader.py` (`load_observation_dataset`).

| Column | Unit | Meaning |
|---|---|---|
| `obs_id` | int | Observation identifier |
| `time_years` | year | Elapsed time from reference epoch (t = 0) |
| `time_days` | day | `time_years × 365.25` |
| `ra_deg` | deg | Right ascension, normalized to [0, 360) |
| `dec_deg` | deg | Declination, within [-90, 90] |
| `sigma_ra_cosdec_arcsec` | arcsec | RA uncertainty in the tangent plane, **already multiplied by cos(dec)** |
| `sigma_dec_arcsec` | arcsec | Declination uncertainty |
| `frame` | str | Coordinate frame (e.g. "equatorial") |
| `time_scale` | str | Time scale (e.g. "TT") |

`V2_FORBIDDEN` rejects any `true_*` column (ground-truth leakage). The C3 loader (`load_dataset_for_estimation`) wraps the C2 loader and adds C3-specific validation: finite values, positive uncertainties, RA/Dec ranges, time-column consistency, non-decreasing timestamps, and ground-truth-column rejection.

Noise semantics (C2 `noise.py`, `add_measurement_noise`): independent Gaussian errors are drawn in arcseconds with standard deviations `sigma_ra_cosdec_arcsec` and `sigma_dec_arcsec`. The RA tangent-plane error is converted to a coordinate RA offset by dividing by `cos(dec)`, then RA is normalized mod 360. This confirms `sigma_ra_cosdec_arcsec` is the tangent-plane (cos(dec)-weighted) uncertainty, not the raw RA-coordinate uncertainty.

### 1.3 Component 3 data models (`models.py`)

- `OrbitState(rx, ry, rz, vx, vy, vz)` — frozen dataclass, 6D heliocentric ecliptic inertial Cartesian state, position AU, velocity AU/year, reference epoch `REFERENCE_EPOCH_YEARS = 0.0`. `validate()` requires all six components finite. `to_array()` → `[rx, ry, rz, vx, vy, vz]`; `to_dict()`/`from_dict()`.
- `ObservationDataset(data, frame, time_scale, metadata)` — validated measurement container.
- `OrbitCandidate(state, epoch_years, metadata)` — a single candidate orbit solution.
- `BestFitResult(state, epoch_years, residuals, fit_metrics)` — fit output; `residuals` and `fit_metrics` are dicts, extensible without changing the model.
- `EstimationResult(candidates, best_fit, source_dataset_metadata)` — overall result.

### 1.4 Component 3 forward model (`dynamics.py`, `observation_model.py`)

- `build_trial_simulation(bodies, integrator_epsilon)` — fresh REBOUND simulation matching C1; imports `BODY_DATA` from C1 (no duplication); Sun + planets + massless asteroid placeholder; `sim.move_to_com()`; IAS15, ε=1e-12; units (yr, AU, Msun).
- `propagate_trial_state(state, epochs_years, bodies)` — propagates a trial state from the reference epoch (t=0) to each epoch. **Validates epochs must be >= 0 and finite** — backward propagation is currently rejected with `ValueError`. Epochs integrated sequentially in sorted order; results returned in input order. Returns per-epoch dicts with `x_au, y_au, z_au, vx_au_per_year, vy_au_per_year, vz_au_per_year, epoch_years` (heliocentric, Sun-relative).
- `propagate_trial_state_single(state, target_time_years, bodies)` — single-epoch wrapper.
- `reconstruct_observer_config(metadata)`, `get_obliquity_deg(metadata)` — reconstruct the Component 2 observer (circular, 1 AU, 1 yr, phase 90°) and obliquity (23.43928°) from observation metadata.
- `predict_apparent_coordinates(asteroid_states, epochs_years, observer_config, obliquity_deg)` — observer positions → relative vectors → LOS unit vectors → ecliptic-to-equatorial rotation → RA/Dec. RA normalized [0,360), Dec clipped [-90,90].
- `predict_from_orbit_state(state, epochs_years, observer_config, obliquity_deg, bodies)` — end-to-end forward model: `(propagation_results, predictions)`.

Gravitational parameter: REBOUND's `sim.G = 39.476926421373` with `M_sun = 1.0`, i.e. μ = 39.476926421373 AU³/yr². No light-time correction, aberration, or relativistic effects.

### 1.5 Dependencies

`pyproject.toml` / `requirements.txt`: `rebound>=5.2,<6`, `numpy>=2.5,<3`, `pandas>=3.1,<4`, `matplotlib>=3.11,<4`. **SciPy is not installed and is not a project dependency.** Per the stopping conditions, no new dependencies may be added. The baseline optimizer must therefore be implemented with NumPy only (see Section 4).

---

## 2. Mathematical formulation

### 2.1 State definition

The estimated state is the six-dimensional Cartesian vector at the reference epoch `t0 = 0.0 yr`:

```
x = [x, y, z, vx, vy, vz]
```

| Element | Unit | Frame |
|---|---|---|
| x, y, z | AU | Heliocentric ecliptic inertial position |
| vx, vy, vz | AU/year | Heliocentric ecliptic inertial velocity |
| t0 | year | Reference epoch = 0.0 (elapsed simulation time) |

This matches `OrbitState` exactly and the reference-epoch convention already documented in `models.py` (`REFERENCE_EPOCH_YEARS = 0.0`).

### 2.2 Forward model (propagation to observation epochs)

Given a trial state `x` at `t0`, the predicted apparent coordinates at observation epoch `t_i` are obtained by:

1. **Propagate** the massless asteroid from `t0` to `t_i` using the C3 REBOUND/IAS15 forward model (`propagate_trial_state`), yielding heliocentric position `r_i = (x_i, y_i, z_i)` in AU.
2. **Compute observer position** `o_i` at `t_i` from the reconstructed `ObserverConfig` (Component 2's `calculate_observer_positions`), heliocentric ecliptic, AU.
3. **Form the line-of-sight vector** `rho_i = r_i - o_i` and its unit vector `uhat_i = rho_i / |rho_i|`.
4. **Rotate ecliptic → equatorial** using the fixed obliquity `ε = 23.43928°`.
5. **Convert to RA/Dec**: `ra_i = atan2(y_eq, x_eq)` normalized to [0, 360), `dec_i = atan2(z_eq, sqrt(x_eq² + y_eq²))` within [-90, 90].

This is exactly `predict_from_orbit_state`, which the estimator calls as its forward model. It reuses existing C3 dynamics and observation prediction without modification.

### 2.3 Reference epoch and observations before/after it

The observation dataset contains epochs `t_i >= 0` (elapsed from simulation start), and `propagate_trial_state` currently requires `t_i >= 0`. The reference epoch `t0 = 0` is therefore at or before the start of every available observation arc in the current datasets (arcs begin at day 0), so all observation epochs are reachable by forward propagation.

**Recommendation for the baseline:** keep the reference epoch fixed at `t0 = 0` and require all observation epochs `t_i >= t0` (forward propagation only). This matches the current `dynamics.py` contract and requires no change to `propagate_trial_state`.

**Backward propagation:** a general estimator may wish to place the reference epoch inside the observation arc (e.g. at the mid-arc epoch), which would require propagating to epochs both before and after `t0`. REBOUND's `sim.integrate(t)` supports negative `t` natively, but the current `propagate_trial_state` explicitly rejects `t < 0`. Supporting backward propagation would require:
- Removing/relaxing the `t >= 0` check in `propagate_trial_state` (or adding a separate backward-capable path),
- Ensuring sequential integration handles unsorted / negative epochs correctly,
- Re-validating determinism and stability diagnostics for negative integration.

This is a future extension, not part of the Phase 3 baseline scope. The design below assumes `t0 <= min_i t_i` (all epochs forward of the reference epoch).

### 2.4 Objective

The estimator solves a weighted nonlinear least-squares problem:

```
minimize   chi2(x) = sum_i [ w_ra_i(x)^2 + w_dec_i(x)^2 ]
over       x in R^6
```

where `w_ra_i`, `w_dec_i` are the normalized (uncertainty-weighted) angular residuals defined in Section 3. The solution `x_hat` is the best-fit heliocentric state at `t0`.

---

## 3. Residual and weighting design

### 3.1 Quantities and units

All angular quantities below are in degrees unless stated. Uncertainties `sigma_ra_cosdec_arcsec`, `sigma_dec_arcsec` are in arcseconds (`1 arcsec = 1/3600 deg`, per `core.constants.ARCSEC_TO_DEG`).

For observation `i`:
- Observed: `ra_i^o`, `dec_i^o` (deg, from CSV).
- Predicted: `ra_i^p(x)`, `dec_i^p(x)` (deg, from forward model, `ra` ∈ [0,360), `dec` ∈ [-90,90]).
- Uncertainties: `s_ra_i = sigma_ra_cosdec_arcsec[i]`, `s_dec_i = sigma_dec_arcsec[i]` (arcsec).

### 3.2 RA wraparound

The raw RA difference must be wrapped to the shortest angular distance before any weighting:

```
dra_raw   = ra_i^o - ra_i^p                          (deg, may exceed ±180)
dra_wrap  = ((dra_raw + 180) mod 360) - 180          (deg, in [-180, 180))
```

This is applied once, before the cos(dec) factor. Because both observed and predicted RA are normalized to [0, 360) by the generator and the forward model respectively, `dra_raw` is well-defined and wrapping handles the branch cut at RA = 0/360.

**Limitation:** wrapping creates a branch discontinuity at ±180 degrees: a residual just below +180° and one just above -180° represent the same small physical angle but differ by ~360° in the wrapped value. Consequently the residual formulation is intended for **local refinement from a reasonably close initial guess**, not for arbitrary distant initial states. Wrapping does not make the objective globally smooth and does not guarantee convergence from poor guesses (see Section 5).

### 3.3 Declination residual

```
dd = dec_i^o - dec_i^p                               (deg, in [-180, 180])
```

No wrapping is needed because both values lie in [-90, 90], so `dd ∈ [-180, 180]`. Near the poles the tangent-plane approximation degrades (see Section 3.7).

### 3.4 RA*cos(dec) residual and avoiding double application of cos(dec)

**Critical:** `sigma_ra_cosdec_arcsec` is the tangent-plane RA uncertainty, i.e. it already includes the `cos(dec)` factor (confirmed by C2 `noise.py`, which converts `ra_noise_arcsec / cos(dec)` into a coordinate RA offset). Therefore:

- Convert the wrapped RA difference to tangent-plane (arc-length) units by multiplying by `cos(dec_obs)` — the **observed** declination is used as the fixed reference:
  ```
  dra_tan_deg = dra_wrap * cos(dec_i^o)              (deg)
  ```
  Justification: `sigma_ra_cosdec_arcsec` represents tangent-plane uncertainty associated with the observed measurement (C2 `noise.py` draws the RA noise relative to the observed declination), so `cos(dec_obs)` is the consistent reference. The predicted declination is not used here, so the residual's cos(dec) factor is fixed with respect to the optimizer's trial state.
- Convert both angular residuals from degrees to arcseconds (× 3600):
  ```
  dra_tan_arcsec = dra_tan_deg * 3600
  dd_arcsec      = dd * 3600
  ```

This applies cos(dec) exactly once to the residual, matching the single cos(dec) already embedded in the uncertainty — **no double application**.

### 3.5 Normalized residuals

```
w_ra_i  = dra_tan_arcsec  / s_ra_i     (dimensionless)
w_dec_i = dd_arcsec       / s_dec_i    (dimensionless)
```

The normalized residual vector stacks all observations:

```
r(x) = [ w_ra_1, w_dec_1, w_ra_2, w_dec_2, ..., w_ra_N, w_dec_N ]^T   (length 2N)
```

### 3.6 Chi-square objective

```
chi2(x) = r(x)^T r(x) = sum_i (w_ra_i^2 + w_dec_i^2)
```

The Gauss-Newton / Levenberg-Marquardt optimizer minimizes `chi2` (equivalently `||r||²`, since `chi2 = ||r||²` and the factor of 2 in the gradient is absorbed into the damping parameter).

### 3.7 Behavior near celestial poles and large residuals

- **Near the poles** (`|dec| → 90°`, `cos(dec) → 0`): multiplying the RA residual by `cos(dec_obs)` drives `dra_tan → 0`, which is geometrically correct (RA is ill-defined at the pole). Because `cos(dec_obs)` is a fixed constant (it depends only on the observed measurement, not on the optimizer's trial state), this does not introduce state-dependent scaling into the residual or the finite-difference Jacobian.
- **Pole exclusion and residual counting policy:** do **not** dynamically drop RA residual components based on the predicted declination during optimization. Changing the residual-vector dimension as the optimizer moves would invalidate finite-difference Jacobians and the chi-square comparison between iterations. Instead:
  - Before optimization, screen each observation: if `cos(dec_i^o)` is below a small threshold (e.g. `1e-12`, consistent with the C2 noise generator's pole guard), the observation is geometrically degenerate.
  - **Baseline disposition:** prefer excluding the entire observation (both its RA and Dec residuals) from the fit up front, or rejecting the dataset entirely. Do not exclude only the RA component while retaining Dec, since that mixes tangent-plane and coordinate residuals inconsistently and changes residual dimension.
  - Keep a fixed residual structure for every retained observation throughout optimization. Do not silently discard residual components during iterations.
  - Define `n_valid_scalar_residuals = 2 × N_retained`, where `N_retained` is the number of observations retained after pole screening. Define `effective_parameter_rank` as the numerical rank of `J_phys` (6 for the full six-dimensional Cartesian state when full rank, less if parameters are fixed or rank-deficient).
  - Degrees of freedom:
    ```
    dof = n_valid_scalar_residuals - effective_parameter_rank
    ```
    e.g. `dof = 2 × N_retained - 6` for the full Cartesian state with no exclusions. It is **not** automatically `2N − 6` when observations are excluded as degenerate; `N` in that expression refers to retained observations only.
- **Large angular residuals:** wrapped angular residuals are intended for **local refinement from a sufficiently close initial guess**. Wrapping bounds each individual RA difference to [-180, 180) so residuals do not blow up from branch-cut jumps near the solution region, and Dec residuals are bounded by the [-90, 90] clipping of observed and predicted values. This does **not** imply a globally smooth or globally well-behaved objective: wrapping creates a branch discontinuity at ±180 degrees (see Section 3.2), and convergence from an arbitrary distant initial guess is not guaranteed.
- **Recommendation:** simple wrapped coordinate residuals with the cos(dec) tangent-plane weighting are sufficient for the initial estimator. Spherical tangent-plane (gnomonic) projection residuals are a refinement for a later phase if sub-arcsecond fidelity near the poles is required. They are not needed for the baseline because the observation noise (0.5 arcsec) and the synthetic arcs are far from the poles.

### 3.8 Derivatives (Jacobian)

The optimizer works in scaled parameter coordinates `u = x / s`, where `x` is the physical six-dimensional state (AU, AU/year) and `s = (s_1, ..., s_6)` is a per-component characteristic scale (e.g. position scale = 1 AU, velocity scale = circular speed at 1 AU ≈ sqrt(μ) ≈ 6.28 AU/yr). The residual vector is a function of scaled parameters: `r(u)`.

With SciPy unavailable, the baseline uses **numerical Jacobian by forward finite differences in scaled coordinates**:

```
h_k = sqrt(eps) * max(abs(u_k), 1)
J_scaled[:, k] ≈ (r(u + h_k e_k) - r(u)) / h_k
```

where `eps` is machine epsilon, `e_k` is the k-th unit vector in scaled space, and `max(abs(u_k), 1)` ensures a non-vanishing step even when `u_k` is exactly zero. Each Jacobian evaluation requires 6 forward-model evaluations (one per scaled parameter), plus one for the residual at `u`.

The physical Jacobian is recovered by the chain rule:

```
J_phys = J_scaled @ diag(1/s)
```

so that `J_phys = ∂r/∂x` is the Jacobian of the normalized residual vector with respect to the physical six-dimensional state. `J_phys` is used for:

- the gradient convergence criterion `||J_physᵀ r||_inf` (equivalently `||J_scaledᵀ r||_inf` up to the known diagonal scaling),
- covariance computation `cov ≈ (J_physᵀ J_phys)⁻¹` in physical state units (AU and AU/year).

**Optimizer step-size convergence** is evaluated in scaled coordinates, e.g. `||δu|| / ||u|| < tol_x`, since scaled parameters are dimensionless and comparable across components. Central differences `(r(u+h) - r(u-h)) / (2h)` are more accurate but double the cost; forward differences are sufficient for the baseline.

---

## 4. Optimizer recommendation

### 4.1 Constraint check

SciPy (including `scipy.optimize.least_squares`) is **not installed** and is not a project dependency. The stopping conditions prohibit adding dependencies or modifying configuration files. Therefore the baseline optimizer must be implemented using NumPy only.

### 4.2 Candidate optimizers considered

| Optimizer | Mechanism | Dependency | Fit for baseline |
|---|---|---|---|
| SciPy `least_squares` (TRF / LM) | Trust-region reflective or Levenberg–Marquardt, analytic or FD Jacobian | SciPy (not installed) | Recommended for a later phase if SciPy is added; not usable now |
| Hand-rolled Levenberg–Marquardt | `(JᵀJ + λ·diag(JᵀJ)) δ = -Jᵀ r`, adaptive λ | NumPy only | **Baseline recommendation** |
| Hand-rolled Gauss–Newton | `JᵀJ δ = -Jᵀ r`, no damping | NumPy only | Simpler but less robust to poor scaling / singular JᵀJ |
| Steepest descent | `x ← x - α ∇chi2` | NumPy only | Too slow / poorly conditioned; not recommended |

### 4.3 Baseline: hand-rolled Levenberg–Marquardt (NumPy only)

**Why LM:** It interpolates between Gauss–Newton (fast near the solution) and gradient descent (robust far from the solution) via the damping parameter λ. It is the standard choice for orbit determination because the normal equations `JᵀJ` can be ill-conditioned (especially when the arc is short or the state is poorly constrained), and LM's damping handles that robustly.

**Algorithm (per iteration, in scaled coordinates `u`):**

1. Evaluate residual `r = r(u)` via the forward model + Section 3 residuals.
2. Compute the numerical Jacobian `J_scaled` by forward finite differences in scaled coordinates (Section 3.8). Form `J_phys = J_scaled @ diag(1/s)`.
3. Solve the damped LM normal equation for the scaled step `δu`:
   ```
   (J_scaledᵀ J_scaled + λ · diag(J_scaledᵀ J_scaled)) δu = -J_scaledᵀ r
   ```
4. Map the step back to physical coordinates: `δx = s ⊙ δu`. Tentatively update `u_trial = u + δu` (equivalently `x_trial = x + δx`).
5. Evaluate `chi2(u_trial)` via the forward model + Section 3 residuals.
6. Define the **predicted reduction** in chi² from the linearized (Gauss-Newton) model:
   ```
   pred_reduction = -2 · (J_scaledᵀ r)ᵀ δu - δuᵀ (J_scaledᵀ J_scaled) δu
   ```
   This equals `||r||² - ||r + J_scaled δu||²`, the reduction predicted by linearizing the residuals. With the LM step above, `pred_reduction = δuᵀ (J_scaledᵀ J_scaled) δu + 2λ · δuᵀ diag(J_scaledᵀ J_scaled) δu`, which is positive for λ > 0 when `J_scaled` has full column rank.
7. Compute the **gain ratio** `rho = (chi2(u) - chi2(u_trial)) / pred_reduction`.
   - If `pred_reduction` is not positive or not finite, the step is not trustworthy: reject it and increase λ (e.g. λ ← λ · ν, ν > 1, cap λ_max), then recompute the step. Do not accept the step on a non-positive or non-finite predicted reduction.
   - If `chi2(u_trial)` is not finite, reject the step and increase λ.
   - If `rho > 0`: accept the step (`u ← u_trial`), decrease λ (e.g. λ ← λ · max(1/3, 1 - (2ρ - 1)³), floor λ_min).
   - Else (`rho <= 0`): reject the step, increase λ (e.g. λ ← λ · ν, ν > 1, cap λ_max).
8. Iterate until convergence (Section 4.3 convergence criteria).

This is a single Levenberg–Marquardt formulation; no alternative optimizer (e.g. trust-region reflective or Gauss–Newton without damping) is introduced in the baseline.

**Parameter scaling and covariance consistency:** State components have heterogeneous units and magnitudes (position ~1–10 AU, velocity ~0.1–10 AU/yr). The optimizer works in scaled parameter space:

- **Physical state** `x` (AU, AU/year): the six components of `OrbitState`.
- **Scaled optimizer parameters** `u = x / s` (dimensionless), where `s = (s_1, ..., s_6)` is a characteristic scale per component (e.g. position scale = 1 AU, velocity scale = circular speed at 1 AU ≈ sqrt(μ) ≈ 6.28 AU/yr, or the magnitude of the current guess). Solve the LM step in scaled space and map back via `δx = s ⊙ δu`.

Two Jacobians are distinguished:

- `J_phys = ∂r/∂x` — Jacobian of the normalized residual vector w.r.t. the **physical** six-dimensional state (used for covariance and for reporting gradients in physical units).
- `J_scaled = ∂r/∂u = J_phys · diag(s)` — Jacobian w.r.t. the **scaled** optimizer parameters (used internally to form the well-conditioned normal equations `J_scaledᵀ J_scaled`).

The covariance is computed in physical units by transforming back:

```
cov_phys = (J_physᵀ J_phys)⁻¹     (for known absolute measurement uncertainties)
```

Equivalently, `cov_phys = diag(s) · (J_scaledᵀ J_scaled)⁻¹ · diag(s)`. This keeps the covariance in AU² and (AU/year)², consistent with `OrbitState`. Scaling is applied only inside the optimizer step; all reported outputs (state, covariance, uncertainties) are in physical units.

This prevents velocity components from dominating the step while keeping the Jacobian and covariance transformations consistent between physical and scaled parameterizations.

**Convergence criteria** (any one triggers termination):
- Relative change in chi2: `|chi2_new - chi2_old| / chi2_old < tol_chi2` (e.g. 1e-10).
- Relative step size in scaled coordinates: `||δu|| / ||u|| < tol_x` (e.g. 1e-10). Scaled coordinates are dimensionless, so this threshold is comparable across state components.
- Gradient norm: `||J_physᵀ r||_inf < tol_grad` (e.g. 1e-8). Equivalently `||diag(1/s) · J_scaledᵀ r||_inf`, since `J_phys = J_scaled @ diag(1/s)`.
- Maximum iterations (e.g. 100) and maximum function evaluations (e.g. 1000) as hard caps.

**Failed propagation handling:** If `propagate_trial_state` raises `ValueError` (REBOUND integration failure, collision, non-finite state) for a trial state, treat that trial as unacceptable: return a large residual vector (e.g. all entries = a large constant) so the optimizer rejects the step and increases damping. Do not crash; do not fall back to ground truth.

**Physical plausibility constraints:** The baseline enforces only finiteness of propagated states (already guaranteed by `dynamics.py` validation). Hard bounds (e.g. perihelion > 0, no planet crossing) are deferred; the estimator returns the best-fit state and the caller validates physical plausibility post-hoc. This keeps Phase 3 scoped to weighted least squares.

---

## 5. Initial-state strategy

This is the most important scientific scoping decision.

### 5.1 The problem

The optimizer requires a starting state `x0`, but the observation dataset contains only noisy RA/Dec — no true orbit, no distance, no velocity. An arbitrary initial state will generally **not** converge to the true orbit. Orbit determination from angles-only data is a classic ill-conditioned problem; a good initial guess is essential.

### 5.2 Strategies considered

| Strategy | Description | Feasibility in Phase 3 |
|---|---|---|
| Explicit user-supplied initial state | Caller provides `OrbitState` at `t0`. | **Baseline scope.** Simple, honest about the requirement. |
| Preliminary orbit from a subset (e.g. Gauss / Gooding method) | Angles-only initial orbit determination from 3 observations. | Out of scope; requires implementing classical IOD, significant new math. |
| Range / range-rate hypotheses | Grid-search over distance and range-rate, pick best. | Out of scope; effectively a multi-start / discovery system. |
| Multiple initial guesses / multi-start | Run LM from several starts, keep best chi2. | Future enhancement; not baseline. |

### 5.3 Baseline recommendation

**Phase 3 baseline: estimator fits a user-supplied initial guess.** The estimator's public entry point accepts an `OrbitState` initial guess (at `t0`) plus the `ObservationDataset`, runs the LM optimizer, and returns the best-fit result. It makes no claim of converging from an arbitrary guess; the caller is responsible for supplying a physically plausible starting orbit (e.g. from a preliminary-orbit tool or an approximate orbit known from other data).

**Explicit distinction:**
- **Baseline estimator (Phase 3):** fits a *supplied* initial guess via weighted least squares. Convergence to the true orbit is contingent on the guess being in the basin of attraction.
- **Autonomous orbit-discovery system (future):** generates plausible initial guesses from the observations alone (IOD, multi-start, range grids) and selects the best solution. This is explicitly **not** part of Phase 3 and should not be conflated with the baseline estimator.

**Recovery testing (Section 7)** uses a deliberately perturbed initial guess (not the true state) to demonstrate the estimator can recover from a nearby-but-wrong start, which is the realistic baseline scenario.

---

## 6. Output model design

### 6.1 Reuse vs. extension

Existing models are reused **without modification** (per stopping conditions: "Do not change models yet"):

- `OrbitState` — best-fit Cartesian state at `t0`. Reused directly.
- `OrbitCandidate` — candidate orbit solutions. Reused; the best-fit candidate and any multi-start candidates (future) go here.
- `BestFitResult(state, epoch_years, residuals, fit_metrics)` — `state` = best-fit `OrbitState`; `epoch_years` = `t0`; `residuals` = dict of residual arrays (e.g. `{"ra": ..., "dec": ...}` in arcsec); `fit_metrics` = dict of scalar fit statistics. All new scalar outputs (chi2, reduced chi2, RMS, n_iter, nfev, convergence status, covariance) go into `fit_metrics` — no model change required.
- `EstimationResult(candidates, best_fit, source_dataset_metadata)` — overall result; `candidates` holds the best-fit `OrbitCandidate`; `source_dataset_metadata` preserves the observation provenance.

### 6.2 Recommended outputs (all produced by the estimator)

| Output | Where | Justification |
|---|---|---|
| Best-fit Cartesian state `[x,y,z,vx,vy,vz]` at `t0` | `BestFitResult.state` | Primary product; reuses `OrbitState`. |
| Predicted observations (RA, Dec per epoch) | `BestFitResult.residuals["ra_pred"]`, `["dec_pred"]` (deg) | Enables residual inspection and plotting. |
| Residuals (observed − predicted, arcsec) | `BestFitResult.residuals["ra"]`, `["dec"]` | Core diagnostic. |
| Normalized residuals | `BestFitResult.residuals["ra_norm"]`, `["dec_norm"]` | For chi2 and sigma-clipping diagnostics. |
| Chi-square | `fit_metrics["chi2"]` | Objective value at solution. |
| Degrees of freedom | `fit_metrics["dof"]` = (number of valid scalar residuals) − (effective parameter rank), e.g. `2 × N_retained − 6` for the full Cartesian state with no exclusions (when valid) | Needed for reduced chi2. Not automatically `2N − 6` when observations are excluded as degenerate. |
| Reduced chi-square | `fit_metrics["chi2_reduced"]` = chi2 / dof (when dof > 0) | Goodness-of-fit; only reported when dof = (valid scalar residuals) − (effective parameter rank) > 0. |
| RMS angular residual | `fit_metrics["rms_ra_arcsec"]`, `["rms_dec_arcsec"]`, `["rms_total_arcsec"]` | Interpretive fit quality in arcsec. |
| Optimizer convergence status | `fit_metrics["converged"]` (bool), `["termination_reason"]` (str) | Whether LM met a convergence criterion. |
| Iteration count | `fit_metrics["n_iter"]` | Optimizer diagnostics. |
| Function evaluation count | `fit_metrics["nfev"]` | Optimizer diagnostics (forward-model + residual evals). |
| Covariance / uncertainty | `fit_metrics["covariance"]` (6×6), `["sigma_state"]` (6,) | If mathematically justified: `cov ≈ (JᵀJ)⁻¹` for known absolute measurement uncertainties, where J is the Jacobian of the normalized residual vector w.r.t. the physical six-dimensional state. Only when `JᵀJ` is full column rank and numerically well conditioned. Multiplying by reduced chi-square (`sigma² = chi2 / dof`) is an optional variance-rescaling convention only when measurement variance is being estimated or rescaled — it must not be applied automatically. Otherwise report as `None` and note ill-conditioning. |
| Candidate orbit info | `EstimationResult.candidates[0]` = `OrbitCandidate(best_fit.state, t0, metadata)` | Orbit candidate container, per existing model. |
| Source dataset metadata | `EstimationResult.source_dataset_metadata` | Provenance / traceability. |

**Covariance caveat:** For known absolute measurement uncertainties, the first-order covariance is `cov ≈ (JᵀJ)⁻¹`, justified only near the solution, with `J` the Jacobian of the normalized residual vector with respect to the physical six-dimensional state and `J` full column rank. Positive degrees of freedom are **not** required for this unscaled covariance when absolute measurement uncertainties are known. Positive dof is required only for reduced chi-square (`chi2 / dof`) and for the optional variance-rescaled covariance (`sigma² = chi2 / dof` applied to `(JᵀJ)⁻¹`), which is a convention only when measurement variance is being estimated or rescaled — it must not be applied automatically. With a short arc or poorly observed components (e.g. along-track velocity), `JᵀJ` can be near-singular; the estimator must assess numerical conditioning (e.g. via Cholesky failure or condition number) and report the covariance as unavailable rather than produce nonsense. If optimization uses scaled parameters, the covariance must be transformed back to physical state units (AU and AU/year).

---

## 7. Scientific validation plan

All validation lives in the **separate test/evaluation path**. Production estimator code never reads `ground_truth.json`, true trajectory data, or `true_*` columns (truth separation enforced by `V2_FORBIDDEN` and the loader).

### 7.1 Test data generation (evaluation path only)

Use the existing Component 2 generator to produce synthetic observations from a **known test orbit** (known state at `t0`). Fixed random seeds (`random_seed` in metadata) for reproducibility. Use the existing baseline datasets (`data/observations/synthetic_asteroid_observations`, etc.) and/or generate dedicated test arcs with varied cadence, arc length, and noise.

### 7.2 Validation cases

1. **Known-orbit recovery:** Generate noisy observations from a known orbit; run the estimator from a perturbed initial guess; compare the estimated state to the known state (comparison performed only in the test path, using `ground_truth.json` / known orbit as reference). Report position and velocity errors in AU and AU/yr.
2. **Noise sensitivity:** Repeat case 1 at several noise levels (e.g. 0.1, 0.5, 1.0, 2.0 arcsec); verify estimated-state error scales approximately with noise and chi2_reduced ≈ 1.
3. **Cadence and arc-length sensitivity:** Vary observation cadence (e.g. 1, 7, 14 days) and arc length (e.g. 30, 90, 1825 days); verify recovery degrades gracefully as the arc shortens (angles-only observability weakens).
4. **Perturbed initial guess:** Start the optimizer from the true state perturbed by a controlled amount (e.g. 1–5% in position/velocity); verify convergence back to within the noise-induced uncertainty. This is the realistic baseline scenario.
5. **Angular residual reduction:** Verify RMS angular residual decreases from the initial guess to the best fit, and that chi2_reduced ≈ 1 at the solution for correctly specified noise.
6. **Convergence failure cases:** Deliberately poor initial guesses (outside the basin of attraction), too few observations (2N ≤ 6 → dof invalid), and degenerate geometries (object near the pole); verify the estimator reports non-convergence rather than returning a spurious state.
7. **RA wraparound case:** An observation arc crossing RA = 0/360; verify wrapped residuals are handled and recovery still succeeds.
8. **Truth isolation:** Static/source check that production modules (`dynamics.py`, `observation_model.py`, the new estimator module) contain no reference to `ground_truth`, `true_ra`, `true_dec`, or interpolation of the true trajectory (mirrors the existing `test_no_ground_truth_access` test).

### 7.3 Success criteria

- From a perturbed-but-plausible initial guess, the estimator converges and the estimated state matches the known state within the noise-derived uncertainty.
- chi2_reduced ≈ 1 when noise is correctly specified.
- Covariance (when reported) is consistent with the observed scatter across repeated noise realizations.
- All failure cases produce a clear non-convergence status, never a silent wrong answer.

---

## 8. Proposed implementation subphases

The initial implementation stays scoped to a **weighted least-squares estimator that fits a user-supplied initial guess**. Autonomous initial-guess generation (orbit discovery) is deliberately excluded.

| Subphase | Scope | Files to create/modify | Math functionality | Tests | Expected output | Dependencies | Risks | Completion criteria |
|---|---|---|---|---|---|---|---|---|
| **3A** | Design (this document) | `docs/component-3/PHASE_3_DESIGN.md` | Formulation, residuals, optimizer, outputs, validation plan | N/A | Approved design | None | Design gaps | Review sign-off |
| **3B** | Residual & weighting module | `src/orbit_discovery/component3/residuals.py` (new) | Wrapped RA residual, Dec residual, cos(dec) tangent-plane weighting, arcsec conversion, normalized residual vector, chi2 | Unit tests for wraparound, pole guard, weighting, chi2 | `residuals(x)` and `chi2(x)` functions | NumPy | Double-counting cos(dec) | Tests pass; no double cos(dec) |
| **3C** | Optimizer (LM, NumPy only) | `src/orbit_discovery/component3/optimizer.py` (new) | Levenberg–Marquardt, numerical forward-difference Jacobian, parameter scaling, adaptive damping, convergence criteria, failed-propagation handling | Unit tests on synthetic 2D/6D convex problems; convergence and failure behavior | `least_squares_lm(x0, fun, jac, ...)` → result dict | NumPy | Ill-conditioned JᵀJ | Converges on well-posed problems; reports failure gracefully |
| **3D** | Estimator orchestrator | `src/orbit_discovery/component3/estimator.py` (new) | Combine forward model (`predict_from_orbit_state`) + residuals + LM; assemble outputs into existing models | Integration test on synthetic observations | `estimate_orbit(initial_state, dataset) -> EstimationResult` | NumPy, C1/C2/C3 | Forward-model cost per eval | End-to-end fit runs and returns populated result |
| **3E** | Output assembly into models | (part of 3D; no new files) | Populate `BestFitResult`, `fit_metrics`, `EstimationResult` (chi2, dof, chi2_reduced, RMS, n_iter, nfev, converged, covariance when justified) | Verify metrics against hand calculation | Fully populated result object | None | Covariance near-singularity | Metrics correct; covariance `None` when singular |
| **3F** | Validation tests (evaluation path) | `tests/test_component3_phase3.py` (new, test-only) | Synthetic recovery, noise sensitivity, cadence/arc sensitivity, perturbed guess, failure cases, RA wraparound, truth isolation | All Section 7 cases | Test suite passes | NumPy; ground_truth.json **test-only** | Test accidentally leaks truth into production | Production code truth-free; tests pass |
| **3G** | Validation report | `docs/component-3/PHASE_3_VALIDATION.md` (new) | Summarize validation results | N/A | Report | None | N/A | Report documents recovery performance |

No existing production source files, tests, or configuration files are modified in any subphase.

---

## 9. Risks and limitations

| Risk | Impact | Mitigation |
|---|---|---|
| **No SciPy available** | Must hand-roll LM with numerical Jacobian; less battle-tested than `scipy.optimize.least_squares` | Keep LM implementation small and well-tested; document that SciPy adoption is a future upgrade |
| **Angles-only orbit determination is ill-conditioned** | Poor initial guesses may not converge; short arcs leave some state components (notably along-track velocity) weakly constrained | Baseline explicitly requires a user-supplied plausible guess; report covariance as `None` when `JᵀJ` is singular; document non-convergence clearly |
| **Backward propagation not supported** | Cannot place `t0` inside the observation arc | Baseline fixes `t0 = 0 <= min_i t_i` (forward only); backward propagation is a future extension requiring changes to `dynamics.py` validation |
| **Pole singularity** | RA tangent-plane residual vanishes near `dec = ±90°`; residual-vector dimension must stay fixed | Pre-screen and flag geometrically degenerate observations before optimization; never drop RA components during iterations; synthetic arcs are far from poles |
| **Reference frame simplification** | Planets circular/coplanar, no light-time/aberration; real asteroid orbits differ | Matches existing C1/C2 model; estimator is consistent with the forward model that generated the data |
| **No autonomous initial-guess generation** | Estimator cannot discover an orbit from observations alone | Explicitly out of Phase 3 scope; future phase |

---

## 10. Explicit acceptance criteria

The following must all hold before Phase 3 implementation is considered complete:

1. **Design reviewed and approved** — this document signed off; no estimator code written before approval.
2. **No production source modified** — `src/orbit_discovery/component3/{dynamics,observation_model,loader,models}.py` and all C1/C2 files unchanged; no new dependencies added; `pyproject.toml`/`requirements*.txt` unchanged.
3. **Truth separation preserved** — production estimator modules contain no reference to `ground_truth`, `true_*`, or true-trajectory interpolation (verified by test).
4. **Residuals correct** — RA wraparound handled; cos(dec) applied exactly once to the residual (matching the single cos(dec) in `sigma_ra_cosdec_arcsec`); arcsec conversion correct; pole guard present.
5. **Baseline estimator works** — `estimate_orbit(user_supplied_initial_state, dataset)` returns an `EstimationResult` with populated `OrbitState`, `BestFitResult` (residuals, fit_metrics incl. chi2, n_iter, nfev, converged), and `OrbitCandidate`.
6. **Reduced chi-square only when valid** — `chi2_reduced` reported only when dof = (number of valid scalar residuals) − (effective parameter rank) > 0; otherwise absent / `None`. It is not automatically `2N − 6`.
7. **Covariance only when justified** — the unscaled covariance `cov_phys = (J_physᵀ J_phys)⁻¹` is reported when `J_phys` has full column rank, `J_physᵀ J_phys` is numerically well conditioned, and `J_phys` is evaluated at the converged solution. Positive degrees of freedom are **not** required for this unscaled covariance when absolute measurement uncertainties are known. Covariance is in physical state units (AU and AU/year).
8. **Validation passes** — synthetic recovery from a perturbed initial guess converges; chi2_reduced ≈ 1 at correct noise; failure cases report non-convergence; RA wraparound case passes.
9. **No regressions** — existing full test suite passes (C1, C2, C3 Phase 1 & 2).
10. **Scope maintained** — no autonomous initial-guess generation / multi-start orbit discovery in Phase 3; that is deferred to a later phase.

---

### Summary

Component 3 Phase 3 delivers the first working orbit estimator: a NumPy-only, Levenberg–Marquardt weighted nonlinear least-squares fit that takes a user-supplied initial `OrbitState` (AU, AU/year, heliocentric ecliptic inertial, reference epoch t=0) and an `ObservationDataset` of noisy RA/Dec, propagates the trial state through the existing C3 REBOUND/IAS15 forward model, predicts apparent coordinates via the existing C3 observation model, and minimizes the chi-square built from wrapped RA residuals and Dec residuals weighted by `sigma_ra_cosdec_arcsec` / `sigma_dec_arcsec` (with cos(dec) applied exactly once, in tangent-plane arcsec units). Results are assembled into the existing `BestFitResult` / `EstimationResult` models via their `residuals` and `fit_metrics` dicts — no model changes. SciPy is unavailable and no new dependencies are permitted, so the optimizer is hand-rolled. The baseline fits a supplied guess; autonomous initial-guess generation is explicitly deferred. Validation uses synthetic observations from known orbits in a separate test path, with ground truth never accessed by production code.

This is **design and investigation only**: no estimator code is written, no existing source or test is modified, and no Phase 3B work begins until this design is reviewed and approved.