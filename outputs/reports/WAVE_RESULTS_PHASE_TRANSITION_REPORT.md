# Phase Transition Report

- Artifact status: non-final diagnostic.
- Manuscript ready: `false`.
- Raw rows: `200`.
- Summary rows: `40`.

## What Was Generated
- `outputs/wave_results/observability/raw.csv`
- `outputs/wave_results/observability/summary.csv`
- `outputs/wave_results/observability/arrays.npz`
- `outputs/wave_results/observability/metadata.json`
- `outputs/wave_results/observability/notes.md`

## What Failed
- No failed rows recorded.

## What Is Not Comparable
- Pilot and diagnostic outputs are not manuscript-ready.
- Synthetic LEO geometry is not an SGP4/TLE replay.
- Stage C is package C7 residual-covariance sync safeguard, not a final manuscript-approved dynamic estimator.

## Safe Claims
- The outputs test observability, rank, and estimator behavior under explicit non-final settings.
- Single-UE rows are marked baseline-only, not cooperative JCLS.

## Unsafe Claims
- These outputs are final manuscript figures.
- JCLS beats Starlink PNT or any field-trial method head-to-head.
- Clock drift is estimated by the static offset state.

## Recommended Next Action
Review pilot evidence, then expand only the promising products with higher Monte Carlo counts.
