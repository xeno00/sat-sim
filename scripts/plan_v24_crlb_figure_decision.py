"""Build a non-final decision plan from V24 CRLB preview diagnostics.

This script is diagnostic-only. It reads existing package-native CRLB JSON and
preview metadata, then writes a compact human-decision plan. It does not run
the legacy notebook, full sweeps, or manuscript figure generation.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SAT_SIM_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANDIDATE_PATH = SAT_SIM_ROOT / "v24_diagnostics" / "crlb_figure_candidate_data.json"
DEFAULT_PREVIEW_MANIFEST_PATH = (
    SAT_SIM_ROOT / "v24_diagnostics" / "crlb_preview" / "preview_manifest.json"
)
DEFAULT_OUTPUT_PATH = SAT_SIM_ROOT / "v24_diagnostics" / "crlb_figure_decision_plan.json"


def _load_json(path: str | Path) -> dict[str, Any]:
    """Load a JSON dictionary from disk."""

    resolved = Path(path)
    return json.loads(resolved.read_text(encoding="utf-8"))


def _write_json(payload: dict[str, Any], output_path: str | Path, *, overwrite: bool) -> Path:
    """Write JSON while refusing accidental overwrites unless requested."""

    resolved = Path(output_path)
    if resolved.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite diagnostic output: {resolved}")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return resolved


def summarize_rank_heatmap(candidate: dict[str, Any]) -> dict[str, Any]:
    """Summarize full-rank feasibility by link pattern and user count."""

    panels = candidate["rank_feasibility_heatmap"]["panels"]
    summaries = []
    total_cells = 0
    full_rank_cells = 0
    for panel in panels:
        user_axis = panel["num_users_axis"]
        satellite_axis = panel["num_satellites_axis"]
        matrix = panel["full_rank_matrix"]
        minimum_full_rank_by_num_users = {}
        panel_total = 0
        panel_full_rank = 0
        for row_index, num_users in enumerate(user_axis):
            full_rank_satellites = [
                satellite_axis[col_index]
                for col_index, is_full_rank in enumerate(matrix[row_index])
                if is_full_rank
            ]
            minimum_full_rank_by_num_users[str(num_users)] = (
                min(full_rank_satellites) if full_rank_satellites else None
            )
            panel_total += len(satellite_axis)
            panel_full_rank += len(full_rank_satellites)
        total_cells += panel_total
        full_rank_cells += panel_full_rank
        summaries.append(
            {
                "link_pattern": panel["link_pattern"],
                "total_cells": panel_total,
                "full_rank_cells": panel_full_rank,
                "rank_deficient_cells": panel_total - panel_full_rank,
                "minimum_full_rank_num_satellites_by_num_users": minimum_full_rank_by_num_users,
            }
        )
    return {
        "candidate_name": "rank_feasibility_heatmap",
        "recommended_role": "primary_decision_candidate",
        "reason": (
            "Directly separates full-rank regimes from rank-deficient regimes "
            "without presenting pseudoinverse values as finite CRLBs."
        ),
        "total_cells": total_cells,
        "full_rank_cells": full_rank_cells,
        "rank_deficient_cells": total_cells - full_rank_cells,
        "by_link_pattern": summaries,
    }


def summarize_finite_crlb_vs_ns(candidate: dict[str, Any]) -> dict[str, Any]:
    """Summarize finite CRLB-vs-Ns series and unavailable masks."""

    series_summaries = []
    total_points = 0
    finite_points = 0
    unavailable_points = 0
    for item in candidate["finite_crlb_vs_ns"]["series"]:
        statuses = item["plot_value_status"]
        finite_count = sum(status == "finite" for status in statuses)
        unavailable_count = len(statuses) - finite_count
        total_points += len(statuses)
        finite_points += finite_count
        unavailable_points += unavailable_count
        series_summaries.append(
            {
                "link_pattern": item["link_pattern"],
                "num_users": item["num_users"],
                "point_count": len(statuses),
                "finite_count": finite_count,
                "unavailable_count": unavailable_count,
                "num_satellites": item["num_satellites"],
                "unavailable_mask": item["unavailable_mask"],
                "parameter_dim_changes": len(set(item["parameter_dim"])) > 1,
            }
        )
    return {
        "candidate_name": "finite_crlb_vs_ns_with_unavailable_points",
        "recommended_role": "secondary_or_supplemental_candidate",
        "monotonicity_claim_valid": candidate["finite_crlb_vs_ns"]["monotonicity_claim_valid"],
        "required_caveat": (
            "The sweep changes the parameter dimension as Ns changes by adding "
            "satellite clock nuisance states, so it must not be presented as a "
            "standard monotonic information-addition curve."
        ),
        "total_points": total_points,
        "finite_points": finite_points,
        "unavailable_rank_deficient_points": unavailable_points,
        "series": series_summaries,
    }


def summarize_fixed_measurement_addition(candidate: dict[str, Any]) -> dict[str, Any]:
    """Summarize the fixed-parameter measurement-addition diagnostic."""

    fixed = candidate["fixed_parameter_measurement_addition"]
    finite_indices = [
        index for index, status in enumerate(fixed["crlb_status"]) if status == "finite_crlb"
    ]
    first_finite_index = finite_indices[0] if finite_indices else None
    return {
        "candidate_name": "fixed_parameter_measurement_addition",
        "recommended_role": "sanity_check_or_supplemental_candidate",
        "num_users": fixed["num_users"],
        "num_satellites": fixed["num_satellites"],
        "parameter_dim": fixed["parameter_dim"],
        "measurement_count": fixed["measurement_count"],
        "first_full_rank_measurement_count": (
            fixed["measurement_count"][first_finite_index]
            if first_finite_index is not None
            else None
        ),
        "monotonicity_status": fixed["monotonicity_status"],
        "required_caveat": (
            "This diagnostic is monotone only because the parameter vector and "
            "geometry are fixed; it should not be used to justify monotonicity "
            "of a growing-Ns sweep."
        ),
    }


def build_decision_plan(
    *,
    candidate_path: str | Path = DEFAULT_CANDIDATE_PATH,
    preview_manifest_path: str | Path = DEFAULT_PREVIEW_MANIFEST_PATH,
) -> dict[str, Any]:
    """Return a non-final human-decision plan for CRLB figure handling."""

    candidate = _load_json(candidate_path)
    manifest = _load_json(preview_manifest_path)
    rank_summary = summarize_rank_heatmap(candidate)
    finite_summary = summarize_finite_crlb_vs_ns(candidate)
    fixed_summary = summarize_fixed_measurement_addition(candidate)
    return {
        "diagnostic_type": "non_final_v24_crlb_figure_decision_plan",
        "schema_version": 1,
        "generated_marker": "deterministic_no_timestamp",
        "decision_input_status": "PASS_WITH_CAVEAT",
        "non_final": True,
        "manuscript_figure": False,
        "source_diagnostics": {
            "candidate_data": str(Path(candidate_path).as_posix()),
            "preview_manifest": str(Path(preview_manifest_path).as_posix()),
            "source_candidate_type": candidate["diagnostic_type"],
            "source_preview_type": manifest["diagnostic_type"],
        },
        "recommended_decision_path": [
            {
                "priority": 1,
                "candidate": "rank_feasibility_heatmap",
                "recommendation": "propose_first",
                "reason": rank_summary["reason"],
            },
            {
                "priority": 2,
                "candidate": "finite_crlb_vs_ns_with_unavailable_points",
                "recommendation": "consider_only_with_caveats",
                "reason": finite_summary["required_caveat"],
            },
            {
                "priority": 3,
                "candidate": "fixed_parameter_measurement_addition",
                "recommendation": "use_as_sanity_check_or_supplement",
                "reason": fixed_summary["required_caveat"],
            },
        ],
        "candidate_summaries": {
            "rank_feasibility_heatmap": rank_summary,
            "finite_crlb_vs_ns": finite_summary,
            "fixed_parameter_measurement_addition": fixed_summary,
        },
        "likely_manuscript_figure_implications": [
            {
                "target": "legacy_CRLB_vs_satellite_count_figures",
                "status": "likely_needs_package_native_rerun_or_replacement",
                "reason": (
                    "Growing Ns changes the gauged parameter dimension and rank-deficient "
                    "cases must be unavailable rather than pseudoinverse-derived finite curves."
                ),
            },
            {
                "target": "legacy_CRLB_localization_and_synchronization_panels",
                "status": "unsafe_until_package_native_workflow_is_approved",
                "reason": (
                    "Legacy notebook provenance is still flagged for ungauged/all-clock CRLB "
                    "handling, while package-native full-gauged diagnostics now produce "
                    "different reportability constraints."
                ),
            },
            {
                "target": "rank_feasibility_or_observability_explanation",
                "status": "strong_candidate_for_new_or_supplemental_material",
                "reason": (
                    "It explains which network regimes have ordinary finite CRLBs before "
                    "discussing bound magnitudes."
                ),
            },
        ],
        "human_review_questions": [
            "Should rank feasibility replace or supplement the current CRLB figure?",
            "Which link pattern should represent the manuscript scenario: dl_only, all_dl_minimal_sl, or all_dl_all_directed_sl?",
            "Should finite CRLB-vs-Ns curves be shown only for finite cases with unavailable markers?",
            "Should response-letter or manuscript text change if the CRLB figure concept changes?",
            "Is a fixed-parameter measurement-addition sanity plot useful enough to include, or only diagnostic?",
        ],
        "stop_gates_for_next_work": [
            "Need to execute JCLS_Simulation.ipynb.",
            "Need to write Work-In-Progress figure or manuscript output directories.",
            "Need to reinterpret rank-deficient pseudoinverse values as finite CRLBs.",
            "Need to make manuscript or response-letter claims before human approval.",
            "Need to run full expensive sweeps or final figure generation.",
        ],
        "preview_outputs": manifest["outputs"],
    }


def write_decision_plan(
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    *,
    candidate_path: str | Path = DEFAULT_CANDIDATE_PATH,
    preview_manifest_path: str | Path = DEFAULT_PREVIEW_MANIFEST_PATH,
    overwrite: bool = True,
) -> Path:
    """Build and write the non-final CRLB figure decision plan."""

    payload = build_decision_plan(
        candidate_path=candidate_path,
        preview_manifest_path=preview_manifest_path,
    )
    return _write_json(payload, output_path, overwrite=overwrite)


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE_PATH)
    parser.add_argument("--preview-manifest", type=Path, default=DEFAULT_PREVIEW_MANIFEST_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--no-overwrite", action="store_true")
    return parser.parse_args()


def main() -> int:
    """Run the non-final CRLB figure decision-plan writer."""

    args = _parse_args()
    output_path = write_decision_plan(
        args.output,
        candidate_path=args.candidate,
        preview_manifest_path=args.preview_manifest,
        overwrite=not args.no_overwrite,
    )
    print(f"Wrote non-final V24 CRLB decision plan: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
