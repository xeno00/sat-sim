# C7 Candidate Clock Sweep Notes

- Artifact status: non-final candidate validation.
- Manuscript ready: `false`.
- Notebook used: `false`.
- Manuscript directories touched: `false`.
- Human signoff required: `true`.
- Baseline: `Step B / LM-only`.
- C7 covariance: typed block-extracted, diagonal-clipped residual-scaled covariance.
- Truth is used only for offline metrics.
- Synchronization plots use ns; raw rows retain km.

## Summary
- Rows: `4`.
- Position improved: `2/4`.
- Synchronization improved: `2/4`.
- Fallback count: `2`.

## Fallback Rows
- `{'num_users': 3, 'num_satellites': 8, 'clock_std_seconds': 0.0001, 'fallback_reason': 'clock_update_exceeds_covariance_scale'}`
- `{'num_users': 3, 'num_satellites': 8, 'clock_std_seconds': 1e-06, 'fallback_reason': 'clock_update_exceeds_covariance_scale'}`
- Fallback reverts UE clock, satellite clock, and drift updates to Step B while preserving the position update.
- Fallback means unsafe/unobservable clock refinement, not single-UE synchronization improvement.
