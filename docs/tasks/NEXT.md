MODE: REVIEW_DIFF

# Next Task: Review C7 Manuscript-Figure Recreation

## Purpose

Review branch `codex/c7-manuscript-figure-recreation` before merge. Do not edit
files, do not generate new outputs, do not run broad exploration, do not execute
the notebook, and do not mark anything manuscript-ready.

## Scope

Inspect:

- `scripts/run_c7_manuscript_figure_recreation.py`
- `scripts/render_all_figure_previews.py`
- `tests/test_c7_manuscript_figure_recreation.py`
- `outputs/c7_manuscript_figure_recreation/`
- `outputs/reports/C7_MANUSCRIPT_FIGURE_PROVENANCE_AUDIT.md`
- `outputs/reports/C7_MANUSCRIPT_FIGURE_PROVENANCE_AUDIT.json`
- `outputs/reports/C7_MANUSCRIPT_FIGURE_TASK_MATRIX.md`
- `outputs/reports/C7_MANUSCRIPT_FIGURE_TASK_MATRIX.json`
- `outputs/reports/C7_MANUSCRIPT_FIGURE_RECREATION_REPORT.md`
- `outputs/reports/C7_MANUSCRIPT_FIGURE_RECREATION_REPORT.json`
- C7 manuscript recreation entries under `outputs/gallery/`
- `outputs/reports/CURRENT_GRAPH_STATUS.md`
- `outputs/reports/CURRENT_GRAPH_STATUS.json`
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

1. Confirm the provenance audit inspected the original notebook/script figure
   generation path for Fig. 4--7 and did not rely on memory.
2. Confirm the runner is bounded and resumable, with dry-run/list-plan,
   row-level checkpoints, row status logs, cache manifests, row timeouts,
   runtime limits, `--only-family`, `--only-row`, and `--cache-root`.
3. Confirm no notebook execution, manuscript-file edits, final manuscript figure
   generation, broad algorithm exploration, or dense clock sweep was performed.
4. Confirm single-UE rows are not treated as cooperative JCLS curves.
5. Confirm Stage A, Stage B, and Stage C semantics are explicit and use:
   without-cooperation/DL-only/coarse baseline, Step B LM-only JCLS, and
   `step_c7_residual_cov_sync_safeguard`.
6. Confirm outputs are under `outputs/c7_manuscript_figure_recreation/` and are
   marked candidate-only, non-final, not for manuscript submission, and not
   manuscript-ready.
7. Confirm Fig. 4/5 network-size outputs are suitable for human review only.
8. Confirm Fig. 6/7 clock-sweep outputs are marked diagnostic/candidate-failed
   when high clock-standard-deviation rows worsen localization.
9. Confirm generated plots match manuscript style reasonably while avoiding
   misleading smoothing/fitting or overclaiming.
10. Confirm gallery previews exist for all four recreated candidate plots.
11. Confirm Markdown reports are human-readable and use valid relative links.
12. Confirm focused tests pass.

Run:

```powershell
python -m unittest tests.test_c7_manuscript_figure_recreation
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
- provenance-audit verdict;
- cache/resume/recovery verdict;
- Fig. 4/5 network-size verdict;
- Fig. 6/7 clock-sweep blocker summary;
- single-UE semantics verdict;
- no-truth-leak and no-notebook-execution verdict;
- gallery/report verdict;
- tests run/results;
- whether outputs are ready for human graph review;
- whether outputs are ready for manuscript use;
- next recommended action after merge.
