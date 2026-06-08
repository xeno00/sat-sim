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

A package-native V24 Fig. 4--7 diagnostic runner is implemented on branch
`codex/package-native-figures-4-7`. It uses package modules only, defines
explicit baseline semantics for without-cooperation, coarse JCLS, and refined
JCLS, and writes deterministic non-final raw CSV, summary CSV, NPZ, PDF,
metadata JSON, and provenance JSON outputs under `v24_figure_outputs/`. The
outputs are provenance/diagnostic artifacts only and are not manuscript figures.
The diagnostic artifacts are hardened with repo-relative paths, explicit
diagnostic-only/non-final/not-manuscript-ready flags, overwrite protection, and
output-root guardrails. If tests pass, the branch may be considered for merge as
diagnostic scaffold infrastructure only, not as final figure provenance.

A manuscript-candidate geometry/noise path is implemented on branch
`codex/manuscript-geometry-noise`. It adds MIT Stata reference LLA/ECEF
geometry, deterministic UE placement inside a 500 m disk, synthetic
Starlink-like LEO satellite geometry with a 30 degree elevation mask, and
separate DL/SL link-budget-derived range-domain sigmas. Candidate outputs are
written under `v24_manuscript_candidate_outputs/` with candidate-only,
non-final, not-manuscript-ready flags. These outputs are closer to V24
geometry/noise assumptions but are still not final manuscript figures because
algorithm fidelity remains unresolved.

A package-native V24 algorithm-fidelity path is implemented on branch
`codex/v24-algorithm-fidelity`. It adds Step 1 weighted GN downlink-only
coarse UE localization, Step 2 weighted LM over the full gauged V24 theta
vector, and Step 3 dynamic SCI/SFI information-form refinement with explicit
`F`, `Q`, and `Pi`. The manuscript-candidate Fig. 4--7 configs now use
`estimator_mode = v24_three_stage_dynamic`, and candidate outputs under
`v24_manuscript_candidate_outputs/` have been regenerated as non-final,
not-manuscript-ready artifacts. Synthetic satellite geometry and final human
signoff remain unresolved.

A status/rank honesty hardening pass is implemented on branch
`codex/v24-algorithm-fidelity`. Step 2 no longer reports success merely because
an LM step was accepted, Step 3 propagates upstream non-convergence/failure, and
candidate raw/summary outputs use conservative success semantics. Figure-run
rank metadata has been relabeled as `full_jcls_scenario_*` to avoid implying
baseline-specific observability. Baseline-specific rank diagnostics remain a
pending task.

A human-review Fig. 4--7 sprint is implemented on branch
`codex/human-ready-figures-sprint`. It adds deterministic non-truth-centered
multistart initialization, permits rank-deficient damped Step 2 updates only as
non-successful initializers, records Step 3 covariance-trace diagnostics, adds
baseline-specific observability/rank fields, and writes human-review package
outputs under `v24_human_review_outputs/`. The human-review report marks all
four figure families as review-only and not manuscript-ready because JCLS
success rates remain low, one-UE full-JCLS cases are unobservable, and refined
JCLS can still underperform the no-cooperation baseline.

An executable notebook regression audit is implemented on branch
`codex/notebook-regression-execution-audit`. It turns the prior static forensic
bridge into line-level notebook Datalink/measurement audits, deterministic
hand/notebook/package row-order fixtures, unit/clock executable fixtures, and a
safe extracted-class notebook smoke harness under
`v24_notebook_regression_outputs/executed_legacy/`. The audit verifies that the
legacy notebook and package share receiver/transmitter row ordering and
`range + transmitter_clock - receiver_clock` sign when package links are
supplied in notebook `get_links()` order. It also verifies the km/range-clock
representation against meters/seconds after a single speed-of-light
conversion. Full notebook figure reproduction is still not performed.

