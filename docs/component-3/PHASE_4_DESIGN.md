# Component 3 — Phase 4: Multiple Candidate Orbit Generation

**Status:** Awaiting Final Technical Review and Implementation Approval  
**Scope:** Design specification only. No implementation authorized.  
**Dependencies:** Component 3 Phases 0–3D  
**Next phase:** Phase 5 — Uncertainty and Diagnostics (not included in this phase)

---

## 1. Objective

Phase 4 extends the single best-fit orbit estimator from Phase 3D into a reproducible multi-start candidate-generation system.

The system will:

1. Use the existing Phase 3D best-fit orbit as the baseline candidate (Start 0).
2. Generate additional initial orbit states through seeded Gaussian perturbations.
3. Refine each perturbed state using the existing Phase 3D estimator.
4. Validate the resulting candidates using numerical, convergence, Jacobian-rank, degrees-of-freedom, and fit-quality checks.
5. Rank eligible candidates deterministically.
6. Remove duplicate solutions while retaining distinct plausible solutions.
7. Apply a configurable candidate-retention limit, identifying "truncated" candidates.
8. Produce a complete audit record for every attempted start, returned alongside the estimation result.

The objective is to explore the local solution space around the Phase 3D solution. This is not a guarantee of finding every possible orbit solution or the global optimum.

### Design principles

- Reuse the Phase 3D estimator and optimizer.
- Do not introduce new third-party dependencies.
- Use deterministic random-number generation (`numpy.random.default_rng`).
- Execute starts sequentially in this initial implementation.
- Keep production estimation independent of ground truth.
- Preserve candidate states at the established reference epoch (`t=0`).
- Keep the Phase 4 implementation isolated from Component 4 and Component 5.

---

## 2. Existing Interfaces and Architecture

Phase 4 will reuse the following Component 3 interfaces.

| Interface | Role |
|---|---|
| `OrbitState` | Six-dimensional Cartesian orbit state |
| `ObservationDataset` | Observation-only dataset and associated metadata |
| `BestFitResult` | Phase 3D best-fit state, residuals, and fit metrics |
| `EstimationResult` | Phase 3D estimation result containing candidates, best fit, and source metadata |
| `run_estimation(...)` | Runs the existing single-start estimation workflow |
| `least_squares_lm(...)` | Existing NumPy-only Levenberg–Marquardt optimizer |
| `propagate_trial_state(...)` | Propagates a trial orbit |
| `compute_residuals(...)` | Computes observation residuals |

### Existing state convention

Each orbit state is:

\[
\mathbf{x} =
\begin{bmatrix}
r_x & r_y & r_z & v_x & v_y & v_z
\end{bmatrix}^{T}
\]

| Quantity | Convention |
|---|---|
| Position | AU |
| Velocity | AU/year |
| Time | Years |
| Reference epoch | \(t=0.0\) years |
| Coordinate frame | Heliocentric ecliptic inertial |
| State dimension | 6 |

### Interface modification policy

The Phase 4 implementation will make a minimal extension to `estimation.py` to expose the final scaled Jacobian (`jac_scaled`) and valid scalar residual count. It must not modify `optimizer.py`, `dynamics.py`, `residuals.py`, `observation_model.py`, or `models.py`.

---

## 3. Configuration Schema

Configuration will be supplied under `phase_4_candidates`.

```json
{
  "phase_4_candidates": {
    "num_starts": 100,
    "random_seed": 42,
    "position_perturbation_scales": [0.01, 0.01, 0.01],
    "velocity_perturbation_scales": [1e-4, 1e-4, 1e-4],
    "duplicate_tolerance_pos": 0.005,
    "duplicate_tolerance_vel": 5e-5,
    "fit_quality_threshold_reduced_chi2": 5.0,
    "max_retained_candidates": 10
  }
}
```

### 3.1 Configuration validation

Validation must occur before generating any starts.

