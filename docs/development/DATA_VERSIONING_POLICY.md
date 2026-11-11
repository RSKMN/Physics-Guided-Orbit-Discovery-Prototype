# Data and Results Versioning Policy

**Project:** Physics-Guided Orbit Discovery Prototype  
**Version:** 0.2.0 baseline  
**Status:** Policy for the first Git publication; no datasets were deleted, moved or regenerated.

## 1. Purpose

This policy defines what belongs in Git for the 0.2.0 baseline and what should be regenerated or stored externally. It exists because the previous `.gitignore` excluded **all** `*.json` and `*.csv` files. That rule would have hidden the scientific configurations, observation tables, metadata and validation evidence that make the prototype reproducible.

The policy is deliberately conservative: generated files are classified only after inspection. A file is not excluded merely because it is generated.

## 2. Principles

1. **Configurations are source.** The six JSON files in `configs/` define the experiments and are tracked.
2. **Data and metadata travel together.** A trajectory or observation table should not be committed without its `metadata.json` and the corresponding configuration copy where one exists.
3. **Reference data is tracked.** Small tables used to reproduce the documented baseline are committed.
4. **Validation evidence is tracked where practical.** Summary CSVs, validation reports and the small repeatability/tolerance runs are committed.
5. **Generated figures are not tracked.** PNG/PDF figures can be recreated from tracked tables and are excluded by path-specific ignore rules.
6. **No global CSV/JSON ignore rules.** Future formats must be handled with explicit path rules, not broad extensions.
7. **Large or sensitive data stays outside the repository.** Git LFS or external storage is used only when the thresholds in §6 are met.
8. **No silent regeneration.** Rebuilding a tracked reference dataset is a deliberate change that should be reviewed and recorded in the changelog.

## 3. Current snapshot

Measured from the repository before staging:

| Area | Files | Size |
|---|---:|---:|
| `configs/` | 6 | 5,594 bytes |
| `data/` | 43 | 2,133,209 bytes |
| `results/` | 11 | 1,912,068 bytes |
| `plots/` | 5 | 337,443 bytes |
| **Total inspected** | **65** | **4,388,314 bytes** |

The total above covers `configs/`, `data/`, `results/` and `plots/`. The separate `tests/validation_report.md` is counted in class B and is not included in this 65-file total.

The largest single file is `results/component-2/figures/time_colored_sky_tracks.png` at 576,947 bytes (about 0.55 MiB). No file currently requires Git LFS.

## 4. Classification

### A. Essential reference data — commit

These files are required to inspect, validate or reproduce the documented Component 1–2 baseline.

| Path or group | Files | Size | Reason |
|---|---:|---:|---|
| `configs/*.json` | 6 | 5,594 B | Scientific experiment definitions; must never be ignored |
| `data/runs/<run>/trajectory.csv` | 3 | 343,652 B | Reference trajectories consumed by Component 2 |
| `data/runs/<run>/config.json` | 3 | 2,604 B | Exact configuration copy for each run |
| `data/runs/<run>/metadata.json` | 3 | 3,353 B | Frame, units, integrator, body list and run provenance |
| `data/observations/<dataset>/observations.csv` | 3 | 85,946 B | Reference synthetic measurements |
| `data/observations/<dataset>/metadata.json` | 3 | 5,070 B | Observer, schedule, noise and coordinate metadata |
| `data/trajectory_two_body.csv` | 1 | 123,027 B | Legacy two-body reference trajectory |
| `data/trajectory_nbody_synthetic.csv` | 1 | 123,062 B | Legacy synthetic N-body reference |
| `data/trajectory_nbody_eros.csv` | 1 | 155,152 B | Legacy Eros/Horizons reference trajectory |
| `results/component-2/comparison_summary.csv` | 1 | 696 B | Compact cross-scenario comparison table |
| **A total** | **25** | **848,156 B** | |

**Decision:** commit all A files. They are small, text-based and necessary to understand the baseline without rerunning the simulator.

### B. Important validation artefacts — commit

These files document numerical checks, repeatability or tolerance sensitivity. They are regenerable in principle, but they are useful evidence for the 0.2.0 baseline and are small enough to track.

| Path or group | Files | Size | Reason |
|---|---:|---:|---|
| `data/eros_diagnostics.csv` | 1 | 2,760 B | Eros/Horizons diagnostic evidence |
| `data/eros_horizons_validation.csv` | 1 | 341 B | Five-planet validation summary |
| `data/eros_horizons_8planets_validation.csv` | 1 | 362 B | Eight-planet validation summary |
| `data/repeatability/run_a|run_b/` | 6 | 211,412 B | Repeatability trajectories, configs and metadata |
| `data/tolerance_tests/` | 10 | 317,337 B | IAS15 tolerance runs and summary |
| `tests/validation_report.md` | 1 | 1,023 B | Captured baseline validation result |
| **B total** | **20** | **533,235 B** | |

