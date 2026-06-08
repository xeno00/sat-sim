MODE: PLAN_ONLY

# Next Task: Plan Step B Truth-Gate Replacement

## Purpose

Use the controlled migration ladder to design the next correction: replacing
legacy truth-gated LM acceptance with observable weighted-residual/trust-region
criteria while keeping all other legacy behavior fixed.

Current ladder status:

- Baseline freeze: healthy.
- `legacy_staged_compatible`: healthy.
- `step_a_no_display_smoothing`: healthy.
- First degraded step: none.

Relevant artifacts:

- `outputs/reports/CONTROLLED_MIGRATION_LADDER.md`
- `outputs/migration_ladder/step_a_no_display_smoothing/`
- `outputs/reports/LEGACY_TO_PACKAGE_PORT_PLAN.md`
- `scripts/run_controlled_migration_ladder.py`
- `jcls_sim/migration.py`

## Scope

Inspect:

- legacy truth-gated acceptance in `scripts/replay_legacy_clock_sweep_figures.py`
- current package estimators in `jcls_sim/estimators.py`
- current package algorithm flow in `jcls_sim/algorithm.py`
- migration step definitions in `jcls_sim/migration.py`
- controlled ladder runner/tests

Do not edit:

- `JCLS_Simulation.ipynb`
- manuscript files
- response-letter files
- bibliography files
- Work-In-Progress figure files
- PSFrag files
- generated manuscript PDFs
- existing manuscript result files

## Required Analysis

1. Identify exact truth-state gates in the legacy replay path.
2. Propose observable replacement gates based on weighted residual decrease,
   trust-region/damping, finite values, rank status, and optional prior
   innovation consistency.
3. Define the smallest Step B implementation that changes only
   `acceptance_mode` while preserving all-clock internals and legacy metrics.
4. Define tiny and medium graph checks.
5. Define tests proving no true-state error is used by Step B acceptance.

## Expected Output

Return an implementation plan with:

- exact files to edit;
- exact step/config names;
- tests to add/update;
- stop rule;
- expected outputs under `outputs/migration_ladder/step_b_*`;
- risk level and remaining blockers.

