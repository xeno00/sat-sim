# H Gauge / All-Clock A/B Fallback

Status: `complete_static_hypothesis`

Completed by orchestrator fallback.

| item |
| --- |
| Gauging changes rank by removing one global clock null direction from the parameter vector. |
| All-clock pseudoinverse can hide null-space behavior and may act like implicit minimum-norm regularization. |
| Removing the reference clock may remove an implicit numerical regularizer that helped legacy notebook trajectories. |
| A plausible next implementation is all-clock internal solve with explicit gauge-relative reporting, but this requires A/B tests before changing package behavior. |
