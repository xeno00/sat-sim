MODE: REVIEW_DIFF

# Next Task: Review Step 3 Covariance/Dynamics Exploration

## Purpose

Review branch `codex/step3-covariance-exploration` before merge. Do not edit
files, do not run notebook code, do not run full ladders, do not run
network-size graphs, and do not generate manuscript figures.

## Scope

Inspect:

- `scripts/explore_step3_covariance.py`
- `scripts/render_all_figure_previews.py`
- `tests/test_step3_covariance_exploration.py`
- `outputs/step3_covariance_exploration/`
- `outputs/reports/STEP3_COVARIANCE_EXPLORATION_TASK_MATRIX.md`
- `outputs/reports/STEP3_COVARIANCE_EXPLORATION_TASK_MATRIX.json`
- `outputs/reports/STEP3_COVARIANCE_EXPLORATION_REPORT.md`
- `outputs/reports/STEP3_COVARIANCE_EXPLORATION_REPORT.json`
- Step 3 covariance exploration entries under `outputs/gallery/`
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

1. Confirm the branch stays code/diagnostic-only and does not touch notebook or
   manuscript artifacts.
2. Confirm default execution uses only sparse cases:
   `(N_u,N_s)=(3,8),(7,8),(7,12)`.
3. Confirm lane variants are bounded to 3--6 variants per lane and cover:
   LM curvature covariance, residual-scaled LM covariance,
   position-freeze/damping, block-scaled drift tuning, gauge/common-clock
   control, and Schur/reduced nuisance-clock updates.
4. Confirm default execution does not run medium validation, network-size
   graphs, full ladders, notebook code, or manuscript figure generation.
5. Confirm explicit medium validation includes only promoted variants and not
   all variants.
6. Confirm diagnostics include Step B and Step 3 position/sync errors, ratios,
   improvement flags, block update norms, covariance block statistics,
   objective components, accept/reject counts, truth-use flags, runtime, and
   cache keys.
7. Confirm no truth-state acceptance or truth-derived covariance is used.
8. Confirm report and metadata mark outputs non-final and not manuscript-ready.
9. Confirm gallery previews exist for the covariance exploration diagnostic
   plots.
10. Confirm focused and full tests pass.

Run:

```powershell
python -m unittest tests.test_step3_covariance_exploration
powershell -NoProfile -ExecutionPolicy Bypass -File '..\scripts\test_sat_sim.ps1'
```

## Expected Output

Return:

- PASS / FAIL / PASS WITH CAVEAT;
- merge recommendation;
- required fixes before merge, if any;
- subagent/fallback status;
- promoted variants and medium-validation result;
- best position, synchronization, and balanced variants;
- whether Step B/LM-only remains the current clean estimator baseline;
- next recommended action after merge.
