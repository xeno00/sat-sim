# PROJECT_STATUS.md

## Current phase

sat-sim architecture refactor for V24 conformance.

## Workflow status

Persistent Codex task files are enabled under `sat-sim/`. Flexible subagents
may be used when helpful. Parallel edit-capable work requires Git
branch/worktree isolation, explicit file ownership, and coordinator-owned
integration/merge decisions.

Python tests use the active Python runtime directly. The workflow intentionally
does not create virtual environments or bootstrap scripts; if standard
scientific test packages are missing, Codex installs the minimal needed
packages into the selected runtime and reports the command.

## Manuscript relationship

The V24 manuscript and response letter live outside this repository and are
near final/human-signoff. Existing manuscript figures are under
code-gauge/provenance review before final confidence. Do not edit manuscript or
response-letter files from this code workflow.

## Code status

Gauge/metrics package and tests are implemented. Measurement-model and explicit
V24 parameter-vector helpers/tests are implemented. Jacobian and gauged FIM
helpers/tests are implemented. Estimator correctness helpers/tests are
implemented. A deterministic end-to-end package smoke test exercises the V24
parameter vector, range-domain measurements, Jacobian, gauged FIM, one-step
estimator helpers, information-form update, and gauge-consistent
synchronization metric.

A package-level reproducibility smoke runner creates deterministic non-final
JSON diagnostics under `v24_diagnostics/` using package modules only. Legacy
notebook bridge planning identified the CRLB/FIM bound extraction path as the
safest first bridge because the notebook currently builds localization and
synchronization bounds with post-hoc clock-column slicing.

Full-gauged bound extraction helpers and a non-final CRLB diagnostic smoke path
are implemented and tested. The package-native non-final CRLB mini-sweep
runner, tests, and non-final JSON diagnostic are implemented. CRLB diagnostic
hardening helpers/tests are implemented: seconds-domain versus range-domain
clock-parameter invariance, rank-deficient manuscript reportability, and
fixed-parameter information-addition monotonicity. The CRLB diagnostic builders
now include nullity, CRLB status, manuscript-readiness flags, and seconds-domain
clock-bound conversions. Non-final CRLB diagnostic JSON files under
`v24_diagnostics/` have been refreshed with the hardened schema.

A better non-final CRLB geometry diagnostic is implemented and merged. It
separates fixed-parameter information addition, growing-`N_s` nuisance-clock
behavior, and rank-feasibility checks, and writes deterministic non-final JSON
to `v24_diagnostics/crlb_geometry_diagnostics.json`. Next: plan a
manuscript-relevant non-final CRLB candidate using the rank-feasibility results
without generating manuscript figures.

A manuscript-relevant non-final CRLB candidate diagnostic is implemented and
merged. It summarizes rank-feasibility cases into finite manuscript-ready cases
and explicitly unavailable rank-deficient cases without generating figures.

Non-final CRLB figure-candidate data are implemented and merged. The data
include rank-feasibility heatmap matrices, finite CRLB-vs-`N_s` series with
unavailable masks, and fixed-parameter measurement-addition series. No figures
are generated.

Non-final CRLB preview SVGs are implemented and merged. The previews read the
merged candidate JSON and write diagnostic-only SVGs plus a manifest under
`v24_diagnostics/crlb_preview/`. They are not manuscript figures and require
human review before any figure workflow decision.

A non-final CRLB figure decision-plan diagnostic is implemented on branch
`codex/crlb-decision-sprint`. It summarizes the preview/candidate data into a
human-review plan, recommends rank feasibility as the first CRLB concept to
consider, and flags legacy CRLB-vs-satellite-count and localization/
synchronization CRLB panels as likely needing package-native rerun or
replacement before final confidence.

A static legacy notebook provenance audit is implemented on branch
`codex/crlb-decision-sprint`. It parses `JCLS_Simulation.ipynb` without
executing it, identifies CRLB/FIM, figure-output, gauge/all-clock,
synchronization-metric, and workspace-persistence cells, and writes a non-final
audit under `v24_diagnostics/legacy_notebook_provenance_audit.json`. The audit
flags the legacy notebook CRLB paths as unsafe until package-native replacement.

A package-native CRLB figure-family regression diagnostic is implemented on
branch `codex/crlb-decision-sprint`. It writes deterministic non-final JSON,
CSV, and NPZ diagnostics under `v24_diagnostics/regression/` for the
localization and synchronization CRLB figure families. The diagnostic uses the
V24 full-gauged FIM/bounds path only and masks rank-deficient/non-ready cases
instead of emitting finite manuscript-style values.

## Blocking risks

- Legacy notebook estimates all clocks.
- Legacy CRLB/FIM may be ungauged.
- Legacy synchronization metric averages all `delta_` variables.
- Legacy notebook still depends on symbolic/free-symbol ordering and Google
  Drive pickle-style workspace persistence.
- Legacy CRLB figure pipelines delete clock columns and form separate FIMs;
  package helpers now avoid this, but the legacy notebook has not been
  refactored and manuscript figures have not been rerun.
- Rank-deficient CRLB cases must not be treated as finite manuscript-style
  bounds unless the relevant subspace is proven estimable.
- Figures may need rerun after the V24-gauge code path is integrated into
  reproducible scripts.

## Last completed task

Estimator correctness tests, deterministic end-to-end package smoke test,
package-level V24 reproducibility smoke runner, full-gauged CRLB bound
extraction helpers, package-native non-final CRLB mini-sweep runner/tests, and
CRLB diagnostic hardening tests are implemented. Non-final diagnostic JSON
exists under `v24_diagnostics/` with hardened CRLB status/reportability fields.
The CRLB geometry diagnostic runner/tests are merged on `main`.
The manuscript-relevant CRLB candidate runner/tests are merged on `main`.
The non-final CRLB figure-candidate data runner/tests are merged on `main`.
The non-final CRLB preview SVG runner/tests are merged on `main`.
The non-final CRLB figure decision-plan runner/tests are implemented on branch
`codex/crlb-decision-sprint`.
The static legacy notebook provenance audit runner/tests are implemented on
branch `codex/crlb-decision-sprint`.
The CRLB figure-family regression diagnostic runner/tests and non-final
JSON/CSV/NPZ outputs are implemented on branch `codex/crlb-decision-sprint`.

## Next task

See `docs/tasks/NEXT.md`.

## Figure-risk notes

- CRLB localization and synchronization figures remain unsafe to trust until a
  manuscript-relevant package-native CRLB figure concept is reviewed from
  non-final diagnostics/previews and explicitly approved for figure-rerun work.
- Non-final CRLB figure-family regression diagnostics now exist under
  `v24_diagnostics/regression/`; they are diagnostic-only and are not manuscript
  figures or final manuscript result data.
- The package-native CRLB mini-sweep diagnostic exists at
  `v24_diagnostics/sweep_v24_crlb_ns.json`, but it is non-final, not a
  manuscript figure, and explicitly marks rank-deficient cases as
  `rank_deficient_diagnostic`.
- Synchronization sweeps likely need rerun after V24-gauge metric integration.
- Localization sweeps are still under human/code-provenance review because the
  legacy solver state is overparameterized relative to V24.
- Do not rerun manuscript figures until the package-level runner and notebook
  bridge/refactor path are tested and explicitly approved.
