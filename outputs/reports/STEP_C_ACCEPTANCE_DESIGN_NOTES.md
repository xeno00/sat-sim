# Step C Acceptance Design Notes

## Executive Summary

Existing Step C outputs are complete diagnostic artifacts. They indicate that replacing MAP acceptance/reversion is the primary breaking factor, not covariance replacement alone.

## Diagnosis Synthesis

- C0 instruments legacy MAP behavior and is diagnostic-only.
- C1 keeps legacy covariance but replaces acceptance; it has major degradation.
- C2 replaces covariance but keeps legacy truth acceptance; it has mild degradation.
- C3 candidates replace both covariance and acceptance; none is healthy.

## What Legacy Acceptance Appears To Protect

- Legacy MAP acceptance appears to prevent accepted updates that improve a local observable score but move the all-clock state into a poorer estimator basin.
- The legacy truth gate protects against overconfident EKF-style corrections from a fragile all-clock state and legacy covariance representation.
- C0 remains behavior-preserving because it instruments the legacy path without removing truth-state reversion.

## Why Local Observable Acceptance Failed

- C1 kept the legacy truth-derived covariance but replaced acceptance with local observable checks and still produced major degradation.
- This indicates residual-only/covariance-local acceptance is insufficient for the legacy all-clock MAP path.
- The local residual score does not fully capture downstream localization/synchronization behavior under the overparameterized all-clock state.

## Why C2 Degraded Less Than C1

- C2 replaced covariance while preserving legacy truth-gated acceptance, and it degraded only mildly.
- This isolates acceptance/reversion, not covariance replacement alone, as the primary breaking factor in the current medium grid.

## Correlating Metrics

| Step | Overall | Metadata | Healthy | Mild | Major | Failed | Accepted | Rejected | Invalid cov rows | Update norm max |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `step_c0_legacy_map_instrumented` | `diagnostic_only` | `healthy` | 0 | 0 | 0 | 0 | 6 | 39 | 0 | 0.001363438050976329 |
| `step_c1_legacy_cov_observable_acceptance` | `major_degradation` | `partially_degraded` | 4 | 3 | 5 | 0 | 43 | 2 | 0 | 0.0028340135977937557 |
| `step_c2_observable_cov_legacy_acceptance` | `mild_degradation` | `healthy` | 10 | 2 | 0 | 0 | 7 | 38 | 0 | 0.0013067200772744153 |
| `step_c3_cov_diag_prior` | `major_degradation` | `partially_degraded` | 7 | 2 | 3 | 0 | 6 | 39 | 0 | 0.0019833563671700356 |
| `step_c3_cov_block_diag` | `major_degradation` | `partially_degraded` | 7 | 3 | 2 | 0 | 9 | 36 | 0 | 0.0019743058475011816 |
| `step_c3_cov_damped_inverse` | `major_degradation` | `failed` | 3 | 3 | 6 | 0 | 35 | 10 | 1 | 0.001982511458121259 |
| `step_c3_cov_damped_pinv` | `major_degradation` | `partially_degraded` | 3 | 4 | 5 | 0 | 43 | 2 | 0 | 0.002799464978815082 |
| `step_c3_cov_residual_scaled` | `major_degradation` | `partially_degraded` | 3 | 4 | 5 | 0 | 44 | 1 | 0 | 0.002799975237036193 |

## Criteria To Test Next

- measurement residual cost nonincrease
- prior consistency cost
- total observable MAP objective nonincrease
- covariance trace nonexplosion and finite/symmetric/PSD checks
- bounded relative state update norm
- bounded position update norm
- bounded clock update norm
