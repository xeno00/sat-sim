# Current Graph Status

## Executive Summary
legacy-compatible graphs are best available for visual review; none are manuscript-ready

## Best Available Graphs for Human Review
- [Corrected LOS localization CRLB replay](../legacy_replay/crlb_los/pos_crlb_0dB_0dB.pdf) - legacy replay, not V24-clean
- [Corrected LOS synchronization CRLB replay](../legacy_replay/crlb_los/sync_crlb_0dB_0dB.pdf) - legacy replay, not V24-clean
- [Full legacy clock-sweep localization replay](../legacy_replay/clock_sweep_full/pos_vary_clock.pdf) - legacy replay, unverified match
- [Full legacy clock-sweep synchronization replay](../legacy_replay/clock_sweep_full/sync_vary_clock.pdf) - legacy replay, unverified match
- [Legacy-compatible network-size localization medium replay](../legacy_replay/network_size_medium/pos_vary_ues.pdf) - medium legacy replay, unverified match
- [Legacy-compatible network-size synchronization medium replay](../legacy_replay/network_size_medium/sync_vary_ues.pdf) - medium legacy replay, unverified match
- [Migration Step A localization medium replay](../migration_ladder/step_a_no_display_smoothing/medium/pos_vary_ues.pdf) - controlled Migration Step A, non-final
- [Migration Step A synchronization medium replay](../migration_ladder/step_a_no_display_smoothing/medium/sync_vary_ues.pdf) - controlled Migration Step A, non-final
- [Migration Step B localization medium replay](../migration_ladder/step_b_lm_residual_acceptance/medium/pos_vary_ues.pdf) - controlled Migration Step B, non-final
- [Migration Step B synchronization medium replay](../migration_ladder/step_b_lm_residual_acceptance/medium/sync_vary_ues.pdf) - controlled Migration Step B, non-final
- [Migration Step C0 localization medium replay](../migration_ladder/step_c0_legacy_map_instrumented/medium/pos_vary_ues.pdf) - controlled Migration Step C0, non-final
- [Migration Step C0 synchronization medium replay](../migration_ladder/step_c0_legacy_map_instrumented/medium/sync_vary_ues.pdf) - controlled Migration Step C0, non-final
- [Migration Step C1 localization medium replay](../migration_ladder/step_c1_legacy_cov_observable_acceptance/medium/pos_vary_ues.pdf) - controlled Migration Step C1, non-final
- [Migration Step C1 synchronization medium replay](../migration_ladder/step_c1_legacy_cov_observable_acceptance/medium/sync_vary_ues.pdf) - controlled Migration Step C1, non-final
- [Migration Step C2 localization medium replay](../migration_ladder/step_c2_observable_cov_legacy_acceptance/medium/pos_vary_ues.pdf) - controlled Migration Step C2, non-final
- [Migration Step C2 synchronization medium replay](../migration_ladder/step_c2_observable_cov_legacy_acceptance/medium/sync_vary_ues.pdf) - controlled Migration Step C2, non-final
- [Migration Step C3 diag prior localization medium replay](../migration_ladder/step_c3_cov_diag_prior/medium/pos_vary_ues.pdf) - controlled Migration Step C3 diag prior, non-final
- [Migration Step C3 diag prior synchronization medium replay](../migration_ladder/step_c3_cov_diag_prior/medium/sync_vary_ues.pdf) - controlled Migration Step C3 diag prior, non-final
- [Migration Step C3 block diag localization medium replay](../migration_ladder/step_c3_cov_block_diag/medium/pos_vary_ues.pdf) - controlled Migration Step C3 block diag, non-final
- [Migration Step C3 block diag synchronization medium replay](../migration_ladder/step_c3_cov_block_diag/medium/sync_vary_ues.pdf) - controlled Migration Step C3 block diag, non-final
- [Migration Step C3 damped inverse localization medium replay](../migration_ladder/step_c3_cov_damped_inverse/medium/pos_vary_ues.pdf) - controlled Migration Step C3 damped inverse, non-final
- [Migration Step C3 damped inverse synchronization medium replay](../migration_ladder/step_c3_cov_damped_inverse/medium/sync_vary_ues.pdf) - controlled Migration Step C3 damped inverse, non-final
- [Migration Step C3 damped pinv localization medium replay](../migration_ladder/step_c3_cov_damped_pinv/medium/pos_vary_ues.pdf) - controlled Migration Step C3 damped pinv, non-final
- [Migration Step C3 damped pinv synchronization medium replay](../migration_ladder/step_c3_cov_damped_pinv/medium/sync_vary_ues.pdf) - controlled Migration Step C3 damped pinv, non-final
- [Migration Step C3 residual scaled localization medium replay](../migration_ladder/step_c3_cov_residual_scaled/medium/pos_vary_ues.pdf) - controlled Migration Step C3 residual scaled, non-final
- [Migration Step C3 residual scaled synchronization medium replay](../migration_ladder/step_c3_cov_residual_scaled/medium/sync_vary_ues.pdf) - controlled Migration Step C3 residual scaled, non-final
- [Migration Step C4 composite acceptance localization medium replay](../migration_ladder/step_c4_composite_map_acceptance/medium/pos_vary_ues.pdf) - controlled Migration Step C4 composite acceptance, non-final
- [Migration Step C4 composite acceptance synchronization medium replay](../migration_ladder/step_c4_composite_map_acceptance/medium/sync_vary_ues.pdf) - controlled Migration Step C4 composite acceptance, non-final

## Suspect/Broken Graphs
- `v24_human_review_outputs`: package-native human-review Fig. 4--7 path can degrade at later JCLS stages; preserve as suspect diagnostics only
- `v24_figure_outputs`: package-native diagnostics are not legacy-compatible and not best available
- `outputs/step3_low_cost_exploration`: low-cost Step 3 triage/proxy diagnostics only; not figure-ready and not a manuscript output
- `outputs/step3_covariance_exploration`: covariance/dynamics Step 3 diagnostics only; promoted variants require review before any larger validation or estimator integration
- `outputs/step3_residual_cov_failure_audit`: residual-scaled covariance failure audit only; not figure-ready and not a manuscript output
- `outputs/step3_residual_cov_robust_candidates`: residual-scaled robust candidate diagnostics only; not figure-ready and not a manuscript output

## Warnings
- No graph is manuscript-ready.
- Legacy CRLB is all-clock/post-hoc and not V24-clean.
- Legacy estimator replays use truth-gated acceptance behavior and all-clock synchronization metrics.
- Controlled migration ladder outputs preserve legacy behavior first; use them to isolate breaking corrections, not as final figures.
- Low-cost Step 3 exploration did not identify a medium-validation candidate and uses proxy evidence for clock-drift and Schur/nuisance-clock lanes.
- Step 3 covariance exploration uses deterministic sparse diagnostics and promoted-only medium validation; it is not a final figure workflow.
- Step 3 residual covariance robust candidates use bounded medium-grid diagnostics; the best candidate still requires review before estimator integration.
