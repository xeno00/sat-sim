"""Run a tiny non-final V24 full-gauged CRLB mini-sweep."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any, Sequence

import numpy as np

SAT_SIM_ROOT = Path(__file__).resolve().parents[1]
if str(SAT_SIM_ROOT) not in sys.path:
    sys.path.insert(0, str(SAT_SIM_ROOT))

from jcls_sim.bounds import (
    average_clock_bound_from_covariance,
    average_ue_peb_from_covariance,
    covariance_from_fim,
    manuscript_crlb_reportability_from_fim,
)
from jcls_sim.constants import C_KM_PER_S
from jcls_sim.configs import V24ScenarioConfig, v24_crlb_mini_sweep_config
from jcls_sim.fim import fim_rank, gaussian_fim_from_jacobian
from jcls_sim.gauge import expected_v24_parameter_dim
from jcls_sim.io import json_ready, write_json_diagnostic
from jcls_sim.jacobian import analytic_toa_jacobian_km

DEFAULT_BASE_SEED = 20260606
DEFAULT_NUM_USERS = 2
DEFAULT_SATELLITE_COUNTS = (2, 3, 4, 5, 6)
DEFAULT_RANGE_STD_DEV_KM = 0.03
DEFAULT_OUTPUT_PATH = SAT_SIM_ROOT / "v24_diagnostics" / "sweep_v24_crlb_ns.json"

LEGACY_STATIC_RISK_NOTES = (
    "Legacy CRLB notebook cells are not executed by this diagnostic.",
    "Static inspection found post-hoc position/clock FIMs formed after column deletion.",
    "This package-native path extracts localization and clock bounds from the full gauged covariance.",
)
SWEEP_INTERPRETATION_WARNING = (
    "This sweep changes parameter dimension with Ns and uses diagnostic "
    "pseudoinverse values for rank-deficient cases; it is not a manuscript CRLB curve."
)


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


def case_seed(base_seed: int, num_satellites: int) -> int:
    """Return a deterministic per-case seed for a satellite count."""

    return int(base_seed) + 1009 * int(num_satellites)


def build_v24_crlb_sweep_case(
    config: V24ScenarioConfig,
    *,
    measure_runtime: bool = False,
) -> dict[str, Any]:
    """Return one non-final full-gauged CRLB mini-sweep case."""

    start = time.perf_counter()
    config.validate()
    theta = config.theta()
    jacobian = analytic_toa_jacobian_km(
        theta,
        config.links,
        config.satellite_positions_km,
        config.num_users,
        config.num_satellites,
    )
    fim = gaussian_fim_from_jacobian(jacobian, config.range_std_devs_km)
    covariance, metadata = covariance_from_fim(fim)
    reportability = manuscript_crlb_reportability_from_fim(
        fim,
        config.num_users,
        config.num_satellites,
    )
    symmetric_fim = (fim + fim.T) / 2.0
    eigenvalues = np.linalg.eigvalsh(symmetric_fim)
    runtime_seconds = time.perf_counter() - start if measure_runtime else 0.0
    average_ue_peb_km = average_ue_peb_from_covariance(
        covariance,
        config.num_users,
        config.num_satellites,
    )
    average_clock_bound_km = average_clock_bound_from_covariance(
        covariance,
        config.num_users,
        config.num_satellites,
    )
    crlb_status, is_manuscript_ready = _crlb_status_from_bounds(
        reportability,
        average_ue_peb_km,
        average_clock_bound_km,
    )

    return json_ready(
        {
            "num_satellites": config.num_satellites,
            "seed": config.seed,
            "scenario_name": config.scenario_name,
            "parameter_dim": int(theta.shape[0]),
            "expected_parameter_dim": expected_v24_parameter_dim(
                config.num_users,
                config.num_satellites,
            ),
            "measurement_count": len(config.links),
            "unknown_count": int(theta.shape[0]),
            "range_std_devs_km": config.range_std_devs_km,
            "links": [list(link) for link in config.links],
            "fim_shape": list(fim.shape),
            "fim_rank": fim_rank(fim),
            "fim_nullity": int(reportability["nullity"]),
            "fim_min_eigenvalue": float(np.min(eigenvalues)),
            "covariance_method": metadata["method"],
            "covariance_rank": int(np.linalg.matrix_rank(covariance)),
            "covariance_condition_number": metadata["condition_number"],
            "diagnostic_average_ue_peb_km": average_ue_peb_km,
            "diagnostic_average_clock_bound_km": average_clock_bound_km,
            "average_ue_peb_km": average_ue_peb_km,
            "average_clock_bound_km": average_clock_bound_km,
            "average_clock_bound_s": average_clock_bound_km / C_KM_PER_S,
            "manuscript_average_ue_peb_km": average_ue_peb_km if is_manuscript_ready else None,
            "manuscript_average_clock_bound_km": average_clock_bound_km if is_manuscript_ready else None,
            "manuscript_average_clock_bound_s": average_clock_bound_km / C_KM_PER_S if is_manuscript_ready else None,
            "manuscript_bounds_defined": is_manuscript_ready,
            "is_full_rank": reportability["is_full_rank"],
            "is_manuscript_ready": is_manuscript_ready,
            "crlb_status": crlb_status,
            "manuscript_crlb_status": reportability["manuscript_crlb_status"],
            "ue_position_subspace_estimable": reportability["ue_position_subspace_estimable"],
            "clock_subspace_estimable": reportability["clock_subspace_estimable"],
            "average_ue_clock_bound_km": average_clock_bound_from_covariance(
                covariance,
                config.num_users,
                config.num_satellites,
                group="ue",
            ),
            "average_non_reference_satellite_clock_bound_km": average_clock_bound_from_covariance(
                covariance,
                config.num_users,
                config.num_satellites,
                group="satellite_non_reference",
            ),
            "runtime_seconds": runtime_seconds,
        }
    )


def build_v24_crlb_sweep_diagnostics(
    *,
    base_seed: int = DEFAULT_BASE_SEED,
    num_users: int = DEFAULT_NUM_USERS,
    satellite_counts: Sequence[int] = DEFAULT_SATELLITE_COUNTS,
    range_std_dev_km: float = DEFAULT_RANGE_STD_DEV_KM,
    measure_runtime: bool = False,
) -> dict[str, Any]:
    """Return deterministic non-final V24 CRLB mini-sweep diagnostics."""

    cases = []
    for num_satellites in satellite_counts:
        config = v24_crlb_mini_sweep_config(
            int(num_satellites),
            case_seed(base_seed, int(num_satellites)),
            num_users=num_users,
            range_std_dev_km=range_std_dev_km,
        )
        cases.append(build_v24_crlb_sweep_case(config, measure_runtime=measure_runtime))

    return json_ready(
        {
            "diagnostic_type": "non_final_v24_full_gauged_crlb_ns_sweep",
            "schema_version": 1,
            "base_seed": int(base_seed),
            "sweep_axis": "num_satellites",
            "num_users": int(num_users),
            "satellite_counts": [int(value) for value in satellite_counts],
            "range_std_dev_km": float(range_std_dev_km),
            "reference_clock_convention": "first satellite node Nu+1 fixed at zero",
            "cases": cases,
            "legacy_static_risk_notes": list(LEGACY_STATIC_RISK_NOTES),
            "sweep_interpretation_warning": SWEEP_INTERPRETATION_WARNING,
            "output_note": "diagnostic/non-final; not a manuscript figure or result sweep",
        }
    )


def write_v24_crlb_sweep_diagnostics(
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    *,
    base_seed: int = DEFAULT_BASE_SEED,
    satellite_counts: Sequence[int] = DEFAULT_SATELLITE_COUNTS,
    range_std_dev_km: float = DEFAULT_RANGE_STD_DEV_KM,
    overwrite: bool = False,
    measure_runtime: bool = False,
) -> Path:
    """Build and write the non-final V24 CRLB mini-sweep JSON."""

    payload = build_v24_crlb_sweep_diagnostics(
        base_seed=base_seed,
        satellite_counts=satellite_counts,
        range_std_dev_km=range_std_dev_km,
        measure_runtime=measure_runtime,
    )
    return write_json_diagnostic(payload, output_path, overwrite=overwrite)


def _parse_satellite_counts(raw_counts: str) -> tuple[int, ...]:
    """Parse a comma-separated satellite-count list."""

    counts = tuple(int(item.strip()) for item in raw_counts.split(",") if item.strip())
    if not counts:
        raise argparse.ArgumentTypeError("At least one satellite count is required.")
    return counts


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--base-seed", type=int, default=DEFAULT_BASE_SEED)
    parser.add_argument("--satellite-counts", type=_parse_satellite_counts, default=DEFAULT_SATELLITE_COUNTS)
    parser.add_argument("--range-std-dev-km", type=float, default=DEFAULT_RANGE_STD_DEV_KM)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--measure-runtime", action="store_true")
    return parser.parse_args()


def main() -> int:
    """Run the non-final V24 CRLB mini-sweep from the command line."""

    args = _parse_args()
    output_path = write_v24_crlb_sweep_diagnostics(
        args.output,
        base_seed=args.base_seed,
        satellite_counts=args.satellite_counts,
        range_std_dev_km=args.range_std_dev_km,
        overwrite=args.overwrite,
        measure_runtime=args.measure_runtime,
    )
    print(f"Wrote non-final V24 CRLB mini-sweep diagnostic: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
