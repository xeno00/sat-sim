MODE: PLAN_ONLY

# Next Task: Plan V24-Clean Staged Estimator Port

## Purpose

Use the medium legacy-compatible network-size replay and the
legacy-to-package port plan to design the next package-native V24 estimator
hardening task. Do not generate manuscript figures.

Current useful artifacts:

- `outputs/legacy_replay/network_size_medium/`
- `outputs/reports/LEGACY_NETWORK_SIZE_REPLAY_REPORT.md`
- `outputs/reports/V24_FIGURE_REPLACEMENT_PLAN.md`
- `outputs/reports/LEGACY_TO_PACKAGE_PORT_PLAN.md`
- `outputs/reports/CURRENT_GRAPH_STATUS.md`

## Scope

Inspect:

- `jcls_sim/algorithm.py`
- `jcls_sim/estimators.py`
- `jcls_sim/figure_generation.py`
- `jcls_sim/metrics.py`
- `jcls_sim/bounds.py`
- `scripts/run_v24_figures_4_7.py`
- `outputs/reports/LEGACY_TO_PACKAGE_PORT_PLAN.md`
- existing tests for algorithm, estimators, metrics, and figure generation

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

1. Identify where package-native Step 1/2/3 acceptance/fallback behavior still
   differs from the successful legacy staged path.
2. Design truth-free acceptance gates using weighted residual decrease,
   innovation consistency, covariance trace, rank status, and finite-value
   checks.
3. Decide how rank-tolerant/pseudoinverse updates should be reported without
   being mislabeled as convergence.
4. Define raw-vs-display transform separation for future figure scripts.
5. Specify focused tests that prove no truth-state access is used in active
   estimator acceptance.

## Expected Output

Return an implementation plan with:

- exact package files to edit;
- exact tests to add/update;
- risk level;
- stop conditions;
- expected diagnostic outputs;
- confirmation no manuscript or notebook edits are needed.

