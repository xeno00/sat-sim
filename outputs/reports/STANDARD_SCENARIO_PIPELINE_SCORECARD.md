# Standard Scenario Pipeline Scorecard

Generated: 2026-06-09

Primary standard case:

`std_nu3_ns10_fullmesh_los_clock1us_seed0`

Secondary stress case:

`std_nu3_ns4_fullmesh_los_clock1us_seed0`

The secondary low-satellite case is useful for observability stress testing, but it is not a substitute for the primary universal fingerprint.

## Primary-Case Performance Table

Missing entries are intentionally left as `missing`; no secondary-case values are substituted into primary fields.

| pipeline_id | system_model_version | stage_a_version | stage_b_version | stage_c_version | truth_usage_summary | units_status | readiness | standard_case_id | initialization_pos_error_m | step_a_pos_error_m | step_b_pos_error_m | step_c_pos_error_m | initialization_sync_error_ns | step_a_sync_error_ns | step_b_sync_error_ns | step_c_sync_error_ns | available_from_existing_outputs | requires_new_run | notes |
|---|---|---|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| legacy_truth_gated_l0 | legacy_all_clock_notebook | A0_legacy_il | B0_legacy_lm_truth_gate | C0_legacy_truth_cov_ekf | truth used for LM/MAP acceptance and covariance | units_consistent_but_legacy | legacy_reference_only | std_nu3_ns10_fullmesh_los_clock1us_seed0 | missing | 566.248829 | 0.074408 | 0.074408 | missing | 1253.462631 | 491.942392 | 491.942392 | yes | no | Provenance anchor only; not defensible as manuscript evidence. |
| legacy_clock_sweep_full_replay | legacy_all_clock_notebook | A0_legacy_il | B0_legacy_lm_truth_gate | C0_legacy_truth_cov_ekf | legacy truth gates/fallbacks preserved | units_consistent_but_legacy | legacy_reference_only | std_nu3_ns10_fullmesh_los_clock1us_seed0 | missing | 463.678518 | 0.149857 | 0.034051 | missing | 638.383078 | 43.522044 | 43.522040 | yes | no | Replayed full clock sweep at sigma_delta=1 us; legacy-only. |
| legacy_network_size_replay | legacy_all_clock_notebook | A0_legacy_il | B0_legacy_lm_truth_gate | C0_legacy_truth_cov_ekf | legacy truth gates/fallbacks preserved | units_consistent_but_legacy | legacy_reference_only | std_nu3_ns10_fullmesh_los_clock1us_seed0 | missing | missing | missing | missing | missing | missing | missing | missing | no | yes | Existing medium replay uses sigma_delta=0.5 ns, not primary 1 us. |
| controlled_migration_step_b_lm_only | legacy_compatible_all_clock | A0_legacy_il | B1_residual_trust_region_lm_no_truth_gate | C_none | no truth-state LM acceptance; truth used only for metrics | units_consistent_but_legacy | human_review_only | std_nu3_ns10_fullmesh_los_clock1us_seed0 | missing | missing | missing | missing | missing | missing | missing | missing | no | yes | Strong on matching legacy behavior, but no primary Ns=10/1us card on main. |
| c7_candidate_figure_validation | package_native_current | A1_package_dl_only | B1_residual_lm | C7_residual_cov_sync_safeguard | no truth-state acceptance; no truth-derived covariance | units_consistent | human_review_only | std_nu3_ns10_fullmesh_los_clock1us_seed0 | missing | missing | missing | missing | missing | missing | missing | missing | no | yes | Candidate validation has nearby network rows and clock-sweep rows, but not the exact primary network card. |
| c7_manuscript_figure_recreation | package_native_current | A1_package_dl_only | B1_residual_lm | C7_residual_cov_sync_safeguard | truth only for offline metrics | units_consistent | human_review_only | std_nu3_ns10_fullmesh_los_clock1us_seed0 | missing | 374.932087 | 88.912645 | 77.485398 | missing | 925.389093 | 82.722672 | 71.859692 | yes | no | Clean but much weaker than legacy-like paths; clock-sweep instability remains. |
| legacy_surgical_truth_gate_removal | legacy_compatible_all_clock | A0_legacy_il | B1_residual_trust_region_lm_no_truth_gate | C_surgical_residual_scaled_info_map | truth gates removed; truth only for metrics | units_consistent_but_legacy | human_review_only | std_nu3_ns10_fullmesh_los_clock1us_seed0 | missing | 566.248829 | 0.074408 | 0.135403 | missing | 1253.462631 | 492.006386 | 492.006383 | yes | no | Stage B is excellent; Stage C worsens localization in this card. |
| legacy_surgical_prior_region_r0_10m | legacy_compatible_all_clock | A0_prior_region_il | B1_residual_trust_region_lm_no_truth_gate | C_surgical_residual_scaled_info_map | truth used for simulation prior construction and metrics, not estimator decisions | units_consistent_but_legacy | human_review_only | std_nu3_ns10_fullmesh_los_clock1us_seed0 | missing | 566.249140 | 0.074450 | 0.095342 | missing | 1253.462631 | 492.182515 | 492.182508 | yes | no | Best current bridge from legacy behavior to non-truth estimator decisions. |
| legacy_surgical_prior_region_r0_100m | legacy_compatible_all_clock | A0_prior_region_il | B1_residual_trust_region_lm_no_truth_gate | C_surgical_residual_scaled_info_map | truth used for simulation prior construction and metrics, not estimator decisions | units_consistent_but_legacy | human_review_only | std_nu3_ns10_fullmesh_los_clock1us_seed0 | missing | 566.249140 | 0.074450 | 0.090972 | missing | 1253.462631 | 490.856450 | 490.856449 | yes | no | Similar to R0=10m; Stage C barely affects synchronization. |
| legacy_surgical_prior_region_r0_100000m | legacy_compatible_all_clock | A0_prior_region_il | B1_residual_trust_region_lm_no_truth_gate | C_surgical_residual_scaled_info_map | truth used for simulation prior construction and metrics, not estimator decisions | units_consistent_but_legacy | human_review_only | std_nu3_ns10_fullmesh_los_clock1us_seed0 | missing | 566.249140 | 0.074450 | 0.036237 | missing | 1253.462631 | 491.153146 | 491.153144 | yes | no | Only listed prior-region card where Stage C improves localization over Step B; needs robustness review. |
| gnss_baseline_exploration | baseline_exploration | missing | missing | missing | unknown from main; parked branch | unknown | debugging_only | std_nu3_ns10_fullmesh_los_clock1us_seed0 | missing | missing | missing | missing | missing | missing | missing | missing | no | yes | Parked branch; lineage/units integration missing on main. |
| wave_results_exploration | wave_exploration | missing | missing | missing | unknown from main; parked branch | unknown | debugging_only | std_nu3_ns10_fullmesh_los_clock1us_seed0 | missing | missing | missing | missing | missing | missing | missing | missing | no | yes | Parked branch; not part of current manuscript-result downselect. |

