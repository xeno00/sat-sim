# jcls_sim Pipeline Schema Implementation Report

Generated: 2026-06-09

## Executive Summary

The schema-only `jcls_sim` pipeline and benchmark layer is implemented. It adds canonical dataclasses, a four-pipeline registry, primary/secondary standard-case definitions, and a no-execution runner stub. No simulations were run, no figures were generated, and no benchmark-card results were created.

## Implemented Package Layer

- `jcls_sim/pipelines/specs.py`
- `jcls_sim/pipelines/registry.py`
- `jcls_sim/pipelines/__init__.py`
- `jcls_sim/benchmark/standard_cases.py`
- `jcls_sim/benchmark/runner.py`
- `jcls_sim/benchmark/__init__.py`

## Registered Pipeline IDs

| pipeline_id | readiness | recommended_use | implementation_status |
|---|---|---|---|
| `legacy_surgical_prior_region` | `candidate_nonfinal` | `pursue_as_primary_after_normalized_validation` | `adapter_planned` |
| `controlled_migration_step_b_lm_only` | `human_review_only` | `defensible_step_b_backbone` | `adapter_planned` |
| `package_native_c7` | `human_review_only` | `v24_clean_backup_reference` | `adapter_planned` |
| `legacy_truth_gated_l0_reference_only` | `legacy_reference_only` | `provenance_reference_only_not_manuscript_evidence` | `deprecated` |

## Standard Cases

| case_id | role |
|---|---|
| `std_nu3_ns10_fullmesh_los_clock1us_seed0` | `primary_standard` |
| `std_nu3_ns4_fullmesh_los_clock1us_seed0` | `secondary_low_satellite_stress` |

## Adapter Status

No execution adapters are implemented in this schema-only layer. `jcls_sim.benchmark.runner.run_pipeline(...)` raises `NotImplementedError` and must not fabricate benchmark results.

## Next Step

Implement the normalized primary benchmark-card runner and the first execution adapters against this schema. Start with a package-native C7 adapter, then add a legacy-surgical adapter boundary that keeps legacy notebook execution hooks out of core `jcls_sim`.