- `num_starts` and `max_retained_candidates` must be integers \(\ge 1\).
- `random_seed` must be a non-negative integer.
- Reject booleans for integer/float fields; reject fractional values for integers.
- Both perturbation-scale arrays must contain exactly three finite, strictly positive values.
- Duplicate tolerances and reduced-chi-square threshold must be finite and strictly positive.
- Reject NaN, infinity, zero, or negative values where positive finite values are expected.

---

## 4. Algorithm and Execution Sequence

### 4.1 Input

The public entry point `run_multi_start_estimation()` receives:
1. The existing Phase 3D `EstimationResult`.
2. The `ObservationDataset` used for estimation.
3. The Phase 4 configuration.

### 4.2 Start generation

Start 0 is the baseline preservation start:
\[
\mathbf{x}^{(0)} = \text{phase3\_result.best\_fit.state}
\]
It uses the existing Phase 3D result directly. **It must not be re-optimized.**

For starts \(k=1,\ldots,K-1\), generate:
\[
\mathbf{x}^{(k)} = \mathbf{x}^{(0)} + \boldsymbol{\delta}^{(k)}, \quad \boldsymbol{\delta}^{(k)} \sim \mathcal{N}(0,\Sigma)
\]
where \(\Sigma = \operatorname{diag}(\sigma_{rx}^2, \sigma_{ry}^2, \sigma_{rz}^2, \sigma_{vx}^2, \sigma_{vy}^2, \sigma_{vz}^2)\).

Use `rng = np.random.default_rng(random_seed)` created once. All \(K-1\) starts are generated before estimation begins to ensure deterministic ordering.

### 4.3 Non-finite perturbations

Every generated initial state must be checked for finite values.

If a generated state contains NaN or infinity:
- Do not pass it to `run_estimation`.
- Record the start as `failed`.
- Use reason `non_finite_initial_state`.
- Continue with the remaining starts.

Do not regenerate a replacement perturbation for that start. This preserves the one-generated-start/one-audit-record relationship.

### 4.4 Estimation loop

Starts are processed sequentially.
- **Start 0:** Construct an `OrbitCandidate` from the existing `phase3_result`. Apply validation and ranking (Section 6).
- **Starts 1..K-1:** Construct `OrbitState` and call `run_estimation(dataset, initial_state=...)`.
- **Error handling:** Catch `ValueError, RuntimeError, FloatingPointError, ArithmeticError, OverflowError`. Record as `failed`. Programming errors (e.g., `TypeError`) must propagate.

---

## 5. Jacobian Rank and Degrees of Freedom

### 5.1 Minimal extension to `estimation.py`

`run_estimation()` must expose the final scaled Jacobian (`jac_scaled`) from `least_squares_lm()` and the number of valid scalar residuals from `compute_residuals()`. It must calculate the SVD rank from the Jacobian and expose `jacobian_rank` and `n_valid_scalar_residuals` in `BestFitResult.fit_metrics`. It must not expose the raw Jacobian in the public `fit_metrics` contract.

### 5.2 Jacobian rank calculation

For a valid scaled Jacobian \(J_{\text{scaled}}\):

