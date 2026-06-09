# GNSS Baseline Exploration Report

## 1. Executive summary

This branch implements non-final GPS/GNSS-style baseline taxonomy, literature context, position-prior sweeps, clock-prior sweeps, and intermittent GNSS holdover diagnostics.

All artifacts are non-final diagnostics and are not manuscript-ready.

## 2. Baseline taxonomy

| label | comparison_class | fair_comparison_to_jcls | oracle_diagnostic_reference | assumption_summary |
| --- | --- | --- | --- | --- |
| standalone_gnss_reference | external_service_reference | False | reference | Open-sky or otherwise usable GNSS access; no NTN cooperation needed. |
| degraded_gnss_reference | scenario_stress_reference | False | diagnostic_reference | Nominal, degraded 10 m, poor 100 m, and unavailable scenario levels. |
| gnss_aided_initialization | initialization_diagnostic | False | diagnostic | One-shot GNSS position prior with NTN/JCLS refinement after GNSS loss. |
| gnss_clock_aided_ntn | clock_aided_diagnostic | False | oracle_for_perfect_clock_variant | Perfect clock, 1 ns, 10 ns, 100 ns, 1 us, and unconstrained cases. |
| intermittent_gnss_update | hybrid_outage_diagnostic | False | diagnostic | GNSS update intervals 1, 5, 15, and 30 s with ppm/ppb drift scenarios. |
| gnss_correction_service_reference | high_infrastructure_reference | False | reference | RTK, PPP, DGNSS, SBAS, or commercial correction-service infrastructure. |
| leo_pnt_literature_reference | literature_context_reference | False | reference_only | Signals, batching time, reference receiver, and orbit knowledge vary by paper. |

## 3. Literature summary

