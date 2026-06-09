# Branch Integration Inventory

Generated: `2026-06-09T14:24:11.072662+00:00`
Integration branch: `codex/integration-compliance-and-merge-discipline`
Integration commit: `e068e77`

This inventory records a final merge/disposition status for active and recent Codex branches.

## Disposition Counts

- `already_merged`: 29
- `merge_now`: 2
- `park_do_not_merge_yet`: 3
- `quarantine_do_not_merge`: 2
- `superseded_do_not_merge`: 5

## Branches

| branch_name | latest_commit | pushed_status | merge_status | disposition | primary_purpose | disposition_reason |
|---|---|---|---|---|---|---|
| codex/c7-candidate-figure-validation | 04ba189 | pushed_synced | not_on_main | superseded_do_not_merge | Bounded C7 candidate figure validation | Superseded by codex/c7-manuscript-figure-recreation. |
| codex/c7-manuscript-figure-recreation | b35c3c1 | pushed_synced | not_on_main | merge_now | C7 Fig. 4--7 candidate recreation plus result lineage/units review | Reviewed C7 candidate/lineage work is non-final, registered, tested, and merged into this integration branch. |
| codex/controlled-legacy-to-v24-migration | 27e83d0 | pushed_synced | reachable_from_main | already_merged | Legacy notebook replay/provenance diagnostics | Branch tip is already reachable from main. |
| codex/crlb-decision-sprint | 1f76f68 | pushed_synced | reachable_from_main | already_merged | CRLB/FIM diagnostics and candidate data | Branch tip is already reachable from main. |
| codex/crlb-diagnostic-hardening | 8baa36c | pushed_synced | reachable_from_main | already_merged | CRLB/FIM diagnostics and candidate data | Branch tip is already reachable from main. |
| codex/crlb-figure-candidate-data | 7130144 | pushed_synced | reachable_from_main | already_merged | CRLB/FIM diagnostics and candidate data | Branch tip is already reachable from main. |
| codex/crlb-geometry-diagnostics | dd5ef21 | pushed_synced | reachable_from_main | already_merged | CRLB/FIM diagnostics and candidate data | Branch tip is already reachable from main. |
| codex/crlb-preview-candidates | 6e5b32f | pushed_synced | reachable_from_main | already_merged | CRLB/FIM diagnostics and candidate data | Branch tip is already reachable from main. |
| codex/gps-gnss-baseline-exploration | 041d00f | pushed_synced | not_on_main | park_do_not_merge_yet | GNSS/baseline exploration diagnostics | Useful diagnostics, but not yet integrated into the lineage/units registry on main. |
| codex/human-ready-figures-sprint | b77da49 | pushed_synced | reachable_from_main | already_merged | Unknown Codex branch purpose; needs human review | Branch tip is already reachable from main. |
| codex/integration-compliance-and-merge-discipline | e068e77 | local_only | not_on_main | merge_now | Unknown Codex branch purpose; needs human review | Integration branch contains the reviewed C7 lineage/recreation merge plus process controls for branch disposition. |
| codex/jcls-wave-results-exploration | 24524fb | pushed_synced | not_on_main | park_do_not_merge_yet | Wave-results exploration diagnostics | Useful diagnostics, but not yet integrated into the lineage/units registry on main. |
| codex/legacy-clock-sweep-replay | 7166d9d | pushed_synced | reachable_from_main | already_merged | Legacy notebook replay/provenance diagnostics | Branch tip is already reachable from main. |
| codex/legacy-crlb-figure-replay | 5917ddf | pushed_synced | reachable_from_main | already_merged | Legacy notebook replay/provenance diagnostics | Branch tip is already reachable from main. |
| codex/legacy-figures-gallery-crlb-nlos | ad58418 | pushed_synced | not_on_main | superseded_do_not_merge | Legacy notebook replay/provenance diagnostics | Historical diagnostic branch superseded by later merged reports or current C7 lineage work. |
| codex/legacy-network-size-and-v24-port-plan | a608cdd | pushed_synced | reachable_from_main | already_merged | Legacy notebook replay/provenance diagnostics | Branch tip is already reachable from main. |
| codex/legacy-surgical-prior-region-initialization | 8a1419d | local_only | not_on_main | quarantine_do_not_merge | Legacy notebook replay/provenance diagnostics | Useful red-team evidence, but it preserves legacy truth-centered behavior and could mislead manuscript-readiness decisions. |
| codex/legacy-surgical-truth-gate-removal | 8a1419d | pushed_synced | not_on_main | quarantine_do_not_merge | Legacy notebook replay/provenance diagnostics | Useful red-team evidence, but it preserves legacy truth-centered behavior and could mislead manuscript-readiness decisions. |
| codex/manuscript-algorithm-parity-check | e78a0e1 | pushed_synced | not_on_main | superseded_do_not_merge | Manuscript-facing diagnostics or algorithm parity reports | Superseded by codex/c7-manuscript-figure-recreation. |
| codex/manuscript-align-to-c7-support | 0e6300b | local_only | not_on_main | superseded_do_not_merge | Manuscript-facing diagnostics or algorithm parity reports | Superseded by codex/c7-manuscript-figure-recreation. |
| codex/manuscript-crlb-candidate | f9fd7cc | pushed_synced | reachable_from_main | already_merged | CRLB/FIM diagnostics and candidate data | Branch tip is already reachable from main. |
| codex/manuscript-geometry-noise | 2332db8 | pushed_synced | reachable_from_main | already_merged | Manuscript-facing diagnostics or algorithm parity reports | Branch tip is already reachable from main. |
| codex/migration-step-b-lm-no-truth-gate | c9cf524 | pushed_synced | reachable_from_main | already_merged | Controlled legacy-to-V24 migration diagnostics | Branch tip is already reachable from main. |
| codex/migration-step-c-diagnosis | 21a880e | pushed_synced | reachable_from_main | already_merged | Controlled legacy-to-V24 migration diagnostics | Branch tip is already reachable from main. |
| codex/migration-step-c-map-no-truth-gate | f70b636 | pushed_synced | not_on_main | superseded_do_not_merge | Controlled legacy-to-V24 migration diagnostics | Historical diagnostic branch superseded by later merged reports or current C7 lineage work. |
| codex/notebook-manuscript-regression-sprint | aaf6589 | pushed_synced | reachable_from_main | already_merged | Manuscript-facing diagnostics or algorithm parity reports | Branch tip is already reachable from main. |
| codex/notebook-regression-execution-audit | db3284e | pushed_synced | reachable_from_main | already_merged | Unknown Codex branch purpose; needs human review | Branch tip is already reachable from main. |
| codex/package-native-figures-4-7 | 5e8a467 | pushed_synced | reachable_from_main | already_merged | Package-native figure/provenance diagnostics | Branch tip is already reachable from main. |
| codex/plot-gallery-cache | ffe177c | pushed_synced | reachable_from_main | already_merged | Unknown Codex branch purpose; needs human review | Branch tip is already reachable from main. |
| codex/step-c4-composite-map-acceptance | 12e133e | pushed_synced | reachable_from_main | already_merged | Unknown Codex branch purpose; needs human review | Branch tip is already reachable from main. |
| codex/step-c5-sliding-window-map | 6b26b10 | pushed_synced | reachable_from_main | already_merged | Unknown Codex branch purpose; needs human review | Branch tip is already reachable from main. |
| codex/step-c7-residual-cov-sync-safeguard | 89a9b2a | pushed_synced | reachable_from_main | already_merged | C7 estimator mode implementation and validation | Branch tip is already reachable from main. |
| codex/step3-covariance-exploration | da444d7 | pushed_synced | reachable_from_main | already_merged | Step 3 covariance/dynamics exploration diagnostics | Branch tip is already reachable from main. |
| codex/step3-gate-exploration | 7c7445b | pushed_synced | reachable_from_main | already_merged | Unknown Codex branch purpose; needs human review | Branch tip is already reachable from main. |
| codex/step3-low-cost-exploration | f482d00 | pushed_synced | reachable_from_main | already_merged | Unknown Codex branch purpose; needs human review | Branch tip is already reachable from main. |
| codex/step3-micro-benchmarks | df9fcaf | pushed_synced | reachable_from_main | already_merged | Step 3 deterministic micro-benchmarks | Branch tip is already reachable from main. |
| codex/step3-near-winner-sparse | a979eb0 | pushed_synced | reachable_from_main | already_merged | Unknown Codex branch purpose; needs human review | Branch tip is already reachable from main. |
| codex/step3-residual-cov-audit | 1cda0a6 | pushed_synced | reachable_from_main | already_merged | Residual-scaled covariance failure audit and robust candidate selection | Branch tip is already reachable from main. |
| codex/v24-algorithm-fidelity | 349ceac | pushed_synced | reachable_from_main | already_merged | Unknown Codex branch purpose; needs human review | Branch tip is already reachable from main. |
| codex/wave-observability-estimator-gap-audit | 24524fb | local_only | not_on_main | park_do_not_merge_yet | Wave-results exploration diagnostics | Useful diagnostics, but not yet integrated into the lineage/units registry on main. |
| main | 2eaa3ba | pushed_synced | reachable_from_main | already_merged | Integration target | Main is the integration target. |
