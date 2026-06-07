# Current Graph Status

## Executive Summary
legacy-compatible graphs are best available for visual review; none are manuscript-ready

## Best Available Graphs for Human Review
- [Corrected LOS localization CRLB replay](../legacy_replay/crlb_los/pos_crlb_0dB_0dB.pdf) - legacy replay, not V24-clean
- [Corrected LOS synchronization CRLB replay](../legacy_replay/crlb_los/sync_crlb_0dB_0dB.pdf) - legacy replay, not V24-clean
- [Full legacy clock-sweep localization replay](../legacy_replay/clock_sweep_full/pos_vary_clock.pdf) - legacy replay, unverified match
- [Full legacy clock-sweep synchronization replay](../legacy_replay/clock_sweep_full/sync_vary_clock.pdf) - legacy replay, unverified match
- [Legacy-compatible network-size localization smoke replay](../legacy_replay/network_size/pos_vary_ues.pdf) - bounded smoke legacy replay, unverified match
- [Legacy-compatible network-size synchronization smoke replay](../legacy_replay/network_size/sync_vary_ues.pdf) - bounded smoke legacy replay, unverified match

## Suspect/Broken Graphs
- `v24_human_review_outputs`: package-native human-review Fig. 4--7 path can degrade at later JCLS stages; preserve as suspect diagnostics only
- `v24_figure_outputs`: package-native diagnostics are not legacy-compatible and not best available

## Warnings
- No graph is manuscript-ready.
- Legacy CRLB is all-clock/post-hoc and not V24-clean.
- Legacy estimator replays use truth-gated acceptance behavior and all-clock synchronization metrics.
