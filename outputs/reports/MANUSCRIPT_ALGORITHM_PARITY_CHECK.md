# Manuscript Algorithm Parity Check

## Executive Summary

The manuscript and current defensible code agree on the high-level three-stage
JCLS structure: DL-only coarse localization, cooperative joint position/clock
LM, and a dynamic soft-information refinement. The current defensible code path,
however, is more specific and more conservative than the manuscript text:

- Stage A / Step 1 is DL-only, per-UE weighted GN and is also the
  without-cooperation baseline.
- Stage B / Step 2 is cooperative JCLS LM-only with residual-cost/trust-region
  acceptance and no truth gate.
- Stage C / Step 3 is the C7 mode
  `step_c7_residual_cov_sync_safeguard`, using typed block-extracted,
  diagonal-clipped residual-scaled covariance, an appended clock-drift state,
  and non-truth synchronization safeguards.

The main parity risk is that the manuscript currently describes a generic
Gaussian SCI/SFI or EKF-like refinement and states that numerical results use
`x=theta`, `F=I`, and fixed clock offsets over 0.5 s. The current defensible C7
candidate instead uses `x=[theta, clock_drift]` and is still non-final and not
manuscript-ready. The manuscript should not claim final refined-JCLS figure
performance until the final algorithm and figure path are approved.

## Inputs Inspected

- `../AGENTS.md`
- `AGENTS.md`
- `RUN_CODEX.md`
- `PROJECT_STATUS.md`
- `docs/tasks/NEXT.md`
- `docs/tasks/QUEUE.md`
- `../Work-In-Progress/SCL-NTN-TAES-2025-V24.tex`
- `../Work-In-Progress/SCL-NTN-TAES-2025-V24.pdf` was available but not parsed;
  the source was used for exact labels and line references.
- `JCLS_Simulation.ipynb` was statically searched; it was not executed.
- `jcls_simulation.py` was not available.
- `jcls_sim/algorithm.py`
- `jcls_sim/migration.py`
- `jcls_sim/figure_generation.py`
- `scripts/run_step_c7_residual_cov_sync_safeguard.py`
- `scripts/run_c7_candidate_figures.py`
- `scripts/run_c7_manuscript_figure_recreation.py`
- Step B, C7, C7 human-review, C7 candidate-validation, C7 provenance, and
  current graph-status reports under `outputs/reports/`.

## Part A - Manuscript Algorithm Extraction

