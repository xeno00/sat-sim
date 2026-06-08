# Controlled Migration Ladder

## Executive Summary
This ladder starts from frozen legacy-compatible behavior, exposes the legacy behavior as a package-described mode, and tests Step A: raw metrics without display smoothing. No figure is manuscript-ready.

- First degraded step: `none`
- Current best migration step: `step_a_no_display_smoothing`

## Baseline Health
- Status: `healthy`
- Localization improvements: 9 of 9
- Synchronization improvements: 9 of 9

## Steps
| Step | Grid | Status | Localization wins | Synchronization wins | Fallbacks | Recommendation |
|---|---|---|---:|---:|---:|---|
| `legacy_staged_compatible` | `tiny` | `healthy` | 2/2 | 2/2 | 12 | keep |
| `legacy_staged_compatible` | `medium` | `healthy` | 9/9 | 9/9 | 48 | keep |
| `step_a_no_display_smoothing` | `tiny` | `healthy` | 2/2 | 2/2 | 12 | keep |
| `step_a_no_display_smoothing` | `medium` | `healthy` | 9/9 | 9/9 | 48 | keep |

## Caveat
This ladder uses the current legacy medium replay rows as the frozen behavior source. It does not make manuscript-ready claims and does not execute the original notebook.
