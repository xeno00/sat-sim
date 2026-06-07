# AGENTS.md — sat-sim V24 Code Workflow

## Purpose

This repository contains the simulation/code provenance path for the V24 JCLS
TAES manuscript. Code work here must be small, test-driven, and explicitly
separated from manuscript editing. Do not use this workflow to edit manuscript
or response-letter files.

## Required entrypoint

For code/simulation/result tasks, read:

1. `AGENTS.md`
2. `RUN_CODEX.md`
3. `PROJECT_STATUS.md`
4. `docs/tasks/QUEUE.md` if present
5. `docs/tasks/NEXT.md`

Then execute according to `RUN_CODEX.md`.

## Code-specific no-edit rules

Do not edit unless a task explicitly allows it:

- `JCLS_Simulation.ipynb`
- manuscript files outside this repository
- response-letter files
- bibliography files
- Work-In-Progress figure files
- PSFrag files
- generated manuscript PDFs
- generated figure PDFs/EPS/PNGs
- existing result outputs

Do not run full sweeps, generate final manuscript figures, or overwrite result
outputs unless explicitly approved.

## V24 simulation conventions

1. First satellite is the reference clock.
2. Reference satellite node id is `Nu + 1`.
3. `delta_{Nu+1}=0`.
4. V24 parameter dimension is `N_theta = 4*Nu + Ns - 1`.
5. Estimated clocks are UE clocks plus non-reference satellite clocks only.
6. V24 clock order is
   `[delta_1, ..., delta_Nu, delta_{Nu+2}, ..., delta_{Nu+Ns}]`.
7. Range-domain measurement model is `z = h(theta) + n`.
8. Receiver/transmitter TOA/range sign convention is
   `h_{i,j} = ||p_i - p_j|| + c(delta_j - delta_i)`.
9. `sigma` is a vector of range-domain standard deviations.
10. `R_z = diag(sigma**2)`.
11. Gaussian/Rician FIM is `I_theta = J_h.T @ R_z^{-1} @ J_h`.
12. FIM/CRLB must use the full gauged joint parameter vector before extracting
    localization/synchronization bounds.
13. Synchronization metrics must be relative to the reference satellite and
    exclude the reference satellite clock.
14. Do not use old scalar NLOS expressions involving `a`, `b`, `q`, or `M` for
    V24 figures.

## Current refactor order

1. Gauge and metrics package.
2. Measurement model and explicit V24 parameter vector.
3. Jacobian and gauged FIM construction.
4. Estimator correctness tests.
5. Runtime profiling and optimization.
6. Reproducible figure reruns.
7. Only then new result figures.

## Flexible subagent workflow

Subagents are optional. Use them only when they improve planning,
implementation, testing, review, or integration. For small exact edits, Codex
may proceed without subagents and should say so.

For each subagent, specify:

- assigned role;
- task;
- branch/worktree;
- files/directories allowed to inspect;
- files allowed to edit, if any;
- files explicitly forbidden;
- tests/checks expected;
- stop conditions.

Role names may be chosen freely. Suggested examples include architecture
planner, implementation worker, test/integration worker, bug diagnosis worker,
math/code conformance reviewer, performance/profiling worker, and
reproducibility worker. These examples are not mandatory.

## Parallel subagent workflow with Git isolation

Parallel edit-capable subagents may be used only when their work is isolated by
Git branch/worktree. Multiple edit-capable subagents must not modify the same
checkout or the same files concurrently.

For parallel edit-capable tasks, prefer:

```powershell
git worktree add ../worktrees/<task-name> -b codex/<task-name>
```

The coordinator/integrator owns task decomposition, branch/worktree creation,
file ownership, integration order, conflict decisions, final tests,
commits/pushes, merge decisions, and updates to `PROJECT_STATUS.md`,
`docs/tasks/NEXT.md`, and `docs/tasks/QUEUE.md`.

Subagents must not independently merge to the target branch.

### File ownership table

Before parallel work begins, create:

```markdown
| Workstream | Branch/worktree | Subagent role | Files allowed to edit | Read-only files | Stop conditions |
|---|---|---|---|---|---|
```

Rules:

1. Only one workstream may own a file for editing.
2. If two workstreams need the same file, serialize them or split the task.
3. `PROJECT_STATUS.md`, `docs/tasks/NEXT.md`, and `docs/tasks/QUEUE.md` are
   coordinator-owned only.
4. Notebook, manuscript, figure, generated-output, and result files are
   read-only by default unless the task explicitly allows them.
5. Subagents must stop if they need an unassigned file.

### Required subagent report format

```text
Assigned role:
Branch/worktree:
Files inspected:
Files changed:
Tests/checks run:
Result:
Risks:
Recommended next action:
Scope boundary encountered:
```

### Coordinator final report format

```text
Mode used:
Subagents used:
File/worktree ownership table:
Branches created:
Files changed:
Tests/builds run:
Result:
Branches committed:
Branches pushed:
Branches merged:
Blocking issues:
Nonblocking caveats:
Cleanup performed:
PROJECT_STATUS.md update summary:
docs/tasks/NEXT.md update summary:
docs/tasks/QUEUE.md update summary:
Out-of-scope files untouched:
```

## Testing and cleanup

- Prefer `python -m unittest discover -s tests` or the repository test script
  specified in `RUN_CODEX.md`.
- Do not run full sweeps unless explicitly approved.
- Remove transient artifacts created by the task when safe:
  `__pycache__`, `.pytest_cache`, temporary files, and clearly temporary
  render/audit folders.
- Retain source files, tests, intentional diagnostics, and intentional result
  outputs.
