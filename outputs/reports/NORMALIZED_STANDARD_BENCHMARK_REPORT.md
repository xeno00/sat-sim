# Normalized Standard Benchmark Report

## Executive Summary
- Benchmark execution run: yes
- Case: `std_nu3_ns10_fullmesh_los_clock1us_seed0`
- Output root: [outputs/standard_benchmark_cards](../standard_benchmark_cards)
- Artifact status: non-final benchmark-card output, not manuscript-ready.

## Adapter Status

| pipeline | adapter status | available stages | missing reasons |
|---|---|---|---|
| `controlled_migration_step_b_lm_only` | `planned_unavailable` | none | controlled_step_b_adapter_not_executable_without_legacy_runner |
| `legacy_surgical_prior_region` | `planned_unavailable` | none | legacy_surgical_adapter_not_integrated_on_main |
| `legacy_truth_gated_l0_reference_only` | `planned_unavailable` | none | truth_gated_provenance_adapter_not_executed_for_benchmark_cards |
| `package_native_c7` | `adapter_available` | step_a; step_b; step_c | package_native_c7_pre_step_initialization_metrics_not_reported |

## Primary Standard-Case Results

| pipeline | Step A pos [m] | Step B pos [m] | Step C pos [m] | Step A sync [ns] | Step B sync [ns] | Step C sync [ns] |
|---|---:|---:|---:|---:|---:|---:|
| `controlled_migration_step_b_lm_only` | missing | missing | missing | missing | missing | missing |
| `legacy_surgical_prior_region` | missing | missing | missing | missing | missing | missing |
| `legacy_truth_gated_l0_reference_only` | missing | missing | missing | missing | missing | missing |
| `package_native_c7` | 1105.15 | 4289.81 | 4287.92 | 937.214 | 3882.06 | 3879.79 |

## Step B vs Step C
- `package_native_c7`: Step C improves position over Step B and improves synchronization over Step B on this one primary card.

## Next Action
Implement the controlled Step B and legacy-surgical adapter boundaries, then rerun this same primary benchmark-card command.
