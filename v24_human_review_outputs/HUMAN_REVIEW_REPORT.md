# V24 Package-Native Human Review Report

Warning: Human-review-ready package-native output. Not manuscript-ready and not for TAES submission until human signoff and manuscript integration review.

- Branch: `codex/human-ready-figures-sprint`
- Commit: `349ceaca60302292ad2b5d0b26f0e228dbf8cc7e`
- Output root: `v24_human_review_outputs`
- Test summary: powershell -NoProfile -ExecutionPolicy Bypass -File '..\\scripts\\test_sat_sim.ps1' passed: 170 tests OK; packages installed: none
- Overall recommendation: `review_only_not_manuscript_ready`

## Commands

- `python scripts/run_v24_figures_4_7.py --config configs/v24_human_review_figures_4_7/fig4_localization_vs_satellites_human_review.json --config configs/v24_human_review_figures_4_7/fig5_synchronization_vs_satellites_human_review.json --config configs/v24_human_review_figures_4_7/fig6_localization_vs_clock_std_human_review.json --config configs/v24_human_review_figures_4_7/fig7_synchronization_vs_clock_std_human_review.json --output-root v24_human_review_outputs --overwrite`
- `python scripts/write_v24_human_review_report.py --output-root v24_human_review_outputs`

## Figure Summaries

### Fig. 4 / `fig4_localization_vs_satellites_human_review`

- PDF: `v24_human_review_outputs/fig4_localization_vs_satellites_human_review/fig4_localization_vs_satellites_human_review.pdf`
- Summary CSV: `v24_human_review_outputs/fig4_localization_vs_satellites_human_review/fig4_localization_vs_satellites_human_review_summary.csv`
- Raw CSV: `v24_human_review_outputs/fig4_localization_vs_satellites_human_review/fig4_localization_vs_satellites_human_review_raw.csv`
- Monte Carlo trials: 8
- Minimum JCLS success rate: 0.0
- Nonreportable summary rows: 4
- Manuscript consideration: False
- Note: Requires human technical review. Low JCLS success rates or nonreportable observability rows should block manuscript use.

### Fig. 5 / `fig5_synchronization_vs_satellites_human_review`

- PDF: `v24_human_review_outputs/fig5_synchronization_vs_satellites_human_review/fig5_synchronization_vs_satellites_human_review.pdf`
- Summary CSV: `v24_human_review_outputs/fig5_synchronization_vs_satellites_human_review/fig5_synchronization_vs_satellites_human_review_summary.csv`
- Raw CSV: `v24_human_review_outputs/fig5_synchronization_vs_satellites_human_review/fig5_synchronization_vs_satellites_human_review_raw.csv`
- Monte Carlo trials: 8
- Minimum JCLS success rate: 0.0
- Nonreportable summary rows: 4
- Manuscript consideration: False
- Note: Requires human technical review. Low JCLS success rates or nonreportable observability rows should block manuscript use.

### Fig. 6 / `fig6_localization_vs_clock_std_human_review`

- PDF: `v24_human_review_outputs/fig6_localization_vs_clock_std_human_review/fig6_localization_vs_clock_std_human_review.pdf`
- Summary CSV: `v24_human_review_outputs/fig6_localization_vs_clock_std_human_review/fig6_localization_vs_clock_std_human_review_summary.csv`
- Raw CSV: `v24_human_review_outputs/fig6_localization_vs_clock_std_human_review/fig6_localization_vs_clock_std_human_review_raw.csv`
- Monte Carlo trials: 8
- Minimum JCLS success rate: 0.0
- Nonreportable summary rows: 0
- Manuscript consideration: False
- Note: Requires human technical review. Low JCLS success rates or nonreportable observability rows should block manuscript use.

### Fig. 7 / `fig7_synchronization_vs_clock_std_human_review`

- PDF: `v24_human_review_outputs/fig7_synchronization_vs_clock_std_human_review/fig7_synchronization_vs_clock_std_human_review.pdf`
- Summary CSV: `v24_human_review_outputs/fig7_synchronization_vs_clock_std_human_review/fig7_synchronization_vs_clock_std_human_review_summary.csv`
- Raw CSV: `v24_human_review_outputs/fig7_synchronization_vs_clock_std_human_review/fig7_synchronization_vs_clock_std_human_review_raw.csv`
- Monte Carlo trials: 8
- Minimum JCLS success rate: 0.0
- Nonreportable summary rows: 0
- Manuscript consideration: False
- Note: Requires human technical review. Low JCLS success rates or nonreportable observability rows should block manuscript use.

## Global Blockers

- Synthetic Starlink-like geometry is used; TLE/SGP4 is not used.
- Dynamic refinement uses x=theta, F=I, Pi=I with diagonal process noise.
- Outputs are non-final, candidate-only, and not for TAES submission without human signoff.
- Any nonreportable observability rows or low JCLS success rates block manuscript use.
