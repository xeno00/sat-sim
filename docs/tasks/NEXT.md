MODE: REVIEW_DIFF

# Next Task: Review Step 3 Residual Covariance Audit

## Purpose

Review branch `codex/step3-residual-cov-audit` before merge. Do not edit
files, do not run notebook code, do not run full ladders, do not run broad
exploration, do not generate manuscript figures, and do not update manuscript
claims.

## Scope

Inspect:

- `scripts/audit_step3_residual_covariance.py`
- `tests/test_step3_residual_covariance_audit.py`
- `scripts/render_all_figure_previews.py`
- `outputs/step3_residual_cov_failure_audit/`
- `outputs/step3_residual_cov_robust_candidates/`
- `outputs/reports/STEP3_RESIDUAL_COV_FAILURE_AUDIT.md`
- `outputs/reports/STEP3_RESIDUAL_COV_FAILURE_AUDIT.json`
- `outputs/reports/STEP3_RESIDUAL_COV_ROBUST_CANDIDATE_REPORT.md`
- `outputs/reports/STEP3_RESIDUAL_COV_ROBUST_CANDIDATE_REPORT.json`
- Step 3 residual covariance entries under `outputs/gallery/`
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

1. Confirm the audit uses only the residual-scaled covariance family and does
   not rerun broad Step 3 lanes.
2. Confirm failure rows are correctly identified for sync/position worsening,
   objective decrease with metric worsening, and unusually large update norms.
3. Confirm block-diagonal and full residual-scaled covariance comparison is
   row-by-row and correctly reports whether off-diagonal cross-covariance is
   actually used.
4. Confirm robust C7 candidates are limited to:
   `residual_scaled_block_diag_base`,
   `residual_scaled_block_diag_with_sync_safeguard`,
   `residual_scaled_block_diag_clock_only_fallback`, and
   `residual_scaled_block_diag_position_damped`.
5. Confirm safeguards use only non-truth diagnostics and that truth-state
   metrics are used only for diagnostic labels.
6. Confirm fallback behavior is recorded for each candidate row.
7. Confirm candidate summaries include both-improved counts, position/sync
   improved counts, mean/max ratios, failure rows, and fallback counts.
8. Confirm gallery previews exist for audit and robust candidate plots.
9. Confirm outputs are non-final and not manuscript-ready.
10. Confirm focused and full tests pass.

Run:

```powershell
python -m unittest tests.test_step3_residual_covariance_audit
powershell -NoProfile -ExecutionPolicy Bypass -File '..\scripts\test_sat_sim.ps1'
```

## Expected Output

Return:

- PASS / FAIL / PASS WITH CAVEAT;
- merge recommendation;
- required fixes before merge, if any;
- failure-row summary;
- whether block-diagonal and full covariance differ;
- best robust candidate and max/mean ratios;
- whether Step B/LM-only remains the current clean estimator baseline;
- next recommended action after merge.
