# Executable Notebook Regression Report

- Ordered-link convention: verified compatible for receiver/transmitter rows.
- Unit/clock representation: verified compatible for km/range-equivalent clocks.
- Full figure reproduction remains not done.

```json
{
  "status": "complete_executable_bridge_prerequisites",
  "artifact_status": "non_final_executable_notebook_regression_report",
  "notebook_and_package_row_conventions_match": true,
  "ordered_link_convention_resolution": "verified_compatible",
  "unit_clock_representation_resolution": "verified_compatible",
  "safe_notebook_smoke_status": "executable_smoke_passed",
  "safe_notebook_smoke_artifact": "v24_notebook_regression_outputs\\executed_legacy\\legacy_notebook_smoke.json",
  "poor_package_native_performance_plausibly_from_row_order_or_unit_mismatch": false,
  "poor_package_native_performance_note": "The deterministic fixtures do not support row-order or unit mismatch as the primary explanation. Remaining causes include optimizer/gauge differences, rank/observability, initialization, geometry/noise, or legacy oracle-gated behavior.",
  "full_notebook_figure_reproduction_feasible_now": false,
  "full_notebook_figure_reproduction_blocker": "Tiny safe smoke execution is allowed; full figure reproduction still requires an approved execution harness for legacy optimizer and figure cells.",
  "next_step_toward_target_figures": "Run and review scripts/run_legacy_notebook_smoke.py, then build a read-only legacy figure-cell harness that redirects outputs under v24_notebook_regression_outputs/executed_legacy/ without touching manuscript figure folders.",
  "artifacts": [
    "NOTEBOOK_DATALINK_LINE_AUDIT.md/json",
    "NOTEBOOK_MEASUREMENT_ORDER_AUDIT.md/json",
    "UNIT_CLOCK_EXECUTABLE_FIXTURE.md/json",
    "FIGURE_REGRESSION_TABLE.md/json"
  ]
}
```