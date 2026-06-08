# Step 3 Residual Covariance Robust Candidate Report

- Artifact status: `non_final_step3_residual_cov_robust_candidate_validation`
- Best robust candidate: `residual_scaled_block_diag_with_sync_safeguard`
- Medium rows: `48`
- Truth-state acceptance: `False`
- Truth-derived covariance: `False`

## Candidate Summary

| Candidate | Both improved | Mean position | Max position | Mean sync | Max sync | Fallbacks | Strict pass |
|---|---:|---:|---:|---:|---:|---:|---|
| `residual_scaled_block_diag_base` | 9/12 | 0.05416 | 0.1445 | 0.4623 | 1.679 | 0 | `False` |
| `residual_scaled_block_diag_with_sync_safeguard` | 9/12 | 0.05416 | 0.1445 | 0.3856 | 1 | 3 | `True` |
| `residual_scaled_block_diag_clock_only_fallback` | 9/12 | 0.2698 | 1 | 0.3856 | 1 | 3 | `True` |
| `residual_scaled_block_diag_position_damped` | 9/12 | 0.7591 | 0.7808 | 0.4623 | 1.679 | 0 | `False` |

## Output Paths

- Raw CSV: `outputs/step3_residual_cov_robust_candidates/raw.csv`
- Summary CSV: `outputs/step3_residual_cov_robust_candidates/summary.csv`
- Metadata JSON: `outputs/step3_residual_cov_robust_candidates/metadata.json`
- Plots:
  - `outputs/step3_residual_cov_robust_candidates/plots/medium_row_position_sync_ratio_heatmap.pdf`
  - `outputs/step3_residual_cov_robust_candidates/plots/medium_row_position_sync_ratio_heatmap.png`
  - `outputs/step3_residual_cov_robust_candidates/plots/failure_row_update_norm_by_block.pdf`
  - `outputs/step3_residual_cov_robust_candidates/plots/failure_row_update_norm_by_block.png`
  - `outputs/step3_residual_cov_robust_candidates/plots/block_diag_vs_full_covariance_row_comparison.pdf`
  - `outputs/step3_residual_cov_robust_candidates/plots/block_diag_vs_full_covariance_row_comparison.png`
  - `outputs/step3_residual_cov_robust_candidates/plots/robust_candidate_max_ratio_comparison.pdf`
  - `outputs/step3_residual_cov_robust_candidates/plots/robust_candidate_max_ratio_comparison.png`
  - `outputs/step3_residual_cov_robust_candidates/plots/robust_candidate_mean_ratio_comparison.pdf`
  - `outputs/step3_residual_cov_robust_candidates/plots/robust_candidate_mean_ratio_comparison.png`
