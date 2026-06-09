MODE: REVIEW_DIFF

# Next Task: Review Wave-Results Exploration Pilot

## Purpose

Review branch `codex/jcls-wave-results-exploration` before any larger
observability or result-generation expansion. Do not edit manuscript files, do
not run full sweeps, do not generate manuscript figures, and do not mark any
wave-results output manuscript-ready.

## Scope

Inspect:

- `scripts/run_wave_results_exploration.py`
- `tests/test_wave_results_exploration.py`
- `outputs/wave_results/`
- `outputs/reports/WAVE_RESULTS_PROVENANCE_AUDIT.md`
- `outputs/reports/WAVE_RESULTS_EXECUTIVE_SUMMARY.md`
- `outputs/reports/WAVE_RESULTS_PHASE_TRANSITION_REPORT.md`
- `outputs/reports/WAVE_RESULTS_SATELLITE_SUBSTITUTION_REPORT.md`
- `outputs/reports/WAVE_RESULTS_CLOCK_TOLERANCE_REPORT.md`
- `outputs/reports/WAVE_RESULTS_SPARSE_SL_REPORT.md`
- `outputs/reports/WAVE_RESULTS_TIME_TO_ACCURACY_REPORT.md`
- `outputs/reports/WAVE_LITERATURE_COMPARISON_TABLE.md`
- `outputs/reports/WAVE_RESULTS_TASK_MATRIX.md`
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

1. Confirm the runner is bounded, resumable, and writes only under
   `outputs/wave_results/` and `outputs/reports/WAVE_*`.
2. Confirm required CLI options are implemented:
   `--dry-run`, `--list-plan`, `--resume`, `--force-rerun`,
   `--max-runtime-minutes`, `--row-timeout-seconds`,
   `--trial-timeout-seconds`, `--max-trials`, `--only-product`,
   `--only-row`, `--pilot`, `--full`, and `--cache-root`.
3. Confirm single-UE rows are marked `jcls_applicable=false` and
   `single_ue_baseline_only=true`.
4. Confirm CRLB values are unavailable for rank-deficient displayed FIM cases.
5. Confirm failed rows are preserved rather than dropped.
6. Confirm all outputs are non-final, candidate diagnostics, not for manuscript
   submission, and `manuscript_ready=false`.
7. Confirm the pilot generated the first two priority products before relying
   on lower-priority products.
8. Confirm the executive summary does not overclaim: Stage B/LM-only improves
   localization in only 4/32 comparable pilot cells and no iso-accuracy
   threshold is reached.
9. Confirm the literature table uses caveated comparison language and does not
   claim JCLS beats Starlink PNT or differential Doppler methods.
10. Confirm focused and full tests pass.

Run:

```powershell
python -m unittest tests.test_wave_results_exploration
python -m unittest discover -s tests
```

## Expected Output

Return:

- PASS / FAIL / PASS WITH CAVEAT;
- merge or expansion recommendation;
- required fixes before merge, if any;
- observability/rank summary;
- satellite-substitution summary;
- empirical Stage A/B/C caveat;
- sparse sidelink and clock-tolerance caveats;
- no-manuscript-edit verdict;
- tests run/results;
- whether outputs are ready for human diagnostic review;
- whether outputs are ready for manuscript use;
- next recommended action.
