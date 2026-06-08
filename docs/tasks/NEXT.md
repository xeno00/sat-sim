MODE: REVIEW_DIFF

# Next Task: Review Low-Cost Step 3 Exploration

## Purpose

Review branch `codex/step3-low-cost-exploration` before merge. Do not edit
files, do not run live legacy exploration, and do not run medium validation
unless a precise bounded follow-up command is approved.

## Scope

Inspect:

- `scripts/explore_step3_low_cost.py`
- `scripts/render_all_figure_previews.py`
- `tests/test_step3_low_cost_exploration.py`
- `outputs/step3_low_cost_exploration/`
- `outputs/reports/STEP3_LOW_COST_EXPLORATION_REPORT.md`
- `outputs/reports/STEP3_LOW_COST_EXPLORATION_REPORT.json`
- `outputs/reports/STEP3_LOW_COST_EXPLORATION_TASK_MATRIX.md`
- `outputs/reports/STEP3_LOW_COST_EXPLORATION_TASK_MATRIX.json`
- Step 3 low-cost exploration entries under `outputs/gallery/`
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
2. Confirm the low-cost runner defaults to sparse/proxy diagnostics and does
   not run the full ladder or medium validation.
3. Confirm live legacy execution is opt-in via `--execute-legacy`.
4. Confirm reports clearly state that clock-drift and Schur/nuisance-clock
   lanes are proxy-only/inconclusive, not ruled out.
5. Confirm all rows include lane, method/config, case, cache key,
   position/sync ratios, improvement flags, and truth-state usage flags.
6. Confirm no row uses truth for acceptance or covariance.
7. Confirm no idea met promotion criteria and medium validation was not run.
8. Confirm gallery previews exist for the low-cost exploration plots.
9. Confirm focused and full tests pass.

Run:

```powershell
python -m unittest tests.test_step3_low_cost_exploration
powershell -NoProfile -ExecutionPolicy Bypass -File '..\scripts\test_sat_sim.ps1'
```

## Expected Output

Return:

- PASS / FAIL / PASS WITH CAVEAT;
- merge recommendation;
- required fixes before merge, if any;
- whether any idea is promising enough for medium validation;
- which lanes remain inconclusive;
- whether Step B/LM-only remains the current clean estimator baseline;
- next recommended action after merge.
