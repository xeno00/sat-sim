# GNSS Baseline Task Matrix

| agent | role | branch_or_worktree | files_allowed_to_edit | status | scope_boundary |
| --- | --- | --- | --- | --- | --- |
| Agent A | GNSS Literature Agent | read-only sidecar | none | completed_read_only_literature_scan | No manuscript or notebook edits. |
| Agent B | Baseline Taxonomy Agent | read-only sidecar | none | completed_read_only_taxonomy | Conservative fair/oracle/reference labels only. |
| Agent C | GNSS Prior Simulation Agent | read-only sidecar | none | completed_read_only_position_prior_plan | No notebook or broad sweeps. |
| Agent D | Clock Prior Simulation Agent | read-only sidecar | none | completed_read_only_clock_prior_plan | No final figure generation. |
| Agent E | Red-Team Agent | read-only sidecar | none | orchestrator_red_team_fallback | Check overclaims/comparability only. |
