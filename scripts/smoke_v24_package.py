"""Run a tiny non-final V24 package reproducibility diagnostic."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import numpy as np

SAT_SIM_ROOT = Path(__file__).resolve().parents[1]
if str(SAT_SIM_ROOT) not in sys.path:
    sys.path.insert(0, str(SAT_SIM_ROOT))

from jcls_sim.configs import V24ScenarioConfig, tiny_v24_reproducibility_config
from jcls_sim.estimators import (
    gauss_newton_step,
    information_form_ekf_update,
    levenberg_marquardt_step,
)
from jcls_sim.fim import fim_rank, gaussian_fim_from_jacobian, range_covariance_from_std_devs_km
from jcls_sim.gauge import expected_v24_parameter_dim, reference_satellite_node_id
from jcls_sim.io import json_ready, write_json_diagnostic
from jcls_sim.jacobian import analytic_toa_jacobian_km, toa_range_vector_from_theta_km
from jcls_sim.metrics import all_non_reference_clock_error, position_error_m
from jcls_sim.parameters import unpack_v24_theta, v24_parameter_index

DEFAULT_OUTPUT_PATH = SAT_SIM_ROOT / "v24_diagnostics" / "smoke_v24_package.json"


def _full_clock_dict_from_theta(theta: np.ndarray, config: V24ScenarioConfig) -> dict[int, float]:
    """Return a full node-clock dictionary from a V24 theta vector."""

    _, ue_clocks_km, non_reference_satellite_clocks_km = unpack_v24_theta(
        theta,
        config.num_users,
        config.num_satellites,
    )
    clocks = {node_id: float(clock) for node_id, clock in enumerate(ue_clocks_km, start=1)}
    reference_node_id = reference_satellite_node_id(config.num_users)
    clocks[reference_node_id] = 0.0
    for offset, clock in enumerate(non_reference_satellite_clocks_km, start=1):
        clocks[reference_node_id + offset] = float(clock)
    return clocks


def build_v24_smoke_diagnostics(
    config: V24ScenarioConfig | None = None,
    *,
    draw_noise: bool = True,
) -> dict[str, Any]:
    """Return deterministic non-final diagnostics for the tiny V24 package path."""

    scenario = config or tiny_v24_reproducibility_config()
    scenario.validate()
    theta = scenario.theta()
    h_theta = toa_range_vector_from_theta_km(
        theta,
        scenario.links,
        scenario.satellite_positions_km,
        scenario.num_users,
        scenario.num_satellites,
    )
    rng = np.random.default_rng(scenario.seed)
    noise = (
        rng.normal(loc=0.0, scale=scenario.range_std_devs_km, size=len(scenario.links))
        if draw_noise
        else np.zeros(len(scenario.links), dtype=float)
    )
    z = h_theta + noise
    residual = z - h_theta
    jacobian = analytic_toa_jacobian_km(
        theta,
        scenario.links,
        scenario.satellite_positions_km,
        scenario.num_users,
        scenario.num_satellites,
    )
    r_z = range_covariance_from_std_devs_km(scenario.range_std_devs_km)
    fim = gaussian_fim_from_jacobian(jacobian, scenario.range_std_devs_km)
    symmetric_fim = (fim + fim.T) / 2.0
    fim_eigenvalues = np.linalg.eigvalsh(symmetric_fim)

    gn_theta = gauss_newton_step(theta, residual, jacobian, scenario.range_std_devs_km)
    lm_theta = levenberg_marquardt_step(
        theta,
        residual,
        jacobian,
        scenario.range_std_devs_km,
        damping=1e-3,
    )
    p_pred = np.diag(np.full(theta.shape[0], 0.25, dtype=float))
    ekf_theta, ekf_cov = information_form_ekf_update(
        theta,
        p_pred,
        h_theta,
        jacobian,
        z,
        scenario.range_std_devs_km,
    )

    gn_positions_km, _, _ = unpack_v24_theta(gn_theta, scenario.num_users, scenario.num_satellites)
    ekf_positions_km, _, _ = unpack_v24_theta(ekf_theta, scenario.num_users, scenario.num_satellites)
    true_full_clocks = scenario.full_clock_dict_km()
    gn_clock_metric_km = all_non_reference_clock_error(
        true_full_clocks,
        _full_clock_dict_from_theta(gn_theta, scenario),
        scenario.num_users,
        scenario.num_satellites,
    )
    ekf_clock_metric_km = all_non_reference_clock_error(
        true_full_clocks,
        _full_clock_dict_from_theta(ekf_theta, scenario),
        scenario.num_users,
        scenario.num_satellites,
    )

    reference_node_id = reference_satellite_node_id(scenario.num_users)
    parameter_index = v24_parameter_index(scenario.num_users, scenario.num_satellites)
    payload = {
        "diagnostic_type": "non_final_v24_package_smoke",
        "schema_version": 1,
        "scenario_name": scenario.scenario_name,
        "seed": scenario.seed,
        "draw_noise": draw_noise,
        "num_users": scenario.num_users,
        "num_satellites": scenario.num_satellites,
        "reference_clock_convention": "first satellite node Nu+1 fixed at zero",
        "used_reference_satellite_node_id": reference_node_id,
        "reference_clock_column_present": f"delta_{reference_node_id}" in parameter_index,
        "parameter_dim": int(theta.shape[0]),
        "expected_parameter_dim": expected_v24_parameter_dim(
            scenario.num_users,
            scenario.num_satellites,
        ),
        "measurement_count": len(scenario.links),
        "links": [list(link) for link in scenario.links],
        "range_std_devs_km": scenario.range_std_devs_km,
        "measurement_noise_km": noise,
        "measurements_nominal_km": h_theta,
        "measurements_observed_km": z,
        "r_z_diag_km2": np.diag(r_z),
        "jacobian_shape": list(jacobian.shape),
        "fim_shape": list(fim.shape),
        "fim_rank": fim_rank(fim),
        "fim_min_eigenvalue": float(np.min(fim_eigenvalues)),
        "fim_trace": float(np.trace(fim)),
        "gn_update_norm": float(np.linalg.norm(gn_theta - theta)),
        "lm_update_norm": float(np.linalg.norm(lm_theta - theta)),
        "ekf_update_norm": float(np.linalg.norm(ekf_theta - theta)),
        "ekf_cov_trace": float(np.trace(ekf_cov)),
        "position_error_m": {
            "gn_mean": float(np.mean(position_error_m(scenario.ue_positions_km, gn_positions_km))),
            "ekf_mean": float(np.mean(position_error_m(scenario.ue_positions_km, ekf_positions_km))),
        },
        "clock_metric_km": {
            "gn_all_non_reference": gn_clock_metric_km,
            "ekf_all_non_reference": ekf_clock_metric_km,
        },
        "output_note": "diagnostic/non-final; not a manuscript figure or result sweep",
    }
    return json_ready(payload)


def write_v24_smoke_diagnostics(
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    *,
    config: V24ScenarioConfig | None = None,
    overwrite: bool = False,
    draw_noise: bool = True,
) -> Path:
    """Build and write the tiny V24 diagnostic JSON."""

    payload = build_v24_smoke_diagnostics(config=config, draw_noise=draw_noise)
    return write_json_diagnostic(payload, output_path, overwrite=overwrite)


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--seed", type=int, default=20260606)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--no-noise", action="store_true")
    return parser.parse_args()


def main() -> int:
    """Run the package smoke diagnostic from the command line."""

    args = _parse_args()
    config = tiny_v24_reproducibility_config(seed=args.seed)
    output_path = write_v24_smoke_diagnostics(
        args.output,
        config=config,
        overwrite=args.overwrite,
        draw_noise=not args.no_noise,
    )
    print(f"Wrote non-final V24 package diagnostic: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
