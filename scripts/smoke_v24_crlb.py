"""Run a tiny non-final V24 full-gauged CRLB diagnostic."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import numpy as np

SAT_SIM_ROOT = Path(__file__).resolve().parents[1]
if str(SAT_SIM_ROOT) not in sys.path:
    sys.path.insert(0, str(SAT_SIM_ROOT))

from jcls_sim.bounds import (
    average_clock_bound_from_covariance,
    average_ue_peb_from_covariance,
    clock_std_bounds_from_covariance,
    covariance_from_fim,
    manuscript_crlb_reportability_from_fim,
    per_user_peb_from_covariance,
)
from jcls_sim.constants import C_KM_PER_S
from jcls_sim.configs import V24ScenarioConfig, tiny_v24_reproducibility_config
from jcls_sim.fim import fim_rank, gaussian_fim_from_jacobian
from jcls_sim.gauge import expected_v24_parameter_dim, reference_satellite_node_id
from jcls_sim.io import json_ready, write_json_diagnostic
from jcls_sim.jacobian import analytic_toa_jacobian_km

DEFAULT_OUTPUT_PATH = SAT_SIM_ROOT / "v24_diagnostics" / "smoke_v24_crlb.json"


def _crlb_status_from_bounds(
    reportability: dict[str, Any],
    *bound_values: float,
) -> tuple[str, bool]:
    """Return diagnostic CRLB status and manuscript-readiness flag."""

    values = np.asarray(bound_values, dtype=float)
    if values.size == 0 or np.any(~np.isfinite(values)) or np.any(values < 0.0):
        return "invalid", False
    status = str(reportability["crlb_status"])
    return status, bool(reportability["is_manuscript_ready"]) and status == "finite_crlb"


def build_v24_crlb_diagnostics(config: V24ScenarioConfig | None = None) -> dict[str, Any]:
    """Return non-final full-gauged CRLB diagnostics for the tiny V24 scenario."""

    scenario = config or tiny_v24_reproducibility_config()
    scenario.validate()
    theta = scenario.theta()
    jacobian = analytic_toa_jacobian_km(
        theta,
        scenario.links,
        scenario.satellite_positions_km,
        scenario.num_users,
        scenario.num_satellites,
    )
    fim = gaussian_fim_from_jacobian(jacobian, scenario.range_std_devs_km)
    covariance, metadata = covariance_from_fim(fim)
    reportability = manuscript_crlb_reportability_from_fim(
        fim,
        scenario.num_users,
        scenario.num_satellites,
    )
    symmetric_fim = (fim + fim.T) / 2.0
    eigenvalues = np.linalg.eigvalsh(symmetric_fim)
    reference_node_id = reference_satellite_node_id(scenario.num_users)
    average_ue_peb_km = average_ue_peb_from_covariance(
        covariance,
        scenario.num_users,
        scenario.num_satellites,
    )
    average_clock_bound_km = {
        "all_non_reference": average_clock_bound_from_covariance(
            covariance,
            scenario.num_users,
            scenario.num_satellites,
        ),
        "ue": average_clock_bound_from_covariance(
            covariance,
            scenario.num_users,
            scenario.num_satellites,
            group="ue",
        ),
        "satellite_non_reference": average_clock_bound_from_covariance(
            covariance,
            scenario.num_users,
            scenario.num_satellites,
            group="satellite_non_reference",
        ),
    }
    crlb_status, is_manuscript_ready = _crlb_status_from_bounds(
        reportability,
        average_ue_peb_km,
        average_clock_bound_km["all_non_reference"],
    )
    return json_ready(
        {
            "diagnostic_type": "non_final_v24_full_gauged_crlb_smoke",
            "schema_version": 1,
            "scenario_name": scenario.scenario_name,
            "seed": scenario.seed,
            "num_users": scenario.num_users,
            "num_satellites": scenario.num_satellites,
            "reference_clock_convention": "first satellite node Nu+1 fixed at zero",
            "used_reference_satellite_node_id": reference_node_id,
            "reference_clock_column_present": False,
            "parameter_dim": int(theta.shape[0]),
            "expected_parameter_dim": expected_v24_parameter_dim(
                scenario.num_users,
                scenario.num_satellites,
            ),
            "measurement_count": len(scenario.links),
            "unknown_count": int(theta.shape[0]),
            "fim_shape": list(fim.shape),
            "fim_rank": fim_rank(fim),
            "fim_nullity": int(reportability["nullity"]),
            "fim_min_eigenvalue": float(np.min(eigenvalues)),
            "covariance_method": metadata["method"],
            "covariance_rank": metadata["rank"],
            "covariance_condition_number": metadata["condition_number"],
            "average_ue_peb_km": average_ue_peb_km,
            "diagnostic_average_ue_peb_km": average_ue_peb_km,
            "manuscript_average_ue_peb_km": average_ue_peb_km if is_manuscript_ready else None,
            "manuscript_average_clock_bound_km": (
                average_clock_bound_km["all_non_reference"] if is_manuscript_ready else None
            ),
            "manuscript_average_clock_bound_s": (
                average_clock_bound_km["all_non_reference"] / C_KM_PER_S if is_manuscript_ready else None
            ),
            "manuscript_bounds_defined": is_manuscript_ready,
            "is_full_rank": reportability["is_full_rank"],
            "is_manuscript_ready": is_manuscript_ready,
            "crlb_status": crlb_status,
            "manuscript_crlb_status": reportability["manuscript_crlb_status"],
            "ue_position_subspace_estimable": reportability["ue_position_subspace_estimable"],
            "clock_subspace_estimable": reportability["clock_subspace_estimable"],
            "per_user_peb_km": per_user_peb_from_covariance(
                covariance,
                scenario.num_users,
                scenario.num_satellites,
            ),
            "average_clock_bound_km": average_clock_bound_km,
            "diagnostic_average_clock_bound_km": average_clock_bound_km["all_non_reference"],
            "average_clock_bound_s": {
                key: value / C_KM_PER_S
                for key, value in average_clock_bound_km.items()
            },
            "clock_std_bounds_km": {
                "all_non_reference": clock_std_bounds_from_covariance(
                    covariance,
                    scenario.num_users,
                    scenario.num_satellites,
                ),
                "ue": clock_std_bounds_from_covariance(
                    covariance,
                    scenario.num_users,
                    scenario.num_satellites,
                    group="ue",
                ),
                "satellite_non_reference": clock_std_bounds_from_covariance(
                    covariance,
                    scenario.num_users,
                    scenario.num_satellites,
                    group="satellite_non_reference",
                ),
            },
            "output_note": "diagnostic/non-final; bounds are extracted from the full gauged covariance",
        }
    )


def write_v24_crlb_diagnostics(
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    *,
    config: V24ScenarioConfig | None = None,
    overwrite: bool = False,
) -> Path:
    """Build and write the tiny full-gauged CRLB diagnostic JSON."""

    payload = build_v24_crlb_diagnostics(config=config)
    return write_json_diagnostic(payload, output_path, overwrite=overwrite)


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--seed", type=int, default=20260606)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> int:
    """Run the full-gauged CRLB smoke diagnostic from the command line."""

    args = _parse_args()
    config = tiny_v24_reproducibility_config(seed=args.seed)
    output_path = write_v24_crlb_diagnostics(args.output, config=config, overwrite=args.overwrite)
    print(f"Wrote non-final V24 CRLB diagnostic: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
