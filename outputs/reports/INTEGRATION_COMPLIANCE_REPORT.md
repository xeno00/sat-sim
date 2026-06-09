# Integration Compliance Report

## Executive Summary

Current main commit: `4e12117`.
Branches reviewed from Git before cleanup: `41`.
Local branch refs deleted: `35`.
Remote branch refs deleted: `34`.
PR #3 was closed as quarantined. Parked/quarantined/human-review branches were kept.

## PR Actions

- Opened: none.
- Merged: none.
- Closed: PR #3 as quarantined.

## Deleted Branches

- Local: `35`
- Remote: `34`

## Parked Branches

- `codex/gps-gnss-baseline-exploration`
- `codex/jcls-wave-results-exploration`
- `codex/wave-observability-estimator-gap-audit`

## Quarantined Branches

- `codex/legacy-surgical-prior-region-initialization`
- `codex/legacy-surgical-truth-gate-removal`

## Human Review Branches

- `codex/legacy-figures-gallery-crlb-nlos`

## Remaining Branch Clutter

- codex/gps-gnss-baseline-exploration (parked, active worktree)
- codex/jcls-wave-results-exploration (parked, active worktree)
- codex/wave-observability-estimator-gap-audit (parked, active worktree/local alias)
- codex/legacy-surgical-truth-gate-removal (quarantined, active worktree, PR #3 closed)
- codex/legacy-surgical-prior-region-initialization (quarantined, active worktree)
- codex/legacy-figures-gallery-crlb-nlos (needs human review)

## Checks Run

- `python scripts/check_protected_files.py --base main --target HEAD --fail-on-protected` -> PASS
- `python -m unittest tests.test_integration_compliance` -> PASS (5 tests)
