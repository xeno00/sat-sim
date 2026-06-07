# Forensic Regression Sprint Report

Status: `complete_static_forensic_bridge`

{
  "report_type": "forensic_regression_sprint_report",
  "status": "complete_static_forensic_bridge",
  "branch": "codex/notebook-manuscript-regression-sprint",
  "commit_hash_at_generation": "b77da497201ad156db0c5c00970341a99a289f70",
  "pushed_status": "pending",
  "agents": [
    {
      "lane": "A_manuscript_system_model",
      "path": "v24_notebook_regression_outputs/subagent_reports/A_manuscript_system_model.json",
      "status": "available",
      "fallback": false
    },
    {
      "lane": "B_manuscript_algorithm",
      "path": "v24_notebook_regression_outputs/subagent_reports/B_manuscript_algorithm.json",
      "status": "orchestrator_completed_fallback",
      "fallback": false
    },
    {
      "lane": "C_manuscript_results",
      "path": "v24_notebook_regression_outputs/subagent_reports/C_manuscript_results.json",
      "status": "complete",
      "fallback": false
    },
    {
      "lane": "D_notebook_classes_models",
      "path": "v24_notebook_regression_outputs/subagent_reports/D_notebook_classes_models.json",
      "status": "orchestrator_completed_fallback",
      "fallback": false
    },
    {
      "lane": "E_notebook_optimizer",
      "path": "v24_notebook_regression_outputs/subagent_reports/E_notebook_optimizer.json",
      "status": "available",
      "fallback": false
    },
    {
      "lane": "F_notebook_figure_blocks",
      "path": "v24_notebook_regression_outputs/subagent_reports/F_notebook_figure_blocks.json",
      "status": "completed",
      "fallback": false
    },
    {
      "lane": "G_units_noise_covariance",
      "path": "v24_notebook_regression_outputs/subagent_reports/G_units_noise_covariance.json",
      "status": "orchestrator_completed_fallback",
      "fallback": false
    },
    {
      "lane": "H_gauge_all_clock",
      "path": "v24_notebook_regression_outputs/subagent_reports/H_gauge_all_clock.json",
      "status": "complete_static_hypothesis",
      "fallback": true
    },
    {
      "lane": "I_baseline_semantics",
      "path": "v24_notebook_regression_outputs/subagent_reports/I_baseline_semantics.json",
      "status": "orchestrator_completed_fallback",
      "fallback": true
    },
    {
      "lane": "L_red_team",
      "path": "v24_notebook_regression_outputs/subagent_reports/L_red_team.json",
      "status": "orchestrator_completed_fallback",
      "fallback": true
    }
  ],
  "tests_run": [],
  "ordered_link_findings": {
    "report_type": "ordered_link_convention_audit",
    "status": "complete_static_blocking_audit",
    "blocking": true,
    "conventions": [
      {
        "implementation": "manuscript",
        "row_order": "ambiguous in prose; subagent A reports transmitter-to-receiver h_{i,j}",
        "clock_sign": "uses c(delta_i-delta_j) in time-domain/meter notation per audit risk",
        "risk": "must align with code receiver/transmitter convention before final figure trust"
      },
      {
        "implementation": "package",
        "row_order": "(receiver_node_id, transmitter_node_id)",
        "clock_sign": "range + transmitter_clock - receiver_clock",
        "risk": "safe if manuscript i/j are mapped consistently; swapped rows preserve dimensions but corrupt residuals"
      },
      {
        "implementation": "notebook",
        "row_order": "Datalink constructor/order requires full manual audit; static cells contain transmitter/receiver pathloss and measurement methods",
        "clock_sign": "requires Datalink measurement static line review",
        "risk": "blocking unresolved until exact Datalink formula is cross-checked"
      }
    ],
    "tests_now": [
      "tests/test_measurements.py",
      "tests/test_jacobian.py"
    ],
    "tests_to_add": [
      "two-UE/two-satellite unique geometry and unique clocks; compare every DL/SL row to hand calculation",
      "swapping receiver/transmitter must change the measurement by 2*(delta_rx-delta_tx) for nonzero clocks",
      "Jacobian clock columns must be -1 for receiver and +1 for transmitter in package convention"
    ]
  },
  "unit_clock_findings": {
    "report_type": "unit_clock_representation_audit",
    "status": "complete_static_blocking_audit",
    "blocking": true,
    "findings": [
      "Manuscript primarily writes range/time model in meters and seconds with c multiplying clock differences.",
      "Notebook stores positions in km and converts seconds to km via 3e8/1000 in Node clock_offset_km.",
      "Package stores positions in km and clock states as range-equivalent km; plotting converts position to m and clocks to seconds/ns.",
      "Notebook covariance code contains both covariance and inverse-covariance patterns; Sigma_z naming is not consistently trustworthy."
    ],
    "questions": [
      "Verify no sqrt(clock_std_dev_km) sampling remains in active notebook figure path.",
      "Verify no double c multiplication between Datalink noise, state clocks, and plotting.",
      "Decide whether Sigma_z in old GN/LM code is covariance or precision in each cell."
    ],
    "tests_to_add": [
      "m/seconds model equals km/range-equivalent model after conversion",
      "clock std seconds -> km -> seconds round trip",
      "unique clocks detect sign inversion",
      "standard deviations are squared exactly once when forming R_z"
    ]
  },
  "gauge_findings": {
    "report_type": "gauge_ab_test_report",
    "status": "complete_static_hypothesis",
    "answers": [
      "Gauging changes rank by removing one global clock null direction from the parameter vector.",
      "All-clock pseudoinverse can hide null-space behavior and may act like implicit minimum-norm regularization.",
      "Removing the reference clock may remove an implicit numerical regularizer that helped legacy notebook trajectories.",
      "A plausible next implementation is all-clock internal solve with explicit gauge-relative reporting, but this requires A/B tests before changing package behavior."
    ],
    "ab_tests_needed": [
      "same scenario all-clock vs first-satellite-gauged FIM rank/condition/nullity",
      "same residual rows all-clock pseudoinverse vs gauged normal equations",
      "sync metric including all deltas vs excluding reference-clock gauge"
    ]
  },
  "baseline_findings": {
    "report_type": "baseline_semantics_report",
    "status": "complete_static_map",
    "baselines": [
      {
        "baseline": "Without cooperation",
        "semantics": "noncooperative TOA/downlink localization; should not estimate full cooperative network clocks",
        "invalid_regime": "single UE full JCLS clock-state estimation",
        "masking_rule": "plot as clockless/no-cooperation baseline or CRLB-free; do not report full-theta success"
      },
      {
        "baseline": "Coarse JCLS",
        "semantics": "full model with clocks after reduced/preconditioned initialization",
        "invalid_regime": "rank-deficient one-epoch full theta treated as successful estimator",
        "masking_rule": "mark nonreportable if rank deficient or nonconverged"
      },
      {
        "baseline": "Refined JCLS",
        "semantics": "soft-information/dynamic update after coarse JCLS",
        "invalid_regime": "refinement of failed local estimate reported as unconditional success",
        "masking_rule": "propagate upstream status and report covariance/information diagnostics"
      }
    ]
  },
  "figure_regression_status": "legacy notebook not executed; existing artifacts inventoried; package outputs mapped",
  "plot_gallery": "v24_notebook_regression_outputs/PLOT_GALLERY.md",
  "poor_package_native_performance_possible_causes": [
    "implementation mismatch",
    "observability/rank deficiency",
    "initialization/preconditioning mismatch",
    "geometry/noise mismatch",
    "ordered-link convention mismatch",
    "unit/covariance convention mismatch",
    "real manuscript/model issue"
  ],
  "manuscript_claims_unsafe_until_resolved": [
    "Figs. 4--7 numerical superiority claims",
    "CRLB extraction if legacy post-hoc clock deletion is used",
    "single-UE/full-JCLS interpretation"
  ],
  "artifact_grade": "diagnostic-only forensic bridge; not manuscript-grade",
  "next_steps": [
    "implement ordered-link deterministic tests if not already present",
    "implement unit/clock conversion tests",
    "design all-clock vs gauged A/B harness",
    "build safe legacy notebook execution harness only after static crosswalk review"
  ]
}
