# Gauge / All-Clock A/B Report

Status: `complete_static_hypothesis`

{
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
}
