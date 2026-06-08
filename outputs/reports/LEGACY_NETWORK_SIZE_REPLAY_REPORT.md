# Legacy-Compatible Network-Size Replay Report

## Executive Summary
Mode `medium` generated non-final legacy-compatible localization and synchronization graphs versus number of satellites. These are not manuscript-ready.

## Generated Plots
- [Localization PDF](../legacy_replay/network_size_medium/pos_vary_ues.pdf)
- [Synchronization PDF](../legacy_replay/network_size_medium/sync_vary_ues.pdf)

## Raw Outputs
- [Raw CSV](../legacy_replay/network_size_medium/legacy_network_size_raw.csv)
- [Summary CSV](../legacy_replay/network_size_medium/legacy_network_size_summary.csv)
- [Arrays NPZ](../legacy_replay/network_size_medium/legacy_network_size_arrays.npz)
- [Metadata JSON](../legacy_replay/network_size_medium/legacy_network_size_metadata.json)

## Trend Summary
- JCLS helps localization in 9 of 9 baseline comparisons.
- JCLS helps synchronization in 9 of 9 baseline comparisons.
- Strongest localization improvement: `{'num_users': 7, 'num_satellites': 12, 'position_improvement_m': 0.38934000617619297, 'sync_improvement_ns': 0.49684854894722424, 'position_ratio_jcls_over_baseline': 0.007651016099110989, 'sync_ratio_jcls_over_baseline': 0.2098984711807988}`
- Strongest synchronization improvement: `{'num_users': 5, 'num_satellites': 12, 'position_improvement_m': 0.36845328726804843, 'sync_improvement_ns': 0.5776285528012194, 'position_ratio_jcls_over_baseline': 0.06088704105602458, 'sync_ratio_jcls_over_baseline': 0.08144000093206719}`

## Caveats
- `all_clock_symbolic_state`: True
- `v24_gauging_absent`: True
- `truth_error_acceptance_gates_used`: True
- `legacy_sync_metric_averages_all_clock_symbols`: True
- `single_ue_is_noncooperative_baseline_only`: True
- `not_claimed_to_match_manuscript_figures`: True
