# Manuscript / Notebook Crosswalk

Status: `complete_static`

{
  "report_type": "manuscript_notebook_crosswalk",
  "status": "complete_static",
  "manuscript_to_notebook": [
    {
      "location": "Section II",
      "object": "theta",
      "role": "joint UE position and non-reference clock parameter vector",
      "expected_notebook_counterpart": "Scenario symbolic/free-symbol state vector",
      "implementation_relation": "approximately/differently"
    },
    {
      "location": "Section II",
      "object": "h_{i,j}",
      "role": "TOA/range measurement model",
      "expected_notebook_counterpart": "Datalink measurement/query functions",
      "implementation_relation": "must verify ordered-link and clock sign"
    },
    {
      "location": "Section II/FIM",
      "object": "R_z",
      "role": "measurement covariance from range-domain noise",
      "expected_notebook_counterpart": "Scenario.get_measurement_covariance / Sigma_z",
      "implementation_relation": "notebook naming sometimes uses covariance where precision appears expected"
    },
    {
      "manuscript_location": "Section IV-D Step 1",
      "mathematical_object": "GN/WNLS compact norm",
      "intended_role": "reduced/clockless coarse localization",
      "expected_notebook_counterpart": "Optimizer.il_step / async_gn_step / gn_step preconditioning",
      "relation": "conceptually direct but notebook may use reduced state tricks"
    },
    {
      "manuscript_location": "Section IV-D Step 2",
      "mathematical_object": "LM objective over theta",
      "intended_role": "full system model with clocks",
      "expected_notebook_counterpart": "Optimizer.lm_step",
      "relation": "direct in concept; all-clock/gauged and Sigma_z handling require audit"
    },
    {
      "manuscript_location": "Section IV-D Step 3",
      "mathematical_object": "SCI/SFI information-form EKF",
      "intended_role": "dynamic refinement",
      "expected_notebook_counterpart": "Optimizer.ekf_step / map filter cells",
      "relation": "approximate; notebook contains multiple covariance variants and process-noise constants"
    },
    {
      "figure": "Fig. 2",
      "claim": "localization CRLB improves with network size",
      "requires_code_support": "full gauged FIM/CRLB or justified legacy equivalent"
    },
    {
      "figure": "Fig. 3",
      "claim": "sync CRLB decreases with users and can increase with satellites",
      "requires_code_support": "clock-bound extraction from correctly gauged covariance"
    },
    {
      "figure": "Fig. 4",
      "claim": "JCLS localization improves over noncooperative TOA",
      "requires_code_support": "legacy/package algorithm regression"
    },
    {
      "figure": "Fig. 5",
      "claim": "refined JCLS sync after 0.5 s",
      "requires_code_support": "dynamic refinement and sync metric regression"
    },
    {
      "figure": "Fig. 6",
      "claim": "localization vs clock-offset std",
      "requires_code_support": "clock sweep and baseline semantics"
    },
    {
      "figure": "Fig. 7",
      "claim": "sync vs clock-offset std",
      "requires_code_support": "clock sweep and sync metric semantics"
    }
  ],
  "notebook_to_manuscript": [
    {
      "notebook_item": "Node clock_offset_km",
      "manuscript_concept": "c delta clock range bias",
      "relation": "unit-converted counterpart"
    },
    {
      "notebook_item": "Datalink",
      "manuscript_concept": "h_{i,j} TOA/range link",
      "relation": "ordered-link/sign audit required"
    },
    {
      "notebook_item": "Optimizer.lm_step",
      "manuscript_concept": "Step 2 LM JCLS",
      "relation": "conceptual counterpart"
    },
    {
      "notebook_item": "Optimizer.ekf_step",
      "manuscript_concept": "Step 3 SCI/SFI update",
      "relation": "approximate counterpart"
    },
    {
      "notebook_item": "plot/sweep cells",
      "manuscript_concept": "Figs. 2--7",
      "relation": "static figure map; reproduction not run"
    }
  ],
  "mismatches_requiring_decision": [
    "all-clock notebook vs V24 gauged theta",
    "Sigma_z covariance/precision ambiguity",
    "ordered-link i,j convention",
    "legacy smoothing/fitting vs raw Monte Carlo values"
  ],
  "subagent_reports": [
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
  ]
}
