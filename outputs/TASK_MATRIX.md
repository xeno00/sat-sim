# Task Matrix

## Executive Summary
This sprint used one read-only subagent for the V24 port plan and orchestrator-owned implementation lanes for replay/cache/gallery/report generation. No lane was silently omitted.

| Lane | Owner | Status | Expected outputs | Blocker |
|---|---|---|---|---|
| A - Legacy Network-Size Replay | orchestrator | `orchestrator_completed` | `outputs/legacy_replay/network_size_medium/pos_vary_ues.pdf`, `outputs/legacy_replay/network_size_medium/sync_vary_ues.pdf`, `outputs/reports/LEGACY_NETWORK_SIZE_REPLAY_REPORT.md` |  |
| B - Cache/Runtime | orchestrator | `orchestrator_completed` | `outputs/cache/CACHE_MANIFEST.md`, `outputs/cache/CACHE_MANIFEST.json` |  |
| C - Figure/Gallery | orchestrator | `orchestrator_completed` | `outputs/gallery/PLOT_GALLERY.md`, `outputs/gallery/PLOT_GALLERY.html`, `outputs/gallery/PLOT_GALLERY.json` |  |
| D - V24 Port Plan | Carson | `subagent_completed_orchestrator_integrated` | `outputs/reports/V24_FIGURE_REPLACEMENT_PLAN.md`, `outputs/reports/LEGACY_TO_PACKAGE_PORT_PLAN.md` |  |
| E - Scientific Red-Team | orchestrator | `orchestrator_completed` | `outputs/reports/CURRENT_GRAPH_STATUS.md`, `outputs/reports/V24_FIGURE_REPLACEMENT_PLAN.md` |  |

## Notes
- **A**: Medium replay generated 12 rows under outputs/legacy_replay/network_size_medium with 12 cold cache misses.
- **B**: Per-row cache keys include script/notebook/cell hashes, mode, Nu, Ns, sigma, iterations, seed, schema version, and row hash.
- **C**: Gallery refreshed with network_size_medium previews and canonical graph package reports.
- **D**: Read-only port-plan findings integrated into V24_FIGURE_REPLACEMENT_PLAN and LEGACY_TO_PACKAGE_PORT_PLAN.
- **E**: Current reports classify all outputs as non-final/not manuscript-ready and preserve package-native suspect labels.
