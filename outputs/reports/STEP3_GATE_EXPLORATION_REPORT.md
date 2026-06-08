# Step 3 Gate Exploration Report

## Executive Summary

- Artifact status: `non_final_step3_gate_exploration`
- Cases tested: `[(3, 8), (7, 8), (7, 12)]`
- Gates tested: `['line_search', 'nis_line_search', 'nullspace_line_search', 'clock_position_line_search', 'covariance_k10', 'covariance_k100', 'measurement_lambda10', 'covariance_k10_measurement_lambda10', 'huber_line_search', 'combined_nis_null_clock']`
- Runtime seconds: `719.219`
- Best gate for position: `measurement_lambda10`
- Best gate for sync: `covariance_k100`
- Best gate for both: `line_search`
- Promising gates for medium validation: `[]`
- Medium validation run: `False`

## Interpretation

Truth state is used only for diagnostic error labels after each candidate update; it is not used for acceptance, covariance, or fallback decisions.
Sparse exploration is intended to identify candidate gates, not to validate manuscript figures.

## Gate Summary

| Gate | Accepted | Position improved | Sync improved | Both improved | Mean pos ratio | Mean sync ratio |
|---|---:|---:|---:|---:|---:|---:|
| `line_search` | 3/3 | 0/3 | 0/3 | 0/3 | 2.35352 | 1.38861 |
| `nis_line_search` | 3/3 | 0/3 | 0/3 | 0/3 | 2.35352 | 1.38861 |
| `nullspace_line_search` | 3/3 | 0/3 | 0/3 | 0/3 | 2.35352 | 1.38861 |
| `clock_position_line_search` | 3/3 | 0/3 | 0/3 | 0/3 | 2.35352 | 1.38861 |
| `covariance_k10` | 3/3 | 0/3 | 0/3 | 0/3 | 2.84275 | 2.03976 |
| `covariance_k100` | 1/3 | 0/3 | 0/3 | 0/3 | 1.27164 | 1.12542 |
| `measurement_lambda10` | 3/3 | 1/3 | 0/3 | 0/3 | 1.0127 | 1.17128 |
| `covariance_k10_measurement_lambda10` | 3/3 | 0/3 | 0/3 | 0/3 | 2.35518 | 1.38548 |
| `huber_line_search` | 3/3 | 0/3 | 0/3 | 0/3 | 1.66218 | 1.26671 |
| `combined_nis_null_clock` | 3/3 | 0/3 | 0/3 | 0/3 | 2.84275 | 2.03976 |

## Output Paths

- Raw CSV: `outputs/step3_gate_exploration/step3_gate_exploration_raw.csv`
- Metadata JSON: `outputs/step3_gate_exploration/metadata.json`
- Objective history: `outputs/step3_gate_exploration/objective_history.json`
- Update diagnostics: `outputs/step3_gate_exploration/update_diagnostics.json`
- Plots:
  - `outputs/step3_gate_exploration/position_sync_ratio_scatter.pdf`
  - `outputs/step3_gate_exploration/position_sync_ratio_scatter.png`
  - `outputs/step3_gate_exploration/update_norm_vs_error_improvement.pdf`
  - `outputs/step3_gate_exploration/update_norm_vs_error_improvement.png`
  - `outputs/step3_gate_exploration/nullspace_ratio_vs_error_improvement.pdf`
  - `outputs/step3_gate_exploration/nullspace_ratio_vs_error_improvement.png`
  - `outputs/step3_gate_exploration/nis_vs_error_improvement.pdf`
  - `outputs/step3_gate_exploration/nis_vs_error_improvement.png`
  - `outputs/step3_gate_exploration/gate_both_improved_bar.pdf`
  - `outputs/step3_gate_exploration/gate_both_improved_bar.png`
