# Experiment Code Location Audit

Generated: 2026-06-09

## Executive Summary

The reusable V24 package code lives mostly in `jcls_sim/`, but most experiment and pipeline definitions still live in `scripts/`. The strongest currently recommended pipeline, the legacy-surgical prior-region path, is implemented as a script-level diagnostic runner rather than a canonical package pipeline. The next normalized benchmark-card runner should therefore not become another ad hoc experiment script. It should call a small canonical `jcls_sim.pipelines` and `jcls_sim.benchmark` interface.

No simulations were run and no figures were generated.

## Git And Worktree State

| item | value |
|---|---|
| branch | `main` |
| current commit at audit start | `b08ceab` |
| main sync | up to date with `origin/main` |
| active worktrees | main, `codex/gps-gnss-baseline-exploration`, `codex/jcls-wave-results-exploration`, `codex/wave-observability-estimator-gap-audit`, `codex/legacy-surgical-prior-region-initialization`, `codex/legacy-surgical-truth-gate-removal` |

## File Classification Summary

### Core package code

| path | classification | notes |
|---|---|---|
| `jcls_sim/algorithm.py` | core_package_code | Package-native estimator stages and C7 reusable implementation. |
| `jcls_sim/bounds.py` | core_package_code | V24 full-gauged bounds and CRLB reportability helpers. |
| `jcls_sim/configs.py` | core_package_code | V24 scenario configuration, links, deterministic configs. |
| `jcls_sim/constants.py` | core_package_code | Speed-of-light constants. |
| `jcls_sim/estimators.py` | core_package_code | Generic weighted normal equations and information-form update helpers. |
| `jcls_sim/figure_generation.py` | pipeline_definition | Package-native figure-family pipeline and plotting helper mixed together. |
| `jcls_sim/fim.py` | core_package_code | FIM and range covariance helpers. |
| `jcls_sim/gauge.py` | core_package_code | V24 clock gauge helpers. |
| `jcls_sim/geometry.py` | core_package_code | Deterministic geometry helpers, including manuscript-like geometry. |
| `jcls_sim/io.py` | cache_helper | JSON conversion helper. |
| `jcls_sim/jacobian.py` | core_package_code | V24 analytic range vector and Jacobian. |
| `jcls_sim/measurements.py` | core_package_code | Measurement order/sign helpers. |
| `jcls_sim/metrics.py` | core_package_code | Position and reference-relative clock metrics. |
| `jcls_sim/migration.py` | pipeline_definition | Migration-step descriptors only; no execution. |
| `jcls_sim/noise.py` | core_package_code | Link budget/range-sigma helpers. |
| `jcls_sim/parameters.py` | core_package_code | V24 parameter names and pack/unpack. |

### Main script families

| script family | classification | examples |
|---|---|---|
| Legacy notebook audits/replays | legacy_replay_script | `audit_notebook_measurements.py`, `replay_legacy_clock_sweep_figures.py`, `replay_legacy_crlb_figures.py`, `replay_legacy_network_size_figures.py`, `run_legacy_notebook_smoke.py` |
| Controlled migration ladder | runner_script | `run_controlled_migration_ladder.py` |
| Step 3 explorations | runner_script | `explore_step3_gates.py`, `benchmark_step3_micro_cases.py`, `explore_step3_covariance.py`, `audit_step3_residual_covariance.py` |
| C7 package/candidate runners | runner_script | `run_step_c7_residual_cov_sync_safeguard.py`, `run_c7_candidate_figures.py`, `run_c7_manuscript_figure_recreation.py` |
| Legacy-surgical runners | runner_script | `run_legacy_surgical_truth_gate_removal.py`, `run_legacy_surgical_prior_region_initialization.py` |
| CRLB diagnostics | runner_script/report_builder | `smoke_v24_crlb.py`, `sweep_v24_crlb.py`, `diagnose_v24_crlb_geometry.py`, `prepare_v24_crlb_figure_candidate.py` |
| Report and gallery builders | report_builder/gallery_builder | `build_result_lineage_units_review.py`, `build_integration_compliance_reports.py`, `render_all_figure_previews.py`, `build_legacy_graph_package.py` |
| Protected/process checks | cache_helper/report_builder | `check_protected_files.py`, `build_integration_compliance_reports.py` |

### Worktree-only scripts

| branch/worktree | script | status |
|---|---|---|
| `codex/gps-gnss-baseline-exploration` | `scripts/run_gnss_baseline_exploration.py` | parked, not on main |
| `codex/jcls-wave-results-exploration` | `scripts/run_wave_results_exploration.py` | parked, not on main |
| `codex/wave-observability-estimator-gap-audit` | `scripts/run_wave_results_exploration.py` | parked/local worktree, not on main |

## Pipeline Family Map

