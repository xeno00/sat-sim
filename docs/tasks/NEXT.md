MODE: REVIEW_DIFF

# Next Task: Review C5 Sliding-Window MAP Smoother

## Purpose

Review branch `codex/step-c5-sliding-window-map` before merge. Do not edit
files and do not run additional ladder rows unless a precise bounded follow-up
command is approved.

## Scope

Inspect:

- `jcls_sim/migration.py`
- `scripts/run_controlled_migration_ladder.py`
- `tests/test_controlled_migration_ladder.py`
- `outputs/migration_ladder/step_c5_sliding_window_map/tiny/`
- `outputs/migration_ladder/step_c5_sliding_window_map/medium/`
- `outputs/reports/STEP_C5_SLIDING_WINDOW_MAP_COMPARISON.md`
- `outputs/reports/STEP_C5_SLIDING_WINDOW_MAP_COMPARISON.json`
- `outputs/reports/STEP2_ONLY_VS_STEP3_REFINEMENT.md`
- `outputs/reports/STEP2_ONLY_VS_STEP3_REFINEMENT.json`
- C5 gallery preview entries under `outputs/gallery/`

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

1. Confirm C5 uses Step B residual/trust-region LM behavior as the forward
   estimator baseline.
2. Confirm C5 keeps all-clock internals, legacy symbolic parameter ordering,
   legacy sync metric, single-UE policy, and legacy geometry/noise settings.
3. Confirm C5 changes only the Step 3 MAP/EKF refinement into a small
   sliding-window MAP smoother.
4. Confirm the C5 smoother does not call `scenario.get_true_state()` for
   acceptance, covariance, or fallback decisions.
5. Confirm C5 metadata records window length, `F=I`, configured `P0`, `Q`,
   measurement covariance use, objective components, accept/reject counts, and
   rejection reasons.
6. Confirm accepted C5 solver steps do not increase the full observable
   smoother objective beyond tolerance.
7. Confirm tiny was run first and medium was run only because tiny was not
   catastrophic.
8. Confirm C5 outputs are non-final and not manuscript-ready.
9. Confirm gallery previews exist for C5 tiny and medium.
10. Confirm `STEP2_ONLY_VS_STEP3_REFINEMENT` correctly reports that Step 2
    currently shows JCLS benefit while Step 3 is mixed or harmful.
11. Confirm tests pass.

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
- whether C5 improves over C4;
- whether C5 approaches Step B/legacy behavior;
- whether Step 3 is now defensible;
- whether Step B/LM-only should be treated as the current clean estimator
  baseline;
- next recommended action.
