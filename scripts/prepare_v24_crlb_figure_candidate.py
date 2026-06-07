"""Prepare non-final V24 CRLB figure-candidate data.

This script writes compact JSON data for human review. It does not generate
figures, edit manuscript files, or write to manuscript figure directories.
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

SAT_SIM_ROOT = Path(__file__).resolve().parents[1]
if str(SAT_SIM_ROOT) not in sys.path:
    sys.path.insert(0, str(SAT_SIM_ROOT))

from jcls_sim.io import json_ready, write_json_diagnostic  # noqa: E402
from scripts.diagnose_v24_crlb_geometry import (  # noqa: E402
    build_crlb_geometry_diagnostics,
)
from scripts.diagnose_v24_manuscript_crlb_candidate import (  # noqa: E402
    build_manuscript_crlb_candidate,
)


DEFAULT_OUTPUT_PATH = SAT_SIM_ROOT / "v24_diagnostics" / "crlb_figure_candidate_data.json"
DEFAULT_BASE_SEED = 20260606
DEFAULT_RANGE_STD_DEV_KM = 0.03

FIGURE_CANDIDATE_POLICY = (
    "This JSON is non-final figure-candidate data. It must not be used as a "
    "manuscript figure until human review approves the concept and any final "
    "figure-generation workflow."
)


def _sorted_unique(values: list[int]) -> list[int]:
    """Return sorted unique integer values."""

    return sorted({int(value) for value in values})


def _case_lookup(cases: list[dict[str, Any]]) -> dict[tuple[str, int, int], dict[str, Any]]:
    """Return cases keyed by link pattern, Nu, and Ns."""

    return {
        (case["link_pattern"], int(case["num_users"]), int(case["num_satellites"])): case
        for case in cases
    }


def _matrix_for_field(
    cases: list[dict[str, Any]],
    *,
    link_pattern: str,
    num_users_values: list[int],
    num_satellite_values: list[int],
    field: str,
) -> list[list[Any]]:
    """Return a Nu-by-Ns matrix for a candidate-case field."""

    lookup = _case_lookup(cases)
    matrix: list[list[Any]] = []
    for num_users in num_users_values:
        row = []
        for num_satellites in num_satellite_values:
            case = lookup[(link_pattern, num_users, num_satellites)]
            row.append(case[field])
        matrix.append(row)
    return matrix


def build_rank_feasibility_heatmap_data(
    candidate: dict[str, Any],
) -> dict[str, Any]:
    """Return rank-feasibility heatmap matrices grouped by link pattern."""

    cases = candidate["cases"]
    num_users_values = _sorted_unique([case["num_users"] for case in cases])
    num_satellite_values = _sorted_unique([case["num_satellites"] for case in cases])
    link_patterns = list(candidate["link_patterns"])
    panels = []
    for link_pattern in link_patterns:
        panels.append(
            {
                "link_pattern": link_pattern,
                "num_users_axis": num_users_values,
                "num_satellites_axis": num_satellite_values,
                "full_rank_matrix": _matrix_for_field(
                    cases,
                    link_pattern=link_pattern,
                    num_users_values=num_users_values,
                    num_satellite_values=num_satellite_values,
                    field="is_full_rank",
                ),
                "fim_rank_matrix": _matrix_for_field(
                    cases,
                    link_pattern=link_pattern,
                    num_users_values=num_users_values,
                    num_satellite_values=num_satellite_values,
                    field="fim_rank",
                ),
                "fim_nullity_matrix": _matrix_for_field(
                    cases,
                    link_pattern=link_pattern,
                    num_users_values=num_users_values,
                    num_satellite_values=num_satellite_values,
                    field="fim_nullity",
                ),
                "parameter_dim_matrix": _matrix_for_field(
                    cases,
                    link_pattern=link_pattern,
                    num_users_values=num_users_values,
                    num_satellite_values=num_satellite_values,
                    field="parameter_dim",
                ),
            }
        )
    return json_ready(
        {
            "candidate_name": "rank_feasibility_heatmap",
            "recommended_as_primary": True,
            "interpretation": (
                "Boolean full-rank map for the full gauged V24 FIM; "
                "rank-deficient cells are not finite CRLB values."
            ),
            "panels": panels,
        }
    )


def build_finite_crlb_vs_ns_data(candidate: dict[str, Any]) -> dict[str, Any]:
    """Return finite CRLB-vs-Ns series with unavailable masks."""

    grouped: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for case in candidate["cases"]:
        grouped[(case["link_pattern"], case["num_users"])].append(case)

    series = []
    for (link_pattern, num_users), cases in sorted(grouped.items()):
        ordered_cases = sorted(cases, key=lambda item: item["num_satellites"])
        series.append(
            {
                "link_pattern": link_pattern,
                "num_users": int(num_users),
                "num_satellites": [case["num_satellites"] for case in ordered_cases],
                "plot_value_status": [case["plot_value_status"] for case in ordered_cases],
                "average_ue_peb_km": [case["average_ue_peb_km"] for case in ordered_cases],
                "average_clock_bound_s": [case["average_clock_bound_s"] for case in ordered_cases],
                "unavailable_mask": [
                    case["plot_value_status"] != "finite" for case in ordered_cases
                ],
                "parameter_dim": [case["parameter_dim"] for case in ordered_cases],
                "fim_rank": [case["fim_rank"] for case in ordered_cases],
                "fim_nullity": [case["fim_nullity"] for case in ordered_cases],
            }
        )
    return json_ready(
        {
            "candidate_name": "finite_crlb_vs_ns_with_unavailable_points",
            "recommended_as_secondary": True,
            "interpretation": (
                "Ns series with finite values only for manuscript-ready full-rank "
                "cases; rank-deficient points are masked unavailable."
            ),
            "monotonicity_claim_valid": False,
            "series": series,
        }
    )


def build_fixed_measurement_addition_data(geometry: dict[str, Any]) -> dict[str, Any]:
    """Return fixed-parameter measurement-addition data from geometry diagnostics."""

    source = geometry["fixed_parameter_information_addition"]
    cases = source["cases"]
    return json_ready(
        {
            "candidate_name": "fixed_parameter_measurement_addition",
            "recommended_as_sanity_check": True,
            "interpretation": (
                "Fixed Nu, Ns, geometry, and parameter dimension; monotonicity "
                "is checked only after the FIM is full-rank."
            ),
            "num_users": source["num_users"],
            "num_satellites": source["num_satellites"],
            "parameter_dim": source["parameter_dim"],
            "measurement_count": [case["measurement_count"] for case in cases],
            "crlb_status": [case["crlb_status"] for case in cases],
            "average_ue_peb_km": [
                case["average_ue_peb_km"] if case["is_manuscript_ready"] else None
                for case in cases
            ],
            "average_clock_bound_s": [
                case["average_clock_bound_s"] if case["is_manuscript_ready"] else None
                for case in cases
            ],
            "unavailable_mask": [not case["is_manuscript_ready"] for case in cases],
            "monotonicity_checked": [case["monotonicity_checked"] for case in cases],
            "monotonicity_status": [case["monotonicity_status"] for case in cases],
        }
    )


def build_crlb_figure_candidate_data(
    *,
    base_seed: int = DEFAULT_BASE_SEED,
    range_std_dev_km: float = DEFAULT_RANGE_STD_DEV_KM,
) -> dict[str, Any]:
    """Return all non-final V24 CRLB figure-candidate data."""

    candidate = build_manuscript_crlb_candidate(
        base_seed=base_seed,
        range_std_dev_km=range_std_dev_km,
    )
    geometry = build_crlb_geometry_diagnostics(
        base_seed=base_seed,
        range_std_dev_km=range_std_dev_km,
    )
    return json_ready(
        {
            "diagnostic_type": "non_final_v24_crlb_figure_candidate_data",
            "schema_version": 1,
            "generated_marker": "deterministic_no_timestamp",
            "base_seed": int(base_seed),
            "output_note": "diagnostic/non-final; no figures generated",
            "figure_candidate_policy": FIGURE_CANDIDATE_POLICY,
            "rank_feasibility_heatmap": build_rank_feasibility_heatmap_data(candidate),
            "finite_crlb_vs_ns": build_finite_crlb_vs_ns_data(candidate),
            "fixed_parameter_measurement_addition": build_fixed_measurement_addition_data(
                geometry
            ),
            "source_diagnostics": {
                "manuscript_crlb_candidate": "v24_diagnostics/manuscript_crlb_candidate.json",
                "crlb_geometry_diagnostics": "v24_diagnostics/crlb_geometry_diagnostics.json",
            },
        }
    )


def write_crlb_figure_candidate_data(
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    *,
    base_seed: int = DEFAULT_BASE_SEED,
    range_std_dev_km: float = DEFAULT_RANGE_STD_DEV_KM,
    overwrite: bool = True,
) -> Path:
    """Build and write non-final V24 CRLB figure-candidate JSON."""

    payload = build_crlb_figure_candidate_data(
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
    """Run the non-final V24 CRLB figure-candidate data builder."""

    args = _parse_args()
    output_path = write_crlb_figure_candidate_data(
        args.output,
        base_seed=args.base_seed,
        range_std_dev_km=args.range_std_dev_km,
        overwrite=not args.no_overwrite,
    )
    print(f"Wrote non-final V24 CRLB figure-candidate data: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
