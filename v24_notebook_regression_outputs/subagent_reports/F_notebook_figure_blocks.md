# Subagent F - Notebook Figure Blocks Static Audit

Assigned role: Notebook Figure Blocks Agent  
Branch/worktree: current checkout, read-only audit except requested report outputs  
Status: completed  

## Scope

Statically inspected `JCLS_Simulation.ipynb` as notebook JSON only. The notebook was not executed. This report inventories bottom/execution blocks, clock sweeps, CRLB figures, localization/synchronization figures, plotting code, hard-coded constants/seeds, figure-to-code mapping, and reproduction risks.

Files changed:

- `v24_notebook_regression_outputs/subagent_reports/F_notebook_figure_blocks.md`
- `v24_notebook_regression_outputs/subagent_reports/F_notebook_figure_blocks.json`

## Notebook Execution State

- Notebook has 54 cells: 30 code cells and 24 markdown cells.
- Code cells have null/blank `execution_count` values, so execution order cannot be recovered reliably from notebook metadata.
- Embedded outputs exist in setup and selected result cells: cells 4, 5, 20, 21, 28, 29, 31, 32, 34, 35, 50, and 52.
- Cell 28 has an embedded `NameError: name 'np' is not defined`, while later cells contain successful-looking outputs. This indicates stale or non-linear execution state.
- No deterministic RNG seed was found. Active randomness uses global `np.random` calls.

## Plotting Code Inventory

Cell 24 defines the two main plotting helpers:

- `display_heatmap(data, title, xlabel, x_range, ylabel, y_range, zlabel="", log=False)`
  - Sets global `plt.rcParams`.
  - Uses `sns.heatmap`.
  - Saves to `title + ".pdf"` with `bbox_inches="tight"`.
  - Adds a hard-coded black box around the first user row.
- `ieee_flexible_plot(...)`
  - Sets global `plt.rcParams`, including `text.usetex=True`.
  - Ignores the `save_path` argument in the active save call.
  - Saves to `title + ".pdf"` in the current working directory.
  - Prints the axes bounding box and calls `plt.show()` before saving.

Cell 25 defines post-processing fit helpers used by plotting cells:

- `fit_and_resample_exponential`
- `fit_and_resample_linear`
- `fit_and_resample_power_law`

These helpers smooth or refit already-generated arrays before plotting, so figures are not direct raw-output plots.

## Figure-To-Code Map

| Figure output | Data cell(s) | Plot cell | Inputs plotted | Notes |
|---|---:|---:|---|---|
| `pos_vary_ues.pdf` | 28 | 29 | `map_position_errors` smoothed by `gaussian_filter`, then power-law refit | Localization vs number of satellites for `num_users_range = [1, 3, 5, 7]`; labels treat row 0 as without cooperation. |
| `sync_vary_ues.pdf` | 28 | 29 | `map_sync_errors` converted to ns, manually edited/smoothed, then exponential refit | Synchronization vs number of satellites; includes hard-coded `ys[-1][0] = ys[-1][1]` and `ys_filtered[0] = 1000`. |
| `pos_vary_clock.pdf` | 31 | 32 | `il_pos`, `lm_pos`, `map_pos`, with IL power-law fit and all series smoothed | Clock standard deviation sweep, localization metric. |
| `sync_vary_clock.pdf` | 31 | 32 | `il_sync`, `lm_sync`, `map_sync`, smoothed and converted to ns | Clock standard deviation sweep, synchronization metric; label says `Refined JCLS, $.5\,$s`. |
| `pos_crlb_0dB_0dB.pdf` | 34 | 35 | `loc` smoothed and power-law refit | CRLB localization vs number of satellites; based on post-hoc location-only FIM after deleting clock columns. |
| `sync_crlb_0dB_0dB.pdf` | 34 | 35 | `sync*1e9`; fit is computed but active plot passes raw `ys` | CRLB synchronization vs number of satellites; based on post-hoc clock-only FIM after deleting position columns. |
| `Mean JCLS UE Position Error after $.5$s (m).pdf` | 28 or workspace load | 42 | `map_position_errors` smoothed | Antiquated heatmap block under `Misc/Broken/Old`; depends on prior variables. |
| `Mean JCLS Synchronization Error after $.5$s (ns).pdf` | 28 or workspace load | 42 | `map_sync_errors` smoothed and converted to ns | Antiquated heatmap block under `Misc/Broken/Old`; depends on prior variables. |
| `Localization CRLB 0dB 0dB.pdf` | 44 | 45 | `loc*1000` heatmap over `dl` and `sl` | Marked by markdown as failed. Cell 44 also overwrites `Sigma` with `scenario.get_measurement_covariance()`. |
| `Synchronization CRLB 0dB 0dB.pdf` | 44 | 45 | `sync*1000/3e8` heatmap over `dl` and `sl` | Marked by markdown as failed. Unit conversion appears inconsistent with earlier sync conversion. |
| `pos error vary clock.pdf` | 47 | 48 | `il_pos_speed`, `lm_pos_speed`, `map_pos_speed` | User-speed sweep, but plot title/xlabel refer to clock; marked failed/old. |