A safe legacy CRLB figure replay is implemented on branch
`codex/legacy-crlb-figure-replay`. It extracts selected notebook class/helper
definitions, replays the legacy `generate_FIM_data` CRLB figure family into
`v24_notebook_regression_outputs/executed_legacy/crlb_replay/`, and writes
raw CSV/NPZ plus redirected PDFs for `pos_crlb_0dB_0dB.pdf` and
`sync_crlb_0dB_0dB.pdf`. The replay preserves legacy all-clock symbolic state,
QR dependent-row removal, post-hoc position/clock slicing, `inv` for
localization bounds, `pinv` for synchronization bounds, and legacy plotting
behavior. The replay is marked `legacy_replayed_unverified_match`,
`legacy_replay: true`, and `manuscript_ready: false`; it is not V24-compatible
without replacement or human review.

A safe legacy clock-sweep estimator replay is implemented on branch
`codex/legacy-clock-sweep-replay`. It extracts selected notebook
class/helper definitions and replays the cell 31/32 clock-standard-deviation
logic in smoke mode and full legacy mode. The full replay writes to
`v24_notebook_regression_outputs/executed_legacy/clock_sweep_replay_full/`,
separate from the smoke replay under
`v24_notebook_regression_outputs/executed_legacy/clock_sweep_replay/`.
The replay writes raw CSV, summary CSV, NPZ arrays, redirected PDFs for
`pos_vary_clock.pdf` and `sync_vary_clock.pdf`, and metadata/final reports.
It preserves legacy all-clock state, IL preconditioning, full-clock LM,
global `map_filter_iteration` fallback behavior, truth-error acceptance gates,
smoothing/fitting transforms, and the legacy all-clock synchronization metric.
The artifacts are marked legacy replay, non-final, and not manuscript-ready.

A plot-gallery and cache/checkpointing layer is implemented on branch
`codex/plot-gallery-cache`. It renders generated/replayed diagnostic PDFs from
`v24_notebook_regression_outputs/`, `v24_human_review_outputs/`,
`v24_manuscript_candidate_outputs/`, and `v24_figure_outputs/` into PNG
previews under `v24_plot_gallery/previews/`, with browsable Markdown/HTML/JSON
gallery files under `v24_plot_gallery/`. The legacy clock-sweep replay now has
row-level JSON/NPZ cache entries under `v24_notebook_regression_outputs/cache/`
with script/notebook/extracted-cell/config hash validation, stale-cache
rejection, failure logs, and cache manifests. The full clock sweep has been
regenerated through valid cache hits instead of rerunning the 1619 s legacy
simulation.

A controlled migration Step B sprint is implemented on branch
`codex/migration-step-b-lm-no-truth-gate`. It adds
`step_b_lm_residual_acceptance`, replacing LM true-state acceptance with
observable residual-cost, finite-candidate, trust-ratio, and bounded-step
checks while preserving all-clock internals, legacy IL/MAP behavior, legacy
metrics, geometry/noise settings, and raw/display separation. Step B writes
tiny and medium diagnostics under
`outputs/migration_ladder/step_b_lm_residual_acceptance/`, updates gallery and
graph-package reports, and writes
`outputs/reports/STEP_B_LM_ACCEPTANCE_COMPARISON.*`. Medium Step B is healthy
and preserves all JCLS improvements; tiny Step B is partially degraded because
one synchronization comparison no longer improves, so the ladder conservatively
marks Step B as the first degraded correction and keeps Step A as the current
best migration step.

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
- Human-review Fig. 4--7 outputs currently conflict with the manuscript
  narrative in several regimes and must not be used as final manuscript
  figures without estimator/model redesign and human technical signoff.
- Legacy notebook ordered-link and unit/clock conventions are now verified
  compatible with the package for deterministic tiny fixtures, but the legacy
  notebook still keeps all clock parameters and uses mixed covariance/precision
  optimizer notation.
