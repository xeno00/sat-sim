# Benchmark Card: controlled_migration_step_b_lm_only

## Status
- Case: `std_nu3_ns10_fullmesh_los_clock1us_seed0`
- Readiness: `human_review_only`
- Units status: `units_consistent_but_legacy`
- Recommended use: `defensible_step_b_backbone`
- Non-final: true
- Manuscript-ready: false

## Stage Metrics

| stage | available | position error [m] | sync error [ns] | missing reason |
|---|---:|---:|---:|---|
| initialization | False | missing | missing | controlled_step_b_adapter_not_executable_without_legacy_runner |
| step_a | False | missing | missing | controlled_step_b_adapter_not_executable_without_legacy_runner |
| step_b | False | missing | missing | controlled_step_b_adapter_not_executable_without_legacy_runner |
| step_c | False | missing | missing | controlled_step_b_adapter_not_executable_without_legacy_runner |

## Truth Use
Legacy initialization is retained, but LM acceptance is residual/trust-region based; truth is used for offline metrics.

## Safe Claims
- controlled_migration_step_b_lm_only is represented without fabricated metrics.
- Unavailable adapter reason is explicit: controlled_step_b_adapter_not_executable_without_legacy_runner.

## Unsafe Claims
- No performance claim is available for this pipeline from this benchmark-card run.
- Missing metrics must not be substituted from legacy or secondary stress cases.

## Next Action
Implement a safe adapter boundary before using this pipeline as benchmark evidence.
