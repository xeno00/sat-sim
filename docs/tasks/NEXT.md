MODE: REVIEW_DIFF

# Next Task: Review Sparse Step 3 Gate Exploration

## Purpose

Review branch `codex/step3-gate-exploration` before merge. Do not edit files,
do not run additional gate experiments, and do not run medium validation unless
a precise bounded follow-up command is approved.

## Scope

Inspect:

- `scripts/explore_step3_gates.py`
- `scripts/render_all_figure_previews.py`
- `tests/test_step3_gate_exploration.py`
- `outputs/step3_gate_exploration/`
- `outputs/reports/STEP3_GATE_EXPLORATION_REPORT.md`
- `outputs/reports/STEP3_GATE_EXPLORATION_REPORT.json`
- Step 3 gate exploration entries under `outputs/gallery/`
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

1. Confirm the exploration is sparse only and uses representative cases
   `(N_u,N_s)=(3,8),(7,8),(7,12)`.
2. Confirm it does not run the full migration ladder or large grids by default.
3. Confirm the gate set includes NIS, line-search, nullspace, clock/position
   ratio, covariance/measurement inflation, and Huber residual weighting.
4. Confirm NIS, nullspace ratio, clock/position update ratio, chosen line-search
   alpha, objective history, and update diagnostics are recorded.
5. Confirm Step 3 acceptance does not use `scenario.get_true_state()`.
6. Confirm truth-state errors are used only for diagnostics/labels.
7. Confirm outputs are non-final, not manuscript-ready, and under
   `outputs/step3_gate_exploration/`.
8. Confirm the report states no gate improved both localization and
   synchronization across the sparse cases.
9. Confirm medium validation was not run.
10. Confirm gallery previews exist for the Step 3 exploration plots.
11. Confirm tests pass.

Run:

```powershell
python -m unittest tests.test_step3_gate_exploration
powershell -NoProfile -ExecutionPolicy Bypass -File '..\scripts\test_sat_sim.ps1'
```

## Expected Output

Return:

- PASS / FAIL / PASS WITH CAVEAT;
- merge recommendation;
- required fixes before merge, if any;
- whether any gate is promising enough for medium validation;
- whether Step B/LM-only remains the current clean estimator baseline;
- next recommended action after merge.
