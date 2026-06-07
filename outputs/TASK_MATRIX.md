# Task Matrix

## Executive Summary
All required lanes were either completed by read-only subagents and integrated by the orchestrator or completed directly by the orchestrator. No lane was silently omitted.

| Lane | Owner | Status | Expected outputs | Blocker |
|---|---|---|---|---|
| A - Gallery/Markdown Quality | Maxwell | `subagent_completed_orchestrator_integrated` | `outputs/gallery/PLOT_GALLERY.md`, `outputs/gallery/PLOT_GALLERY.html`, `outputs/gallery/PLOT_GALLERY.json` |  |
| B - Output Structure | orchestrator | `orchestrator_completed` | `outputs/OUTPUT_INDEX.md`, `outputs/OUTPUT_INDEX.json` |  |
| C - CRLB Legend + LOS Replay | Carver | `subagent_completed_orchestrator_integrated` | `outputs/legacy_replay/crlb_los/pos_crlb_0dB_0dB.pdf`, `outputs/legacy_replay/crlb_los/sync_crlb_0dB_0dB.pdf`, `outputs/reports/CRLB_LOS_REPLAY_REPORT.md` |  |
| D - NLOS CRLB | Carver | `subagent_completed_failure_report` | `outputs/reports/CRLB_NLOS_REPORT.md`, `outputs/reports/CRLB_NLOS_REPORT.json` | No executable legacy Rayleigh/NLOS CRLB path or package score-covariance NLOS FIM path exists. |
| E - Legacy-Compatible Positioning Figures | Rawls | `subagent_completed_orchestrator_integrated` | `outputs/legacy_replay/network_size/pos_vary_ues.pdf`, `outputs/legacy_replay/network_size/sync_vary_ues.pdf`, `outputs/reports/LEGACY_NETWORK_SIZE_REPLAY_REPORT.md` | Full 52-row notebook replay remains expensive; this sprint completed bounded smoke only. |
| F - Cache/Checkpoint | orchestrator | `orchestrator_completed` | `outputs/cache/CACHE_MANIFEST.md`, `outputs/cache/CACHE_MANIFEST.json` |  |
| G - Scientific Red-Team | Laplace | `subagent_completed_orchestrator_integrated` | `outputs/reports/CURRENT_GRAPH_STATUS.md`, `outputs/reports/CURRENT_GRAPH_STATUS.json` |  |

## Notes
- **A**: reported broken Markdown/HTML image paths, Windows separators, duplicate status ambiguity; fixes integrated into scripts/render_all_figure_previews.py and tests
- **B**: canonical outputs/ structure and OUTPUT_INDEX generated
- **C**: reported corrected legend convention and LOS caveats; plotter regenerated LOS CRLB PDFs
- **D**: reported NLOS/Rayleigh path is not executable/defensible; precise failure report generated instead of fake graphs
- **E**: mapped notebook cells 28/29 and safe bounded smoke replay; outputs generated under outputs/legacy_replay/network_size
- **F**: network-size replay used row-level cache with 3 cold misses; cache manifest written under outputs/cache
- **G**: reported no graphs manuscript-ready; package-native Fig. 4-7 marked suspect in CURRENT_GRAPH_STATUS
