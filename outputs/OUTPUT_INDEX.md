# Output Index

## Executive Summary
Canonical graph-package outputs now live under `outputs/`. Existing `v24_*` folders remain as legacy/provenance paths.

## Folders
| Folder | Contains | Safe to cite? | Safe to delete/regenerate? |
|---|---|---:|---:|
| `outputs/gallery` | PNG previews and browsable Markdown/HTML/JSON gallery | False | True |
| `outputs/legacy_replay` | legacy-compatible replay graphs and raw diagnostics | False | True |
| `outputs/package_diagnostic` | package diagnostic aliases/status only | False | True |
| `outputs/manuscript_candidate` | candidate-only graph provenance/status | False | True |
| `outputs/human_review` | human-review diagnostics/status | False | True |
| `outputs/cache` | validated replay cache/checkpoint entries | False | True |
| `outputs/reports` | human-readable reports and machine JSON | False | True |

## Current Best Graphs
- [Corrected LOS localization CRLB replay](legacy_replay/crlb_los/pos_crlb_0dB_0dB.pdf) - legacy replay, not V24-clean
- [Corrected LOS synchronization CRLB replay](legacy_replay/crlb_los/sync_crlb_0dB_0dB.pdf) - legacy replay, not V24-clean
- [Full legacy clock-sweep localization replay](legacy_replay/clock_sweep_full/pos_vary_clock.pdf) - legacy replay, unverified match
- [Full legacy clock-sweep synchronization replay](legacy_replay/clock_sweep_full/sync_vary_clock.pdf) - legacy replay, unverified match
- [Legacy-compatible network-size localization smoke replay](legacy_replay/network_size/pos_vary_ues.pdf) - bounded smoke legacy replay, unverified match
- [Legacy-compatible network-size synchronization smoke replay](legacy_replay/network_size/sync_vary_ues.pdf) - bounded smoke legacy replay, unverified match

## Legacy/Provenance Paths
- `v24_notebook_regression_outputs` remains for provenance; prefer canonical `outputs/` links for review.
- `v24_plot_gallery` remains for provenance; prefer canonical `outputs/` links for review.
- `v24_figure_outputs` remains for provenance; prefer canonical `outputs/` links for review.
- `v24_manuscript_candidate_outputs` remains for provenance; prefer canonical `outputs/` links for review.
- `v24_human_review_outputs` remains for provenance; prefer canonical `outputs/` links for review.
