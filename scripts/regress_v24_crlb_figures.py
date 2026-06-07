"""Write non-final package-native V24 CRLB figure-family diagnostics.

This script does not generate manuscript figures, execute the legacy notebook,
or touch manuscript result directories. It writes deterministic JSON/CSV/NPZ
diagnostics under ``v24_diagnostics/regression/`` for human review.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Iterable

import numpy as np

SAT_SIM_ROOT = Path(__file__).resolve().parents[1]
if str(SAT_SIM_ROOT) not in sys.path:
    sys.path.insert(0, str(SAT_SIM_ROOT))

from jcls_sim.io import json_ready, write_json_diagnostic  # noqa: E402
from scripts.diagnose_v24_crlb_geometry import (  # noqa: E402
    DEFAULT_BASE_SEED,
    DEFAULT_RANGE_STD_DEV_KM,
)
from scripts.diagnose_v24_manuscript_crlb_candidate import (  # noqa: E402
    build_manuscript_crlb_candidate,
)


DEFAULT_OUTPUT_DIR = SAT_SIM_ROOT / "v24_diagnostics" / "regression"
DEFAULT_JSON_NAME = "crlb_figure_family_regression.json"
DEFAULT_CSV_NAME = "crlb_figure_family_regression.csv"
DEFAULT_NPZ_NAME = "crlb_figure_family_regression_masks.npz"

REGRESSION_POLICY = (
    "Non-final CRLB figure-family regression diagnostic only. Values are derived "
    "from package-native V24 full-gauged FIM/bounds. Rank-deficient or otherwise "
    "non-manuscript-ready cases are masked unavailable and must not be plotted as "
    "finite manuscript CRLB values."
)

FIGURE_FAMILIES = (
    {
        "family_id": "localization_crlb",
        "legacy_figure_hint": "pos_crlb_0dB_0dB",
        "metric_field": "average_ue_peb_km",
        "metric_name": "average_ue_peb",
        "unit": "km",
        "description": "Package-native full-gauged localization CRLB family.",
    },
    {
        "family_id": "synchronization_crlb",
        "legacy_figure_hint": "sync_crlb_0dB_0dB",
        "metric_field": "average_clock_bound_s",
        "metric_name": "average_clock_bound",
        "unit": "s",
        "description": "Package-native full-gauged synchronization CRLB family.",
    },
)

STATUS_CODE_MAP = {
    "finite": 1,
    "unavailable_rank_deficient": 0,
    "human_review": -1,
    "invalid": -2,
}


def _ordered_candidate_cases(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    """Return candidate cases in deterministic figure-family order."""

    return sorted(
        candidate["cases"],
        key=lambda case: (
            str(case["link_pattern"]),
            int(case["num_users"]),
            int(case["num_satellites"]),
            str(case["case_id"]),
        ),
    )


def _finite_value(case: dict[str, Any], metric_field: str) -> float | None:
    """Return a finite manuscript-ready value, or None if unavailable."""

    if case["plot_value_status"] != "finite" or not case["is_manuscript_ready"]:
        return None
    value = case[metric_field]
    if value is None:
        return None
    return float(value)


def _regression_row(
    *,
    family: dict[str, str],
    case: dict[str, Any],
) -> dict[str, Any]:
    """Return one flat regression row for a figure family and candidate case."""

    finite_value = _finite_value(case, family["metric_field"])
    finite = finite_value is not None
    plot_status = str(case["plot_value_status"])
    rank_deficient = str(case["crlb_status"]) == "rank_deficient_diagnostic"
    return json_ready(
        {
            "row_id": f"{family['family_id']}::{case['case_id']}",
            "figure_family": family["family_id"],
            "legacy_figure_hint": family["legacy_figure_hint"],
            "metric_name": family["metric_name"],
            "metric_unit": family["unit"],
            "source_case_id": case["case_id"],
            "num_users": case["num_users"],
            "num_satellites": case["num_satellites"],
            "link_pattern": case["link_pattern"],
            "measurement_count": case["measurement_count"],
            "parameter_dim": case["parameter_dim"],
            "unknown_count": case["unknown_count"],
            "fim_rank": case["fim_rank"],
            "fim_nullity": case["fim_nullity"],
            "crlb_status": case["crlb_status"],
            "manuscript_crlb_status": case["manuscript_crlb_status"],
            "plot_value_status": plot_status,
            "status_code": STATUS_CODE_MAP.get(plot_status, STATUS_CODE_MAP["invalid"]),
            "finite_mask": finite,
            "unavailable_mask": not finite,
            "rank_deficient_mask": rank_deficient,
            "finite_bound_value": finite_value,
            "finite_bound_unit": family["unit"] if finite else None,
            "average_ue_peb_km_finite_only": case["average_ue_peb_km"]
            if finite and family["metric_field"] == "average_ue_peb_km"
            else None,
            "average_clock_bound_s_finite_only": case["average_clock_bound_s"]
            if finite and family["metric_field"] == "average_clock_bound_s"
            else None,
            "unavailable_reason": None if finite else case["unavailable_reason"],
        }
    )


def _family_payload(family: dict[str, str], cases: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Return one figure-family regression payload."""

    rows = [_regression_row(family=family, case=case) for case in cases]
    finite_count = sum(1 for row in rows if row["finite_mask"])
    unavailable_count = len(rows) - finite_count
    return json_ready(
        {
            "family_id": family["family_id"],
            "legacy_figure_hint": family["legacy_figure_hint"],
            "description": family["description"],
            "metric_name": family["metric_name"],
            "metric_unit": family["unit"],
            "finite_case_count": finite_count,
            "unavailable_case_count": unavailable_count,
            "rows": rows,
        }
    )