| label | category | source_title | reported_or_relevant_value | comparison_caveat |
| --- | --- | --- | --- | --- |
| standalone_gnss_reference | GPS/GNSS standalone positioning performance | GPS.gov: GPS Accuracy | Smartphone open-sky example 4.9 m radius; high-quality single-frequency FAA data <=1.82 m horizontal, 95%; GPS URE <=2.0 m, 95%. | User accuracy depends on geometry, blockage, atmosphere, multipath, and receiver quality; URE is not user position accuracy. |
| standalone_gnss_reference | GPS SPS performance commitment | GPS.gov: GPS Performance | 2024 SPS metrics include <=8 m horizontal 95% global average, <=13 m vertical 95% global average, and <=30 ns time transfer 95%. | Service commitment/global metric, not a particular UE, urban, or NTN receiver result. |
| standalone_gnss_reference | GPS timing reference | GPS.gov: GPS Accuracy - timing | GPS time-transfer accuracy relative to UTC(USNO) <=30 ns, 95%, for specialized fixed time-transfer receivers. | Not a generic mobile UE clock guarantee. |
| gnss_aided_initialization | A-GNSS / 3GPP NG-RAN positioning | 3GPP TS 38.305 UE positioning in NG-RAN | NG-RAN positioning supports A-GNSS along with NR positioning methods such as DL-TDOA, DL-AoD, Multi-RTT, UL-TDOA, and UL-AoA. | Standards support and architecture, not an accuracy guarantee. |
| gnss_aided_initialization | Assisted GNSS / 3GPP LPP | 3GPP TS 37.355 LTE Positioning Protocol (LPP) | LPP covers E-UTRA and NR positioning and includes A-GNSS assistance/provide-location procedures. | Protocol support is not a standalone accuracy claim. |
| gnss_aided_initialization | OMA SUPL / assisted GNSS | OMA SUPL v2.0 enabler test specification | SUPL test cases include A-GPS/A-GNSS SET-assisted and SET-based modes. | Defines assistance architecture/test cases, not a universal accuracy number. |
| gnss_correction_service_reference | SBAS / WAAS | FAA WAAS Performance Analysis Report | FAA monitored WAAS reports provide site-level horizontal/vertical 95% performance statistics under aviation integrity modes. | Aviation augmentation infrastructure; not unaided GNSS or GNSS-denied JCLS. |
| gnss_correction_service_reference | Single-base RTK | NOAA NGS User Guidelines for Single Base Real Time GNSS Positioning | Survey-grade real-time precision often cited around 1 cm + 1 ppm horizontal and 2 cm + 1 ppm vertical at 1 sigma, when procedures and ambiguity fixing are successful. | Precision and absolute accuracy differ; requires correction infrastructure and favorable GNSS conditions. |
| gnss_correction_service_reference | Network RTK / RTN | NOAA NGS Guidelines for Real Time GNSS Networks | RTN guidelines discuss centimeter-class horizontal/vertical precision under controlled network and field procedures. | Network correction infrastructure is not comparable to GNSS-denied cooperative JCLS. |
| gnss_correction_service_reference | CORS / postprocessed differential GNSS | NOAA CORS Network | CORS supports postprocessed high-accuracy positioning workflows through fiducial reference stations. | Postprocessed survey infrastructure, not real-time standalone GNSS or JCLS. |
| gnss_correction_service_reference | RTK/PPP/differential GNSS | NovAtel: RTK vs PPP correction services | RTK, DGNSS, SBAS, and PPP are correction methods; RTK uses correction links, PPP can provide centimetre-level accuracy with global corrections. | High-infrastructure reference, not a fair GNSS-denied baseline. |
| gnss_correction_service_reference | PPP/correction products | International GNSS Service products / PPP-AR | IGS provides precise orbit and clock products; PPP-AR uses precise products and bias information. | Correction products are external infrastructure and may have latency or service constraints. |
| gnss_correction_service_reference | Real-time PPP corrections | Performance of real-time IGS satellite clocks for PPP | IGS real-time correction literature reports centimeter-class orbit and sub-nanosecond clock correction targets/behavior for PPP inputs. | Correction-stream performance is not direct user position accuracy and assumes external infrastructure. |
| leo_pnt_literature_reference | LEO-PNT / signal of opportunity survey | Receiver architectures for positioning with low earth orbit satellite signals: a survey | Survey reports examples including 7.7 m 2D Starlink with altitude aiding, 25.9 m 2D and 33.5 m 3D without external altitude over 800 s using six satellites. | Literature context only; assumptions differ from JCLS cooperative NTN. |
| leo_pnt_literature_reference | Opportunistic Starlink PNT | The First Carrier Phase Tracking and Positioning Results With Starlink LEO Satellite Signals | Reported experimental examples include 7.7 m 2D error with known altitude and tens-of-meters 2D/3D errors without external altitude over an extended batch. | Proof-of-concept experiment, not an operational PNT service or infrastructure-matched JCLS baseline. |
| leo_pnt_literature_reference | LEO observability | Observability Analysis of Opportunistic Receiver Localization with LEO Satellite Pseudorange Measurements | Analyzes observability from LEO pseudorange measurements over time and includes experimental demonstrations. | Observability context, not a general accuracy benchmark. |
| leo_pnt_literature_reference | NR-NTN positioning with GNSS comparison | LEO-based Positioning: Foundations, Signal Design, and Receiver Enhancements for 6G NTN | Discusses LEO-based NR-NTN positioning as complementary infrastructure to GNSS and potentially an alternative with enhancements. | Design-study context, not a reproduced baseline for this manuscript. |
| leo_pnt_literature_reference | NTN positioning and GNSS augmentation | NTN-based 6G Localization: Vision, Role of LEOs, and Open Problems | Identifies multi-LEO positioning and GNSS-augmented LEO positioning when insufficient GNSS satellites are visible. | Useful for framing weak/unavailable GNSS, not for direct numerical comparison. |
| leo_pnt_literature_reference | LEO-enhanced GNSS PPP | LEO enhanced GNSS precise point positioning with emphasis on model comparison | Reports LEO-augmented GNSS PPP geometry/accuracy improvements under the paper's simulation and data assumptions. | LEO-augmented GNSS, not standalone cooperative NTN JCLS. |
| intermittent_gnss_update | TCXO drift scenario support | Rakon TCXO product family | TCXO frequency stability options span roughly +/-0.05 to +/-1.5 ppm. | The sweep values are scenario assumptions, not final literature-calibrated device models. |
| intermittent_gnss_update | GNSS holdover | PMU holdover performance enhancement using double-oven controlled oscillator | Reports maintaining timing within 1 us drift for more than 1.5 hours in a GPS holdover context. | Application-specific timing holdover, not UE-grade clock-drift model. |

