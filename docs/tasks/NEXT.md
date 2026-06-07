MODE: REVIEW_DIFF

This task may be executed via `RUN_CODEX.md`. Do not edit files. Do not merge
unless the human explicitly approves merge after review.

# Next Task: Review Manuscript-Candidate Geometry/Noise Branch Before Merge

## Purpose

Review branch `codex/manuscript-geometry-noise` before merge. The branch adds a
manuscript-candidate geometry/noise path for V24 Fig. 4--7 families while
leaving algorithm fidelity for a later sprint.

## Scope

Inspect:

- `jcls_sim/geometry.py`
- `jcls_sim/noise.py`
- `jcls_sim/figure_generation.py`
- `configs/v24_manuscript_candidate_figures_4_7/*.json`
- `tests/test_geometry.py`
- `tests/test_noise.py`
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

1. Confirm UE geometry is deterministic, MIT/Stata-centered, and inside a 500 m
   disk.
2. Confirm LLA/ECEF units are sane and positions are stored internally in km.
3. Confirm synthetic LEO satellite geometry is clearly labeled, applies a
   30 degree elevation mask, records visible/requested/selected satellites, and
   is interface-compatible with later TLE/SGP4 replacement.
4. Confirm DL/SL link-budget sigmas use configured frequencies, bandwidths,
   powers, gains, FSPL, noise power, SNR, and the beta/SNR TOA formula.
5. Confirm range-domain sigmas are in km and metrics remain meters/seconds/ns as
   appropriate.
6. Confirm metadata records UE LLA/ECEF coordinates, satellite IDs/elevations/
   ranges/ECEF coordinates, link assumptions, SNR ranges, and sigma ranges.
7. Confirm candidate outputs are under `v24_manuscript_candidate_outputs/` and
   include:
   - `diagnostic_only: false`
   - `candidate_only: true`
   - `non_final: true`
   - `manuscript_ready: false`
   - `not_for_manuscript_submission: true`
8. Confirm existing hardened diagnostic outputs remain diagnostic-only.
9. Confirm tests pass:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File '.\scripts\test_sat_sim.ps1'
   ```

## Known Caveats To Verify Are Explicit

- Satellite geometry is synthetic Starlink-like LEO, not TLE/SGP4 yet.
- Candidate outputs are not manuscript-grade.
- Algorithm fidelity remains incomplete: refined JCLS is repeated static-epoch
  fusion, not full dynamic SCI/SFI with `F`, `Q`, and `Pi`.
- No manuscript text should be changed based on these outputs.

## Required Output

Return:

- PASS / PASS WITH CAVEAT / FAIL;
- merge recommendation;
- required fixes before merge, if any;
- nonblocking caveats;
- confirmation out-of-scope files were untouched;
- next recommended task after merge, expected to be algorithm fidelity.
