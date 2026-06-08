# Migration Step: step_c5_sliding_window_map (tiny)

## Executive Summary
Start from Step B residual-LM behavior and replace the legacy MAP/EKF truth-gated refinement with a small sliding-window MAP smoother using configured P0, Q, R, and objective-decrease acceptance.

- Status: `partially_degraded`
- Manuscript ready: `False`
- Localization improvements: 1 of 2
- Synchronization improvements: 1 of 2
- Fallback count: 2

## Plots
- [Localization PDF](pos_vary_ues.pdf)
- [Synchronization PDF](sync_vary_ues.pdf)
