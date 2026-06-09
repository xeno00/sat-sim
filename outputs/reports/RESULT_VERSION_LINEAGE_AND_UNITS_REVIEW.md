# Result Version Lineage and Units Review

## Executive Summary
This is the first-stop bookkeeping artifact for generated results. It records the system-model/stage tuple, truth usage, unit status, and current-use decision for each major result family. No listed family is manuscript-ready.

- Result families covered: `13`
- Standard benchmark label: `std_nu3_ns10_fullmesh_los_clock1us_seed0`
- Secondary low-satellite stress case: `std_nu3_ns4_fullmesh_los_clock1us_seed0`
- Units-consistent families: `6`
- Units-uncertain families: `3`
- Quarantined/debug-only/not-use families: `6`

## Result Lineage Table
| result_family | output_root | branch | commit | generating_script | system_model_version | stage_a_version | stage_b_version | stage_c_version | pipeline_class | truth_usage | units_status | standard_case_id | standard_case_stage_a_pos_m | standard_case_stage_b_pos_m | standard_case_stage_c_pos_m | standard_case_stage_a_sync_ns | standard_case_stage_b_sync_ns | standard_case_stage_c_sync_ns | primary_standard_case_id | primary_standard_status | primary_standard_stage_a_pos_m | primary_standard_stage_b_pos_m | primary_standard_stage_c_pos_m | primary_standard_stage_a_sync_ns | primary_standard_stage_b_sync_ns | primary_standard_stage_c_sync_ns | secondary_low_sat_case_id | secondary_low_sat_case_role | secondary_low_sat_status | secondary_low_sat_stage_a_pos_m | secondary_low_sat_stage_b_pos_m | secondary_low_sat_stage_c_pos_m | secondary_low_sat_stage_a_sync_ns | secondary_low_sat_stage_b_sync_ns | secondary_low_sat_stage_c_sync_ns | rough_performance_tag | readiness | recommended_use | quarantine_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| original_notebook_manuscript_results | Work-In-Progress/Figures/GeneratePSFrag | manual_manuscript_storage | not_git_tracked | JCLS_Simulation.ipynb original figure cells | legacy_all_clock_notebook | A0_legacy_il_clockless_preconditioning | B0_legacy_lm_truth_gate | C0_legacy_truth_cov_ekf | legacy_final_artifact | truth gates/covariance suspected from legacy notebook path; exact manuscript artifact lineage not fully executable | units_uncertain | std_nu3_ns10_fullmesh_los_clock1us_seed0 | unknown | unknown | unknown | unknown | unknown | unknown | std_nu3_ns10_fullmesh_los_clock1us_seed0 | unknown_needs_review | unknown | unknown | unknown | unknown | unknown | unknown | std_nu3_ns4_fullmesh_los_clock1us_seed0 | secondary_low_satellite_stress_case | not_applicable | unknown | unknown | unknown | unknown | unknown | unknown | unknown | quarantine_until_reconciled | legacy_reference_only | Manuscript artifacts predate the current tested provenance stack and mix legacy all-clock/truth-gated behavior. |
| legacy_clock_sweep_replay | outputs/legacy_replay/clock_sweep_full | codex/legacy-clock-sweep-replay | unknown_not_recorded | scripts/replay_legacy_clock_sweep_figures.py --full | legacy_all_clock_notebook | A0_legacy_il_clockless_preconditioning | B0_legacy_lm_truth_gate | C0_legacy_truth_cov_ekf | legacy | truth-error LM/MAP acceptance and legacy fallbacks used; full notebook not executed | units_consistent_but_legacy | std_nu3_ns10_fullmesh_los_clock1us_seed0 | 463.679 | 0.149857 | 0.0340513 | 638.383 | 43.522 | 43.522 | std_nu3_ns10_fullmesh_los_clock1us_seed0 | available | 463.679 | 0.149857 | 0.0340513 | 638.383 | 43.522 | 43.522 | std_nu3_ns4_fullmesh_los_clock1us_seed0 | secondary_low_satellite_stress_case | not_applicable | unknown | unknown | unknown | unknown | unknown | unknown | legacy clock sweep reproduces executable behavior but uses oracle gates/fallbacks | legacy_reference_only | legacy_reference_only | Truth-gated acceptance, all-clock state, and legacy synchronization metric are unsafe for V24 evidence. |
| legacy_network_size_replay | outputs/legacy_replay/network_size_medium | codex/legacy-network-size-and-v24-port-plan | 093fbdf | scripts/replay_legacy_network_size_figures.py --medium | legacy_all_clock_notebook | A0_legacy_il_clockless_preconditioning | B0_legacy_lm_truth_gate | C0_legacy_truth_cov_ekf | legacy | truth gates/fallbacks used in legacy estimator path | units_consistent_but_legacy | std_nu3_ns10_fullmesh_los_clock1us_seed0 | unknown | unknown | unknown | unknown | unknown | unknown | std_nu3_ns10_fullmesh_los_clock1us_seed0 | missing_needs_benchmark_run | unknown | unknown | unknown | unknown | unknown | unknown | std_nu3_ns4_fullmesh_los_clock1us_seed0 | secondary_low_satellite_stress_case | not_applicable | unknown | unknown | unknown | unknown | unknown | unknown | legacy medium replay improves JCLS in 9/9 baseline comparisons | legacy_reference_only | legacy_reference_only | Legacy all-clock/truth-gated path is provenance, not V24-clean evidence. |
| legacy_crlb_los_replay | outputs/legacy_replay/crlb_los | codex/legacy-crlb-figure-replay | unknown_not_recorded | scripts/replay_legacy_crlb_figures.py | legacy_all_clock_crlb | not_applicable | not_applicable | not_applicable | legacy_diagnostic | no estimator truth gate, but all-clock/post-hoc CRLB slicing preserved | units_consistent_but_legacy | not_applicable_crlb_curve | unknown | unknown | unknown | unknown | unknown | unknown | std_nu3_ns10_fullmesh_los_clock1us_seed0 | not_applicable | unknown | unknown | unknown | unknown | unknown | unknown | std_nu3_ns4_fullmesh_los_clock1us_seed0 | secondary_low_satellite_stress_case | not_applicable | unknown | unknown | unknown | unknown | unknown | unknown | legacy CRLB replay; not V24-clean | legacy_reference_only | legacy_reference_only | All-clock/post-hoc CRLB path is incompatible with current V24 gauged FIM requirements. |
| step_b_lm_only_results | outputs/migration_ladder/step_b_lm_residual_acceptance/medium | codex/migration-step-b-lm-no-truth-gate | unknown_not_recorded | scripts/run_controlled_migration_ladder.py --step step_b_lm_residual_acceptance --medium | legacy_compatible_all_clock | A0_legacy_il_clockless_preconditioning | B1_residual_lm | C_none_or_legacy_fallback_disabled_for_lm_only_readout | diagnostic | LM truth acceptance removed; later legacy MAP fields in CSV are not used as Step B evidence | units_consistent_but_legacy | std_nu3_ns10_fullmesh_los_clock1us_seed0 | unknown | unknown | unknown | unknown | unknown | unknown | std_nu3_ns10_fullmesh_los_clock1us_seed0 | missing_needs_benchmark_run | unknown | unknown | unknown | unknown | unknown | unknown | std_nu3_ns4_fullmesh_los_clock1us_seed0 | secondary_low_satellite_stress_case | available | 0.67259 | 0.213194 | unknown | 0.536919 | 0.133519 | unknown | healthy clean baseline on controlled migration grid; primary Nu=3,Ns=10 benchmark missing | use_for_human_review | use_for_human_review |  |
| c7_residual_cov_sync_safeguard | outputs/step_c7_residual_cov_sync_safeguard | codex/step-c7-residual-cov-sync-safeguard | 89a9b2a | scripts/run_step_c7_residual_cov_sync_safeguard.py | package_native_current | A1_package_dl_only | B1_residual_lm | C7_residual_cov_sync_safeguard | diagnostic | truth used only for offline metrics; no truth acceptance/covariance/safeguard | units_consistent | std_nu3_ns10_fullmesh_los_clock1us_seed0 | unknown | unknown | unknown | unknown | unknown | unknown | std_nu3_ns10_fullmesh_los_clock1us_seed0 | missing_needs_benchmark_run | unknown | unknown | unknown | unknown | unknown | unknown | std_nu3_ns4_fullmesh_los_clock1us_seed0 | secondary_low_satellite_stress_case | available | unknown | 2.38546 | 0.0393877 | unknown | 0.81504 | 0.104365 | medium-grid diagnostic is healthy, but primary Nu=3,Ns=10 benchmark is missing | use_for_human_review | use_for_human_review |  |
| c7_candidate_figure_validation | outputs/c7_candidate_figures | codex/c7-candidate-figure-validation | 04ba189 | scripts/run_c7_candidate_figures.py | package_native_current | A1_package_dl_only | B1_residual_lm | C7_residual_cov_sync_safeguard | candidate | truth used only for offline metrics; no truth acceptance/covariance/safeguard | units_consistent | std_nu3_ns10_fullmesh_los_clock1us_seed0 | unknown | unknown | unknown | unknown | unknown | unknown | std_nu3_ns10_fullmesh_los_clock1us_seed0 | missing_needs_benchmark_run | unknown | unknown | unknown | unknown | unknown | unknown | std_nu3_ns4_fullmesh_los_clock1us_seed0 | secondary_low_satellite_stress_case | not_applicable | unknown | unknown | unknown | unknown | unknown | unknown | network mean ratios pos=0.054160465424072914, sync=0.38561149595048044; clock sweep blocked | use_for_human_review | use_for_human_review | Sparse clock-sweep localization instability blocks manuscript use. |
| c7_manuscript_figure_recreation | outputs/c7_manuscript_figure_recreation | codex/c7-manuscript-figure-recreation | 0e6300b | scripts/run_c7_manuscript_figure_recreation.py | package_native_current_manuscript_style_geometry | A1_package_dl_only | B1_residual_lm | C7_residual_cov_sync_safeguard | candidate | truth used only for offline metrics; no truth acceptance/covariance/safeguard; notebook not executed | units_consistent | std_nu3_ns10_fullmesh_los_clock1us_seed0 | unknown | 88.9126 | 77.4854 | unknown | 82.7227 | 71.8597 | std_nu3_ns10_fullmesh_los_clock1us_seed0 | available | unknown | 88.9126 | 77.4854 | unknown | 82.7227 | 71.8597 | std_nu3_ns4_fullmesh_los_clock1us_seed0 | secondary_low_satellite_stress_case | available | unknown | 184.979 | 180.203 | unknown | 308.754 | 315.584 | network-size figures human-review only; clock sweep candidate failed | use_for_human_review | use_for_human_review | Clock-sweep family remains diagnostic/candidate-failed because high-clock rows worsen localization. |
| wave_results_exploration | not_found | not_found | not_found | not_found | unknown | unknown | unknown | unknown | not_found | unknown | units_uncertain | std_nu3_ns10_fullmesh_los_clock1us_seed0 | unknown | unknown | unknown | unknown | unknown | unknown | std_nu3_ns10_fullmesh_los_clock1us_seed0 | unknown_needs_review | unknown | unknown | unknown | unknown | unknown | unknown | std_nu3_ns4_fullmesh_los_clock1us_seed0 | secondary_low_satellite_stress_case | not_applicable | unknown | unknown | unknown | unknown | unknown | unknown | no wave-results output root found in repository inventory | quarantine_until_reconciled | do_not_use | Required family name was requested, but no matching output artifacts were found. |
| package_native_suspect_fig4_7_outputs | v24_figure_outputs | codex/package-native-figures-4-7 | unknown_not_recorded | scripts/run_package_native_figures_4_7.py | package_native_current_synthetic_static | A1_package_dl_only | B1_residual_lm | generic_dynamic_sci_sfi | diagnostic | truth used only for offline metrics, but algorithm fidelity unresolved | units_consistent | unknown_needs_review | unknown | unknown | unknown | unknown | unknown | unknown | std_nu3_ns10_fullmesh_los_clock1us_seed0 | missing_needs_benchmark_run | unknown | unknown | unknown | unknown | unknown | unknown | std_nu3_ns4_fullmesh_los_clock1us_seed0 | secondary_low_satellite_stress_case | not_applicable | unknown | unknown | unknown | unknown | unknown | unknown | package-native suspect Fig. 4-7 diagnostics conflict with manuscript narrative | quarantine_until_reconciled | use_for_debugging_only | Synthetic geometry/noise and algorithm fidelity were unresolved; outputs are suspect diagnostics only. |
| manuscript_candidate_geometry_noise_outputs | v24_manuscript_candidate_outputs | codex/manuscript-geometry-noise | unknown_not_recorded | scripts/run_v24_manuscript_candidate_figures.py | package_native_mit_stata_leo_synthetic | A1_package_dl_only | B1_residual_lm | generic_dynamic_sci_sfi | candidate | truth used only for offline metrics, but estimator robustness unresolved | units_consistent | unknown_needs_review | unknown | unknown | unknown | unknown | unknown | unknown | std_nu3_ns10_fullmesh_los_clock1us_seed0 | missing_needs_benchmark_run | unknown | unknown | unknown | unknown | unknown | unknown | std_nu3_ns4_fullmesh_los_clock1us_seed0 | secondary_low_satellite_stress_case | not_applicable | unknown | unknown | unknown | unknown | unknown | unknown | closer geometry/noise, still not final | quarantine_until_reconciled | use_for_debugging_only | Synthetic satellite geometry, estimator robustness, and numerical behavior remain unresolved. |
| human_review_fig4_7_outputs | v24_human_review_outputs | codex/human-ready-figures-sprint | unknown_not_recorded | scripts/run_human_review_figures.py | package_native_human_review | A1_package_dl_only | B1_residual_lm | generic_dynamic_sci_sfi | diagnostic | truth used only for offline metrics; not final | units_consistent | unknown_needs_review | unknown | unknown | unknown | unknown | unknown | unknown | std_nu3_ns10_fullmesh_los_clock1us_seed0 | missing_needs_benchmark_run | unknown | unknown | unknown | unknown | unknown | unknown | std_nu3_ns4_fullmesh_los_clock1us_seed0 | secondary_low_satellite_stress_case | not_applicable | unknown | unknown | unknown | unknown | unknown | unknown | human-review package conflicts with manuscript narrative in several regimes | quarantine_until_reconciled | use_for_debugging_only | JCLS success rates were low and refined JCLS could underperform baseline. |
| gnss_baseline_exploration | not_found | not_found | not_found | not_found | unknown | unknown | unknown | unknown | not_found | unknown | units_uncertain | std_nu3_ns10_fullmesh_los_clock1us_seed0 | unknown | unknown | unknown | unknown | unknown | unknown | std_nu3_ns10_fullmesh_los_clock1us_seed0 | unknown_needs_review | unknown | unknown | unknown | unknown | unknown | unknown | std_nu3_ns4_fullmesh_los_clock1us_seed0 | secondary_low_satellite_stress_case | not_applicable | unknown | unknown | unknown | unknown | unknown | unknown | no GNSS/baseline exploration output root found in repository inventory | quarantine_until_reconciled | do_not_use | Required family was requested if present; no matching output artifacts were found. |

