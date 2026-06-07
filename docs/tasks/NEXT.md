MODE: REVIEW_DIFF

This task may be executed via `RUN_CODEX.md`. Do not edit files unless the
human explicitly approves implementation. Do not merge unless explicitly
allowed.

# Next Task: Review CRLB Geometry Diagnostics Branch Before Merge

## Purpose

Review the branch implementing better non-final CRLB diagnostic geometry before
it is merged. Confirm the diagnostics separate fixed-parameter information
addition from growing-`N_s` nuisance-clock behavior and keep all outputs
non-final.

## Scope

Inspect:

- `jcls_sim/configs.py`
- `scripts/diagnose_v24_crlb_geometry.py`
- `tests/test_crlb_diagnostics.py`
- `v24_diagnostics/crlb_geometry_diagnostics.json`
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
- generated figure PDFs/EPS/PNGs
- existing manuscript result files
- plotting code
- figure-generation code

## Checks

1. Fixed-parameter diagnostic:
   - `Nu`, `Ns`, geometry, and parameter dimension remain fixed.
   - Measurement count increases over nested subsets.
   - Monotonicity is checked only for full-rank finite-CRLB cases.
   - Rank-deficient cases remain diagnostic-only.

2. Growing-`N_s` diagnostic:
   - Metadata clearly says the sweep changes parameter dimension.
   - Metadata says monotonic CRLB interpretation is not valid.
   - Clock-bound seconds conversion is present.
   - Rank-deficient cases are not manuscript-ready.

3. Rank-feasibility grid:
   - Grid includes `Nu`, `Ns`, link pattern, measurement count, parameter
     dimension, rank, nullity, full-rank flag, CRLB status, and notes.

4. JSON/output:
   - Output lives only under `v24_diagnostics/`.
   - No manuscript figures or final result files were generated.
   - No large FIM/Jacobian matrices are written.

5. Tests:
   - Run `powershell -NoProfile -ExecutionPolicy Bypass -File '.\scripts\test_sat_sim.ps1'`
     from the repository root, or the documented bundled-Python unittest
     fallback if the wrapper path is unavailable.

## Required Output

Return:

- PASS / FAIL / PASS WITH CAVEAT;
- merge recommendation;
- required fixes before merge, if any;
- nonblocking caveats;
- confirmation that manuscript, response-letter, bibliography, figure, PSFrag,
  PDF, notebook, and final-result files were not edited.

