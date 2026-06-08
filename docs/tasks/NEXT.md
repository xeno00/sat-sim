MODE: REVIEW_DIFF

# Next Task: Review Step 3 Near-Winner Sparse Exploration

## Purpose

Review branch `codex/step3-near-winner-sparse` before merge. Do not edit files,
do not run notebook code, do not run full ladders, do not run network-size
graphs, and do not generate manuscript figures.

## Scope

Inspect:

- `scripts/explore_step3_near_winner_sparse.py`
- `scripts/render_all_figure_previews.py`
- `tests/test_step3_near_winner_sparse.py`
- `outputs/step3_near_winner_sparse/`
- `outputs/reports/STEP3_NEAR_WINNER_SPARSE_REPORT.md`
- `outputs/reports/STEP3_NEAR_WINNER_SPARSE_REPORT.json`
- Step 3 near-winner sparse entries under `outputs/gallery/`
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
2. Confirm the runner defaults to the three sparse cases only:
   `(N_u,N_s)=(3,8),(7,8),(7,12)`.
3. Confirm the tested variants are restricted to the near-winner family:
   block-scaled drift variants, common-clock projection, blockwise clipping,
   strong/loose clock priors, no-drift projection, Schur/nuisance-clock
   reduction, and clock-only Step 3.
4. Confirm default execution does not run medium validation, network-size
   graphs, full ladders, notebook code, or manuscript figure generation.
5. Confirm the explicit promoted-only medium validation includes only promoted
   variants and not all variants.
6. Confirm diagnostics include Step B and Step 3 position/sync errors,
   ratios, improvement flags, objective decrease, update norms by block,
   common-clock/gauge component, Schur diagnostics, runtime, and cache status.
7. Confirm no truth-state acceptance or truth-derived covariance is used.
8. Confirm report and metadata mark outputs non-final and not manuscript-ready.
9. Confirm gallery previews exist for the sparse diagnostic plots.
10. Confirm focused and full tests pass.

Run:

```powershell
python -m unittest tests.test_step3_near_winner_sparse
powershell -NoProfile -ExecutionPolicy Bypass -File '..\scripts\test_sat_sim.ps1'
```

## Expected Output

Return:

- PASS / FAIL / PASS WITH CAVEAT;
- merge recommendation;
- required fixes before merge, if any;
- promoted variants and medium-validation result;
- best position, synchronization, and balanced variants;
- whether clock-only Step 3 is promising;
- whether Step B/LM-only remains the current clean estimator baseline;
- next recommended action after merge.
