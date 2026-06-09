# Pipeline Downselect Report

Generated: 2026-06-09

## Executive Summary

The best path to pursue for manuscript result generation is not the broad C7/package-native branch as currently configured. The clean package-native C7 path is theory-aligned and important as a backup/reference, but its manuscript-recreation outputs for the primary case are much weaker than the legacy-like results and its clock-sweep behavior remains unstable.

The strongest existing bridge is the legacy-surgical prior-region family:

`legacy_compatible_all_clock + A0_prior_region_il + B1_residual_trust_region_lm_no_truth_gate + C_surgical_residual_scaled_info_map`

This path is close to the legacy manuscript behavior while removing the most problematic estimator-decision truth gates. The most defensible part of this path is currently Step B residual/trust-region LM. Step C should be carried as a candidate refinement, not as a final claim, until a normalized benchmark-card run and figure-family validation show it is robust.

## Primary Pipeline Tuple

| field | value |
|---|---|
| system_model_version | legacy_compatible_all_clock |
| initialization_version | coarse_prior_region_initialization |
| stage_a_version | A0_prior_region_il |
| stage_b_version | B1_residual_trust_region_lm_no_truth_gate |
| stage_c_version | C_surgical_residual_scaled_info_map |
| metric_version | legacy_all_clock_metric_pending_v24_reference_relative_recompute |
| truth_usage | truth used for simulation prior construction and offline metrics; no truth-state acceptance or truth-derived covariance |
| units_version | legacy_km_range_equivalent_clock_units_with_m_ns_reporting |

## Why This Path

1. It has primary-case data at `N_u=3,N_s=10,\sigma_delta=1 us`.
2. It reaches sub-meter localization in Step B on the primary case.
3. It removes legacy LM truth acceptance and truth-derived covariance from the estimator decision path.
4. It preserves enough legacy model behavior to plausibly explain the manuscript figures.
5. It is simpler and faster to validate than another open-ended Step 3 design.

## Main Caveats

- It still uses legacy all-clock internal state and legacy synchronization metrics unless recomputed.
- It uses truth for simulation prior construction and offline metric labels.
- Stage C does not consistently improve over Step B in the primary-card variants inspected.
- The prior-region initialization assumption must be stated and tested across radii/seeds before manuscript use.
- V24 reference-relative synchronization metrics should be recomputed for any manuscript candidate outputs.

## Backup Pipeline

`package_native_current + A1_package_dl_only + B1_residual_lm + C7_residual_cov_sync_safeguard`

The package-native C7 path remains the backup because it is the cleanest against V24 gauge, metric, measurement, and no-truth constraints. Its current weakness is performance and clock-sweep instability under manuscript-like recreation. It should not be the primary manuscript-result path unless the normalized benchmark-card runner shows the legacy-surgical result was an artifact of mismatched assumptions.

## Required Minimal Next Run

Build and run a normalized benchmark-card runner for:

`std_nu3_ns10_fullmesh_los_clock1us_seed0`

Include exactly these candidate families first:

1. legacy-surgical prior-region path, with multiple prior radii already represented if cheap;
2. controlled Step B residual LM-only path;
3. package-native C7 path;
4. legacy truth-gated L0 only as a provenance reference, clearly excluded from manuscript evidence.

The runner must produce initialization, Step A, Step B, and Step C localization/synchronization metrics with one shared schema and explicit truth-use/units metadata.

## Recommendation

Pursue the legacy-surgical prior-region path as the primary manuscript-result generation candidate, with Step B as the first defensible result backbone. Treat Stage C as an optional/candidate refinement until the normalized primary benchmark card, V24 metric recomputation, multi-seed robustness, and figure-family validation are complete.
