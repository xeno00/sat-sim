# Hung Ladder Recovery Report

## Executive Summary

- No still-running Python ladder process was found during recovery.
- The existing canonical C0/C1/C2/C3 outputs from the overnight run appear complete as diagnostic artifacts.
- The failure mode was unsafe default execution behavior, not evidence that the existing Step C diagnosis artifacts are invalid.
- Bounded recovery now writes separate `tiny_bounded` outputs and bounded reports/cache manifests.

## Repository State

- Branch: `codex/migration-step-c-diagnosis`
- Commit: `c74b5ad2c92d05a952fd6a3e5de2c18fc36892c3`
- Working tree status at refreshed report generation: `M PROJECT_STATUS.md
 M docs/tasks/NEXT.md
 M scripts/run_controlled_migration_ladder.py
 M tests/test_controlled_migration_ladder.py
?? outputs/cache/migration_ladder/7ffea5cb5a6676ff/
?? outputs/cache/migration_ladder/CACHE_MANIFEST_BOUNDED_RECOVERY.json
?? outputs/cache/migration_ladder/CACHE_MANIFEST_BOUNDED_RECOVERY.md
?? outputs/cache/migration_ladder/ROW_STATUS.jsonl
?? outputs/cache/migration_ladder/RUN_HEARTBEAT.json
?? outputs/migration_ladder/step_c0_legacy_map_instrumented/tiny_bounded/
?? outputs/reports/CONTROLLED_MIGRATION_LADDER_BOUNDED_RECOVERY.json
?? outputs/reports/CONTROLLED_MIGRATION_LADDER_BOUNDED_RECOVERY.md
?? outputs/reports/HUNG_LADDER_RECOVERY_REPORT.json
?? outputs/reports/HUNG_LADDER_RECOVERY_REPORT.md`
- Stuck ladder process found: `false`

## Existing C-Substep Output Inventory

| Step | Grid | Complete? | Raw CSV | Summary | Metadata | PDFs | PNG previews | Metadata status | Cache status |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| `step_c0_legacy_map_instrumented` | `tiny` | yes | yes | yes | yes | yes | yes | `partially_degraded` | `complete` |
| `step_c0_legacy_map_instrumented` | `medium` | yes | yes | yes | yes | yes | yes | `healthy` | `complete` |
| `step_c1_legacy_cov_observable_acceptance` | `tiny` | yes | yes | yes | yes | yes | yes | `partially_degraded` | `complete` |
| `step_c1_legacy_cov_observable_acceptance` | `medium` | yes | yes | yes | yes | yes | yes | `partially_degraded` | `complete` |
| `step_c2_observable_cov_legacy_acceptance` | `tiny` | yes | yes | yes | yes | yes | yes | `partially_degraded` | `complete` |
| `step_c2_observable_cov_legacy_acceptance` | `medium` | yes | yes | yes | yes | yes | yes | `healthy` | `complete` |
| `step_c3_cov_diag_prior` | `tiny` | yes | yes | yes | yes | yes | yes | `partially_degraded` | `complete` |
| `step_c3_cov_diag_prior` | `medium` | yes | yes | yes | yes | yes | yes | `partially_degraded` | `complete` |
| `step_c3_cov_block_diag` | `tiny` | yes | yes | yes | yes | yes | yes | `partially_degraded` | `complete` |
| `step_c3_cov_block_diag` | `medium` | yes | yes | yes | yes | yes | yes | `partially_degraded` | `complete` |
| `step_c3_cov_damped_inverse` | `tiny` | yes | yes | yes | yes | yes | yes | `partially_degraded` | `complete` |
| `step_c3_cov_damped_inverse` | `medium` | yes | yes | yes | yes | yes | yes | `failed` | `complete` |
| `step_c3_cov_damped_pinv` | `tiny` | yes | yes | yes | yes | yes | yes | `partially_degraded` | `complete` |
| `step_c3_cov_damped_pinv` | `medium` | yes | yes | yes | yes | yes | yes | `partially_degraded` | `complete` |
| `step_c3_cov_residual_scaled` | `tiny` | yes | yes | yes | yes | yes | yes | `partially_degraded` | `complete` |
| `step_c3_cov_residual_scaled` | `medium` | yes | yes | yes | yes | yes | yes | `partially_degraded` | `complete` |

## Step C Scientific First Pass

- Best Step-B-preserving substep: `step_c0_legacy_map_instrumented preserved Step B behavior as diagnostic-only; among actual replacements, step_c2_observable_cov_legacy_acceptance degraded least.`
- Least-degraded C3 covariance candidate: `step_c3_cov_block_diag` (`major_degradation`).
- C3 covariance candidates are still not healthy; this is not a manuscript-ready correction.
- First major degradation: `step_c1_legacy_cov_observable_acceptance`.
- Breaking factor in existing diagnosis report: `acceptance_replacement`.
- Best non-truth covariance candidate: `None`.

## Safeguards Implemented

- default tiny-only execution
- explicit --medium required for medium rows
- --max-rows
- --max-substeps
- --tiny-only
- --no-medium
- --timeout-seconds-per-row metadata/status guard
- --timeout-seconds-total guard between rows
- --resume flag recorded in metadata
- --dry-run
- --list-planned-work planned-row printout
- --stop-after-first-degradation
- bounded output/report/cache manifest stems
- row-level status JSONL
- heartbeat JSON
- bounded cache entries marked bounded_noncanonical

## Suspected Hang Cause

Unsafe default runner behavior executed tiny and medium grids across all migration steps and all C3 covariance candidates without row/substep/time limits. No stuck Python process was found during recovery; existing canonical outputs appear complete.

## Bounded Recovery Smoke

- Output metadata: `outputs/migration_ladder/step_c0_legacy_map_instrumented/tiny_bounded/migration_step_metadata.json`
- Execution status: `complete`
- Executed rows: 2 of 2
- Canonical cache valid: `False`
- Cache status: `bounded_noncanonical`
- Heartbeat path: `outputs/cache/migration_ladder/RUN_HEARTBEAT.json`
- Heartbeat status: `complete`
- Last completed output: `step_c0_legacy_map_instrumented:tiny:1:8`

## Tests Run

- `python -m unittest tests.test_controlled_migration_ladder`: 27 passed
- `powershell -NoProfile -ExecutionPolicy Bypass -File '..\scripts\test_sat_sim.ps1'`: 238 passed

## Recommendation Before Rerun

Do not rerun full Step C. Review existing complete C outputs and STEP_C_DIAGNOSIS_REPORT first. If additional execution is needed, use --dry-run/--list-planned-work, --tiny-only, --max-rows, and timeouts; require --medium explicitly for medium rows.