| Component | Section/source | Equation labels | Prose summary | Variables | Assumptions | Step | Conceptual or used in results |
|---|---|---|---|---|---|---|---|
| Algorithm overview | Sec. `Algorithm Overview`, lines 1286-1294 | none | Estimate `theta^(n)` from `Z^(1:n)` in three sequential steps. | `theta^(n)`, `Z^(1:n)`, `p_u^(1)` | First two steps use first interval; Step 3 repeats as new measurements arrive. | 1/2/3 | Conceptual framework and intended numerical structure. |
| Step 1 coarse localization | Sec. `Coarse Localization`, lines 1296-1348 | `eq:step1optimization`, `eq:ue_models`, `eq:parameter_vector` | Each UE estimates its position from its own first-interval measurements; Rician likelihood becomes WNLS; solved by GN. | `p_i`, `z_i`, `h_i(p_i)`, `R_z,i`, `J_h,i` | Clock variables are padded/fixed to zero in the single-position subproblem; DL geometry needs enough non-collinear satellite measurements. | Step 1 | Used as initialization and as the conventional no-cooperation baseline. |
| Step 2 joint LM | Sec. `Initial Joint Localization and Synchronization`, lines 1350-1383 | `eq:step2optimization`, `eq:measurement_model`, `eq:parameter_vector` | Spatial cooperation refines the coarse state by weighted LM over joint positions and non-reference clocks. | `theta`, `z`, `h(theta)`, `R_z`, `J_h`, `lambda_m` | Starts from Step 1 positions and zero non-reference clocks; uses first interval only. | Step 2 | Used conceptually; current code uses residual/trust-region acceptance details not stated in manuscript. |
| Step 3 SCI/SFI refinement | Sec. `Joint Localization and Synchronization Refinement`, lines 1386-1388 | none | Dynamic refinement combines SCI prediction and SFI measurement likelihoods to update a posterior over network state. | `x`, `theta`, `Z^(1:n)`, DL/SL measurements | Soft information is probability-distribution information rather than hard decisions. | Step 3 | Conceptual. The prose is broader than the current defensible C7 code path. |
| State vector and projection | Sec. `Soft Context Information and Dynamics Prediction`, lines 1391-1398 | `eq:space_projection` | State `x` includes at least `theta`; `Pi x = theta`; `x` may include velocity, acceleration, or clock drift. | `x`, `theta`, `Pi`, `M`, `N_theta` | Bayesian random-vector state; projection maps dynamic state to JCLS parameter vector. | Step 3 | Conceptual and partly matched by C7 through theta-plus-drift. |
| Dynamics prediction | Sec. `Soft Context Information and Dynamics Prediction`, lines 1399-1420, 1486-1490 | `eq:pred`, `eq:state_transition` | HMM-style prediction with SCI and linear state transition `x(n+1)=F x(n)+w(n)`; covariance prediction `P_pred=F P F^T+Q`. | `Phi`, `F`, `Q`, `P`, `w`, `x_pred`, `P_pred` | Random-walk/linear dynamics; independent UE mobility model. | Step 3 | Conceptual. Generic package helper has this; current C7 candidate uses direct stacked-epoch residual update rather than a generic F/Q loop. |
| Clock-drift augmentation | Sec. `Soft Context Information and Dynamics Prediction`, lines 1421-1485 | clock block equations near lines 1425-1477 | Augment non-reference clock offsets with clock-drift components and propagate offset by `Delta t * dot_delta`. | `delta`, `dot_delta`, `x_c`, `F_c`, `Q_c`, `Delta t` | Drift affects measurements through predicted clock offsets, not direct TOA state components. | Step 3 | Conceptually matches C7, but manuscript numerical-results text says results use `x=theta`, `F=I`. |
| Gaussian product / MAP update | Sec. `Soft Feature Information and Measurement Update`, lines 1492-1619 | `eq:update` plus posterior covariance/mean/MAP equations | Pairwise measurement likelihoods multiply the predicted prior; Gaussian prior and linearized likelihood yield information-form posterior covariance/mean and equivalent MAP estimate. | `L_z`, `R_z`, `J_h`, `mu`, `P_hat`, `x_pred`, `h_pred` | Pairwise independent measurements, Gaussian prior, linearized likelihood, range-domain noise covariance. | Step 3 | Conceptual. Current C7 uses a related one-step linearized update with residual-scaled covariance and safeguards. |
| Numerical specialization | Sec. `Numerical Results`, lines 1733-1759 | `eq:crlb`, `eq:state_transition` | Results are stated to use short-interval specialization `x=theta`, `F=I`, fixed UE and non-reference satellite clock offsets over 500 ms; drift model optional if significant. | `x`, `theta`, `F`, `sigma_m`, `sigma_delta` | Stationary UEs near MIT Stata; fixed clock-offset realizations; no steady-state convergence claim. | Step 3/results | Mismatch with the current defensible C7 candidate, which uses clock drift. |
| Synchronization metric | Sec. `Numerical Results`, lines 1808-1817 and 1843-1845 | figure labels `fig:sync_sats`, `fig:sync_clocks` | Average node synchronization error after 0.5 s, reported in ns in plots/text. | clock offsets, `sigma_delta`, average sync error | Error is tied to UE and non-reference satellite clock estimates. | Results | Needs explicit reference-clock/exclusion convention to match code. |
| Single-UE/no-cooperation semantics | Sec. intro/system/results, lines 422, 1779-1782 | `eq:step1optimization` | A single UE is under-constrained for joint position and clock differences; single-UE networks use conventional TOA localization and cannot exploit cooperation. | `N_u=1`, DL-only measurements, clock offsets | No SL cooperation exists for one UE. | Step 1/results | Conceptually matches C7 recreation, but candidate validation also has single-UE C7 fallback rows that must not be described as sync improvement. |

## Part B - Code Algorithm Extraction