- Legacy CRLB replay is behavioral provenance only. It reproduces the notebook
  logic into a safe output folder, but the legacy all-clock/post-hoc bound path
  remains unsafe for V24 manuscript claims.
- Legacy clock-sweep full replay is behavioral provenance only. It
  demonstrates executable replay of the estimator sweep logic at the legacy
  seven-point, 25-iteration setting, but truth-gated LM/MAP behavior and
  all-clock synchronization metrics remain unsafe for V24 manuscript claims.

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
The package-native V24 Fig. 4--7 diagnostic runner/tests and non-final outputs
are implemented and provenance-hardened on branch
`codex/package-native-figures-4-7`.
The manuscript-candidate geometry/noise runner/tests and non-final candidate
outputs are implemented on branch `codex/manuscript-geometry-noise`.
The package-native V24 algorithm-fidelity runner/tests and refreshed non-final
candidate outputs are implemented on branch `codex/v24-algorithm-fidelity`.
Status/rank honesty hardening for that branch is implemented and candidate
outputs have been refreshed again with conservative success semantics and
`full_jcls_scenario_*` rank fields.
Human-review Fig. 4--7 package outputs, provenance, and
`HUMAN_REVIEW_REPORT.md/.json` are implemented on branch
`codex/human-ready-figures-sprint`; the report currently recommends review-only
status rather than manuscript consideration.
Executable notebook regression-audit artifacts are implemented on branch
`codex/notebook-regression-execution-audit`: line-level Datalink/Scenario
audits, deterministic row-order and unit fixtures, a safe extracted-class
legacy smoke harness, and upgraded figure-regression statuses. Ordered-link and
unit/clock representation are no longer blocking unresolved; they are verified
compatible for the audited tiny fixtures. Full figure reproduction remains
not done.
Safe legacy CRLB replay artifacts are implemented on branch
`codex/legacy-crlb-figure-replay` for `pos_crlb_0dB_0dB.pdf` and
`sync_crlb_0dB_0dB.pdf`. The figures are replayed into diagnostics only and
remain unverified matches/not manuscript-ready because of legacy all-clock and
post-hoc slicing caveats.
Safe legacy clock-sweep full replay artifacts are implemented on branch
`codex/legacy-clock-sweep-replay` for `pos_vary_clock.pdf` and
`sync_vary_clock.pdf`. The figures are replayed into diagnostics only and
remain unverified matches/not manuscript-ready because of legacy truth-gated
optimizer and all-clock metric caveats.
Plot-gallery previews and validated cache/checkpointing for the full
clock-sweep replay are implemented on branch `codex/plot-gallery-cache`; the
latest cached full replay reports 7/7 cache hits and writes
`v24_plot_gallery/PLOT_GALLERY.html`.
Canonical legacy graph-package outputs are implemented on branch
`codex/legacy-figures-gallery-crlb-nlos`. The branch verifies the merged base,
creates `outputs/` as the human-review graph package root, fixes Markdown/HTML
gallery rendering, regenerates LOS CRLB replay plots with corrected legends,
writes an explicit NLOS CRLB failure report, produces a bounded
legacy-compatible network-size smoke replay, marks package-native Fig. 4--7
outputs as suspect, and writes cache/status/index reports. All outputs remain
non-final and not manuscript-ready.
A medium legacy-compatible network-size replay is implemented on branch
`codex/legacy-network-size-and-v24-port-plan`. It runs a 4-by-3 grid over
`N_u={1,3,5,7}` and `N_s={4,8,12}` with deterministic seeds, per-row cache,
single-UE noncooperative baseline handling, and non-final PDF/CSV/NPZ/metadata
outputs under `outputs/legacy_replay/network_size_medium/`. It also writes
`V24_FIGURE_REPLACEMENT_PLAN` and `LEGACY_TO_PACKAGE_PORT_PLAN` reports. The
medium replay shows JCLS improvement in all baseline comparisons, but remains
legacy/all-clock/truth-gated provenance and is not manuscript-ready.
A controlled legacy-to-V24 migration ladder is implemented on branch
`codex/controlled-legacy-to-v24-migration`. It freezes the working legacy
behavior under `outputs/migration_baseline/legacy_behavior_freeze/`, exposes a
package-described `legacy_staged_compatible` mode via `jcls_sim.migration`, and
tests Step A (`raw_metrics_no_smoothing`) on tiny and medium grids under
`outputs/migration_ladder/`. Step A preserves localization/synchronization
improvements and does not trigger the stop rule. No output is manuscript-ready.
Step B (`step_b_lm_residual_acceptance`) is implemented on branch
`codex/migration-step-b-lm-no-truth-gate`; it removes LM truth-state acceptance
and records residual/trust-region diagnostics. Medium is healthy, tiny is
partially degraded, and the ladder conservatively marks Step B as the first
degraded correction pending review.
Step C diagnosis is implemented on branch `codex/migration-step-c-diagnosis`.
It splits MAP/EKF truth-dependence into C0/C1/C2/C3 sub-ablations under
`outputs/migration_ladder/` and writes
`outputs/reports/STEP_C_DIAGNOSIS_REPORT.md`. The current diagnosis isolates
`acceptance_replacement` as the primary breaking factor: C1 (legacy truth
covariance with observable MAP acceptance) is majorly degraded, while C2
(non-truth covariance with legacy truth acceptance) is only mildly degraded.
No C3 non-truth covariance candidate is healthy when paired with observable
MAP acceptance. These outputs are non-final and not manuscript-ready.

