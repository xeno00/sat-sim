# Branch Cleanup and PR Report

## Executive Summary

Current main commit before cleanup: `4e12117`.
Current main commit after cleanup: `4e12117`.
Branches found before cleanup: `41`.
Local branches deleted: `35`.
Remote branches deleted: `34`.
No new science, simulations, or manuscript figures were generated.

## PRs

- Opened: none.
- Merged: none.
- Closed: [PR #3](https://github.com/xeno00/sat-sim/pull/3) as quarantined legacy surgical truth-gate diagnostic.

## Branches Deleted Locally

- `codex/c7-candidate-figure-validation`
- `codex/c7-manuscript-figure-recreation`
- `codex/controlled-legacy-to-v24-migration`
- `codex/crlb-decision-sprint`
- `codex/crlb-diagnostic-hardening`
- `codex/crlb-figure-candidate-data`
- `codex/crlb-geometry-diagnostics`
- `codex/crlb-preview-candidates`
- `codex/human-ready-figures-sprint`
- `codex/integration-compliance-and-merge-discipline`
- `codex/legacy-clock-sweep-replay`
- `codex/legacy-crlb-figure-replay`
- `codex/legacy-network-size-and-v24-port-plan`
- `codex/manuscript-algorithm-parity-check`
- `codex/manuscript-align-to-c7-support`
- `codex/manuscript-crlb-candidate`
- `codex/manuscript-geometry-noise`
- `codex/migration-step-b-lm-no-truth-gate`
- `codex/migration-step-c-diagnosis`
- `codex/migration-step-c-map-no-truth-gate`
- `codex/notebook-manuscript-regression-sprint`
- `codex/notebook-regression-execution-audit`
- `codex/package-native-figures-4-7`
- `codex/plot-gallery-cache`
- `codex/step-c4-composite-map-acceptance`
- `codex/step-c5-sliding-window-map`
- `codex/step-c7-residual-cov-sync-safeguard`
- `codex/step3-covariance-exploration`
- `codex/step3-gate-exploration`
- `codex/step3-low-cost-exploration`
- `codex/step3-micro-benchmarks`
- `codex/step3-near-winner-sparse`
- `codex/step3-residual-cov-audit`
- `codex/update-primary-standard-case-nu3-ns10`
- `codex/v24-algorithm-fidelity`

## Branches Deleted Remotely

- `codex/c7-candidate-figure-validation`
- `codex/c7-manuscript-figure-recreation`
- `codex/controlled-legacy-to-v24-migration`
- `codex/crlb-decision-sprint`
- `codex/crlb-diagnostic-hardening`
- `codex/crlb-figure-candidate-data`
- `codex/crlb-geometry-diagnostics`
- `codex/crlb-preview-candidates`
- `codex/human-ready-figures-sprint`
- `codex/integration-compliance-and-merge-discipline`
- `codex/legacy-clock-sweep-replay`
- `codex/legacy-crlb-figure-replay`
- `codex/legacy-network-size-and-v24-port-plan`
- `codex/manuscript-algorithm-parity-check`
- `codex/manuscript-crlb-candidate`
- `codex/manuscript-geometry-noise`
- `codex/migration-step-b-lm-no-truth-gate`
- `codex/migration-step-c-diagnosis`
- `codex/migration-step-c-map-no-truth-gate`
- `codex/notebook-manuscript-regression-sprint`
- `codex/notebook-regression-execution-audit`
- `codex/package-native-figures-4-7`
- `codex/plot-gallery-cache`
- `codex/step-c4-composite-map-acceptance`
- `codex/step-c5-sliding-window-map`
- `codex/step-c7-residual-cov-sync-safeguard`
- `codex/step3-covariance-exploration`
- `codex/step3-gate-exploration`
- `codex/step3-low-cost-exploration`
- `codex/step3-micro-benchmarks`
- `codex/step3-near-winner-sparse`
- `codex/step3-residual-cov-audit`
- `codex/update-primary-standard-case-nu3-ns10`
- `codex/v24-algorithm-fidelity`

## Branches Kept Parked

- `codex/gps-gnss-baseline-exploration`
- `codex/jcls-wave-results-exploration`
- `codex/wave-observability-estimator-gap-audit`

## Branches Kept Quarantined

- `codex/legacy-surgical-prior-region-initialization`
- `codex/legacy-surgical-truth-gate-removal`

## Branches Requiring Human Review

- `codex/legacy-figures-gallery-crlb-nlos`

## Remaining Branch Clutter

- codex/gps-gnss-baseline-exploration (parked, active worktree)
- codex/jcls-wave-results-exploration (parked, active worktree)
- codex/wave-observability-estimator-gap-audit (parked, active worktree/local alias)
- codex/legacy-surgical-truth-gate-removal (quarantined, active worktree, PR #3 closed)
- codex/legacy-surgical-prior-region-initialization (quarantined, active worktree)
- codex/legacy-figures-gallery-crlb-nlos (needs human review)

## Full Branch Table

| branch_name | locations | latest_commit | tip_is_ancestor_of_main | commits_not_in_main | current_disposition | local_deletion_confirmed | remote_deletion_confirmed | disposition_reason |
|---|---|---|---|---|---|---|---|---|
| codex/c7-candidate-figure-validation | both | 04ba189 | True | 0 | already_merged_close_delete | True | True | Branch tip is reachable from main; safe to delete local/remote refs when no active worktree owns it. |
| codex/c7-manuscript-figure-recreation | both | b35c3c1 | True | 0 | already_merged_close_delete | True | True | Branch tip is reachable from main; safe to delete local/remote refs when no active worktree owns it. |
| codex/controlled-legacy-to-v24-migration | both | 27e83d0 | True | 0 | already_merged_close_delete | True | True | Branch tip is reachable from main; safe to delete local/remote refs when no active worktree owns it. |
| codex/crlb-decision-sprint | both | 1f76f68 | True | 0 | already_merged_close_delete | True | True | Branch tip is reachable from main; safe to delete local/remote refs when no active worktree owns it. |
| codex/crlb-diagnostic-hardening | both | 8baa36c | True | 0 | already_merged_close_delete | True | True | Branch tip is reachable from main; safe to delete local/remote refs when no active worktree owns it. |
| codex/crlb-figure-candidate-data | both | 7130144 | True | 0 | already_merged_close_delete | True | True | Branch tip is reachable from main; safe to delete local/remote refs when no active worktree owns it. |
| codex/crlb-geometry-diagnostics | both | dd5ef21 | True | 0 | already_merged_close_delete | True | True | Branch tip is reachable from main; safe to delete local/remote refs when no active worktree owns it. |
| codex/crlb-preview-candidates | both | 6e5b32f | True | 0 | already_merged_close_delete | True | True | Branch tip is reachable from main; safe to delete local/remote refs when no active worktree owns it. |
| codex/gps-gnss-baseline-exploration | both | 041d00f | False | 1 | park_keep_branch | False | False | Useful exploratory diagnostics, but not integrated into current lineage/units registry and not ready to merge. |
| codex/human-ready-figures-sprint | both | b77da49 | True | 0 | already_merged_close_delete | True | True | Branch tip is reachable from main; safe to delete local/remote refs when no active worktree owns it. |
| codex/integration-compliance-and-merge-discipline | both | 74d070c | True | 0 | already_merged_close_delete | True | True | Branch tip is reachable from main; safe to delete local/remote refs when no active worktree owns it. |
| codex/jcls-wave-results-exploration | both | 24524fb | False | 1 | park_keep_branch | False | False | Useful exploratory diagnostics, but not integrated into current lineage/units registry and not ready to merge. |
| codex/legacy-clock-sweep-replay | both | 7166d9d | True | 0 | already_merged_close_delete | True | True | Branch tip is reachable from main; safe to delete local/remote refs when no active worktree owns it. |
| codex/legacy-crlb-figure-replay | both | 5917ddf | True | 0 | already_merged_close_delete | True | True | Branch tip is reachable from main; safe to delete local/remote refs when no active worktree owns it. |
| codex/legacy-figures-gallery-crlb-nlos | both | ad58418 | False | 1 | needs_human_review | False | False | Large unique legacy/NLOS gallery branch changes many outputs and needs human review before PR or deletion. |
| codex/legacy-network-size-and-v24-port-plan | both | a608cdd | True | 0 | already_merged_close_delete | True | True | Branch tip is reachable from main; safe to delete local/remote refs when no active worktree owns it. |
| codex/legacy-surgical-prior-region-initialization | local | 8a1419d | False | 1 | quarantine_keep_branch | False | False | Legacy surgical diagnostics preserve truth-centered behavior and are unsafe to merge as current evidence. |
| codex/legacy-surgical-truth-gate-removal | both | 8a1419d | False | 1 | quarantine_keep_branch | False | False | Legacy surgical diagnostics preserve truth-centered behavior and are unsafe to merge as current evidence. |
| codex/manuscript-algorithm-parity-check | both | e78a0e1 | True | 0 | already_merged_close_delete | True | True | Branch tip is reachable from main; safe to delete local/remote refs when no active worktree owns it. |
| codex/manuscript-align-to-c7-support | local | 0e6300b | True | 0 | already_merged_close_delete | True | False | Branch tip is reachable from main; safe to delete local/remote refs when no active worktree owns it. |
| codex/manuscript-crlb-candidate | both | f9fd7cc | True | 0 | already_merged_close_delete | True | True | Branch tip is reachable from main; safe to delete local/remote refs when no active worktree owns it. |
| codex/manuscript-geometry-noise | both | 2332db8 | True | 0 | already_merged_close_delete | True | True | Branch tip is reachable from main; safe to delete local/remote refs when no active worktree owns it. |
| codex/migration-step-b-lm-no-truth-gate | both | c9cf524 | True | 0 | already_merged_close_delete | True | True | Branch tip is reachable from main; safe to delete local/remote refs when no active worktree owns it. |
| codex/migration-step-c-diagnosis | both | 21a880e | True | 0 | already_merged_close_delete | True | True | Branch tip is reachable from main; safe to delete local/remote refs when no active worktree owns it. |
| codex/migration-step-c-map-no-truth-gate | both | f70b636 | False | 1 | superseded_close_delete | True | True | Superseded by later Step C diagnosis/C4/C5/C7 work and residual covariance audit; do not merge. |
| codex/notebook-manuscript-regression-sprint | both | aaf6589 | True | 0 | already_merged_close_delete | True | True | Branch tip is reachable from main; safe to delete local/remote refs when no active worktree owns it. |
| codex/notebook-regression-execution-audit | both | db3284e | True | 0 | already_merged_close_delete | True | True | Branch tip is reachable from main; safe to delete local/remote refs when no active worktree owns it. |
| codex/package-native-figures-4-7 | both | 5e8a467 | True | 0 | already_merged_close_delete | True | True | Branch tip is reachable from main; safe to delete local/remote refs when no active worktree owns it. |
| codex/plot-gallery-cache | both | ffe177c | True | 0 | already_merged_close_delete | True | True | Branch tip is reachable from main; safe to delete local/remote refs when no active worktree owns it. |
| codex/step-c4-composite-map-acceptance | both | 12e133e | True | 0 | already_merged_close_delete | True | True | Branch tip is reachable from main; safe to delete local/remote refs when no active worktree owns it. |
| codex/step-c5-sliding-window-map | both | 6b26b10 | True | 0 | already_merged_close_delete | True | True | Branch tip is reachable from main; safe to delete local/remote refs when no active worktree owns it. |
| codex/step-c7-residual-cov-sync-safeguard | both | 89a9b2a | True | 0 | already_merged_close_delete | True | True | Branch tip is reachable from main; safe to delete local/remote refs when no active worktree owns it. |
| codex/step3-covariance-exploration | both | da444d7 | True | 0 | already_merged_close_delete | True | True | Branch tip is reachable from main; safe to delete local/remote refs when no active worktree owns it. |
| codex/step3-gate-exploration | both | 7c7445b | True | 0 | already_merged_close_delete | True | True | Branch tip is reachable from main; safe to delete local/remote refs when no active worktree owns it. |
| codex/step3-low-cost-exploration | both | f482d00 | True | 0 | already_merged_close_delete | True | True | Branch tip is reachable from main; safe to delete local/remote refs when no active worktree owns it. |
| codex/step3-micro-benchmarks | both | df9fcaf | True | 0 | already_merged_close_delete | True | True | Branch tip is reachable from main; safe to delete local/remote refs when no active worktree owns it. |
| codex/step3-near-winner-sparse | both | a979eb0 | True | 0 | already_merged_close_delete | True | True | Branch tip is reachable from main; safe to delete local/remote refs when no active worktree owns it. |
| codex/step3-residual-cov-audit | both | 1cda0a6 | True | 0 | already_merged_close_delete | True | True | Branch tip is reachable from main; safe to delete local/remote refs when no active worktree owns it. |
| codex/update-primary-standard-case-nu3-ns10 | both | 12894d6 | True | 0 | already_merged_close_delete | True | True | Branch tip is reachable from main; safe to delete local/remote refs when no active worktree owns it. |
| codex/v24-algorithm-fidelity | both | 349ceac | True | 0 | already_merged_close_delete | True | True | Branch tip is reachable from main; safe to delete local/remote refs when no active worktree owns it. |
| codex/wave-observability-estimator-gap-audit | local | 24524fb | False | 1 | park_keep_branch | False | False | Useful exploratory diagnostics, but not integrated into current lineage/units registry and not ready to merge. |

## Checks Run

- `python scripts/check_protected_files.py --base main --target HEAD --fail-on-protected` -> PASS
- `python -m unittest tests.test_integration_compliance` -> PASS (5 tests)
