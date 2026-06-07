MODE: IMPLEMENT_APPROVED

This task may be executed via `RUN_CODEX.md`. Use flexible subagents only if
useful. Commit and push task-scoped changes when complete. Do not merge unless
explicitly allowed.

# Next Task: Refresh Hardened Non-Final CRLB Diagnostics

## Purpose

Regenerate the existing non-final CRLB diagnostic JSON files so they include the
hardened rank/nullity and manuscript-reportability fields added by the CRLB
diagnostic hardening pass. Do not generate manuscript figures.

## Scope

Allowed files to edit:

- `v24_diagnostics/smoke_v24_crlb.json`
- `v24_diagnostics/sweep_v24_crlb_ns.json`
- `PROJECT_STATUS.md`
- `docs/tasks/NEXT.md`

Allowed files to inspect:

- `scripts/smoke_v24_crlb.py`
- `scripts/sweep_v24_crlb.py`
- `jcls_sim/bounds.py`
- `tests/test_bounds.py`
- `tests/test_crlb_sweep.py`

Do not edit:

- `JCLS_Simulation.ipynb`
- manuscript files
- response-letter files
- bibliography files
- Work-In-Progress figure files
- PSFrag files
- generated manuscript PDFs
- generated figure PDFs/EPS/PNGs
- plotting code
- figure-generation code
- package source files
- tests

## Tasks

1. Run only the tiny non-final CRLB diagnostic writers with overwrite enabled:
   - `scripts/smoke_v24_crlb.py`
   - `scripts/sweep_v24_crlb.py`
2. Confirm both JSON files include:
   - `measurement_count`
   - `unknown_count`
   - `parameter_dim`
   - `fim_rank`
   - `fim_nullity`
   - `covariance_method`
   - `manuscript_crlb_status`
   - `manuscript_bounds_defined`
3. Confirm rank-deficient cases have `manuscript_crlb_status` set to
   `undefined_rank_deficient` and manuscript-style bound values set to `null`.
4. Run the sat-sim unit tests only.
5. Update `PROJECT_STATUS.md` and replace `docs/tasks/NEXT.md` with the next
   recommended PLAN_ONLY review task.

## Hard Constraints

- Do not run notebook code.
- Do not generate figures.
- Do not run full sweeps.
- Do not edit manuscript, response-letter, bibliography, figure, PSFrag,
  generated PDF, notebook, package source, or test files.
- Keep all outputs non-final under `v24_diagnostics/`.