## 4. Implemented/modelled baselines

- `standalone_gnss_reference`: taxonomy and literature context only.
- `degraded_gnss_reference`: scenario table for nominal/degraded/poor/unavailable GNSS.
- `gnss_aided_initialization`: bounded position-prior sensitivity sweep.
- `gnss_clock_aided_ntn`: bounded clock-prior sensitivity sweep.
- `intermittent_gnss_update`: clock-drift/range-bias table and plot.
- `gnss_correction_service_reference`: taxonomy and literature context only.
- `leo_pnt_literature_reference`: literature/context table only.

## 5. What is fair to compare

The only fair comparisons are those where external timing/positioning infrastructure is explicit. Most GNSS rows are references or diagnostics, not infrastructure-matched competitors.

## 6. Oracle/reference rows

Perfect-clock GNSS-aided NTN is an oracle. Correction-service GNSS and standalone GNSS are external-service references. LEO-PNT literature rows are context references unless their signal, clock, orbit, and batching assumptions are reproduced.

## 7. Prior-sensitivity results

| stage | position_prior_level | mean_localization_rmse_m | mean_synchronization_rmse_ns | convergence_probability |
| --- | --- | --- | --- | --- |
| c7_jcls | 0.1_m | 0.010125753084719961 | 0.028257967846661583 | 1.0 |
| c7_jcls | 100_m | 0.7121847672311743 | 2.6725579736838285 | 1.0 |
| c7_jcls | 10_m | 0.33581104833858855 | 1.0023600231034437 | 1.0 |
| c7_jcls | 1_m | 0.09945796307551565 | 0.2754935305256219 | 1.0 |
| c7_jcls | no_gnss_prior | 0.7188191594118165 | 2.702266074748582 | 1.0 |
| stage_a_dl_only | 0.1_m | 0.041119543477392446 | 0.028397463203224383 | 1.0 |
| stage_a_dl_only | 100_m | 1.5749215993040402 | 5.6650372611151765 | 1.0 |
| stage_a_dl_only | 10_m | 0.4007937145798028 | 1.1815311859655668 | 1.0 |
| stage_a_dl_only | 1_m | 0.10043791757263998 | 0.27689834922535134 | 1.0 |
| stage_a_dl_only | no_gnss_prior | 1.5469383171473907 | 5.5827253367546 | 1.0 |
| step_b_jcls | 0.1_m | 0.02973106310142801 | 0.028379477580510525 | 1.0 |
| step_b_jcls | 100_m | 4.519796564076825 | 9.227508891762728 | 1.0 |
| step_b_jcls | 10_m | 0.34321649824437955 | 1.0077233747447158 | 1.0 |
| step_b_jcls | 1_m | 0.09981623581109766 | 0.27565905234238286 | 1.0 |
| step_b_jcls | no_gnss_prior | 4.523046645056467 | 9.274875457461178 | 1.0 |

## 8. Clock-prior results

