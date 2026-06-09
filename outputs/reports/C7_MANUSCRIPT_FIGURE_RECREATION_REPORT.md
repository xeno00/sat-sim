# C7 Manuscript Figure Recreation Report

## Executive Summary
- Verdict: **PASS WITH CAVEAT**.
- Outputs are candidate-only, non-final, and not manuscript-ready.
- Notebook source was inspected but not executed.
- Stage A/B/C package path was used; legacy truth-gated MAP/EKF was not used as primary evidence.
- Clock-sweep status: `candidate_failed_or_diagnostic_only`.

## Algorithm Path
- Stage A: without cooperation / DL-only / coarse baseline.
- Stage B: Step B / LM-only JCLS.
- Stage C: C7 `step_c7_residual_cov_sync_safeguard`.
- C7 covariance terminology: typed block-extracted, diagonal-clipped residual-scaled covariance.

## Single-UE Semantics
- `N_u=1` rows are used only for without-cooperation baseline data.
- Cooperative JCLS curves use `N_u=3,5,7`.

## Runtime / Cache
- Planned rows: `56`.
- Failed rows: `0`.
- Current run wall time: `0.149` seconds.
- Completed cache entries: `56`.
- Sum of cached row runtimes: `27.340` seconds.
- Cache root: `outputs/c7_manuscript_figure_recreation/cache`.

## Figures
- fig4: [PDF](../c7_manuscript_figure_recreation/plots/fig4_c7_localization_vs_satellites.pdf) / [PNG](../c7_manuscript_figure_recreation/plots/fig4_c7_localization_vs_satellites.png)
- fig5: [PDF](../c7_manuscript_figure_recreation/plots/fig5_c7_synchronization_vs_satellites.pdf) / [PNG](../c7_manuscript_figure_recreation/plots/fig5_c7_synchronization_vs_satellites.png)
- fig6: [PDF](../c7_manuscript_figure_recreation/plots/fig6_c7_localization_vs_clock_std.pdf) / [PNG](../c7_manuscript_figure_recreation/plots/fig6_c7_localization_vs_clock_std.png)
- fig7: [PDF](../c7_manuscript_figure_recreation/plots/fig7_c7_synchronization_vs_clock_std.pdf) / [PNG](../c7_manuscript_figure_recreation/plots/fig7_c7_synchronization_vs_clock_std.png)

## Data Links
- [Raw CSV](../c7_manuscript_figure_recreation/raw.csv)
- [Summary CSV](../c7_manuscript_figure_recreation/summary.csv)
- [Arrays NPZ](../c7_manuscript_figure_recreation/arrays.npz)
- [Metadata JSON](../c7_manuscript_figure_recreation/metadata.json)
- [RUN_STATUS.json](../c7_manuscript_figure_recreation/RUN_STATUS.json)
- [ROW_STATUS.jsonl](../c7_manuscript_figure_recreation/ROW_STATUS.jsonl)
- [CACHE_MANIFEST.md](../c7_manuscript_figure_recreation/CACHE_MANIFEST.md)

## Safe Claims
- Outputs are candidate-only and non-final.
- The runner uses package-native Stage A/B/C with C7 as the Stage 3 candidate.
- Single-UE rows are not treated as cooperative JCLS.

## Unsafe Claims
- These figures are manuscript-ready.
- Clock-sweep behavior is validated if high-clock rows remain unstable.
- Legacy truth-gated MAP/EKF is primary evidence.

## Recommendation
Human review of candidate network-size plots and clock-sweep failure/diagnostic behavior.
