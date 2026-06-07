# RUN_CODEX.md — sat-sim

This is the executable workflow entrypoint for code/simulation tasks in
`sat-sim`.

Before running a task, read:

1. `AGENTS.md`
2. `PROJECT_STATUS.md`
3. `docs/tasks/QUEUE.md` if present
4. `docs/tasks/NEXT.md`

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
allows it.

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
- Report branch, commit, push, and merge state in the final response.

## Tests

Preferred test command:

```powershell
python -m unittest discover -s tests
```

If default `python` lacks NumPy, use the bundled runtime:

```powershell
& 'C:\Users\James\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest discover -s tests
```

Do not run full sweeps or generate final manuscript figures unless explicitly
approved.
