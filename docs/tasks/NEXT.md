MODE: IMPLEMENT_APPROVED

This task may be executed via `RUN_CODEX.md`. Keep it diagnostic-only. Do not
run notebook code, full sweeps, or manuscript figure generation.

# Next Task: Implement Legacy Notebook Provenance Audit

## Purpose

Create a read-only provenance audit for `JCLS_Simulation.ipynb` that maps
legacy figure/CRLB-related notebook cells to V24 package-native risk flags
without executing the notebook or changing any result files.

## Allowed Edit Files

- `scripts/audit_legacy_notebook_provenance.py`
- `tests/test_legacy_notebook_provenance.py`
- `v24_diagnostics/legacy_notebook_provenance_audit.json`
- `PROJECT_STATUS.md`
- `docs/tasks/NEXT.md`
- `docs/tasks/QUEUE.md`

## Read-Only Files

- `JCLS_Simulation.ipynb`
- `v24_diagnostics/crlb_figure_decision_plan.json`
- package modules/tests as needed for context

## Goals

1. Parse the notebook JSON as text/data only; do not execute it.
2. Identify cells containing CRLB/FIM/bound keywords, figure-output/save
   keywords, legacy all-clock/gauge-risk keywords, and synchronization-metric
   keywords.
3. Produce a compact non-final JSON audit under `v24_diagnostics/` with cell
   indices, matched keyword categories, risk level, and a short excerpt.
4. Flag whether legacy CRLB/figure cells are likely unsafe until package-native
   V24 paths replace them.
5. Add tests using a small synthetic notebook fixture so tests do not depend on
   exact legacy notebook contents.

## Hard Constraints

- Do not edit `JCLS_Simulation.ipynb`.
- Do not run notebook code.
- Do not generate figures.
- Do not run full sweeps.
- Do not edit manuscript, response-letter, bibliography, Work-In-Progress
  figures, PSFrag files, generated manuscript PDFs, or existing manuscript
  result outputs.

## Expected Tests

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File '.\scripts\test_sat_sim.ps1'
```

## Stop Gates

- Notebook execution is needed.
- The audit requires changing notebook/result/figure files.
- Tests fail and the fix is not obvious/safely scoped.
- The audit needs human scientific judgment to classify a cell.
