# Minimal Legacy Corrected Manuscript-Style Figures Report

> Non-final sparse candidate figures. Not manuscript-ready. Not for submission.

## Executive Summary

- Plotting layer: `scripts/minimal_legacy_corrected_jcls.py --plot-sparse-figures`.
- Source data: `outputs/minimal_legacy_corrected/sparse_manuscript/raw.csv`.
- Figure root: `outputs/minimal_legacy_corrected/sparse_manuscript/manuscript_style_figures`.
- Style: IEEE-sized serif plots adapted from the notebook `ieee_flexible_plot` helper.
- Data treatment: sparse raw data plotted directly; no smoothing/fitting/PSFrag generation.

## Figure Traceability

| manuscript figure | manuscript label | legacy artifact | candidate outputs |
|---|---|---|---|
| Fig. 4 | `fig:pos_sats` | `pos_vary_ues.pdf` | `outputs/minimal_legacy_corrected/sparse_manuscript/manuscript_style_figures/fig4_pos_vary_ues_sparse_candidate.pdf`, `outputs/minimal_legacy_corrected/sparse_manuscript/manuscript_style_figures/fig4_pos_vary_ues_sparse_candidate.png` |
| Fig. 5 | `fig:sync_sats` | `sync_vary_ues.pdf` | `outputs/minimal_legacy_corrected/sparse_manuscript/manuscript_style_figures/fig5_sync_vary_ues_sparse_candidate.pdf`, `outputs/minimal_legacy_corrected/sparse_manuscript/manuscript_style_figures/fig5_sync_vary_ues_sparse_candidate.png` |
| Fig. 6 | `fig:pos_clocks` | `pos_vary_clock.pdf` | `outputs/minimal_legacy_corrected/sparse_manuscript/manuscript_style_figures/fig6_pos_vary_clock_sparse_candidate.pdf`, `outputs/minimal_legacy_corrected/sparse_manuscript/manuscript_style_figures/fig6_pos_vary_clock_sparse_candidate.png` |
| Fig. 7 | `fig:sync_clocks` | `sync_vary_clock.pdf` | `outputs/minimal_legacy_corrected/sparse_manuscript/manuscript_style_figures/fig7_sync_vary_clock_sparse_candidate.pdf`, `outputs/minimal_legacy_corrected/sparse_manuscript/manuscript_style_figures/fig7_sync_vary_clock_sparse_candidate.png` |

## Caveats

- These are non-final sparse candidate figures for human review only.
- Fig. 4/5 use the sparse Step A N_u=3 curve as the without-cooperation reference because the sparse run did not include N_u=1.
- Synchronization metric remains legacy all-clock pending V24 reference-relative recompute.
- The sparse run used one seed and no Monte Carlo averaging.

## Truth-Use Ledger

- `truth_used_for_prior_construction`: `True`
- `truth_used_for_initialization`: `False`
- `truth_used_for_lm_acceptance`: `False`
- `truth_used_for_step_c_acceptance`: `False`
- `truth_used_for_covariance`: `False`
- `truth_used_for_fallback_or_reversion`: `False`
- `truth_used_for_offline_metrics`: `True`

## Units Ledger

- `clock_sigma_input_units`: `seconds`
- `internal_clock_state_units`: `legacy range-equivalent km`
- `internal_position_units`: `km`
- `localization_error_units`: `m`
- `measurement_covariance_units`: `legacy km^2/range-domain covariance`
- `measurement_units`: `km`
- `synchronization_error_units`: `ns`
- `units_status`: `units_consistent_but_legacy`
