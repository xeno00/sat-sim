# Legacy Surgical Prior-Region Initialization Report

> Diagnostic only; not manuscript-ready.

## 1. Executive summary

- Decision: `green`.
- Prior-region initialization defensible on bounded rows: `True`.
- Multi-seed sensitivity: not_run; seed 0 only.

## 2. Prior-region scientific justification

- last known UE position
- satellite beam footprint
- network registration area
- inertial/dead-reckoning propagation
- mission operating area
- coarse GNSS before outage
- map/geofence constraints
- user/service-region knowledge

## 3. Initialization model

UE initial positions are sampled from a declared coarse prior region centered on truth only for simulation construction.

- `prior_ball_R0`: uniform sample inside a 3-D ball of radius `R0`.
- `prior_gaussian_sigma0`: Gaussian sample with isotropic standard deviation `sigma0`.

## 4. Prior-radius sweep results

| Case | Pipeline | R0 [m] | Stage B [m] | Stage C [m] | Conv. prob. |
|---|---|---:|---:|---:|---:|
| `std_nu3_ns10_fullmesh_los_clock10ns_seed0` | `legacy_nontruth_lm` | 10 | 0.07445 | n/a | 1 |
| `std_nu3_ns10_fullmesh_los_clock10ns_seed0` | `legacy_surgical_nontruth` | 10 | 0.07445 | 0.05777 | 1 |
| `std_nu3_ns10_fullmesh_los_clock10ns_seed0` | `legacy_nontruth_lm` | 100 | 0.07445 | n/a | 1 |
| `std_nu3_ns10_fullmesh_los_clock10ns_seed0` | `legacy_surgical_nontruth` | 100 | 0.07445 | 0.06015 | 1 |
| `std_nu3_ns10_fullmesh_los_clock10ns_seed0` | `legacy_nontruth_lm` | 1000 | 0.07445 | n/a | 1 |
| `std_nu3_ns10_fullmesh_los_clock10ns_seed0` | `legacy_surgical_nontruth` | 1000 | 0.07445 | 0.09673 | 1 |
| `std_nu3_ns10_fullmesh_los_clock10ns_seed0` | `legacy_nontruth_lm` | 1e+04 | 0.07445 | n/a | 1 |
| `std_nu3_ns10_fullmesh_los_clock10ns_seed0` | `legacy_surgical_nontruth` | 1e+04 | 0.07445 | 0.09493 | 1 |
| `std_nu3_ns10_fullmesh_los_clock10ns_seed0` | `legacy_nontruth_lm` | 1e+05 | 0.07445 | n/a | 1 |
| `std_nu3_ns10_fullmesh_los_clock10ns_seed0` | `legacy_surgical_nontruth` | 1e+05 | 0.07445 | 0.03577 | 1 |
| `std_nu3_ns10_fullmesh_los_clock1us_seed0` | `legacy_nontruth_lm` | 10 | 0.07445 | n/a | 1 |
| `std_nu3_ns10_fullmesh_los_clock1us_seed0` | `legacy_surgical_nontruth` | 10 | 0.07445 | 0.09534 | 1 |
| `std_nu3_ns10_fullmesh_los_clock1us_seed0` | `legacy_nontruth_lm` | 100 | 0.07445 | n/a | 1 |
| `std_nu3_ns10_fullmesh_los_clock1us_seed0` | `legacy_surgical_nontruth` | 100 | 0.07445 | 0.09097 | 1 |
| `std_nu3_ns10_fullmesh_los_clock1us_seed0` | `legacy_nontruth_lm` | 1000 | 0.07445 | n/a | 1 |
| `std_nu3_ns10_fullmesh_los_clock1us_seed0` | `legacy_surgical_nontruth` | 1000 | 0.07445 | 0.09689 | 1 |
| `std_nu3_ns10_fullmesh_los_clock1us_seed0` | `legacy_nontruth_lm` | 1e+04 | 0.07445 | n/a | 1 |
| `std_nu3_ns10_fullmesh_los_clock1us_seed0` | `legacy_surgical_nontruth` | 1e+04 | 0.07445 | 0.09631 | 1 |
| `std_nu3_ns10_fullmesh_los_clock1us_seed0` | `legacy_nontruth_lm` | 1e+05 | 0.07445 | n/a | 1 |
| `std_nu3_ns10_fullmesh_los_clock1us_seed0` | `legacy_surgical_nontruth` | 1e+05 | 0.07445 | 0.03624 | 1 |
| `std_nu3_ns4_fullmesh_los_clock1us_seed0` | `legacy_nontruth_lm` | 10 | 0.5432 | n/a | 1 |
| `std_nu3_ns4_fullmesh_los_clock1us_seed0` | `legacy_surgical_nontruth` | 10 | 0.5432 | 0.871 | 1 |
| `std_nu3_ns4_fullmesh_los_clock1us_seed0` | `legacy_nontruth_lm` | 100 | 0.5432 | n/a | 1 |
| `std_nu3_ns4_fullmesh_los_clock1us_seed0` | `legacy_surgical_nontruth` | 100 | 0.5432 | 0.8614 | 1 |
| `std_nu3_ns4_fullmesh_los_clock1us_seed0` | `legacy_nontruth_lm` | 1000 | 0.5432 | n/a | 1 |
| `std_nu3_ns4_fullmesh_los_clock1us_seed0` | `legacy_surgical_nontruth` | 1000 | 0.5432 | 0.8685 | 1 |
| `std_nu3_ns4_fullmesh_los_clock1us_seed0` | `legacy_nontruth_lm` | 1e+04 | 0.5432 | n/a | 1 |
| `std_nu3_ns4_fullmesh_los_clock1us_seed0` | `legacy_surgical_nontruth` | 1e+04 | 0.5432 | 0.8709 | 1 |
| `std_nu3_ns4_fullmesh_los_clock1us_seed0` | `legacy_nontruth_lm` | 1e+05 | 0.5432 | n/a | 1 |
| `std_nu3_ns4_fullmesh_los_clock1us_seed0` | `legacy_surgical_nontruth` | 1e+05 | 0.5432 | 0.266 | 1 |