| Component | File/function/class | Estimator mode | Input/output state | Units | Covariance convention | Acceptance/safeguard logic | Truth usage | Fallback/output artifacts |
|---|---|---|---|---|---|---|---|---|
| Gauge and theta | `jcls_sim/gauge.py`, `jcls_sim/parameters.py` | V24 gauged theta | UE positions, UE clocks, non-reference satellite clocks; reference satellite is node `Nu+1` and excluded. | positions km, clocks range-domain km | n/a | n/a | no truth used | `N_theta=4*Nu+Ns-1`; order `[UE positions, UE clocks, non-reference satellite clocks]`. |
| Measurement model | `jcls_sim/measurements.py`, `jcls_sim/jacobian.py` | range-domain TOA | `z=h(theta)+n`; link rows are `(receiver, transmitter)`. | range km | `R=diag(sigma^2)` | n/a | no truth used for estimator model | `h=range+transmitter_clock-receiver_clock`; Jacobian uses + transmitter and - receiver clock signs. |
| Stage A / Step 1 | `jcls_sim/algorithm.py::coarse_individual_localization` | `step1_coarse_individual_dl_gn` | Packs output theta with estimated UE positions and zero clock states. | km/range-km | Weighted normal equations from range sigmas. | Deterministic multistart; rank-deficient DL geometry marks user failure. | no truth-centered initialization | Used in C7 and figure paths as `without_cooperation`. |
| Step B / Step 2 | `jcls_sim/algorithm.py::joint_lm_jcls` | `step2_joint_lm_jcls` | Full gauged V24 theta from Step 1 to LM theta. | km/range-km | Precision weighting via `1/sigma^2`; damping added to normal matrix. | Accept candidate if weighted residual cost does not increase; adjust damping; rank-deficient accepted updates are not marked converged. | no truth state used | Diagnostics include accepted steps, damping, residual norm, rank, condition number. |
| Migration Step B | `jcls_sim/migration.py::step_b_lm_residual_acceptance`, Step B report | `legacy_staged_compatible` migration step | Legacy-compatible state but LM truth gate replaced. | legacy range/clock units | legacy MAP covariance still fixed in Step B migration reports | Observable residual-cost, finite-candidate, bounded-step/trust-region checks. | removes LM truth-state acceptance; later MAP path still legacy in migration ladder | `outputs/reports/STEP_B_LM_ACCEPTANCE_COMPARISON.*`; medium grid healthy 12/12. |
| Generic package Step 3 | `jcls_sim/algorithm.py::dynamic_soft_information_refinement` | `v24_three_stage_dynamic` | Default `x=theta`, `F=I`, `Pi=I`, diagonal `Q`. | km/range-km | `P0` from local linearization; information-form EKF update. | Stops on numerical failure; propagates upstream failure. | no truth-derived covariance | Package helper exists, but current defensible candidate path is C7. |
| C7 covariance | `jcls_sim/algorithm.py::step_c7_residual_scaled_block_covariance` | `step_c7_residual_cov_sync_safeguard` | State is theta plus clock-drift block in C7 figure path. | position km, clock range-km, drift km/s | `sigma_hat^2 * pinv(J.T R^-1 J + lambda I)`, typed block-extracted, diagonal-clipped. | Covariance floors/ceilings by position, UE clock, satellite clock, drift. | `truth_state_used_for_covariance=False` | Diagnostics include residual scale factor, rank, covariance shape/source. |
| C7 update/safeguard | `jcls_sim/algorithm.py::step_c7_residual_cov_sync_safeguard_refinement` | `step_c7_residual_cov_sync_safeguard` | Initial state plus linearized update; returns final state and covariance. | km/range-km/km/s | Prior precision from C7 covariance; normal matrix `J.T R^-1 J + P^-1`. | Reject/revert clock and drift update if nonfinite, objective not decreased, single-UE clock update not observable, clock update exceeds covariance scale, or large common clock component. | `truth_state_used_for_acceptance=False`, `truth_state_used_for_safeguard=False` | Preserves position update; reverts UE clock, satellite clock, and drift to Step B on fallback. |
| C7 figure trial path | `jcls_sim/figure_generation.py::run_single_trial_step_c7_algorithm` | `step_c7_residual_cov_sync_safeguard` | Runs Step 1, Step 2, then C7 state `x=[theta, zeros(clock_count)]`. | km internally; metrics m and seconds/ns | Drift floor set from process-noise std; stacked measurement sigmas. | C7 safeguards; Step B remains baseline in candidate report. | truth used only for offline metrics | Produces rows for `without_cooperation`, `coarse_jcls`, `refined_jcls`. |
| Metrics | `jcls_sim/metrics.py`, `figure_generation._metric_row` | all plotted modes | Compare estimated clocks relative to reference satellite and exclude reference. | position error m; sync error seconds/ns; raw clock error km in candidate CSVs | n/a | n/a | truth only for offline metric computation | Candidate plots convert synchronization to ns; raw CSV keeps range-domain km. |
| Candidate figures | `scripts/run_c7_candidate_figures.py` | Step B baseline vs C7 candidate | Network-size grid and sparse clock sweep. | sync plots ns; raw km retained | uses C7 metadata | Blocks clock-sweep candidate use if high-clock rows degrade localization. | no truth in acceptance/covariance/safeguard | `outputs/c7_candidate_figures/`; non-final, candidate-only, not manuscript-ready. |
| Current graph status | reports under `outputs/reports/` | C7 candidate/provenance | Non-final graph packages only. | mixed plot units, documented | n/a | human review required | notebook not executed in C7 candidate path | No C7 output is manuscript-ready. |

