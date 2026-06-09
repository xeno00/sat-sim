# Manuscript Result Requirements Matrix

Generated: 2026-06-09

## Manuscripts Inspected

| role | path |
|---|---|
| V23 clean | `C:/Users/James/MIT Dropbox/James Morrison/Academics/MIT/WINSLab/WINS Manuscripts/Morrison, J/SCL-NTN-TAES-2025/All-Version-Archive/V23/SCL-NTN-TAES-2025-V23.tex` |
| V23 tracked | `C:/Users/James/MIT Dropbox/James Morrison/Academics/MIT/WINSLab/WINS Manuscripts/Morrison, J/SCL-NTN-TAES-2025/All-Version-Archive/V23/SCL-NTN-TAES-2025-V23-Tracked-Changes.tex` |
| WIP V24 clean | `C:/Users/James/MIT Dropbox/James Morrison/Academics/MIT/WINSLab/WINS Manuscripts/Morrison, J/SCL-NTN-TAES-2025/Work-In-Progress/SCL-NTN-TAES-2025-V24.tex` |
| WIP V24 tracked | `C:/Users/James/MIT Dropbox/James Morrison/Academics/MIT/WINSLab/WINS Manuscripts/Morrison, J/SCL-NTN-TAES-2025/Work-In-Progress/SCL-NTN-TAES-2025-V24-Tracked-Changes.tex` |

The WIP V24 clean manuscript appears to be the current clean copy for result-claim alignment. No manuscript files were edited.

## Requirement Table

| manuscript_claim_or_figure | V23_location | WIP_location | required_metric | required_scenario | current_supported_by_pipeline | confidence | blocking_issue |
|---|---|---|---|---|---|---|---|
| Fig. 4 localization vs number of satellites | V23 Section VI, Fig. `pos_vary_ues.pdf`; text around network-size results | V24 Section VI, Fig. `pos_vary_ues.pdf`; revised to distinguish baseline, Step B, and C7 candidate | average UE 3D localization error in meters | Starlink-like LEO, MIT/Stata UEs, sigma_delta=1 us, operation time 0.5 s, cooperative Nu=3,5,7 | legacy-surgical prior-region has strong primary card; C7 manuscript recreation has weaker primary card | medium | Need normalized benchmark-card and bounded candidate figure generation with V24 metrics. |
| Fig. 5 synchronization vs number of satellites | V23 Section VI, Fig. `sync_vary_ues.pdf` | V24 Section VI, Fig. `sync_vary_ues.pdf`; reference-relative clock metric wording | average synchronization error in ns | same network-size scenario; reference-relative and excluding reference satellite for V24 | legacy-surgical reports legacy all-clock sync; C7 reports V24-compatible sync | medium-low | Need recompute legacy-surgical sync in V24 reference-relative metric before manuscript use. |
| Fig. 6 localization vs clock standard deviation | V23 Section VI, Fig. `pos_vary_clock.pdf` | V24 Section VI, Fig. `pos_vary_clock.pdf`; C7 refinement marked validation-dependent | average UE 3D localization error in meters | Nu=3,Ns=10; sweep sigma_delta, including 1 us | legacy clock-sweep replay reproduces strong legacy behavior; C7 clock sweep unstable at high clock sigma | low | Need bounded legacy-surgical clock-sweep candidate; do not use current C7 high-clock result as final. |
| Fig. 7 synchronization vs clock standard deviation | V23 Section VI, Fig. `sync_vary_clock.pdf` | V24 Section VI, Fig. `sync_vary_clock.pdf`; ns metric and reference-relative caveat | average synchronization error in ns | Nu=3,Ns=10; sweep sigma_delta | legacy replay has strong legacy-only behavior; legacy-surgical has primary point but not full sweep; C7 sparse sweep unstable | low | Need full metric-normalized clock-sweep validation for selected path. |
| CRLB localization/synchronization figures | V23 CRLB figures `pos_crlb_0dB_0dB.pdf`, `sync_crlb_0dB_0dB.pdf` | V24 CRLB text hardened around full gauged FIM, rank reportability, and reference exclusion | finite full-gauged CRLB only when relevant subspace estimable | manuscript CRLB settings | package-native FIM/bounds tests and diagnostics exist | medium | Need decide whether final manuscript should use rank feasibility, finite CRLB candidate, or remove/replace legacy CRLB panels. |
| Sub-meter localization claim | V23 claims JCLS below 1 m and best networks around 10 cm | V24 makes more guarded, provenance-dependent claims | localization error in meters | validated figure families only | legacy-surgical Step B supports sub-meter primary card; C7 package does not | medium | Must not mix C7 package outputs with legacy-surgical claims. |
| Refined Step 3 benefit claim | V23 claims refined JCLS improves localization and sync | V24 says refined C7 remains validation-dependent | Step C improvement over Step B | network and clock sweeps | legacy truth-gated replay supports; nontruth legacy-surgical mixed; C7 mixed/unstable | low | Step C is not yet final defensible across figure families. |
| Cooperation gain claim | V23/V24 claim cooperation improves information structure | V24 excludes Nu=1 from cooperative JCLS semantics | Step B/C vs baseline localization/sync | Nu=3,5,7 cooperative curves | likely supported by legacy-surgical Step B; needs candidate figures | medium | Single-UE rows must remain baseline/safeguard diagnostics only. |
| Clock drift / clock error behavior | V23 used clock standard deviation sweep and operation time 0.5 s | V24 clarifies offset/drift and dynamic caveats | localization/sync vs sigma_delta | Nu=3,Ns=10, clock sweep | not yet defensibly supported by clean selected path | low | Need normalized clock-sweep candidate before manuscript claim. |

## Safe Claims Now

- The V24 manuscript theory now uses a gauged parameter convention and reference-relative synchronization metric.
- The package-native code has tested measurement/Jacobian/FIM/metric layers.
- Step B residual LM without truth-state acceptance is the strongest currently defensible estimator subpath.
- Legacy-surgical prior-region outputs are the most promising route for reproducing manuscript-scale performance without estimator-decision truth gates.

## Unsafe Claims Now

- Do not claim C7 package-native outputs are manuscript-ready.
- Do not claim Step C is broadly validated.
- Do not use legacy all-clock synchronization numbers as V24 reference-relative synchronization without recomputation.
- Do not treat Nu=1 as cooperative JCLS.
- Do not use secondary `N_u=3,N_s=4` stress results as primary evidence.
