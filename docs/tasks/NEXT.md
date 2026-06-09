MODE: IMPLEMENT_APPROVED

# Next Task: Normalized Primary Benchmark-Card Runner

## Purpose

Build the smallest normalized benchmark-card runner needed to compare the
current candidate result pipelines under the same primary standard case:

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

## Branch Ledger Policy

`outputs/reports/ACTIVE_BRANCH_LEDGER.md` and
`outputs/reports/ACTIVE_BRANCH_LEDGER.json` are the canonical live branch-status
source. Update them whenever branch disposition changes.

A branch with unique work must have one of: merged to main, open PR, parked
with reason, quarantined with reason, superseded with replacement, or deleted
after safe disposition. A pushed branch alone is not a valid final state.

## Recommended Next Action

Create a normalized benchmark-card runner for
`std_nu3_ns10_fullmesh_los_clock1us_seed0` that reports initialization, Step A,
Step B, and Step C localization/synchronization metrics for:

1. `legacy_surgical_prior_region` as the recommended primary candidate;
2. `controlled_migration_step_b_lm_only` as the Step B backbone;
3. `package_native_c7` as the theory-clean backup/reference;
4. `legacy_truth_gated_l0` as reference-only provenance.

The runner must write non-final benchmark-card CSV/JSON outputs with:

- pipeline tuple fields;
- truth-use fields;
- units fields;
- initialization, Step A, Step B, and Step C metrics;
- V24 reference-relative synchronization where possible;
- legacy all-clock synchronization kept separate when needed;
- readiness/recommended-use fields.

After the run, update the result registry, lineage/units review, scorecard, and
downselect report.

## Stop Gates

- Need for broad simulations or manuscript figure generation.
- Need to edit protected manuscript/result files without explicit approval.
- Discovery that candidate pipelines cannot be normalized without a human
  scientific decision.

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
