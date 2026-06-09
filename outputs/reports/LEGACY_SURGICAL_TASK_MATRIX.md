# Legacy Surgical Task Matrix

> Diagnostic only; not manuscript-ready.

| Lane | Status | Output |
|---|---|---|
| Agent A - Legacy Truth-Use Mapper | `orchestrator_fallback` | truth_use_inventory in LEGACY_SURGICAL_TRUTH_GATE_REMOVAL_REPORT.json |
| Agent B - Legacy Reproduction Agent | `orchestrator_completed` | L0 rows in outputs/legacy_surgical_truth_gate_removal/raw.csv |
| Agent C - Non-Truth LM Agent | `orchestrator_completed` | L1 rows and LM traces in raw.csv/trace.jsonl |
| Agent D - Non-Truth Covariance Agent | `orchestrator_completed` | L2 rows and MAP diagnostics in raw.csv/trace.jsonl |
| Agent E - Units/Metric Agent | `orchestrator_fallback` | units_ledger in report JSON/Markdown |
| Agent F - Red-Team Agent | `orchestrator_fallback` | safe/unsafe claims and tests |
