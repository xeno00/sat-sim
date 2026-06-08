MODE: REVIEW_DIFF

# Next Task: Review Step C Diagnosis Before Merge

## Purpose

Review branch `codex/migration-step-c-diagnosis` before merge. This branch
starts from Step B and splits the degraded Step C MAP/EKF correction into
smaller C0/C1/C2/C3 sub-ablations.

## Scope

Inspect:

- `jcls_sim/migration.py`
- `scripts/run_controlled_migration_ladder.py`
- `scripts/build_legacy_graph_package.py`
- `tests/test_controlled_migration_ladder.py`
- `outputs/migration_ladder/step_c0_legacy_map_instrumented/`
- `outputs/migration_ladder/step_c1_legacy_cov_observable_acceptance/`
- `outputs/migration_ladder/step_c2_observable_cov_legacy_acceptance/`
- `outputs/migration_ladder/step_c3_cov_diag_prior/`
- `outputs/migration_ladder/step_c3_cov_block_diag/`
- `outputs/migration_ladder/step_c3_cov_damped_inverse/`
- `outputs/migration_ladder/step_c3_cov_damped_pinv/`
- `outputs/migration_ladder/step_c3_cov_residual_scaled/`
- `outputs/reports/STEP_C_DIAGNOSIS_REPORT.md`
- `outputs/reports/STEP_C_DIAGNOSIS_REPORT.json`
- `outputs/reports/CONTROLLED_MIGRATION_LADDER.md`
- `outputs/reports/CONTROLLED_MIGRATION_LADDER.json`
- `outputs/gallery/PLOT_GALLERY.md`
- `outputs/OUTPUT_INDEX.md`

Do not edit:

- `JCLS_Simulation.ipynb`
- manuscript files
- response-letter files
- bibliography files
- Work-In-Progress figure files
- PSFrag files
- generated manuscript PDFs
- existing manuscript result files

## Required Review Checks

1. Confirm C0 changes no behavior relative to Step B and only instruments
   legacy MAP/global fallback behavior.
2. Confirm C1 keeps legacy truth-derived MAP covariance and replaces only MAP
   acceptance/reversion with observable residual/covariance checks.
3. Confirm C2 replaces only MAP covariance and preserves legacy truth-gated MAP
   acceptance/reversion.
4. Confirm C3 candidates use non-truth covariance and observable acceptance.
5. Confirm all substeps preserve all-clock internals, legacy symbolic ordering,
   legacy IL/clockless preconditioning, Step B residual LM acceptance, legacy
   sync metric, geometry/noise settings, single-UE policy, and raw/display
   separation.
6. Confirm every output is non-final and not manuscript-ready.
7. Confirm `STEP_C_DIAGNOSIS_REPORT` identifies the breaking factor and that
   its conclusion is supported by C1/C2 statuses.
8. Confirm covariance diagnostics include trace/range/condition, update counts,
   residual costs, true-state usage flags, and fallback paths.
9. Confirm no manuscript, response-letter, bibliography, notebook, PSFrag,
   Work-In-Progress figure, generated manuscript PDF, or existing manuscript
   result files were edited.
10. Run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File '..\scripts\test_sat_sim.ps1'
```

## Expected Output

Return:

- PASS / FAIL / PASS WITH CAVEAT;
- merge recommendation;
- required fixes before merge, if any;
- whether Step C degradation is caused primarily by MAP acceptance replacement,
  covariance replacement, or both;
- whether any C3 non-truth covariance candidate is healthy;
- next recommended Step C replacement strategy.
