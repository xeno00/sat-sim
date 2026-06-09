# V24 Theory Red-Team Audit

## Executive Summary

Verdict: `theory_pass_with_required_edits`.

The V24 theoretical chain is broadly defensible: the parameter dimension follows from the first-satellite clock gauge, the Gaussian/Rician Fisher information reduces to `J_h^T R_z^{-1} J_h`, and the general NLOS score-covariance form is the right way to avoid unsupported scalar NLOS closed forms. The implementation in `sat-sim` is also mostly consistent with the V24 gauged parameter vector after unit conversion.

The audit found reviewer-risk issues that should be fixed before resubmission:

1. The measurement sign/index convention is not explicit enough. The manuscript writes `h_{i,j}=||p_i-p_j||+c(delta_i-delta_j)` for a measurement "from i to j"; code uses `(receiver, transmitter)` tuples and `range + transmitter_clock - receiver_clock`. These are consistent only if manuscript index `i` is the transmitter and `j` is the receiver, and if the sign convention for `delta` is defined accordingly.
2. The mixed LOS/NLOS FIM section assumes rows `1..N_DL` are DL and remaining rows are SL, but the manuscript definition of `h(theta)=[h_1^T ... h_Nu^T]^T` with `h_j=[h_{1,j},...,h_{Nu+Ns,j}]` interleaves SL and DL rows by receiver. Either reorder `h`/`z` or define DL/SL index sets abstractly by link type.
3. The Gaussian FIM `J_h^T R_z^{-1} J_h` is correct only when `R_z` is treated as known/fixed and independent of `theta`. If SNR or link variance depends on geometry, the missing covariance-derivative trace term must be excluded by assumption.
4. The equation `R_z = Cov(z) = E{n n^T}` is only generally true for zero-mean noise. NLOS excess-delay models can be biased; keep `R_z` for LOS Gaussian covariance or define a second moment separately.
5. CRLB extraction is under-specified in text and captions: square-root versus MSE bound, inverse versus pseudoinverse/rank-deficient handling, clock group, reference-clock exclusion, and seconds/ns conversion should be explicit.
6. NLOS regularity/support assumptions need one sentence. The score-covariance FIM requires a valid differentiable density, finite score covariance, support independent of `theta` or handled boundary terms, and `E{u}=0`.

No manuscript source, PDFs, bibliography, response letters, PSFrag, Work-In-Progress figures, generated manuscript PDFs, or existing manuscript result files were edited for this audit. The clean V24 TeX file already contained manual edits from the preceding manuscript-alignment task in this workspace; this audit did not add more manuscript edits.

## Part A - Extracted V24 Theory Statements

Source inspected: `../Work-In-Progress/SCL-NTN-TAES-2025-V24.tex` in the current workspace state.

