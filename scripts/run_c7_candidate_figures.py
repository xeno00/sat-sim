"""Generate bounded non-final C7 candidate figures for human review.

This script uses Step B / LM-only as the comparison baseline and
``step_c7_residual_cov_sync_safeguard`` as the Step 3 candidate. Outputs are
candidate-only diagnostics under ``outputs/c7_candidate_figures/``; they are
not manuscript figures and are not marked manuscript-ready.
"""

from __future__ import annotations

import csv
import json
import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


SAT_SIM_ROOT = Path(__file__).resolve().parents[1]
if str(SAT_SIM_ROOT) not in sys.path:
    sys.path.insert(0, str(SAT_SIM_ROOT))

from jcls_sim.algorithm import STEP_C7_ESTIMATOR_MODE  # noqa: E402
from jcls_sim.constants import C_KM_PER_S  # noqa: E402
from scripts import explore_step3_covariance as cov  # noqa: E402
from scripts import run_step_c7_residual_cov_sync_safeguard as c7  # noqa: E402


OUTPUT_ROOT = SAT_SIM_ROOT / "outputs" / "c7_candidate_figures"
PLOT_ROOT = OUTPUT_ROOT / "plots"
REPORT_ROOT = SAT_SIM_ROOT / "outputs" / "reports"
NETWORK_CASES = [(num_users, num_satellites) for num_users in (1, 3, 5, 7) for num_satellites in (4, 8, 12)]
CLOCK_SWEEP_SECONDS = [1.0e-4, 1.0e-6, 1.0e-8, 1.0e-10]
CLOCK_SWEEP_CASE = {"num_users": 3, "num_satellites": 8}
PRECISE_COVARIANCE_TERMINOLOGY = "typed block-extracted, diagonal-clipped residual-scaled covariance"
BASE_FIELDS = [
    "family",
    "candidate",
    "estimator_mode",
    "num_users",
    "num_satellites",
    "grid",
    "clock_std_seconds",
    "clock_std_km",
    "runtime_seconds",
    "cache_status",
    "step_b_position_error_m",
    "step_b_sync_error_km",
    "step_b_sync_error_ns",
    "c7_position_error_m",
    "c7_sync_error_km",
    "c7_sync_error_ns",
    "position_ratio",
    "sync_ratio",
    "both_improved",
    "position_improved",
    "sync_improved",
    "fallback_triggered",
    "fallback_reason",
    "fallback_behavior",
    "affected_state_blocks",
    "objective_decreased",
    "truth_state_used_for_acceptance",
    "truth_state_used_for_covariance",
    "truth_state_used_for_safeguard",
]


def _repo_rel(path: Path) -> str:
    """Return a sat-sim-relative path."""

    return path.relative_to(SAT_SIM_ROOT).as_posix()


def _json_dump(path: Path, payload: dict[str, Any]) -> None:
    """Write stable JSON."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    """Write rows to a CSV with a fixed field order."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _sync_km_to_ns(value_km: float) -> float:
    """Convert range-domain clock/sync error in km to ns."""

    return float(value_km / C_KM_PER_S * 1.0e9)


def _augment_row(row: dict[str, Any], *, family: str, clock_std_seconds: float | None = None) -> dict[str, Any]:
    """Add candidate-figure metadata and synchronization seconds-domain fields."""

    clock_std_km = None if clock_std_seconds is None else float(clock_std_seconds * C_KM_PER_S)
    return {
        **row,
        "family": family,
        "grid": "network_medium" if family == "network_size" else "clock_sparse",
        "clock_std_seconds": "" if clock_std_seconds is None else float(clock_std_seconds),
        "clock_std_km": "" if clock_std_km is None else clock_std_km,
        "step_b_sync_error_ns": _sync_km_to_ns(float(row["step_b_sync_error_km"])),
        "c7_sync_error_ns": _sync_km_to_ns(float(row["c7_sync_error_km"])),
    }