## Data And Execution Blocks

Main executable blocks:

- Cell 20: preconditioning demo for `Scenario(num_users=2, num_satellites=6, clock_std_dev_seconds=1e-6)`, IL then LM.
- Cell 21: dynamic/MAP-style refinement over 25 iterations using `query_measurements(tfap=True)`.
- Cell 28: network-size sweep generator and execution for `num_satellites_range = range(3, 15+1)` and `num_users_range = [1, 3, 5, 7]`, then `save_workspace('/content/drive/MyDrive/my_workspace.pkl')`.
- Cell 31: clock-standard-deviation sweep generator and execution with `clock_std_devs = np.logspace(-4, -10, 7)`, `num_users=3`, `num_satellites=10`, `num_iterations=25`, then workspace save.
- Cell 34: 0 dB FIM/CRLB sweep over `num_satellites_range = range(3, 15+1)` and `num_users_range = [1, 3, 5, 7]`, then workspace save.
- Cell 44: failed/old DL/SL bandwidth CRLB sweep using `dl = np.linspace(20e6, 50e6, 2)` and `sl = np.linspace(1e6, 1000e6, 2)`.
- Cell 47: failed/old user-speed sweep using `user_speeds = np.linspace(0, 50, 10)`.
- Cells 50 and 52: explicit workspace save/load to `/content/drive/MyDrive/my_workspace.pkl`.
- Cell 53: TLE download helper; defined at notebook bottom but not tied to the figure blocks above.

## Clock Sweeps

Clock-standard-deviation figures are generated by cells 31 and 32.

- Sweep values: `np.logspace(-4, -10, 7)` seconds, later plotted as nanoseconds with `clock_std_devs*1e9`.
- Scenario: `num_users=3`, `num_satellites=10`.
- Iterations: `num_iterations=25` MAP updates after IL and LM.
- Initialization: `optimizer.initialize_state(..., error_range=100)`.
- Metrics:
  - localization: `calculate_average_position_error`, in meters;
  - synchronization: `calculate_average_clock_error`, in seconds, then multiplied by `1e9`.
- Failure risks:
  - no RNG seed;
  - all clocks are estimated by the legacy state;
  - metric averages every `delta_` parameter found in `symbolic_parameter_vector`;
  - embedded output shows at least one LM non-convergence warning;
  - labels contain invalid Python string escape warnings around LaTeX snippets.

## CRLB/FIM Figure Blocks

Primary CRLB cells are 34 and 35.

- Cell 34 builds `Sigma` from SNR with `snr_dl=10**(0/10)` and `snr_sl=10**(0/10)`.
- It evaluates the symbolic Jacobian at the true state, removes dependent rows by QR, then forms `FIM = J_ind.T @ inv(Sigma_ind) @ J_ind`.
- It then identifies clock and position columns from symbol names.
- Localization CRLB is computed from a location-only FIM after deleting clock columns: `J_x_no_clock = np.delete(J_ind, clock_indices, axis=1)`.
- Synchronization CRLB is computed from a clock-only FIM after deleting position columns: `J_clock = np.delete(J_ind, position_indices, axis=1)`.
- This does not use the V24 full-gauged joint FIM before bound extraction.
- Sync averaging divides by `scenario.num_users + scenario.num_satellites`, including the reference satellite clock in the legacy all-clock state.

Failed/old CRLB bandwidth cells are 44 and 45.

- Markdown labels this section `Test 4: Fisher Information DL/SL bandwidth (Failed)`.
- Cell 44 defines `build_sigma_matrix_from_bw`, but then overwrites `Sigma = scenario.get_measurement_covariance()`.
- It computes both `FIM = J_ind.T @ inv(Sigma_ind) @ J_ind` and then `FIM = J.T @ inv(Sigma) @ J`, but downstream `FIM_loc`/`FIM_clock` still use `J_ind`/`Sigma_ind`.
- Heatmap conversions differ from primary CRLB plots and should not be treated as final provenance.

## Localization/Synchronization Figure Blocks

Network-size result figures are cells 28 and 29.

