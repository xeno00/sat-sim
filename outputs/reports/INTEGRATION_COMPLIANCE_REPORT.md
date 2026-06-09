# Integration Compliance Report

## Executive Summary

This integration pass merged the reviewed C7 manuscript recreation and lineage/units work into the integration branch, inventoried active Codex branches, and added explicit merge/disposition discipline for future tasks.
Subagent review agreed with the merge posture: merge the C7 integration stack, park GNSS/wave until lineage catches up, and quarantine legacy-surgical truth-gate evidence until human red-team review.

## Branches Reviewed

- Total reviewed: 41
- Merge now or already merged: 31
- Parked: 3
- Superseded: 5
- Quarantined: 2
- Unknown/human review: 0

## Branches Merged In This Integration Branch

- `codex/c7-manuscript-figure-recreation` via merge commit `Merge C7 manuscript recreation and lineage reports`.

## Parked Branches

- `codex/gps-gnss-baseline-exploration`
- `codex/jcls-wave-results-exploration`
- `codex/wave-observability-estimator-gap-audit`

## Superseded Branches

- `codex/c7-candidate-figure-validation`
- `codex/legacy-figures-gallery-crlb-nlos`
- `codex/manuscript-algorithm-parity-check`
- `codex/manuscript-align-to-c7-support`
- `codex/migration-step-c-map-no-truth-gate`

## Quarantined Branches

- `codex/legacy-surgical-prior-region-initialization`
- `codex/legacy-surgical-truth-gate-removal`

## Protected-File Check

The integration branch must pass `python scripts/check_protected_files.py --base main --target HEAD --fail-on-protected` before merge to main.

## Remaining Unmerged Work

Parked and quarantined branches should not be merged until their result lineage, units status, readiness, and recommended-use status are explicit.
