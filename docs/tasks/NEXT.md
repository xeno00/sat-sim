MODE: REVIEW_DIFF

# Next Task: Review Migration Step B Before Merge

## Purpose

Review branch `codex/migration-step-b-lm-no-truth-gate` before merge. Step B
replaces the legacy LM true-state acceptance gate with observable
residual/trust-region criteria while keeping all other legacy-compatible
behavior fixed.

## Scope

Inspect:

- `jcls_sim/migration.py`
- `scripts/run_controlled_migration_ladder.py`
- `scripts/build_legacy_graph_package.py`
- `tests/test_controlled_migration_ladder.py`
- `outputs/migration_ladder/step_b_lm_residual_acceptance/`
- `outputs/reports/STEP_B_LM_ACCEPTANCE_COMPARISON.md`
- `outputs/reports/STEP_B_LM_ACCEPTANCE_COMPARISON.json`
- `outputs/reports/CONTROLLED_MIGRATION_LADDER.md`
- `outputs/reports/CONTROLLED_MIGRATION_LADDER.json`
- `outputs/gallery/PLOT_GALLERY.md`
- `outputs/OUTPUT_INDEX.md`

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

1. Confirm Step B changes only `acceptance_mode` relative to Step A.
2. Confirm Step B LM acceptance does not call `scenario.get_true_state()` or
   otherwise use true-state error for accepting/rejecting LM steps.
3. Confirm true-state errors are used only after estimation for diagnostics and
   plotting.
4. Confirm all-clock internals, legacy IL, MAP/global fallback, legacy sync
   metric, geometry/noise settings, single-UE policy, and raw/display separation
   are preserved.
5. Confirm tiny and medium Step B outputs exist, are non-final, and are not
   manuscript-ready.
6. Confirm residual-cost diagnostics are recorded and accepted LM steps do not
   increase weighted residual cost beyond tolerance.
7. Confirm `STEP_B_LM_ACCEPTANCE_COMPARISON` compares Step B against Step A
   medium rows and reports localization/synchronization behavior per grid row.
8. Confirm the ladder conservatively marks Step B as the first degraded
   correction because tiny synchronization is partially degraded, while medium
   Step B is healthy.
9. Confirm gallery/index/status reports include Step B previews.
10. Run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File '..\scripts\test_sat_sim.ps1'
```

## Expected Output

Return:

- PASS / FAIL / PASS WITH CAVEAT;
- merge recommendation;
- required fixes before merge, if any;
- nonblocking caveats;
- whether Step B is healthy or first degraded/breaking correction;
- next recommended correction after merge or after fixing.