## Units Review

### legacy_notebook_and_legacy_replays
- Unit-risk verdict: `units_consistent_but_legacy`
- Position units: UE `km`, satellite `km`, output `m`, conversion `legacy position error km multiplied by 1000 where plotting/reporting expects meters`.
- Clock units: state `range-equivalent km`, sigma input `seconds in notebook clock-sweep inputs`, sigma internal `range-equivalent km after speed-of-light conversion in legacy logic`, output `seconds/raw or ns/plotted depending on replay`, conversion `range-equivalent km divided by c_km_per_s, then multiplied by 1e9 for ns plots`.
- Measurement units: vector `km`, model `km`, covariance `km^2`, Jacobian `position columns dimensionless; clock columns dimensionless for range-equivalent clocks`.
- Notes: Executable fixtures verified row order and km/range-clock representation for tiny cases, but legacy all-clock/truth-gated behavior remains unsafe.

### package_native_current_and_c7
- Unit-risk verdict: `units_consistent`
- Position units: UE `km`, satellite `km`, output `m`, conversion `position_error_m reports Euclidean km error multiplied by 1000`.
- Clock units: state `range-equivalent km`, sigma input `seconds or ns in figure configs, converted before range-domain simulation`, sigma internal `range-equivalent km`, output `seconds internally, ns for plotted/reported figure metrics`, conversion `gauge-relative range-km error divided by c_km_per_s; ns uses *1e9`.
- Measurement units: vector `km`, model `km`, covariance `km^2 from sigma_km^2`, Jacobian `position columns dimensionless direction cosines; clock columns dimensionless range-km derivatives`.
- Notes: Package tests cover km-to-meter position output and gauge-relative clock metrics; C7 reports raw km and plotted ns explicitly.

