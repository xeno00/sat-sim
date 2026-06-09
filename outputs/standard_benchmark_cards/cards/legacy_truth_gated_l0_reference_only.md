# Benchmark Card: legacy_truth_gated_l0_reference_only

## Status
- Case: `std_nu3_ns10_fullmesh_los_clock1us_seed0`
- Readiness: `legacy_reference_only`
- Units status: `units_consistent_but_legacy`
- Recommended use: `provenance_reference_only_not_manuscript_evidence`
- Non-final: true
- Manuscript-ready: false

## Stage Metrics

| stage | available | position error [m] | sync error [ns] | missing reason |
|---|---:|---:|---:|---|
| initialization | False | missing | missing | truth_gated_provenance_adapter_not_executed_for_benchmark_cards |
| step_a | False | missing | missing | truth_gated_provenance_adapter_not_executed_for_benchmark_cards |
| step_b | False | missing | missing | truth_gated_provenance_adapter_not_executed_for_benchmark_cards |
| step_c | False | missing | missing | truth_gated_provenance_adapter_not_executed_for_benchmark_cards |

## Truth Use
Legacy provenance reference uses truth-centered initialization, truth-gated acceptance/fallback, truth-derived covariance, and offline metrics.

## Safe Claims
- legacy_truth_gated_l0_reference_only is represented without fabricated metrics.
- Unavailable adapter reason is explicit: truth_gated_provenance_adapter_not_executed_for_benchmark_cards.

## Unsafe Claims
- No performance claim is available for this pipeline from this benchmark-card run.
- Missing metrics must not be substituted from legacy or secondary stress cases.

## Next Action
Implement a safe adapter boundary before using this pipeline as benchmark evidence.
