# Legacy Surgical Truth-Gate Removal Report

> Diagnostic only; not manuscript-ready.

## 1. Executive summary

- Decision: `green_light`.
- L0 reproduces legacy/manuscript-like Stage B on the primary row: `True`.
- L1 preserves Stage B without truth-gated LM: `True`.
- L2 preserves Stage C without truth-derived covariance: `True`.

## 2. Whether L0 reproduces legacy

- `std_nu3_ns10_fullmesh_los_clock10ns_seed0`: L0 Stage A 5.66 m, Stage B 0.0714 m, Stage C 0.0714 m.
- `std_nu3_ns10_fullmesh_los_clock1us_seed0`: L0 Stage A 566 m, Stage B 0.0744 m, Stage C 0.0744 m.
- `std_nu3_ns4_fullmesh_los_clock1us_seed0`: L0 Stage A 2.23e+03 m, Stage B 0.88 m, Stage C 0.477 m.

## 3. Whether L1 preserves Stage B without truth-gated LM

- `std_nu3_ns10_fullmesh_los_clock10ns_seed0`: L1 Stage B 0.0744 m (1.04x L0), close=`True`.
- `std_nu3_ns10_fullmesh_los_clock1us_seed0`: L1 Stage B 0.0744 m (1x L0), close=`True`.
- `std_nu3_ns4_fullmesh_los_clock1us_seed0`: L1 Stage B 0.99 m (1.13x L0), close=`True`.

## 4. Whether L2 preserves Stage C without truth-derived covariance

- `std_nu3_ns10_fullmesh_los_clock10ns_seed0`: L2 Stage B 0.0744 m, Stage C 0.133 m (1.86x L0), close=`True`.
- `std_nu3_ns10_fullmesh_los_clock1us_seed0`: L2 Stage B 0.0744 m, Stage C 0.135 m (1.82x L0), close=`True`.
- `std_nu3_ns4_fullmesh_los_clock1us_seed0`: L2 Stage B 0.99 m, Stage C 0.771 m (1.62x L0), close=`True`.

## 5. Exact truth-gated lines/functions removed or replaced

| Component | Source | Classification | Surgical action |
|---|---|---|---|
| Legacy initialization | `JCLS_Simulation.ipynb:1243-1255` | `algorithmic_truth_use_remove` | L1: preserved by explicit branch constraint to keep legacy initial state logic; L2: preserved by explicit branch constraint to keep legacy initial state logic |
| LM acceptance | `JCLS_Simulation.ipynb:1413` | `algorithmic_truth_use_remove` | L1: replaced by residual/trust-region acceptance; L2: replaced by residual/trust-region acceptance |
| check_output reversion | `JCLS_Simulation.ipynb:1287-1297,1551` | `algorithmic_truth_use_remove` | L1: not used for residual-LM path; L2: not used for residual-LM path |
| MAP covariance | `JCLS_Simulation.ipynb:1258-1265` | `algorithmic_truth_use_remove` | L1: Stage C not run; L2: replaced by residual-scaled information pseudoinverse |
| MAP acceptance/reversion | `JCLS_Simulation.ipynb:1728-1738` | `algorithmic_truth_use_remove` | L1: Stage C not run; L2: replaced by observable residual/covariance checks |
| Offline localization/synchronization metrics | `JCLS_Simulation.ipynb:1567-1620` | `offline_metric_truth_use_ok` | L1: used for metrics only; L2: used for metrics only |
| CRLB/Jacobian diagnostics at true state | `JCLS_Simulation.ipynb:2913,3500` | `legacy_reproduction_truth_use_only` | L1: not used by this runner; L2: not used by this runner |

## 6. Units ledger for the legacy path

