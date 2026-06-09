# Codex Task Files for sat-sim

This folder holds persistent task instructions for Codex sessions working on
the `sat-sim` codebase.

## How to use

For code/simulation/result tasks, Codex should read:

1. `AGENTS.md`
2. `RUN_CODEX.md`
3. `PROJECT_STATUS.md`
4. `docs/tasks/QUEUE.md` if present
5. `docs/tasks/NEXT.md`

Then execute only the task in `docs/tasks/NEXT.md` or the explicitly requested
queue task. After each substantial implementation task, update
`PROJECT_STATUS.md` and replace `docs/tasks/NEXT.md` with the next recommended
task. Do not start the next task automatically.

## Merge policy

Every task file should state `MERGE_POLICY`, `DISPOSITION_REQUIRED`,
`PROTECTED_FILES`, `POST_MERGE_CHECKS`, and `FINAL_RESPONSE_SCHEMA`.

A branch is not complete merely because it was pushed. It must be merged,
parked, superseded, quarantined, or explicitly awaiting human review. If it is
not merged, the task report must say why and name the next disposition action.
Use `scripts/check_protected_files.py` before merging any task branch.

A branch with unique work must either be merged, have an open PR, or be
recorded as parked, quarantined, superseded, or awaiting human review with a
reason. A pushed branch alone is not an acceptable final state.

The canonical live branch-status source is
`outputs/reports/ACTIVE_BRANCH_LEDGER.md` and
`outputs/reports/ACTIVE_BRANCH_LEDGER.json`. Update it when branch disposition
changes. Cleanup and integration reports are snapshots and should point to the
active branch ledger.

## Python dependencies

Do not add virtual-environment or bootstrap machinery unless the human
explicitly asks. Use the selected Python runtime directly. If a standard
scientific package needed by the task is missing, install the minimal package
set into that same runtime with `python -m pip install ...`, rerun the import
check, and report the exact install command. Current standard test dependencies
are `numpy`, `scipy`, and `matplotlib`. Stop and ask before installing packages
outside the standard scientific Python stack.

## Modes

- `MODE: PLAN_ONLY`: inspect and plan; do not edit files.
- `MODE: IMPLEMENT_APPROVED`: execute the approved task with the smallest safe
  diff and run the requested tests/checks.
- `MODE: REVIEW_DIFF`: audit changes or consistency; do not edit unless the
  task explicitly says to fix.

## Parallel task design

Tasks intended for parallel execution should declare:

- mode;
- allowed files;
- forbidden files;
- whether the task may run in parallel;
- expected tests/checks;
- stop gates;
- whether the task may merge;
- whether the task may generate outputs.
- merge/disposition policy.

Parallel edit-capable tasks must use branch/worktree isolation and explicit
file ownership. `PROJECT_STATUS.md`, `docs/tasks/NEXT.md`, and
`docs/tasks/QUEUE.md` are coordinator-owned and should not be edited by
subagents.

Each subagent must report using this format:

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

### Example parallel-safe task

```markdown
Mode: IMPLEMENT_APPROVED
Parallel-safe: yes
Allowed files:
- jcls_sim/bounds.py
- tests/test_bounds.py
Forbidden:
- JCLS_Simulation.ipynb
- result outputs
Tests:
- python -m unittest discover -s tests
Stop if:
- any other branch touches bounds.py or test_bounds.py
May merge: no
May run expensive simulations: no
```

## Final response schema

```text
Branch:
Commit:
Pushed:
PR:
PR status:
Merged to main:
Merge commit:
If not merged, disposition:
Reason not merged:
If branch remains open, why:
If branch deleted, deletion confirmation:
Tests:
Protected-file check:
Reports/outputs:
Current main before:
Current main after:
Working tree clean:
Branches inspected:
Branches remaining:
PRs opened:
PRs closed:
PRs merged:
Branches deleted local:
Branches deleted remote:
Branches parked:
Branches quarantined:
Branches needing human review:
ACTIVE_BRANCH_LEDGER updated:
If no, reason:
Branches changed:
Remaining active branches:
Next action:
```

## Future command

From the repository root, the user may simply say:

```text
Follow AGENTS.md.
```

Root `AGENTS.md` routes code/simulation work here automatically.