## Part C - Parity Matrix

| Row | Manuscript says | Code does | Parity status | Severity | Recommended action |
|---|---|---|---|---|---|
| State vector definition | `theta=[p_u, delta_u, delta_s]`; `x` includes at least `theta` and may include dynamics states. | V24 theta matches; C7 uses `x=[theta, clock_drift]`. | conceptual_match_but_needs_clarification | medium | Clarify that the final numerical implementation must state whether Step 3 uses `x=theta` or an augmented drift state. |
| Gauge/reference clock convention | First satellite is reference; `delta_{Nu+1}=0`; `N_theta=4Nu+Ns-1`. | Same reference node `Nu+1`; estimated clocks exclude reference. | matches | low | Keep. Add metric sentence that reference satellite is excluded from synchronization averages. |
| Measurement model | Range-domain TOA with clock differences and additive noise. | `h=range+transmitter_clock-receiver_clock`; `R=diag(sigma^2)`. | matches | low | Keep main model; ignore commented appendix unless reactivated. |
| Units for position/clock | Manuscript model says measurements in meters and clock offsets as time multiplied by `c`; results in m/ns. | Code stores positions in km and clocks as range-domain km; converts metrics to m and seconds/ns. | implementation_detail | low | Add a numerical-method note if needed: internal clock states are range-equivalent and converted for reporting. |
| Step 1 implementation | Per-UE WNLS/GN using own first-interval measurements; conventional no-cooperation baseline. | Per-UE DL-only weighted GN with zero clocks and deterministic multistart; rank checks. | matches | low | Keep. If editing, say "DL-only" explicitly. |
| Step 2 implementation | Weighted LM over full theta initialized by Step 1 and zero clocks. | Weighted LM over full gauged theta. | matches | low | Keep. |
| Step 2 acceptance logic | Generic LM update equations; damping described conceptually. | Residual-cost/trust-region acceptance; no truth gate; rank-deficient updates not reported as converged. | implementation_detail | medium | Add a brief numerical-method sentence only if discussing code defensibility. |
| Step 3 dynamic model | Generic SCI/SFI dynamic model with `F,Q,P,Pi`; optional clock drift. | Generic helper has `x=theta,F=I,Pi=I`; current C7 path uses stacked epochs and theta-plus-drift state. | conceptual_match_but_needs_clarification | high | Decide final Step 3 path; align numerical-results text with either identity-state helper or C7 drift state. |
| Step 3 covariance | Gaussian prior covariance prediction and information-form posterior covariance. | C7 uses typed block-extracted, diagonal-clipped residual-scaled covariance from LM curvature; not a plain predicted `P`. | mismatch | high | If C7 is final, describe covariance as an implementation/numerical method caveat and avoid implying dense/cross covariance. |
| Step 3 clock drift | Manuscript theory includes clock-drift augmentation; numerical results say `x=theta`, `F=I`, fixed clock offsets over 500 ms. | C7 candidate appends clock drift and updates offset by epoch time. | mismatch | high | Must reconcile before submission if C7 figures or claims are used. |
| Step 3 projection `Pi` | `theta=Pi x`, described as diagonal projection. | Generic helper records `Pi=I`; C7 effectively projects by slicing first `theta_dim` entries from augmented state. | conceptual_match_but_needs_clarification | medium | If C7 is final, describe projection as selecting theta from augmented theta-plus-drift state. |
| Step 3 MAP/information update | Linearized Gaussian likelihood and prior give posterior mean/MAP. | Generic helper implements information-form EKF; C7 computes one safeguarded linearized update with residual-scaled covariance. | conceptual_match_but_needs_clarification | medium | Condense generic soft-information discussion and avoid saying a standard EKF/MAP is adopted straightforwardly. |
| Step 3 safeguard/fallback | Not described. | C7 reverts clock/drift increments for unsafe/unobservable updates; single-UE fallback reason is `single_user_clock_update_not_observable`. | manuscript_missing | high | Add numerical-method caveat if C7 is used; do not present fallback as performance improvement. |
| Single-UE semantics | Single UE cannot exploit cooperation; results say single-UE networks use conventional TOA. | C7 recreation treats `Nu=1` as no-cooperation baseline; candidate validation also records C7 fallback equality for `Nu=1`. | conceptual_match_but_needs_clarification | medium | Make explicit that `Nu=1` is a baseline/no-cooperation case and not evidence of cooperative synchronization refinement. |
| Output metrics | Average 3D UE localization error and average node synchronization error after 0.5 s. | Position mean in m; sync error relative to reference satellite excluding reference, seconds/ns for plots. | conceptual_match_but_needs_clarification | medium | Add metric definition for synchronization reference/exclusion convention. |
| Figure-generation workflow | Manuscript includes current figure PDFs and claims refined JCLS trends. | Current C7 outputs are candidate-only, non-final, not manuscript-ready; sparse clock sweep is blocked by localization instability. | mismatch | high | Must not use current C7 outputs as final manuscript evidence without human signoff and a final approved rerun path. |

