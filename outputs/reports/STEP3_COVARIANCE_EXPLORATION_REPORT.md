# Step 3 Covariance Exploration Report

## Executive Summary

- Artifact status: `non_final_step3_covariance_exploration`
- Runtime seconds: `22.734`
- Sparse cases: `['Nu3_Ns8', 'Nu7_Ns8', 'Nu7_Ns12']`
- Lanes run: `['block_scaled_drift_tuning', 'gauge_common_clock', 'lm_curvature', 'position_freeze_damping', 'residual_scaled_lm', 'schur_reduced', 'red_team_triage']`
- Promoted variants: `['block_diag_residual_scaled_covariance', 'full_residual_scaled_covariance']`
- Medium validation run: `True`

## Best Variants

- Best position variant: `block_diag_residual_scaled_covariance`
- Best synchronization variant: `block_diag_residual_scaled_covariance`
- Best balanced variant: `block_diag_residual_scaled_covariance`

## Lane Findings

- LM-derived position covariance helped: `True`
- Residual-scaled covariance helped: `True`
- Position-freeze/damping helped: `True`
- Clock drift helped: `True`
- Gauge projection helped: `True`
- Schur/reduced update helped: `True`

## Variant Summary

| Lane | Variant | Both improved | Mean pos ratio | Mean sync ratio |
|---|---|---:|---:|---:|
| `block_scaled_drift_tuning` | `block_drift_base` | 3/3 | 0.05201 | 0.3404 |
| `block_scaled_drift_tuning` | `block_drift_loose_clock` | 3/3 | 0.03165 | 0.2428 |
| `block_scaled_drift_tuning` | `block_drift_loose_position` | 3/3 | 0.052 | 0.3404 |
| `block_scaled_drift_tuning` | `block_drift_strong_clock` | 3/3 | 0.06264 | 0.3937 |
| `block_scaled_drift_tuning` | `block_drift_tight_position` | 3/3 | 0.05205 | 0.3404 |
| `gauge_common_clock` | `damp_common_clock_025` | 3/3 | 0.05201 | 0.3368 |
| `gauge_common_clock` | `no_drift_project_common_clock` | 3/3 | 0.06399 | 0.4399 |
| `gauge_common_clock` | `project_common_clock` | 3/3 | 0.05201 | 0.3663 |
| `lm_curvature` | `block_diag_lm_covariance` | 2/3 | 0.1673 | 1.267 |
| `lm_curvature` | `full_lm_covariance` | 2/3 | 0.1673 | 1.267 |
| `lm_curvature` | `lm_covariance_floors_ceilings` | 3/3 | 0.07293 | 0.463 |
| `position_freeze_damping` | `freeze_positions_clock_drift` | 0/3 | 1 | 0.3404 |
| `position_freeze_damping` | `position_damped_clock_loose` | 3/3 | 0.751 | 0.2428 |
| `position_freeze_damping` | `position_update_clipped` | 3/3 | 0.2441 | 0.3404 |
| `position_freeze_damping` | `position_update_damped_025` | 3/3 | 0.7519 | 0.3404 |
| `residual_scaled_lm` | `block_diag_residual_scaled_covariance` | 3/3 | 0.02107 | 0.1838 |
| `residual_scaled_lm` | `full_residual_scaled_covariance` | 3/3 | 0.02107 | 0.1838 |
| `residual_scaled_lm` | `residual_scaled_floors_ceilings` | 3/3 | 0.02107 | 0.1838 |
| `schur_reduced` | `clock_first_position_small` | 3/3 | 0.8511 | 0.3404 |
| `schur_reduced` | `clock_only_reduced` | 0/3 | 1 | 0.3404 |
| `schur_reduced` | `schur_position_clock_backsolve` | 3/3 | 0.06399 | 0.4713 |
| `schur_reduced` | `schur_position_only` | 0/3 | 0.06399 | 1 |

## Medium Validation Summary

| Variant | Both improved | Mean pos ratio | Mean sync ratio |
|---|---:|---:|---:|
| `block_diag_residual_scaled_covariance` | 9/12 | 0.05416 | 0.4623 |
| `full_residual_scaled_covariance` | 9/12 | 0.05416 | 0.4623 |

## Output Paths

- All raw CSV: `outputs/step3_covariance_exploration/all_raw.csv`
- All summary CSV: `outputs/step3_covariance_exploration/all_summary.csv`
- Metadata JSON: `outputs/step3_covariance_exploration/metadata.json`
- Task matrix: `outputs/reports/STEP3_COVARIANCE_EXPLORATION_TASK_MATRIX.md`
- Plots:
  - `outputs/step3_covariance_exploration/plots/position_sync_ratio_scatter.pdf`
  - `outputs/step3_covariance_exploration/plots/position_sync_ratio_scatter.png`
  - `outputs/step3_covariance_exploration/plots/both_improved_count_by_lane_variant.pdf`
  - `outputs/step3_covariance_exploration/plots/both_improved_count_by_lane_variant.png`
  - `outputs/step3_covariance_exploration/plots/best_variant_per_lane.pdf`
  - `outputs/step3_covariance_exploration/plots/best_variant_per_lane.png`
  - `outputs/step3_covariance_exploration/plots/position_covariance_vs_position_ratio.pdf`
  - `outputs/step3_covariance_exploration/plots/position_covariance_vs_position_ratio.png`
  - `outputs/step3_covariance_exploration/plots/clock_covariance_vs_sync_ratio.pdf`
  - `outputs/step3_covariance_exploration/plots/clock_covariance_vs_sync_ratio.png`
  - `outputs/step3_covariance_exploration/plots/update_norm_by_block.pdf`
  - `outputs/step3_covariance_exploration/plots/update_norm_by_block.png`
  - `outputs/step3_covariance_exploration/plots/runtime_by_lane.pdf`
  - `outputs/step3_covariance_exploration/plots/runtime_by_lane.png`