## Secondary Low-Satellite Stress Case

| pipeline_id | standard_case_id | step_a_pos_error_m | step_b_pos_error_m | step_c_pos_error_m | step_a_sync_error_ns | step_b_sync_error_ns | step_c_sync_error_ns | notes |
|---|---|---:|---:|---:|---:|---:|---:|---|
| c7_residual_cov_sync_safeguard | std_nu3_ns4_fullmesh_los_clock1us_seed0 | missing | available in C7 medium grid but not primary | available in C7 medium grid but not primary | missing | available in C7 medium grid but not primary | available in C7 medium grid but not primary | Useful stress case only; do not use as primary fingerprint. |
| prior C7 contradiction | std_nu3_ns4_fullmesh_los_clock1us_seed0 | missing | centimeter-scale diagnostic in one path | tens/hundreds-meter in manuscript recreation path | missing | inconsistent | inconsistent | Contradiction is anchored to secondary stress case and remains unresolved until normalized Ns=10 benchmark card exists. |

## Score Rubric

Scores are 0 to 5, where 5 is strongest. For `amount_of_remaining_work`, 5 means least remaining work.

| pipeline_id | performance_primary | sync_primary | manuscript_theory_compat | absence_algorithmic_truth_use | units_gauge_consistency | reproducibility_caching | simplicity | readiness_for_figures | reviewer_defensibility | amount_of_remaining_work | recommended_use |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| legacy_truth_gated_l0 | 5 | 4 | 1 | 0 | 2 | 3 | 3 | 1 | 0 | 1 | legacy_reference_only |
| controlled_migration_step_b_lm_only | 4 | 3 | 3 | 4 | 3 | 4 | 5 | 3 | 4 | 4 | pursue_as_primary_subpath |
| legacy_surgical_prior_region | 5 | 3 | 3 | 4 | 3 | 4 | 4 | 4 | 4 | 3 | pursue_as_primary |
| legacy_surgical_truth_gate_removal | 5 | 3 | 3 | 4 | 3 | 4 | 4 | 3 | 4 | 3 | pursue_as_backup |
| c7_package_native | 2 | 3 | 5 | 5 | 5 | 4 | 3 | 2 | 4 | 2 | pursue_as_backup |
| c7_manuscript_figure_recreation | 2 | 3 | 5 | 5 | 5 | 4 | 3 | 2 | 3 | 2 | human_review_only |
| legacy_replays | 5 | 4 | 1 | 0 | 2 | 3 | 2 | 1 | 1 | 1 | legacy_reference_only |
| gnss_wave_explorations | missing | missing | missing | missing | missing | missing | 2 | 0 | 1 | 1 | debugging_only |

## Downselect

Primary path to pursue:

`legacy_compatible_all_clock + A0_prior_region_il + B1_residual_trust_region_lm_no_truth_gate + C_surgical_residual_scaled_info_map`, with Step B residual LM as the evidentiary backbone and Step C treated as candidate refinement until normalized robustness checks pass.

Backup path:

`package_native_current + A1_package_dl_only + B1_residual_lm + C7_residual_cov_sync_safeguard`, retained as the theory-clean backup and code-consistency reference.

Minimal next run:

Build a normalized benchmark-card runner for `std_nu3_ns10_fullmesh_los_clock1us_seed0` that runs the selected legacy-surgical prior-region path, controlled Step B LM-only, and package-native C7 under identical geometry, clock, noise, metric, and reporting conventions.
