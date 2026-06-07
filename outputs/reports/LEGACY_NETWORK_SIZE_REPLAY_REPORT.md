# Legacy-Compatible Network-Size Replay Report

## Executive Summary
This bounded smoke replay generated legacy-compatible localization and synchronization graphs versus number of satellites. It is diagnostic only, not manuscript-ready, and not a full reproduction of the notebook's manuscript figure grid.

## Generated Plots
- [Localization PDF](../legacy_replay/network_size/pos_vary_ues.pdf)
- [Synchronization PDF](../legacy_replay/network_size/sync_vary_ues.pdf)

## Raw Outputs
- [Raw CSV](../legacy_replay/network_size/legacy_network_size_raw.csv)
- [Arrays NPZ](../legacy_replay/network_size/legacy_network_size_arrays.npz)
- [Metadata JSON](../legacy_replay/network_size/legacy_network_size_metadata.json)

## What The Plots Mean
The plots exercise the safe extracted legacy staged algorithm path on a tiny deterministic network-size smoke grid. They are useful for visual regression and failure/fallback accounting, not for TAES submission.

## Caveats
- `bounded_smoke_replay_only`: True
- `all_clock_symbolic_state`: True
- `v24_gauging_absent`: True
- `truth_error_acceptance_gates_used`: True
- `legacy_sync_metric_averages_all_clock_symbols`: True
- `not_claimed_to_match_manuscript_figures`: True
- `first_user_row_without_cooperation_convention_not_used_in_this_smoke`: True