### package_native_suspect_v24_figures
- Unit-risk verdict: `units_consistent`
- Position units: UE `km`, satellite `km`, output `m`, conversion `reported as meters in metadata/summary`.
- Clock units: state `range-equivalent km`, sigma input `figure-config dependent`, sigma internal `range-equivalent km`, output `seconds/ns depending on figure family`, conversion `package metric conversion as above`.
- Measurement units: vector `km`, model `km`, covariance `km^2`, Jacobian `package range-domain Jacobian`.
- Notes: Units appear consistent, but system model and algorithm fidelity are suspect; do not cite as evidence.

### original_manuscript_artifacts
- Unit-risk verdict: `units_uncertain`
- Position units: UE `unknown from artifact alone`, satellite `unknown from artifact alone`, output `m in manuscript-style labels`, conversion `unknown_needs_review`.
- Clock units: state `unknown from artifact alone`, sigma input `seconds/ns depending on figure`, sigma internal `unknown_needs_review`, output `ns in labels`, conversion `unknown_needs_review`.
- Measurement units: vector `unknown_needs_review`, model `unknown_needs_review`, covariance `unknown_needs_review`, Jacobian `unknown_needs_review`.
- Notes: The PDF artifacts alone do not prove the execution path or units; keep as manuscript artifacts, not code evidence.

