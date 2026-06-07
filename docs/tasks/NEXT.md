MODE: REVIEW_DIFF

This task may be executed via `RUN_CODEX.md`. Do not edit files unless the
human explicitly approves implementation. Do not merge unless explicitly
allowed.

# Next Task: Review CRLB Figure-Candidate Data Branch Before Merge

## Purpose

Review the branch implementing non-final CRLB figure-candidate data before
merge. Confirm it prepares JSON data only, masks unavailable/rank-deficient
points, and does not generate manuscript figures.

## Scope

Inspect:

- `scripts/prepare_v24_crlb_figure_candidate.py`
- `tests/test_crlb_figure_candidate.py`
- `v24_diagnostics/crlb_figure_candidate_data.json`
- `PROJECT_STATUS.md`
- `docs/tasks/NEXT.md`

Do not edit:

- `JCLS_Simulation.ipynb`
- manuscript files
- response-letter files
- bibliography files
- Work-In-Progress figure files
- PSFrag files
- generated manuscript PDFs
- generated figure PDFs/EPS/PNGs
- existing manuscript result files
- plotting code
- figure-generation code

## Checks

1. Output is explicitly non-final and says no figures were generated.
2. Rank-feasibility heatmap data include axes and full-rank/rank/nullity
   matrices.
3. Finite CRLB-vs-`N_s` series include unavailable masks and do not expose
   finite values for unavailable points.
4. Fixed-parameter measurement-addition data masks rank-deficient points.
5. No plotting or figure-generation code was introduced.
6. Run `powershell -NoProfile -ExecutionPolicy Bypass -File '.\scripts\test_sat_sim.ps1'`
   from the repository root.

## Required Output

Return:

- PASS / FAIL / PASS WITH CAVEAT;
- merge recommendation;
- required fixes before merge, if any;
- nonblocking caveats;
- confirmation that manuscript, response-letter, bibliography, figure, PSFrag,
  PDF, notebook, and final-result files were not edited.