| stage | clock_prior_level | mean_localization_rmse_m | mean_synchronization_rmse_ns | convergence_probability |
| --- | --- | --- | --- | --- |
| c7_jcls | 1000_ns | 0.701465441431986 | 2.63131728358184 | 1.0 |
| c7_jcls | 100_ns | 0.5138432054800649 | 1.797013288976796 | 1.0 |
| c7_jcls | 10_ns | 0.17043155747638608 | 0.4085389038346814 | 1.0 |
| c7_jcls | 1_ns | 0.0251953943545497 | 0.06259990586905732 | 1.0 |
| c7_jcls | perfect_clock_oracle | 4.170215809583356 | 0.0 | 1.0 |
| c7_jcls | unconstrained | 0.7188191594118165 | 2.702266074748582 | 1.0 |
| dl_only | 1000_ns | 1.543499145609224 | 5.643386338214306 | 1.0 |
| dl_only | 100_ns | 1.7492362254470741 | 5.74658314588244 | 1.0 |
| dl_only | 10_ns | 1.6413466570346866 | 3.3163698964778554 | 1.0 |
| dl_only | 1_ns | 0.211617722970758 | 0.5217582154002454 | 1.0 |
| dl_only | perfect_clock_oracle | 100.0 | 4.2909568352261433e-10 | 1.0 |
| dl_only | unconstrained | 1.5469383171473907 | 5.5827253367546 | 1.0 |
| step_b_jcls | 1000_ns | 4.492232573287222 | 9.075946011509291 | 1.0 |
| step_b_jcls | 100_ns | 4.157131678399089 | 7.104642740832708 | 1.0 |
| step_b_jcls | 10_ns | 2.998767699990038 | 2.7258106908802944 | 1.0 |
| step_b_jcls | 1_ns | 2.598535352740839 | 0.4801624834670481 | 1.0 |
| step_b_jcls | perfect_clock_oracle | 100.0 | 4.2909568352261433e-10 | 1.0 |
| step_b_jcls | unconstrained | 4.523046645056467 | 9.274875457461178 | 1.0 |

## 9. Intermittent GNSS results

| oscillator_label | update_interval_s | time_error_us | range_bias_equivalent_m | viability_label |
| --- | --- | --- | --- | --- |
| tcxo_0_5_ppm | 1.0 | 0.5 | 149.896229 | large_bias_jcls_clock_estimation_or_external_update_needed |
| tcxo_0_5_ppm | 5.0 | 2.5 | 749.481145 | large_bias_jcls_clock_estimation_or_external_update_needed |
| tcxo_0_5_ppm | 15.0 | 7.499999999999999 | 2248.4434349999997 | large_bias_jcls_clock_estimation_or_external_update_needed |
| tcxo_0_5_ppm | 30.0 | 14.999999999999998 | 4496.886869999999 | large_bias_jcls_clock_estimation_or_external_update_needed |
| tcxo_0_1_ppm | 1.0 | 0.09999999999999999 | 29.979245799999998 | moderate_bias_requires_clock_estimation |
| tcxo_0_1_ppm | 5.0 | 0.5 | 149.896229 | large_bias_jcls_clock_estimation_or_external_update_needed |
| tcxo_0_1_ppm | 15.0 | 1.5 | 449.688687 | large_bias_jcls_clock_estimation_or_external_update_needed |
| tcxo_0_1_ppm | 30.0 | 3.0 | 899.377374 | large_bias_jcls_clock_estimation_or_external_update_needed |
| ocxo_0_01_ppm | 1.0 | 0.01 | 2.9979245800000003 | low_holdover_bias_context |
| ocxo_0_01_ppm | 5.0 | 0.049999999999999996 | 14.989622899999999 | moderate_bias_requires_clock_estimation |
| ocxo_0_01_ppm | 15.0 | 0.15 | 44.968868699999994 | moderate_bias_requires_clock_estimation |
| ocxo_0_01_ppm | 30.0 | 0.3 | 89.93773739999999 | moderate_bias_requires_clock_estimation |
| disciplined_ocxo_0_001_ppm | 1.0 | 0.001 | 0.29979245800000004 | low_holdover_bias_context |
| disciplined_ocxo_0_001_ppm | 5.0 | 0.005 | 1.4989622900000001 | low_holdover_bias_context |
| disciplined_ocxo_0_001_ppm | 15.0 | 0.015000000000000001 | 4.496886870000001 | low_holdover_bias_context |
| disciplined_ocxo_0_001_ppm | 30.0 | 0.030000000000000002 | 8.993773740000002 | low_holdover_bias_context |

## 10. Recommended baselines for final manuscript figures

- Use degraded_gnss_reference as a scenario/reference panel only, with nominal/degraded/poor/unavailable levels marked as assumptions.
- Use gnss_aided_initialization as a prior-sensitivity diagnostic if reviewer framing needs to answer whether a brief GNSS fix removes the need for JCLS.
- Use gnss_clock_aided_ntn only as a clock-aiding/oracle diagnostic; keep perfect clock visibly labeled as oracle.
- Use intermittent_gnss_update to explain why update interval and oscillator drift can dominate range bias during GNSS outages.