### wave_or_gnss_missing
- Unit-risk verdict: `units_uncertain`
- Position units: UE `unknown`, satellite `unknown`, output `unknown`, conversion `unknown`.
- Clock units: state `unknown`, sigma input `unknown`, sigma internal `unknown`, output `unknown`, conversion `unknown`.
- Measurement units: vector `unknown`, model `unknown`, covariance `unknown`, Jacobian `unknown`.
- Notes: No matching wave-results or GNSS/baseline exploration output roots were found.

## Version Combination Tuples
| pipeline_tuple | implemented | has_benchmark_card | reproduces_legacy | candidate_final | quarantined | notes |
| --- | --- | --- | --- | --- | --- | --- |
| legacy_all_clock + A0_legacy_il + B0_legacy_lm_truth_gate + C0_legacy_truth_cov_ekf | True | True | True | False | True | Use as legacy reference only; truth gates and all-clock metrics are unsafe for V24 evidence. |
| legacy_compatible_all_clock + A0_legacy_il + B1_residual_lm + C_none | True | True | False | False | False | Current clean Step B/LM-only baseline for human review. |
| package_native_current + A1_package_dl_only + B1_residual_lm + C_none | True | True | False | False | False | Used as baseline in C7 candidate validation. |
| package_native_current + A1_package_dl_only + B1_residual_lm + C7_residual_cov_sync_safeguard | True | True | False | False | False | Ready for human graph review only; not manuscript-ready. |
| gauge_fixed + A2_gauge_fixed_dl_only + B2_gauge_fixed_residual_lm + C7_residual_cov_sync_safeguard | False | False | False | False | True | Recognized future tuple; not implemented as a distinct result family. |

