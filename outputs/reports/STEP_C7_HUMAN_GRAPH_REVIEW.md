# Step C7 Human Graph Review

## Executive Summary

Verdict: **PASS WITH CAVEAT**.

The merged `step_c7_residual_cov_sync_safeguard` outputs are visually and scientifically credible enough for human graph review and for a bounded candidate-figure validation pass. They are **not** manuscript-ready and should not be described as final result figures.

Main validation facts are consistent across `raw.csv`, `summary.csv`, metadata, the C7 report, and the gallery:

- Medium grid: `N_u=[1,3,5,7]`, `N_s=[4,8,12]`.
- Position improved: `12/12`.
- Synchronization improved: `9/12`.
- Both improved: `9/12`.
- Mean/max position ratio: `0.054160` / `0.144487`.
- Mean/max synchronization ratio: `0.385611` / `1.000000`.
- Fallback count: `3`.
- Fallback rows: `(1,4)`, `(1,8)`, `(1,12)`.
- Fallback reason: `single_user_clock_update_not_observable`.
- Truth-state acceptance: `false`.
- Truth-derived covariance: `false`.

The main caveat is terminology: the C7 covariance path should be described as **typed block-extracted, diagonal-clipped residual-scaled covariance**, not as a full block covariance or cross-covariance method.

## Merge and Review Recommendation

- Merge status: `codex/step-c7-residual-cov-sync-safeguard` was fast-forward merged into `main`.
- Merged commit: `89a9b2a`.
- Push status: `main` was pushed and is synced with `origin/main`.
- Review recommendation: proceed to bounded candidate-figure validation, keeping all outputs non-final.
- Do not mark C7 outputs manuscript-ready.

## Subagent / Lane Status

Subagents were spawned for rendering, raw-data, and scientific/no-truth/terminology lanes. They did not complete within a bounded wait and were closed. The orchestrator completed all lanes by direct inspection.

| Lane | Status | Review Owner | Result |
|---|---|---|---|
| Graph Rendering Review | orchestrator_completed | orchestrator fallback | PASS WITH CAVEAT |
| Raw Data Consistency Review | orchestrator_completed | orchestrator fallback | PASS |
| Scientific Claims Review | orchestrator_completed | orchestrator fallback | PASS WITH CAVEAT |
| Terminology/Caveat Review | orchestrator_completed | orchestrator fallback | PASS WITH CAVEAT |
| No-Truth-Leak Review | orchestrator_completed | orchestrator fallback | PASS |

## Plot-By-Plot Review

| Plot | Render | Labels / Legends | Consistency With Data | Human Review Suitability | Caveats |
|---|---|---|---|---|---|
| `localization_error_vs_satellites` | PASS | Axes and legend clear. | Consistent with 12/12 position improvement and ratios below 1. | Suitable for human review. | C7 and Step B are on very different scales; candidate figure may need log scale, inset, or ratio panel. |
| `synchronization_error_vs_satellites` | PASS | Axes and legend clear. | Consistent with 9/12 sync improvement and single-UE fallback equality. | Suitable for human review. | Fallback rows are visible as equal Step B/C7 values but not explicitly annotated. Units are km; a candidate plot may need seconds/ns conversion. |
| `position_ratio_heatmap` | PASS | Ratio label is clear. | All cells are below 1 and match raw ratios. | Suitable for human review. | Good diagnostic plot; candidate figure should explain ratio semantics. |
| `sync_ratio_heatmap` | PASS | Ratio label is clear. | Single-UE rows are exactly 1.0; other rows below 1. | Suitable for human review. | Should annotate or caption that 1.0 rows are safeguard fallbacks. |
| `fallback_count_by_nu_ns` | PASS | Axes and colorbar clear. | Fallbacks only at `N_u=1`, matching raw data. | Suitable for human review. | Useful as companion diagnostic, not a main performance figure. |
| `update_norm_by_state_block` | PASS WITH CAVEAT | Labels render, but units/scaling are not explicit. | Mean update norms are plausible and consistent with C7 diagnostics. | Suitable as internal diagnostic. | Heterogeneous state blocks have different units/scales; do not use for manuscript-style claims without normalization. |
| `covariance_eigenvalue_diagnostics` | PASS WITH CAVEAT | Axes render; color/group meaning is not explained. | Values are consistent with covariance diagnostics. | Suitable as internal diagnostic. | Needs legend or explicit encoding description before candidate presentation. |
| `ablation_comparison` | PASS | Legend and threshold line clear; x labels are readable but crowded. | Matches summary: no-safeguard and no-residual-scaling weaken sync behavior. | Suitable for human review. | Uses mean ratios only; max-ratio caveats should remain in text. |

