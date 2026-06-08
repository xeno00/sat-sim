MODE: REVIEW_DIFF

# Next Task: Review C7 Residual-Covariance Sync-Safeguard Estimator

## Purpose

Review branch `codex/step-c7-residual-cov-sync-safeguard` before merge. Do not
edit files, do not run notebook code, do not run broad exploration, do not run
full ladders, do not generate manuscript figures, and do not update manuscript
claims.

## Scope

Inspect:

- `jcls_sim/algorithm.py`
- `jcls_sim/migration.py`
- `jcls_sim/figure_generation.py`
- `scripts/run_step_c7_residual_cov_sync_safeguard.py`
- `scripts/run_controlled_migration_ladder.py`
- `scripts/render_all_figure_previews.py`
- `tests/test_step_c7_residual_cov_sync_safeguard.py`
- `outputs/step_c7_residual_cov_sync_safeguard/`
- `outputs/reports/STEP_C7_TASK_MATRIX.md`
- `outputs/reports/STEP_C7_TASK_MATRIX.json`
- `outputs/reports/STEP_C7_RESIDUAL_COV_SYNC_SAFEGUARD_REPORT.md`
- `outputs/reports/STEP_C7_RESIDUAL_COV_SYNC_SAFEGUARD_REPORT.json`
- C7 entries under `outputs/gallery/`
- `PROJECT_STATUS.md`

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

1. Confirm C7 is implemented as a real package estimator mode, not only as an
   audit/report-layer diagnostic.
2. Confirm `step_c7_residual_cov_sync_safeguard` is registered as its own
   migration estimator mode and cannot silently fall through to copied legacy
   rows.
3. Confirm residual-scaled covariance uses
   `sigma_hat^2 pinv(J.T R^-1 J + lambda I)` with
   `sigma_hat^2 = r.T R^-1 r / max(1, N_z - N_theta)`.
4. Confirm covariance is block-diagonalized/diagonal-clipped with position,
   UE-clock, satellite-clock, and drift blocks.
5. Confirm the synchronization safeguard uses only non-truth diagnostics.
6. Confirm single-UE clock/drift fallback records
   `single_user_clock_update_not_observable` and reverts unsafe clock/drift
   updates to Step B.
7. Confirm truth-state errors are used only for offline metric labels/ratios.
8. Confirm medium validation reproduces the reviewed audit-level behavior:
   9/12 both improved, 12/12 position improved, 9/12 sync improved, max sync
   ratio 1.0, fallback count 3.
9. Confirm ablation outputs are clearly non-final and not manuscript-ready.
10. Confirm gallery previews include the C7 plots.
11. Confirm reports are human-readable and include direct output links.
12. Confirm focused and full tests pass.

Run:

```powershell
python -m unittest tests.test_step3_residual_covariance_audit
python -m unittest tests.test_step_c7_residual_cov_sync_safeguard
powershell -NoProfile -ExecutionPolicy Bypass -File '..\scripts\test_sat_sim.ps1'
```

## Expected Output

Return:

- PASS / FAIL / PASS WITH CAVEAT;
- merge recommendation;
- required fixes before merge, if any;
- C7 medium-validation summary;
- ablation summary;
- fallback count/reasons;
- no-truth-leak verdict;
- whether Step B/LM-only remains the clean baseline pending human graph review;
- next recommended action after merge.
