# Result Registry

The mandatory lineage and units review is the authoritative bookkeeping artifact for result provenance:

- [RESULT_VERSION_LINEAGE_AND_UNITS_REVIEW.md](../reports/RESULT_VERSION_LINEAGE_AND_UNITS_REVIEW.md)
- [RESULT_VERSION_LINEAGE_AND_UNITS_REVIEW.json](../reports/RESULT_VERSION_LINEAGE_AND_UNITS_REVIEW.json)

Every new result family must include a pipeline tuple, unit verdict, readiness status, and recommended-use status before it is discussed as evidence.

## Registered Families
| result_family | output_root | system_model_version | stage_a_version | stage_b_version | stage_c_version | units_status | readiness | recommended_use |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| original_notebook_manuscript_results | Work-In-Progress/Figures/GeneratePSFrag | legacy_all_clock_notebook | A0_legacy_il_clockless_preconditioning | B0_legacy_lm_truth_gate | C0_legacy_truth_cov_ekf | units_uncertain | quarantine_until_reconciled | legacy_reference_only |
| legacy_clock_sweep_replay | outputs/legacy_replay/clock_sweep_full | legacy_all_clock_notebook | A0_legacy_il_clockless_preconditioning | B0_legacy_lm_truth_gate | C0_legacy_truth_cov_ekf | units_consistent_but_legacy | legacy_reference_only | legacy_reference_only |
| legacy_network_size_replay | outputs/legacy_replay/network_size_medium | legacy_all_clock_notebook | A0_legacy_il_clockless_preconditioning | B0_legacy_lm_truth_gate | C0_legacy_truth_cov_ekf | units_consistent_but_legacy | legacy_reference_only | legacy_reference_only |
| legacy_crlb_los_replay | outputs/legacy_replay/crlb_los | legacy_all_clock_crlb | not_applicable | not_applicable | not_applicable | units_consistent_but_legacy | legacy_reference_only | legacy_reference_only |
| step_b_lm_only_results | outputs/migration_ladder/step_b_lm_residual_acceptance/medium | legacy_compatible_all_clock | A0_legacy_il_clockless_preconditioning | B1_residual_lm | C_none_or_legacy_fallback_disabled_for_lm_only_readout | units_consistent_but_legacy | use_for_human_review | use_for_human_review |
| c7_residual_cov_sync_safeguard | outputs/step_c7_residual_cov_sync_safeguard | package_native_current | A1_package_dl_only | B1_residual_lm | C7_residual_cov_sync_safeguard | units_consistent | use_for_human_review | use_for_human_review |
| c7_candidate_figure_validation | outputs/c7_candidate_figures | package_native_current | A1_package_dl_only | B1_residual_lm | C7_residual_cov_sync_safeguard | units_consistent | use_for_human_review | use_for_human_review |
| c7_manuscript_figure_recreation | outputs/c7_manuscript_figure_recreation | package_native_current_manuscript_style_geometry | A1_package_dl_only | B1_residual_lm | C7_residual_cov_sync_safeguard | units_consistent | use_for_human_review | use_for_human_review |
| wave_results_exploration | not_found | unknown | unknown | unknown | unknown | units_uncertain | quarantine_until_reconciled | do_not_use |
| package_native_suspect_fig4_7_outputs | v24_figure_outputs | package_native_current_synthetic_static | A1_package_dl_only | B1_residual_lm | generic_dynamic_sci_sfi | units_consistent | quarantine_until_reconciled | use_for_debugging_only |
| manuscript_candidate_geometry_noise_outputs | v24_manuscript_candidate_outputs | package_native_mit_stata_leo_synthetic | A1_package_dl_only | B1_residual_lm | generic_dynamic_sci_sfi | units_consistent | quarantine_until_reconciled | use_for_debugging_only |
| human_review_fig4_7_outputs | v24_human_review_outputs | package_native_human_review | A1_package_dl_only | B1_residual_lm | generic_dynamic_sci_sfi | units_consistent | quarantine_until_reconciled | use_for_debugging_only |
| gnss_baseline_exploration | not_found | unknown | unknown | unknown | unknown | units_uncertain | quarantine_until_reconciled | do_not_use |