1. Require `jac_scaled` to be a finite 2D NumPy array.
2. Require exactly six columns (one per fitted parameter).
3. Require its row count to equal `n_valid_scalar_residuals`.
4. Compute singular values \(s_i\) using SVD.
5. Validate that the singular-value array is nonempty and finite.
6. Use relative tolerance \(\tau = 10^{-8} \times s_{\max}\), where \(s_{\max}\) is the largest singular value.
7. Rank is \(\#\{s_i : s_i > \tau\}\).
8. A valid all-zero spectrum has rank zero.

If the Jacobian is missing, malformed, not finite, not 2D, not exactly six columns, row-count mismatch, or singular values are empty/invalid:
- Outcome: `rejected`
- Reason: `invalid_jacobian`
- `jacobian_rank = None`

### 5.3 Degrees of freedom (DOF)

\[
\nu = N_{\text{valid}} - \operatorname{rank}(J_{\text{scaled}})
\]

If rank is `None` or \(\nu \le 0\):
- `chi2_reduced = None`
- Reject the candidate (reason: `insufficient_degrees_of_freedom`).

If rank is available but `rank < 6`:
- Reject the candidate (reason: `rank_deficient`).

Only candidates with `rank == 6`, \(\nu > 0\), and positive integer `n_valid_scalar_residuals` proceed to fit-quality filtering.

### 5.4 Reduced chi-square

For candidates with full rank and positive degrees of freedom:

\[
\chi^2_{\nu} = \frac{\chi^2}{\nu}
\]

The configurable default quality threshold is:

\[
\chi^2_{\nu} < 5.0
\]

Strict inequality: a candidate exactly at the threshold is rejected.

No covariance estimation or reduced-chi-square variance rescaling is performed in Phase 4.

---

## 6. Candidate Validation

Every successfully returned fit must pass the following validation checks before ranking.

### 6.1 Required explicit fields

A candidate must provide:
- A six-component state with all components finite.
- Finite, non-negative `chi2`.
- Finite, non-negative `optimality`.
- A valid convergence boolean (`True` or `False`, not null; booleans are not integers).
- A valid Jacobian rank (integer \(\ge 0\), not `None`).
- A valid positive integer residual count (`n_valid_scalar_residuals > 0`).
- Positive degrees of freedom (`dof > 0`).
- Finite, non-negative reduced chi-square (`chi2_reduced`).

A missing or invalid required metric must never be replaced with an assumed value.

### 6.2 Validation rules table

| Check | Requirement | Rejection reason |
|---|---|---|
| State | Exactly 6 finite components | `non_finite_state` |
| Chi-square | Finite and \(\ge 0\) | `invalid_fit_metrics` |
| Optimality | Finite and \(\ge 0\) | `invalid_fit_metrics` |
| Convergence | Valid boolean (not integer), `True` | `non_converged` |
| Residual Count | Positive integer (not boolean) | `invalid_fit_metrics` |
| Jacobian rank | Finite integer, available | `invalid_jacobian` |
| Identifiability | Rank exactly six | `rank_deficient` |
| Degrees of freedom | \(\nu > 0\) | `insufficient_degrees_of_freedom` |
| Propagation | Final propagation/prediction succeeds | `propagation_error` |
| Fit quality | \(\chi^2_{\nu} < \text{threshold}\) | `high_reduced_chi2` |

### 6.3 Baseline validation and provenance

Start 0 uses the existing Phase 3D `EstimationResult`. Its required information must be obtained from:

| Required value | Source |
|---|---|
| Baseline state | `phase3_result.best_fit.state` |
| Reference epoch | `phase3_result.best_fit.epoch_years` |
| Convergence status | `phase3_result.candidates[0].metadata["converged"]` |
| Chi-square | `phase3_result.best_fit.fit_metrics["chi2"]` |
| Jacobian rank | `phase3_result.best_fit.fit_metrics["jacobian_rank"]` |
| Valid scalar residual count | `phase3_result.best_fit.fit_metrics["n_valid_scalar_residuals"]` |
| Reduced chi-square | Calculated by Phase 4 from chi-square and DOF |

The implementation must verify:
- `best_fit` exists.
- The baseline state exists and contains six finite values.
- The reference epoch equals exactly \(0.0\) years.
- `candidates` contains at least one baseline candidate.
- Its convergence metadata exists and is a valid boolean.
- All required fit metrics (including `jacobian_rank` and `n_valid_scalar_residuals`) exist and are valid.

Baseline metrics must have been produced by an updated `run_estimation()` contract providing `jacobian_rank` and `n_valid_scalar_residuals`. If baseline metadata is missing or invalid:
- Outcome: `rejected`
- Reason: `missing_baseline_metrics` (or more specific baseline validation reason).

Missing baseline metrics must cause rejection, **never** re-optimization or fabrication.

### 6.4 Numerical execution failure vs. scientific validation failure

- `failed`: Numerical execution did not produce a usable fit (e.g., expected exception during `run_estimation` such as `propagation_error`, non-finite initial state).
- `rejected`: A fit result was returned but failed scientific or numerical validation (e.g., non-convergence, rank deficiency, insufficient DOF, high reduced chi-square, non-finite metrics).

---

## 7. Ranking and Deduplication

### 7.1 Deterministic ranking

Only candidates that pass all validation checks are eligible for ranking.

Sort ascending by:
1. `chi2_reduced`
2. `chi2` (raw)
3. `start_index` (final deterministic tie-breaker)

### 7.2 Duplicate distance

Candidate states are compared at the same reference epoch and in the same coordinate frame.

For candidates \(i\) and \(j\), define:

\[
D_{ij} =
\sqrt{
\frac{\|\mathbf r_i - \mathbf r_j\|^2}{\epsilon_r^2}
+
\frac{\|\mathbf v_i - \mathbf v_j\|^2}{\epsilon_v^2}
}
\]

where:
- \(\mathbf r\) is the three-dimensional position vector \([r_x, r_y, r_z]\).
- \(\mathbf v\) is the three-dimensional velocity vector \([v_x, v_y, v_z]\).
- \(\epsilon_r\) is `duplicate_tolerance_pos` (AU).
- \(\epsilon_v\) is `duplicate_tolerance_vel` (AU/year).

Duplicate classification:
- \(D_{ij} < 1.0\): duplicate.
- \(D_{ij} == 1.0\): **not** a duplicate (distinct).
- \(D_{ij} > 1.0\): distinct.

### 7.3 Greedy deduplication

Algorithm:
1. Iterate through eligible candidates in ranking order.
2. Retain the first (best-ranked) candidate.
3. For each subsequent candidate \(C_i\), compare against every already-retained candidate \(C_j\).
4. If \(D_{ij} < 1.0\) for any retained \(C_j\), classify \(C_i\) as `duplicate`.
5. Set `duplicate_of` to the start index of the better-ranked retained candidate \(C_j\).
6. Otherwise, add \(C_i\) to the retained-candidate list.

The first occurrence in ranking order is always preferred.

### 7.4 Retention limit

Apply `max_retained_candidates` only after deduplication.

Candidates that pass validation, are not duplicates, but exceed the retention limit receive:
- Outcome: `truncated`
- Reason: `max_retained_candidates`

They must not be classified as `failed` or `rejected`.

---

## 8. Audit Log and Public Return Contract

### 8.1 Public return contract

```
estimation_result, audit_log = run_multi_start_estimation(
    phase3_result=phase3_result,
    dataset=dataset,
    config=config,
)
```

The first value is an `EstimationResult`. The second value is an ordered list of audit records, with exactly one record per attempted start \(k \in 0 \dots K-1\).

The audit log remains in memory in Phase 4. Persistent file output is outside this phase.

### 8.2 Audit record schema

Each record must contain:

| Field | Type | Description |
|---|---|---|
| `start_index` | int | Unique zero-based start index |
| `initial_state` | list[float] | Six-component initial state \([rx, ry, rz, vx, vy, vz]\) |
| `outcome` | str | Final outcome classification |
| `convergence_status` | bool \| null | Convergence result, or `null` if unavailable |
| `valid` | bool \| null | Whether scientific candidate validation passed |
| `fit_metrics` | dict \| null | Available fit and diagnostic metrics |
| `reason` | str \| null | Final outcome reason, or `null` |
| `duplicate_of` | int \| null | Start index of better-ranked retained candidate, or `null` |

`fit_metrics` must include `chi2`, `chi2_reduced`, `jacobian_rank`, `n_valid_scalar_residuals`, and `degrees_of_freedom` where applicable.

### 8.3 Audit lifecycle

Every start must receive exactly one final outcome.

| Outcome | Meaning |
|---|---|
| `failed` | Numerical execution did not produce a usable fit |
| `rejected` | Fit completed but failed scientific or numerical validation |
| `duplicate` | Candidate passed validation but duplicated a better-ranked retained candidate |
| `retained` | Candidate passed validation and deduplication and was kept |
| `truncated` | Candidate passed validation and deduplication but exceeded retention limit |

Representative reasons:
- `failed`: `non_finite_initial_state`, `estimation_error`
- `rejected`: `missing_baseline_metrics`, `non_finite_state`, `non_converged`, `invalid_jacobian`, `rank_deficient`, `insufficient_degrees_of_freedom`, `high_reduced_chi2`, `propagation_error`
- `duplicate`: `duplicate_candidate`
- `truncated`: `max_retained_candidates`
- `retained`: `null`

The audit outcome must be finalized only after ranking, deduplication, and retention are complete.

### 8.4 Serialization

The audit records must be JSON-compatible with strict serialization:
- Convert NumPy scalar values to native Python scalars.
- Convert NumPy arrays to ordinary lists.
- Use JSON `null` for unavailable, undefined, or non-finite values.
- Never serialize NaN or Infinity as non-standard JSON tokens.
- Strict `json.dumps(..., allow_nan=False)` must succeed.
- Records remain ordered by `start_index`.

---

## 9. Candidate Metadata and Component 4 Handoff

### 9.1 Required candidate metadata

Each retained `OrbitCandidate.metadata` must include:

| Metadata key | Meaning |
|---|---|
| `start_index` | Original multi-start index |
| `converged` | Optimizer convergence status |
| `valid` | Candidate validation status |
| `chi2` | Raw chi-square |
| `chi2_reduced` | Reduced chi-square |
| `jacobian_rank` | Final numerical Jacobian rank |
| `n_valid_scalar_residuals` | Number of valid scalar residuals |
| `degrees_of_freedom` | Residual count minus Jacobian rank |
| `epoch_years` | Candidate reference epoch |
| `coordinate_frame` | Heliocentric ecliptic inertial |
| `position_unit` | AU |
| `velocity_unit` | AU/year |
| `time_unit` | Years |
| `model_configuration` | Reproducible dynamical-model configuration |

### 9.2 Dynamical model metadata

The `model_configuration` must explicitly describe:

- Sun plus planetary perturbations.
- Massless asteroid test particle.
- Gravitational parameter \(39.476926421373\) AU³/year².
- IAS15 integrator with epsilon \(10^{-12}\).
- Reference to C1 `BODY_DATA` for planetary configuration.
- Reference epoch \(0.0\) years, heliocentric ecliptic inertial frame.
- Position unit AU, velocity unit AU/year.

### 9.3 EstimationResult semantics

- `EstimationResult.best_fit` preserves the original Phase 3D `BestFitResult` for provenance. It must not be replaced by the best Phase 4 candidate.
- `EstimationResult.candidates` contains retained Phase 4 candidates in deterministic ranking order.
- `candidates[0]` represents the best retained candidate.
- If no candidates survive validation, `candidates` is empty while `best_fit` remains the original Phase 3D result.

---

## 10. Ground-Truth Isolation

Phase 4 is a production candidate-generation workflow with mandatory restrictions:

- `candidates.py` must not import ground-truth modules.
- `candidates.py` must not open or read `ground_truth.json`.
- Phase 4 must not inspect or use `true_*` fields.
- Candidate generation must use only observation data, model configuration, and the Phase 3D baseline result.
- Operational observation datasets and their metadata must contain only permitted observation and model information.

The existing dataset metadata contract must not be silently changed. If metadata sanitization is believed necessary, the proposed boundary and its impact must be documented and approved before modifying shared interfaces.

### Ground-truth isolation tests

Tests must demonstrate that candidate generation works when ground-truth files and modules are unavailable. Static checks are limited to `candidates.py` and `test_component3_candidates.py`. A metadata-only check is not sufficient to prove filesystem or module independence.

---

## 11. Implementation Scope

### New files

```text
src/orbit_discovery/component3/candidates.py
tests/test_component3_candidates.py
```

### Modified file

```text
src/orbit_discovery/component3/estimation.py
```

### Permitted changes to `estimation.py`

Only the following changes are authorized:

1. Expose `jacobian_rank` calculated from the final scaled Jacobian.
2. Expose `n_valid_scalar_residuals` from the final residual vector.
3. Preserve existing Phase 3D result structures and behavior.

No changes to `optimizer.py`, `dynamics.py`, `residuals.py`, `observation_model.py`, or `models.py` are permitted under this design.

### Module responsibilities

`candidates.py` will contain Phase 4 configuration validation, seeded initial-state generation, baseline extraction and validation, multi-start orchestration, candidate validation, reduced-chi-square calculation, candidate ranking, duplicate detection and greedy deduplication, retention-limit handling, audit-log construction and JSON-compatible conversion, and candidate model metadata construction.

---

## 12. Detailed Test Plan

### 12.1 Configuration tests
- Valid configuration accepted.
- Missing fields rejected.
- Invalid types rejected (booleans for integers, fractions for integers).
- Invalid perturbation-array lengths rejected.
- NaN and infinity rejected.
- Zero and negative scales or tolerances rejected.

### 12.2 Baseline tests
- Start 0 uses existing Phase 3D best-fit state.
- Start 0 does not call `run_estimation`.
- Start 0 has `start_index = 0`.
- Baseline metrics obtained from documented sources.
- Baseline metrics must be present (produced by updated `run_estimation`).
- Missing baseline candidate metadata rejected.
- Missing baseline fit metrics (including rank and residual count) rejected.
- Non-finite baseline state rejected.
- Baseline reference epoch other than \(0.0\) rejected.
- Original `BestFitResult` preserved in final `EstimationResult`.
- Never fabricate missing baseline metrics.

### 12.3 Perturbation and reproducibility tests
- Same seed and same baseline produce identical initial-state sequences.
- Different seeds produce different sequences in controlled test.
- Perturbations independent for all six state components.
- Position perturbations use AU scales; velocity perturbations use AU/year scales.
- Non-finite generated states not passed to estimator.
- Every generated start receives one audit record.

### 12.4 Estimation and exception tests
- Each non-baseline start invokes `run_estimation` once.
- Numerical exceptions recorded as failed starts.
- `TypeError` and programming errors propagate.
- Failed start does not prevent later starts.
- Sequential execution preserves start-index order in audit log.

### 12.5 Jacobian rank and degrees-of-freedom tests
- Valid six-column scaled Jacobian produces expected SVD rank.
- Relative tolerance exactly `1e-8 * largest_singular_value`.
- Invalid Jacobian dimensionality produces unavailable rank (`None`).
- Non-finite Jacobian produces unavailable rank.
- Missing Jacobian does not produce fabricated rank.
- Zero singular-value spectrum handled explicitly (rank zero).
- Dimension mismatch (row count != valid scalar residual count) rejected.
- Rank-deficient Jacobian rejected (`rank_deficient`).
- Non-positive degrees of freedom rejected (`insufficient_degrees_of_freedom`).
- Reduced chi-square calculated correctly for valid candidates.

### 12.6 Candidate validation tests
- Non-finite state rejected.
- Missing or non-finite metrics rejected.
- Non-converged candidate rejected.
- Final propagation/prediction failure rejected.
- Rank-deficient candidate rejected.
- Insufficient degrees of freedom rejected.
- Candidate above reduced-chi-square threshold rejected.
- Candidate exactly at threshold rejected.

### 12.7 Ranking tests
- Candidates sorted by reduced chi-square ascending.
- Raw chi-square breaks reduced-chi-square ties.
- Start index breaks remaining ties.
- Ranking deterministic across repeated runs.

### 12.8 Deduplication tests
- Identical states detected as duplicates (\(D_{ij} < 1.0\)).
- States with distance exactly \(1.0\) are **not** duplicates.
- States with distance \(> 1.0\) are distinct.
- Better-ranked candidate retained.
- Duplicate audit records contain correct `duplicate_of` index.
- Deduplication compares states at same epoch and frame.

### 12.9 Retention tests
- Retention limit applied after deduplication.
- Highest-ranked candidates retained.
- Candidates beyond limit receive `truncated`.
- Truncated candidates not classified as rejected or failed.
- Retention limit of one works correctly.

### 12.10 Audit-log tests
- Exactly one audit record per attempted start.
- Records ordered by start index.
- Every record has required fields including `n_valid_scalar_residuals` and `degrees_of_freedom`.
- Every record has exactly one final outcome.
- All five outcomes tested: `failed`, `rejected`, `duplicate`, `retained`, `truncated`.
- Undefined metrics serialize as JSON `null`.
- NumPy scalar and array values converted correctly.
- Strict JSON serialization succeeds with `allow_nan=False`.

### 12.11 Metadata and truth-isolation tests
- Retained candidates contain required model metadata.
- Candidate states use \(0.0\)-year reference epoch.
- C1 planetary configuration referenced rather than duplicated.
- No ground-truth files required for candidate generation.
- Candidate generation succeeds when ground-truth files/modules unavailable.
- New production module and test contain no ground-truth imports or file access.

### 12.12 Regression tests
Run:
```powershell
pytest tests/test_component3_candidates.py
pytest tests/test_component3_estimation.py
pytest tests/test_component3_optimizer.py
pytest tests/test_component3_residuals.py
pytest
```
All existing Component 3 tests and full repository test suite must pass. No existing tests deleted, weakened, or skipped.

---

## 13. Explicit Exclusions

Phase 4 does not include:
- Component 4 implementation.
- Phase 5 uncertainty estimation or diagnostics.
- Covariance calculation.
- Bayesian orbit estimation.
- Probabilistic confidence intervals.
- Global optimization or guaranteed discovery of all possible orbit solutions.
- Parallel or distributed candidate execution.
- Persistent audit-log storage.
- New external dependencies.
- Changes to observation-generation component.
- Changes to ground-truth evaluation workflow.
- Changes to optimizer unless separately justified and approved.

---

## 14. Scientific Limitations

1. **Local search:** Perturbations around the Phase 3D solution explore a local neighborhood only. They do not guarantee discovery of distant solution families.
2. **Empirical perturbation scales:** Position and velocity perturbation scales are configurable exploration parameters, not statistically derived uncertainty estimates.
3. **Fit-quality threshold:** The reduced-chi-square threshold is a configurable screening criterion, not by itself a complete statistical goodness-of-fit test.
4. **Numerical rank:** SVD rank depends on scaling and selected relative tolerance; the chosen threshold must be documented and kept consistent.
5. **Duplicate tolerances:** Duplicate detection based on normalized Cartesian state distance does not establish physical identity at every future epoch.
6. **No probabilistic completeness:** The retained candidate ensemble is not a posterior distribution and must not be interpreted as a statistically complete representation of orbital uncertainty.
7. **Model dependence:** Candidate quality depends on the existing dynamical model, observation model, and measurement uncertainties.

---

## 15. Phase 4 Exit Criteria

Phase 4 is complete only when:

- Multi-start execution is reproducible.
- The baseline is reused without re-optimization.
- All non-baseline starts use the existing Phase 3D estimator.
- Invalid candidates are rejected with explicit reasons.
- Jacobian rank and degrees of freedom are validated.
- Reduced-chi-square filtering works correctly.
- Candidate ranking is deterministic.
- Duplicate removal retains the better-ranked candidate.
- Distinct plausible candidates are not accidentally collapsed by the configured duplicate metric.
- The retention limit is applied after deduplication.
- Every attempted start has exactly one audit outcome.
- Candidate metadata is sufficient for the planned Component 4 handoff.
- Ground-truth isolation is demonstrated.
- All focused and full regression tests pass.

**Implementation status: Not authorized.**

This document defines the proposed Phase 4 design. Implementation may begin only after the design has been reviewed and explicitly approved.