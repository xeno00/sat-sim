"""Build a non-final manuscript-relevant V24 CRLB candidate diagnostic.

This script does not generate figures or manuscript results. It summarizes the
package-native rank-feasibility grid into finite manuscript-ready cases and
explicitly unavailable rank-deficient cases.
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Sequence

SAT_SIM_ROOT = Path(__file__).resolve().parents[1]
if str(SAT_SIM_ROOT) not in sys.path:
    sys.path.insert(0, str(SAT_SIM_ROOT))

from jcls_sim.constants import C_KM_PER_S  # noqa: E402
from jcls_sim.io import json_ready, write_json_diagnostic  # noqa: E402
from scripts.diagnose_v24_crlb_geometry import (  # noqa: E402
    DEFAULT_BASE_SEED,
    DEFAULT_RANGE_STD_DEV_KM,
    DEFAULT_RANK_GRID_NUM_SATELLITES,
    DEFAULT_RANK_GRID_NUM_USERS,
    DEFAULT_RANK_GRID_PATTERNS,
    PACKAGE_CONVENTIONS,
    build_rank_feasibility_grid,
)


DEFAULT_OUTPUT_PATH = SAT_SIM_ROOT / "v24_diagnostics" / "manuscript_crlb_candidate.json"

UNAVAILABLE_POLICY = (
    "Rank-deficient points are marked unavailable and must not be plotted as "
    "finite manuscript CRLB values."
)


def _plot_status(case: dict[str, Any]) -> str:
    """Return the plot-value status for a rank-grid case."""

    if case["crlb_status"] == "finite_crlb" and case["is_manuscript_ready"]:
        return "finite"
    if case["crlb_status"] == "rank_deficient_diagnostic":
        return "unavailable_rank_deficient"
    return "human_review"


def _candidate_case(case: dict[str, Any]) -> dict[str, Any]:
    """Return a manuscript-candidate case with unavailable fields guarded."""

    plot_status = _plot_status(case)
    finite = plot_status == "finite"
    return json_ready(
        {
            "case_id": case["case_id"],
            "num_users": case["num_users"],
            "num_satellites": case["num_satellites"],
            "link_pattern": case["link_pattern"],
            "measurement_count": case["measurement_count"],
            "parameter_dim": case["parameter_dim"],
            "unknown_count": case["unknown_count"],
            "fim_rank": case["fim_rank"],
            "fim_nullity": case["fim_nullity"],
            "is_full_rank": case["is_full_rank"],
            "crlb_status": case["crlb_status"],
            "manuscript_crlb_status": case["manuscript_crlb_status"],
            "is_manuscript_ready": case["is_manuscript_ready"],
            "plot_value_status": plot_status,
            "average_ue_peb_km": case["average_ue_peb_km"] if finite else None,
            "average_clock_bound_km": case["average_clock_bound_km"] if finite else None,
            "average_clock_bound_s": case["average_clock_bound_s"] if finite else None,
            "unavailable_reason": None if finite else case["crlb_status"],
            "notes": case["notes"],
        }
    )


def _minimal_full_rank_table(cases: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return minimal full-rank satellite counts by user count and link pattern."""

    grouped: dict[tuple[str, int], list[int]] = defaultdict(list)
    for case in cases:
        if case["plot_value_status"] == "finite":
            grouped[(case["link_pattern"], case["num_users"])].append(case["num_satellites"])
    rows = []
    for (link_pattern, num_users), satellite_counts in sorted(grouped.items()):
        rows.append(
            {
                "link_pattern": link_pattern,
                "num_users": num_users,
                "min_full_rank_num_satellites": min(satellite_counts),
                "full_rank_num_satellites": sorted(satellite_counts),
            }
        )
    return rows


def build_manuscript_crlb_candidate(
    *,
    base_seed: int = DEFAULT_BASE_SEED,
    num_users_values: Sequence[int] = DEFAULT_RANK_GRID_NUM_USERS,
    num_satellite_values: Sequence[int] = DEFAULT_RANK_GRID_NUM_SATELLITES,
    link_patterns: Sequence[str] = DEFAULT_RANK_GRID_PATTERNS,
    range_std_dev_km: float = DEFAULT_RANGE_STD_DEV_KM,
) -> dict[str, Any]:
    """Return non-final manuscript-relevant CRLB candidate diagnostics."""

    grid = build_rank_feasibility_grid(
        seed=base_seed,
        num_users_values=num_users_values,
        num_satellite_values=num_satellite_values,
        link_patterns=link_patterns,
        range_std_dev_km=range_std_dev_km,
    )
    candidate_cases = [_candidate_case(case) for case in grid["cases"]]
    finite_cases = [case for case in candidate_cases if case["plot_value_status"] == "finite"]
    unavailable_cases = [
        case for case in candidate_cases if case["plot_value_status"] != "finite"
    ]
    return json_ready(
        {
            "diagnostic_type": "non_final_v24_manuscript_crlb_candidate",
            "schema_version": 1,
            "generated_marker": "deterministic_no_timestamp",
            "base_seed": int(base_seed),
            "candidate_type": "rank_feasibility_with_finite_bound_summaries",
            "output_note": "diagnostic/non-final; not a manuscript figure or result sweep",
            "unavailable_policy": UNAVAILABLE_POLICY,
            "package_conventions": PACKAGE_CONVENTIONS,
            "num_users_values": [int(value) for value in num_users_values],
            "num_satellite_values": [int(value) for value in num_satellite_values],
            "link_patterns": list(link_patterns),
            "range_std_dev_km": float(range_std_dev_km),
            "finite_case_count": len(finite_cases),
            "unavailable_case_count": len(unavailable_cases),
            "minimal_full_rank_table": _minimal_full_rank_table(candidate_cases),
            "cases": candidate_cases,
        }
    )


def write_manuscript_crlb_candidate(
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    *,
    base_seed: int = DEFAULT_BASE_SEED,
    range_std_dev_km: float = DEFAULT_RANGE_STD_DEV_KM,
    overwrite: bool = True,
) -> Path:
    """Build and write the non-final manuscript-relevant CRLB candidate JSON."""

    payload = build_manuscript_crlb_candidate(
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
    """Run the non-final V24 manuscript CRLB candidate diagnostic."""

    args = _parse_args()
    output_path = write_manuscript_crlb_candidate(
        args.output,
        base_seed=args.base_seed,
        range_std_dev_km=args.range_std_dev_km,
        overwrite=not args.no_overwrite,
    )
    print(f"Wrote non-final V24 manuscript CRLB candidate diagnostic: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