## Contradictions and Quarantine Decisions

### c7_centimeter_vs_manuscript_recreation_meter_scale
- Source A: `outputs/step_c7_residual_cov_sync_safeguard/raw.csv Nu=3,Ns=4`
- Source B: `outputs/c7_manuscript_figure_recreation/raw.csv network Nu=3,Ns=4 refined_jcls`
- Numerical mismatch: C7 diagnostic Stage C position 0.0393877 m versus C7 manuscript recreation Stage C position 180.203 m; ratio about 4575.11
- Likely cause: This older contradiction is anchored to the secondary low-satellite stress case, not the primary universal benchmark. The rows are not a controlled same-system benchmark: diagnostic medium uses a small deterministic validation setup, while manuscript recreation uses notebook-inspired figure-family settings, different geometry/noise/clock assumptions, and manuscript-style output semantics.
- Quarantine decision: Treat the contradiction as unresolved secondary-stress evidence only; do not use it as the primary-standard comparison.
- Next diagnostic action: Run the normalized primary benchmark std_nu3_ns10_fullmesh_los_clock1us_seed0 through both pipelines before making any primary-standard claim.

### legacy_clock_sweep_good_behavior_vs_c7_clock_sweep_instability
- Source A: `outputs/legacy_replay/clock_sweep_full/legacy_clock_sweep_metadata.json`
- Source B: `outputs/c7_candidate_figures/metadata.json and outputs/c7_manuscript_figure_recreation/metadata.json`
- Numerical mismatch: Legacy replay reports refined position below 0.06 m at all seven clock points after truth-gated fallback behavior; C7 bounded/sparse clock-sweep reports candidate-failed localization at high clock standard deviation.
- Likely cause: Legacy uses all-clock state, truth-error acceptance/fallback behavior, all-clock synchronization metric, and smoothing/fitting transforms; C7 uses non-truth safeguards and package-native metrics.
- Quarantine decision: Use legacy clock sweep as reference only and C7 clock sweep as debugging evidence only.
- Next diagnostic action: Run a normalized clock-sweep benchmark with raw Stage A/B/C metrics, no smoothing, and explicit clock-unit conversion audit.

