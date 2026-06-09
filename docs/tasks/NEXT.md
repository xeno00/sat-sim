MODE: PLAN_ONLY

# Next Task: Remaining Benchmark Adapter Boundaries

## Purpose

Design the next safe adapter implementation step for the normalized benchmark-card
runner after the first `package_native_c7` primary-standard card.

The first adapter branch produced non-final benchmark cards under
`outputs/standard_benchmark_cards/`. Only `package_native_c7` is currently
executable from core `jcls_sim`; the other registered pipelines are represented
with explicit missing metrics and missing reasons.

Do not generate manuscript figures. Do not run broad sweeps. Do not edit
manuscript source, response letters, bibliography, notebook source, PSFrag,
Work-In-Progress figures, generated manuscript PDFs, or existing manuscript
result files.

## Required Inputs

- `outputs/reports/NORMALIZED_BENCHMARK_ADAPTER_IMPLEMENTATION_REPORT.md`
- `outputs/reports/NORMALIZED_STANDARD_BENCHMARK_REPORT.md`
- `outputs/standard_benchmark_cards/PIPELINE_MANIFEST.md`
- `outputs/standard_benchmark_cards/raw.csv`
- `outputs/standard_benchmark_cards/summary.csv`
- `outputs/reports/PIPELINE_DOWNSELECT_REPORT.md`
- `outputs/reports/STANDARD_SCENARIO_PIPELINE_SCORECARD.md`
- `outputs/reports/MISSING_STANDARD_METRICS.md`
- `outputs/reports/RESULT_VERSION_LINEAGE_AND_UNITS_REVIEW.md`
- `outputs/registry/RESULT_REGISTRY.md`
- `outputs/reports/JCLS_SIM_PIPELINE_INTEGRATION_PLAN.md`
- `outputs/reports/PIPELINE_CODE_DUPLICATION_AUDIT.md`

## Branch Ledger Policy

`outputs/reports/ACTIVE_BRANCH_LEDGER.md` and
`outputs/reports/ACTIVE_BRANCH_LEDGER.json` are the canonical live branch-status
source. Update them whenever branch disposition changes.

A branch with unique work must have one of: merged to main, open PR, parked with
reason, quarantined with reason, superseded with replacement, or deleted after
safe disposition. A pushed branch alone is not a valid final state.

## Recommended Next Action

Plan the smallest next implementation that can make the normalized benchmark
card more scientifically useful without moving legacy notebook execution hooks
into core `jcls_sim`.

Prioritize:

1. A safe `controlled_migration_step_b_lm_only` adapter boundary if it can call
   existing reusable code without notebook execution.
2. A safe `legacy_surgical_prior_region` adapter boundary if the merged code is
   accessible from main without copying legacy notebook execution into
   `jcls_sim`.
3. Keeping `legacy_truth_gated_l0_reference_only` as provenance/reference only
   unless a read-only external adapter can report metrics with strong truth-use
   caveats.

The next implementation must preserve:

- pipeline tuple fields;
- truth-use fields;
- units fields;
- readiness/recommended-use fields;
- missing metric reasons;
- primary case `std_nu3_ns10_fullmesh_los_clock1us_seed0`.

## Stop Gates

- Need for broad simulations or manuscript figure generation.
- Need to edit protected manuscript/result files without explicit approval.
- Need to move legacy notebook execution hooks into `jcls_sim` before an adapter
  boundary is designed and tested.
- Need to substitute the secondary low-satellite stress case for the primary
  standard case.

## Final Response Checklist

```text
Branch:
Commit:
Pushed:
PR:
PR status:
Merged to main:
Merge commit:
If not merged, disposition:
If not merged, reason:
Tests:
Protected-file check:
Reports/outputs:
ACTIVE_BRANCH_LEDGER updated:
Next action:
```
