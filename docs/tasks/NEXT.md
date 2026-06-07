MODE: PLAN_ONLY

This task may be executed via `RUN_CODEX.md`. Do not edit files unless the
human explicitly approves implementation. Do not merge unless explicitly
allowed.

# Next Task: Plan Manuscript-Relevant Non-Final CRLB Candidate

## Purpose

Use the package-native CRLB geometry diagnostics to design a manuscript-relevant
non-final CRLB candidate before any figure rerun. The goal is to choose a
scientifically defensible diagnostic direction, not to generate final
manuscript figures.

## Context

The merged CRLB geometry diagnostic separates:

- fixed-parameter information addition;
- growing-`N_s` nuisance-clock behavior;
- rank-feasibility checks.

The fixed-parameter diagnostic provides the clean monotonicity sanity check.
The growing-`N_s` diagnostic is useful context but is not a monotonic CRLB
curve because `N_theta` changes. The rank-feasibility grid can identify
full-rank regimes before any manuscript-style CRLB rerun.

## Scope

Allowed files to inspect:

- `v24_diagnostics/crlb_geometry_diagnostics.json`
- `v24_diagnostics/sweep_v24_crlb_ns.json`
- `scripts/diagnose_v24_crlb_geometry.py`
- `scripts/sweep_v24_crlb.py`
- `jcls_sim/configs.py`
- `jcls_sim/bounds.py`
- `tests/test_crlb_diagnostics.py`
- `tests/test_crlb_sweep.py`
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

1. Which candidate is most defensible for manuscript-relevant non-final CRLB
   diagnostics?
   - full-rank CRLB versus `N_s` with unavailable points marked;
   - CRLB versus measurement subset size for fixed `Nu,Ns`;
   - rank-feasibility heatmap over `Nu,Ns`;
   - another small diagnostic derived from the rank grid.
2. Which candidate best supports or replaces the existing CRLB manuscript
   figures without overclaiming monotonicity?
3. What full-rank regimes should be used, based on the current
   `crlb_geometry_diagnostics.json`?
4. What metadata must be carried forward so rank-deficient/unavailable points
   cannot be mistaken for finite CRLB values?
5. What implementation should be approved next, and what files should it edit?

## Required Output

Return:

- PASS / PASS WITH CAVEAT / FAIL for using the current geometry diagnostics as
  planning input;
- recommended manuscript-relevant non-final CRLB candidate;
- rationale and scientific caveats;
- exact proposed output JSON schema;
- proposed tests;
- expected runtime/scope;
- stop gates;
- exact files to edit in the next `IMPLEMENT_APPROVED` task;
- confirmation that no files were edited in this `PLAN_ONLY` task.

## Hard Constraints

- Do not run notebook code.
- Do not generate figures.
- Do not run full sweeps.
- Do not edit manuscript, response-letter, bibliography, figure, PSFrag,
  generated PDF, notebook, package source, test, or result files.

