# Controlled Migration Ladder

## Executive Summary
This ladder starts from frozen legacy-compatible behavior and changes one migration axis at a time. No figure is manuscript-ready.

- First degraded step: `none`
- Current best migration step: `step_c0_legacy_map_instrumented`

## Baseline Health
- Status: `healthy`
- Localization improvements: 9 of 9
- Synchronization improvements: 9 of 9

## Steps
| Step | Grid | Status | Localization wins | Synchronization wins | Fallbacks | Recommendation |
|---|---|---|---:|---:|---:|---|
| `step_c0_legacy_map_instrumented` | `tiny` | `partially_degraded` | 0/0 | 0/0 | 2 | stop and inspect |

## Caveat
This ladder uses the current legacy medium replay rows as the frozen behavior source. It does not make manuscript-ready claims and does not execute the original notebook.
