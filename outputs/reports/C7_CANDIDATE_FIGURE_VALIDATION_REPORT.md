# C7 Candidate Figure Validation Report

## Executive Summary
- Verdict: **PASS WITH CAVEAT**.
- Outputs are non-final candidate diagnostics for human review only.
- Manuscript ready: `false`.
- Notebook used: `false`.
- Manuscript directories touched: `false`.
- Human signoff required: `true`.
- Baseline: `Step B / LM-only`.
- C7 estimator mode: `step_c7_residual_cov_sync_safeguard`.
- C7 covariance: typed block-extracted, diagonal-clipped residual-scaled covariance.
- Truth is used only for offline metrics and ratios.
- Clock-sweep status: `sparse_bounded_blocked_by_localization_instability`.

## Figure Family Summary
| Family | Rows | Position improved | Sync improved | Both improved | Fallbacks | Max position ratio | Max sync ratio |
|---|---:|---:|---:|---:|---:|---:|---:|
| `network_size` | 12 | 12 | 9 | 9 | 3 | 0.144487 | 1.000000 |
| `clock_sweep` | 4 | 2 | 2 | 2 | 2 | 1002.997986 | 1.000000 |

## What Was Generated
- Network-size localization versus satellites.
- Network-size synchronization versus satellites, plotted in ns.
- Sparse clock-sweep localization for `10^{-4},10^{-6},10^{-8},10^{-10}` seconds.
- Sparse clock-sweep synchronization, plotted in ns.
- Fallback-annotation diagnostic.
- Ratio-summary diagnostic.
- Raw CSVs, summary CSV, NPZ arrays, metadata JSON, and per-family notes.

## What Was Not Generated
- No manuscript figures were generated.
- No broad algorithm exploration was run.
- No dense/full clock sweep was run; the clock sweep is sparse bounded only.
- No legacy truth-gated MAP/EKF evidence was used as primary evidence.

## Remaining Blockers
- Sparse clock-sweep C7 candidate is not suitable for candidate-figure use yet because at least one bounded clock-standard-deviation row worsens localization substantially.

## Runtime / Cache Notes
- Runtime: `6.844` seconds.
- Cache status: deterministic direct run; no long-running cache-dependent sweep.

## Step B vs C7 Comparison
- Step B / LM-only remains the baseline.
- C7 is plotted as a Step 3 candidate.
- Synchronization plots use ns for readability; raw CSV keeps range-domain km values.

## Fallback-Row Explanation
- `{'num_users': 1, 'num_satellites': 4, 'clock_std_seconds': '', 'fallback_reason': 'single_user_clock_update_not_observable'}`
- `{'num_users': 1, 'num_satellites': 8, 'clock_std_seconds': '', 'fallback_reason': 'single_user_clock_update_not_observable'}`
- `{'num_users': 1, 'num_satellites': 12, 'clock_std_seconds': '', 'fallback_reason': 'single_user_clock_update_not_observable'}`
- `{'num_users': 3, 'num_satellites': 8, 'clock_std_seconds': 0.0001, 'fallback_reason': 'clock_update_exceeds_covariance_scale'}`
- `{'num_users': 3, 'num_satellites': 8, 'clock_std_seconds': 1e-06, 'fallback_reason': 'clock_update_exceeds_covariance_scale'}`
- Fallback reverts UE clock, satellite clock, and drift updates to Step B while preserving the position update.
- Fallback means unsafe/unobservable clock refinement, not single-UE synchronization improvement.

## Safe Claims
- C7 candidate outputs are non-final human-review diagnostics.
- Step B / LM-only is the comparison baseline.
- C7 improves localization on the bounded network grid.
- C7 uses a non-truth single-UE synchronization safeguard.
- Single-UE fallback rows preserve Step B synchronization by reverting unsafe clock/drift updates.
- Sparse clock-sweep outputs were generated only for four bounded clock-standard-deviation points.

## Unsafe Claims
- C7 outputs are manuscript-ready.
- C7 validates final manuscript figures.
- The covariance method uses dense block or cross-covariance.
- Sparse clock-sweep behavior proves full legacy clock-sweep behavior.
- Single-UE C7 improves synchronization rather than preserving Step B via fallback.

## Output Links
- Metadata JSON: [outputs/c7_candidate_figures/metadata.json](../c7_candidate_figures/metadata.json)
- Combined raw CSV: [outputs/c7_candidate_figures/raw.csv](../c7_candidate_figures/raw.csv)
- Summary CSV: [outputs/c7_candidate_figures/summary.csv](../c7_candidate_figures/summary.csv)
- Arrays NPZ: [outputs/c7_candidate_figures/arrays.npz](../c7_candidate_figures/arrays.npz)
- Notes: [outputs/c7_candidate_figures/network_size_notes.md](../c7_candidate_figures/network_size_notes.md)
- Notes: [outputs/c7_candidate_figures/clock_sweep_notes.md](../c7_candidate_figures/clock_sweep_notes.md)

## Figures
- PDF: [outputs/c7_candidate_figures/plots/c7_network_localization_vs_satellites.pdf](../c7_candidate_figures/plots/c7_network_localization_vs_satellites.pdf)
  PNG: [outputs/c7_candidate_figures/plots/c7_network_localization_vs_satellites.png](../c7_candidate_figures/plots/c7_network_localization_vs_satellites.png)
- PDF: [outputs/c7_candidate_figures/plots/c7_network_synchronization_vs_satellites.pdf](../c7_candidate_figures/plots/c7_network_synchronization_vs_satellites.pdf)
  PNG: [outputs/c7_candidate_figures/plots/c7_network_synchronization_vs_satellites.png](../c7_candidate_figures/plots/c7_network_synchronization_vs_satellites.png)
- PDF: [outputs/c7_candidate_figures/plots/c7_clock_sweep_localization.pdf](../c7_candidate_figures/plots/c7_clock_sweep_localization.pdf)
  PNG: [outputs/c7_candidate_figures/plots/c7_clock_sweep_localization.png](../c7_candidate_figures/plots/c7_clock_sweep_localization.png)
- PDF: [outputs/c7_candidate_figures/plots/c7_clock_sweep_synchronization.pdf](../c7_candidate_figures/plots/c7_clock_sweep_synchronization.pdf)
  PNG: [outputs/c7_candidate_figures/plots/c7_clock_sweep_synchronization.png](../c7_candidate_figures/plots/c7_clock_sweep_synchronization.png)
- PDF: [outputs/c7_candidate_figures/plots/c7_fallback_annotations.pdf](../c7_candidate_figures/plots/c7_fallback_annotations.pdf)
  PNG: [outputs/c7_candidate_figures/plots/c7_fallback_annotations.png](../c7_candidate_figures/plots/c7_fallback_annotations.png)
- PDF: [outputs/c7_candidate_figures/plots/c7_ratio_summary.pdf](../c7_candidate_figures/plots/c7_ratio_summary.pdf)
  PNG: [outputs/c7_candidate_figures/plots/c7_ratio_summary.png](../c7_candidate_figures/plots/c7_ratio_summary.png)

## Recommendation For Human Review
Human review of bounded C7 network-size candidate figures and sparse clock-sweep failure evidence. Do not run a denser clock sweep until the high-clock-standard-deviation localization instability is explained.
