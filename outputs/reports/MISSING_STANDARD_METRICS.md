# Missing Standard Metrics

Generated: 2026-06-09

Primary standard case:

`std_nu3_ns10_fullmesh_los_clock1us_seed0`

## Missing or Incomplete Primary Metrics

| pipeline_id | missing fields | why it matters | next action |
|---|---|---|---|
| controlled_migration_step_b_lm_only | primary Ns=10/1us Step A/B card | This is the cleanest legacy-compatible Step B baseline, but the merged medium grid is not the primary standard. | Include in normalized benchmark-card runner. |
| package_native_c7 | pre-Step-A initialization metric only | The normalized runner now has the exact primary Step A/B/C card, but the package-native adapter does not yet report a distinct pre-Step-A initialization metric. | Add initialization metric capture if needed; otherwise use the current card for package-native Step A/B/C comparison only. |
| legacy_surgical_prior_region | V24 reference-relative synchronization metric; multi-seed robustness; figure-family raw outputs | Strongest path, but legacy sync metric and one-seed performance are not enough for final manuscript evidence. | Recompute metrics under unified schema and run bounded candidate figure validation. |
| legacy_network_size_replay | primary 1us network-size row for Ns=10 | Existing replay is useful provenance but uses a different clock standard deviation. | Do not use as primary; optional legacy reference rerun only if needed. |
| c7_candidate_figure_validation | primary Ns=10 network row | Candidate validation used sparse nearby network rows. | Do not substitute Ns=8/12; use normalized runner. |
| gnss_baseline_exploration | all primary fields | Parked branch not integrated into main lineage. | Keep parked until lineage/units entry and human review. |
| wave_results_exploration | all primary fields | Parked branch not integrated into main lineage. | Keep parked until lineage/units entry and human review. |

## Do Not Substitute

Do not substitute `std_nu3_ns4_fullmesh_los_clock1us_seed0` into any primary field. That case is the secondary low-satellite stress case only.

## Minimal Diagnostic Run

The first normalized benchmark-card runner now exists under `outputs/standard_benchmark_cards/`.
The remaining minimal diagnostic work is to add safe adapters for the non-package-native candidates with:

1. shared geometry/noise/clock settings;
2. shared output schema;
3. explicit truth-use fields;
4. units fields for position, clock, measurement, and metrics;
5. initialization, Step A, Step B, and Step C metric columns;
6. legacy truth-gated output included only as provenance reference.