## 5. Largest prior radius retaining manuscript-like Stage B behavior

- Primary case: `100000.0` m.
- L1 primary: `100000.0` m.
- L2 primary: `100000.0` m.

## 6. Largest prior radius retaining useful Stage C behavior

- L2 primary: `100000.0` m.

## 7. Whether this removes the truth-centered initialization caveat

- Removed as an algorithm description caveat: `True`.
- Remaining truth use is explicitly labeled as prior-region simulation construction and offline metrics.

## 8. What remains unsafe

- Do not call the prior construction truth-free; truth centers the simulated prior region.
- Do not claim broad robustness because the default run is seed 0 only.
- Do not claim V24-gauged metric equivalence; these remain legacy all-clock metrics.
- Do not use L0 as deployable algorithm evidence.

## 9. Suggested manuscript wording

The nonlinear JCLS estimator requires coarse initialization. In the numerical study, each UE is initialized from a coarse prior region with radius R_0, representing context information such as last-known position, satellite beam footprint, network registration area, or mission-region knowledge. This prior is used only to initialize the iterative estimator; true state information is not used in the LM acceptance rule, covariance construction, or dynamic refinement safeguard.

## 10. Recommended next action

Promote legacy-surgical plus prior-region initialization to candidate figure generation.

## Figures

- `prior_radius_vs_stage_b_localization`: `outputs\legacy_surgical_prior_region_initialization\figures\prior_radius_vs_stage_b_localization.png`, `outputs\legacy_surgical_prior_region_initialization\figures\prior_radius_vs_stage_b_localization.pdf`
- `prior_radius_vs_stage_c_localization`: `outputs\legacy_surgical_prior_region_initialization\figures\prior_radius_vs_stage_c_localization.png`, `outputs\legacy_surgical_prior_region_initialization\figures\prior_radius_vs_stage_c_localization.pdf`
- `prior_region_truth_use_map`: `outputs\legacy_surgical_prior_region_initialization\figures\prior_region_truth_use_map.png`, `outputs\legacy_surgical_prior_region_initialization\figures\prior_region_truth_use_map.pdf`
- `prior_radius_vs_convergence_probability`: unavailable: seed_count <= 1