## Raw-Data Consistency Summary

The plotted behavior matches `outputs/step_c7_residual_cov_sync_safeguard/raw.csv` and `summary.csv`.

Main C7 row details:

- `N_u=1` rows: position improves; synchronization ratio is `1.0`; fallback triggered.
- `N_u=3,5,7` rows: position and synchronization both improve.
- No position ratio is greater than `1`.
- No synchronization ratio is greater than `1`.
- `objective_decreased` is `True` for all main C7 rows.
- Truth flags for acceptance, covariance, and safeguard are all `False`.

Ablation summary:

- Without safeguard: max synchronization ratio worsens to `1.679045`.
- Without residual scaling: mean/max synchronization ratio worsen to `1.158285` / `1.879426`.
- Without drift: still no sync worsening, but mean synchronization ratio weakens to `0.473133`.

## Scientific Interpretation

C7 shows credible Step 3 improvement over Step B on this bounded medium validation grid. The strongest evidence is that localization improves in every row, synchronization improves in all multi-UE rows, and the non-truth safeguard prevents single-UE clock/drift updates from degrading synchronization.

The single-UE fallbacks are scientifically reasonable because single-UE clock/drift refinement is not observable/safe in the same way as cooperative multi-UE cases. The fallback behavior is visible in both the synchronization ratio heatmap and fallback-count heatmap.

The safeguard appears to be an observability/consistency control rather than a hidden truth gate. The recorded truth flags are false for acceptance, covariance, and safeguard logic. Truth is used only for offline validation metrics and ratios.

## Safe Claims

The following claims are safe for internal review:

- C7 is a non-final diagnostic Step 3 estimator mode.
- C7 improves localization on all 12 medium-grid diagnostic rows.
- C7 improves synchronization on 9 of 12 rows.
- C7 does not worsen synchronization on the bounded medium grid because the single-UE safeguard reverts unsafe clock/drift updates.
- The safeguard is non-truth-based in the recorded implementation and metadata.
- The current plots support bounded candidate-figure validation.

## Unsafe Claims

The following claims remain unsafe:

- C7 is manuscript-ready.
- C7 proves final Step 3 performance for the paper.
- C7 validates all manuscript figures.
- C7 behavior has been validated on full legacy figure sweeps.
- The covariance method uses dense block covariance or cross-covariance.
- Single-UE C7 improves synchronization; the current result is equality after fallback.

## Terminology Corrections Needed

Before any candidate-figure report or broader human-facing summary, describe the covariance as:

> typed block-extracted, diagonal-clipped residual-scaled covariance

Avoid:

- "full block covariance";
- "full cross-covariance";
- unqualified "block covariance" if it implies retained off-diagonal structure.

Existing C7 report language saying "block-diagonal, diagonal-clipped" is mostly acceptable for internal diagnostics, but the clearer phrase above should be used going forward.

## No-Truth-Leak Status

PASS.

The C7 raw rows record:

- `truth_state_used_for_acceptance=False`;
- `truth_state_used_for_covariance=False`;
- `truth_state_used_for_safeguard=False`.

Truth-state errors are used only for offline position/synchronization metric calculation and ratio labels.

## Readiness

- Ready for human graph review: **yes**.
- Ready for bounded candidate-figure validation: **yes, with caveats**.
- Ready for manuscript submission: **no**.

## Recommended Next Action

Run a bounded C7 candidate-figure validation pass only after human approval. The next pass should:

1. keep C7 outputs non-final;
2. retain Step B as the comparison baseline;
3. use the precise covariance terminology;
4. annotate fallback rows explicitly;
5. consider seconds/ns units for synchronization plots;
6. avoid broad exploration or new Step 3 variants.

