# Migration Step: step_c5_sliding_window_map (medium)

## Executive Summary
Start from Step B residual-LM behavior and replace the legacy MAP/EKF truth-gated refinement with a small sliding-window MAP smoother using configured P0, Q, R, and objective-decrease acceptance.

- Status: `partially_degraded`
- Manuscript ready: `False`
- Localization improvements: 8 of 9
- Synchronization improvements: 7 of 9
- Fallback count: 3

## Plots
- [Localization PDF](pos_vary_ues.pdf)
- [Synchronization PDF](sync_vary_ues.pdf)
