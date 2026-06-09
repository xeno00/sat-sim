# Wave Results Executive Summary

- Status: non-final diagnostic package.
- Manuscript ready: `false`.

## Products
| Product | Status | Rows |
|---|---|---:|
| `observability` | `generated` | 200 |
| `satellite_substitution` | `generated` | 20 |
| `clock_tolerance` | `generated` | 18 |
| `sparse_sidelink` | `generated` | 9 |
| `time_to_accuracy` | `generated` | 5 |
| `literature_comparison` | `generated` | 6 |

## Top Three Wave-Making Findings
- FIM full-rank feasibility appears only for multi-UE cells in this pilot; minimum full-rank N_s by N_u is {2: 5, 3: 5, 4: 4, 5: 4}.
- Empirical Stage B/LM-only improves localization in 4/32 comparable pilot cells; most cells need estimator/initialization review before any accuracy claim.
- No 10 m, 1 m, 0.2 m, or 0.1 m satellite-substitution threshold was reached in the current pilot; the table correctly preserves these gaps.

## Safe Claims
- Cooperation can be evaluated as an observability/rank and satellite-substitution mechanism, not just an RMSE improvement.
- Single-UE rows are baseline-only and are excluded from cooperative JCLS claims.
- Sparse and clock-tolerance pilots identify where more runtime should be spent next.

## Unsafe Claims
- Any plot is manuscript-ready.
- Static clock-offset estimates are clock-drift estimates.
- JCLS is proven superior to unrelated Starlink or Doppler PNT literature.

## Recommendation
Continue with a full-grid observability/satellite-substitution expansion if the pilot findings survive human review.
