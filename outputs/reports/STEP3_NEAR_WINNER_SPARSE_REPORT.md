# Step 3 Near-Winner Sparse Report

## Executive Summary

- Artifact status: `non_final_step3_near_winner_sparse`
- Runtime seconds: `7.125`
- Sparse cases: `['Nu3_Ns8', 'Nu7_Ns8', 'Nu7_Ns12']`
- Variants tested: `['block_scaled_drift_base', 'block_scaled_drift_common_clock_projected', 'block_scaled_drift_blockwise_update_clip', 'block_scaled_drift_strong_clock_prior', 'block_scaled_drift_loose_clock_prior', 'block_scaled_no_drift_common_clock_projected', 'schur_nuisance_clock_reduced_block_scaled', 'clock_only_step3_after_step_b']`
- Promoted variants: `['block_scaled_drift_loose_clock_prior', 'block_scaled_drift_base']`
- Medium validation run: `True`

## Best Variants

- Best position variant: `block_scaled_drift_loose_clock_prior`
- Best synchronization variant: `block_scaled_drift_loose_clock_prior`
- Best balanced variant: `block_scaled_drift_loose_clock_prior`
- Clock-only Step 3 promising: `True`
- Drift helps: `True`
- Common-clock projection helps: `False`
- Schur/nuisance-clock reduction helps: `False`

## Variant Summary

| Variant | Both improved | Position improved | Sync improved | Mean pos ratio | Mean sync ratio |
|---|---:|---:|---:|---:|---:|
| `block_scaled_drift_base` | 3/3 | 3/3 | 3/3 | 0.05201 | 0.3404 |
| `block_scaled_drift_common_clock_projected` | 3/3 | 3/3 | 3/3 | 0.05201 | 0.3663 |
| `block_scaled_drift_blockwise_update_clip` | 3/3 | 3/3 | 3/3 | 0.05201 | 0.3404 |
| `block_scaled_drift_strong_clock_prior` | 3/3 | 3/3 | 3/3 | 0.06264 | 0.3937 |
| `block_scaled_drift_loose_clock_prior` | 3/3 | 3/3 | 3/3 | 0.03165 | 0.2428 |
| `block_scaled_no_drift_common_clock_projected` | 3/3 | 3/3 | 3/3 | 0.06399 | 0.4399 |
| `schur_nuisance_clock_reduced_block_scaled` | 3/3 | 3/3 | 3/3 | 0.06399 | 0.4713 |
| `clock_only_step3_after_step_b` | 0/3 | 0/3 | 3/3 | 1 | 0.3404 |

## Medium Validation Summary

| Variant | Both improved | Position improved | Sync improved | Mean pos ratio | Mean sync ratio |
|---|---:|---:|---:|---:|---:|
| `block_scaled_drift_base` | 12/12 | 12/12 | 12/12 | 0.06406 | 0.4255 |
| `block_scaled_drift_loose_clock_prior` | 12/12 | 12/12 | 12/12 | 0.04478 | 0.3291 |

## Interpretation

Sparse diagnostics test whether the micro-benchmark near-winner family transfers to representative network cases. These outputs are non-final and are not manuscript figures.

## Output Paths

- Raw CSV: `outputs/step3_near_winner_sparse/raw.csv`
- Summary CSV: `outputs/step3_near_winner_sparse/summary.csv`
- Metadata JSON: `outputs/step3_near_winner_sparse/metadata.json`
- Plots:
  - `outputs/step3_near_winner_sparse/plots/position_sync_ratio_scatter.pdf`
  - `outputs/step3_near_winner_sparse/plots/position_sync_ratio_scatter.png`
  - `outputs/step3_near_winner_sparse/plots/both_improved_count_by_variant.pdf`
  - `outputs/step3_near_winner_sparse/plots/both_improved_count_by_variant.png`
  - `outputs/step3_near_winner_sparse/plots/position_ratio_heatmap.pdf`
  - `outputs/step3_near_winner_sparse/plots/position_ratio_heatmap.png`
  - `outputs/step3_near_winner_sparse/plots/sync_ratio_heatmap.pdf`
  - `outputs/step3_near_winner_sparse/plots/sync_ratio_heatmap.png`
  - `outputs/step3_near_winner_sparse/plots/update_norm_by_block.pdf`
  - `outputs/step3_near_winner_sparse/plots/update_norm_by_block.png`
  - `outputs/step3_near_winner_sparse/plots/runtime_by_variant.pdf`
  - `outputs/step3_near_winner_sparse/plots/runtime_by_variant.png`