### jcls_label_mixes_stage_tuples
- Source A: `legacy replay labels coarse/refined JCLS`
- Source B: `package-native and C7 labels coarse/refined JCLS`
- Numerical mismatch: Same label can refer to legacy truth-gated all-clock MAP, Step B LM-only, generic dynamic SCI/SFI, or C7 residual-covariance safeguard.
- Likely cause: Historical figure labels are algorithm-stage labels, not full pipeline tuple identifiers.
- Quarantine decision: Every new result must include the explicit system/A/B/C tuple before being discussed as evidence.
- Next diagnostic action: Add pipeline tuple labels to future summary CSV/metadata and figure notes.

### manuscript_ready_claim_absent_but_outputs_exist
- Source A: `all inspected report JSON files`
- Source B: `generated PDF outputs`
- Numerical mismatch: No inspected current output claims manuscript_ready=true, but many PDFs resemble manuscript figures.
- Likely cause: Diagnostic and candidate plots intentionally mimic figure families for review.
- Quarantine decision: Do not cite any generated PDF unless its lineage row is promoted by human signoff.
- Next diagnostic action: Keep RESULT_VERSION_LINEAGE_AND_UNITS_REVIEW as the first lookup before discussing figures.

## Standard Benchmark Section
The primary universal benchmark label is `std_nu3_ns10_fullmesh_los_clock1us_seed0`.