| Topic | Manuscript location | Extracted statement |
|---|---:|---|
| Measurement counts | `eq:measurement_counts`, near lines 572-579 | `N_DL=N_u N_s`, `N_SL=N_u^2-N_u`, `N_z=N_DL+N_SL=N_u^2+N_u N_s-N_u`. |
| Satellite positions | system model near lines 565-566 | Satellite positions are known from GNSS and shared through reference signals/SIB-19 timing context. |
| Gauge/reference clock | system model near lines 593-596 | First satellite is reference; `delta_{N_u+1}=0`; `N_theta=4N_u+N_s-1`. |
| Parameter vector | `eq:parameter_vector`, near lines 595-605 | `theta=[p_u^T, delta_u^T, delta_s^T]^T`, with UE positions, UE clocks, and non-reference satellite clocks. |
| Measurement model | near lines 606-623 | `h_{i,j}=||p_i-p_j||+c(delta_i-delta_j)`, `h(theta)=[h_1^T ... h_Nu^T]^T`, `z=h(theta)+n`. |
| Covariance | `eq:rician_cov_as_expectation`, near lines 624-640 | `R_z=Cov(z)=E{n n^T}` and `sigma` entries are range-domain standard deviations. |
| Multipath noise | `subsec:measurementmodel`, near lines 875-929 | Scalar range model `z=c tau_hat_(1)=h(theta)+n`; vector noise `n=c(tau_e+tau_MI+tau_m)`; range density transform; convolution `f_n=f_c tau_e * f_c tau_MI * f_c tau_m`; likelihood `f_{z|theta}=f_n(z-h(theta))`. |
| LOS/Rician | near lines 931-964 | `tau_e=0`, `tau_MI ~= 0`, `c tau_m ~ N(0,R_z)`, `R_z=diag(sigma^2)`, `z|theta ~ N(h(theta),R_z)`. |
| NLOS | near lines 966-975 and `subsec:rayleigh_fim` | Use `f_n^NLOS=f_{c tau_e}^NLOS * f_{c tau_MI}^NLOS * f_{c tau_m}` and score covariance, not a scalar closed form. |
| Information inequality | `subsec:crlb`, near lines 1000-1049 | General biased-estimator information inequality, then unbiased MSE and total MSE trace bound. |
| Score/FIM | near lines 1051-1122 | `u=nabla_theta log f_z(z;theta)`, `I_theta=E{u u^T}`, `y=z-h(theta)`, `v(y)=-nabla_y log f_n(y)`, `u=J_h^T v`, `V=E{v(n)v(n)^T}`, `I_theta=J_h^T V J_h`. |
| LOS FIM | `eq:rician_fim`, near lines 1126-1151 | For Gaussian range noise, `v=R_z^{-1}y`, `V=R_z^{-1}`, hence `I_theta=J_h^T R_z^{-1} J_h`. |
| Mixed LOS/NLOS | `subsec:combined_fim`, near lines 1223-1266 | Define DL and SL row index sets and use diagonal `V` with LOS entries `[R_z^{-1}]_ii` and NLOS entries `E{v_i(n)^2}`. |
| CRLB figures | captions/text near lines 1206-1268 | Captions say "CRLB for average 3D UE localization error" and "CRLB for average node synchronization"; extraction formula and units are not stated in active text. |

## Part B - Independent Derivations

### Measurement Count

Each of `N_u` UEs receives one DL measurement from each of `N_s` satellites, so

```text
N_DL = N_u N_s.
```

If sidelinks are directed and each UE receives one measurement from every other UE, then each receiver has `N_u-1` UE transmitters, so

```text
N_SL = N_u (N_u - 1) = N_u^2 - N_u.
```

Thus

```text
N_z = N_u N_s + N_u (N_u - 1) = N_u^2 + N_u N_s - N_u.
```

This matches the manuscript if SL measurements are directed. The independence assumption for both directions of the same UE pair must be stated carefully: reciprocal links can share clocks, geometry, scheduling, channel environment, and possibly noise sources, so conditional independence is an assumption, not automatic.

### Parameter Dimension

The estimated UE positions have dimension `3N_u`. The UE clock vector has dimension `N_u`. The satellite clock vector excludes the first satellite because `delta_{N_u+1}=0`, so it has dimension `N_s-1`. Therefore

```text
N_theta = 3N_u + N_u + (N_s - 1) = 4N_u + N_s - 1.
```

This matches the manuscript and package helper `expected_v24_parameter_dim(num_users,num_satellites)`.

### Measurement Sign and Jacobian Row

Let

```text
e_{i,j} = (p_i - p_j) / ||p_i - p_j||.
```

For the manuscript scalar model

```text
h_{i,j}=||p_i-p_j||+c(delta_i-delta_j),
```

with `i` interpreted as transmitter and `j` as receiver, the derivatives are:

```text
d h_{i,j}/d p_i = e_{i,j}^T          if node i is a UE,
d h_{i,j}/d p_j = -e_{i,j}^T         if node j is a UE,
d h_{i,j}/d delta_i = c              if delta_i is in theta,
d h_{i,j}/d delta_j = -c             if delta_j is in theta.
```

If `i` is a satellite, satellite position is known and there is no satellite-position column. If `i=N_u+1`, the reference-satellite clock has no column. If `j` is a UE receiver, `d h/d p_j=-e_{i,j}^T` and `d h/d delta_j=-c`.

