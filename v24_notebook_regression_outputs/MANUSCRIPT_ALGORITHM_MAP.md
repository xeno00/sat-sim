# Manuscript Algorithm Map

Status: `complete_static`

| location | object | role | expected_notebook_counterpart | implementation_relation |
| --- | --- | --- | --- | --- |
| Section II | theta | joint UE position and non-reference clock parameter vector | Scenario symbolic/free-symbol state vector | approximately/differently |
| Section II | h_{i,j} | TOA/range measurement model | Datalink measurement/query functions | must verify ordered-link and clock sign |
| Section II/FIM | R_z | measurement covariance from range-domain noise | Scenario.get_measurement_covariance / Sigma_z | notebook naming sometimes uses covariance where precision appears expected |
|  |  |  | Optimizer.il_step / async_gn_step / gn_step preconditioning |  |
|  |  |  | Optimizer.lm_step |  |
|  |  |  | Optimizer.ekf_step / map filter cells |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
