MODE: IMPLEMENT_APPROVED

# Next Task: Normalized Primary Benchmark-Card Runner Adapters

## Purpose

Implement the first execution adapters and bounded normalized benchmark-card
runner against the new schema-only package layer.

`std_nu3_ns10_fullmesh_los_clock1us_seed0`

Do not generate manuscript figures. Do not run broad sweeps. Do not edit
manuscript source, response letters, bibliography, notebook source, PSFrag,
Work-In-Progress figures, generated manuscript PDFs, or existing manuscript
result files.

## Required Inputs

- `outputs/reports/REPO_AND_MANUSCRIPT_CONTEXT_REBASE.md`
- `outputs/reports/PIPELINE_DOWNSELECT_REPORT.md`
- `outputs/reports/STANDARD_SCENARIO_PIPELINE_SCORECARD.md`
- `outputs/reports/MANUSCRIPT_RESULT_REQUIREMENTS_MATRIX.md`
- `outputs/reports/MISSING_STANDARD_METRICS.md`
- `outputs/reports/RESULT_VERSION_LINEAGE_AND_UNITS_REVIEW.md`
- `outputs/registry/RESULT_REGISTRY.md`
- `outputs/reports/EXPERIMENT_CODE_LOCATION_AUDIT.md`
- `outputs/reports/JCLS_SIM_PIPELINE_INTEGRATION_PLAN.md`
- `outputs/reports/PIPELINE_CODE_DUPLICATION_AUDIT.md`
- `outputs/reports/JCLS_SIM_PIPELINE_SCHEMA_IMPLEMENTATION_REPORT.md`

## Branch Ledger Policy

`outputs/reports/ACTIVE_BRANCH_LEDGER.md` and
`outputs/reports/ACTIVE_BRANCH_LEDGER.json` are the canonical live branch-status
source. Update them whenever branch disposition changes.

A branch with unique work must have one of: merged to main, open PR, parked
with reason, quarantined with reason, superseded with replacement, or deleted
after safe disposition. A pushed branch alone is not a valid final state.

## Recommended Next Action

Use the registered schema pipeline specs:

1. `legacy_surgical_prior_region` as the recommended primary candidate;
2. `controlled_migration_step_b_lm_only` as the Step B backbone;
3. `package_native_c7` as the theory-clean backup/reference;
4. `legacy_truth_gated_l0` as reference-only provenance.

Implement adapters incrementally and preserve:

- pipeline tuple fields;
- truth-use fields;
- units fields;
- readiness/recommended-use fields.
- missing metric reasons.

Start with the package-native C7 adapter if possible, then add a legacy-surgical
adapter boundary that keeps notebook/legacy namespace execution hooks out of
core `jcls_sim`. The runner must not generate manuscript figures or broad
sweeps.

## Stop Gates

- Need for broad simulations or manuscript figure generation.
- Need to edit protected manuscript/result files without explicit approval.
- Need to move legacy notebook execution hooks into `jcls_sim` before an adapter
  boundary is designed and tested.

## Final Response Checklist

```text
Current main before:
Current main after:
Working tree clean:
Branches inspected:
Branches remaining:
PRs opened:
PRs closed:
PRs merged:
Branches deleted local:
Branches deleted remote:
Branches parked:
Branches quarantined:
Branches needing human review:
Protected-file check:
Tests:
Reports updated:
ACTIVE_BRANCH_LEDGER updated:
If no, reason:
Branches changed:
Remaining active branches:
Next action:
```