The package uses links as `(receiver, transmitter)` and computes `range + transmitter_clock - receiver_clock`. This matches the manuscript equation only under the mapping `i=transmitter`, `j=receiver`. Without that explicit mapping, a reviewer could read the code and manuscript as opposite sign conventions.

### Score and FIM

From

```text
f_{z|theta}(z|theta)=f_n(z-h(theta)),
y(theta)=z-h(theta),
```

and `J_h = partial h / partial theta` with shape `N_z x N_theta`,

```text
nabla_theta log f_n(y(theta))
  = (partial y / partial theta)^T nabla_y log f_n(y)
  = (-J_h)^T nabla_y log f_n(y)
  = J_h^T v(y),
```

where `v(y)=-nabla_y log f_n(y)`. Hence

```text
I_theta = E{u u^T} = J_h^T E{v(n)v(n)^T} J_h = J_h^T V J_h.
```

Dimensions:

```text
J_h in R^{N_z x N_theta}
v in R^{N_z}
V in R^{N_z x N_z}
I_theta in R^{N_theta x N_theta}.
```

The derivation is correct, provided the density is regular and the score covariance exists.

### Gaussian LOS Case

For `n ~ N(0,R_z)`,

```text
log f_n(y) = -1/2 y^T R_z^{-1} y + const
nabla_y log f_n(y) = -R_z^{-1} y
v(y) = R_z^{-1} y.
```

Thus

```text
V = E{R_z^{-1} n n^T R_z^{-1}}
  = R_z^{-1} E{n n^T} R_z^{-1}
  = R_z^{-1}.
```

Therefore `I_theta=J_h^T R_z^{-1}J_h`. This is unit-consistent if all range states and sigmas use the same range unit. The manuscript uses meters and seconds with a factor `c`; the package uses km and range-equivalent km clocks. Tests verify equivalence after conversion.

If `R_z=R_z(theta)`, the Gaussian FIM has the additional term

```text
1/2 tr(R_z^{-1} dR_z/dtheta_a R_z^{-1} dR_z/dtheta_b).
```

The manuscript formula is correct only if `R_z` is fixed/known at the operating point or independent of `theta`.

### NLOS Case

The general form

```text
I_theta=J_h^T V J_h,  V=E{v(n)v(n)^T}
```

with `v(y)=-nabla_y log f_n^NLOS(y)` is the correct defensible expression. It avoids resurrecting older scalar NLOS moment formulas.

Required assumptions:

- `f_n^NLOS` is a valid differentiable density.
- The support is independent of `theta`, or boundary terms are negligible/handled.
- The regularity condition gives `E{u}=0`.
- `V` is finite.
- Conditional independence across measurements is needed before setting `V` diagonal.

The convolution with the Gaussian timing-error component can give full support and help regularity, but the manuscript should say this or state the needed regularity assumptions.

### Mixed LOS/NLOS Case

If rows are conditionally independent and row sets correctly map to measurement ordering, then

```text
V_ii = [R_z^{-1}]_ii                    for LOS rows,
V_ii = E{[v(n)]_i^2}                    for NLOS rows,
V_ij = 0                                for i != j.
```

The formula is valid. The manuscript row-index definition is risky because the active `h(theta)` definition does not order all DL rows first and all SL rows second. This is a must-fix indexing clarification.

## Part C - Hidden Assumptions and Reviewer Risks

