# V24 Figure Replacement Plan

## Executive Summary
Use legacy-compatible outputs as visual/provenance evidence only. Port the successful staged-estimation behavior into package-native V24 before manuscript replacement.

No figure is marked manuscript-ready.

| Figure | Classification | Current best visual | Reason |
|---|---|---|---|
| Fig. 2 LOS CRLB localization | legacy_provenance_only, needs_v24_clean_replacement | [outputs/legacy_replay/crlb_los/pos_crlb_0dB_0dB.pdf](../legacy_replay/crlb_los/pos_crlb_0dB_0dB.pdf) | LOS CRLB replay has corrected legends but preserves legacy all-clock/post-hoc bound extraction. |
| Fig. 3 LOS CRLB synchronization | legacy_provenance_only, needs_v24_clean_replacement | [outputs/legacy_replay/crlb_los/sync_crlb_0dB_0dB.pdf](../legacy_replay/crlb_los/sync_crlb_0dB_0dB.pdf) | Legacy sync CRLB uses all-clock/post-hoc slicing and is not V24-gauge clean. |
| Fig. 4 localization vs satellites | current_best_visual_evidence, candidate_for_human_review, needs_v24_clean_replacement | [outputs/legacy_replay/network_size_medium/pos_vary_ues.pdf](../legacy_replay/network_size_medium/pos_vary_ues.pdf) | Medium legacy-compatible replay visibly tests JCLS benefit, but remains all-clock/truth-gated legacy behavior. |
| Fig. 5 synchronization vs satellites | current_best_visual_evidence, candidate_for_human_review, needs_v24_clean_replacement | [outputs/legacy_replay/network_size_medium/sync_vary_ues.pdf](../legacy_replay/network_size_medium/sync_vary_ues.pdf) | Medium legacy-compatible replay is the best visual evidence, but the metric remains legacy all-clock synchronization. |
| Fig. 6 localization vs clock standard deviation | current_best_visual_evidence, legacy_provenance_only, needs_v24_clean_replacement | [outputs/legacy_replay/clock_sweep_full/pos_vary_clock.pdf](../legacy_replay/clock_sweep_full/pos_vary_clock.pdf) | Full legacy clock-sweep replay shows the intended qualitative behavior but uses truth-gated legacy estimation. |
| Fig. 7 synchronization vs clock standard deviation | current_best_visual_evidence, legacy_provenance_only, needs_v24_clean_replacement | [outputs/legacy_replay/clock_sweep_full/sync_vary_clock.pdf](../legacy_replay/clock_sweep_full/sync_vary_clock.pdf) | Full legacy clock-sweep replay is visually useful but uses legacy all-clock synchronization metrics. |
| NLOS CRLB variants | needs_nlos_model_design | none | No executable legacy Rayleigh/NLOS or package score-covariance NLOS FIM path currently exists. |
