# Legacy Clock-Sweep Full Replay Report

- Status: `legacy_full_replayed_unverified_match`
- Mode: `full`
- Runtime seconds: 7.512
- Output root: `v24_notebook_regression_outputs\executed_legacy\clock_sweep_replay_full`
- Manuscript ready: `False`

## Outputs

- `v24_notebook_regression_outputs\executed_legacy\clock_sweep_replay_full\legacy_clock_sweep_raw.csv`
- `v24_notebook_regression_outputs\executed_legacy\clock_sweep_replay_full\legacy_clock_sweep_summary.csv`
- `v24_notebook_regression_outputs\executed_legacy\clock_sweep_replay_full\legacy_clock_sweep_arrays.npz`
- `v24_notebook_regression_outputs\executed_legacy\clock_sweep_replay_full\pos_vary_clock.pdf`
- `v24_notebook_regression_outputs\executed_legacy\clock_sweep_replay_full\sync_vary_clock.pdf`

## Counts

- `row_count`: 7
- `successful_rows`: 7
- `rows_with_failures`: 0
- `total_fallback_events`: 175
- `il_failures`: 0
- `lm_failures`: 0
- `map_failures`: 0.0
- `map_global_fallback_count`: 175.0

## Caveats

- `truth_centered_initialization`: False
- `true_state_acceptance_gates_used`: True
- `lm_reverts_or_accepts_based_on_true_state_error`: True
- `map_reverts_based_on_true_state_error`: True
- `exceptions_fall_back_to_il_or_previous_state`: True
- `all_clock_symbolic_state`: True
- `v24_gauging_absent`: True
- `smoothing_fitting_manual_transforms_applied`: True
- `legacy_sync_metric_averages_all_clock_symbols`: True
- `classification`: legacy_only_unsafe_for_v24_claims_without_replacement_or_human_review

## Commands

- `python scripts/replay_legacy_clock_sweep_figures.py --smoke`
- `python scripts/replay_legacy_clock_sweep_figures.py --full`
