MODE: PLAN_ONLY

This task may be executed via `RUN_CODEX.md`. Do not edit files unless the
human explicitly approves implementation. Do not generate manuscript figures.

# Next Task: Plan Human Decision From CRLB Preview Outputs

## Purpose

Use the merged non-final CRLB preview outputs to prepare a human decision plan
for CRLB figure handling. This is still not a manuscript-figure generation task.

## Context

The package now has non-final CRLB figure-candidate data and preview SVGs under
`v24_diagnostics/`. The previews are diagnostic aids only:

- rank-feasibility heatmap preview;
- finite CRLB-vs-`N_s` UE PEB preview with unavailable markers;
- finite CRLB-vs-`N_s` clock-bound preview with unavailable markers;
- fixed-parameter measurement-addition preview.

## Scope

Allowed files to inspect:

- `v24_diagnostics/crlb_preview/preview_manifest.json`
- `v24_diagnostics/crlb_preview/*.svg`
- `v24_diagnostics/crlb_figure_candidate_data.json`
- `v24_diagnostics/manuscript_crlb_candidate.json`
- `v24_diagnostics/crlb_geometry_diagnostics.json`
- `scripts/preview_v24_crlb_figure_candidates.py`
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
- generated manuscript figure PDFs/EPS/PNGs
- existing manuscript result files
- plotting code
- package source files
- tests

## Planning Questions

1. Which preview concept should be proposed to the human team first?
2. Which current manuscript CRLB figure(s) would each concept replace or
   supplement?
3. What exact caveats must accompany any CRLB-vs-`N_s` presentation?
4. What manuscript or response-letter changes would be needed if the CRLB
   figure concept changes?
5. What implementation task should be approved next if humans choose a
   non-final manuscript-style figure candidate?

## Required Output

Return:

- PASS / PASS WITH CAVEAT / FAIL for using the preview outputs as decision
  input;
- recommended CRLB figure decision path;
- human-review questions;
- exact next implementation task if a non-final manuscript-style figure
  candidate is approved;
- files that task may edit;
- stop gates;
- confirmation no files were edited.

## Hard Constraints

- Do not run notebook code.
- Do not generate manuscript figures.
- Do not run full sweeps.
- Do not edit manuscript, response-letter, bibliography, figure, PSFrag,
  generated PDF, notebook, package source, test, or result files.
