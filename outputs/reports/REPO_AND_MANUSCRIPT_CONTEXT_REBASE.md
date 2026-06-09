# Repo And Manuscript Context Rebase

Generated: 2026-06-09

## Executive Summary

This pass re-read the `sat-sim` workflow state, branch ledger, result registry, major reports, package code paths, and both V23 and WIP V24 manuscript sources. No manuscript files were edited and no simulations or figure-generation runs were launched.

The repository now contains two very different result directions:

1. A clean, V24-aligned package-native path, especially C7, with strong gauge/units/no-truth properties but weak manuscript-scale candidate performance and unstable clock-sweep behavior.
2. A legacy-compatible surgical path that stays closer to the manuscript-producing algorithm while removing the most problematic estimator-decision truth gates. This path gives primary-case sub-meter localization and is currently the most promising route for manuscript result generation.

The recommended primary path is:

`legacy_compatible_all_clock + A0_prior_region_il + B1_residual_trust_region_lm_no_truth_gate + C_surgical_residual_scaled_info_map`

However, Step B residual LM is the current evidentiary backbone. Step C should remain candidate/refinement only until normalized benchmark and figure-family validation pass.

## Files And Manuscripts Inspected

| category | path |
|---|---|
| sat-sim workflow | `AGENTS.md`, `RUN_CODEX.md`, `PROJECT_STATUS.md`, `docs/tasks/NEXT.md`, `docs/tasks/QUEUE.md` |
| branch ledger | `outputs/reports/ACTIVE_BRANCH_LEDGER.md/json` |
| result lineage | `outputs/reports/RESULT_VERSION_LINEAGE_AND_UNITS_REVIEW.md/json`, `outputs/registry/RESULT_REGISTRY.md/json` |
| current graph status | `outputs/reports/CURRENT_GRAPH_STATUS.md/json` |
| V23 clean manuscript | `C:/Users/James/MIT Dropbox/James Morrison/Academics/MIT/WINSLab/WINS Manuscripts/Morrison, J/SCL-NTN-TAES-2025/All-Version-Archive/V23/SCL-NTN-TAES-2025-V23.tex` |
| WIP V24 clean manuscript | `C:/Users/James/MIT Dropbox/James Morrison/Academics/MIT/WINSLab/WINS Manuscripts/Morrison, J/SCL-NTN-TAES-2025/Work-In-Progress/SCL-NTN-TAES-2025-V24.tex` |

The WIP V24 clean source appears to be the current clean manuscript copy for result-claim alignment. The tracked WIP source was also identified, but this audit made no manuscript edits.

## Repository Organization State

- `sat-sim` has a persistent Codex workflow with `AGENTS.md`, `RUN_CODEX.md`, `PROJECT_STATUS.md`, and task docs.
- Branch/disposition discipline is active; `outputs/reports/ACTIVE_BRANCH_LEDGER.md/json` is the canonical active-branch source.
- The primary standard benchmark is `std_nu3_ns10_fullmesh_los_clock1us_seed0`.
- The old `std_nu3_ns4_fullmesh_los_clock1us_seed0` case is secondary only.
- Major report-producing branches have been merged, parked, or quarantined. Parked GNSS/wave branches remain outside main.

## Branch And Active Work State

The active branch ledger lists six non-main branches as of the latest reconciliation:

- `codex/gps-gnss-baseline-exploration`: parked exploration.
- `codex/jcls-wave-results-exploration`: parked exploration.
- `codex/wave-observability-estimator-gap-audit`: parked local worktree branch.
- `codex/legacy-surgical-truth-gate-removal`: merged/delete-safe local worktree ref.
- `codex/legacy-surgical-prior-region-initialization`: merged/delete-safe local worktree ref.
- `codex/legacy-figures-gallery-crlb-nlos`: human-review branch.

Parked branches may contain additional reports not present on main. Their outputs should not be treated as current evidence until lineage and units entries are integrated.

## Manuscript Result Requirements

See `outputs/reports/MANUSCRIPT_RESULT_REQUIREMENTS_MATRIX.md/json`.

Key requirements:

- Fig. 4: localization vs number of satellites, meters, cooperative curves should not treat `N_u=1` as cooperative JCLS.
- Fig. 5: synchronization vs number of satellites, ns, V24 reference-relative and excluding reference satellite.
- Fig. 6: localization vs clock standard deviation, `N_u=3,N_s=10`.
- Fig. 7: synchronization vs clock standard deviation, `N_u=3,N_s=10`.
- CRLB figures: use full gauged FIM/rank semantics, not legacy post-hoc slicing.

## Pipeline Inventory

| family | status | summary |
|---|---|---|
| original notebook/manuscript path | legacy_reference_only | Strong performance but truth-gated and all-clock; not defensible as final evidence. |
| legacy clock/network/CRLB replays | legacy_reference_only | Useful provenance; preserves legacy behavior and caveats. |
| controlled migration Step B | human_review_only | Strongest simple non-truth estimator-decision subpath; needs primary normalized card. |
| Step C0/C1/C2/C3/C4/C5 explorations | debugging_only | Diagnosed why naive Step 3 replacements fail; not a forward baseline. |
| C7 package-native path | human_review_only | Cleanest V24/no-truth path; performance mismatch and clock-sweep instability block primary use. |
| legacy-surgical truth-gate removal | human_review_only | Removes key truth gates; primary Step B strong; Step C mixed. |
| legacy-surgical prior-region initialization | pursue_as_primary | Best existing bridge from manuscript-scale behavior to non-truth estimator decisions. |
| GNSS/wave explorations | parked/debugging_only | Not current manuscript-result evidence. |
| theory/code tests | infrastructure | Gauge, measurement, Jacobian, FIM, metrics, CRLB tests support later validation. |