A hung-ladder recovery pass is implemented on branch
`codex/migration-step-c-diagnosis`. No still-running Python ladder process was
found. Existing canonical C0/C1/C2/C3 tiny and medium outputs appear complete
as diagnostic artifacts, so the recovery separates runner-safety risk from
output validity. `scripts/run_controlled_migration_ladder.py` now defaults to
tiny-only execution, requires `--medium` for medium rows, supports dry-run/
planned-work listing, max-row/substep limits, timeout metadata, bounded output
stems, row status logs, noncanonical bounded cache status, and a heartbeat at
`outputs/cache/migration_ladder/RUN_HEARTBEAT.json`. A bounded C0 two-row smoke
wrote to `outputs/migration_ladder/step_c0_legacy_map_instrumented/tiny_bounded/`
without overwriting canonical ladder outputs.

A composite observable MAP acceptance attempt is implemented on branch
`codex/step-c4-composite-map-acceptance`. It starts from Step B behavior, keeps
all-clock internals and legacy MAP covariance, and changes only MAP
acceptance/reversion to a composite observable rule using residual cost, prior
consistency, total MAP objective, covariance trace/information checks, bounded
state/position/clock update norms, and finite/symmetric/PSD covariance checks.
It writes `outputs/reports/STEP_C_ACCEPTANCE_DESIGN_NOTES.*`,
`outputs/migration_ladder/step_c4_composite_map_acceptance/`, and
`outputs/reports/STEP_C4_COMPOSITE_ACCEPTANCE_COMPARISON.*`. Tiny is not
catastrophic, so medium was run. Medium remains `major_degradation` versus
Step B: C4 accepted 43 MAP updates and rejected 2, but still does not approach
Step B behavior closely enough to replace legacy MAP truth acceptance.

Step C5 sliding-window MAP smoothing is implemented on branch
`codex/step-c5-sliding-window-map`. It keeps Step B residual/trust-region LM
behavior, all-clock internal state, legacy metrics, and legacy geometry/noise
settings, then replaces the legacy MAP/EKF truth-gated refinement with a small
`T=3`, `F=I` sliding-window MAP objective using configured diagonal `P0`, `Q`,
and measurement covariance `R`. Tiny was not catastrophic, so medium was run.
Medium remains `major_degradation` versus Step B. C5 records full-objective
decrease for accepted smoothing steps, but Step 3 improves over Step 2 in only
3/9 localization rows and 2/9 synchronization rows. Current evidence supports
reviewing Step B/LM-only as the clean estimator baseline before attempting
another Step 3 design.

