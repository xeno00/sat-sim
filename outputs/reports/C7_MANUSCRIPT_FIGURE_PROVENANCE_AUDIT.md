# C7 Manuscript Figure Provenance Audit

## Executive Summary
- Source inspected: `JCLS_Simulation.ipynb` and V24 manuscript source.
- Notebook code was inspected but not executed.
- `jcls_simulation.py` was not available.
- Outputs are non-final and not manuscript-ready.

## Figure Findings
### fig4_pos_vary_ues
- Notebook cells: `[28, 29]`.
- Source function: `generate_data_for_heatmap`.
- X values: range(3, 15+1).
- Labels: `['Without cooperation', 'JCLS, Nu=3', 'JCLS, Nu=5', 'JCLS, Nu=7']`.
- Plot title/output stem: `pos_vary_ues`.
- Smoothing/fitting: gaussian_filter(map_position_errors, sigma=0.22) then power-law fit/resample.
### fig5_sync_vary_ues
- Notebook cells: `[28, 29]`.
- Source function: `generate_data_for_heatmap`.
- X values: range(3, 15+1).
- Labels: `['Without cooperation', 'JCLS, Nu=3', 'JCLS, Nu=5', 'JCLS, Nu=7']`.
- Plot title/output stem: `sync_vary_ues`.
- Smoothing/fitting: gaussian/exponential smoothing; without-cooperation row manually set to 1000 ns.
### fig6_pos_vary_clock
- Notebook cells: `[31, 32]`.
- Source function: `generate_data_for_clock_std_dev`.
- X values: np.logspace(-4, -10, 7) seconds, plotted as ns.
- Labels: `['Without cooperation', 'Coarse JCLS', 'Refined JCLS']`.
- Plot title/output stem: `pos_vary_clock`.
- Smoothing/fitting: power-law fit for IL, gaussian_filter(ys, sigma=.25) for plotted curves.
### fig7_sync_vary_clock
- Notebook cells: `[31, 32]`.
- Source function: `generate_data_for_clock_std_dev`.
- X values: np.logspace(-4, -10, 7) seconds, plotted as ns.
- Labels: `['Without cooperation', 'Coarse JCLS', 'Refined JCLS']`.
- Plot title/output stem: `sync_vary_clock`.
- Smoothing/fitting: power-law fitting noted, then gaussian_filter(ysync, sigma=.65).

## Legacy Risk Notes
- Original notebook used truth-gated MAP/EKF behavior; this recreation does not.
- Original notebook smoothed/fitted plotted values; this recreation writes raw candidate data and uses manuscript-like styling without hiding failures.
- Single-UE rows are treated only as without-cooperation baseline rows, not cooperative JCLS.