## Primary Standard-Case Metric Availability

See `outputs/reports/STANDARD_SCENARIO_PIPELINE_SCORECARD.md/json`.

Short version:

- Legacy truth-gated L0 has primary metrics but is provenance only.
- Legacy clock-sweep replay has primary clock-sweep metrics but is provenance only.
- C7 manuscript recreation has primary metrics, but performance is tens of meters.
- Legacy-surgical truth-gate removal and prior-region runs have primary metrics and are the best current candidates.
- Controlled migration Step B and package-native C7 still need a normalized same-run primary card.

## Pipeline Performance Summary

Representative primary-case rows:

| pipeline | Step A pos m | Step B pos m | Step C pos m | Step A sync ns | Step B sync ns | Step C sync ns | verdict |
|---|---:|---:|---:|---:|---:|---:|---|
| legacy truth-gated L0 | 566.249 | 0.074 | 0.074 | 1253.463 | 491.942 | 491.942 | legacy reference only |
| legacy clock-sweep replay at 1 us | 463.679 | 0.150 | 0.034 | 638.383 | 43.522 | 43.522 | legacy reference only |
| C7 manuscript recreation | 374.932 | 88.913 | 77.485 | 925.389 | 82.723 | 71.860 | clean but weak |
| legacy-surgical truth-gate removal | 566.249 | 0.074 | 0.135 | 1253.463 | 492.006 | 492.006 | strong Step B, mixed Step C |
| legacy-surgical prior-region R0=10m | 566.249 | 0.074 | 0.095 | 1253.463 | 492.183 | 492.183 | primary candidate |
| legacy-surgical prior-region R0=100000m | 566.249 | 0.074 | 0.036 | 1253.463 | 491.153 | 491.153 | promising but needs robustness |

## Truth-Use And Units Table

| pipeline | truth use | units status | readiness |
|---|---|---|---|
| legacy truth-gated L0 | truth-state acceptance and covariance | units_consistent_but_legacy | legacy_reference_only |
| controlled Step B | no truth-state LM acceptance; truth only metrics | units_consistent_but_legacy | human_review_only |
| legacy-surgical prior-region | truth for simulation prior construction and metrics, not estimator decisions | units_consistent_but_legacy | pursue_as_primary |
| package-native C7 | truth only metrics | units_consistent | human_review_only |
| legacy CRLB replay | legacy all-clock/post-hoc slicing | units_consistent_but_legacy | legacy_reference_only |
| package-native CRLB diagnostics | no truth gates | units_consistent | diagnostic_only |

## Contradictions And Unresolved Discrepancies

1. C7 diagnostic/candidate outputs once suggested very strong network-size behavior, while C7 manuscript recreation at the primary case reports tens of meters. This remains unresolved and is not a primary-standard comparison until the normalized benchmark-card runner is built.
2. Legacy-like paths produce centimeter/sub-meter localization at the primary case, while package-native C7 produces tens of meters. This likely reflects model/initialization/system-path mismatch, not just Step 3 details.
3. Legacy all-clock synchronization metrics are not automatically V24 reference-relative synchronization metrics. Any selected legacy-compatible path needs metric recomputation before manuscript use.
4. Step C improves some localization cards but not consistently enough to support a broad refined-JCLS claim.

## Recommended Primary Pipeline

Pursue:

`legacy_compatible_all_clock + A0_prior_region_il + B1_residual_trust_region_lm_no_truth_gate + C_surgical_residual_scaled_info_map`

Use Step B residual LM as the first defensible result backbone. Treat Step C as candidate/refinement until normalized validation passes.

## Backup Pipeline

Retain:

`package_native_current + A1_package_dl_only + B1_residual_lm + C7_residual_cov_sync_safeguard`

Use it as the theory-clean backup and regression/reference path, not the primary manuscript-result generator right now.

## Minimal Next Experiment

Build a normalized benchmark-card runner for:

`std_nu3_ns10_fullmesh_los_clock1us_seed0`

Include:

1. legacy-surgical prior-region path;
2. controlled Step B LM-only path;
3. package-native C7 path;
4. legacy truth-gated L0 as provenance reference only.

Required outputs:

- initialization, Step A, Step B, and Step C localization/sync metrics;
- V24 reference-relative synchronization where possible;
- legacy all-clock sync retained separately if needed;
- truth-use fields;
- units fields;
- candidate readiness/disposition.

## Stop / Merge / Quarantine Recommendations

- Do not merge parked GNSS/wave outputs as manuscript evidence yet.
- Keep legacy-surgical branches merged as diagnostic/report evidence, but do not call them final.
- Keep legacy truth-gated outputs as reference-only.
- Pause new C7 algorithm exploration unless it is needed to explain normalized benchmark-card discrepancies.
- Prioritize one benchmark-card runner over new broad sweeps.

## Explicit Next Codex Prompt Sketch

```text
Follow AGENTS.md.

MODE: IMPLEMENT_APPROVED

Build a normalized primary benchmark-card runner for std_nu3_ns10_fullmesh_los_clock1us_seed0. Include legacy-surgical prior-region, controlled Step B LM-only, package-native C7, and legacy truth-gated L0 as reference-only. Do not generate manuscript figures. Write raw CSV/JSON cards with initialization, Step A, Step B, and Step C localization/synchronization metrics, truth-use metadata, units metadata, V24 reference-relative sync where possible, and readiness flags. Update result lineage and the downselect reports after the run.
```
