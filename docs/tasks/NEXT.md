MODE: REVIEW_DIFF

# Next Task: Review Step 3 Micro-Benchmarks

## Purpose

Review branch `codex/step3-micro-benchmarks` before merge. Do not edit files,
do not run network-size graphs, do not run full ladders, and do not run medium
grids.

## Scope

Inspect:

- `scripts/benchmark_step3_micro_cases.py`
- `scripts/render_all_figure_previews.py`
- `tests/test_step3_micro_benchmarks.py`
- `outputs/step3_micro_benchmarks/`
- `outputs/reports/STEP3_MICRO_BENCHMARK_REPORT.md`
- `outputs/reports/STEP3_MICRO_BENCHMARK_REPORT.json`
- Step 3 micro-benchmark entries under `outputs/gallery/`
- `PROJECT_STATUS.md`

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

1. Confirm the branch stays code/diagnostic-only and does not touch notebook or
   manuscript artifacts.
2. Confirm the micro-benchmark runner defaults to tiny deterministic cases and
   does not run network-size graphs, full ladders, or medium grids.
3. Confirm all six requested cases are implemented:
   clock-only, position-only, clock drift, common-clock/gauge, mixed
   position-clock, and Schur/nuisance-clock.
4. Confirm all six requested variants are tested:
   baseline C5 proxy, block-scaled no-drift, block-scaled drift,
   common-clock projection, Schur/nuisance-clock reduction, and clock-only
   filter.
5. Confirm diagnostics record before/after position and clock errors,
   residual/prior/dynamics/objective components, update norms, nullspace/gauge
   component, covariance scales, and case pass/fail.
6. Confirm promotion is based on explicit micro-case pass/fail and does not
   imply manuscript readiness or network-size validation.
7. Confirm report and metadata mark outputs non-final and not manuscript-ready.
8. Confirm gallery previews exist for the micro-benchmark plots.
9. Confirm focused and full tests pass.

Run:

```powershell
python -m unittest tests.test_step3_micro_benchmarks
powershell -NoProfile -ExecutionPolicy Bypass -File '..\scripts\test_sat_sim.ps1'
```

## Expected Output

Return:

- PASS / FAIL / PASS WITH CAVEAT;
- merge recommendation;
- required fixes before merge, if any;
- which variants passed the micro-benchmark promotion rule;
- which variants failed and why;
- whether any variant is promising enough for the next sparse network
  experiment;
- whether Step B/LM-only remains the current clean estimator baseline;
- next recommended action after merge.
