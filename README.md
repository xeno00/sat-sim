# sat-sim

This repository has been rebased to a minimal legacy-compatible JCLS result
pipeline.

The exploratory package framework, diagnostic report tree, galleries, broad
runner scripts, and historical test scaffolding were removed so the repository
head is centered on one corrected legacy-derived path.

## What Remains

- `JCLS_Simulation.ipynb`: the original legacy notebook source.
- `scripts/minimal_legacy_corrected_jcls.py`: the new minimal corrected result
  pipeline.
- A small set of helper scripts retained only because the new script imports
  them at runtime:
  - `scripts/replay_legacy_clock_sweep_figures.py`
  - `scripts/replay_legacy_network_size_figures.py`
  - `scripts/run_controlled_migration_ladder.py`
  - `scripts/run_legacy_surgical_truth_gate_removal.py`
  - `scripts/run_legacy_surgical_prior_region_initialization.py`
- Minimal `jcls_sim` helpers required by those retained scripts:
  - `jcls_sim/constants.py`
  - `jcls_sim/migration.py`
- Recent non-final output from the minimal corrected run under
  `outputs/minimal_legacy_corrected/`.
- The recent minimal corrected pipeline report under `outputs/reports/`.

Everything else was intentionally pruned.

## Pipeline Policy

The retained pipeline preserves the legacy model behavior needed for comparison
with the manuscript while removing or replacing known indefensible estimator
decisions:

- no truth-gated LM acceptance;
- no truth-gated Step C acceptance;
- no truth-derived covariance;
- no truth-based fallback or reversion decisions.

Truth is allowed only for simulated prior construction and offline metric
evaluation, and those uses are recorded in metadata.

## Run Commands

List the primary standard case without execution:

```powershell
python scripts\minimal_legacy_corrected_jcls.py --list-plan --mode primary
```

Run the primary standard case:

```powershell
python scripts\minimal_legacy_corrected_jcls.py --run --mode primary --prior-radius-m 100000 --output-root outputs\minimal_legacy_corrected --force
```

List the sparse manuscript-targeted plan without execution:

```powershell
python scripts\minimal_legacy_corrected_jcls.py --list-plan --mode sparse-manuscript
```

Sparse manuscript execution is available but should be treated as a bounded
candidate-data run, not final figure generation.

By default, run outputs are stored under a timestamped run-history directory
instead of overwriting the canonical output folder. For example:

```powershell
python scripts\minimal_legacy_corrected_jcls.py --run --mode sparse-manuscript --prior-radius-m 100000 --output-root outputs\minimal_legacy_corrected
```

This writes to:

```text
outputs/minimal_legacy_corrected/sparse_manuscript/run_history/<run_id>/
```

and updates:

```text
outputs/minimal_legacy_corrected/sparse_manuscript/LATEST_RUN.json
outputs/minimal_legacy_corrected/sparse_manuscript/RUN_HISTORY.jsonl
```

Use `--run-id <name>` to choose a stable run directory. Use
`--publish-canonical` only when you intentionally want to write directly to the
canonical sparse output root.

Generate manuscript-style sparse candidate plots from an existing sparse run:

```powershell
python scripts\minimal_legacy_corrected_jcls.py --mode sparse-manuscript --output-root outputs\minimal_legacy_corrected --plot-sparse-figures
```

The plotting layer reads `LATEST_RUN.json` when available; otherwise it falls
back to the canonical sparse output root. Use `--sparse-run-root <path>` to plot
a specific stored run. For stored runs, it writes non-final Fig. 4--7
traceability plots under a short per-run figure path:

```text
outputs/minimal_legacy_corrected/figures/<run_id>/
```

The shorter figure path avoids Windows path-length failures while preserving
the data provenance link through the figure traceability JSON. Canonical sparse
outputs still use `outputs/minimal_legacy_corrected/sparse_manuscript/` only
when `--publish-canonical` is explicitly requested.

## Output Policy

Outputs from this repository are non-final unless explicitly reviewed and
approved by the human author. The current output root is:

```text
outputs/minimal_legacy_corrected/
```

The script writes CSV, JSON, and JSONL diagnostics. It does not write manuscript
figures, galleries, or root-level `v24_*` outputs.