## 11. Safe claims

- JCLS targets operating assumptions where continuous external GNSS PNT may be unavailable, intermittent, or used only as aiding.
- Standalone GNSS and correction-service GNSS assume external timing/positioning infrastructure that is not infrastructure-matched to JCLS.
- Perfect-clock and correction-service references are useful diagnostics or context, not fair GNSS-denied baselines.
- The 0.5 ppm over 15 s example corresponds to 7.5 microseconds and about 2.25 km range-equivalent bias.

## 12. Unsafe claims

- JCLS beats GPS/GNSS generally.
- The 10 m and 100 m degraded GNSS levels are literature values.
- RTK/PPP is a fair baseline for GNSS-denied JCLS without matching correction infrastructure.
- A GNSS-aided initialization row represents standalone JCLS performance.
- Perfect clock oracle rows represent achievable GNSS clock aid for all UEs and NTN satellites.

## 13. Next recommended action

Human review should choose at most one GNSS-aided diagnostic panel plus one taxonomy/context table before any manuscript edits.

## Artifact links

- taxonomy_csv: `outputs/gnss_baseline_exploration/gnss_baseline_taxonomy.csv`
- taxonomy_json: `outputs/gnss_baseline_exploration/gnss_baseline_taxonomy.json`
- taxonomy_md: `outputs/gnss_baseline_exploration/gnss_baseline_taxonomy.md`
- literature_json: `outputs/reports/GNSS_BASELINE_LITERATURE_TABLE.json`
- literature_md: `outputs/reports/GNSS_BASELINE_LITERATURE_TABLE.md`
- context_comparison_json: `outputs/gnss_baseline_exploration/context_comparison_table.json`
- context_comparison_md: `outputs/gnss_baseline_exploration/context_comparison_table.md`
- task_matrix_json: `outputs/reports/GNSS_BASELINE_TASK_MATRIX.json`
- task_matrix_md: `outputs/reports/GNSS_BASELINE_TASK_MATRIX.md`
- position_prior_raw_csv: `outputs/gnss_baseline_exploration/gnss_prior_sensitivity_raw.csv`
- position_prior_summary_csv: `outputs/gnss_baseline_exploration/gnss_prior_sensitivity_summary.csv`
- position_prior_json: `outputs/gnss_baseline_exploration/gnss_prior_sensitivity.json`
- clock_prior_raw_csv: `outputs/gnss_baseline_exploration/clock_prior_sensitivity_raw.csv`
- clock_prior_summary_csv: `outputs/gnss_baseline_exploration/clock_prior_sensitivity_summary.csv`
- clock_prior_json: `outputs/gnss_baseline_exploration/clock_prior_sensitivity.json`
- intermittent_csv: `outputs/gnss_baseline_exploration/intermittent_gnss_clock_drift.csv`
- intermittent_json: `outputs/gnss_baseline_exploration/intermittent_gnss_clock_drift.json`
- degraded_gnss_csv: `outputs/gnss_baseline_exploration/degraded_gnss_reference.csv`
- degraded_gnss_json: `outputs/gnss_baseline_exploration/degraded_gnss_reference.json`
- gnss_prior_sensitivity_localization_pdf: `outputs/gnss_baseline_exploration/plots/gnss_prior_sensitivity_localization.pdf`
- gnss_prior_sensitivity_synchronization_pdf: `outputs/gnss_baseline_exploration/plots/gnss_prior_sensitivity_synchronization.pdf`
- clock_prior_sensitivity_localization_pdf: `outputs/gnss_baseline_exploration/plots/clock_prior_sensitivity_localization.pdf`
- clock_prior_sensitivity_synchronization_pdf: `outputs/gnss_baseline_exploration/plots/clock_prior_sensitivity_synchronization.pdf`
- intermittent_gnss_clock_drift_bias_pdf: `outputs/gnss_baseline_exploration/plots/intermittent_gnss_clock_drift_bias.pdf`
- baseline_taxonomy_matrix_pdf: `outputs/gnss_baseline_exploration/plots/baseline_taxonomy_matrix.pdf`
