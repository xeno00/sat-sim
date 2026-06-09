# Integration Compliance Task Matrix

| Lane | Status | Owner | Outputs |
|---|---|---|---|
| Agent A - Branch inventory | subagent_completed | Planck plus integration coordinator | outputs/reports/BRANCH_INTEGRATION_INVENTORY.md, outputs/reports/BRANCH_INTEGRATION_INVENTORY.json |
| Agent B - Protected-file compliance | subagent_completed | Boole plus integration coordinator | scripts/check_protected_files.py |
| Agent C - Merge triage/red-team | subagent_completed | Ampere plus integration coordinator | outputs/reports/INTEGRATION_COMPLIANCE_REPORT.md, outputs/reports/INTEGRATION_COMPLIANCE_REPORT.json |
| Agent D - Integration executor | orchestrator_completed | integration coordinator | merge commit on integration branch |
| Agent E - Process-rule updater | orchestrator_completed | integration coordinator | AGENTS.md, RUN_CODEX.md, docs/tasks/README.md, docs/tasks/NEXT.md |
| Agent F - Red-team | orchestrator_completed | integration coordinator | outputs/reports/MERGE_DISCIPLINE_POLICY.md, outputs/reports/MERGE_DISCIPLINE_POLICY.json |
