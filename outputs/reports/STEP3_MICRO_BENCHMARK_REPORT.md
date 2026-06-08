# Step 3 Micro-Benchmark Report

## Executive Summary

- Artifact status: `non_final_step3_micro_benchmarks`
- Runtime seconds: `7.843`
- Cases: `['clock_only_correction', 'position_only_correction', 'clock_drift_correction', 'gauge_common_clock_perturbation', 'mixed_position_clock_perturbation', 'schur_nuisance_clock_toy']`
- Variants: `['baseline_c5_current_cov', 'block_scaled_no_drift', 'block_scaled_with_clock_drift', 'gauge_common_clock_projected', 'schur_nuisance_clock_reduced', 'clock_only_filter']`
- Promoted variants: `['block_scaled_no_drift', 'block_scaled_with_clock_drift', 'gauge_common_clock_projected', 'schur_nuisance_clock_reduced']`

## Variant Summary

| Variant | Passed | Finite | Mean position ratio | Mean clock ratio |
|---|---:|---:|---:|---:|
| `baseline_c5_current_cov` | 4/6 | 6/6 | 0.0632412 (3) | 1.05599 (5) |
| `block_scaled_no_drift` | 5/6 | 6/6 | 0.0215865 (3) | 0.861271 (5) |
| `block_scaled_with_clock_drift` | 6/6 | 6/6 | 0.0215865 (3) | 0.756064 (5) |
| `gauge_common_clock_projected` | 5/6 | 6/6 | 0.0215865 (3) | 0.825004 (5) |
| `schur_nuisance_clock_reduced` | 5/6 | 6/6 | 0.0215865 (3) | 0.861271 (5) |
| `clock_only_filter` | 3/6 | 6/6 | 1 (3) | 0.861271 (5) |

## Interpretation

Micro-benchmarks isolate Step 3 matrix behavior in deterministic toy systems. Passing these cases is necessary but not sufficient for network-size figure work.

## Output Paths

- Raw CSV: `outputs/step3_micro_benchmarks/raw.csv`
- Summary CSV: `outputs/step3_micro_benchmarks/summary.csv`
- Metadata JSON: `outputs/step3_micro_benchmarks/metadata.json`
- Plots:
  - `outputs/step3_micro_benchmarks/plots/position_error_before_after.pdf`
  - `outputs/step3_micro_benchmarks/plots/position_error_before_after.png`
  - `outputs/step3_micro_benchmarks/plots/clock_error_before_after.pdf`
  - `outputs/step3_micro_benchmarks/plots/clock_error_before_after.png`
  - `outputs/step3_micro_benchmarks/plots/block_update_norms.pdf`
  - `outputs/step3_micro_benchmarks/plots/block_update_norms.png`
  - `outputs/step3_micro_benchmarks/plots/pass_fail_heatmap.pdf`
  - `outputs/step3_micro_benchmarks/plots/pass_fail_heatmap.png`
  - `outputs/step3_micro_benchmarks/plots/position_clock_improvement_scatter.pdf`
  - `outputs/step3_micro_benchmarks/plots/position_clock_improvement_scatter.png`
