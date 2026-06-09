# RUN_CODEX.md — sat-sim

This is the executable workflow entrypoint for code/simulation tasks in
`sat-sim`.

Before running a task, read:

1. `sat-sim/AGENTS.md`
2. `sat-sim/PROJECT_STATUS.md`
3. `sat-sim/docs/tasks/QUEUE.md` if present
4. `sat-sim/docs/tasks/NEXT.md`

If already working from the `sat-sim` directory, these are the same files
without the `sat-sim/` prefix.

## Single-task mode

Default for simple tasks:

1. Execute only `docs/tasks/NEXT.md`.
2. Use subagents only if useful under `AGENTS.md`.
3. Branch before edits when the task is implementation work.
4. Commit the task branch after tests when a commit is appropriate.
5. Push the task branch when possible.
6. Update `PROJECT_STATUS.md` and `docs/tasks/NEXT.md`.
7. Do not start the next task.

Default merge policy: push branches and stop for human review. Merge only when
the current task, `docs/tasks/QUEUE.md`, or direct human instruction explicitly
allows it. When merge is allowed, the branch is not complete until it is merged
or assigned an explicit disposition: parked, superseded, quarantined, or
awaiting human review.

## Queue/sprint mode

When `docs/tasks/QUEUE.md` has active tasks and the user says to run the queue,
Codex may execute multiple tasks subject to stop gates.

Codex may run multiple independent tasks in parallel only if:

- tasks have non-overlapping edit sets;
- each edit-capable task has its own branch/worktree;
- a coordinator file-ownership table is created first;
- tests/checks for each branch are defined.

Codex must not parallelize tasks that touch:

- the same source file;
- `PROJECT_STATUS.md`;
- `docs/tasks/NEXT.md`;
- `docs/tasks/QUEUE.md`;
- notebook, result-output, manuscript, response-letter, or figure files.

Codex may parallelize one implementation branch, one read-only audit branch,
one test-only branch, and one legacy review worktree when file ownership is
clear.

## Stop gates

Stop for:

- failing tests;
- merge conflicts;
- unexpected file changes;
- need for notebook edits/execution;
- need for manuscript edits;
- expensive simulations;
- final figure-generation requests;
- output overwrite risk;
- human decision required.

## Run budget

- Default max tasks per run: `3`.
- Default max edit-capable branches per run: `2`.
- Read-only audits are allowed only if they do not consume excessive time.
- Stop when the time budget or task budget is reached.

## Git lifecycle

- Branch before edits.
- Prefer Git worktrees for parallel edit-capable work:

  ```powershell
  git worktree add ../worktrees/<task-name> -b codex/<task-name>
  ```

- Commit task branches after requested tests/checks pass.
- Push task branches when possible.
- Merge only if explicitly allowed.
- Never force-push without explicit approval.
- Run protected-file checks before merging:

  ```powershell
  python scripts/check_protected_files.py --base main --target HEAD --fail-on-protected
  ```

- Report branch, commit, push, merge state, and final disposition in the final
  response.

## Required branch disposition

Every completed task must end with one of:

- `merged_to_main`;
- `parked_do_not_merge_yet`;
- `superseded_do_not_merge`;
- `quarantined_do_not_merge`;
- `awaiting_human_review`.

Use this final response schema:

```text
Branch:
Commit:
Pushed:
Merged to main:
Merge commit:
If not merged, disposition:
Reason not merged:
Tests:
Protected-file check:
Reports/outputs:
Next action:
```

Output-producing branches must include branch/commit/script metadata,
candidate/final/diagnostic readiness, units status, and recommended use before
their outputs are treated as evidence or merged without caveat.

## Tests

Preferred test command:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File '.\scripts\test_sat_sim.ps1'
```

Python dependency policy:

- Do not add virtual-environment machinery unless the human explicitly asks.
- First use the selected Python runtime.
- If required standard scientific packages are missing, install only the
  minimal missing standard packages into that same runtime with
  `python -m pip install ...`, then rerun the import check and tests.
- For now, the standard test dependencies are `numpy`, `scipy`, and
  `matplotlib`.
- Report the exact install command used.
- Do not silently install large or unusual packages. Stop and ask before
  installing packages outside the standard scientific Python stack.

Manual fallback:

```powershell
python -m unittest discover -s tests
```

If default `python` is unavailable, use the bundled runtime:

```powershell
& 'C:\Users\James\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest discover -s tests
```

If the bundled runtime is selected and dependencies are missing, install into
that runtime, for example:

```powershell
& 'C:\Users\James\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pip install numpy scipy matplotlib
```

Do not run full sweeps or generate final manuscript figures unless explicitly
approved.

## Cleanup expectations

- Remove only transient artifacts created by the current task, such as
  `__pycache__`, `.pytest_cache`, temporary files, temporary render folders, and
  temporary job-name outputs.
- Retain source files, tests, scripts, intentional diagnostics, intentional
  result outputs, and any files explicitly requested by the task.
- Do not delete manuscript files, generated manuscript PDFs, figure outputs,
  notebook files, or archived/baseline data.
- Report cleanup performed in the final response.
