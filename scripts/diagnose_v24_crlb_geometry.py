"""Build non-final V24 CRLB geometry diagnostics.

This script does not generate manuscript figures. It writes deterministic JSON
under ``v24_diagnostics/`` to separate fixed-parameter information addition
from growing-system satellite-count diagnostics.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Sequence

import numpy as np

SAT_SIM_ROOT = Path(__file__).resolve().parents[1]
if str(SAT_SIM_ROOT) not in sys.path:
    sys.path.insert(0, str(SAT_SIM_ROOT))

from jcls_sim.bounds import (  # noqa: E402
    average_clock_bound_from_covariance,
    average_ue_peb_from_covariance,
    covariance_from_fim,
    manuscript_crlb_reportability_from_fim,
)
from jcls_sim.configs import (  # noqa: E402
    V24ScenarioConfig,
    v24_crlb_geometry_config,
    v24_geometry_links,
)
from jcls_sim.constants import C_KM_PER_S  # noqa: E402
from jcls_sim.fim import fim_rank, gaussian_fim_from_jacobian  # noqa: E402
from jcls_sim.gauge import expected_v24_parameter_dim  # noqa: E402
from jcls_sim.io import json_ready, write_json_diagnostic  # noqa: E402
from jcls_sim.jacobian import analytic_toa_jacobian_km  # noqa: E402


DEFAULT_OUTPUT_PATH = SAT_SIM_ROOT / "v24_diagnostics" / "crlb_geometry_diagnostics.json"
DEFAULT_BASE_SEED = 20260606
DEFAULT_RANGE_STD_DEV_KM = 0.03
DEFAULT_FIXED_NUM_USERS = 3
DEFAULT_FIXED_NUM_SATELLITES = 6
DEFAULT_GROWING_NUM_USERS = 3
DEFAULT_GROWING_MAX_SATELLITES = 8
DEFAULT_GROWING_SATELLITE_COUNTS = (2, 3, 4, 5, 6, 7, 8)
DEFAULT_RANK_GRID_NUM_USERS = (2, 3, 4)
DEFAULT_RANK_GRID_NUM_SATELLITES = (2, 3, 4, 5, 6, 7, 8)
DEFAULT_RANK_GRID_PATTERNS = (
    "dl_only",
    "all_dl_minimal_sl",
    "all_dl_all_directed_sl",
)
DEFAULT_FIXED_STAGES = (9, 12, 15, 16, 17, 18, 21, 24)
PSD_TOL = 1e-9

PACKAGE_CONVENTIONS = {
    "reference_clock": "first satellite node Nu+1 fixed at zero",
    "parameter_dimension": "N_theta = 4*Nu + Ns - 1",
    "clock_order": "[UE clocks, non-reference satellite clocks]",
    "measurement_model": "range_km + transmitter_clock_km - receiver_clock_km",
    "fim": "J_h.T @ diag(sigma**-2) @ J_h",
    "bounds": "extracted from the full gauged covariance",
}

INTERPRETATION_WARNINGS = (
    "All outputs are non-final diagnostics and are not manuscript figures.",
    "Fixed-parameter monotonicity is checked only for full-rank finite-CRLB cases.",
    "Growing-Ns cases add non-reference satellite clock nuisance states and are not monotonic CRLB experiments.",
    "Rank-deficient pseudoinverse diagnostics are not manuscript-ready CRLB bounds.",
)


def _finite_bounds(*values: float) -> bool:
    """Return whether all bound values are finite and nonnegative."""

    array = np.asarray(values, dtype=float)
    return bool(array.size > 0 and np.all(np.isfinite(array)) and np.all(array >= 0.0))


def _crlb_case(
    *,
    case_id: str,
    config: V24ScenarioConfig,
    links: Sequence[tuple[int, int]],
    range_std_devs_km: np.ndarray | None = None,
    extra_fields: dict[str, Any] | None = None,
    include_links: bool = False,
) -> tuple[dict[str, Any], np.ndarray]:
    """Return one CRLB diagnostic case and its covariance."""

    config.validate()
    theta = config.theta()
    sigmas = (
        np.full(len(links), DEFAULT_RANGE_STD_DEV_KM, dtype=float)
        if range_std_devs_km is None
        else np.asarray(range_std_devs_km, dtype=float)
    )
    jacobian = analytic_toa_jacobian_km(
        theta,
        links,
        config.satellite_positions_km,
        config.num_users,
        config.num_satellites,
    )
    fim = gaussian_fim_from_jacobian(jacobian, sigmas)
    covariance, covariance_metadata = covariance_from_fim(fim)
    reportability = manuscript_crlb_reportability_from_fim(
        fim,
        config.num_users,
        config.num_satellites,
    )
    symmetric_fim = (fim + fim.T) / 2.0
    eigenvalues = np.linalg.eigvalsh(symmetric_fim)
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
    status = str(reportability["crlb_status"])
    is_manuscript_ready = (
        bool(reportability["is_manuscript_ready"])
        and status == "finite_crlb"
        and _finite_bounds(average_ue_peb_km, average_clock_bound_km)
    )
    if not _finite_bounds(average_ue_peb_km, average_clock_bound_km):
        status = "invalid"
        is_manuscript_ready = False

    payload: dict[str, Any] = {
        "case_id": case_id,
        "scenario_name": config.scenario_name,
        "seed": config.seed,
        "num_users": config.num_users,
        "num_satellites": config.num_satellites,
        "parameter_dim": int(theta.shape[0]),
        "expected_parameter_dim": expected_v24_parameter_dim(
            config.num_users,
            config.num_satellites,
        ),
        "unknown_count": int(theta.shape[0]),
        "measurement_count": len(links),
        "range_std_dev_km": float(sigmas[0]) if np.allclose(sigmas, sigmas[0]) else None,
        "range_std_dev_count": int(sigmas.shape[0]),
        "fim_shape": list(fim.shape),
        "fim_rank": fim_rank(fim),
        "fim_nullity": int(reportability["nullity"]),
        "fim_min_eigenvalue": float(np.min(eigenvalues)),
        "covariance_method": covariance_metadata["method"],
        "covariance_condition_number": covariance_metadata["condition_number"],
        "covariance_trace": float(np.trace(covariance)),
        "average_ue_peb_km": average_ue_peb_km,
        "average_clock_bound_km": average_clock_bound_km,
        "average_clock_bound_s": average_clock_bound_km / C_KM_PER_S,
        "manuscript_average_ue_peb_km": average_ue_peb_km if is_manuscript_ready else None,
        "manuscript_average_clock_bound_km": average_clock_bound_km if is_manuscript_ready else None,
        "manuscript_average_clock_bound_s": average_clock_bound_km / C_KM_PER_S if is_manuscript_ready else None,
        "manuscript_bounds_defined": is_manuscript_ready,
        "is_full_rank": bool(reportability["is_full_rank"]),
        "is_manuscript_ready": is_manuscript_ready,
        "crlb_status": status,
        "manuscript_crlb_status": reportability["manuscript_crlb_status"],
        "ue_position_subspace_estimable": reportability["ue_position_subspace_estimable"],
        "clock_subspace_estimable": reportability["clock_subspace_estimable"],
    }
    if include_links:
        payload["links"] = [list(link) for link in links]
        payload["range_std_devs_km"] = sigmas
    if extra_fields:
        payload.update(extra_fields)
    return json_ready(payload), covariance


def _fixed_pool_subset_config(
    base_config: V24ScenarioConfig,
    num_satellites: int,
    *,
    link_pattern: str,
    range_std_dev_km: float,
) -> V24ScenarioConfig:
    """Return a nested satellite-subset scenario from a larger pool."""

    links = v24_geometry_links(base_config.num_users, num_satellites, link_pattern)
    return V24ScenarioConfig(
        scenario_name=f"v24_crlb_growing_ns_{link_pattern}_nu{base_config.num_users}_ns{num_satellites}",
        num_users=base_config.num_users,
        num_satellites=int(num_satellites),
        seed=base_config.seed,
        ue_positions_km=base_config.ue_positions_km.copy(),
        satellite_positions_km=base_config.satellite_positions_km[:num_satellites].copy(),
        ue_clock_offsets_km=base_config.ue_clock_offsets_km.copy(),
        non_reference_satellite_clock_offsets_km=(
            base_config.non_reference_satellite_clock_offsets_km[: num_satellites - 1].copy()
        ),
        links=links,
        range_std_devs_km=np.full(len(links), float(range_std_dev_km), dtype=float),
    )


def build_fixed_parameter_information_addition(
    *,
    seed: int = DEFAULT_BASE_SEED,
    num_users: int = DEFAULT_FIXED_NUM_USERS,
    num_satellites: int = DEFAULT_FIXED_NUM_SATELLITES,
    range_std_dev_km: float = DEFAULT_RANGE_STD_DEV_KM,
    stage_measurement_counts: Sequence[int] = DEFAULT_FIXED_STAGES,
) -> dict[str, Any]:
    """Return fixed-parameter nested-measurement CRLB diagnostics."""

    config = v24_crlb_geometry_config(
        num_users,
        num_satellites,
        seed,
        link_pattern="all_dl_all_directed_sl",
        range_std_dev_km=range_std_dev_km,
    )
    full_pool = tuple(config.links)
    previous_full_rank_covariance: np.ndarray | None = None
    previous_full_rank_case_id: str | None = None
    cases = []
    for stage_index, raw_count in enumerate(stage_measurement_counts, start=1):
        measurement_count = min(int(raw_count), len(full_pool))
        links = full_pool[:measurement_count]
        case, covariance = _crlb_case(
            case_id=f"fixed_stage_{stage_index:02d}",
            config=config,
            links=links,
            range_std_devs_km=np.full(measurement_count, float(range_std_dev_km), dtype=float),
            extra_fields={
                "measurement_stage": stage_index,
                "fixed_parameter_dim": True,
                "full_pool_measurement_count": len(full_pool),
            },
        )
        case["monotonicity_checked"] = False
        case["monotonicity_status"] = "not_applicable"
        case["monotonicity_reason"] = "rank_deficient"
        case["monotonicity_min_reduction_eigenvalue"] = None
        case["monotonicity_trace_delta"] = None
        if case["crlb_status"] == "finite_crlb" and case["is_full_rank"]:
            if previous_full_rank_covariance is None:
                case["monotonicity_reason"] = "no_previous_full_rank_case"
            else:
                reduction = previous_full_rank_covariance - covariance
                symmetric_reduction = (reduction + reduction.T) / 2.0
                min_reduction_eigenvalue = float(np.min(np.linalg.eigvalsh(symmetric_reduction)))
                trace_delta = float(np.trace(covariance) - np.trace(previous_full_rank_covariance))
                monotonic_pass = min_reduction_eigenvalue >= -PSD_TOL and trace_delta <= PSD_TOL
                case["monotonicity_checked"] = True
                case["monotonicity_status"] = "pass" if monotonic_pass else "fail"
                case["monotonicity_reason"] = f"compared_to_{previous_full_rank_case_id}"
                case["monotonicity_min_reduction_eigenvalue"] = min_reduction_eigenvalue
                case["monotonicity_trace_delta"] = trace_delta
            previous_full_rank_covariance = covariance
            previous_full_rank_case_id = str(case["case_id"])
        cases.append(case)

    return json_ready(
        {
            "diagnostic_name": "fixed_parameter_information_addition",
            "description": "Nested measurement subsets with fixed Nu, Ns, geometry, and parameter dimension.",
            "num_users": num_users,
            "num_satellites": num_satellites,
            "parameter_dim": expected_v24_parameter_dim(num_users, num_satellites),
            "fixed_parameter_dim": True,
            "link_pattern": "all_dl_all_directed_sl",
            "stage_measurement_counts": [case["measurement_count"] for case in cases],
            "monotonicity_rule": "checked only between full-rank finite-CRLB cases",
            "cases": cases,
        }
    )


def build_growing_ns_diagnostic(
    *,
    seed: int = DEFAULT_BASE_SEED,
    num_users: int = DEFAULT_GROWING_NUM_USERS,
    max_satellites: int = DEFAULT_GROWING_MAX_SATELLITES,
    satellite_counts: Sequence[int] = DEFAULT_GROWING_SATELLITE_COUNTS,
    range_std_dev_km: float = DEFAULT_RANGE_STD_DEV_KM,
) -> dict[str, Any]:
    """Return growing-Ns diagnostics using nested satellites from a fixed pool."""

    base_config = v24_crlb_geometry_config(
        num_users,
        max_satellites,
        seed,
        link_pattern="all_dl_all_directed_sl",
        range_std_dev_km=range_std_dev_km,
    )
    cases = []
    for num_satellites in satellite_counts:
        config = _fixed_pool_subset_config(
            base_config,
            int(num_satellites),
            link_pattern="all_dl_all_directed_sl",
            range_std_dev_km=range_std_dev_km,
        )
        case, _ = _crlb_case(
            case_id=f"growing_ns_{num_satellites}",
            config=config,
            links=config.links,
            range_std_devs_km=config.range_std_devs_km,
            extra_fields={
                "this_case_changes_parameter_dimension": True,
                "rank_deficient_warning": "rank deficient; diagnostic only"
                if config.theta().shape[0] > 0
                else None,
            },
        )
        if case["is_full_rank"]:
            case["rank_deficient_warning"] = None
        cases.append(case)

    return json_ready(
        {
            "diagnostic_name": "growing_ns_nuisance_clock_context",
            "description": "Nested satellite subsets with parameter dimension changing as non-reference satellite clocks are added.",
            "num_users": num_users,
            "max_satellites": max_satellites,
            "satellite_counts": [int(value) for value in satellite_counts],
            "link_pattern": "all_dl_all_directed_sl",
            "this_sweep_changes_parameter_dimension": True,
            "monotonic_crlb_interpretation_valid": False,
            "interpretation_warning": (
                "Adding satellites also adds non-reference satellite clock nuisance states; "
                "this is not a fixed-parameter monotonic CRLB experiment."
            ),
            "cases": cases,
        }
    )


def build_rank_feasibility_grid(
    *,
    seed: int = DEFAULT_BASE_SEED,
    num_users_values: Sequence[int] = DEFAULT_RANK_GRID_NUM_USERS,
    num_satellite_values: Sequence[int] = DEFAULT_RANK_GRID_NUM_SATELLITES,
    link_patterns: Sequence[str] = DEFAULT_RANK_GRID_PATTERNS,
    range_std_dev_km: float = DEFAULT_RANGE_STD_DEV_KM,
) -> dict[str, Any]:
    """Return a small rank-feasibility grid over Nu, Ns, and link pattern."""

    cases = []
    for num_users in num_users_values:
        for num_satellites in num_satellite_values:
            for pattern in link_patterns:
                case_seed = int(seed) + 101 * int(num_users) + 1009 * int(num_satellites)
                config = v24_crlb_geometry_config(
                    int(num_users),
                    int(num_satellites),
                    case_seed,
                    link_pattern=pattern,
                    range_std_dev_km=range_std_dev_km,
                )
                case, _ = _crlb_case(
                    case_id=f"rank_grid_nu{num_users}_ns{num_satellites}_{pattern}",
                    config=config,
                    links=config.links,
                    range_std_devs_km=config.range_std_devs_km,
                    extra_fields={
                        "link_pattern": pattern,
                    },
                )
                if case["is_full_rank"]:
                    case["notes"] = "full rank under this deterministic geometry and link pattern"
                else:
                    case["notes"] = "rank deficient under this deterministic geometry and link pattern"
                cases.append(case)

    return json_ready(
        {
            "diagnostic_name": "rank_feasibility_grid",
            "description": "Small deterministic rank grid before any manuscript-style CRLB rerun.",
            "num_users_values": [int(value) for value in num_users_values],
            "num_satellite_values": [int(value) for value in num_satellite_values],
            "link_patterns": list(link_patterns),
            "cases": cases,
        }
    )


def build_crlb_geometry_diagnostics(
    *,
    base_seed: int = DEFAULT_BASE_SEED,
    range_std_dev_km: float = DEFAULT_RANGE_STD_DEV_KM,
) -> dict[str, Any]:
    """Return the complete non-final V24 CRLB geometry diagnostic payload."""

    return json_ready(
        {
            "diagnostic_type": "non_final_v24_crlb_geometry_diagnostics",
            "schema_version": 1,
            "generated_marker": "deterministic_no_timestamp",
            "base_seed": int(base_seed),
            "range_std_dev_km": float(range_std_dev_km),
            "package_conventions": PACKAGE_CONVENTIONS,
            "interpretation_warnings": list(INTERPRETATION_WARNINGS),
            "fixed_parameter_information_addition": build_fixed_parameter_information_addition(
                seed=base_seed,
                range_std_dev_km=range_std_dev_km,
            ),
            "growing_ns_diagnostic": build_growing_ns_diagnostic(
                seed=base_seed,
                range_std_dev_km=range_std_dev_km,
            ),
            "rank_feasibility_grid": build_rank_feasibility_grid(
                seed=base_seed,
                range_std_dev_km=range_std_dev_km,
            ),
            "output_note": "diagnostic/non-final; not a manuscript figure or result sweep",
        }
    )


def write_crlb_geometry_diagnostics(
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    *,
    base_seed: int = DEFAULT_BASE_SEED,
    range_std_dev_km: float = DEFAULT_RANGE_STD_DEV_KM,
    overwrite: bool = True,
) -> Path:
    """Build and write deterministic non-final CRLB geometry diagnostics."""

    payload = build_crlb_geometry_diagnostics(
        base_seed=base_seed,
        range_std_dev_km=range_std_dev_km,
    )
    return write_json_diagnostic(payload, output_path, overwrite=overwrite)


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--base-seed", type=int, default=DEFAULT_BASE_SEED)
    parser.add_argument("--range-std-dev-km", type=float, default=DEFAULT_RANGE_STD_DEV_KM)
    parser.add_argument("--no-overwrite", action="store_true")
    return parser.parse_args()


def main() -> int:
    """Run the non-final V24 CRLB geometry diagnostic from the command line."""

    args = _parse_args()
    output_path = write_crlb_geometry_diagnostics(
        args.output,
        base_seed=args.base_seed,
        range_std_dev_km=args.range_std_dev_km,
        overwrite=not args.no_overwrite,
    )
    print(f"Wrote non-final V24 CRLB geometry diagnostic: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