| Assumption | Where it appears | Required for | Risk | Recommended clarification |
|---|---|---|---|---|
| Satellite positions are known exactly | System model and SIB-19 footnote | Excluding satellite positions from `theta` and `J_h` | medium | State satellite ephemeris uncertainty is neglected or treated as external. |
| First satellite fixes global clock gauge | System model | Identifiability of clock offsets | low | Keep, but repeat that the reference satellite clock has no FIM column. |
| Directed SL rows are independent | Measurement counts and `V` diagonal | `N_SL=N_u(N_u-1)` and diagonal `V` | high | State conditional independence or use a non-diagonal score covariance. |
| `R_z` and `V` are independent of `theta` | LOS FIM | Omitting covariance-derivative FIM term | high | Add fixed/known operating-point statement. |
| Link sigmas are selected externally | Measurement noise and code | `J^T R^{-1}J` only | high | State sigmas are fixed range-domain inputs for FIM evaluation. |
| NLOS density regularity/support | NLOS FIM | Score covariance FIM | medium | Add regularity/support sentence, noting Gaussian timing convolution if used. |
| Directed reciprocal SL links counted | Measurement counts | `N_u^2-N_u` | medium | Explain `(i,j)` and `(j,i)` are distinct directed measurements under conditional independence. |
| Manuscript meters vs code km | Results/code | Unit consistency | low | Keep conversion statement in reports/tests; manuscript can remain meters. |
| Clock seconds vs range-equivalent code clocks | Theory/code | Clock columns and sync metrics | medium | State clock offsets in manuscript are seconds and enter range through `c`; code stores range-equivalent clocks. |
| Sync metric reference-relative | Results/code | Figure labels and captions | medium | Keep recent caption clarification; also clarify CRLB sync bounds. |
| CRLB extraction uses gauged vector | CRLB figures/code | Avoid all-clock singular gauge | high | State bounds are from gauged `theta`, not all-clock legacy state. |
| FIM inverse vs pseudoinverse | CRLB text/code | Rank-deficient cases | high | State full-rank condition; if not full rank, do not report finite CRLB without subspace analysis. |
| `R_z=Cov(z)=E{nn^T}` | covariance equation | Covariance interpretation | medium | Correct to `Cov(n)` generally, or restrict equality to zero-mean LOS Gaussian noise. |

## Part D - CRLB Extraction Audit

The active manuscript does not provide enough detail to verify the plotted CRLB semantics from text alone. The captions say "CRLB for average 3D UE localization error" and "CRLB for average node synchronization," but do not define whether the plotted quantity is MSE, RMSE, PEB, square-root CRLB, or mean of per-node standard-deviation bounds.

Defensible extraction from the gauged covariance `C=I_theta^{-1}` should be:

```text
PEB_i = sqrt(trace(C[p_i,p_i]))
average localization bound = (1/N_u) sum_i PEB_i
```

for average 3D UE localization error in meters.

For synchronization, a defensible metric is:

```text
clock_std_k = sqrt(C[delta_k,delta_k])
average sync bound = mean over UE and non-reference satellite clock rows
```

with the reference satellite excluded and seconds converted to ns. If the manuscript intends UE clocks only or all non-reference node clocks, that group must be named.

The package helper `bounds.py` uses a full gauged V24 dimension, extracts per-UE PEBs as square roots of 3D position block traces, extracts clock standard-deviation bounds from UE and non-reference satellite clock blocks, excludes the reference clock by construction, and uses inverse or pseudoinverse depending on rank/conditioning metadata. It also marks manuscript CRLB undefined when the relevant full gauged FIM is rank deficient.

Must-fix: the manuscript should define the CRLB extraction formula and rank condition before interpreting Figs. `pos_crlb` and `sync_crlb`.

## Part E - Reference Audit Summary

