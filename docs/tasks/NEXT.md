MODE: REVIEW_DIFF

# Next Task: Primary Standard Benchmark-Card Runner

## Purpose

Build a normalized benchmark-card runner for
`std_nu3_ns10_fullmesh_los_clock1us_seed0`. Do not edit manuscript files, do
not execute the notebook, do not run broad simulations, and do not generate
final manuscript figures.

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

Create a small runner/report that evaluates the primary standard case:

- case id: `std_nu3_ns10_fullmesh_los_clock1us_seed0`;
- `N_u=3`, `N_s=10`;
- full-mesh sidelinks;
- LOS/Rician when supported;
- manuscript-like MIT/Stata UE geometry and Starlink-like LEO geometry when
  supported;
- clock standard deviation `1 microsecond`;
- seed `0`;
- operation time `0.5 s` when Stage C is available;
- one trial for the standard fingerprint.

Compare Step B / LM-only and C7 under identical geometry/noise/clock settings.
Keep the old `std_nu3_ns4_fullmesh_los_clock1us_seed0` case only as
`secondary_low_satellite_stress_case`; do not use it as the primary benchmark.
Update `RESULT_VERSION_LINEAGE_AND_UNITS_REVIEW` after the benchmark-card
runner exists.

## FINAL_RESPONSE_SCHEMA

```text
Branch:
Commit:
Pushed:
PR:
PR status:
Merged to main:
Merge commit:
If not merged, disposition:
Reason not merged:
If branch remains open, why:
If branch deleted, deletion confirmation:
Tests:
Protected-file check:
Reports/outputs:
Next action:
```
