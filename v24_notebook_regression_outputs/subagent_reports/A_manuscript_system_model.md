# Subagent A Manuscript System Model Report

Assigned role: Manuscript System Model Agent

Branch/worktree: `codex/notebook-manuscript-regression-sprint` in `sat-sim`

Files inspected:
- `AGENTS.md`
- `RUN_CODEX.md`
- `PROJECT_STATUS.md`
- `docs/tasks/NEXT.md`
- `docs/tasks/QUEUE.md`
- `../Work-In-Progress/SCL-NTN-TAES-2025-V24.tex` lines 539-648 and 874-976
- `jcls_sim/gauge.py`
- `jcls_sim/parameters.py`
- `jcls_sim/measurements.py`
- `jcls_sim/jacobian.py`
- `jcls_sim/fim.py`
- `jcls_sim/configs.py`

Files changed:
- `v24_notebook_regression_outputs/subagent_reports/A_manuscript_system_model.md`
- `v24_notebook_regression_outputs/subagent_reports/A_manuscript_system_model.json`

Tests/checks run: Static inspection only; no notebook execution, manuscript build, code tests, or simulations were run.

Result: Completed read-only manuscript Section II mapping and wrote the requested report pair.

Risks: The ordered-link sign convention is the main regression risk. The manuscript indexes `h_{i,j}` as node `i` transmitting to UE `j`, while package code stores links as `(receiver_node_id, transmitter_node_id)`. These are consistent only when the mapping is applied explicitly.

Recommended next action: Require every notebook/package measurement row to carry explicit `receiver_node_id`, `transmitter_node_id`, `link_type`, and range-domain units before comparing against V24 manuscript equations.

Scope boundary encountered: I did not edit or execute the manuscript, notebook, package code, tests, figures, or existing result outputs.

## Manuscript Objects Table

| Object | V24 manuscript definition | Section II source | Expected code counterpart | Audit note |
|---|---|---|---|---|
| Measurement count `N_z` | `N_DL + N_SL = N_u N_s + (N_u^2 - N_u)` | `eq:measurement_counts`, lines 571-579 | `len(config.links)` in `V24ScenarioConfig.validate`; link builders in `jcls_sim/configs.py` | Directed SL count implies all ordered UE-to-UE links except self-links. |
| DL graph | Each of `N_s` satellites broadcasts DL reference signals to each of `N_u` UEs | lines 566-569, 571-574 | `downlink_links(num_users, num_satellites)` returns `(user_node_id, satellite_node_id)` | Code tuple is receiver first, transmitter second. |
| SL graph | UEs form a terrestrial ad hoc mesh; directed count is `N_u^2 - N_u` | lines 568, 571-577 | `directed_sidelink_links(num_users)` returns all `(receiver, transmitter)` UE pairs with receiver not equal transmitter | Matches count when all directed links are used. Minimal SL diagnostics are not the full manuscript graph. |
| Measurement vector `z` | Random vector `RV{z} in R^{N_z}`; one measurement per signal; can contain heterogeneous measurements | lines 593, 619-623 | `z = h_theta + noise` in smoke/runner paths; observed arrays in km | Manuscript writes meters; package diagnostics use km. |
| Range model `h(theta)` | Stack of UE-specific range models `V{h}_j(theta)` into `V{h}(theta) in R^{N_z}` | lines 607-615 | `toa_range_vector_from_theta_km(theta, links, satellite_positions_km, ...)` | Code evaluates rows in the order supplied by `links`; manuscript stack order is by receiving UE `j`, excluding self from each `h_j`. |
| Scalar TOA/range model | Measurement from node `i` to UE `j` in meters: `h_{i,j}=||p_i-p_j|| + c(delta_i-delta_j)` with `delta_{Nu+1}=0` | line 606 | `toa_range_model_km(receiver_node_id, transmitter_node_id, ...) = range + transmitter_clock - receiver_clock` | Equivalent if manuscript `(i,j)` maps to code `(receiver=j, transmitter=i)` and clock variables are range-equivalent km. |
| Parameter vector `theta` | `[p_u^T, delta_u^T, delta_s^T]^T in R^{N_theta}` | `eq:parameter_vector`, lines 594-604 | `pack_v24_theta`, `unpack_v24_theta`, `v24_parameter_names` | Code order matches positions, UE clocks, non-reference satellite clocks. |
| Parameter dimension | `N_theta = 4 N_u + N_s - 1` | line 594 | `expected_v24_parameter_dim(num_users, num_satellites)` | Matches. |
| UE positions | ECEF, `p_u = [p_1^T ... p_Nu^T]^T in R^{3Nu}` | line 595 | `ue_positions_km` array shape `(Nu, 3)` | Manuscript says ECEF and meters in measurement equation; code uses km. |
| Satellite positions | Known satellite positions, shared via reference signals/SIB-19 | lines 567, 596-597, 624 footnote | `satellite_positions_km` array shape `(Ns, 3)`; not estimated in theta | Matches known-satellite-position assumption. |
| UE clocks | `delta_u = [delta_1 ... delta_Nu]^T` | lines 598-599 | `ue_clock_offsets_km` and `ue_clock_param_names` | Manuscript clock offsets are time-domain in `c delta`; code stores range-equivalent clock offsets. |
| Satellite clocks | Non-reference satellite vector `[delta_{Nu+2} ... delta_{Nu+Ns}]^T` | lines 600-601 | `non_reference_satellite_clock_offsets_km`; `non_reference_satellite_clock_param_names` | Matches exclusion of first satellite. |
| Reference clock | First satellite is reference; `delta_{Nu+1} = 0` | lines 594, 606 | `reference_satellite_node_id(num_users) = Nu + 1`; `full_clock_dict_km` sets it to `0.0` | Matches V24 gauge. |
| Noise `n` | Additive random vector, distribution specified by multipath model | lines 619-624, 883-918 | generated noise arrays; estimator residual `z - h_pred` | Code paths commonly use Gaussian range noise; NLOS convolution likelihood is not represented by the simple Gaussian FIM helper. |
| Measurement covariance `R_z` | `Cov(z) = E[n n^T]`; for LOS/Rician, `R_z = diag(sigma^2)` | lines 624-640, 946-954 | `range_covariance_from_std_devs_km(range_std_devs_km)` | Matches diagonal Gaussian/Rician case in range-domain km units. |
| Standard deviations `sigma` | Positive range-domain standard deviations; entries may vary by link conditions | line 640, line 954 | `range_std_devs_km`, per-link validation in `V24ScenarioConfig.validate` | Code supports per-link values but does not by itself encode LOS/NLOS distributions. |
| Units | Range measurements in meters; scalar pseudorange `z = c tau_hat`; delay-domain density maps through `c` | line 606, lines 876-907 | Package variables use `_km`; clock offsets are range-equivalent km; clock bounds converted to seconds via `C_KM_PER_S` in runner paths | Unit conversion must be explicit in any notebook regression. |

