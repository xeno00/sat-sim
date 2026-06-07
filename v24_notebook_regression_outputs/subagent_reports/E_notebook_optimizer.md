# Subagent E: Notebook Optimizer Agent

Assigned role: Notebook Optimizer Agent

Branch/worktree: current checkout, branch `codex/notebook-manuscript-regression-sprint`; no new branch or worktree created because the task only allowed two report outputs.

Files inspected: `JCLS_Simulation.ipynb` statically only. Workflow files were read for routing, but no package code, scripts, tests, manuscript files, outputs, or notebook execution were used for the audit.

Files changed:

- `v24_notebook_regression_outputs/subagent_reports/E_notebook_optimizer.md`
- `v24_notebook_regression_outputs/subagent_reports/E_notebook_optimizer.json`

Tests/checks run: no notebook execution and no tests, by instruction.

Result: static optimizer map completed.

Risks: conclusions are source-level only. They identify behavior present in the notebook source and saved outputs, but do not validate runtime values.

Recommended next action: do not use the notebook optimizer as a V24 figure or manuscript-result source without replacing the all-clock, oracle-gated, covariance/precision-inconsistent paths with package-native V24-gauged implementations and explicit success/status reporting.

Scope boundary encountered: notebook execution, package-code comparison, and figure-output regeneration were out of scope.

## Static Scope

The optimizer implementation is in notebook code cell 17. Related invocation/status patterns appear in cells 20, 21, 28, 31, 47, and CRLB/numerical helper patterns appear in cells 34 and 44. Scenario and measurement-model context needed to interpret optimizer state ordering appears in cells 13 and 15.

The notebook `Scenario` builds `symbolic_parameter_vector` from all free symbols sorted by name. The link model includes both transmitter and receiver clock symbols in range-domain form, and the commented master-clock substitution is disabled. This means the legacy optimizer operates on an all-clock, ungauged parameter vector unless a method explicitly removes clocks.

## Optimizer Map

`Optimizer.__init__` creates history dictionaries for measurements, true states, estimated states, and covariances, but the audited optimizer methods do not consistently populate them.

`initialize_state(scenario, error_range)`:

- Initializes each UE position at the true position plus independent uniform perturbations in `[-error_range, error_range]`.
- Sets every `delta_<node_id>` clock parameter to zero, including UE clocks and satellite clocks.
- Reorders values according to `scenario.symbolic_parameter_vector`.
- Uses random draws without local seeding and returns `float64`.
- Regression risk: the initial state is truth-centered for positions and all-clock zero for clocks, not a V24-gauged initialization with a reference satellite removed.

`rm_clock_params(scenario)`:

- Makes a shallow `copy(scenario)`.
- Removes every parameter whose name starts with `delta_`.
- Substitutes all removed clock symbols with zero in the symbolic model and recomputes the Jacobian.
- Overrides `get_true_state` and `h` using lambdas.
- Leaves links and measurement covariance behavior otherwise inherited from the original scenario.
- Regression risk: this is a clock-free auxiliary model, not a V24 model with estimated UE clocks plus non-reference satellite clocks.

`il_step(scenario, x, z)`:

- Loops over users.
- Selects downlink measurements for the active user only: receiver is the user and transmitter is a `Satellite`.
- Builds a temporary one-user scenario with the active user position and all satellite positions.
- Extracts the active user's state entries plus satellite-related entries by suffix matching, then calls `async_gn_step`.
- Writes the returned temporary state back into the full vector.
- Because `async_gn_step` returns zeros in clock slots, IL effectively keeps/removes clock effects by forcing selected clock entries to zero during individual-localization updates.
- Regression risk: user and satellite node IDs in temporary scenarios are renumbered, so correctness depends on vector length/ordering rather than symbol identity.

`async_gn_step(scenario, x, z)`:

- Deletes all `delta_` entries from `x`.
- Calls `rm_clock_params`.
- Runs one `gn_step` on the clock-free model.
- Reconstructs a full-length vector with non-clock entries filled and clock entries set to zero.
- Regression risk: direct AGN use resets all clock parameters to zero after each step.

`gn_step(x, h_x, J_x, z, Sigma_z)`:

- Checks dimensions.
- Forms `pinv(J_x.T @ Sigma_z @ J_x)`.
- Applies `x + H_approx @ J_x.T @ Sigma_z @ (z - h_x)`.
- Regression risk: `Sigma_z` is treated as a covariance elsewhere, but this GN form weights by covariance rather than precision. That differs from the V24 package convention `J.T @ R_z^{-1} @ J`.

`lm_step(scenario, x, z, damping_factor, nu)`:

- Computes `h_x`, `J_x`, and `Sigma_z`, then dimension checks.
- First computes a covariance-weighted pseudoinverse LM step, but then overwrites it with a precision-weighted `np.linalg.inv(J.T @ inv(Sigma_z) @ J + lambda I)` step.
- If `cond(Sigma_z) > 1e10`, adds `1e-8 I` to `Sigma_z` in place.
- Computes chi-square-like cost using `inv(Sigma_z)`.
- Accepts the step only if `rho > 0` and the Euclidean error to `scenario.get_true_state()` decreases.
- Updates damping by the Nielsen-style `max(1/3, 1 - (2 rho - 1)^3)` rule on accept and multiplies by `nu` on reject.
- Returns only `(x, damping_factor, nu, updated)`.
- Regression risk: the true-state acceptance gate is an oracle not available in a real estimator or manuscript algorithm. The first LM step formula is dead/overwritten code, and the accepted path still relies on direct matrix inverses.

