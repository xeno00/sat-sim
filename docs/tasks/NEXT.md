MODE: REVIEW_DIFF

# Next Task: Review Step C Diagnosis Recovery Before Merge

## Purpose

Review branch `codex/migration-step-c-diagnosis` after the hung-ladder recovery
and runtime-guard pass. Do not edit files and do not rerun the full ladder.

## Scope

Inspect:

- `scripts/run_controlled_migration_ladder.py`
- `tests/test_controlled_migration_ladder.py`
- `outputs/reports/HUNG_LADDER_RECOVERY_REPORT.md`
- `outputs/reports/HUNG_LADDER_RECOVERY_REPORT.json`
- `outputs/reports/STEP_C_DIAGNOSIS_REPORT.md`
- `outputs/reports/STEP_C_DIAGNOSIS_REPORT.json`
- canonical C0/C1/C2/C3 outputs under `outputs/migration_ladder/`
- bounded smoke output under
  `outputs/migration_ladder/step_c0_legacy_map_instrumented/tiny_bounded/`
- heartbeat/status files under `outputs/cache/migration_ladder/`

Do not edit:

- `JCLS_Simulation.ipynb`
- manuscript files
- response-letter files
- bibliography files
- Work-In-Progress figure files
- PSFrag files
- generated manuscript PDFs
- existing manuscript result files

## Required Review Checks

1. Confirm no canonical C0/C1/C2/C3 tiny/medium outputs were overwritten by
   the bounded recovery smoke.
2. Confirm the recovery report distinguishes runner-safety failure from output
   validity.
3. Confirm every canonical C-substep output has raw CSV, summary CSV, metadata,
   PDFs, gallery PNG previews, and complete cache status.
4. Confirm bounded recovery output is under a separate `tiny_bounded` path.
5. Confirm bounded cache entries are marked noncanonical, not valid canonical
   cache.
6. Confirm default CLI execution is tiny-only.
7. Confirm medium execution requires explicit `--medium`.
8. Confirm dry-run/planned-work output reports rows before execution.
9. Confirm max-row/substep/time guard metadata is present.
10. Confirm heartbeat and row-status files are written.
11. Confirm focused tests and full sat-sim tests pass.

Run:

```powershell
python -m unittest tests.test_controlled_migration_ladder
powershell -NoProfile -ExecutionPolicy Bypass -File '..\scripts\test_sat_sim.ps1'
```

## Expected Output

Return:

- PASS / FAIL / PASS WITH CAVEAT;
- merge recommendation;
- required fixes before merge, if any;
- whether it is safe to continue Step C diagnosis review without rerunning the
  full ladder;
- next bounded command to run only if additional execution is required.
