# PROJECT_STATUS.md

## Current phase

sat-sim architecture refactor for V24 conformance.

## Workflow status

Persistent Codex task files are enabled under `sat-sim/`. Flexible subagents
may be used when helpful. Parallel edit-capable work requires Git
branch/worktree isolation, explicit file ownership, and coordinator-owned
integration/merge decisions.

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
runner, tests, and non-final JSON diagnostic are implemented. Next: review the
mini-sweep diagnostic trends and decide whether to implement package-native
non-final CRLB diagnostic curves.

## Blocking risks

- Legacy notebook estimates all clocks.
- Legacy CRLB/FIM may be ungauged.
- Legacy synchronization metric averages all `delta_` variables.
- Legacy notebook still depends on symbolic/free-symbol ordering and Google
  Drive pickle-style workspace persistence.
- Legacy CRLB figure pipelines delete clock columns and form separate FIMs;
  package helpers now avoid this, but the legacy notebook has not been
  refactored and manuscript figures have not been rerun.
- Figures may need rerun after the V24-gauge code path is integrated into
  reproducible scripts.

## Last completed task

Estimator correctness tests, deterministic end-to-end package smoke test,
package-level V24 reproducibility smoke runner, full-gauged CRLB bound
extraction helpers, and package-native non-final CRLB mini-sweep runner/tests
are implemented. Non-final diagnostic JSON exists under `v24_diagnostics/`.

## Next task

See `docs/tasks/NEXT.md`.

## Figure-risk notes

- CRLB localization and synchronization figures remain unsafe to trust until a
  package-native non-final CRLB mini-sweep is reviewed and explicitly approved
  for figure-rerun work.
- The package-native CRLB mini-sweep diagnostic exists at
  `v24_diagnostics/sweep_v24_crlb_ns.json`, but it is non-final and not a
  manuscript figure.
- Synchronization sweeps likely need rerun after V24-gauge metric integration.
- Localization sweeps are still under human/code-provenance review because the
  legacy solver state is overparameterized relative to V24.
- Do not rerun manuscript figures until the package-level runner and notebook
  bridge/refactor path are tested and explicitly approved.
