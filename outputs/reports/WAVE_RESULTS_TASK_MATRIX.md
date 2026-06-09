# Wave Results Task Matrix

| Agent | Lane | Status | Expected output | Blocker | Fallback owner |
|---|---|---|---|---|---|
| Agent A | Provenance and Notebook Figure Audit | read_only_subagent_or_orchestrator | outputs/reports/WAVE_RESULTS_PROVENANCE_AUDIT.* | none | orchestrator |
| Agent B | Observability / CRLB Product | orchestrator_completed | outputs/wave_results/observability/ | none | orchestrator |
| Agent C | Empirical RMSE Product | orchestrator_completed | raw trial rows and empirical heatmap | none | orchestrator |
| Agent D | Satellite Substitution Product | orchestrator_completed | outputs/wave_results/satellite_substitution/ | none | orchestrator |
| Agent E | Clock Tolerance Product | orchestrator_pilot_completed | outputs/wave_results/clock_tolerance/ | none | orchestrator |
| Agent F | Sparse Sidelink Product | orchestrator_pilot_completed | outputs/wave_results/sparse_sidelink/ | none | orchestrator |
| Agent G | Time-to-Accuracy Product | orchestrator_surrogate_pilot_completed | outputs/wave_results/time_to_accuracy/ | none | orchestrator |
| Agent H | Literature Comparison Product | orchestrator_web_and_local_completed | outputs/reports/WAVE_LITERATURE_COMPARISON_TABLE.* | none | orchestrator |
| Agent I | Crash/Cache/Resume Product | orchestrator_completed | RUN_STATUS, ROW_STATUS, cache manifests | none | orchestrator |
| Agent J | Scientific Red Team | read_only_subagent_or_orchestrator | safe/unsafe claims in reports | none | orchestrator |

## File Ownership

| Workstream | Branch/worktree | Subagent role | Files allowed to edit | Read-only files | Stop conditions |
|---|---|---|---|---|---|
| wave-results implementation | codex/jcls-wave-results-exploration @ C:/codex-wt/jcls-wave-results-exploration | orchestrator | scripts/run_wave_results_exploration.py; tests/test_wave_results_exploration.py; outputs/wave_results/**; outputs/reports/WAVE_*; PROJECT_STATUS.md; docs/tasks/NEXT.md | JCLS_Simulation.ipynb; Work-In-Progress/**; All-Version-Archive/**; existing manuscript result files | need for notebook edits; need for manuscript edits; expensive unbounded run |
