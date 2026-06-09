# Minimal Legacy Corrected Pipeline Report

> Non-final diagnostic. Not manuscript-ready.

## Executive Summary

- Pipeline: `legacy_surgical_nontruth`
- Primary case: `std_nu3_ns10_fullmesh_los_clock1us_seed0`
- Prior: `prior_ball_R0`, R0 = `100000.0` m
- Truth gates removed: `True`
- Truth-derived covariance removed: `True`
- C5/sliding-window MAP used: `False`

## Primary Standard-Case Results

| stage | localization [m] | synchronization [ns] | success | failure reason |
|---|---:|---:|---:|---|
| initialization | 69095.17702453087 | None | True | initialization_sync_metric_not_reported_by_legacy_initializer |
| step_a | 566.249140452735 | 1253.462631089372 | True |  |
| step_b | 0.0744502771727543 | 491.1531460309657 | True |  |
| step_c | 0.03623739136921989 | 491.15314406554756 | True |  |

## Legacy Behavior Preserved

- legacy all-clock internal state
- legacy notebook/extracted Scenario and Optimizer classes
- legacy measurement ordering and units
- legacy IL/LM/MAP stage sequence

## Truth Gates Removed

- Stage A truth-output reversion replaced by finite residual completion
- LM truth-error acceptance replaced by residual/trust-region acceptance
- MAP covariance uses residual-scaled information pseudoinverse, not x-true_state error

## Covariance Replacement

Residual-scaled information pseudoinverse with the merged step_c3 residual-scaled covariance policy.

## First-Run Success Criteria

- `step_b_localization_lt_1m`: `True`
- `step_c_localization_lt_1m`: `True`
- `step_c_not_catastrophically_worse_than_step_b`: `True`
- `truth_gates_removed`: `True`
- `truth_derived_covariance_removed`: `True`

## Step B / Step C Assessment

- Step B sufficient by <1 m localization criterion: `True`.
- Step C improves Step B localization: `True`.
- Step C improves Step B synchronization: `True`.
- Sparse manuscript-targeted run status: `prepared_not_executed`.
- Should this become the manuscript result pipeline: `needs_review`.

## Truth-Use Ledger

- `truth_used_for_prior_construction`: `True`
- `truth_used_for_initialization`: `False`
- `truth_used_for_lm_acceptance`: `False`
- `truth_used_for_step_c_acceptance`: `False`
- `truth_used_for_covariance`: `False`
- `truth_used_for_fallback_or_reversion`: `False`
- `truth_used_for_offline_metrics`: `True`

## Units Ledger

- `internal_position_units`: `km`
- `internal_clock_state_units`: `legacy range-equivalent km`
- `measurement_units`: `km`
- `measurement_covariance_units`: `legacy km^2/range-domain covariance`
- `localization_error_units`: `m`
- `synchronization_error_units`: `ns`
- `clock_sigma_input_units`: `seconds`
- `units_status`: `units_consistent_but_legacy`

## Safe Claims

- Corrected pipeline uses truth only for simulated prior construction and offline metrics.
- Primary standard case was run as a single row, not a sweep.
- Outputs are non-final and not manuscript-ready.

## Unsafe Claims

- Do not claim this is a final manuscript result pipeline until sparse and multi-seed validation pass.
- Do not claim V24 reference-relative synchronization metrics; these are legacy all-clock metrics.
- Do not claim no truth is used anywhere; truth is used to center the simulated prior region.

## What This Replaces If Successful

- package-native C7 figure recreation path
- broad C0-C7 exploratory variants
- gallery outputs
- root-level v24_* generated outputs
- redundant benchmark glue

## Recommendation

Needs review. Run sparse manuscript mode only after the primary row is accepted as plausible.