Sparse Step 3 gate exploration is implemented on branch
`codex/step3-gate-exploration`. It tests NIS, line-search, nullspace,
clock/position-ratio, covariance/measurement inflation, and Huber gates on
representative cases `(N_u,N_s)=(3,8),(7,8),(7,12)`. Outputs are written under
`outputs/step3_gate_exploration/`, with the report at
`outputs/reports/STEP3_GATE_EXPLORATION_REPORT.md`. No tested gate improves
both localization and synchronization across the sparse set, so no medium
validation was run. Current evidence strengthens the recommendation to treat
Step B/LM-only as the clean estimator baseline and redesign Step 3
structurally rather than continue tuning scalar observable gates.

A low-cost diverse Step 3 exploration is implemented on branch
`codex/step3-low-cost-exploration`. Live legacy evaluation for broad lanes
exceeded the sprint runtime budget, so the completed Step 3 gate diagnostics
were reused as proxy evidence for six idea classes under
`outputs/step3_low_cost_exploration/`. The report
`outputs/reports/STEP3_LOW_COST_EXPLORATION_REPORT.md` marks proxy-only lanes
explicitly. No idea met promotion criteria for medium validation. Clock-drift
and Schur/nuisance-clock remain inconclusive because they were not executed as
true structural implementations in this low-cost fallback.

Step 3 deterministic micro-benchmarks are implemented on branch
`codex/step3-micro-benchmarks`. The benchmark runner
`scripts/benchmark_step3_micro_cases.py` executes six tiny toy cases and six
structural variants without running network-size graphs, full ladders, medium
grids, notebook code, or manuscript figure generation. Outputs are written
under `outputs/step3_micro_benchmarks/`, with the report at
`outputs/reports/STEP3_MICRO_BENCHMARK_REPORT.md`. The micro-benchmarks isolate
clock-only, position-only, clock-drift, common-clock/gauge, mixed
position-clock, and Schur/nuisance-clock behavior. Passing a micro-benchmark is
necessary but not sufficient for network-size promotion; Step B/LM-only remains
the current clean estimator baseline pending review of the micro-benchmark
branch.

Near-winner sparse Step 3 exploration is implemented on branch
`codex/step3-near-winner-sparse`. The runner
`scripts/explore_step3_near_winner_sparse.py` tests eight variants close to the
micro-benchmark winner on sparse cases `(N_u,N_s)=(3,8),(7,8),(7,12)`, using
Step B/LM-only as the baseline. Default execution is sparse-only; promoted
medium validation requires an explicit flag and is restricted to at most two
promoted variants. Outputs are written under
`outputs/step3_near_winner_sparse/`, with the report at
`outputs/reports/STEP3_NEAR_WINNER_SPARSE_REPORT.md`. The diagnostic promoted
`block_scaled_drift_loose_clock_prior` and `block_scaled_drift_base`; explicit
promoted-only medium validation was run for those variants. These outputs are
non-final and not manuscript figures.

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
- Package-native Fig. 4--7 diagnostic outputs exist under
  `v24_figure_outputs/`; these outputs use synthetic deterministic static
  geometry and flat range-domain noise, are intentionally not forced to match
  the legacy notebook, and require human technical review before any manuscript
  figure replacement decision.
- Manuscript-candidate Fig. 4--7 outputs exist under
  `v24_manuscript_candidate_outputs/`; these outputs use MIT/Stata-centered UE
  geometry, synthetic visible LEO satellites, and link-budget-derived DL/SL
  sigmas, and the package-native V24 three-stage estimator path. They are still
  non-final and not manuscript-ready because synthetic satellite geometry,
  estimator robustness, numerical behavior, and final human signoff remain
  unresolved.
