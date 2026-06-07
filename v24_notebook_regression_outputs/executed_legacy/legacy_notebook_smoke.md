# Legacy Notebook Smoke

- Status: executable_smoke_passed
- Scope: selected class cells only; no figure cells; no notebook source edits.
- Links: [(1, 2), (1, 3), (1, 4), (2, 1), (2, 3), (2, 4)]
- Optimizer results: {'IL': {'status': 'failed_execution', 'error_type': 'ValueError', 'error': "('IL', 'did not improve estimate')"}, 'LM': {'status': 'passed', 'state_norm_error_km': 0.0}, 'EKF': {'status': 'passed', 'state_norm_error_km': 0.0, 'covariance_shape': [10, 10]}}

```json
{
  "status": "executable_smoke_passed",
  "artifact_status": "non_final_legacy_notebook_smoke",
  "notebook_source_modified": false,
  "full_notebook_executed": false,
  "selected_cells_executed": [
    "Node",
    "User",
    "Satellite",
    "Datalink",
    "Scenario",
    "Optimizer"
  ],
  "skipped_side_effects": [
    "google.colab drive.mount",
    "pip/apt/wget notebook lines",
    "workspace pickle load/save",
    "plt.show",
    "figure cells"
  ],
  "seed": 2025,
  "num_users": 2,
  "num_satellites": 2,
  "links_receiver_transmitter": [
    [
      1,
      2
    ],
    [
      1,
      3
    ],
    [
      1,
      4
    ],
    [
      2,
      1
    ],
    [
      2,
      3
    ],
    [
      2,
      4
    ]
  ],
  "link_types": [
    "Sidelink",
    "Downlink",
    "Downlink",
    "Sidelink",
    "Downlink",
    "Downlink"
  ],
  "symbolic_parameter_order": [
    "delta_1",
    "delta_2",
    "delta_3",
    "delta_4",
    "x_1",
    "x_2",
    "y_1",
    "y_2",
    "z_1",
    "z_2"
  ],
  "measurement_count": 6,
  "state_dimension": 10,
  "z_tfap_km": [
    4.684937810560445,
    10.458039027185569,
    12.48,
    5.364937810560445,
    8.800609733428363,
    9.476603957913984
  ],
  "h_true_km": [
    4.684937810560445,
    10.458039027185569,
    12.48,
    5.364937810560445,
    8.800609733428363,
    9.476603957913984
  ],
  "max_abs_z_minus_h_km": 0.0,
  "jacobian_shape": [
    6,
    10
  ],
  "covariance_tfap_diag": [
    1e-12,
    1e-12,
    1e-12,
    1e-12,
    1e-12,
    1e-12
  ],
  "optimizer_results": {
    "IL": {
      "status": "failed_execution",
      "error_type": "ValueError",
      "error": "('IL', 'did not improve estimate')"
    },
    "LM": {
      "status": "passed",
      "state_norm_error_km": 0.0
    },
    "EKF": {
      "status": "passed",
      "state_norm_error_km": 0.0,
      "covariance_shape": [
        10,
        10
      ]
    }
  },
  "figure_outputs_written": false,
  "output_root": "v24_notebook_regression_outputs\\executed_legacy"
}
```