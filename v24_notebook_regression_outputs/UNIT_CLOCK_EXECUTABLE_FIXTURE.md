# Unit/Clock Executable Fixture

- Meters/seconds and km/range-equivalent clock models agree after one c conversion.
- `range_std_devs_km` are treated as standard deviations; covariance is `diag(sigma**2)`.

```json
{
  "status": "verified_compatible",
  "artifact_status": "non_final_unit_clock_fixture",
  "meters_seconds_model_m": 4733.658046444653,
  "km_range_clock_model_m": 4733.658046444653,
  "absolute_difference_m": 0.0,
  "clock_sigma_seconds": 1e-06,
  "clock_sigma_km": 0.299792458,
  "round_trip_seconds": 1e-06,
  "covariance_diag_km2": [
    0.08987551787368175,
    0.359502071494727
  ],
  "expected_covariance_diag_km2": [
    0.08987551787368175,
    0.359502071494727
  ],
  "sampling_scale_km": 0.299792458,
  "sample_std_km": 0.3000373105383557,
  "sqrt_sigma_would_be_wrong_km": 0.547533065668184,
  "no_double_c_multiplication": true,
  "conclusion": "Notebook/package km range-equivalent clocks match the meters/seconds model after one c conversion; sigma inputs are standard deviations and covariance uses sigma squared."
}
```