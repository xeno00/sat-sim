# Output Index

## Executive Summary
Canonical graph-package outputs now live under `outputs/`. Existing `v24_*` folders remain as legacy/provenance paths.

## Folders
| Folder | Contains | Safe to cite? | Safe to delete/regenerate? |
|---|---|---:|---:|
| `outputs/gallery` | PNG previews and browsable Markdown/HTML/JSON gallery | False | True |
| `outputs/legacy_replay` | legacy-compatible replay graphs and raw diagnostics | False | True |
| `outputs/package_diagnostic` | package diagnostic aliases/status only | False | True |
| `outputs/manuscript_candidate` | candidate-only graph provenance/status | False | True |
| `outputs/human_review` | human-review diagnostics/status | False | True |
| `outputs/migration_baseline` | frozen legacy behavior baseline for controlled migration comparisons | False | True |
| `outputs/migration_ladder` | controlled legacy-to-V24 migration step outputs | False | True |
| `outputs/cache` | validated replay cache/checkpoint entries | False | True |
| `outputs/reports` | human-readable reports and machine JSON | False | True |

## Current Best Graphs
- [Corrected LOS localization CRLB replay](legacy_replay/crlb_los/pos_crlb_0dB_0dB.pdf) - legacy replay, not V24-clean
- [Corrected LOS synchronization CRLB replay](legacy_replay/crlb_los/sync_crlb_0dB_0dB.pdf) - legacy replay, not V24-clean
- [Full legacy clock-sweep localization replay](legacy_replay/clock_sweep_full/pos_vary_clock.pdf) - legacy replay, unverified match
- [Full legacy clock-sweep synchronization replay](legacy_replay/clock_sweep_full/sync_vary_clock.pdf) - legacy replay, unverified match
- [Legacy-compatible network-size localization medium replay](legacy_replay/network_size_medium/pos_vary_ues.pdf) - medium legacy replay, unverified match
- [Legacy-compatible network-size synchronization medium replay](legacy_replay/network_size_medium/sync_vary_ues.pdf) - medium legacy replay, unverified match
- [Migration Step A localization medium replay](migration_ladder/step_a_no_display_smoothing/medium/pos_vary_ues.pdf) - controlled Migration Step A, non-final
- [Migration Step A synchronization medium replay](migration_ladder/step_a_no_display_smoothing/medium/sync_vary_ues.pdf) - controlled Migration Step A, non-final
- [Migration Step B localization medium replay](migration_ladder/step_b_lm_residual_acceptance/medium/pos_vary_ues.pdf) - controlled Migration Step B, non-final
- [Migration Step B synchronization medium replay](migration_ladder/step_b_lm_residual_acceptance/medium/sync_vary_ues.pdf) - controlled Migration Step B, non-final
- [Migration Step C0 localization medium replay](migration_ladder/step_c0_legacy_map_instrumented/medium/pos_vary_ues.pdf) - controlled Migration Step C0, non-final
- [Migration Step C0 synchronization medium replay](migration_ladder/step_c0_legacy_map_instrumented/medium/sync_vary_ues.pdf) - controlled Migration Step C0, non-final
- [Migration Step C1 localization medium replay](migration_ladder/step_c1_legacy_cov_observable_acceptance/medium/pos_vary_ues.pdf) - controlled Migration Step C1, non-final
- [Migration Step C1 synchronization medium replay](migration_ladder/step_c1_legacy_cov_observable_acceptance/medium/sync_vary_ues.pdf) - controlled Migration Step C1, non-final
- [Migration Step C2 localization medium replay](migration_ladder/step_c2_observable_cov_legacy_acceptance/medium/pos_vary_ues.pdf) - controlled Migration Step C2, non-final
- [Migration Step C2 synchronization medium replay](migration_ladder/step_c2_observable_cov_legacy_acceptance/medium/sync_vary_ues.pdf) - controlled Migration Step C2, non-final
- [Migration Step C3 diag prior localization medium replay](migration_ladder/step_c3_cov_diag_prior/medium/pos_vary_ues.pdf) - controlled Migration Step C3 diag prior, non-final
- [Migration Step C3 diag prior synchronization medium replay](migration_ladder/step_c3_cov_diag_prior/medium/sync_vary_ues.pdf) - controlled Migration Step C3 diag prior, non-final
- [Migration Step C3 block diag localization medium replay](migration_ladder/step_c3_cov_block_diag/medium/pos_vary_ues.pdf) - controlled Migration Step C3 block diag, non-final
- [Migration Step C3 block diag synchronization medium replay](migration_ladder/step_c3_cov_block_diag/medium/sync_vary_ues.pdf) - controlled Migration Step C3 block diag, non-final
- [Migration Step C3 damped inverse localization medium replay](migration_ladder/step_c3_cov_damped_inverse/medium/pos_vary_ues.pdf) - controlled Migration Step C3 damped inverse, non-final
- [Migration Step C3 damped inverse synchronization medium replay](migration_ladder/step_c3_cov_damped_inverse/medium/sync_vary_ues.pdf) - controlled Migration Step C3 damped inverse, non-final
- [Migration Step C3 damped pinv localization medium replay](migration_ladder/step_c3_cov_damped_pinv/medium/pos_vary_ues.pdf) - controlled Migration Step C3 damped pinv, non-final
- [Migration Step C3 damped pinv synchronization medium replay](migration_ladder/step_c3_cov_damped_pinv/medium/sync_vary_ues.pdf) - controlled Migration Step C3 damped pinv, non-final
- [Migration Step C3 residual scaled localization medium replay](migration_ladder/step_c3_cov_residual_scaled/medium/pos_vary_ues.pdf) - controlled Migration Step C3 residual scaled, non-final
- [Migration Step C3 residual scaled synchronization medium replay](migration_ladder/step_c3_cov_residual_scaled/medium/sync_vary_ues.pdf) - controlled Migration Step C3 residual scaled, non-final

## Legacy/Provenance Paths
- `v24_notebook_regression_outputs` remains for provenance; prefer canonical `outputs/` links for review.
- `v24_plot_gallery` remains for provenance; prefer canonical `outputs/` links for review.
- `v24_figure_outputs` remains for provenance; prefer canonical `outputs/` links for review.
- `v24_manuscript_candidate_outputs` remains for provenance; prefer canonical `outputs/` links for review.
- `v24_human_review_outputs` remains for provenance; prefer canonical `outputs/` links for review.
