MODE: PLAN_ONLY

# Next Task: Plan Safe Legacy Network-Size Figure Replay

## Purpose

Use the successful safe CRLB and clock-sweep replay artifacts to plan the next
legacy figure-family replay. Do not implement yet and do not regenerate
manuscript figures.

Already replayed into diagnostics:

- `pos_crlb_0dB_0dB.pdf`
- `sync_crlb_0dB_0dB.pdf`
- `pos_vary_clock.pdf`
- `sync_vary_clock.pdf`

The next candidate family is:

- `pos_vary_ues.pdf`
- `sync_vary_ues.pdf`

## Scope

Inspect:

- `v24_notebook_regression_outputs/LEGACY_CRLB_REPLAY_REPORT.md`
- `v24_notebook_regression_outputs/LEGACY_CLOCK_SWEEP_REPLAY_REPORT.md`
- `v24_notebook_regression_outputs/FIGURE_REGRESSION_TABLE.md`
- `scripts/replay_legacy_crlb_figures.py`
- `scripts/replay_legacy_clock_sweep_figures.py`
- `JCLS_Simulation.ipynb` statically only

Do not edit:

- `JCLS_Simulation.ipynb`
- manuscript files
- response-letter files
- bibliography files
- Work-In-Progress figure files
- PSFrag files
- generated manuscript PDFs
- generated manuscript figure PDFs/EPS/PNGs
- existing manuscript result files

## Required Analysis

1. Identify exact notebook cells/functions needed for:
   - `pos_vary_ues.pdf`
   - `sync_vary_ues.pdf`
2. Determine whether replay depends on:
   - nonlinear estimator convergence,
   - workspace variables from previous cells,
   - oracle/truth-gated updates,
   - smoothing/fitting/manual edits,
   - random seeds or Monte Carlo loops.
3. Decide whether a safe replay should:
   - execute the original legacy network-size logic with reduced grid/trials;
   - replay saved/static arrays if present;
   - create a tiny deterministic smoke replay;
   - or stop because a human decision is required.
4. Propose output paths under
   `v24_notebook_regression_outputs/executed_legacy/network_size_replay/`.
5. Define tests and stop conditions.

## Expected Output

Return a plan with:

- network-size figure dependency map;
- extraction/skipping rules;
- runtime/seed risk;
- output redirection strategy;
- smallest next implementation task;
- tests to add;
- whether full legacy network-size replay is feasible.

Update `PROJECT_STATUS.md` and `docs/tasks/NEXT.md` only if the human approves a
new implementation plan.
