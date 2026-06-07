# Figure Regression Table

- Existing static mapping records are preserved in the JSON.
- CRLB, clock-sweep, and bounded network-size target figures have safe legacy-compatible replay outputs, but none are manuscript-ready.

| Figure | Status | Legacy replay | Manuscript ready | Reason |
|---|---|---:|---:|---|
| pos_vary_ues.pdf | legacy_network_size_smoke_replayed_unverified_match | True | False | Bounded safe legacy-compatible network-size smoke replay completed under canonical outputs; match is unverified, full notebook-size replay was not attempted, and legacy caveats remain. |
| sync_vary_ues.pdf | legacy_network_size_smoke_replayed_unverified_match | True | False | Bounded safe legacy-compatible network-size smoke replay completed under canonical outputs; match is unverified, full notebook-size replay was not attempted, and legacy caveats remain. |
| pos_vary_clock.pdf | legacy_full_replayed_unverified_match | True | False | Full legacy notebook clock-sweep logic replayed in redirected diagnostics; match is unverified and legacy caveats remain. |
| sync_vary_clock.pdf | legacy_full_replayed_unverified_match | True | False | Full legacy notebook clock-sweep logic replayed in redirected diagnostics; match is unverified and legacy caveats remain. |
| pos_crlb_0dB_0dB.pdf | legacy_replayed_unverified_match | True | False | Legacy notebook CRLB logic replayed safely into diagnostics, but match to existing artifact is unverified and V24 caveats remain. |
| sync_crlb_0dB_0dB.pdf | legacy_replayed_unverified_match | True | False | Legacy notebook CRLB logic replayed safely into diagnostics, but match to existing artifact is unverified and V24 caveats remain. |