| Citation key | Repo bibliographic entry | Claim supported | Audit result |
|---|---|---|---|
| `kay` | Kay, *Fundamentals of Statistical Signal Processing: Estimation Theory*, 1993 | MLE/GN/estimation and CRLB regularity background | Supports; use for information inequality if no more specific CRLB citation is added. |
| `WanSheMazShiWin:J14` | Wang, Shen, Mazuelas, Shin, Win, "On OFDM Ranging Accuracy in Multipath Channels," IEEE Systems Journal, 2014 | OFDM/ranging Fisher information context | Supports ranging/FI context, not the full JCLS parameter FIM. Externally verified title/venue/year. |
| `OTDOA_RFAP` | Kong and Kim, "Error Analysis of the OTDOA From the Resolved First Arrival Path in LTE," IEEE TWC, 2016 | RFAP and multipath/NLOS error components | Supports RFAP error modeling; manuscript should avoid overclaiming exact applicability to NTN/PRS without adaptation. Externally verified title/claim summary. |
| `EmeDhiBue:TIT25` | Emenonye, Dhillon, Buehrer, "Fundamentals of LEO-Based Localization," IEEE TIT, 2025 | Prior LEO localization FI | Supports prior LEO localization FI; not a JCLS/clock-offset gauge substitute. Externally spot-checked. |
| `ConMazBarLinWin:J19` | Conti et al., "Soft Information for Localization-of-Things," Proc. IEEE, 2019 | SCI/SFI and soft information | Supports soft-information framing; not a proof of this specific C7 numerical implementation. Externally verified. |
| `WymLieWin:J09` | Wymeersch, Lien, Win, "Cooperative Localization in Wireless Networks," Proc. IEEE, 2009 | Cooperative localization and random-walk/message-passing context | Supports cooperation context; not a specific NTN clock-gauge FIM. |
| `3GPP:TS:36.211:V18.0.1` | 3GPP/ETSI E-UTRA physical channels and modulation | PRS waveform details | Supports LTE/E-UTRA PRS details; if manuscript claims NR PRS, check whether NR spec should also be cited. Externally verified through ETSI PDF. |
| `3GPP:TR:38.811:V15.4.0` | 3GPP NR NTN study | NTN channel/LOS/NLOS context | Supports NTN environment/channel guidance; external spot-check was secondary, not official 3GPP. |
| `camajori_tedeschini_feasibility_2023` | Scientific Reports 2023 feasibility study | 5G positioning/ranging-noise inspiration | Supports 5G positioning feasibility context; using its CRLB expression as ranging variance should be explained as a modeling choice. Externally verified. |

External spot-check sources used include public indexed pages for Wang et al. 2014, Conti et al. 2019, Kong-Kim 2016, Camajori Tedeschini et al. 2023, ETSI TS 36.211 V18.0.1, and LEO localization metadata. No bibliography file was edited.

## Part F - Code Consistency Audit

| Manuscript equation/convention | Expected implementation convention | Current code convention | Status |
|---|---|---|---|
| `delta_{N_u+1}=0` | Reference satellite omitted/fixed | `gauge.reference_satellite_node_id(num_users)=num_users+1`; reference omitted from V24 clock ids | matches |
| `N_theta=4N_u+N_s-1` | Gauged theta dimension | `expected_v24_parameter_dim` returns `4*num_users+num_satellites-1` | matches |
| `theta=[p_u,delta_u,delta_s]` | UE positions, UE clocks, non-reference sat clocks | `parameters.pack_v24_theta` same order | matches |
| `h_{i,j}=range+c(delta_i-delta_j)` | If `i=transmitter`, `j=receiver`, use transmitter minus receiver | `toa_range_model_km(receiver, transmitter)` returns `range + transmitter_clock - receiver_clock` | matches_after_index_mapping |
| `J_h` row signs | Receiver position plus direction, transmitter UE position minus direction under receiver/transmitter tuple | `analytic_toa_jacobian_km` matches finite sign tests for package tuple convention | matches_after_index_mapping |
| Manuscript meters/seconds | Internal code may use km/range-equivalent clock | Code positions/clocks/sigmas in km; metrics convert position to m and clock to seconds/ns | matches_after_unit_conversion |
| `R_z=diag(sigma^2)` | Range-domain covariance | `fim.range_covariance_from_std_devs_km` returns `diag(sigmas**2)` | matches_after_unit_conversion |
| Gaussian FIM | `J.T @ R^-1 @ J` | `gaussian_fim_from_jacobian` implements weighted `J.T J` | matches |
| NLOS score covariance | Need generic `V` support | Package FIM helper currently Gaussian only; NLOS score covariance is theory-only | code_missing |
| Mixed LOS/NLOS row sets | Correct row mapping by link type | Code link configs often order DL first then SL; manuscript `h` ordering interleaves rows | manuscript_mismatch |
| CRLB covariance | Inverse if full rank, pseudoinverse diagnostic otherwise | `covariance_from_fim` uses inverse or pinv with metadata; reportability gates rank-deficient manuscript readiness | implementation_detail |
| Localization CRLB | Average per-UE PEB | `average_ue_peb_from_covariance` averages `sqrt(trace(position block))` | matches |
| Synchronization CRLB/metric | Reference-relative, reference excluded | `metrics` and `bounds` exclude reference by construction | matches |
| Legacy notebook | Should not define V24 final theory | Reports indicate legacy all-clock/post-hoc slicing/truth-gated paths | legacy_only |

