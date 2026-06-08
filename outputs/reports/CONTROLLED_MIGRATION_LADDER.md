# Controlled Migration Ladder

## Executive Summary
This ladder starts from frozen legacy-compatible behavior and changes one migration axis at a time. No figure is manuscript-ready.

- First degraded step: `step_b_lm_residual_acceptance`
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
| `step_b_lm_residual_acceptance` | `tiny` | `partially_degraded` | 2/2 | 1/2 | 12 | stop and inspect |
| `step_b_lm_residual_acceptance` | `medium` | `healthy` | 9/9 | 9/9 | 48 | keep |
| `step_c0_legacy_map_instrumented` | `tiny` | `partially_degraded` | 2/2 | 1/2 | 2 | stop and inspect |
| `step_c0_legacy_map_instrumented` | `medium` | `healthy` | 9/9 | 9/9 | 3 | keep |
| `step_c1_legacy_cov_observable_acceptance` | `tiny` | `partially_degraded` | 1/2 | 1/2 | 2 | stop and inspect |
| `step_c1_legacy_cov_observable_acceptance` | `medium` | `partially_degraded` | 7/9 | 8/9 | 3 | stop and inspect |
| `step_c2_observable_cov_legacy_acceptance` | `tiny` | `partially_degraded` | 2/2 | 1/2 | 2 | stop and inspect |
| `step_c2_observable_cov_legacy_acceptance` | `medium` | `healthy` | 9/9 | 9/9 | 3 | keep |
| `step_c3_cov_diag_prior` | `tiny` | `partially_degraded` | 1/2 | 1/2 | 2 | stop and inspect |
| `step_c3_cov_diag_prior` | `medium` | `partially_degraded` | 7/9 | 8/9 | 3 | stop and inspect |
| `step_c3_cov_block_diag` | `tiny` | `partially_degraded` | 1/2 | 1/2 | 2 | stop and inspect |
| `step_c3_cov_block_diag` | `medium` | `partially_degraded` | 7/9 | 8/9 | 3 | stop and inspect |
| `step_c3_cov_damped_inverse` | `tiny` | `partially_degraded` | 1/2 | 1/2 | 2 | stop and inspect |
| `step_c3_cov_damped_inverse` | `medium` | `failed` | 7/9 | 8/9 | 3 | stop and inspect |
| `step_c3_cov_damped_pinv` | `tiny` | `partially_degraded` | 1/2 | 1/2 | 2 | stop and inspect |
| `step_c3_cov_damped_pinv` | `medium` | `partially_degraded` | 7/9 | 8/9 | 3 | stop and inspect |
| `step_c3_cov_residual_scaled` | `tiny` | `partially_degraded` | 1/2 | 1/2 | 2 | stop and inspect |
| `step_c3_cov_residual_scaled` | `medium` | `partially_degraded` | 7/9 | 8/9 | 3 | stop and inspect |

## Caveat
This ladder uses the current legacy medium replay rows as the frozen behavior source. It does not make manuscript-ready claims and does not execute the original notebook.
