# Manuscript Algorithm Parity Task Matrix

## Executive Summary

This audit used read-only lanes where possible and orchestrator fallback where
the lanes timed out. Only report files under `outputs/reports/` are owned by
this task. Manuscript files, response files, bibliography files, notebooks,
PSFrag files, Work-In-Progress figures, generated manuscript PDFs, and existing
manuscript result files were not edited.

| Workstream | Branch/worktree | Subagent role | Files allowed to edit | Read-only files | Stop conditions | Status |
|---|---|---|---|---|---|---|
| Manuscript extraction | `codex/manuscript-algorithm-parity-check` | Agent A - Manuscript Algorithm Extractor | none | `../Work-In-Progress/SCL-NTN-TAES-2025-V24.tex`, `../Work-In-Progress/SCL-NTN-TAES-2025-V24.pdf` | manuscript edit, LaTeX build, notebook execution | Spawned, timed out, closed; orchestrator fallback completed |
| Code extraction | `codex/manuscript-algorithm-parity-check` | Agent B - Code Algorithm Extractor | none | `jcls_sim/algorithm.py`, `jcls_sim/migration.py`, `jcls_sim/figure_generation.py`, C7/Step B scripts and reports | code edit, simulation run, output rewrite | Spawned, timed out, closed; orchestrator fallback completed |
| Parity matrix | `codex/manuscript-algorithm-parity-check` | Agent C - Parity Matrix Builder | `outputs/reports/MANUSCRIPT_ALGORITHM_PARITY_CHECK.*` | manuscript and code extraction inputs | need manuscript or code changes | Orchestrator completed |
| Condensation/style | `codex/manuscript-algorithm-parity-check` | Agent D - Condensation/Style Agent | none | manuscript source, workflow files, C7 reports | manuscript edit, notebook execution, simulation run | Read-only subagent completed |
| Scientific red-team | `codex/manuscript-algorithm-parity-check` | Agent E - Scientific Red-Team | none | manuscript source, code path, reports | need new derivation or result rerun | Spawned, timed out, closed; orchestrator fallback completed |
| Report integration | `codex/manuscript-algorithm-parity-check` | Orchestrator | requested report files only | all inputs above | JSON/check failure, manuscript-file change | In progress during report creation |

## Lane Notes

- Agent D completed independently and recommended condensing the Step 3 prose,
  keeping C7 implementation details in numerical-method/provenance notes, and
  making single-UE/no-cooperation semantics explicit.
- Agents A, B, and E did not complete within the bounded wait and were closed.
  Their lanes were completed by direct read-only inspection.
- No subagent was allowed to edit any file.

## Checks Planned

- Parse all JSON reports.
- Confirm referenced file paths exist.
- Confirm required Markdown sections exist.
- Confirm manuscript, response-letter, bibliography, notebook, PSFrag,
  Work-In-Progress figure, generated manuscript PDF, and existing manuscript
  result files were not modified by this branch.
