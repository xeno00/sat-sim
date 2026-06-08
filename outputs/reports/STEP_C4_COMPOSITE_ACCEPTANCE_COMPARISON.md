# Step C4 Composite MAP Acceptance Comparison

## Executive Summary

- Grid: `medium`
- C4 status: `major_degradation`
- Best C3 reference: `step_c3_cov_block_diag`
- MAP truth acceptance replaceable now: `False`

## Aggregate Diagnostics

- Localization improvement rows: 7 of 9
- Synchronization improvement rows: 8 of 9
- MAP accepted/rejected updates: 43/2
- Score components: `['clock_update_norm', 'covariance_trace_nonexplosion', 'finite_symmetric_psd_covariance', 'information_gain_nonnegative', 'measurement_residual_cost', 'position_update_norm', 'prior_consistency_cost', 'relative_update_norm', 'total_map_objective']`
- Rejection reasons: `['map_objective_increased', 'residual_cost_increased']`

## Row Comparisons Against Step B

| Nu | Ns | Status | Step B pos [m] | C4 pos [m] | Step B sync [s] | C4 sync [s] | MAP acc/rej | Jmap before | Jmap after |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 4 | `healthy` | 0.26229065223009157 | 0.26229065223009157 | 2.1421024323915456e-10 | 2.1421024323915456e-10 | 0/0 |  |  |
| 1 | 8 | `healthy` | 0.23928421797729885 | 0.23928421797729885 | 3.740229093377279e-10 | 3.740229093377279e-10 | 0/0 |  |  |
| 1 | 12 | `healthy` | 0.39234181975549676 | 0.39234181975549676 | 6.288413967376565e-10 | 6.288413967376565e-10 | 0/0 |  |  |
| 3 | 4 | `major_degradation` | 0.2131941128459946 | 0.5489803428903006 | 1.3351889972769755e-10 | 4.1092240276788137e-10 | 5/0 | 16.815166893078285 | 8.149849651281746 |
| 3 | 8 | `healthy` | 0.05374084598746667 | 0.054660946984881574 | 2.515678196318507e-10 | 2.51554236103232e-10 | 5/0 | 68.83551676152742 | 8.705702281160924 |
| 3 | 12 | `major_degradation` | 0.022860981344926663 | 0.0933953552972071 | 7.447557176800584e-11 | 1.3189904305663817e-10 | 5/0 | 46.5636147398081 | 24.113273658309634 |
| 5 | 4 | `mild_degradation` | 0.1700512820767665 | 0.305759965713734 | 1.4494523083046297e-10 | 9.463785927936458e-11 | 4/1 | 61.22389164962448 | 77.44178739982824 |
| 5 | 8 | `mild_degradation` | 0.04523821719692235 | 0.05702020763600035 | 7.754213241242157e-11 | 7.587910285075454e-11 | 5/0 | 82.40458737425202 | 31.446343560168497 |
| 5 | 12 | `mild_degradation` | 0.023888533003920628 | 0.033370982444264924 | 5.109866734455777e-11 | 5.262635668229507e-11 | 4/1 | 105.61234073837491 | 52.78691422784636 |
| 7 | 4 | `major_degradation` | 0.05961863505009501 | 0.20811526817726905 | 7.160304341120762e-11 | 7.121704942423568e-11 | 5/0 | 114.61314747967432 | 39.38444524480346 |
| 7 | 8 | `major_degradation` | 0.0051434377395518606 | 0.011077968316579388 | 9.337374203473802e-11 | 9.337397268208415e-11 | 5/0 | 145.49733338371573 | 58.06053366243773 |
| 7 | 12 | `major_degradation` | 0.0031973234619046484 | 0.008987797059591456 | 1.321066583145034e-10 | 1.3210513005998452e-10 | 5/0 | 149.63627713983564 | 96.62001020364328 |