def _flat_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return all figure-family rows from a regression payload."""

    rows: list[dict[str, Any]] = []
    for family in payload["figure_families"]:
        rows.extend(family["rows"])
    return rows


def build_crlb_figure_family_regression(
    *,
    base_seed: int = DEFAULT_BASE_SEED,
    range_std_dev_km: float = DEFAULT_RANGE_STD_DEV_KM,
) -> dict[str, Any]:
    """Return non-final CRLB localization/synchronization regression diagnostics."""

    candidate = build_manuscript_crlb_candidate(
        base_seed=base_seed,
        range_std_dev_km=range_std_dev_km,
    )
    ordered_cases = _ordered_candidate_cases(candidate)
    figure_families = [_family_payload(family, ordered_cases) for family in FIGURE_FAMILIES]
    flat_rows = [row for family in figure_families for row in family["rows"]]
    return json_ready(
        {
            "diagnostic_type": "non_final_v24_crlb_figure_family_regression",
            "schema_version": 1,
            "generated_marker": "deterministic_no_timestamp",
            "base_seed": int(base_seed),
            "range_std_dev_km": float(range_std_dev_km),
            "non_final": True,
            "manuscript_figure": False,
            "notebook_executed": False,
            "output_note": "diagnostic/non-final; no manuscript figures generated",
            "regression_policy": REGRESSION_POLICY,
            "source_diagnostic": "non_final_v24_manuscript_crlb_candidate",
            "source_path_hint": "v24_diagnostics/manuscript_crlb_candidate.json",
            "status_code_map": STATUS_CODE_MAP,
            "figure_family_count": len(figure_families),
            "case_count_per_family": len(ordered_cases),
            "row_count": len(flat_rows),
            "finite_row_count": sum(1 for row in flat_rows if row["finite_mask"]),
            "unavailable_row_count": sum(1 for row in flat_rows if row["unavailable_mask"]),
            "figure_families": figure_families,
        }
    )


def _ensure_can_write(path: Path, *, overwrite: bool) -> None:
    """Raise if a diagnostic output would be overwritten unexpectedly."""

    if path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing regression output: {path}")


def write_regression_csv(
    payload: dict[str, Any],
    output_path: str | Path,
    *,
    overwrite: bool = True,
) -> Path:
    """Write flat figure-family regression rows as CSV."""

    path = Path(output_path)
    _ensure_can_write(path, overwrite=overwrite)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = _flat_rows(payload)
    fieldnames = [
        "row_id",
        "figure_family",
        "legacy_figure_hint",
        "metric_name",
        "metric_unit",
        "source_case_id",
        "num_users",
        "num_satellites",
        "link_pattern",
        "measurement_count",
        "parameter_dim",
        "unknown_count",
        "fim_rank",
        "fim_nullity",
        "crlb_status",
        "manuscript_crlb_status",
        "plot_value_status",
        "status_code",
        "finite_mask",
        "unavailable_mask",
        "rank_deficient_mask",
        "finite_bound_value",
        "finite_bound_unit",
        "average_ue_peb_km_finite_only",
        "average_clock_bound_s_finite_only",
        "unavailable_reason",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


def write_regression_npz(
    payload: dict[str, Any],
    output_path: str | Path,
    *,
    overwrite: bool = True,
) -> Path:
    """Write compact numeric masks and finite-only values as NPZ."""

    path = Path(output_path)
    _ensure_can_write(path, overwrite=overwrite)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = _flat_rows(payload)
    finite_values = np.array(
        [
            np.nan if row["finite_bound_value"] is None else float(row["finite_bound_value"])
            for row in rows
        ],
        dtype=float,
    )
    np.savez(
        path,
        finite_bound_value=finite_values,
        finite_mask=np.array([bool(row["finite_mask"]) for row in rows], dtype=bool),
        unavailable_mask=np.array([bool(row["unavailable_mask"]) for row in rows], dtype=bool),
        rank_deficient_mask=np.array([bool(row["rank_deficient_mask"]) for row in rows], dtype=bool),
        status_code=np.array([int(row["status_code"]) for row in rows], dtype=int),
        num_users=np.array([int(row["num_users"]) for row in rows], dtype=int),
        num_satellites=np.array([int(row["num_satellites"]) for row in rows], dtype=int),
        measurement_count=np.array([int(row["measurement_count"]) for row in rows], dtype=int),
        parameter_dim=np.array([int(row["parameter_dim"]) for row in rows], dtype=int),
        fim_rank=np.array([int(row["fim_rank"]) for row in rows], dtype=int),
        fim_nullity=np.array([int(row["fim_nullity"]) for row in rows], dtype=int),
        figure_family=np.array([str(row["figure_family"]) for row in rows]),
        link_pattern=np.array([str(row["link_pattern"]) for row in rows]),
        row_id=np.array([str(row["row_id"]) for row in rows]),
    )
    return path


def write_crlb_figure_family_regression(
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    *,
    base_seed: int = DEFAULT_BASE_SEED,
    range_std_dev_km: float = DEFAULT_RANGE_STD_DEV_KM,
    overwrite: bool = True,
) -> dict[str, Any]:
    """Build and write non-final JSON/CSV/NPZ CRLB regression diagnostics."""

    output_root = Path(output_dir)
    payload = build_crlb_figure_family_regression(
        base_seed=base_seed,
        range_std_dev_km=range_std_dev_km,
    )
    json_path = output_root / DEFAULT_JSON_NAME
    csv_path = output_root / DEFAULT_CSV_NAME
    npz_path = output_root / DEFAULT_NPZ_NAME
    write_json_diagnostic(payload, json_path, overwrite=overwrite)
    write_regression_csv(payload, csv_path, overwrite=overwrite)
    write_regression_npz(payload, npz_path, overwrite=overwrite)
    payload["written_outputs"] = {
        "json": str(json_path.as_posix()),
        "csv": str(csv_path.as_posix()),
        "npz": str(npz_path.as_posix()),
    }
    write_json_diagnostic(payload, json_path, overwrite=True)
    return payload


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--base-seed", type=int, default=DEFAULT_BASE_SEED)
    parser.add_argument("--range-std-dev-km", type=float, default=DEFAULT_RANGE_STD_DEV_KM)
    parser.add_argument("--no-overwrite", action="store_true")
    return parser.parse_args()


def main() -> int:
    """Run the non-final CRLB figure-family regression writer."""

    args = _parse_args()
    payload = write_crlb_figure_family_regression(
        args.output_dir,
        base_seed=args.base_seed,
        range_std_dev_km=args.range_std_dev_km,
        overwrite=not args.no_overwrite,
    )
    outputs = payload["written_outputs"]
    print(f"Wrote non-final CRLB regression JSON: {outputs['json']}")
    print(f"Wrote non-final CRLB regression CSV: {outputs['csv']}")
    print(f"Wrote non-final CRLB regression NPZ: {outputs['npz']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
