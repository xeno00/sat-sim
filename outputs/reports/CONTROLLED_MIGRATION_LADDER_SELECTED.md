# Controlled Migration Ladder

## Executive Summary
This ladder starts from frozen legacy-compatible behavior and changes one migration axis at a time. No figure is manuscript-ready.

- First degraded step: `none`
- Current best migration step: `step_c5_sliding_window_map`

## Baseline Health
- Status: `healthy`
- Localization improvements: 9 of 9
- Synchronization improvements: 9 of 9

## Steps
| Step | Grid | Status | Localization wins | Synchronization wins | Fallbacks | Recommendation |
|---|---|---|---:|---:|---:|---|
| `step_c5_sliding_window_map` | `tiny` | `partially_degraded` | 1/2 | 1/2 | 2 | stop and inspect |
| `step_c5_sliding_window_map` | `medium` | `partially_degraded` | 8/9 | 7/9 | 3 | stop and inspect |

## Caveat
This ladder uses the current legacy medium replay rows as the frozen behavior source. It does not make manuscript-ready claims and does not execute the original notebook.