| pipeline_or_experiment_name | current_code_locations | current_runner | current_output_roots | system/stage tuple | truth_usage | units_status | readiness | reusable package code? | should integrate? | recommended_target_module | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| original notebook bridge/extraction | `JCLS_Simulation.ipynb`, replay/audit scripts | `scripts/audit_notebook_measurements.py`, `scripts/run_legacy_notebook_smoke.py` | `v24_notebook_regression_outputs/` | legacy all-clock + legacy stages | legacy truth behavior audited/extracted | units_consistent_but_legacy for tiny fixtures | legacy_reference_only | no | no | keep in `scripts/legacy_*` provenance | Do not port notebook execution into package. |
| legacy clock sweep replay | replay script | `scripts/replay_legacy_clock_sweep_figures.py` | `outputs/legacy_replay/clock_sweep_full` | legacy all-clock + truth-gated LM/MAP | truth gates/fallbacks preserved | units_consistent_but_legacy | legacy_reference_only | no | no | legacy/provenance only | Useful oracle/provenance reference. |
| legacy network-size replay | replay script | `scripts/replay_legacy_network_size_figures.py` | `outputs/legacy_replay/network_size_medium` | legacy all-clock + truth-gated LM/MAP | truth gates preserved | units_consistent_but_legacy | legacy_reference_only | no | no | legacy/provenance only | Existing replay not primary 1us standard. |
| legacy CRLB replay | replay script | `scripts/replay_legacy_crlb_figures.py` | `outputs/legacy_replay/crlb_los`, `outputs/legacy_replay/crlb_nlos` | legacy all-clock CRLB | no estimator gate, but post-hoc slicing | units_consistent_but_legacy | legacy_reference_only | no | no | legacy/provenance only | Preserve as CRLB provenance, not V24 FIM. |
| controlled migration ladder | `jcls_sim/migration.py`, large runner script | `scripts/run_controlled_migration_ladder.py` | `outputs/migration_ladder/` | legacy-compatible all-clock ladder | varies by step | units_consistent_but_legacy | diagnostic/human_review | partial | yes, specs only | `jcls_sim/pipelines/migration.py` | Extract step specs and row schemas; leave CLI/report writing in script. |
| Step B residual LM-only | migration runner | `scripts/run_controlled_migration_ladder.py --step step_b_lm_residual_acceptance` | `outputs/migration_ladder/step_b_lm_residual_acceptance/` | legacy-compatible + B1 residual LM | no truth LM acceptance | units_consistent_but_legacy | human_review_only | partial | yes | `jcls_sim/pipelines/migration.py` | Needed in benchmark runner as Step B backbone. |
| Step C0/C1/C2/C3/C4/C5 | migration and exploration scripts | `scripts/run_controlled_migration_ladder.py`, exploration scripts | `outputs/migration_ladder/`, `outputs/step3_*` | diagnostic variants | varies; some truth-cov/acceptance retained | mixed | debugging_only | no | no, except reusable diagnostics | leave in scripts | Useful for history, not next benchmark. |
| package-native Fig. 4--7 diagnostics | `jcls_sim/figure_generation.py` | `scripts/run_v24_figures_4_7.py` | `v24_figure_outputs`, `v24_human_review_outputs` | package-native A/B/generic C | truth metrics only | units_consistent | suspect/debug | yes | partially | `jcls_sim/pipelines/package_native.py` | Separate pipeline stages from plotting. |
| C7 candidate validation | `jcls_sim/algorithm.py`, `figure_generation.py`, runner | `scripts/run_c7_candidate_figures.py` | `outputs/c7_candidate_figures` | package-native + C7 | no truth acceptance/covariance | units_consistent | human_review_only | yes | yes | `jcls_sim/pipelines/c7.py` | C7 adapter should become package pipeline. |
| C7 manuscript recreation | `jcls_sim/figure_generation.py`, runner | `scripts/run_c7_manuscript_figure_recreation.py` | `outputs/c7_manuscript_figure_recreation` | package-native manuscript-style geometry + C7 | truth metrics only | units_consistent | human_review_only | yes | yes | `jcls_sim/pipelines/c7.py`, `jcls_sim/benchmark/runner.py` | Needs benchmark-card adapter, not plotting-first runner. |
| legacy-surgical truth-gate removal | script-level pipeline specs and legacy namespace hooks | `scripts/run_legacy_surgical_truth_gate_removal.py` | `outputs/legacy_surgical_truth_gate_removal` | legacy-compatible all-clock + nontruth LM/MAP | truth metrics; initialization still truth-centered in this branch | units_consistent_but_legacy | human_review_only | partial | yes, carefully | `jcls_sim/pipelines/legacy_surgical.py` | Extract specs and metadata; keep legacy namespace execution adapter separate. |
| legacy-surgical prior-region initialization | script-level specs and legacy namespace hooks | `scripts/run_legacy_surgical_prior_region_initialization.py` | `outputs/legacy_surgical_prior_region_initialization` | legacy-compatible all-clock + prior region + residual LM + nontruth MAP | truth for prior simulation and metrics only | units_consistent_but_legacy | pursue_as_primary | partial | yes | `jcls_sim/pipelines/legacy_surgical.py`, `jcls_sim/benchmark/standard_cases.py` | Primary integration target. |
| GNSS/baseline exploration | parked worktree only | `scripts/run_gnss_baseline_exploration.py` | branch-only outputs | unknown/baseline | unknown on main | unknown | parked/debugging_only | no | no | parked only | Needs lineage/units before integration. |
| wave-results exploration | parked worktrees only | `scripts/run_wave_results_exploration.py` | branch-only outputs | wave exploration | unknown on main | unknown | parked/debugging_only | no | no | parked only | Not part of current benchmark path. |
| CRLB package-native diagnostics | `jcls_sim/fim.py`, `bounds.py`, scripts | CRLB scripts | `v24_diagnostics/`, `outputs/*crlb*` | V24 gauged FIM | no estimator truth | units_consistent | diagnostic_only | yes | partially | `jcls_sim/benchmark/metrics.py` only if benchmark uses CRLB | Keep CRLB runners separate from estimator benchmark. |

## Immediate Finding

The next benchmark runner needs a package-level pipeline interface before execution. Today, the selected primary pipeline is script-bound, while the backup C7 path is package-bound. Without a common adapter, any benchmark-card script will reintroduce ad hoc schema and truth/units drift.