The primary standard case is defined as `N_u=3`, `N_s=10`, full-mesh sidelinks, LOS/Rician where supported, manuscript-like MIT/Stata UE geometry and Starlink-like LEO geometry where supported, clock standard deviation `1 microsecond`, seed `0`, operation time `0.5 s` when Stage C/dynamic update is available, and one trial for the standard fingerprint.

Rationale:
- it matches the manuscript clock-sweep network size.
- it is large enough that ordinary low-satellite observability failures should not dominate the fingerprint.
- it gives each pipeline a fairer chance to show intended JCLS behavior.
- it is still small enough to run quickly as a one-row standard benchmark.
- it directly tests the regime where the manuscript claims strong JCLS behavior.

The old `std_nu3_ns4_fullmesh_los_clock1us_seed0` benchmark is retained only as `secondary_low_satellite_stress_case`. It remains useful for low-satellite observability stress testing, but it is no longer the primary universal fingerprint.

If a pipeline lacks the primary `N_u=3,N_s=10` row, `primary_standard_status` is marked `missing_needs_benchmark_run`, `unsupported`, `not_applicable`, or `unknown_needs_review`. The secondary low-satellite row is never substituted into the primary fields.

Next required diagnostic: build normalized benchmark-card runner for `std_nu3_ns10_fullmesh_los_clock1us_seed0`.

## Current-Use Decision
| result_family | current_use_status | decision | reason |
| --- | --- | --- | --- |
| original_notebook_manuscript_results | legacy_reference_only | Do not use as manuscript evidence. | Manuscript artifacts predate the current tested provenance stack and mix legacy all-clock/truth-gated behavior. |
| legacy_clock_sweep_replay | legacy_reference_only | Do not use as manuscript evidence. | Truth-gated acceptance, all-clock state, and legacy synchronization metric are unsafe for V24 evidence. |
| legacy_network_size_replay | legacy_reference_only | Do not use as manuscript evidence. | Legacy all-clock/truth-gated path is provenance, not V24-clean evidence. |
| legacy_crlb_los_replay | legacy_reference_only | Do not use as manuscript evidence. | All-clock/post-hoc CRLB path is incompatible with current V24 gauged FIM requirements. |
| step_b_lm_only_results | use_for_human_review | Use only with explicit caveats. | healthy clean baseline on controlled migration grid; primary Nu=3,Ns=10 benchmark missing |
| c7_residual_cov_sync_safeguard | use_for_human_review | Use only with explicit caveats. | medium-grid diagnostic is healthy, but primary Nu=3,Ns=10 benchmark is missing |
| c7_candidate_figure_validation | use_for_human_review | Use only with explicit caveats. | Sparse clock-sweep localization instability blocks manuscript use. |
| c7_manuscript_figure_recreation | use_for_human_review | Use only with explicit caveats. | Clock-sweep family remains diagnostic/candidate-failed because high-clock rows worsen localization. |
| wave_results_exploration | do_not_use | Do not use as manuscript evidence. | Required family name was requested, but no matching output artifacts were found. |
| package_native_suspect_fig4_7_outputs | use_for_debugging_only | Do not use as manuscript evidence. | Synthetic geometry/noise and algorithm fidelity were unresolved; outputs are suspect diagnostics only. |
| manuscript_candidate_geometry_noise_outputs | use_for_debugging_only | Do not use as manuscript evidence. | Synthetic satellite geometry, estimator robustness, and numerical behavior remain unresolved. |
| human_review_fig4_7_outputs | use_for_debugging_only | Do not use as manuscript evidence. | JCLS success rates were low and refined JCLS could underperform baseline. |
| gnss_baseline_exploration | do_not_use | Do not use as manuscript evidence. | Required family was requested if present; no matching output artifacts were found. |

## Blunt Recommendation
- Currently recommended result family: step_b_lm_only_results and c7_residual_cov_sync_safeguard for human review only; no family is manuscript-ready
- Next diagnostic action: Build a normalized benchmark-card runner for std_nu3_ns10_fullmesh_los_clock1us_seed0, then run Step B and C7 under identical geometry/noise/clock settings before any manuscript evidence claim.
