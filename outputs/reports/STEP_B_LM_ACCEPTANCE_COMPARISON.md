# Step B LM Acceptance Comparison

## Executive Summary
Step B replaces LM truth-state acceptance with residual/trust-region checks while preserving the rest of the legacy-compatible pipeline.

- Overall status: `healthy`
- Healthy rows: 12
- Mild degradation rows: 0
- Major degradation rows: 0
- Failed rows: 0

| Users | Satellites | Status | Step A MAP pos [m] | Step B MAP pos [m] | Step A MAP sync [s] | Step B MAP sync [s] | LM accept/reject | Residual cost decrease |
|---:|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | 4 | `healthy` | 0.262291 | 0.262291 | 2.1421e-10 | 2.1421e-10 | 0/0 |  |
| 1 | 8 | `healthy` | 0.239284 | 0.239284 | 3.74023e-10 | 3.74023e-10 | 0/0 |  |
| 1 | 12 | `healthy` | 0.392342 | 0.392342 | 6.28841e-10 | 6.28841e-10 | 0/0 |  |
| 3 | 4 | `healthy` | 0.213194 | 0.213194 | 1.33532e-10 | 1.33519e-10 | 2/0 | 101897.34616604894 |
| 3 | 8 | `healthy` | 0.0495181 | 0.0537408 | 2.51735e-10 | 2.51568e-10 | 2/0 | 2113118.669952209 |
| 3 | 12 | `healthy` | 0.022861 | 0.022861 | 7.45477e-11 | 7.44756e-11 | 2/0 | 8521220.072154047 |
| 5 | 4 | `healthy` | 0.170267 | 0.170051 | 1.44954e-10 | 1.44945e-10 | 2/0 | 523179.4091935894 |
| 5 | 8 | `healthy` | 0.0452382 | 0.0452382 | 7.74659e-11 | 7.75421e-11 | 2/0 | 2145880.6749968845 |
| 5 | 12 | `healthy` | 0.0238885 | 0.0238885 | 5.12128e-11 | 5.10987e-11 | 2/0 | 7880544.896628986 |
| 7 | 4 | `healthy` | 0.0596186 | 0.0596186 | 7.16123e-11 | 7.1603e-11 | 2/0 | 48131.57113264637 |
| 7 | 8 | `healthy` | 0.00497022 | 0.00514344 | 9.30114e-11 | 9.33737e-11 | 2/0 | 6223301.130937129 |
| 7 | 12 | `healthy` | 0.00300181 | 0.00319732 | 1.31993e-10 | 1.32107e-10 | 2/0 | 12517286.519653067 |
