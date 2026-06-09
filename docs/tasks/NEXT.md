MODE: REVIEW_DIFF

# Next Task: Review Minimal Corrected Legacy Primary Row

## Purpose

Review the new minimal corrected legacy-compatible result pipeline before
running sparse manuscript-targeted rows.

This task should decide whether the primary standard row is credible enough to
justify running `--mode sparse-manuscript`.

Do not generate manuscript figures. Do not run broad sweeps. Do not edit
manuscript source, response letters, bibliography, notebook source, PSFrag,
Work-In-Progress figures, generated manuscript PDFs, or existing manuscript
result files.

## Required Inputs

- `scripts/minimal_legacy_corrected_jcls.py`
- `outputs/minimal_legacy_corrected/raw.csv`
- `outputs/minimal_legacy_corrected/summary.csv`
- `outputs/minimal_legacy_corrected/metadata.json`
- `outputs/minimal_legacy_corrected/PIPELINE_MANIFEST.md`
- `outputs/reports/MINIMAL_LEGACY_CORRECTED_PIPELINE_REPORT.md`
- `tests/test_minimal_legacy_corrected.py`

## Review Questions

1. Does the script remain a minimal corrected legacy-compatible runner rather
   than a new framework?
2. Are forbidden truth-use flags false?
3. Is truth use limited to prior construction and offline metrics?
4. Is the residual/trust-region LM path used?
5. Is MAP covariance non-truth residual-scaled information covariance?
6. Does the primary row satisfy the first-run success criteria?
7. Is Step B already sufficient?
8. Does Step C improve Step B without a new truth gate?
9. Is sparse manuscript mode prepared but not executed?
10. Should sparse manuscript mode be run next?

## If Review Passes

Recommended next implementation command:

```powershell
python scripts\minimal_legacy_corrected_jcls.py --run --mode sparse-manuscript --prior-radius-m 100000 --output-root outputs\minimal_legacy_corrected --force
```

Only run this after human approval or a clean review result.

## Branch Ledger Policy

`outputs/reports/ACTIVE_BRANCH_LEDGER.md` and
`outputs/reports/ACTIVE_BRANCH_LEDGER.json` are the canonical live branch-status
source. Update them whenever branch disposition changes.

## Final Response Checklist

```text
Branch:
Commit:
Pushed:
PR:
PR status:
Merged to main:
If not merged, disposition:
Tests:
Protected-file check:
Reports/outputs:
ACTIVE_BRANCH_LEDGER updated:
Next action:
```