**Decision:** commit all B files. They preserve the validation narrative and are well below the size thresholds for external storage.

### C. Regenerable outputs — exclude

These files are plots or derived figures produced by tracked code and data. The tables and metadata needed to regenerate them remain tracked.

| Path or group | Files | Size | Disposition |
|---|---:|---:|---|
| `data/runs/<run>/trajectory_xy.png` | 3 | 241,707 B | Exclude; regenerate with Component 1 |
| `data/runs/<run>/trajectory_3d.png` | 3 | 517,424 B | Exclude; regenerate with Component 1 |
| `results/component-2/figures/*.png` | 5 | 1,769,837 B | Exclude; regenerate with the comparison script |
| `results/component-2/figures/*.pdf` | 5 | 141,535 B | Exclude; regenerate with the comparison script |
| `plots/*.png` | 5 | 337,443 B | Exclude; legacy generated figures |
| **C total** | **21** | **3,007,946 B** | |

**Decision:** exclude all C files through path-specific `.gitignore` rules. Keep the generating code and the tracked CSV/JSON inputs so the figures remain reproducible.

### D. Large files — no current entries

No current file exceeds 1 MiB. There is no need for Git LFS in the 0.2.0 baseline.

**Future threshold (proposal):**

- Single file over **10 MiB**: evaluate Git LFS.
- Single file over **50 MiB** or a large binary ensemble: use external storage and record a persistent identifier or retrieval instructions.
- Any data that cannot be public: keep out of Git and document access conditions.

These thresholds are policy guidance, not an automatic rule. A large file that is essential to the scientific claim may still justify LFS.

## 5. `.gitignore` policy

The baseline `.gitignore` uses path-specific exclusions:

- `data/runs/*/*.png` — generated simulation figures;
- `results/component-2/figures/` — generated comparison figures;
- `plots/` — legacy generated figures;
- `artifacts/` — future generated outputs;
- `.venv/`, Python caches, build products, logs, local secrets and OS/IDE files.

It deliberately does **not** contain global `*.json` or `*.csv` rules. Scientific configurations, metadata, trajectories, observations and validation CSVs remain trackable.

**Do not add broad extension rules** such as `*.csv`, `*.json`, `data/`, `results/` or `*.png`. Add a path-specific rule and document why the file is regenerable.

## 6. What must accompany committed data

For every new reference dataset:

1. commit the table(s);
2. commit the generating configuration;
3. commit the metadata or manifest;
4. record the code version or revision;
5. record the random seed and dependency environment;
6. state whether the dataset is a reference baseline or a disposable experiment.

A table without metadata is not a stable scientific artefact.

## 7. Reproducibility notes for 0.2.0

- Component 1 writes `config.json`, `metadata.json` and `trajectory.csv` under `data/runs/<simulation_name>/`.
- Component 2 writes `observations.csv` and `metadata.json` under `data/observations/<observation_name>/`.
- The three observation configurations use `random_seed: 42`, so rerunning with the same inputs should reproduce the same measurements.
- Observation times are elapsed simulation days, not calendar epochs.
- No `schema_version` is present in the current CSV or metadata files.
- No absolute `epoch_jd_tdb` is present in the synthetic runs.
- The current observation CSV contains `true_ra_deg` and `true_dec_deg`; this is a known truth-separation limitation, not a reason to exclude the data.

## 8. Audit commands

These commands are read-only and are useful before a commit:

```powershell
git status --short
git check-ignore -v data\runs\synthetic_asteroid\trajectory.csv
git check-ignore -v results\component-2\figures\sky_track.png
git ls-files configs data results
```

Expected behaviour:

- the trajectory CSV is **not** ignored;
- the generated figure **is** ignored;
- all six configs appear in the staged file list;
- `data/` and `results/` contain only the A/B classes after staging.

## 9. Change control

If a future dataset replaces a 0.2.0 reference:

- do not overwrite the baseline silently;
- create a new versioned directory or filename;
- update this policy and the baseline manifest;
- record the change and its scientific reason in `CHANGELOG.md`;
- keep the old baseline if it is needed to reproduce published figures.

## 10. Non-goals

This policy does not:

- delete, move or regenerate any existing dataset;
- declare generated figures unimportant;
- authorise a commit or push;
- define the final long-term data architecture (see `REFACTORING_PLAN.md`);
- replace a formal data-management plan required by an institution or journal.
