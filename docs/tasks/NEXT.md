MODE: REVIEW_DIFF

This task may be executed via `RUN_CODEX.md`. Do not edit files. Do not merge
unless the human explicitly approves merge after review.

# Next Task: Review Hardened V24 Algorithm-Fidelity Branch Before Merge

## Purpose

Review branch `codex/v24-algorithm-fidelity` after the status/rank honesty
hardening pass. The branch adds a package-native V24 three-stage algorithm path
for manuscript-candidate Fig. 4--7 diagnostics while preserving non-final
candidate-output boundaries.

## Scope

Inspect:

- `jcls_sim/algorithm.py`
- `jcls_sim/figure_generation.py`
- `configs/v24_manuscript_candidate_figures_4_7/*.json`
- `tests/test_algorithm.py`
- `tests/test_figure_generation.py`
- `v24_manuscript_candidate_outputs/**`
- `PROJECT_STATUS.md`
- `docs/tasks/NEXT.md`

Do not edit:

- `JCLS_Simulation.ipynb`
- manuscript files
- response-letter files
- bibliography files
- Work-In-Progress figure files
- PSFrag files
- generated manuscript PDFs
- generated manuscript figure PDFs/EPS/PNGs
- existing manuscript result files

## Checks

1. Confirm Step 1 uses DL-only weighted GN for individual UE coarse
   localization and does not use truth-centered initialization.
2. Confirm Step 2 uses weighted LM over the full gauged V24 theta vector with
   precision weighting and no reference-satellite clock state.
3. Confirm Step 2 success is conservative:
   - `success=True` only for `status = converged`;
   - accepted-but-not-converged cases report `updated_not_converged`;
   - rank-deficient or numerical-failure cases are not successes.
4. Confirm Step 3 uses dynamic SCI/SFI information-form updates with explicit
   `F`, `Q`, and `Pi`, and uses the innovation `z - h_pred`.
5. Confirm Step 3 propagates upstream Step 2 status:
   - upstream non-convergence is visible in raw output;
   - upstream rank deficiency/failure does not become an unconditional success.
6. Confirm candidate configs use `estimator_mode = v24_three_stage_dynamic`
   and record `process_noise_std_km`, refinement interval, and epoch spacing.
7. Confirm candidate metadata/provenance reports the estimator mode, state model
   `x=theta`, `F=I`, `Pi=I`, `Q=process_noise_std_km^2 I`, and retains:
   - `candidate_only: true`
   - `non_final: true`
   - `manuscript_ready: false`
   - `not_for_manuscript_submission: true`
8. Confirm rank metadata is honest:
   - raw/summary outputs do not use ambiguous `fim_rank` or `is_full_rank`
     fields for figure baselines;
   - rank fields are named `full_jcls_scenario_*`;
   - metadata/provenance explains these are not baseline-specific
     observability claims.
9. Confirm generated candidate outputs remain under
   `v24_manuscript_candidate_outputs/` only.
10. Confirm no manuscript, response-letter, bibliography, notebook, PSFrag,
    Work-In-Progress figure, generated manuscript PDF, or existing manuscript
    result files were edited.
11. Confirm tests pass:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File '..\scripts\test_sat_sim.ps1'
   ```

## Known Caveats To Verify Are Explicit

- Candidate outputs are not manuscript-grade.
- Satellite geometry is still synthetic Starlink-like LEO, not TLE/SGP4.
- The default dynamic model is currently `x=theta`, `F=I`, `Pi=I`, and diagonal
  `Q`; it is a package-native fidelity step, not a final physical dynamics
  model.
- Baseline-specific observability/rank diagnostics remain pending.
- Estimator robustness/initialization remains the main blocker before any
  manuscript-grade rerun.
- No manuscript text should be changed based on these outputs.

## Required Output

Return:

- PASS / PASS WITH CAVEAT / FAIL;
- merge recommendation;
- required fixes before merge, if any;
- nonblocking caveats;
- confirmation out-of-scope files were untouched;
- next recommended task after merge, expected to address estimator robustness
  and baseline-specific observability.
