# Codex Task Queue for sat-sim

This queue is advisory unless the user explicitly asks Codex to run the queue.
Use `RUN_CODEX.md` and `AGENTS.md` for execution rules.

Queue execution rules:

- Commit/push after each completed implementation task when a commit is
  appropriate.
- Stop if commit/push fails.
- Stop if tests fail.
- Stop if a task needs out-of-scope notebook, manuscript, response-letter,
  figure, or generated-output edits.
- Default `May merge: no`.
- Default `May run expensive simulations: no`.

## 1. Package-native CRLB mini-sweep comparison plan

Status: superseded by merged CRLB geometry, manuscript-candidate,
figure-candidate, preview, and decision-plan diagnostics.

Mode: `PLAN_ONLY`

Parallel-safe: yes, read-only/planning

Allowed edit files:

- none

Read-only files:

- `v24_diagnostics/sweep_v24_crlb_ns.json`
- `scripts/sweep_v24_crlb.py`
- `jcls_sim/configs.py`
- `jcls_sim/jacobian.py`
- `jcls_sim/fim.py`
- `jcls_sim/bounds.py`
- `tests/test_crlb_sweep.py`
- `PROJECT_STATUS.md`
- `docs/tasks/NEXT.md`

Expected tests:

- none required

Stop gates:

- need for code edits
- need for notebook execution
- figure/output generation request
- human technical decision required

May merge: no

May run expensive simulations: no

## 2. Package-native CRLB mini-sweep implementation

Status: completed/superseded by merged package-native CRLB sweep and hardened
diagnostics.

Mode: `IMPLEMENT_APPROVED`

Parallel-safe: maybe, only if it edits distinct runner/output files

Allowed edit files:

- `jcls_sim/configs.py`
- `scripts/sweep_v24_crlb.py`
- `tests/test_crlb_sweep.py`
- optional `jcls_sim/__init__.py`
- `PROJECT_STATUS.md`
- `docs/tasks/NEXT.md`

Read-only files:

- existing package modules and tests needed for API compatibility

Expected tests:

- `python -m unittest discover -s tests`

Stop gates:

- any other branch touches the same allowed edit files
- test failure
- notebook import or execution needed
- generated manuscript figure risk
- output overwrite risk

May merge: no

May run expensive simulations: no

## 3. Legacy notebook bridge audit

Status: implemented on branch `codex/crlb-decision-sprint`; awaiting
read-only review before merge. See `docs/tasks/NEXT.md`.

Mode: `PLAN_ONLY` / `REVIEW_DIFF`

Parallel-safe: yes, read-only

Allowed edit files:

- none

Read-only files:

- `JCLS_Simulation.ipynb`
- package modules and diagnostic JSON needed for comparison
- `PROJECT_STATUS.md`
- `docs/tasks/NEXT.md`

Expected tests:

- none required unless explicitly requested

Stop gates:

- notebook execution required
- code edits required
- generated output overwrite risk

May merge: no

May run expensive simulations: no

## 4. Runtime profiling plan

Status: pending after legacy notebook provenance audit.

Mode: `PLAN_ONLY`

Parallel-safe: yes, read-only

Allowed edit files:

- none

Read-only files:

- package modules
- scripts
- tests
- diagnostics

Expected tests:

- none required

Stop gates:

- need for expensive profiling run
- need for optimizer refactor
- need for final figure generation

May merge: no

May run expensive simulations: no
