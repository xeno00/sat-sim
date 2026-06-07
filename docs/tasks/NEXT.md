MODE: REVIEW_DIFF

This task may be executed via `RUN_CODEX.md`. Do not edit files. Do not merge
unless the human explicitly approves merge after review.

# Next Task: Review CRLB Decision Sprint Branch Before Merge

## Purpose

Review branch `codex/crlb-decision-sprint` before merge. The branch adds
diagnostic-only CRLB figure decision planning and static legacy notebook
provenance audit outputs.

## Scope

Inspect:

- `scripts/plan_v24_crlb_figure_decision.py`
- `tests/test_crlb_figure_decision_plan.py`
- `v24_diagnostics/crlb_figure_decision_plan.json`
- `scripts/audit_legacy_notebook_provenance.py`
- `tests/test_legacy_notebook_provenance.py`
- `v24_diagnostics/legacy_notebook_provenance_audit.json`
- `PROJECT_STATUS.md`
- `docs/tasks/NEXT.md`
- `docs/tasks/QUEUE.md`

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

## Checks

1. Confirm diagnostics are non-final and stored only under `v24_diagnostics/`.
2. Confirm no notebook execution is used.
3. Confirm no manuscript/response/bibliography/figure outputs are touched.
4. Confirm the decision plan recommends rank feasibility first and treats
   finite CRLB-vs-`N_s` as secondary with the growing-parameter caveat.
5. Confirm the notebook audit flags CRLB/FIM + gauge/all-clock risk cells and
   reports the legacy CRLB paths as unsafe until package-native replacement.
6. Confirm tests pass:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File '.\scripts\test_sat_sim.ps1'
   ```

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
