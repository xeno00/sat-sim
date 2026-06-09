# C7 Candidate Network Size Notes

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
- Rows: `12`.
- Position improved: `12/12`.
- Synchronization improved: `9/12`.
- Fallback count: `3`.

## Fallback Rows
- `{'num_users': 1, 'num_satellites': 4, 'clock_std_seconds': '', 'fallback_reason': 'single_user_clock_update_not_observable'}`
- `{'num_users': 1, 'num_satellites': 8, 'clock_std_seconds': '', 'fallback_reason': 'single_user_clock_update_not_observable'}`
- `{'num_users': 1, 'num_satellites': 12, 'clock_std_seconds': '', 'fallback_reason': 'single_user_clock_update_not_observable'}`
- Fallback reverts UE clock, satellite clock, and drift updates to Step B while preserving the position update.
- Fallback means unsafe/unobservable clock refinement, not single-UE synchronization improvement.
