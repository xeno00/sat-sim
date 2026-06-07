"""Write a human-review report for package-native V24 Fig. 4--7 outputs.

The report is diagnostic provenance only. It does not mark outputs as
manuscript-ready and does not write to manuscript figure directories.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

SAT_SIM_ROOT = Path(__file__).resolve().parents[1]
if str(SAT_SIM_ROOT) not in sys.path:
    sys.path.insert(0, str(SAT_SIM_ROOT))

from jcls_sim.figure_generation import HUMAN_REVIEW_ARTIFACT_FLAGS, HUMAN_REVIEW_ARTIFACT_WARNING, repo_relative_path, validate_output_root  # noqa: E402
from jcls_sim.io import json_ready  # noqa: E402


DEFAULT_OUTPUT_ROOT = SAT_SIM_ROOT / "v24_human_review_outputs"


def _git_value(*args: str) -> str:
    """Return a git command value or ``unknown`` if unavailable."""

    try:
        return subprocess.check_output(["git", *args], cwd=SAT_SIM_ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _read_csv(path: Path) -> list[dict[str, str]]:
    """Read CSV rows."""

    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _float_or_none(value: Any) -> float | None:
    """Convert a CSV value to float when possible."""

    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _figure_summary(row: dict[str, Any], output_root: Path, previous_root: Path | None) -> dict[str, Any]:
    """Return a compact human-review summary for one figure output."""

    metadata_path = SAT_SIM_ROOT / str(row["metadata_file"])
    summary_path = SAT_SIM_ROOT / str(row["summary_output_file"])
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    summaries = _read_csv(summary_path)
    baseline_records = []
    for summary in summaries:
        mean = _float_or_none(summary.get("mean"))
        scale = float(metadata["units"].get("plot_metric_scale", 1.0))
        baseline_records.append(
            {
                "baseline_id": summary["baseline_id"],
                "x_value": summary["x_value"],
                "series_value": summary["series_value"],
                "trial_count": int(float(summary["trial_count"])),
                "success_rate": _float_or_none(summary.get("success_rate")),
                "mean_raw_metric": mean,
                "mean_plot_metric": None if mean is None else mean * scale,
                "metric_unit": metadata["units"].get("plot_metric_unit"),
                "all_baseline_observability_reportable": summary.get("all_baseline_observability_reportable"),
                "all_baseline_observability_full_rank": summary.get("all_baseline_observability_full_rank"),
                "max_baseline_observability_nullity": int(float(summary["max_baseline_observability_nullity"])),
                "max_baseline_observability_condition_number": _float_or_none(
                    summary.get("max_baseline_observability_condition_number")
                ),
            }
        )
    success_rates = [
        record["success_rate"]
        for record in baseline_records
        if record["success_rate"] is not None and record["baseline_id"] in {"coarse_jcls", "refined_jcls"}
    ]
    nonreportable = [
        record
        for record in baseline_records
        if str(record["all_baseline_observability_reportable"]).lower() != "true"
    ]
    previous_comparison = {
        "previous_root": repo_relative_path(previous_root) if previous_root and previous_root.exists() else None,
        "comparison_status": "available_for_manual_comparison" if previous_root and previous_root.exists() else "previous_root_not_found",
    }
    return {
        "figure_id": row["figure_id"],
        "manuscript_figure": row["manuscript_figure"],
        "metadata_file": row["metadata_file"],
        "summary_file": row["summary_output_file"],
        "raw_file": row["raw_output_file"],
        "pdf_file": row["plot_output_file"],
        "runtime_seconds": float(row["runtime_seconds"]),
        "monte_carlo_trials": int(row["monte_carlo_trials"]),
        "base_seed": int(row["base_seed"]),
        "minimum_jcls_success_rate": min(success_rates) if success_rates else None,
        "nonreportable_summary_row_count": len(nonreportable),
        "recommended_for_manuscript_consideration": bool(success_rates and min(success_rates) >= 0.8 and not nonreportable),
        "recommendation_note": (
            "Requires human technical review. Low JCLS success rates or nonreportable "
            "observability rows should block manuscript use."
        ),
        "baseline_records": baseline_records,
        "previous_candidate_comparison": previous_comparison,
        "case_metadata_summary": metadata.get("case_metadata", []),
    }


def build_report(output_root: Path, previous_root: Path | None = None, test_summary: str = "not recorded") -> dict[str, Any]:
    """Build a human-review report payload from an output root."""

    output_root = validate_output_root(output_root)
    table_path = output_root / "figure_provenance_table.json"
    if not table_path.exists():
        raise FileNotFoundError(f"Missing combined provenance table: {table_path}")
    table = json.loads(table_path.read_text(encoding="utf-8"))
    figures = [_figure_summary(row, output_root, previous_root) for row in table["rows"]]
    recommended_count = sum(bool(figure["recommended_for_manuscript_consideration"]) for figure in figures)
    return {
        "report_type": "package_native_v24_human_review_report",
        **HUMAN_REVIEW_ARTIFACT_FLAGS,
        "artifact_warning": HUMAN_REVIEW_ARTIFACT_WARNING,
        "branch": _git_value("branch", "--show-current"),
        "commit_hash": _git_value("rev-parse", "HEAD"),
        "output_root": repo_relative_path(output_root),
        "previous_candidate_root": repo_relative_path(previous_root) if previous_root and previous_root.exists() else None,
        "commands_to_regenerate": [
            "python scripts/run_v24_figures_4_7.py --config configs/v24_human_review_figures_4_7/fig4_localization_vs_satellites_human_review.json --config configs/v24_human_review_figures_4_7/fig5_synchronization_vs_satellites_human_review.json --config configs/v24_human_review_figures_4_7/fig6_localization_vs_clock_std_human_review.json --config configs/v24_human_review_figures_4_7/fig7_synchronization_vs_clock_std_human_review.json --output-root v24_human_review_outputs --overwrite",
            "python scripts/write_v24_human_review_report.py --output-root v24_human_review_outputs",
        ],
        "test_summary": test_summary,
        "figure_count": len(figures),
        "figures_recommended_for_manuscript_consideration": recommended_count,
        "overall_recommendation": (
            "review_only_not_manuscript_ready"
            if recommended_count < len(figures)
            else "human_may_consider_after_visual_and_scientific_review"
        ),
        "global_blockers": [
            "Synthetic Starlink-like geometry is used; TLE/SGP4 is not used.",
            "Dynamic refinement uses x=theta, F=I, Pi=I with diagonal process noise.",
            "Outputs are non-final, candidate-only, and not for TAES submission without human signoff.",
            "Any nonreportable observability rows or low JCLS success rates block manuscript use.",
        ],
        "figures": figures,
    }


def write_report(output_root: Path, previous_root: Path | None = None, test_summary: str = "not recorded") -> tuple[Path, Path]:
    """Write JSON and Markdown human-review reports."""

    output_root = validate_output_root(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    report = build_report(output_root, previous_root=previous_root, test_summary=test_summary)
    json_path = output_root / "HUMAN_REVIEW_REPORT.json"
    md_path = output_root / "HUMAN_REVIEW_REPORT.md"
    json_path.write_text(json.dumps(json_ready(report), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# V24 Package-Native Human Review Report",
        "",
        f"Warning: {report['artifact_warning']}",
        "",
        f"- Branch: `{report['branch']}`",
        f"- Commit: `{report['commit_hash']}`",
        f"- Output root: `{report['output_root']}`",
        f"- Test summary: {report['test_summary']}",
        f"- Overall recommendation: `{report['overall_recommendation']}`",
        "",
        "## Commands",
        "",
    ]
    lines.extend([f"- `{command}`" for command in report["commands_to_regenerate"]])
    lines.extend(["", "## Figure Summaries", ""])
    for figure in report["figures"]:
        lines.extend(
            [
                f"### {figure['manuscript_figure']} / `{figure['figure_id']}`",
                "",
                f"- PDF: `{figure['pdf_file']}`",
                f"- Summary CSV: `{figure['summary_file']}`",
                f"- Raw CSV: `{figure['raw_file']}`",
                f"- Monte Carlo trials: {figure['monte_carlo_trials']}",
                f"- Minimum JCLS success rate: {figure['minimum_jcls_success_rate']}",
                f"- Nonreportable summary rows: {figure['nonreportable_summary_row_count']}",
                f"- Manuscript consideration: {figure['recommended_for_manuscript_consideration']}",
                f"- Note: {figure['recommendation_note']}",
                "",
            ]
        )
    lines.extend(["## Global Blockers", ""])
    lines.extend([f"- {blocker}" for blocker in report["global_blockers"]])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--previous-root", type=Path, default=SAT_SIM_ROOT / "v24_manuscript_candidate_outputs")
    parser.add_argument("--test-summary", default="not recorded")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    json_path, md_path = write_report(args.output_root, previous_root=args.previous_root, test_summary=args.test_summary)
    print(f"human review json: {json_path}")
    print(f"human review markdown: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
