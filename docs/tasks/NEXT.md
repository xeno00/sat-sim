MODE: PLAN_ONLY

This task may be executed via `RUN_CODEX.md`. Do not edit files unless the
human explicitly approves implementation. Do not merge unless explicitly
allowed.

# Next Task: Plan Human CRLB Figure Decision From Candidate Data

## Purpose

Use the merged non-final CRLB figure-candidate data to prepare a human decision
plan for CRLB figure handling. This is still not a figure-generation task.

## Context

The package now produces non-final JSON data for:

- rank-feasibility heatmap matrices;
- finite CRLB-vs-`N_s` series with unavailable masks;
- fixed-parameter measurement-addition series.

The data are under `v24_diagnostics/` and are not manuscript figures.

## Scope

Allowed files to inspect:

- `v24_diagnostics/crlb_figure_candidate_data.json`
- `v24_diagnostics/manuscript_crlb_candidate.json`
- `v24_diagnostics/crlb_geometry_diagnostics.json`
- `scripts/prepare_v24_crlb_figure_candidate.py`
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
- package source files
- tests

## Planning Questions

1. Which CRLB figure concept should be proposed to the human team first?
2. Which current manuscript CRLB figure(s) would each concept replace or
   supplement?
3. What exact caveats must accompany any CRLB-vs-`N_s` presentation?
4. What non-final plotting/data-preview task, if any, should be approved next?
5. What manuscript or response-letter changes would be needed if the CRLB
   figure concept changes?

## Required Output

Return:

- PASS / PASS WITH CAVEAT / FAIL for using the current candidate data as
  decision input;
- recommended figure decision path;
- human-review questions;
- exact next implementation task if preview plotting is approved;
- files that task may edit;
- stop gates;
- confirmation no files were edited.

## Hard Constraints

- Do not run notebook code.
- Do not generate figures.
- Do not run full sweeps.
- Do not edit manuscript, response-letter, bibliography, figure, PSFrag,
  generated PDF, notebook, package source, test, or result files.

