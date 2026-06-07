MODE: REVIEW_DIFF

This task may be executed via `RUN_CODEX.md`. Do not edit files unless the
human explicitly approves implementation. Do not merge unless explicitly
allowed.

# Next Task: Review Manuscript CRLB Candidate Branch Before Merge

## Purpose

Review the branch implementing the non-final manuscript-relevant CRLB candidate
diagnostic before merge. Confirm it marks rank-deficient cases unavailable and
only exposes finite bound values for manuscript-ready full-rank cases.

## Scope

Inspect:

- `scripts/diagnose_v24_manuscript_crlb_candidate.py`
- `tests/test_manuscript_crlb_candidate.py`
- `v24_diagnostics/manuscript_crlb_candidate.json`
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

1. Candidate output:
   - diagnostic type is non-final;
   - output note says it is not a manuscript figure or result sweep;
   - unavailable policy is explicit.

2. Rank-deficient handling:
   - rank-deficient cases use `plot_value_status = unavailable_rank_deficient`;
   - rank-deficient cases have null finite plot values;
   - rank-deficient cases are not manuscript-ready.

3. Full-rank handling:
   - full-rank manuscript-ready cases use `plot_value_status = finite`;
   - finite cases include average UE PEB and clock bounds;
   - seconds conversion is correct.

4. Summary:
   - finite and unavailable case counts are present;
   - minimal full-rank satellite counts are reported by user count and link
     pattern.

5. Tests:
   - Run `powershell -NoProfile -ExecutionPolicy Bypass -File '.\scripts\test_sat_sim.ps1'`
     from the repository root.

## Required Output

Return:

- PASS / FAIL / PASS WITH CAVEAT;
- merge recommendation;
- required fixes before merge, if any;
- nonblocking caveats;
- confirmation that manuscript, response-letter, bibliography, figure, PSFrag,
  PDF, notebook, and final-result files were not edited.