`ekf_step(scenario, x_old, P_old, z, easy=False)`:

- Uses identity transition `F = I`.
- Uses `Q = 0`.
- Uses `R = scenario.get_measurement_covariance(tfap=easy)`.
- Forms `S = J P J.T + R` and `K = P J.T inv(S)`.
- Updates covariance as `(I - KJ) P_pred`.
- Regression risk: no process noise, no drift state, no projection matrix, no Joseph-form covariance in this method, and no rank/PSD/status reporting.

`map_filter_iteration(self, scenario, P, x, z, verbose=False)`:

- Defined outside the `Optimizer` class, despite downstream code sometimes trying `optimizer.map_filter_iteration`.
- The first `self` argument is unused; fallback calls pass `None`.
- Warns on unexpected state/covariance shapes but continues.
- Uses identity transition `F = I` and `Q = 1e2 I`.
- Uses `pinv(J P J.T + R + 0 I)` for the gain.
- Uses Joseph covariance update.
- Computes true-state error before and after the update; if the update worsens true-state error, it reverts `x_new = x` but still returns the updated covariance.
- Regression risk: dynamic refinement is oracle-gated and can decouple reverted state from updated covariance.

## Convergence And Status Logic

`converged(x, x_new, tol)` uses `norm(x_new - x) / norm(x) < tol`. There is no zero-norm guard, no absolute tolerance branch, and no residual/cost/status object.

`run(...)`:

- Supports `GD`, `IL`, `AGN`, `SGN`, and `LM`.
- Initializes LM damping at `damp = 1.5` and `nu = 1.9` on the first iteration.
- Stops only when `converged(...)` is true and `updated` is true.
- Emits a `RuntimeWarning` when the iteration loop exhausts.
- Returns only the final array after `check_output`.

`check_output(...)`:

- Computes initial and final Euclidean error to `true_state`.
- Raises on NaN or if final true-state error is larger than initial true-state error.
- Regression risk: this makes success depend on ground truth and hides estimator status behind exceptions.

Downstream sweep status behavior:

- Cells 28, 31, and 47 broadly catch all LM exceptions and silently fall back to `x_lm = x_il`.
- MAP filtering tries `optimizer.map_filter_iteration(...)` first, then broadly catches and calls the free `map_filter_iteration(None, ...)` fallback.
- Heatmap cell 28 bypasses LM/MAP entirely for the first user-count row (`i == 0`) by assigning `x_lm = x_il` and `x_map = x_il`.
- Saved notebook outputs include a prior `RuntimeWarning` for maximum LM iterations, but no structured status is propagated into result arrays.

## Numerical Tricks And Stability Patterns

- Extensive use of `np.linalg.pinv` for GN, MAP gain, and synchronization CRLB submatrices.
- Extensive use of direct `np.linalg.inv` for LM, EKF, MAP helpers, FIM/CRLB calculations, and covariance inverses.
- `Sigma_z` receives an in-place `1e-8 I` jitter in LM if its condition number exceeds `1e10`.
- PSD checks in CRLB helper cells add `1e-10 I` before Cholesky.
- Dependent measurements are removed by QR with tolerance `1e-10`.
- SNR helper uses a floor of `1e-10` when downlink SNR is exactly zero.
- MAP free function uses `Q = 1e2 I`, while `ekf_step` uses `Q = 0`.
- Some CRLB helper paths delete clock columns and build separate localization and clock FIMs, using `inv` for localization and `pinv` for clock bounds.

## V24 Regression Implications

- The notebook optimizer estimates or manipulates all clock parameters. It does not enforce the V24 reference satellite gauge `delta_{Nu+1} = 0`.
- Synchronization metrics average all `delta_` entries, including satellite clocks, rather than UE clocks plus non-reference satellite clocks relative to the reference satellite.
- The optimizer's accepted LM and MAP updates use true-state error gates, so historical notebook curves can be optimistic or non-reproducible as estimator performance claims.
- GN/LM weighting is internally inconsistent: GN uses `Sigma_z`, while the later LM solve uses `Sigma_z^{-1}`.
- Dynamic refinement is identity-state, not an explicit V24 `F`, `Q`, `Pi` soft-information refinement with audited status semantics.
- Broad exception fallbacks can turn optimizer failures into IL baselines without explicit failure labels.

## Recommended Next Action

For notebook regression against V24 package-native outputs, treat this optimizer as legacy provenance only. The smallest safe bridge is a static crosswalk or failing-status fixture that records:

- all-clock versus V24-gauged dimension mismatch;
- true-state/oracle acceptance gates in LM and MAP;
- covariance/precision weighting mismatch;
- missing structured convergence status;
- fallback-to-IL behavior in sweeps.

Do not port notebook curves directly into manuscript candidate outputs unless these behaviors are replaced or explicitly marked as legacy/non-V24.
