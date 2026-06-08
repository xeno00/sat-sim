# Step C Diagnosis Report

## Executive Summary
This report splits the MAP/EKF truth-dependence correction into sub-ablations. All outputs are non-final diagnostics.

- Breaking factor: `acceptance_replacement`
- Best non-truth covariance candidate: `none`
- MAP truth acceptance removable: `False`
- MAP truth covariance removable: `False`

| Step | Grid | Overall | Healthy | Mild | Major | Failed | Truth covariance | Truth acceptance | MAP accept/reject |
|---|---|---|---:|---:|---:|---:|---|---|---:|
| `step_c0_legacy_map_instrumented` | `medium` | `diagnostic_only` | 0 | 0 | 0 | 0 | `True` | `True` | 6/39 |
| `step_c1_legacy_cov_observable_acceptance` | `medium` | `major_degradation` | 4 | 3 | 5 | 0 | `True` | `False` | 43/2 |
| `step_c2_observable_cov_legacy_acceptance` | `medium` | `mild_degradation` | 10 | 2 | 0 | 0 | `False` | `True` | 7/38 |
| `step_c3_cov_diag_prior` | `medium` | `major_degradation` | 7 | 2 | 3 | 0 | `False` | `False` | 6/39 |
| `step_c3_cov_block_diag` | `medium` | `major_degradation` | 7 | 3 | 2 | 0 | `False` | `False` | 9/36 |
| `step_c3_cov_damped_inverse` | `medium` | `major_degradation` | 3 | 3 | 6 | 0 | `False` | `False` | 35/10 |
| `step_c3_cov_damped_pinv` | `medium` | `major_degradation` | 3 | 4 | 5 | 0 | `False` | `False` | 43/2 |
| `step_c3_cov_residual_scaled` | `medium` | `major_degradation` | 3 | 4 | 5 | 0 | `False` | `False` | 44/1 |