## Highest-Risk Mismatches

1. **Numerical Step 3 state mismatch.** Manuscript numerical text says
   `x=theta`, `F=I`, fixed clock offsets over 0.5 s. The current defensible C7
   path uses `x=[theta, clock_drift]`.
2. **Covariance/update mismatch.** Manuscript gives a generic Gaussian
   information/MAP update. C7 depends on residual-scaled LM curvature,
   typed block extraction, diagonal clipping, and safeguards.
3. **Figure-readiness mismatch.** C7 network-size candidate behavior is
   promising, but all C7 outputs remain non-final and not manuscript-ready;
   the sparse clock-sweep candidate is blocked by high-clock localization
   instability.
4. **Single-UE semantics.** Single-UE rows must be described as no-cooperation
   or fallback-preserved cases, not as cooperative synchronization refinement.

## Safe Wording

- "The proposed framework consists of a DL-only coarse localization stage, a
  cooperative joint position/clock LM stage, and a dynamic soft-information
  refinement stage."
- "In the current C7 candidate implementation, the refinement state augments
  the gauged position/clock vector with clock-drift components."
- "The C7 covariance is a typed block-extracted, diagonal-clipped
  residual-scaled covariance used as a numerical safeguard."
- "Single-UE cases cannot exploit sidelink cooperation; they are treated as a
  no-cooperation baseline or as safeguarded non-observable clock-update cases."
- "Current C7 outputs are non-final diagnostics for human review."

## Unsafe Wording

- "C7 outputs are manuscript-ready."
- "The current sparse clock sweep validates the final refined-JCLS clock-sweep
  figures."
- "Single-UE C7 improves synchronization."
- "The C7 covariance is a dense block covariance or cross-covariance method."
- "The reported refined-JCLS results are produced by a generic EKF/MAP filter"
  unless the final code path actually uses that filter without C7 safeguards.

## Part E - Manuscript Action List

### Must Fix Before Submission

| Priority | Action | Rationale |
|---|---|---|
| 1 | Reconcile the numerical-results Step 3 specialization with the final code path. | Current text says `x=theta`, `F=I`, no drift, while C7 uses an augmented drift state. |
| 2 | Do not present C7 candidate outputs as final manuscript evidence until a final approved rerun exists. | C7 reports mark all outputs non-final and not manuscript-ready. |
| 3 | If C7 becomes final, add a concise numerical-method caveat for residual-scaled covariance and non-truth safeguards. | The current manuscript MAP/Gaussian product alone omits key implementation behavior. |
| 4 | Clarify single-UE/no-cooperation semantics in figure/results language. | Single-UE rows are not cooperative JCLS synchronization improvements. |
| 5 | Define the synchronization metric relative to the reference satellite and excluding the reference clock. | This is the code metric convention and should be auditable in manuscript claims. |

### Should Fix If Time

- Condense the Step 3 soft-information prose around lines 1386-1388.
- Replace broad comparisons to EM/Viterbi/Kalman filtering with one short
  sentence that the formulation is compatible with Bayesian linearized
  information updates.
- Add "DL-only" to the Step 1 baseline description.
- Add a short numerical-method statement that internal clock states may be
  represented in range-equivalent units and converted for reporting.

### Nice To Have

- Move detailed C7 safeguards to a provenance/numerical-method note instead of
  the main algorithm derivation.
- Keep theory equations intact unless the final code path requires a precise
  C7-specific derivation.
- Remove or keep commented Jacobian appendix inactive; do not reactivate it
  without checking sign conventions.

## Recommended Next Actions

1. Human decision: choose whether final manuscript results should be aligned to
   the generic identity-state SCI/SFI helper or to the C7 drift/safeguard path.
2. If C7 is chosen, write a minimal manuscript edit plan before touching
   manuscript files.
3. Run no broader clock sweep until the sparse C7 clock-sweep instability is
   explained or an approved alternative is selected.
4. Keep all current C7 graph packages labeled non-final and not
   manuscript-ready.

## Audit Statement

No manuscript, response-letter, bibliography, notebook, PSFrag,
Work-In-Progress figure, generated manuscript PDF, or existing manuscript
result file was edited for this report.
