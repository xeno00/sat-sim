MODE: REVIEW_DIFF

# Next Task: Review Bounded C7 Candidate-Figure Validation

## Purpose

Review branch `codex/c7-candidate-figure-validation` before merge. Do not edit
files, do not run broad exploration, do not generate manuscript figures, do not
modify the C7 algorithm, and do not mark anything manuscript-ready.

## Scope

Inspect:

- `scripts/run_c7_candidate_figures.py`
- `scripts/render_all_figure_previews.py`
- `tests/test_c7_candidate_figures.py`
- `outputs/c7_candidate_figures/`
- `outputs/reports/C7_CANDIDATE_FIGURE_TASK_MATRIX.md`
- `outputs/reports/C7_CANDIDATE_FIGURE_TASK_MATRIX.json`
- `outputs/reports/C7_CANDIDATE_FIGURE_VALIDATION_REPORT.md`
- `outputs/reports/C7_CANDIDATE_FIGURE_VALIDATION_REPORT.json`
- C7 candidate entries under `outputs/gallery/`
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

1. Confirm the candidate generator is bounded and uses only Step B / LM-only and
   `step_c7_residual_cov_sync_safeguard`.
2. Confirm no broad algorithm exploration, full clock sweep, notebook execution,
   or manuscript-figure generation is performed.
3. Confirm all outputs are under `outputs/c7_candidate_figures/` and are marked
   non-final, candidate-only, not for manuscript submission, and not
   manuscript-ready.
4. Confirm the report uses the exact terminology:
   `typed block-extracted, diagonal-clipped residual-scaled covariance`.
5. Confirm synchronization plots use ns while raw CSV retains range-domain km.
6. Confirm network-size candidate data match the C7 medium-grid behavior:
   12/12 localization rows improve, 9/12 synchronization rows improve, 9/12
   rows improve both metrics, and fallback count is 3.
7. Confirm fallback rows are visible or explained, especially the single-UE
   rows with `single_user_clock_update_not_observable`.
8. Confirm sparse clock-sweep outputs are generated but explicitly blocked for
   candidate-figure use because high clock-standard-deviation rows worsen
   localization substantially.
9. Confirm truth is not used for acceptance, covariance, or safeguard decisions.
10. Confirm gallery previews exist for all six candidate plots.
11. Confirm Markdown reports are human-readable and use valid relative links.
12. Confirm focused tests pass.

Run:

```powershell
python -m unittest tests.test_c7_candidate_figures
```

Optionally run the full sat-sim suite only if practical and only if it does not
rewrite unrelated diagnostic outputs:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File '..\scripts\test_sat_sim.ps1'
```

## Expected Output

Return:

- PASS / FAIL / PASS WITH CAVEAT;
- merge recommendation;
- required fixes before merge, if any;
- network-size figure-family summary;
- sparse clock-sweep blocker summary;
- fallback count/reasons;
- no-truth-leak verdict;
- gallery/report verdict;
- tests run/results;
- whether outputs are ready for human graph review;
- whether outputs are ready for manuscript use;
- next recommended action after merge.
