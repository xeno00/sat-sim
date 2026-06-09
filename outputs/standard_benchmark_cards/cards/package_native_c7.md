# Benchmark Card: package_native_c7

## Status
- Case: `std_nu3_ns10_fullmesh_los_clock1us_seed0`
- Readiness: `human_review_only`
- Units status: `units_consistent`
- Recommended use: `v24_clean_backup_reference`
- Non-final: true
- Manuscript-ready: false

## Stage Metrics

| stage | available | position error [m] | sync error [ns] | missing reason |
|---|---:|---:|---:|---|
| initialization | False | missing | missing | package_native_c7_pre_step_initialization_metrics_not_reported |
| step_a | True | 1105.15 | 937.214 |  |
| step_b | True | 4289.81 | 3882.06 |  |
| step_c | True | 4287.92 | 3879.79 |  |

## Truth Use
No truth is used for estimator decisions; truth is used only for offline metrics.

## Safe Claims
- package_native_c7 produced a bounded single-trial card for std_nu3_ns10_fullmesh_los_clock1us_seed0.
- Truth-use, units, readiness, and missing-stage semantics are recorded in the card.

## Unsafe Claims
- This is not a manuscript figure, sweep, Monte Carlo result, or final evidence.
- One primary-standard fingerprint does not establish robustness.

## Next Action
Review benchmark card and implement remaining planned adapters before downselect.
