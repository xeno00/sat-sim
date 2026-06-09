# Pipeline Code Duplication Audit

Generated: 2026-06-09

## Executive Summary

The main duplication risk is not in the low-level V24 package math, which is reasonably centralized. It is in experiment-level pipeline schemas, legacy-compatible metrics, initialization, LM/MAP acceptance, covariance construction, and output metadata. Those concepts are repeatedly encoded in scripts, reports, and branch-local runners.

## Duplication Table

| concept | locations | current_variants | should_canonicalize_to | risk_if_not_canonicalized |
|---|---|---|---|---|
| Measurement ordering/sign convention | `jcls_sim/measurements.py`, `jcls_sim/jacobian.py`, `scripts/audit_notebook_measurements.py`, legacy replay namespace | V24 receiver/transmitter package convention; legacy notebook extracted convention | Keep package convention canonical; legacy adapters must declare compatibility | Silent row/sign mismatch in benchmark comparisons. |
| Parameter packing/gauge | `jcls_sim/parameters.py`, `jcls_sim/gauge.py`, legacy all-clock scripts | V24 gauged theta; legacy all-clock symbolic vector | `jcls_sim/pipelines/specs.py` must record system model and gauge mode | Mixing all-clock and V24 gauged results under one label. |
| Standard case definitions | `scripts/run_legacy_surgical_*.py`, reports, `AGENTS.md`, registry | Primary Ns=10 and secondary Ns=4 repeated manually | `jcls_sim/benchmark/standard_cases.py` | Primary benchmark drift or accidental Ns=4 substitution. |
| Pipeline specs/stage versions | `jcls_sim/migration.py`, legacy-surgical scripts, lineage report, scorecard | Dataclasses in multiple scripts; string tables in reports | `jcls_sim/pipelines/specs.py` and `registry.py` | Inconsistent pipeline IDs and truth-use claims. |
| Initialization | `jcls_sim/algorithm.py`, `jcls_sim/figure_generation.py`, legacy-surgical scripts, legacy notebook replay | Package deterministic init; legacy cube/truth-centered init; prior-region init | `jcls_sim/pipelines/*` adapter-level initialization declarations | Manuscript candidate may accidentally use truth-centered legacy start. |
| LM acceptance | `jcls_sim/algorithm.py`, `scripts/run_controlled_migration_ladder.py`, `scripts/run_legacy_surgical_*.py` | Package residual LM; legacy truth gate; residual/trust-region legacy-compatible | Pipeline adapter with explicit `truth_state_used_for_lm_acceptance` | Truth-gated and nontruth LM can be confused. |
| MAP/EKF/C7 update | `jcls_sim/algorithm.py`, `scripts/run_controlled_migration_ladder.py`, Step 3 exploration scripts, legacy-surgical scripts | C7 package update; C0-C5 diagnostics; legacy truth MAP; residual-scaled nontruth MAP | `jcls_sim/pipelines/c7.py` and `legacy_surgical.py` adapters | Step C claims could use an unintended experimental variant. |
| Covariance construction | `jcls_sim/algorithm.py`, `jcls_sim/fim.py`, `scripts/run_controlled_migration_ladder.py`, `scripts/audit_step3_residual_covariance.py`, legacy-surgical scripts | V24 FIM covariance, C7 residual-scaled clipped covariance, C3/C4/C5 variants, truth-derived legacy covariance | Pipeline-specific covariance metadata and tests | Heterogeneous state blocks may receive wrong scale or truth-derived covariance. |
| Synchronization metric | `jcls_sim/metrics.py`, legacy replay scripts, migration runner, legacy-surgical scripts | V24 reference-relative excluding reference; legacy all-clock MAE/RMSE style | `jcls_sim/benchmark/metrics.py` with explicit metric version | Legacy sync numbers may be cited as V24 reference-relative sync. |
| Position metric | `jcls_sim/metrics.py`, `jcls_sim/figure_generation.py`, legacy scripts | Mostly meters output from km positions; repeated conversions | `jcls_sim/benchmark/metrics.py` | m/km conversion mistakes in comparison tables. |
| Output metadata/manifests | many scripts and reports | Each runner writes local schema | `jcls_sim/benchmark/runner.py` result schema; scripts only serialize | Missing truth/units/readiness fields in benchmark cards. |
| Gallery/report generation | `scripts/render_all_figure_previews.py`, report builders | Multiple ad hoc report/gallery schemas | remain scripts-only, consume canonical metadata | Low risk to algorithms, high risk to bookkeeping clarity. |

## Highest-Risk Duplicates

1. Legacy all-clock synchronization metric vs V24 reference-relative metric.
2. Truth-gated legacy LM/MAP acceptance vs residual/trust-region nontruth acceptance.
3. Primary standard case repeated in scripts and reports.
4. Script-local pipeline specs for legacy-surgical prior-region path.
5. C7 covariance terminology and diagonal clipping recorded inconsistently across reports.

## Canonicalization Priority

1. Standard case registry.
2. Pipeline spec/truth-use/unit dataclasses.
3. Metric-normalization adapter for position and synchronization.
4. Legacy-surgical pipeline spec and safe adapter boundary.
5. Package-native C7 adapter.
6. Benchmark-card runner.

## Do Not Canonicalize Yet

- Notebook extraction/execution internals.
- Legacy CRLB replay logic.
- Parked GNSS/wave exploratory scripts.
- One-off Step 3 broad exploration scripts.
