# V24 Theory Derivation Checklist

Use this checklist before approving manuscript theory text.

| Check | Status | Notes |
|---|---|---|
| Measurement count `N_z=N_uN_s+N_u(N_u-1)` | pass with assumption | Correct for directed SL measurements. Needs conditional-independence statement for reciprocal links. |
| Parameter dimension `N_theta=4N_u+N_s-1` | pass | Follows from UE positions, UE clocks, and non-reference satellite clocks. |
| First satellite clock gauge | pass | `delta_{N_u+1}=0`; reference clock must have no column. |
| Satellite positions excluded from theta | pass with assumption | Requires known ephemeris; uncertainty ignored or external. |
| Measurement sign convention | required edit | Manuscript and code match only if `h_{i,j}` means transmitter `i` to receiver `j`; code tuples are `(receiver, transmitter)`. |
| Jacobian row signs | pass after mapping | Derivatives follow from `e_{i,j}` and clock sign. Add active manuscript derivation or table if reviewer risk is high. |
| `R_z=diag(sigma^2)` | pass for LOS Gaussian | Must state sigmas are fixed range-domain standard deviations. |
| General `R_z=Cov(z)=E{nn^T}` | required edit | Equality with second moment requires zero-mean noise; NLOS can be biased. |
| Likelihood `f_{z|theta}=f_n(z-h(theta))` | pass | Requires additive noise with theta-independent support/regularity. |
| Score derivation `u=J_h^T v` | pass | Correct with `v=-nabla_y log f_n(y)`. |
| General FIM `I=J^T V J` | pass with assumptions | Needs regular score covariance and finite `V`. |
| Gaussian LOS `I=J^T R^{-1}J` | pass with assumption | Correct if `R_z` fixed/known and independent of theta. |
| Covariance derivative term | required edit | If `R_z(theta)`, add trace term or state why excluded. |
| NLOS score covariance | pass with required edit | Correct framework; add density/support/regularity assumptions. |
| Mixed LOS/NLOS diagonal `V` | required edit | Formula correct, but manuscript row index sets do not match active `h(theta)` ordering. |
| CRLB inverse | required edit | State full-rank gauged FIM condition; otherwise pseudoinverse/estimable subspace only. |
| Localization CRLB extraction | required edit | Add `PEB_i=sqrt(trace(C[p_i,p_i]))` and average formula. |
| Synchronization CRLB extraction | required edit | Define clock group, reference exclusion, and seconds/ns conversion. |
| Code measurement model | pass after mapping | `range + transmitter_clock - receiver_clock`, km/range-equivalent clocks. |
| Code sync metric | pass | Reference-relative and excludes reference satellite. |

Recommended disposition: complete the five `must_fix_before_resubmission` items in `V24_THEORY_RED_TEAM_AUDIT.md` before claiming the theory is reviewer-hardened.
