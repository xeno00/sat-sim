MODE: PLAN_ONLY

# Next Task: Plan Safe Legacy Figure-Cell Replay After Executable Notebook Audit

## Purpose

Use the executable notebook regression-audit outputs under
`v24_notebook_regression_outputs/` to plan the smallest safe legacy figure-cell
replay path. Do not implement yet and do not regenerate manuscript figures.

The current audit verifies deterministic row-order and unit/clock compatibility
for tiny fixtures, and the extracted-class smoke harness can instantiate the
legacy classes and run tiny model/Jacobian/LM/EKF checks. Full notebook figure
reproduction has not been performed.

## Scope

Inspect:

- `v24_notebook_regression_outputs/EXECUTABLE_NOTEBOOK_REGRESSION_REPORT.md`
- `v24_notebook_regression_outputs/EXECUTABLE_NOTEBOOK_REGRESSION_REPORT.json`
- `v24_notebook_regression_outputs/NOTEBOOK_DATALINK_LINE_AUDIT.md`
- `v24_notebook_regression_outputs/NOTEBOOK_MEASUREMENT_ORDER_AUDIT.md`
- `v24_notebook_regression_outputs/UNIT_CLOCK_EXECUTABLE_FIXTURE.md`
- `v24_notebook_regression_outputs/executed_legacy/legacy_notebook_smoke.json`
- `v24_notebook_regression_outputs/FIGURE_REGRESSION_TABLE.md`
- `scripts/run_legacy_notebook_smoke.py`
- `scripts/audit_notebook_measurements.py`
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

1. Identify the exact notebook cells/functions needed to replay only:
   - `pos_vary_ues.pdf`
   - `sync_vary_ues.pdf`
   - `pos_vary_clock.pdf`
   - `sync_vary_clock.pdf`
   - `pos_crlb_0dB_0dB.pdf`
   - `sync_crlb_0dB_0dB.pdf`
2. Identify every side effect that must be skipped or redirected:
   - Colab setup,
   - package installs,
   - workspace pickle load/save,
   - `plt.show`,
   - manuscript figure folders,
   - existing result outputs.
3. Decide whether the first implementation should replay:
   - one tiny deterministic optimizer smoke case;
   - one tiny CRLB figure-family smoke case;
   - one target figure script with one Monte Carlo trial;
   - or only extract callable figure functions and stop.
4. Propose an output root under
   `v24_notebook_regression_outputs/executed_legacy/` that cannot overwrite
   manuscript or legacy outputs.
5. State whether human approval is required before executing any target figure
   cell.

## Expected Output

Return a plan with:

- figure-cell dependency map;
- required extraction/skipping rules;
- output redirection strategy;
- smallest next implementation task;
- tests to add;
- stop conditions;
- whether full notebook figure reproduction is now feasible.

Update `PROJECT_STATUS.md` and `docs/tasks/NEXT.md` only if the human approves a
new implementation plan.
