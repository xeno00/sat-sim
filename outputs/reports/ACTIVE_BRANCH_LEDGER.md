# Active Branch Ledger

## Executive Summary

Canonical live branch-status source of truth. Generated `2026-06-09T18:39:42.464694+00:00` from actual Git refs and GitHub PR state.
Snapshot base main commit: `4e2a6da`.
Active branches remaining: `8`.
Open PRs among active branches: `1`.

This ledger supersedes ad hoc branch-status prose in older cleanup reports. Other reports are snapshots and should point here for live branch state.

## Active Branch Table

| branch | commit | local/remote | PR | disposition | risk | readiness | next action |
|---|---|---|---|---|---|---|---|
| codex/gps-gnss-baseline-exploration | 041d00f | both | none | parked_keep | result_lineage_missing | debug_only | Review GNSS report outputs and add a result-lineage/units entry or keep parked. |
| codex/jcls-wave-results-exploration | 24524fb | both | none | parked_keep | result_lineage_missing | debug_only | Run read-only lineage/units review for wave-results outputs. |
| codex/jcls-sim-pipeline-schema | de87fca | both | #6 closed_merged | merged_delete_safe | process_only | not_science | Delete local/remote schema branch during the next branch-cleanup pass. |
| codex/normalized-benchmark-adapters-v1 | b4a01fc | both | #7 open_draft | open_pr_review | diagnostic_only | debug_only | Review PR #7; if accepted, merge normalized benchmark adapter layer and keep outputs non-final/debugging-only. |
| codex/legacy-figures-gallery-crlb-nlos | ad58418 | both | none | needs_human_review | diagnostic_only | legacy_reference_only | Human review of legacy graph review package; decide park vs quarantine vs sanitized PR. |
| codex/legacy-surgical-prior-region-initialization | 0eefdea | local_only | #4 closed_merged | merged_delete_safe | legacy_truth_risk | legacy_reference_only | Remove active worktree when no longer needed, then delete local branch. |
| codex/legacy-surgical-truth-gate-removal | 8a1419d | local_only | #3 closed_quarantined; commit reachable through merged PR #4 | merged_delete_safe | legacy_truth_risk | legacy_reference_only | Remove active worktree when no longer needed, then delete local branch. |
| codex/wave-observability-estimator-gap-audit | 24524fb | local_only | none | parked_keep | result_lineage_missing | debug_only | Resolve with the wave-results branch; remove duplicate worktree when no longer needed. |

## Parked Branches

- `codex/gps-gnss-baseline-exploration`: GNSS/baseline diagnostics are unique and potentially useful, but not yet in current lineage/units registry. Next action: Review GNSS report outputs and add a result-lineage/units entry or keep parked.
- `codex/jcls-wave-results-exploration`: Wave-results pilot contains unique output-heavy diagnostics and active worktree state; not yet registered in current lineage/units ledger. Next action: Run read-only lineage/units review for wave-results outputs.
- `codex/wave-observability-estimator-gap-audit`: Local active-worktree alias at the same tip as wave-results exploration; kept because the worktree is active. Next action: Resolve with the wave-results branch; remove duplicate worktree when no longer needed.

## Quarantined Branches

- None.

## Merged/Delete-Safe Branches

- `codex/jcls-sim-pipeline-schema`: PR #6 merged into main at 4e2a6da; branch ref is safe to delete during branch cleanup. Next action: Delete local/remote schema branch during the next branch-cleanup pass.
- `codex/legacy-surgical-prior-region-initialization`: PR #4 merged this branch content into main. Local branch remains only because an active worktree owns it. Next action: Remove active worktree when no longer needed, then delete local branch.
- `codex/legacy-surgical-truth-gate-removal`: The commit is now reachable from main via merged PR #4, while PR #3 remains closed/quarantined. Local branch remains only because an active worktree owns it. Next action: Remove active worktree when no longer needed, then delete local branch.

## Branches Needing Human Review

- `codex/legacy-figures-gallery-crlb-nlos`: Unique legacy graph review package with legacy replay/gallery outputs, scripts, tests, and reports. Useful provenance may remain, but legacy/non-final outputs could confuse manuscript evidence. Next action: Human review of legacy graph review package; decide park vs quarantine vs sanitized PR.

## Branches With PRs

- `codex/jcls-sim-pipeline-schema`: PR #6 `closed_merged` https://github.com/xeno00/sat-sim/pull/6
- `codex/normalized-benchmark-adapters-v1`: PR #7 `open_draft` https://github.com/xeno00/sat-sim/pull/7
- `codex/legacy-surgical-prior-region-initialization`: PR #4 `closed_merged` https://github.com/xeno00/sat-sim/pull/4
- `codex/legacy-surgical-truth-gate-removal`: PR #3 `closed_quarantined; commit reachable through merged PR #4` https://github.com/xeno00/sat-sim/pull/3

## Branches Safe To Delete

- `codex/jcls-sim-pipeline-schema`: PR #6 merged into main at 4e2a6da; branch ref is safe to delete during branch cleanup. Next action: Delete local/remote schema branch during the next branch-cleanup pass.

## Next Actions In Priority Order

1. Review PR #7 for `codex/normalized-benchmark-adapters-v1`; merge after human approval if acceptable.
2. Delete the merged schema branch refs when branch cleanup is next requested.
3. Human review `codex/legacy-figures-gallery-crlb-nlos` and decide park/quarantine/sanitized PR/supersede.
4. Add lineage/units entries before GNSS or wave-result branch PRs.
5. Remove duplicate/parked worktrees only after their branches are merged, superseded, or explicitly abandoned.

## Drift Warnings

- PR #6 merged into main; codex/jcls-sim-pipeline-schema is now merged/delete-safe.
- PR #7 is open as the active normalized benchmark adapter review branch.
- codex/wave-observability-estimator-gap-audit is local-only and points to the same commit as codex/jcls-wave-results-exploration, but it is attached to an active worktree.
- codex/legacy-surgical-prior-region-initialization and codex/legacy-surgical-truth-gate-removal are merged into main but local refs remain because active worktrees own them.