- Human-review Fig. 4--7 outputs exist under `v24_human_review_outputs/`. They
  include PDFs, raw/summary CSV, NPZ, metadata, provenance, and a top-level
  human-review report. The outputs are candidate-only, non-final, not for
  submission, and currently do not support manuscript replacement.
- No manuscript text or response-letter text should be changed based on the
  current package-native Fig. 4--7 diagnostic or candidate outputs.
- Canonical graph-package outputs now live under `outputs/`. The best current
  visual-review artifacts are legacy-compatible replays, not V24-clean
  manuscript figures. `outputs/reports/CURRENT_GRAPH_STATUS.md` is the current
  source of truth for graph readiness and suspect outputs.
- `outputs/reports/V24_FIGURE_REPLACEMENT_PLAN.md` and
  `outputs/reports/LEGACY_TO_PACKAGE_PORT_PLAN.md` identify the next technical
  direction: port the helpful legacy staged-estimation behavior into
  package-native V24 code without truth leakage before final figure reruns.
- `outputs/reports/CONTROLLED_MIGRATION_LADDER.md` is the current source of
  truth for correction-by-correction migration health. The first tested
  correction, removing display smoothing from metrics, is healthy; truth-gate
  replacement remains the next major risk.
- `outputs/reports/STEP_C_DIAGNOSIS_REPORT.md` is the current source of truth
  for MAP/EKF truth-dependence diagnosis. It indicates MAP truth acceptance is
  the primary breaking factor; covariance replacement alone is not the primary
  failure in the current medium grid, but no fully non-truth candidate is yet
  healthy.
- `outputs/reports/HUNG_LADDER_RECOVERY_REPORT.md` is the current source of
  truth for recovery from the unsafe ladder invocation. It classifies the
  existing C outputs as complete diagnostics and recommends read-only review
  before further bounded execution.
- `outputs/reports/STEP_C4_COMPOSITE_ACCEPTANCE_COMPARISON.md` records that
  the first composite observable MAP acceptance criterion improves guardrail
  observability but remains majorly degraded versus Step B. MAP truth
  acceptance should not be considered replaceable yet.
- `outputs/reports/STEP_C5_SLIDING_WINDOW_MAP_COMPARISON.md` records that a
  simple Step-B-initialized sliding-window MAP smoother with configured
  diagonal `P0/Q` and full-objective-decrease acceptance remains majorly
  degraded versus Step B. `outputs/reports/STEP2_ONLY_VS_STEP3_REFINEMENT.md`
  currently supports reviewing Step B/LM-only as the clean estimator result
  before attempting another Step 3 design.
- `outputs/reports/STEP3_GATE_EXPLORATION_REPORT.md` records that sparse
  observable gate/covariance-control experiments did not produce a Step 3 gate
  that improves both localization and synchronization across representative
  cases. Medium validation was not run.
- `outputs/reports/STEP3_LOW_COST_EXPLORATION_REPORT.md` records a low-cost
  diverse Step 3 triage using prior gate diagnostics as proxy evidence. It did
  not identify a medium-validation candidate. It is useful for triage only, not
  as evidence that clock-drift or Schur/nuisance-clock structural approaches
  have been ruled out.
- `outputs/reports/STEP3_MICRO_BENCHMARK_REPORT.md` records deterministic toy
  Step 3 matrix/formulation checks. These diagnostics are not network-size
  graphs, are not manuscript outputs, and should be used only to decide which
  structural Step 3 variant deserves the next sparse network experiment.
- `outputs/reports/STEP3_NEAR_WINNER_SPARSE_REPORT.md` records a bounded
  sparse transfer check for block-scaled covariance and clock-drift variants.
  It is still diagnostic-only; the next decision should be a read-only review
  before any larger network-size validation or estimator integration.
