# I Baseline Semantics Fallback

Status: `orchestrator_completed_fallback`

Completed by orchestrator fallback.

| baseline | semantics | invalid_regime | masking_rule |
| --- | --- | --- | --- |
| Without cooperation | noncooperative TOA/downlink localization; should not estimate full cooperative network clocks | single UE full JCLS clock-state estimation | plot as clockless/no-cooperation baseline or CRLB-free; do not report full-theta success |
| Coarse JCLS | full model with clocks after reduced/preconditioned initialization | rank-deficient one-epoch full theta treated as successful estimator | mark nonreportable if rank deficient or nonconverged |
| Refined JCLS | soft-information/dynamic update after coarse JCLS | refinement of failed local estimate reported as unconditional success | propagate upstream status and report covariance/information diagnostics |
