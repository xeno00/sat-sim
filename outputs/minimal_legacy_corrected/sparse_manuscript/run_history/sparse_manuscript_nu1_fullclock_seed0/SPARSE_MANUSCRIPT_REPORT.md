# Minimal Legacy Corrected Sparse Manuscript Report

> Sparse diagnostic only. Non-final. Not manuscript-ready. Not for submission.

## Executive Summary

- Sparse rows executed: `27` total.
- N_u=1 baseline included: `True`.
- Noncooperative baseline rows: `5`.
- Cooperative network-size rows: `15`.
- Clock-sweep rows: `7`.
- Full seven-point clock sweep run: `True`.
- Fig. 4/5 use true N_u=1 without-cooperation baseline: `True`.
- Any N_u=3 Step A baseline substitution remains: `False`.
- Stage B/C skipped for N_u=1: `True`.
- Cooperative Step B localization sub-meter across sparse rows: `True`.
- Step C improves cooperative mean localization: `True`.

## Sparse Grid Executed

- Noncooperative network baseline: `N_u=1`, `N_s=[4, 8, 10, 12, 14]`, clock std `1 us`, seed `0`.
- Cooperative network size: `N_u=[3, 5, 7]`, `N_s=[4, 8, 10, 12, 14]`, clock std `1 us`, seed `0`.
- Clock sweep: `N_u=3`, `N_s=10`, clock std `['1e-10 s', '1e-09 s', '1e-08 s', '1e-07 s', '1e-06 s', '1e-05 s', '0.0001 s']`, seed `0`.
- Prior: `prior_ball_R0`, radius `100 km`.

## Noncooperative Baseline Table

|N_u|N_s|cooperation_mode|init loc m|Step A loc m|Step A sync ns|stage_b_status|stage_c_status|
|---|---|---|---:|---:|---:|---|---|
|1|4|without_cooperation|65555.8|2330.22|1446.97|not_applicable|not_applicable|
|1|8|without_cooperation|65555.8|738.562848|1279.18|not_applicable|not_applicable|
|1|10|without_cooperation|65555.8|798.072822|1356.01|not_applicable|not_applicable|
|1|12|without_cooperation|65555.8|526.96329|1360.75|not_applicable|not_applicable|
|1|14|without_cooperation|65555.8|533.178193|1364.07|not_applicable|not_applicable|

## Cooperative Network-Size Table

|N_u|N_s|cooperation_mode|init loc m|Step A loc m|Step B loc m|Step C loc m|Step A sync ns|Step B sync ns|Step C sync ns|C improves loc|C improves sync|
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|
|3|4|cooperative|69095.2|2231.07|0.543245|0.266047|1230.53|487.978573|487.978568|true|true|
|3|8|cooperative|69095.2|516.999606|0.216515|0.225454|1171.96|271.142792|271.142788|false|true|
|3|10|cooperative|69095.2|566.24914|0.07445|0.036237|1253.46|491.153146|491.153144|true|true|
|3|12|cooperative|69095.2|393.555723|0.071047|0.070449|1271.24|611.580038|611.580041|true|false|
|3|14|cooperative|69095.2|343.365282|0.070447|0.023241|1284.7|599.234125|599.234122|true|true|
|5|4|cooperative|65628.7|2323.91|0.21369|0.359306|1413.58|835.098117|835.098112|false|true|
|5|8|cooperative|65628.7|642.794578|0.091776|0.062655|1307.69|542.715896|542.715892|true|true|
|5|10|cooperative|65628.7|666.95071|0.046829|0.053193|1360.23|697.429113|697.429105|false|true|
|5|12|cooperative|65628.7|475.892175|0.011249|0.034015|1363.36|781.114185|781.114188|false|false|
|5|14|cooperative|65628.7|460.158674|0.031857|0.055692|1365.7|752.09344|752.093437|false|true|
|7|4|cooperative|60226.6|2215.34|0.216929|0.080119|1331.78|680.004799|680.004804|true|false|
|7|8|cooperative|60226.6|645.127738|0.006192|0.005735|1261.82|471.491575|471.491584|true|false|
|7|10|cooperative|60226.6|716.601827|0.010365|0.004256|1313.58|613.568898|613.568904|true|false|
|7|12|cooperative|60226.6|489.826562|0.003634|0.004768|1321.29|698.103978|698.103976|false|true|
|7|14|cooperative|60226.6|450.849706|0.002295|0.005323|1327.42|679.273407|679.273404|false|true|

## Clock-Sweep Table

|clock std s|clock std label|init loc m|Step A loc m|Step B loc m|Step C loc m|Step A sync ns|Step B sync ns|Step C sync ns|C improves loc|C improves sync|
|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|
|1e-10|0.1 ns|69095.2|0.05688|0.07445|0.033858|0.125346|0.087276|0.053742|true|true|
|1e-09|1 ns|69095.2|0.566481|0.07445|0.03673|1.253463|0.49186|0.491864|true|false|
|1e-08|10 ns|69095.2|5.662523|0.07445|0.035771|12.534626|4.923195|4.923201|true|false|
|1e-07|100 ns|69095.2|56.623141|0.07445|0.038034|125.346263|49.347487|49.347487|true|false|
|1e-06|1000 ns|69095.2|566.24914|0.07445|0.036237|1253.46|491.153146|491.153144|true|true|
|1e-05|10000 ns|69095.2|5664.67|0.07445|0.036758|12534.6|4935.13|4935.13|true|false|
|0.0001|100000 ns|69095.2|57047.1|0.07445|0.081205|125346|50337.3|50337.3|false|true|

## Trend Summary

- Network-size localization trend: cooperative Step B remains sub-meter across the sparse rows; Step C remains bounded and improves the cooperative mean localization.
- Network-size synchronization trend: cooperative synchronization remains in the hundreds of ns for the 1 us clock case, with Step C changes mostly at numerical precision.
- Clock-sweep localization trend: Step A degrades as the clock standard deviation grows, while Step B/C remain low across the sparse clock points.
- Clock-sweep synchronization trend: synchronization error scales with the clock standard deviation, as expected under the legacy all-clock metric.
- Qualitative manuscript trend match: `yes_with_caveats`.

## Truth-Use Ledger

- `truth_used_for_prior_construction`: `True`
- `truth_used_for_initialization`: `False`
- `truth_used_for_lm_acceptance`: `False`
- `truth_used_for_step_c_acceptance`: `False`
- `truth_used_for_covariance`: `False`
- `truth_used_for_fallback_or_reversion`: `False`
- `truth_used_for_offline_metrics`: `True`

## Units Ledger

- `internal_position_units`: `km`
- `internal_clock_state_units`: `legacy range-equivalent km`
- `measurement_units`: `km`
- `measurement_covariance_units`: `legacy km^2/range-domain covariance`
- `localization_error_units`: `m`
- `synchronization_error_units`: `ns`
- `clock_sigma_input_units`: `seconds`
- `units_status`: `units_consistent_but_legacy`

## Safe Claims

- True N_u=1 noncooperative baseline rows are present for Fig. 4/5 traceability.
- Stage B and Stage C are skipped, not failed, for N_u=1.
- Cooperative Step B localization remains sub-meter across the sparse network-size rows.
- Forbidden truth uses remain false in the metadata ledger.

## Unsafe Claims

- Do not treat these sparse plots as final manuscript figures.
- Do not claim Monte Carlo robustness from this seed-0 sparse run.
- Do not claim V24 reference-relative synchronization metrics; the metric remains legacy all-clock.
- Do not claim Step C universally improves Step B row-by-row.
