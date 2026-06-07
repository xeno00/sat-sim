MODE: REVIEW_DIFF

This task may be executed via `RUN_CODEX.md`. Do not edit files. Do not merge
unless the human explicitly approves merge after review.

# Next Task: Review CRLB Preview Candidate Branch Before Merge

## Purpose

Review branch `codex/crlb-preview-candidates` before merge. The branch creates
non-final SVG previews from already-merged CRLB figure-candidate JSON. The
previews are diagnostic-only aids for human figure-concept review and are not
manuscript figures.

## Scope

Inspect:

- `scripts/preview_v24_crlb_figure_candidates.py`
- `tests/test_crlb_preview_candidates.py`
- `v24_diagnostics/crlb_preview/preview_manifest.json`
- `v24_diagnostics/crlb_preview/*.svg`
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
- package source files
- existing diagnostics outside `v24_diagnostics/crlb_preview/`

## Checks

1. Confirm the script reads existing CRLB candidate JSON and does not run the
   notebook, full sweeps, or final figure-generation paths.
2. Confirm preview outputs are written only under
   `v24_diagnostics/crlb_preview/`.
3. Confirm the manifest marks outputs as non-final, not manuscript figures, and
   requiring human review.
4. Confirm unavailable/rank-deficient CRLB points are visibly represented and
   not silently converted into finite values.
5. Confirm the growing-`N_s` preview does not imply monotonicity.
6. Confirm the fixed-parameter preview states that monotonicity is checked only
   after full rank.
7. Confirm tests pass:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File '..\scripts\test_sat_sim.ps1'
   ```

8. Confirm no manuscript, response-letter, bibliography, notebook, final figure,
   or existing manuscript result files were touched.

## Required Output

Return:

- PASS / FAIL / PASS WITH CAVEAT;
- merge recommendation;
- required fixes before merge, if any;
- nonblocking caveats;
- confirmation out-of-scope files were untouched;
- next recommended task after merge.

## Hard Constraints

- Do not edit files.
- Do not generate manuscript figures.
- Do not run full sweeps.
- Do not run notebook code.
- Do not merge unless explicitly approved after the review.
