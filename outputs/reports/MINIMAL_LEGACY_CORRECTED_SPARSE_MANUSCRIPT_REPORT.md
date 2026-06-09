# Minimal Legacy Corrected Sparse Manuscript Report

> Sparse diagnostic only. Non-final. Not manuscript-ready. Not for submission.

## Executive Summary

- Run command: `python scripts\minimal_legacy_corrected_jcls.py --run --mode sparse-manuscript --prior-radius-m 100000 --output-root outputs\minimal_legacy_corrected --force`
- Sparse rows executed: `19` total, `15` network-size rows, `4` clock-sweep rows.
- Failures: `0`.
- Runtime: `2226.02` s.
- Step B localization: mean `0.100438` m, max `0.543245` m.
- Step C localization: mean `0.077826` m, max `0.359306` m.
- Step B synchronization: mean `3162.65` ns, max `50337.3` ns.
- Step C synchronization: mean `3162.65` ns, max `50337.3` ns.
- Step C improves localization in `11/19` rows.
- Step C improves synchronization in `12/19` rows, mostly at tiny numerical differences.

Interpretation: Step B is already sufficient for the sparse candidate data. Step C is bounded and improves mean localization, but it is not a universal row-by-row improvement over Step B.

## Sparse Grid Executed

- Network size: `N_u = [3, 5, 7]`, `N_s = [4, 8, 10, 12, 14]`, clock std `1 us`, seed `0`.
- Clock sweep: `N_u = 3`, `N_s = 10`, clock std `[1 ns, 100 ns, 1 us, 100 us]`, seed `0`.
- Prior: `prior_ball_R0`, radius `100 km`.

## Network-Size Table

|N_u|N_s|init loc m|Step A loc m|Step B loc m|Step C loc m|Step A sync ns|Step B sync ns|Step C sync ns|C improves loc|C improves sync|
|---|---|---|---|---|---|---|---|---|---|---|
|3|4|69095.2|2231.07|0.543245|0.266047|1230.53|487.978573|487.978568|true|true|
|3|8|69095.2|516.999606|0.216515|0.225454|1171.96|271.142792|271.142788|false|true|
|3|10|69095.2|566.24914|0.07445|0.036237|1253.46|491.153146|491.153144|true|true|
|3|12|69095.2|393.555723|0.071047|0.070449|1271.24|611.580038|611.580041|true|false|
|3|14|69095.2|343.365282|0.070447|0.023241|1284.7|599.234125|599.234122|true|true|
|5|4|65628.7|2323.91|0.21369|0.359306|1413.58|835.098117|835.098112|false|true|
|5|8|65628.7|642.794578|0.091776|0.062655|1307.69|542.715896|542.715892|true|true|
|5|10|65628.7|666.95071|0.046829|0.053193|1360.23|697.429113|697.429105|false|true|
|5|12|65628.7|475.892175|0.011249|0.034015|1363.36|781.114185|781.114188|false|false|
|5|14|65628.7|460.158674|0.031857|0.055692|1365.7|752.09344|752.093437|false|true|
|7|4|60226.6|2215.34|0.216929|0.080119|1331.78|680.004799|680.004804|true|false|
|7|8|60226.6|645.127738|0.006192|0.005735|1261.82|471.491575|471.491584|true|false|
|7|10|60226.6|716.601827|0.010365|0.004256|1313.58|613.568898|613.568904|true|false|
|7|12|60226.6|489.826562|0.003634|0.004768|1321.29|698.103978|698.103976|false|true|
|7|14|60226.6|450.849706|0.002295|0.005323|1327.42|679.273407|679.273404|false|true|

## Clock-Sweep Table

|clock std s|clock std label|init loc m|Step A loc m|Step B loc m|Step C loc m|Step A sync ns|Step B sync ns|Step C sync ns|C improves loc|C improves sync|
|---|---|---|---|---|---|---|---|---|---|---|
|1e-09|1 ns|69095.2|0.566481|0.07445|0.03673|1.253463|0.49186|0.491864|true|false|
|1e-07|100 ns|69095.2|56.623141|0.07445|0.038034|125.346263|49.347487|49.347487|true|false|
|1e-06|1 us|69095.2|566.24914|0.07445|0.036237|1253.46|491.153146|491.153144|true|true|
|0.0001|100 us|69095.2|57047.1|0.07445|0.081205|125346|50337.3|50337.3|false|true|

## Trend Summary

- Network-size localization trend: Step B is sub-meter in all 15 network-size rows; localization generally improves as satellites increase, with small non-monotone low-noise rows after Step B is already centimeter/millimeter-scale.
- Network-size synchronization trend: Step B and Step C synchronization are in the hundreds of ns for the 1 us clock case and are nearly identical; Step C changes sync only at numerical precision in most rows.
- Clock-sweep localization trend: Step B localization remains about 7.4 cm across 1 ns to 100 us; Step C improves 3 of 4 rows and remains below 10 cm at the 100 us stress point.
- Clock-sweep synchronization trend: Synchronization error scales with clock standard deviation: about 0.49 ns, 49 ns, 491 ns, and 50.3 us for the four sparse clock points.
- Qualitative manuscript trend match: `yes_with_caveats`. The data support preparing candidate final figure data for human review, but not direct manuscript submission yet.

## Truth-Use Ledger

- `truth_used_for_prior_construction`: `True`
- `truth_used_for_initialization`: `False`
- `truth_used_for_lm_acceptance`: `False`
- `truth_used_for_step_c_acceptance`: `False`
- `truth_used_for_covariance`: `False`
- `truth_used_for_fallback_or_reversion`: `False`
- `truth_used_for_offline_metrics`: `True`
- `truth_use_blocker`: `False`

## Units Ledger

- `clock_sigma_input_units`: `seconds`
- `internal_clock_state_units`: `legacy range-equivalent km`
- `internal_position_units`: `km`
- `localization_error_units`: `m`
- `measurement_covariance_units`: `legacy km^2/range-domain covariance`
- `measurement_units`: `km`
- `synchronization_error_units`: `ns`
- `units_status`: `units_consistent_but_legacy`

## Safe Claims

- Sparse non-final manuscript-targeted run completed all 19 rows with no recorded row failures.
- Step B residual/trust-region LM is sub-meter in every sparse row and is often centimeter-scale or better.
- Step C remains bounded and non-catastrophic in the sparse run; it improves mean localization but is not uniformly better row-by-row.
- Forbidden truth uses remain false in the output ledger: LM acceptance, Step C acceptance, covariance, and fallback/reversion.

## Unsafe Claims

- Do not claim these are final manuscript figures.
- Do not claim Step C universally improves Step B; several rows show slight localization degradation after an already excellent Step B estimate.
- Do not claim V24 reference-gauged synchronization metrics; the metric version remains legacy all-clock pending V24 reference-relative recompute.
- Do not infer Monte Carlo robustness from this seed-0 sparse run.

## Next Recommendation

Use this sparse data for human review of manuscript-like trends. If accepted, prepare final manuscript figure-generation code from the Step B backbone first, with Step C shown only if the human decides the mixed row-by-row behavior is acceptable.
