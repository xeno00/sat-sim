MODE: REVIEW_DIFF

This task may be executed via `RUN_CODEX.md`. Do not edit files. Do not merge
unless the human explicitly approves merge after review.

# Next Task: Review Package-Native Fig. 4--7 Diagnostics Before Merge

## Purpose

Review branch `codex/package-native-figures-4-7` before merge. The branch adds
package-native, deterministic, non-final diagnostic generation for the V24
manuscript Fig. 4--7 families. The branch should be considered for merge only
as diagnostic scaffold infrastructure, not as final manuscript figure
provenance.

## Scope

Inspect:

- `configs/v24_figures_4_7/*.json`
- `jcls_sim/figure_generation.py`
- `scripts/run_v24_figures_4_7.py`
- `tests/test_figure_generation.py`
- `v24_figure_outputs/**`
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

1. Confirm all outputs are non-final and stored only under `v24_figure_outputs/`.
2. Confirm no notebook execution or notebook imports are used.
3. Confirm no manuscript/response/bibliography/Work-In-Progress figure outputs
   are touched.
4. Confirm checked-in configs are deterministic and include seeds, trials,
   units, and assumptions.
5. Confirm the baselines are explicitly defined:
   - Without cooperation: per-UE DL-only localization, no clock estimation.
   - Coarse JCLS: full V24 theta, one measurement epoch.
   - Refined JCLS: full V24 theta initialized from coarse and fused over
     repeated static-geometry epochs.
6. Confirm metadata/provenance JSON includes commit/config/seed/trials/units/
   runtime/code path and notebook/manuscript-output flags.
7. Confirm all metadata/provenance/table paths are repo-relative and contain no
   machine-specific absolute paths.
8. Confirm all metadata/provenance/table payloads include:
   - `diagnostic_only: true`
   - `non_final: true`
   - `manuscript_ready: false`
   - `not_for_manuscript_submission: true`
   - a human-readable diagnostic warning.
9. Confirm output-root guardrails reject Work-In-Progress, PSFrag, notebook/
   legacy, parent traversal, and outside-repository output roots unless the
   documented developer-only unsafe override is used.
10. Confirm overwrite behavior is conservative by default and requires
   `--overwrite` for existing outputs.
11. Confirm synchronization plots display nanoseconds while raw stored metrics
   remain seconds.
12. Confirm raw CSV, summary CSV, NPZ, PDF, metadata JSON, provenance JSON, and
   combined provenance table are present.
13. Confirm tests pass:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File '..\scripts\test_sat_sim.ps1'
   ```

   or from the parent repository root:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File '.\scripts\test_sat_sim.ps1'
   ```

## Known Caveats To Verify Are Explicit

- The outputs use synthetic deterministic static geometry, not legacy TLE or
  notebook geometry.
- The outputs use flat range-domain standard deviations, not the legacy
  link-budget-derived sigma model.
- The refined JCLS baseline is repeated-epoch static-geometry fusion, not a
  full dynamic EKF/F/Q/Pi reproduction.
- The configs intentionally do not force package-native curves to match legacy
  notebook curves.

## Required Output

Return:

- PASS / PASS WITH CAVEAT / FAIL;
- merge recommendation;
- required fixes before merge, if any;
- nonblocking caveats;
- confirmation out-of-scope files were untouched;
- next recommended task after merge.

## Hard Constraints

- Do not edit files.
- Do not run notebook code.
- Do not generate manuscript figures.
- Do not run full sweeps.
- Do not merge unless explicitly approved after review.
