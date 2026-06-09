# Benchmark Card: legacy_surgical_prior_region

## Status
- Case: `std_nu3_ns10_fullmesh_los_clock1us_seed0`
- Readiness: `candidate_nonfinal`
- Units status: `units_consistent_but_legacy`
- Recommended use: `pursue_as_primary_after_normalized_validation`
- Non-final: true
- Manuscript-ready: false

## Stage Metrics

| stage | available | position error [m] | sync error [ns] | missing reason |
|---|---:|---:|---:|---|
| initialization | False | missing | missing | legacy_surgical_adapter_not_integrated_on_main |
| step_a | False | missing | missing | legacy_surgical_adapter_not_integrated_on_main |
| step_b | False | missing | missing | legacy_surgical_adapter_not_integrated_on_main |
| step_c | False | missing | missing | legacy_surgical_adapter_not_integrated_on_main |

## Truth Use
Truth is used for simulation prior construction and offline metrics; estimator acceptance, covariance, and fallback decisions are non-truth.

## Safe Claims
- legacy_surgical_prior_region is represented without fabricated metrics.
- Unavailable adapter reason is explicit: legacy_surgical_adapter_not_integrated_on_main.

## Unsafe Claims
- No performance claim is available for this pipeline from this benchmark-card run.
- Missing metrics must not be substituted from legacy or secondary stress cases.

## Next Action
Implement a safe adapter boundary before using this pipeline as benchmark evidence.
