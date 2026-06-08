MODE: REVIEW_DIFF

# Next Task: Review C4 Composite MAP Acceptance

## Purpose

Review branch `codex/step-c4-composite-map-acceptance` before merge. Do not
edit files and do not run additional ladder rows unless a precise bounded
follow-up command is approved.

## Scope

Inspect:

- `jcls_sim/migration.py`
- `scripts/run_controlled_migration_ladder.py`
- `scripts/build_legacy_graph_package.py`
- `tests/test_controlled_migration_ladder.py`
- `outputs/reports/STEP_C_ACCEPTANCE_DESIGN_NOTES.md`
- `outputs/reports/STEP_C_ACCEPTANCE_DESIGN_NOTES.json`
- `outputs/migration_ladder/step_c4_composite_map_acceptance/tiny/`
- `outputs/migration_ladder/step_c4_composite_map_acceptance/medium/`
- `outputs/reports/STEP_C4_COMPOSITE_ACCEPTANCE_COMPARISON.md`
- `outputs/reports/STEP_C4_COMPOSITE_ACCEPTANCE_COMPARISON.json`
- C4 gallery preview entries under `outputs/gallery/`

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

1. Confirm C4 starts from Step B behavior, not degraded C1/C2/C3 behavior.
2. Confirm C4 keeps all-clock internals, Step B residual LM acceptance, legacy
   covariance, legacy sync metric, single-UE policy, and geometry/noise
   settings.
3. Confirm C4 changes only MAP acceptance/reversion logic.
4. Confirm C4 does not call `scenario.get_true_state()` for acceptance.
5. Confirm C4 metadata records `map_acceptance_mode:
   composite_observable`, all score components, and accept/reject reasons.
6. Confirm accepted C4 updates do not increase the observable total MAP
   objective beyond tolerance.
7. Confirm tiny was run first and medium was run only because tiny was not
   catastrophic.
8. Confirm C4 outputs are non-final and not manuscript-ready.
9. Confirm gallery previews exist for C4 tiny and medium.
10. Confirm tests pass.

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
- whether C4 improves over C1;
- whether C4 approaches Step B behavior;
- whether MAP truth acceptance can now be replaced;
- next recommended acceptance-design action.
