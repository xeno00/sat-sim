# Figure Regression Table

- Existing static mapping records are preserved in the JSON.
- CRLB target figures have safe legacy replay outputs, but are not manuscript-ready.

| Figure | Status | Legacy replay | Manuscript ready | Reason |
|---|---|---:|---:|---|
| pos_vary_ues.pdf | static_mapped_only | False | False | Original notebook figure-generation path was not executed; only line-level measurement and tiny smoke fixtures were audited. |
| sync_vary_ues.pdf | static_mapped_only | False | False | Original notebook figure-generation path was not executed; only line-level measurement and tiny smoke fixtures were audited. |
| pos_vary_clock.pdf | static_mapped_only | False | False | Original notebook figure-generation path was not executed; only line-level measurement and tiny smoke fixtures were audited. |
| sync_vary_clock.pdf | static_mapped_only | False | False | Original notebook figure-generation path was not executed; only line-level measurement and tiny smoke fixtures were audited. |
| pos_crlb_0dB_0dB.pdf | legacy_replayed_unverified_match | True | False | Legacy notebook CRLB logic replayed safely into diagnostics, but match to existing artifact is unverified and V24 caveats remain. |
| sync_crlb_0dB_0dB.pdf | legacy_replayed_unverified_match | True | False | Legacy notebook CRLB logic replayed safely into diagnostics, but match to existing artifact is unverified and V24 caveats remain. |

- Existing static record count: 252
- Notebook executed: False
- CRLB replay report: `v24_notebook_regression_outputs\executed_legacy\crlb_replay\legacy_crlb_replay_metadata.json`
