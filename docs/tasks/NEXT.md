MODE: PLAN_ONLY

# Next Task: Plan Estimator/Model Redesign After Human-Review Fig. 4--7 Sprint

## Purpose

Use the human-review outputs under `v24_human_review_outputs/` to plan the next
package-native estimator/model step. Do not implement yet.

The current human-review outputs are useful provenance artifacts, but they are
not manuscript-ready. The report marks all four figure families as
review-only/not for submission because JCLS convergence is weak, one-UE full
JCLS cases are unobservable, and refined JCLS can underperform the
no-cooperation baseline.

## Scope

Inspect:

- `v24_human_review_outputs/HUMAN_REVIEW_REPORT.md`
- `v24_human_review_outputs/HUMAN_REVIEW_REPORT.json`
- `v24_human_review_outputs/**/summary.csv`
- `v24_human_review_outputs/**/metadata.json`
- `jcls_sim/algorithm.py`
- `jcls_sim/figure_generation.py`
- `tests/test_algorithm.py`
- `tests/test_figure_generation.py`

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

1. Identify which figure families fail due to:
   - unobservable one-UE/full-JCLS cases;
   - poor Step 2 convergence;
   - weak conditioning;
   - dynamic model limitations;
   - synthetic geometry/noise assumptions.
2. Decide whether the next implementation should prioritize:
   - non-leaky priors/regularization for clocks and Step 1 positions;
   - scaled trust-region optimization;
   - augmented velocity/clock-drift state;
   - full-rank figure-case filtering/masking;
   - a different manuscript figure concept;
   - TLE/SGP4 geometry upgrade.
3. Propose the smallest next code-only task with tests.
4. State whether any existing manuscript Fig. 4--7 should be considered unsafe.

## Expected Output

Return a plan with:

- failure-mode matrix by figure and baseline;
- recommended next implementation task;
- files likely affected;
- tests to add;
- stop conditions;
- whether human technical decision is required.

Update `PROJECT_STATUS.md` and `docs/tasks/NEXT.md` only if the human approves a
new implementation plan.
