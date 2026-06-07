# C Manuscript Results

Assigned role: Subagent C - Manuscript Results Agent
Branch/worktree: current checkout
Files inspected: `../Work-In-Progress/SCL-NTN-TAES-2025-V24.tex` only
Files changed: `v24_notebook_regression_outputs/subagent_reports/C_manuscript_results.md`, `v24_notebook_regression_outputs/subagent_reports/C_manuscript_results.json`
Tests/checks run: none; manuscript-only extraction
Result: complete
Risks: Figure numbers are inferred from manuscript order. No code, notebook, generated output, or figure file was inspected in this C1 retry.
Recommended next action: Cross-check these manuscript assumptions against notebook/static figure-generation outputs in a separate pass.
Scope boundary encountered: Code support was not assessed because C1 requested immediate inspection only of the V24 manuscript source around Section V and captions.

## Compact Table

| Fig. | Label / figure file | Axis / sweep | Metric | Baselines / series | Assumptions and claims needing code support |
|---|---|---|---|---|---|
| 2 | `fig:pos_crlb` / `pos_crlb_0dB_0dB.pdf` | Network size; exact plotted axes not fully specified in inspected caption. | CRLB for average 3D UE localization error. | Theoretical CRLB only. | 0 dB SNR over Rician DL and SL. Claim: additional nodes improve average UE localization bound. Verify Rician DL/SL, 0 dB convention, full parameter/gauge handling, and localization-bound averaging. Lines 1199-1207, 1268. |
| 3 | `fig:sync_crlb` / `sync_crlb_0dB_0dB.pdf` | Network size; discussion distinguishes added users and added satellite links. | CRLB for average node synchronization. | Theoretical CRLB only. | 0 dB SNR over Rician DL and SL. Claims: synchronization CRLB decreases as users are added, increases with additional satellite links, and additional users enhance clock-offset estimation. Verify reference-clock/gauge handling and synchronization averaging. Lines 1210-1216, 1268. |
| 4 | `fig:pos_sats` / `pos_vary_ues.pdf` | x-axis: number of satellites `N_s`; series: different numbers of cooperating UEs. | Average 3D UE localization error after 0.5 s. | Conventional non-cooperative TOA downlink localization for single-UE/no-cooperation comparison; JCLS for cooperating UE cases. | MIT Stata stationary terrestrial UEs; Starlink-like LEO orbits; 500 m UE disk; 30 deg minimum elevation; DL 2.2 GHz, 20 MHz, 55 dBm, 20 dB gain; SL 5.9 GHz, 40 MHz, 20 dBm, 3 dB gain; TOA-CRLB ranging variance; `x=theta`, `F=I`; fixed UE and non-reference satellite clock offsets over 500 ms; `sigma_delta=1 us`; Monte Carlo noise averaging; `N_s <= 15` is upper-end availability sensitivity. Claims: sub-meter JCLS across configurations, diminishing satellite returns, sustained cooperating-UE gains, about 10 cm largest-network error. Lines 1733-1782, 1784-1799. |
| 5 | `fig:sync_sats` / `sync_vary_ues.pdf` | x-axis: number of satellites `N_s`; series: different numbers of cooperating UEs. | Average node synchronization error after 0.5 s. | Same network configurations as Fig. 4; discussion compares cooperation to non-cooperative TOA localization. | Same global Section V assumptions as Fig. 4, with fixed geometry/connectivity and Monte Carlo noise averaging. Claims: slower improvement than localization, earlier saturation, about 20 ns marginal gain from `N_u=5` to `N_u=7`, significant cooperation gain over non-cooperative TOA, limited benefit beyond moderate UE count. Lines 1801-1817. |
| 6 | `fig:pos_clocks` / `pos_vary_clock.pdf` | x-axis: clock-offset standard deviation `sigma_delta`. | Average 3D UE localization error. | Conventional TOA without network clock-offset estimation; coarse JCLS; refined JCLS after 500 ms. | Fixed network with `N_u=3` cooperating UEs and `N_s=10` satellites; UE and non-reference satellite offsets generated using swept `sigma_delta`; stationary short-interval assumptions. Claims: conventional TOA rapidly degrades, JCLS mitigates clock-offset sensitivity, refined JCLS stays low over a broad range, both JCLS stages degrade at very large `sigma_delta`, JCLS enables accurate localization where conventional TOA fails. Lines 1821-1840. |
| 7 | `fig:sync_clocks` / `sync_vary_clock.pdf` | x-axis: clock-offset standard deviation `sigma_delta`. | Average node synchronization error. | Conventional TOA-based localization; coarse JCLS; refined JCLS after 500 ms. | Same fixed network as Fig. 6; evaluated after 500 ms for each JCLS stage. Claims: synchronization error increases with `sigma_delta` for all methods, both JCLS stages consistently outperform conventional TOA, refined JCLS is lowest across entire range, tens-to-hundreds of ns clock-error reductions yield orders-of-magnitude localization improvement. Lines 1843-1845, 1892-1905. |

## Baseline Definitions

| Baseline / stage | Manuscript definition from inspected text |
|---|---|
| Conventional non-cooperative TOA localization | Uses LEO satellite downlinks and does not estimate network clock offsets; single-UE cases use this because they cannot exploit cooperation. Lines 1779, 1782, 1822. |
| Coarse JCLS | A proposed-framework stage reported in the clock-sweep figures before refined JCLS; implementation details are not defined in the inspected Section V passage. Lines 1822, 1845. |
| Refined JCLS | Refinement-stage result evaluated after 500 ms / 0.5 s; 500 ms is a fixed short-observation interval, not steady state or formal convergence time. Lines 1746-1748, 1822, 1844. |
| CRLB figures | Theoretical bound figures rather than achieved estimator baselines. Lines 1206, 1215, 1268. |

## Global Section V Assumptions

- Stationary terrestrial UEs near MIT Stata Center; not aerial-UE or UAV-specific simulations.
- UE locations are random within a 500 m radius circle.
- Minimum elevation angle is 30 deg.
- Satellite orbits correspond to the Starlink constellation.
- DL settings: 2.2 GHz, 20 MHz bandwidth, 55 dBm transmit power, 20 dB gain.
- UE/SL settings: 5.9 GHz, 40 MHz bandwidth, 20 dBm transmit power, 3 dB antenna gain.
- Ranging noise variance follows `sigma_m^2 = c^2 / (8 (pi beta)^2 gamma)`.
- Short-interval dynamic specialization uses `x^(n)=theta^(n)` and `F=I`.
- UE and non-reference satellite clock offsets are fixed over 500 ms.
- The 500 ms interval is not steady state or formal convergence time.
- The `N_s <= 15` sweep is an upper-end availability/sensitivity case, not a universal instantaneous-link-availability claim.
