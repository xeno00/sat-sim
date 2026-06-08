# Step 3 Low-Cost Exploration Report

## Executive Summary

- Artifact status: `non_final_step3_low_cost_exploration_proxy`
- Cases tested: `[(3, 8), (7, 8), (7, 12)]`
- Lanes run: `['block_covariance', 'clock_drift', 'gauge_nullspace', 'robust_measurement', 'schur_nuisance_clock', 'solver_mechanics']`
- Row count: `18`
- Runtime seconds: `3.625`
- Promoted ideas: `[]`
- Medium validation run: `False`
- Best localization idea: `clock_drift::measurement_lambda10`
- Best synchronization idea: `block_covariance::covariance_k100`
- Best balanced idea: `clock_drift::measurement_lambda10`

## Interpretation

This sprint used the completed Step 3 gate exploration as a low-cost proxy source after live legacy evaluations exceeded runtime limits. Block-covariance, gauge/nullspace, robust-measurement, and solver-mechanics lanes map directly to prior gate experiments. Clock-drift and Schur/nuisance-clock lanes are proxy-only and should be treated as inconclusive, not executed validations. No proxy lane met promotion criteria for medium validation.

## Summary by Method

| Lane | Method | Accepted | Both improved | Catastrophic | Mean pos ratio | Mean sync ratio |
|---|---|---:|---:|---:|---:|---:|
| `block_covariance` | `covariance_k100` | 1/3 | 0/3 | 0/3 | 1.27164 | 1.12542 |
| `clock_drift` | `measurement_lambda10` | 3/3 | 0/3 | 0/3 | 1.0127 | 1.17128 |
| `gauge_nullspace` | `nullspace_line_search` | 3/3 | 0/3 | 2/3 | 2.35352 | 1.38861 |
| `robust_measurement` | `huber_line_search` | 3/3 | 0/3 | 0/3 | 1.66218 | 1.26671 |
| `schur_nuisance_clock` | `clock_position_line_search` | 3/3 | 0/3 | 2/3 | 2.35352 | 1.38861 |
| `solver_mechanics` | `line_search` | 3/3 | 0/3 | 2/3 | 2.35352 | 1.38861 |

## Output Paths

- Raw CSV: `outputs/step3_low_cost_exploration/raw.csv`
- Summary CSV: `outputs/step3_low_cost_exploration/summary.csv`
- Metadata JSON: `outputs/step3_low_cost_exploration/metadata.json`
- Task matrix: `outputs/reports/STEP3_LOW_COST_EXPLORATION_TASK_MATRIX.json`
- Plots:
  - `outputs/step3_low_cost_exploration/plots/pareto_position_sync_ratio.pdf`
  - `outputs/step3_low_cost_exploration/plots/pareto_position_sync_ratio.png`
  - `outputs/step3_low_cost_exploration/plots/both_improved_by_lane.pdf`
  - `outputs/step3_low_cost_exploration/plots/both_improved_by_lane.png`
  - `outputs/step3_low_cost_exploration/plots/failure_count_by_lane.pdf`
  - `outputs/step3_low_cost_exploration/plots/failure_count_by_lane.png`
  - `outputs/step3_low_cost_exploration/plots/runtime_by_lane.pdf`
  - `outputs/step3_low_cost_exploration/plots/runtime_by_lane.png`
  - `outputs/step3_low_cost_exploration/plots/best_config_per_lane.pdf`
  - `outputs/step3_low_cost_exploration/plots/best_config_per_lane.png`