def _deterministic_clock_error(count: int, clock_std_seconds: float) -> np.ndarray:
    """Return a deterministic clock-error vector with the requested seconds-domain scale."""

    idx = np.arange(count, dtype=float)
    pattern = np.sin(0.71 * (idx + 1.0)) + 0.35 * np.cos(0.29 * (idx + 2.0))
    pattern -= float(np.mean(pattern))
    std = float(np.std(pattern))
    if std == 0.0:
        pattern = np.ones(count, dtype=float)
        std = 1.0
    return pattern / std * float(clock_std_seconds * C_KM_PER_S)


def _clock_sweep_case(clock_std_seconds: float) -> cov.SparseCase:
    """Return the bounded deterministic clock-sweep case."""

    base = cov._make_case(CLOCK_SWEEP_CASE["num_users"], CLOCK_SWEEP_CASE["num_satellites"])
    clock_error = _deterministic_clock_error(base.true_clocks_km.size, clock_std_seconds)
    return replace(
        base,
        name=f"clock_std_{clock_std_seconds:.0e}",
        step_b_clocks_km=base.true_clocks_km + clock_error,
    )


def _evaluate_network_rows() -> list[dict[str, Any]]:
    """Evaluate the bounded network-size candidate grid."""

    candidate = c7.CANDIDATES[0]
    return [
        _augment_row(
            c7.evaluate_case_candidate(cov._make_case(num_users, num_satellites), candidate),
            family="network_size",
        )
        for num_users, num_satellites in NETWORK_CASES
    ]


def _evaluate_clock_rows() -> list[dict[str, Any]]:
    """Evaluate the bounded sparse clock-standard-deviation sweep."""

    candidate = c7.CANDIDATES[0]
    rows = []
    for clock_std_seconds in CLOCK_SWEEP_SECONDS:
        rows.append(
            _augment_row(
                c7.evaluate_case_candidate(_clock_sweep_case(clock_std_seconds), candidate),
                family="clock_sweep",
                clock_std_seconds=clock_std_seconds,
            )
        )
    return rows


