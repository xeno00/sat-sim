MODE: REVIEW_DIFF

# Next Task: Parked Branch Review and Lineage Registration

## Purpose

Review parked diagnostic branches before any further merge. Do not edit
manuscript files, do not execute the notebook, do not run broad simulations,
and do not generate final manuscript figures.

## MERGE_POLICY

Branches may be merged only after they have a result-lineage/units entry,
protected-file check, and explicit disposition. A pushed branch with no
disposition is incomplete.

## DISPOSITION_REQUIRED

Each reviewed branch must be classified as exactly one of:

- `merge_now`;
- `merge_after_minor_fix`;
- `park_do_not_merge_yet`;
- `superseded_do_not_merge`;
- `quarantine_do_not_merge`;
- `already_merged`;
- `unknown_needs_human_review`.

## PROTECTED_FILES

Do not edit or merge changes to `JCLS_Simulation.ipynb`, manuscript files,
response-letter files, bibliography files, Work-In-Progress figures, PSFrag
files, generated manuscript PDFs, or existing manuscript result files without
explicit human approval.

## POST_MERGE_CHECKS

Run:

```powershell
python scripts/check_protected_files.py --base main --target HEAD --fail-on-protected
python -m unittest tests.test_result_lineage_units_review tests.test_integration_compliance
```

Run the full wrapper only if practical:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File '..\scripts\test_sat_sim.ps1'
```

## Scope

Begin with parked branches from
`outputs/reports/BRANCH_INTEGRATION_INVENTORY.json`, especially wave, GNSS, and
legacy-surgical diagnostic branches. For each branch, decide whether it needs a
lineage/units entry, should remain parked, should be quarantined, or is safe to
merge.

## FINAL_RESPONSE_SCHEMA

```text
Branch:
Commit:
Pushed:
Merged to main:
Merge commit:
If not merged, disposition:
Reason not merged:
Tests:
Protected-file check:
Reports/outputs:
Next action:
```
