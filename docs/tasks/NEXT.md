MODE: PLAN_ONLY

# Next Task: V24 Theory Fix Plan

## Purpose

Use `outputs/reports/V24_THEORY_RED_TEAM_AUDIT.md` and companion reports to
prepare a minimal manuscript-theory patch plan. Do not edit manuscript source,
response letters, bibliography, PSFrag, Work-In-Progress figures, generated
manuscript PDFs, existing manuscript result files, or simulation outputs unless
explicitly instructed.

## Required Inputs

- `outputs/reports/V24_THEORY_RED_TEAM_AUDIT.md`
- `outputs/reports/V24_THEORY_DERIVATION_CHECKLIST.md`
- `outputs/reports/V24_THEORY_REFERENCE_AUDIT.md`
- `outputs/reports/V24_THEORY_FIX_RECOMMENDATIONS.md`
- current V24 manuscript source in the manuscript repository/directory

## Branch Ledger Policy

`outputs/reports/ACTIVE_BRANCH_LEDGER.md` and
`outputs/reports/ACTIVE_BRANCH_LEDGER.json` are the canonical live branch-status
source. Update them whenever branch disposition changes.

A branch with unique work must have one of: merged to main, open PR, parked
with reason, quarantined with reason, superseded with replacement, or deleted
after safe disposition. A pushed branch alone is not a valid final state.

## Recommended Next Action

Prepare a surgical manuscript edit plan for the required theory fixes:

1. measurement index/sign convention;
2. mixed DL/SL row-index sets;
3. fixed range-domain covariance assumption;
4. NLOS density regularity/support assumptions;
5. CRLB extraction, units, clock group, reference exclusion, and rank semantics.

## Stop Gates

- Need for new simulations or figure generation.
- Need to edit protected manuscript/result files without explicit approval.
- Discovery that the intended clock sign convention conflicts with the code or
  current manuscript equations.

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
