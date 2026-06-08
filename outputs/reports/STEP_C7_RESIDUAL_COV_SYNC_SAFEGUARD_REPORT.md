# Step C7 Residual-Covariance Sync Safeguard Report

## Executive Summary
- Estimator mode: `step_c7_residual_cov_sync_safeguard`.
- Status: non-final diagnostic validation, not manuscript-ready output.
- Medium validation rows: `12`.
- Both improved: `9/12`.
- Position improved: `12/12`.
- Synchronization improved: `9/12`.
- Mean/max position ratio: `0.054160` / `0.144487`.
- Mean/max sync ratio: `0.385611` / `1.000000`.
- Fallback count: `3`; reasons: `single_user_clock_update_not_observable`.

## Estimator Mode Definition
C7 starts from the Step B/LM-only state, computes residual-scaled LM covariance, extracts/clips position and clock blocks, appends a clock-drift block when present, and applies a Step 3 update.

## Covariance Initialization
`P_{theta,0} = sigma_hat^2 (J^T R^{-1} J + lambda I)^dagger`, with `sigma_hat^2 = r^T R^{-1}r / max(1, N_z - N_theta)`. The validation uses the block-diagonal, diagonal-clipped form preferred after the residual-covariance audit.

## Safeguard Logic
The synchronization safeguard uses only finite-state, observable objective, clock-update-to-covariance scale, common-clock component, and single-UE observability diagnostics. When triggered, it reverts UE clock, satellite clock, and drift updates to the Step B state.

## No-Truth-Leak Statement
Truth-state errors are used only for offline validation metrics and ratios. C7 does not use truth-state acceptance, truth-derived covariance, or truth-derived safeguard decisions.

## Validation Grid
`N_u=[1,3,5,7]`, `N_s=[4,8,12]`.

## Worsened Rows
- No C7 row worsened position or synchronization relative to Step B.

## Ablation Results
| Candidate | Both improved | Mean position ratio | Max position ratio | Mean sync ratio | Max sync ratio | Fallbacks |
|---|---:|---:|---:|---:|---:|---:|
| `step_c7_residual_cov_sync_safeguard` | 9/12 | 0.054160 | 0.144487 | 0.385611 | 1.000000 | 3 |
| `c7_ablation_without_safeguard` | 9/12 | 0.054160 | 0.144487 | 0.462324 | 1.679045 | 0 |
| `c7_ablation_without_residual_scaling` | 5/12 | 0.178388 | 0.369321 | 1.158285 | 1.879426 | 3 |
| `c7_ablation_without_drift` | 9/12 | 0.038374 | 0.096710 | 0.473133 | 1.000000 | 3 |

## Output Links
- Raw CSV: [outputs/step_c7_residual_cov_sync_safeguard/raw.csv](../step_c7_residual_cov_sync_safeguard/raw.csv)
- Summary CSV: [outputs/step_c7_residual_cov_sync_safeguard/summary.csv](../step_c7_residual_cov_sync_safeguard/summary.csv)
- Metadata JSON: [outputs/step_c7_residual_cov_sync_safeguard/metadata.json](../step_c7_residual_cov_sync_safeguard/metadata.json)
- Arrays NPZ: [outputs/step_c7_residual_cov_sync_safeguard/arrays.npz](../step_c7_residual_cov_sync_safeguard/arrays.npz)

## Plots
- [outputs/step_c7_residual_cov_sync_safeguard/plots/localization_error_vs_satellites.pdf](../step_c7_residual_cov_sync_safeguard/plots/localization_error_vs_satellites.pdf)
- [outputs/step_c7_residual_cov_sync_safeguard/plots/synchronization_error_vs_satellites.pdf](../step_c7_residual_cov_sync_safeguard/plots/synchronization_error_vs_satellites.pdf)
- [outputs/step_c7_residual_cov_sync_safeguard/plots/position_ratio_heatmap.pdf](../step_c7_residual_cov_sync_safeguard/plots/position_ratio_heatmap.pdf)
- [outputs/step_c7_residual_cov_sync_safeguard/plots/sync_ratio_heatmap.pdf](../step_c7_residual_cov_sync_safeguard/plots/sync_ratio_heatmap.pdf)
- [outputs/step_c7_residual_cov_sync_safeguard/plots/fallback_count_by_nu_ns.pdf](../step_c7_residual_cov_sync_safeguard/plots/fallback_count_by_nu_ns.pdf)
- [outputs/step_c7_residual_cov_sync_safeguard/plots/update_norm_by_state_block.pdf](../step_c7_residual_cov_sync_safeguard/plots/update_norm_by_state_block.pdf)
- [outputs/step_c7_residual_cov_sync_safeguard/plots/covariance_eigenvalue_diagnostics.pdf](../step_c7_residual_cov_sync_safeguard/plots/covariance_eigenvalue_diagnostics.pdf)
- [outputs/step_c7_residual_cov_sync_safeguard/plots/ablation_comparison.pdf](../step_c7_residual_cov_sync_safeguard/plots/ablation_comparison.pdf)

## Readiness
- Ready for human graph review: `true`.
- Manuscript-ready: `false`.

## Recommended Next Action
Human graph review of C7 diagnostics, then decide whether to run a bounded clock/network figure-candidate validation.
