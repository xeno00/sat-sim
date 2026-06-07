MODE: PLAN_ONLY

This task may be executed via `RUN_CODEX.md`. Use flexible subagents if useful.
Use branch/worktree isolation for any parallel edit-capable work. Create a
file-ownership table before edits. Commit and push task-scoped changes when
complete. Do not merge unless explicitly allowed.

# Next Task: Review Package-Native CRLB Mini-Sweep Diagnostics

## Purpose

Review the non-final package-native CRLB mini-sweep diagnostic trends and decide
whether the next implementation step should be package-native non-final CRLB
diagnostic curves. Do not generate final manuscript figures.

## Scope

Allowed files to inspect:

- `v24_diagnostics/sweep_v24_crlb_ns.json`
- `scripts/sweep_v24_crlb.py`
- `jcls_sim/configs.py`
- `jcls_sim/jacobian.py`
- `jcls_sim/fim.py`
- `jcls_sim/bounds.py`
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

## Review Questions

1. Does the mini-sweep JSON contain one case for each `N_s in [2, 3, 4, 5, 6]`?
2. Are the reported dimensions consistent with `4*Nu + Ns - 1`?
3. Are FIM ranks, covariance methods, and condition numbers reported clearly?
4. Are the reported PEB and clock-bound metrics finite and nonnegative?
5. Do the trends look plausible enough for a non-final diagnostic, or do they
   suggest a package bug or geometry-design issue?
6. Which cases remain rank-deficient, and is that expected for the tiny
   diagnostic geometry?
7. Are the static legacy-risk notes adequate for provenance tracking?
8. What would be the safest next implementation task if diagnostic curves are
   warranted?

## Required Output

Return a concise plan/audit report with:

- PASS / PASS WITH CAVEAT / FAIL for the mini-sweep diagnostic;
- a small table of `N_s`, dimension, rank, covariance method, average UE PEB,
  and average clock bound;
- blocking issues, if any;
- nonblocking caveats;
- whether existing manuscript CRLB figures remain unsafe to trust;
- recommended next task;
- proposed replacement contents for `PROJECT_STATUS.md` and `docs/tasks/NEXT.md`
  if the human approves moving forward.

## Hard Constraints

- Do not edit files in this task.
- Do not run notebook code.
- Do not generate figures.
- Do not run full sweeps.
- Do not update status/task files during this `PLAN_ONLY` review unless the
  human explicitly asks for implementation.
