# Step 3 Residual Covariance Failure Audit

- Artifact status: `non_final_step3_residual_cov_failure_audit`
- Target variants: `['block_diag_residual_scaled_covariance', 'full_residual_scaled_covariance']`
- Failure rows: `10` / `24`
- Same failure cases: `['Nu1_Ns12', 'Nu1_Ns4', 'Nu1_Ns8', 'Nu7_Ns12', 'Nu7_Ns8']`
- Block/full effectively identical: `True`
- Full cross-covariance used: `False`
- Preferred variant: `block_diag_residual_scaled_covariance`

## Failure Rows

| Variant | Nu | Ns | Position ratio | Sync ratio | Objective before | Objective after | Reasons |
|---|---:|---:|---:|---:|---:|---:|---|
| `block_diag_residual_scaled_covariance` | 1 | 4 | 0.1445 | 1.679 | 604.8 | 0.7656 | sync_ratio_gt_1, sync_worse_gt_5_percent, objective_decreases_but_metric_worsens |
| `block_diag_residual_scaled_covariance` | 1 | 8 | 0.1293 | 1.154 | 1114 | 1.252 | sync_ratio_gt_1, sync_worse_gt_5_percent, objective_decreases_but_metric_worsens |
| `block_diag_residual_scaled_covariance` | 1 | 12 | 0.139 | 1.087 | 1375 | 1.404 | sync_ratio_gt_1, sync_worse_gt_5_percent, objective_decreases_but_metric_worsens |
| `block_diag_residual_scaled_covariance` | 7 | 8 | 0.01667 | 0.1463 | 9724 | 0.3236 | unusually_large_update_norm |
| `block_diag_residual_scaled_covariance` | 7 | 12 | 0.01795 | 0.1844 | 1.373e+04 | 0.4079 | unusually_large_update_norm |
| `full_residual_scaled_covariance` | 1 | 4 | 0.1445 | 1.679 | 604.8 | 0.7656 | sync_ratio_gt_1, sync_worse_gt_5_percent, objective_decreases_but_metric_worsens |
| `full_residual_scaled_covariance` | 1 | 8 | 0.1293 | 1.154 | 1114 | 1.252 | sync_ratio_gt_1, sync_worse_gt_5_percent, objective_decreases_but_metric_worsens |
| `full_residual_scaled_covariance` | 1 | 12 | 0.139 | 1.087 | 1375 | 1.404 | sync_ratio_gt_1, sync_worse_gt_5_percent, objective_decreases_but_metric_worsens |
| `full_residual_scaled_covariance` | 7 | 8 | 0.01667 | 0.1463 | 9724 | 0.3236 | unusually_large_update_norm |
| `full_residual_scaled_covariance` | 7 | 12 | 0.01795 | 0.1844 | 1.373e+04 | 0.4079 | unusually_large_update_norm |

## Block-Diagonal vs Full Covariance

The upstream covariance builder diagonal-clips both residual-scaled variants, so off-diagonal position-clock covariance is not used in either target row set.