| Item | Unit | Surgical policy |
|---|---|---|
| Position/range state | kilometer internally | preserved; output localization metric is converted to meters by legacy helper |
| Range-like measurements | kilometer-equivalent legacy TOA/range residual | preserved; no gauge or unit cleanup in this branch |
| Clock state | range-equivalent kilometer in symbolic delta entries | preserved |
| Synchronization metric display | nanoseconds | reported as ns in raw/summary while retaining seconds fields where useful; not V24 reference-relative RMSE |
| Initialization perturbation | kilometer-scale error_range argument | preserved |
| Speed of light constant | legacy notebook uses approximate 300000 km/s; package constant is km/s | ledger only; no unit conversion introduced |
| Measurement covariance/noise | km^2 covariance after seconds-to-km conversion | preserved |
| Parameter ordering | lexicographic symbolic order | preserved because metric slicing depends on it |

## 7. Legacy quirks preserved

- Legacy notebook geometry and symbolic state ordering.
- Legacy all-clock state convention.
- Legacy truth-centered initialization around the true UE positions.
- Legacy measurement ordering and query_measurements noise generation.
- Legacy IL initialization and LM/MAP stage sequence.
- Legacy metric definitions for offline localization and synchronization error.
- Legacy error_range=100.0 initialization perturbation.

## 8. Legacy quirks suspicious

- Legacy L0 LM and check_output use true-state error for acceptance/reversion.
- All pipelines preserve legacy truth-centered initialization because the branch isolates decision/covariance changes only.
- Legacy L0 MAP covariance uses squared true-state error.
- Legacy L0 MAP fallback path may leave Stage C equal to Stage B in these bounded rows.
- Internal position/range states are km while output localization is meters; no gauge or unit cleanup was attempted.
- Legacy synchronization is all-clock mean absolute error, not V24 reference-relative RMSE.
- Legacy SNR/covariance code contains unit-suspicious km/m mixing; this branch preserves it rather than silently correcting it.

## 9. Whether this path is better than package-native C7 recreation

- Better for manuscript-like reproduction in bounded rows: `True`.
- Recommendation: Pause current package-native manuscript recreation for final figures; use it only as a diagnostic until it matches this legacy-surgical path.

## 10. Recommended next action

Promote the legacy-surgical path for final candidate figure generation, with the current package-native C7 recreation paused until separately diagnosed.

## Figures

- `legacy_surgical_stage_error_comparison`: `outputs\legacy_surgical_truth_gate_removal\figures\legacy_surgical_stage_error_comparison.png`, `outputs\legacy_surgical_truth_gate_removal\figures\legacy_surgical_stage_error_comparison.pdf`
- `legacy_surgical_lm_cost_trace`: `outputs\legacy_surgical_truth_gate_removal\figures\legacy_surgical_lm_cost_trace.png`, `outputs\legacy_surgical_truth_gate_removal\figures\legacy_surgical_lm_cost_trace.pdf`
- `legacy_surgical_truth_use_map`: `outputs\legacy_surgical_truth_gate_removal\figures\legacy_surgical_truth_use_map.png`, `outputs\legacy_surgical_truth_gate_removal\figures\legacy_surgical_truth_use_map.pdf`

## Safe claims

- On the bounded standard cases, residual/trust-region LM reproduces the L0 Stage B localization result without true-state LM acceptance.
- For the primary standard case, residual-scaled information covariance gives a non-truth Stage C update that remains sub-meter and close to L0.
- L0 is provenance/reproduction evidence only and is not deployable algorithm evidence.
- The notebook file was not executed end-to-end; selected extracted legacy definitions were executed.
- In L1/L2, truth-gated LM/MAP decisions and truth-derived MAP covariance are removed; legacy truth-centered initialization remains preserved and documented.

## Unsafe claims

- Do not claim the legacy notebook results were originally truth-free.
- Do not claim the package-native C7 recreation is validated by these results.
- Do not claim broad-sweep robustness; this branch intentionally ran only bounded standard rows.
- Do not use L0 as manuscript algorithm evidence.
- Do not claim comparability with package-native C7 unless the full estimator/clock/gauge/metric/unit/seed tuple is matched.
