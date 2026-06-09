# Wave Results Provenance Audit

- Artifact status: non-final diagnostic audit.
- Notebook present: `True`.
- Exported `jcls_simulation.py` present: `False`.
- Notebook execution: `false`.
- Manuscript/source edits: `false`.

## Original Figure Logic Observed
- Network-size grid: `{'num_satellites_range': 'range(3, 15+1) found in notebook text', 'num_users_range': '[1, 3, 5, 7] found in notebook text', 'num_iterations': '15 found near generate_data_for_heatmap'}`.
- Clock-sweep PDFs referenced: `{'pos_vary_clock_pdf': False, 'sync_vary_clock_pdf': False}`.
- CRLB figures referenced: `{'pos_crlb': True, 'sync_crlb': True}`.

## Starting Settings For This Branch
- `ue_area`: UEs around MIT Stata center via package candidate geometry helper
- `leo_model`: synthetic Starlink-like visible LEO satellites
- `minimum_elevation_deg`: 30.0
- `snapshot_time_s`: 0.5
- `clock_reference`: 0.5 ppm over 15 s = 7.5 us ~= 2.25 km
- `dl`: 2.2 GHz, 20 MHz, 55 dBm, 20 dB Tx gain
- `sl`: 5.9 GHz, 40 MHz, 20 dBm, 3 dB Tx gain

## Risks
- Notebook contains TODO comments for clock drift modeling.
- Notebook contains legacy all-clock and truth-gated behavior documented by existing project reports.
- This wave runner does not execute or edit the notebook.
