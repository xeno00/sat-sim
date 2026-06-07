MODE: PLAN_ONLY

# Next Task: Decide Full Legacy Replay Versus V24-Clean Figure Replacement

## Purpose

Use the canonical graph package under `outputs/` to decide the next safe figure
provenance step. Do not edit manuscript files and do not generate manuscript
figures.

Completed diagnostic/replay artifacts:

- Corrected LOS CRLB legacy replay under `outputs/legacy_replay/crlb_los/`.
- NLOS CRLB failure report under `outputs/reports/CRLB_NLOS_REPORT.md`.
- Full legacy clock-sweep replay copied under
  `outputs/legacy_replay/clock_sweep_full/`.
- Bounded legacy-compatible network-size smoke replay under
  `outputs/legacy_replay/network_size/`.
- Canonical gallery under `outputs/gallery/`.
- Current graph status under `outputs/reports/CURRENT_GRAPH_STATUS.md`.

## Scope

Inspect:

- `outputs/OUTPUT_INDEX.md`
- `outputs/gallery/PLOT_GALLERY.md`
- `outputs/reports/CURRENT_GRAPH_STATUS.md`
- `outputs/reports/CRLB_LOS_REPLAY_REPORT.md`
- `outputs/reports/CRLB_NLOS_REPORT.md`
- `outputs/reports/LEGACY_NETWORK_SIZE_REPLAY_REPORT.md`
- `outputs/cache/CACHE_MANIFEST.md`
- `v24_notebook_regression_outputs/FIGURE_REGRESSION_TABLE.md`

Do not edit:

- `JCLS_Simulation.ipynb`
- manuscript files
- response-letter files
- bibliography files
- Work-In-Progress figure files
- PSFrag files
- generated manuscript PDFs
- generated manuscript figure PDFs/EPS/PNGs
- existing manuscript result files

## Required Analysis

1. Decide whether a full legacy network-size replay is worth running next, given
   the bounded smoke replay and runtime/caveats.
2. Decide whether NLOS CRLB needs a model-design task before any graph can be
   generated.
3. Decide whether the canonical graph package is sufficient for human visual
   review or needs more gallery/report polish.
4. Identify which existing manuscript figures are most likely to need V24-clean
   replacement rather than legacy replay provenance.
5. Propose the smallest next implementation task.

## Expected Output

Return a plan with:

- full legacy replay recommendation;
- V24-clean replacement recommendation;
- NLOS CRLB model-design recommendation;
- risk level;
- exact allowed files for the next implementation task;
- stop conditions and tests.