## Expected Code Counterparts

| Manuscript concept | Expected package representation | Required invariant |
|---|---|---|
| Node ids | UEs `1..Nu`; satellites `Nu+1..Nu+Ns` | Reference satellite node id is exactly `Nu+1`. |
| `theta` layout | `pack_v24_theta(ue_positions_km, ue_clock_offsets_km, non_reference_satellite_clock_offsets_km)` | No reference satellite clock column is present. |
| `h(theta)` rows | `toa_range_vector_from_theta_km(theta, links, satellite_positions_km, Nu, Ns)` | Link order defines row order and must be documented. |
| DL links | `(receiver_ue_id, transmitter_satellite_id)` | Equivalent to manuscript satellite-to-UE DL only if transmitter is the satellite. |
| SL links | `(receiver_ue_id, transmitter_ue_id)` directed pairs | Full manuscript graph uses all ordered UE pairs except self-links. |
| Clock sign | `range + transmitter_clock - receiver_clock` | Equivalent to manuscript line 606 under transmitter-to-receiver interpretation. |
| Clock units | Range-equivalent km | Equivalent to manuscript `c delta` only after converting time offsets by speed of light. |
| `R_z` | `diag(range_std_devs_km**2)` | This is only the diagonal Gaussian/Rician covariance model. |
| FIM input | `gaussian_fim_from_jacobian(jacobian, range_std_devs_km)` | Assumes Section II LOS/Rician Gaussian measurement distribution. |

## Ambiguities

1. Ordered-link notation: manuscript line 606 says measurement from node `i` to UE `j` and uses `c(delta_i-delta_j)`. Code functions use `(receiver_node_id, transmitter_node_id)` and compute `transmitter - receiver`. This is mathematically consistent, but only if manuscript `h_{i,j}` is mapped to code link `(j, i)`.
2. `sat-sim/AGENTS.md` summarizes the sign convention as `h_{i,j}=||p_i-p_j||+c(delta_j-delta_i)`. That can be consistent with the code if `i` is the receiver and `j` is the transmitter, but it is not the same indexing prose as manuscript line 606.
3. Section II says `z` may contain heterogeneous measurements, but the inspected package counterparts mostly implement range-domain TOA rows with Gaussian/Rician covariance. NLOS convolution likelihood support is not visible in the simple `fim.py` helper.
4. Manuscript `V{h}_j` stacks every other node for UE `j`; package row order is delegated to `links`. A regression harness must compare by explicit row metadata, not by assuming identical implicit ordering.
5. Section II uses meters in the displayed model, while package code uses kilometers. Reports and plots may mix meters, kilometers, seconds, nanoseconds, and range-equivalent clock units if conversions are not centralized.

## Mismatches and Regression Risks

| Risk | Severity | Evidence | Consequence |
|---|---|---|---|
| Silent link-order reversal | High | Manuscript line 606 uses transmitter-to-receiver prose; code links are receiver/transmitter tuples | Reversing `(receiver, transmitter)` flips the clock-bias sign while leaving Euclidean range unchanged, making bugs hard to detect from range-only checks. |
| Time-domain versus range-equivalent clocks | High | Manuscript writes `c(delta_i-delta_j)`; code clock variables are `_km` and Jacobian clock derivatives are `+/-1` | Directly comparing clock values without `c` and km/m conversion can produce wrong synchronization metrics or FIM scaling. |
| Full directed SL graph versus reduced diagnostics | Medium | Manuscript count is `N_u^2-N_u`; code also has `minimal_sidelink_links` | Using minimal SL diagnostics as if they represented Section II full mesh would understate measurement count and observability. |
| Gaussian covariance applied outside LOS/Rician case | Medium | Section II distinguishes LOS/Rician Gaussian covariance from NLOS density convolution | CRLB/FIM diagnostics using `diag(sigma^2)` should be labeled Gaussian/Rician or approximate, not general NLOS. |
| Implicit row order | Medium | Manuscript stacks by UE; code stacks according to supplied `links` | Notebook/package regression may falsely pass or fail if rows are compared without link metadata. |

## Bottom Line

The inspected package modules have the right V24 gauge, parameter dimension, theta layout, diagonal range covariance, and receiver/transmitter range model needed to represent Section II. The two places needing the most care are sign convention naming and units: every regression artifact should state that code links are `(receiver, transmitter)` and code clocks are range-equivalent kilometers, whereas the manuscript describes a transmission from node `i` to UE `j` and writes clock offsets in the time-domain through `c delta`.