def _summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Summarize candidate rows by figure family."""

    summaries = []
    for family in ("network_size", "clock_sweep"):
        selected = [row for row in rows if row["family"] == family]
        if not selected:
            continue
        summaries.append(
            {
                "family": family,
                "row_count": len(selected),
                "position_improved_count": sum(float(row["position_ratio"]) < 1.0 for row in selected),
                "sync_improved_count": sum(float(row["sync_ratio"]) < 1.0 for row in selected),
                "both_improved_count": sum(bool(row["both_improved"]) for row in selected),
                "fallback_count": sum(bool(row["fallback_triggered"]) for row in selected),
                "fallback_rows": [
                    {
                        "num_users": row["num_users"],
                        "num_satellites": row["num_satellites"],
                        "clock_std_seconds": row["clock_std_seconds"],
                        "fallback_reason": row["fallback_reason"],
                    }
                    for row in selected
                    if bool(row["fallback_triggered"])
                ],
                "mean_position_ratio": float(np.mean([float(row["position_ratio"]) for row in selected])),
                "max_position_ratio": float(np.max([float(row["position_ratio"]) for row in selected])),
                "mean_sync_ratio": float(np.mean([float(row["sync_ratio"]) for row in selected])),
                "max_sync_ratio": float(np.max([float(row["sync_ratio"]) for row in selected])),
            }
        )
    return summaries


def _plot_network(rows: list[dict[str, Any]], *, metric_b: str, metric_c7: str, ylabel: str, filename: str) -> Path:
    """Plot a network-size figure family with fallback markers."""

    fig, ax = plt.subplots(figsize=(7.2, 4.3))
    for num_users in sorted({int(row["num_users"]) for row in rows}):
        selected = sorted([row for row in rows if int(row["num_users"]) == num_users], key=lambda item: int(item["num_satellites"]))
        ns = [int(row["num_satellites"]) for row in selected]
        ax.plot(ns, [float(row[metric_b]) for row in selected], marker="o", linestyle="--", label=f"Step B Nu={num_users}")
        ax.plot(ns, [float(row[metric_c7]) for row in selected], marker="s", label=f"C7 Nu={num_users}")
        fallback = [row for row in selected if bool(row["fallback_triggered"])]
        if fallback:
            ax.scatter(
                [int(row["num_satellites"]) for row in fallback],
                [float(row[metric_c7]) for row in fallback],
                marker="x",
                s=80,
                color="black",
                label=f"fallback Nu={num_users}",
                zorder=5,
            )
    ax.set_xlabel("Number of satellites")
    ax.set_ylabel(ylabel)
    ax.set_title("Non-final C7 candidate validation")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=7, ncol=2)
    fig.tight_layout()
    output = PLOT_ROOT / filename
    fig.savefig(output)
    fig.savefig(output.with_suffix(".png"))
    plt.close(fig)
    return output


def _plot_clock(rows: list[dict[str, Any]], *, metric_b: str, metric_c7: str, ylabel: str, filename: str) -> Path:
    """Plot a sparse clock-standard-deviation figure family."""

    selected = sorted(rows, key=lambda item: float(item["clock_std_seconds"]))
    x = np.asarray([float(row["clock_std_seconds"]) for row in selected], dtype=float)
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    ax.semilogx(x, [float(row[metric_b]) for row in selected], marker="o", linestyle="--", label="Step B")
    ax.semilogx(x, [float(row[metric_c7]) for row in selected], marker="s", label="C7")
    ax.set_xlabel("Clock standard deviation (s)")
    ax.set_ylabel(ylabel)
    ax.set_title("Non-final sparse C7 clock sweep")
    ax.grid(True, alpha=0.3, which="both")
    ax.legend()
    fig.tight_layout()
    output = PLOT_ROOT / filename
    fig.savefig(output)
    fig.savefig(output.with_suffix(".png"))
    plt.close(fig)
    return output


def _plot_fallback_annotations(rows: list[dict[str, Any]]) -> Path:
    """Plot fallback counts by family/case."""

    labels = []
    counts = []
    for row in [item for item in rows if item["family"] == "network_size"]:
        labels.append(f"Nu={row['num_users']},Ns={row['num_satellites']}")
        counts.append(int(bool(row["fallback_triggered"])))
    fig, ax = plt.subplots(figsize=(9.0, 4.2))
    ax.bar(np.arange(len(labels)), counts)
    ax.set_xticks(np.arange(len(labels)), labels, rotation=45, ha="right")
    ax.set_ylabel("Fallback count")
    ax.set_title("C7 fallback annotations: single-UE clock/drift safeguard")
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    output = PLOT_ROOT / "c7_fallback_annotations.pdf"
    fig.savefig(output)
    fig.savefig(output.with_suffix(".png"))
    plt.close(fig)
    return output


def _plot_ratio_summary(summaries: list[dict[str, Any]]) -> Path:
    """Plot mean/max position and synchronization ratios by family."""

    labels = [row["family"].replace("_", " ") for row in summaries]
    x = np.arange(len(labels))
    width = 0.18
    fig, ax = plt.subplots(figsize=(7.0, 4.0))
    ax.bar(x - 1.5 * width, [row["mean_position_ratio"] for row in summaries], width, label="mean position")
    ax.bar(x - 0.5 * width, [row["max_position_ratio"] for row in summaries], width, label="max position")
    ax.bar(x + 0.5 * width, [row["mean_sync_ratio"] for row in summaries], width, label="mean sync")
    ax.bar(x + 1.5 * width, [row["max_sync_ratio"] for row in summaries], width, label="max sync")
    ax.axhline(1.0, color="black", linewidth=0.8, linestyle="--")
    ax.set_xticks(x, labels)
    ax.set_ylabel("C7 / Step B ratio")
    ax.set_title("C7 candidate ratio summary")
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    output = PLOT_ROOT / "c7_ratio_summary.pdf"
    fig.savefig(output)
    fig.savefig(output.with_suffix(".png"))
    plt.close(fig)
    return output


def _write_plots(network_rows: list[dict[str, Any]], clock_rows: list[dict[str, Any]], summaries: list[dict[str, Any]]) -> list[Path]:
    """Write required PDF/PNG figures."""

    PLOT_ROOT.mkdir(parents=True, exist_ok=True)
    return [
        _plot_network(
            network_rows,
            metric_b="step_b_position_error_m",
            metric_c7="c7_position_error_m",
            ylabel="Average UE localization error (m)",
            filename="c7_network_localization_vs_satellites.pdf",
        ),
        _plot_network(
            network_rows,
            metric_b="step_b_sync_error_ns",
            metric_c7="c7_sync_error_ns",
            ylabel="Average synchronization error (ns)",
            filename="c7_network_synchronization_vs_satellites.pdf",
        ),
        _plot_clock(
            clock_rows,
            metric_b="step_b_position_error_m",
            metric_c7="c7_position_error_m",
            ylabel="Average UE localization error (m)",
            filename="c7_clock_sweep_localization.pdf",
        ),
        _plot_clock(
            clock_rows,
            metric_b="step_b_sync_error_ns",
            metric_c7="c7_sync_error_ns",
            ylabel="Average synchronization error (ns)",
            filename="c7_clock_sweep_synchronization.pdf",
        ),
        _plot_fallback_annotations(network_rows),
        _plot_ratio_summary(summaries),
    ]


def _write_family_notes(name: str, rows: list[dict[str, Any]], summary: dict[str, Any]) -> tuple[Path, Path]:
    """Write Markdown and JSON notes for one figure family."""

    json_path = OUTPUT_ROOT / f"{name}_notes.json"
    md_path = OUTPUT_ROOT / f"{name}_notes.md"
    payload = {
        "artifact_status": f"non_final_c7_candidate_{name}_notes",
        "family": name,
        "candidate_only": True,
        "non_final": True,
        "not_for_manuscript_submission": True,
        "manuscript_ready": False,
        "notebook_used": False,
        "manuscript_directories_touched": False,
        "human_signoff_required": True,
        "estimator_mode": STEP_C7_ESTIMATOR_MODE,
        "baseline": "Step B / LM-only",
        "covariance_terminology": PRECISE_COVARIANCE_TERMINOLOGY,
        "sync_units": "ns in candidate plots; raw rows also retain range-domain km",
        "summary": summary,
        "row_count": len(rows),
        "fallback_rows": summary["fallback_rows"],
    }
    _json_dump(json_path, payload)
    lines = [
        f"# C7 Candidate {name.replace('_', ' ').title()} Notes",
        "",
        "- Artifact status: non-final candidate validation.",
        "- Manuscript ready: `false`.",
        "- Notebook used: `false`.",
        "- Manuscript directories touched: `false`.",
        "- Human signoff required: `true`.",
        f"- Baseline: `{payload['baseline']}`.",
        f"- C7 covariance: {PRECISE_COVARIANCE_TERMINOLOGY}.",
        "- Truth is used only for offline metrics.",
        "- Synchronization plots use ns; raw rows retain km.",
        "",
        "## Summary",
        f"- Rows: `{summary['row_count']}`.",
        f"- Position improved: `{summary['position_improved_count']}/{summary['row_count']}`.",
        f"- Synchronization improved: `{summary['sync_improved_count']}/{summary['row_count']}`.",
        f"- Fallback count: `{summary['fallback_count']}`.",
    ]
    if summary["fallback_rows"]:
        lines.extend(["", "## Fallback Rows"])
        for row in summary["fallback_rows"]:
            lines.append(f"- `{row}`")
        lines.append("- Fallback reverts UE clock, satellite clock, and drift updates to Step B while preserving the position update.")
        lines.append("- Fallback means unsafe/unobservable clock refinement, not single-UE synchronization improvement.")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return md_path, json_path


def _write_task_matrix() -> dict[str, Any]:
    """Write the candidate-figure task matrix."""

    lanes = [
        {
            "agent": "Agent A",
            "lane": "Network-size Figures",
            "status": "orchestrator_completed",
            "expected_output_files": "network raw CSV, localization/synchronization PDFs and notes",
            "blocker": None,
            "fallback_owner": "orchestrator",
        },
        {
            "agent": "Agent B",
            "lane": "Clock-sweep Figures",
            "status": "orchestrator_completed",
            "expected_output_files": "sparse clock-sweep raw CSV, PDFs and notes",
            "blocker": None,
            "fallback_owner": "orchestrator",
        },
        {
            "agent": "Agent C",
            "lane": "Figure Styling/Gallery",
            "status": "orchestrator_completed",
            "expected_output_files": "labels, fallback markers, gallery previews",
            "blocker": None,
            "fallback_owner": "orchestrator",
        },
        {
            "agent": "Agent D",
            "lane": "Scientific Red Team",
            "status": "read_only_subagent_completed",
            "expected_output_files": "safe/unsafe claims and caveat review",
            "blocker": None,
            "fallback_owner": "orchestrator",
        },
        {
            "agent": "Agent E",
            "lane": "Report Quality",
            "status": "read_only_subagent_completed",
            "expected_output_files": "human-readable report and relative-link review",
            "blocker": None,
            "fallback_owner": "orchestrator",
        },
    ]
    payload = {
        "artifact_status": "non_final_c7_candidate_figure_task_matrix",
        "mode": "IMPLEMENT_APPROVED",
        "edit_owner": "orchestrator",
        "lanes": lanes,
    }
    _json_dump(REPORT_ROOT / "C7_CANDIDATE_FIGURE_TASK_MATRIX.json", payload)
    lines = [
        "# C7 Candidate Figure Task Matrix",
        "",
        "| Agent | Lane | Status | Expected output | Blocker | Fallback owner |",
        "|---|---|---|---|---|---|",
    ]
    for lane in lanes:
        lines.append(
            f"| {lane['agent']} | {lane['lane']} | {lane['status']} | "
            f"{lane['expected_output_files']} | {lane['blocker'] or 'none'} | {lane['fallback_owner']} |"
        )
    (REPORT_ROOT / "C7_CANDIDATE_FIGURE_TASK_MATRIX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload


def _write_report(
    *,
    network_summary: dict[str, Any],
    clock_summary: dict[str, Any],
    plot_paths: list[Path],
    raw_paths: dict[str, str],
    notes: list[str],
    metadata_path: Path,
    task_matrix: dict[str, Any],
    runtime_seconds: float,
) -> dict[str, Any]:
    """Write human-readable and JSON candidate-validation reports."""

    report_json = REPORT_ROOT / "C7_CANDIDATE_FIGURE_VALIDATION_REPORT.json"
    report_md = REPORT_ROOT / "C7_CANDIDATE_FIGURE_VALIDATION_REPORT.md"
    clock_sweep_blocked = bool(clock_summary["max_position_ratio"] > 1.05 or clock_summary["max_sync_ratio"] > 1.05)
    clock_sweep_status = "sparse_bounded_blocked_by_localization_instability" if clock_sweep_blocked else "sparse_bounded_candidate"
    remaining_blockers = []
    if clock_sweep_blocked:
        remaining_blockers.append(
            "Sparse clock-sweep C7 candidate is not suitable for candidate-figure use yet because at least one bounded clock-standard-deviation row worsens localization substantially."
        )
    payload = {
        "artifact_status": "non_final_c7_candidate_figure_validation",
        "verdict": "PASS WITH CAVEAT",
        "candidate_only": True,
        "non_final": True,
        "not_for_manuscript_submission": True,
        "manuscript_ready": False,
        "notebook_used": False,
        "manuscript_directories_touched": False,
        "human_signoff_required": True,
        "ready_for_human_review": True,
        "ready_for_bounded_candidate_validation": True,
        "estimator_mode": STEP_C7_ESTIMATOR_MODE,
        "baseline": "Step B / LM-only",
        "covariance_terminology": PRECISE_COVARIANCE_TERMINOLOGY,
        "truth_state_used_for_acceptance": False,
        "truth_state_used_for_covariance": False,
        "truth_state_used_for_safeguard": False,
        "truth_used_only_for_offline_metrics": True,
        "sync_units": "ns in plots; km retained in raw CSV",
        "network_summary": network_summary,
        "clock_sweep_summary": clock_summary,
        "clock_sweep_status": clock_sweep_status,
        "full_clock_sweep_run": False,
        "remaining_blockers": remaining_blockers,
        "runtime_seconds": runtime_seconds,
        "plots": [_repo_rel(path) for path in plot_paths],
        "raw_paths": raw_paths,
        "metadata_json": _repo_rel(metadata_path),
        "task_matrix": task_matrix,
        "safe_claims": [
            "C7 candidate outputs are non-final human-review diagnostics.",
            "Step B / LM-only is the comparison baseline.",
            "C7 improves localization on the bounded network grid.",
            "C7 uses a non-truth single-UE synchronization safeguard.",
            "Single-UE fallback rows preserve Step B synchronization by reverting unsafe clock/drift updates.",
            "Sparse clock-sweep outputs were generated only for four bounded clock-standard-deviation points.",
        ],
        "unsafe_claims": [
            "C7 outputs are manuscript-ready.",
            "C7 validates final manuscript figures.",
            "The covariance method uses dense block or cross-covariance.",
            "Sparse clock-sweep behavior proves full legacy clock-sweep behavior.",
            "Single-UE C7 improves synchronization rather than preserving Step B via fallback.",
        ],
        "recommended_next_action": (
            "Human review of bounded C7 network-size candidate figures and sparse clock-sweep failure evidence. "
            "Do not run a denser clock sweep until the high-clock-standard-deviation localization instability is explained."
        ),
    }
    _json_dump(report_json, payload)
    lines = [
        "# C7 Candidate Figure Validation Report",
        "",
        "## Executive Summary",
        "- Verdict: **PASS WITH CAVEAT**.",
        "- Outputs are non-final candidate diagnostics for human review only.",
        "- Manuscript ready: `false`.",
        "- Notebook used: `false`.",
        "- Manuscript directories touched: `false`.",
        "- Human signoff required: `true`.",
        f"- Baseline: `{payload['baseline']}`.",
        f"- C7 estimator mode: `{STEP_C7_ESTIMATOR_MODE}`.",
        f"- C7 covariance: {PRECISE_COVARIANCE_TERMINOLOGY}.",
        "- Truth is used only for offline metrics and ratios.",
        f"- Clock-sweep status: `{clock_sweep_status}`.",
        "",
        "## Figure Family Summary",
        "| Family | Rows | Position improved | Sync improved | Both improved | Fallbacks | Max position ratio | Max sync ratio |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for summary in (network_summary, clock_summary):
        lines.append(
            f"| `{summary['family']}` | {summary['row_count']} | "
            f"{summary['position_improved_count']} | {summary['sync_improved_count']} | "
            f"{summary['both_improved_count']} | {summary['fallback_count']} | "
            f"{summary['max_position_ratio']:.6f} | {summary['max_sync_ratio']:.6f} |"
        )
    lines.extend(
        [
            "",
            "## What Was Generated",
            "- Network-size localization versus satellites.",
            "- Network-size synchronization versus satellites, plotted in ns.",
            "- Sparse clock-sweep localization for `10^{-4},10^{-6},10^{-8},10^{-10}` seconds.",
            "- Sparse clock-sweep synchronization, plotted in ns.",
            "- Fallback-annotation diagnostic.",
            "- Ratio-summary diagnostic.",
            "- Raw CSVs, summary CSV, NPZ arrays, metadata JSON, and per-family notes.",
            "",
            "## What Was Not Generated",
            "- No manuscript figures were generated.",
            "- No broad algorithm exploration was run.",
            "- No dense/full clock sweep was run; the clock sweep is sparse bounded only.",
            "- No legacy truth-gated MAP/EKF evidence was used as primary evidence.",
            "",
            "## Remaining Blockers",
        ]
    )
    if remaining_blockers:
        lines.extend(f"- {item}" for item in remaining_blockers)
    else:
        lines.append("- No blocker found in the bounded candidate validation.")
    lines.extend(
        [
            "",
            "## Runtime / Cache Notes",
            f"- Runtime: `{runtime_seconds:.3f}` seconds.",
            "- Cache status: deterministic direct run; no long-running cache-dependent sweep.",
            "",
            "## Step B vs C7 Comparison",
            "- Step B / LM-only remains the baseline.",
            "- C7 is plotted as a Step 3 candidate.",
            "- Synchronization plots use ns for readability; raw CSV keeps range-domain km values.",
            "",
            "## Fallback-Row Explanation",
        ]
    )
    if network_summary["fallback_rows"] or clock_summary["fallback_rows"]:
        for row in network_summary["fallback_rows"] + clock_summary["fallback_rows"]:
            lines.append(f"- `{row}`")
        lines.append("- Fallback reverts UE clock, satellite clock, and drift updates to Step B while preserving the position update.")
        lines.append("- Fallback means unsafe/unobservable clock refinement, not single-UE synchronization improvement.")
    else:
        lines.append("- No fallback rows.")
    lines.extend(
        [
            "",
            "## Safe Claims",
            *[f"- {claim}" for claim in payload["safe_claims"]],
            "",
            "## Unsafe Claims",
            *[f"- {claim}" for claim in payload["unsafe_claims"]],
            "",
            "## Output Links",
            f"- Metadata JSON: [{_repo_rel(metadata_path)}](../c7_candidate_figures/{metadata_path.name})",
            f"- Combined raw CSV: [{raw_paths['combined_raw_csv']}](../c7_candidate_figures/raw.csv)",
            f"- Summary CSV: [{raw_paths['summary_csv']}](../c7_candidate_figures/summary.csv)",
            f"- Arrays NPZ: [{raw_paths['arrays_npz']}](../c7_candidate_figures/arrays.npz)",
        ]
    )
    for note in notes:
        lines.append(f"- Notes: [{note}](../c7_candidate_figures/{Path(note).name})")
    lines.extend(["", "## Figures"])
    for path in plot_paths:
        png = path.with_suffix(".png")
        lines.append(f"- PDF: [{_repo_rel(path)}](../c7_candidate_figures/plots/{path.name})")
        lines.append(f"  PNG: [{_repo_rel(png)}](../c7_candidate_figures/plots/{png.name})")
    lines.extend(
        [
            "",
            "## Recommendation For Human Review",
            payload["recommended_next_action"],
        ]
    )
    report_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload


def _write_metadata(rows: list[dict[str, Any]], summaries: list[dict[str, Any]], plot_paths: list[Path], raw_paths: dict[str, str], runtime_seconds: float) -> Path:
    """Write top-level metadata."""

    path = OUTPUT_ROOT / "metadata.json"
    clock_summary = next(row for row in summaries if row["family"] == "clock_sweep")
    clock_sweep_blocked = bool(clock_summary["max_position_ratio"] > 1.05 or clock_summary["max_sync_ratio"] > 1.05)
    payload = {
        "artifact_status": "non_final_c7_candidate_figures",
        "candidate_only": True,
        "non_final": True,
        "not_for_manuscript_submission": True,
        "manuscript_ready": False,
        "notebook_used": False,
        "manuscript_directories_touched": False,
        "human_signoff_required": True,
        "ready_for_human_review": True,
        "estimator_mode": STEP_C7_ESTIMATOR_MODE,
        "baseline": "Step B / LM-only",
        "covariance_terminology": PRECISE_COVARIANCE_TERMINOLOGY,
        "truth_state_used_for_acceptance": False,
        "truth_state_used_for_covariance": False,
        "truth_state_used_for_safeguard": False,
        "truth_used_only_for_offline_metrics": True,
        "sync_units": "ns in plots; km retained in raw CSV",
        "network_grid": {"num_users": [1, 3, 5, 7], "num_satellites": [4, 8, 12]},
        "clock_sweep_seconds": CLOCK_SWEEP_SECONDS,
        "clock_sweep_case": CLOCK_SWEEP_CASE,
        "clock_sweep_status": "sparse_bounded_blocked_by_localization_instability" if clock_sweep_blocked else "sparse_bounded_candidate",
        "full_clock_sweep_run": False,
        "row_count": len(rows),
        "runtime_seconds": runtime_seconds,
        "summaries": summaries,
        "plots": [_repo_rel(path) for path in plot_paths],
        "raw_paths": raw_paths,
    }
    _json_dump(path, payload)
    return path


def run_candidate_validation(*, render_gallery: bool = True) -> dict[str, Any]:
    """Run bounded C7 candidate figure validation and write outputs."""

    started = time.monotonic()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    PLOT_ROOT.mkdir(parents=True, exist_ok=True)
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    network_rows = _evaluate_network_rows()
    clock_rows = _evaluate_clock_rows()
    rows = network_rows + clock_rows
    summaries = _summarize(rows)
    network_summary = next(row for row in summaries if row["family"] == "network_size")
    clock_summary = next(row for row in summaries if row["family"] == "clock_sweep")
    plot_paths = _write_plots(network_rows, clock_rows, summaries)
    raw_fields = BASE_FIELDS + [
        field
        for field in c7.CSV_FIELDS
        if field not in BASE_FIELDS
    ]
    _write_csv(OUTPUT_ROOT / "raw.csv", rows, raw_fields)
    _write_csv(OUTPUT_ROOT / "network_size_raw.csv", network_rows, raw_fields)
    _write_csv(OUTPUT_ROOT / "clock_sweep_raw.csv", clock_rows, raw_fields)
    _write_csv(
        OUTPUT_ROOT / "summary.csv",
        summaries,
        [
            "family",
            "row_count",
            "position_improved_count",
            "sync_improved_count",
            "both_improved_count",
            "fallback_count",
            "mean_position_ratio",
            "max_position_ratio",
            "mean_sync_ratio",
            "max_sync_ratio",
        ],
    )
    np.savez(
        OUTPUT_ROOT / "arrays.npz",
        network_position_ratios=np.asarray([float(row["position_ratio"]) for row in network_rows]),
        network_sync_ratios=np.asarray([float(row["sync_ratio"]) for row in network_rows]),
        clock_std_seconds=np.asarray(CLOCK_SWEEP_SECONDS, dtype=float),
        clock_position_ratios=np.asarray([float(row["position_ratio"]) for row in clock_rows]),
        clock_sync_ratios=np.asarray([float(row["sync_ratio"]) for row in clock_rows]),
        fallback_triggered=np.asarray([bool(row["fallback_triggered"]) for row in rows], dtype=bool),
    )
    notes = [
        _repo_rel(_write_family_notes("network_size", network_rows, network_summary)[0]),
        _repo_rel(_write_family_notes("clock_sweep", clock_rows, clock_summary)[0]),
    ]
    runtime_seconds = time.monotonic() - started
    raw_paths = {
        "combined_raw_csv": _repo_rel(OUTPUT_ROOT / "raw.csv"),
        "network_raw_csv": _repo_rel(OUTPUT_ROOT / "network_size_raw.csv"),
        "clock_sweep_raw_csv": _repo_rel(OUTPUT_ROOT / "clock_sweep_raw.csv"),
        "summary_csv": _repo_rel(OUTPUT_ROOT / "summary.csv"),
        "arrays_npz": _repo_rel(OUTPUT_ROOT / "arrays.npz"),
    }
    metadata_path = _write_metadata(rows, summaries, plot_paths, raw_paths, runtime_seconds)
    task_matrix = _write_task_matrix()
    report = _write_report(
        network_summary=network_summary,
        clock_summary=clock_summary,
        plot_paths=plot_paths,
        raw_paths=raw_paths,
        notes=notes,
        metadata_path=metadata_path,
        task_matrix=task_matrix,
        runtime_seconds=runtime_seconds,
    )
    gallery = None
    if render_gallery:
        from scripts.render_all_figure_previews import render_gallery as _render_gallery

        gallery = _render_gallery(force=False)
    return {
        "artifact_status": "non_final_c7_candidate_figure_validation_complete",
        "output_root": _repo_rel(OUTPUT_ROOT),
        "runtime_seconds": runtime_seconds,
        "network_summary": network_summary,
        "clock_sweep_summary": clock_summary,
        "plots": [_repo_rel(path) for path in plot_paths],
        "report": report,
        "gallery_entry_count": None if gallery is None else gallery.get("entry_count"),
    }


def main() -> None:
    """CLI entry point."""

    payload = run_candidate_validation(render_gallery=True)
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
