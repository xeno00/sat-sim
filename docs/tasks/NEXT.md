MODE: PLAN_ONLY

This task may be executed via `RUN_CODEX.md`. Use flexible subagents if useful.
Do not edit files unless the human explicitly approves implementation. Do not
merge unless explicitly allowed.

# Next Task: Design Better Non-Final CRLB Diagnostic Geometry

## Purpose

Design the next package-native CRLB diagnostic before any manuscript figure
rerun. The existing mini-sweep is useful for smoke testing, but it changes
parameter dimension with `N_s`, uses tiny near-threshold geometries, and marks
rank-deficient cases as diagnostic only. The next diagnostic should separate
fixed-parameter information-addition behavior from changing-`N_s` nuisance-clock
behavior.

## Scope

Allowed files to inspect:

- `v24_diagnostics/smoke_v24_crlb.json`
- `v24_diagnostics/sweep_v24_crlb_ns.json`
- `scripts/smoke_v24_crlb.py`
- `scripts/sweep_v24_crlb.py`
- `jcls_sim/configs.py`
- `jcls_sim/jacobian.py`
- `jcls_sim/fim.py`
- `jcls_sim/bounds.py`
- `tests/test_bounds.py`
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
- existing result files
- plotting code
- figure-generation code
- package source files
- tests

## Planning Questions

1. What fixed-parameter monotonic diagnostic should be implemented to verify
   information addition without changing `N_theta`?
2. What changing-`N_s` diagnostic geometry should be used to study satellite
   availability while making nuisance-clock growth explicit?
3. Should the design use:
   - fixed satellite pool with nested subsets;
   - fixed UE geometry;
   - repeated random geometries with median/quantiles;
   - rank-only observability checks;
   - exclusion or explicit marking of rank-deficient cases?
4. What metadata should each future diagnostic case report?
5. Which current manuscript CRLB figures remain unsafe until this design is
   implemented and reviewed?

## Required Output

Return a concise implementation plan with:

- PASS / PASS WITH CAVEAT / FAIL for current hardened diagnostics;
- proposed diagnostic geometry;
- proposed output JSON schema;
- proposed tests;
- expected runtime/scope;
- stop gates;
- exact files to edit in the next IMPLEMENT_APPROVED task;
- confirmation that no files were edited in this PLAN_ONLY task.

## Hard Constraints

- Do not run notebook code.
- Do not generate figures.
- Do not run full sweeps.
- Do not edit manuscript, response-letter, bibliography, figure, PSFrag,
  generated PDF, notebook, package source, test, or result files.