Focused tests run:

```text
python -m unittest tests.test_measurements tests.test_jacobian tests.test_fim tests.test_bounds tests.test_metrics tests.test_ordered_link_units
```

Result: 48 tests passed.

## Part G - Fix Recommendations

| Priority | Recommendation | Exact manuscript edit intent |
|---|---|---|
| must_fix_before_resubmission | Clarify measurement index/sign convention | Add: "In `h_{i,j}`, node `i` is the transmitting node and node `j` is the receiving UE; equivalently, implementation link tuples are ordered `(receiver, transmitter)` and evaluate `range + transmitter clock - receiver clock`." |
| must_fix_before_resubmission | Fix mixed DL/SL row-index sets | Replace contiguous `N_DL={1,...,N_DL}` and `N_SL={N_DL+1,...}` with abstract sets `D_DL` and `D_SL` or reorder `h(theta)` so DL rows are first. |
| must_fix_before_resubmission | State fixed covariance assumption | Add near LOS FIM: "`R_z` is treated as a known range-domain covariance fixed at the operating point; derivatives of link variance with respect to `theta` are not included." |
| must_fix_before_resubmission | Clarify CRLB extraction | Add formulas for `PEB_i=sqrt(trace(C[p_i,p_i]))` and synchronization standard-deviation averaging over specified clock group with reference excluded. |
| must_fix_before_resubmission | State full-rank/gauged CRLB condition | Add that CRLBs are computed from the gauged parameter vector; if the gauged FIM is singular, finite manuscript CRLBs require explicit estimable-subspace treatment. |
| should_fix | Correct covariance wording | Change `R_z=Cov(z)=E{nn^T}` to `R_z=Cov(n)` and state equality with `E{nn^T}` only for zero-mean noise. |
| should_fix | Add NLOS regularity sentence | State valid differentiable density, finite score covariance, support conditions, and conditional independence needed for diagonal `V`. |
| should_fix | Directed SL independence | Add a sentence that both directions are modeled as distinct conditionally independent observations, if that is intended. |
| should_fix | Satellite ephemeris uncertainty | State satellite positions are known inputs and ephemeris error is neglected or external to the bound. |
| nice_to_have | NR PRS citation check | If the text is truly NR/5G PRS rather than LTE/E-UTRA PRS, add/verify the relevant NR physical-channel citation. |

## Part H - Pass/Fail Rubric

Final verdict: `theory_pass_with_required_edits`.

Rationale: the core FIM derivation is mathematically correct under standard regularity/fixed-covariance assumptions, and the package-native code largely matches the gauged V24 convention after unit conversion. However, the manuscript must clarify measurement indexing/sign, mixed DL/SL row indexing, fixed covariance assumptions, NLOS regularity, and CRLB extraction before the theory is reviewer-hardened.

## Protected-File Check

For this audit task, files intentionally edited are limited to sat-sim reports and sat-sim status/task pointers. No new manuscript figures or simulations were generated. No manuscript source, manuscript PDFs, response letters, bibliography, PSFrag, Work-In-Progress figures, generated manuscript PDFs, or existing manuscript result files were edited during this audit.

Pre-existing workspace note: `../Work-In-Progress/SCL-NTN-TAES-2025-V24.tex` contains manual edits from the immediately preceding manuscript-alignment task in this same session. This audit did not revert or extend them.