- `pos_vary_ues.pdf`: uses refined/MAP position errors only, not IL/LM curves.
- `sync_vary_ues.pdf`: uses refined/MAP sync errors only, applies manual value edits and smoothing.
- "Without cooperation" is a plot label derived from the first user-count row, not a separately generated V24 no-cooperation baseline.

Clock sweep result figures are cells 31 and 32.

- `pos_vary_clock.pdf`: compares IL, LM, and MAP arrays.
- `sync_vary_clock.pdf`: compares IL, LM, and MAP sync arrays.

Old heatmap figures are cell 42.

- Depends on existing workspace variables.
- Applies additional smoothing and prints raw matrices.
- Not under the main `Results` success blocks.

## Hard-Coded Constants And Seeds

No active `np.random.seed`, `random.seed`, or `default_rng` seed was found.

Important hard-coded constants:

- Speed of light conversion: `3e8/1000`.
- UE radio defaults: `f=5.9e9`, `bw=40e6`, `p=10**(20/10)/1e3`, `g=10**(3/10)`.
- Satellite radio defaults: `f=2.2e9`, `bw=20e6`, `p=10**(55/10)/1e3`, `g=10**(20/10)`.
- Noise power: `p_n = 1e-12`.
- Movement step factors: `20/1000`, `User.speed`, `move_clock_sigma = 1e-8`.
- Scenario default clock standard deviation: `1e-6`.
- Measurement true-path covariance placeholder: `1e-12`.
- LM defaults: `damp = 1.5`, `nu = 1.9`; markdown notes `TFAP=True` wants `.9` and `2.1`.
- MAP/refinement covariance/process terms: `P/1.1`, `Q = 1e2*np.eye(len(x))`, 25 iterations.
- Sweeps:
  - satellites: `range(3, 15+1)`;
  - users: `[1, 3, 5, 7]`;
  - clock std devs: `np.logspace(-4, -10, 7)`;
  - bandwidths: `np.linspace(20e6, 50e6, 2)` and `np.linspace(1e6, 1000e6, 2)`;
  - speeds: `np.linspace(0, 50, 10)`.
- Plot smoothing/manipulation:
  - `gaussian_filter(..., sigma=0.22)`, `.25`, `.65`, `.7`, `.3`, `.75`;
  - `ys[-1][0] = ys[-1][1]`;
  - `ys_filtered[0] = np.full(..., 1000)`.

## Reproduction Commands And Failure Risks

Static audit command used:

```powershell
$nb = Get-Content -LiteralPath 'JCLS_Simulation.ipynb' -Raw | ConvertFrom-Json
```

Legacy full-notebook reproduction command, not recommended and not run:

```powershell
jupyter nbconvert --to notebook --execute .\JCLS_Simulation.ipynb --output .\v24_notebook_regression_outputs\legacy_executed_notebook.ipynb
```

Targeted legacy cell-order reproduction, not recommended and not run:

```text
Run cells 4, 5, 7, 9, 11, 13, 15, 17, 24, 25, then one data/plot pair:
- cells 28 and 29 for pos_vary_ues.pdf / sync_vary_ues.pdf
- cells 31 and 32 for pos_vary_clock.pdf / sync_vary_clock.pdf
- cells 34 and 35 for pos_crlb_0dB_0dB.pdf / sync_crlb_0dB_0dB.pdf
```

Primary reproduction risks:

- Notebook setup cell runs Colab-specific `drive.mount`, `pip`, `apt-get`, `wget`, `unzip`, `sudo`, and `texhash` commands.
- Workspace persistence is hard-coded to `/content/drive/MyDrive/my_workspace.pkl`.
- No deterministic seed is set.
- Figure files are saved in the current working directory by title string, not an explicit output root.
- `save_path` is accepted by `ieee_flexible_plot` but ignored.
- Stale outputs and blank execution counts make notebook order unreliable.
- Some figure blocks require variables produced by earlier cells or loaded from pickle workspace.
- Primary CRLB blocks use legacy all-clock/post-hoc sliced FIM logic, not V24 full-gauged bound extraction.
- Synchronization metrics include all clock symbols found in the legacy state unless downstream code changes them.
- Old/failed bottom blocks are still present and can overwrite/confuse figure provenance.

Tests/checks run: static PowerShell JSON parse and text-pattern extraction only.  
Tests not run: notebook execution, unit tests, simulations, figure generation.  
Result: completed.  
Recommended next action: treat notebook figure blocks as legacy provenance only; reproduce figures through package-native V24-gauged scripts after human approval rather than executing this notebook as a final figure source.  
Scope boundary encountered: notebook source was not edited or executed, and no figure outputs were generated.
