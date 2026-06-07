# Ordered-Link Convention Audit

Status: `complete_static_blocking_audit`

{
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
}
