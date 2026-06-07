MODE: PLAN_ONLY

This task may be executed via `RUN_CODEX.md`. Do not edit files unless the
human explicitly approves implementation. Do not merge unless explicitly
allowed.

# Next Task: Plan CRLB Figure Strategy From Non-Final Candidate

## Purpose

Use the merged non-final manuscript CRLB candidate diagnostic to decide how the
paper's CRLB-related figures should be handled. This is a planning task only:
do not generate figures, edit the notebook, or modify manuscript files.

## Context

The package now has:

- full-gauged V24 FIM and CRLB bound extraction;
- rank-deficient manuscript-readiness guards;
- fixed-parameter information-addition diagnostics;
- growing-`N_s` diagnostics with explicit non-monotonic interpretation;
- a manuscript-relevant non-final CRLB candidate JSON that marks
  rank-deficient points unavailable and finite points manuscript-ready.

## Scope

Allowed files to inspect:

- `v24_diagnostics/manuscript_crlb_candidate.json`
- `v24_diagnostics/crlb_geometry_diagnostics.json`
- `v24_diagnostics/sweep_v24_crlb_ns.json`
- `scripts/diagnose_v24_manuscript_crlb_candidate.py`
- `scripts/diagnose_v24_crlb_geometry.py`
- `scripts/sweep_v24_crlb.py`
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

1. Which existing manuscript CRLB figures are most likely unsafe or need
   replacement based on the V24 candidate diagnostics?
2. Which diagnostic figure direction is scientifically safest:
   - rank-feasibility heatmap;
   - finite CRLB versus `N_s` with unavailable points marked;
   - fixed-parameter measurement-addition CRLB curve;
   - a table-only diagnostic summary?
3. What must be true before final manuscript figure regeneration is approved?
4. What package script/output should be implemented next as a non-final figure
   candidate, still outside manuscript figure folders?
5. What response/manuscript implications would need human approval if the CRLB
   figure concept changes?

## Required Output

Return:

- PASS / PASS WITH CAVEAT / FAIL for using current non-final diagnostics as
  figure-strategy input;
- recommended CRLB figure strategy;
- figures/results that remain unsafe;
- exact non-final implementation task to approve next;
- files that task should edit;
- hard stop gates;
- confirmation no files were edited.

## Hard Constraints

- Do not run notebook code.
- Do not generate figures.
- Do not run full sweeps.
- Do not edit manuscript, response-letter, bibliography, figure, PSFrag,
  generated PDF, notebook, package source, test, or result files.

