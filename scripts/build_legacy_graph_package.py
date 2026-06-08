"""Build a canonical human-readable graph package under ``outputs/``."""

from __future__ import annotations

import csv
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


SAT_SIM_ROOT = Path(__file__).resolve().parents[1]
if str(SAT_SIM_ROOT) not in sys.path:
    sys.path.insert(0, str(SAT_SIM_ROOT))

OUTPUTS = SAT_SIM_ROOT / "outputs"
REPORTS = OUTPUTS / "reports"
LOS_ROOT = OUTPUTS / "legacy_replay" / "crlb_los"
NLOS_ROOT = OUTPUTS / "legacy_replay" / "crlb_nlos"


def _read_matrix(path: Path) -> tuple[np.ndarray, list[int], list[int]]:
    """Read legacy CRLB matrix CSV."""

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        sat_values = [int(item) for item in header[1:]]
        user_values = []
        rows = []
        for row in reader:
            if not row:
                continue
            user_values.append(int(row[0]))
            rows.append([float(item) for item in row[1:]])
    return np.asarray(rows, dtype=float), user_values, sat_values


def _plot_crlb(matrix: np.ndarray, users: list[int], sats: list[int], output: Path, ylabel: str) -> None:
    """Write corrected CRLB plot with readable legends."""

    fig, ax = plt.subplots(figsize=(4.4, 3.2), dpi=240)
    x = np.asarray(sats, dtype=float)
    for index, num_users in enumerate(users):
        label = (
            r"Without cooperation ($N_\mathrm{u}=1$)"
            if index == 0 and num_users == 1
            else rf"JCLS ($N_\mathrm{{u}}={num_users}$)"
        )
        ax.plot(x, matrix[index], marker="o", label=label)
    ax.set_xlabel("Number of satellites")
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best", fontsize=7, frameon=True)
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output)
    plt.close(fig)


def build_los_crlb() -> dict[str, Any]:
    """Build corrected LOS CRLB plots from legacy replay matrices."""

    src = SAT_SIM_ROOT / "v24_notebook_regression_outputs" / "executed_legacy" / "crlb_replay"
    LOS_ROOT.mkdir(parents=True, exist_ok=True)
    loc, users, sats = _read_matrix(src / "legacy_pos_plot_y_m.csv")
    sync, _, _ = _read_matrix(src / "legacy_sync_plot_y_ns.csv")
    pos_pdf = LOS_ROOT / "pos_crlb_0dB_0dB.pdf"
    sync_pdf = LOS_ROOT / "sync_crlb_0dB_0dB.pdf"
    _plot_crlb(loc, users, sats, pos_pdf, "Average 3D UE localization CRLB [m]")
    _plot_crlb(sync, users, sats, sync_pdf, "Average synchronization CRLB [ns]")
    shutil.copy2(src / "legacy_pos_plot_y_m.csv", LOS_ROOT / "legacy_pos_plot_y_m.csv")
    shutil.copy2(src / "legacy_sync_plot_y_ns.csv", LOS_ROOT / "legacy_sync_plot_y_ns.csv")
    np.savez(LOS_ROOT / "legacy_crlb_los_arrays.npz", localization_m=loc, synchronization_ns=sync, users=users, satellites=sats)
    report = {
        "artifact_status": "non_final_legacy_crlb_los_replay_corrected_legend",
        "status": "legacy_replayed_unverified_match",
        "legacy_replay": True,
        "manuscript_ready": False,
        "los_nlos": "LOS",
        "noise_fim_model": "legacy notebook LOS CRLB replay matrices; plots regenerated with corrected legends only",
        "output_root": str(LOS_ROOT.relative_to(SAT_SIM_ROOT)).replace("\\", "/"),
        "plot_outputs": [str(pos_pdf.relative_to(SAT_SIM_ROOT)).replace("\\", "/"), str(sync_pdf.relative_to(SAT_SIM_ROOT)).replace("\\", "/")],
        "raw_outputs": [
            str((LOS_ROOT / "legacy_pos_plot_y_m.csv").relative_to(SAT_SIM_ROOT)).replace("\\", "/"),
            str((LOS_ROOT / "legacy_sync_plot_y_ns.csv").relative_to(SAT_SIM_ROOT)).replace("\\", "/"),
            str((LOS_ROOT / "legacy_crlb_los_arrays.npz").relative_to(SAT_SIM_ROOT)).replace("\\", "/"),
        ],
        "caveats": [
            "Legacy all-clock/post-hoc CRLB path preserved as provenance.",
            "Legend and plot readability corrected; underlying CRLB numbers are not V24-clean.",
            "First legend row follows the legacy notebook's single-UE/no-sidelink convention.",
        ],
    }
    (LOS_ROOT / "crlb_los_metadata.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    md = [
        "# Corrected LOS CRLB Replay Report",
        "",
        "## Executive Summary",
        "The LOS CRLB replay matrices were preserved and replotted with readable legends. These plots are legacy replay provenance and are not manuscript-ready.",
        "",
        "## Plots",
        "- [Localization CRLB PDF](../legacy_replay/crlb_los/pos_crlb_0dB_0dB.pdf)",
        "- [Synchronization CRLB PDF](../legacy_replay/crlb_los/sync_crlb_0dB_0dB.pdf)",
        "",
        "## Caveats",
        *[f"- {item}" for item in report["caveats"]],
    ]
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "CRLB_LOS_REPLAY_REPORT.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (REPORTS / "CRLB_LOS_REPLAY_REPORT.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return report


def build_nlos_failure_report() -> dict[str, Any]:
    """Write a precise NLOS CRLB failure report."""

    NLOS_ROOT.mkdir(parents=True, exist_ok=True)
    report = {
        "artifact_status": "non_final_nlos_crlb_failure_report",
        "status": "nlos_crlb_not_generated",
        "manuscript_ready": False,
        "los_nlos": "NLOS",
        "failure_reason": "No executable legacy Rayleigh/NLOS CRLB path or package score-covariance NLOS FIM path exists in the current merged repository. Search found only Gaussian/Rician FIM helpers.",
        "dl_sl_nlos_scope": "not generated",
        "noise_fim_model": "none; generation blocked to avoid faking NLOS CRLB curves",
        "output_root": str(NLOS_ROOT.relative_to(SAT_SIM_ROOT)).replace("\\", "/"),
        "required_next_step": "Implement and test a defensible NLOS score-covariance/FIM path before generating NLOS CRLB figures.",
    }
    (NLOS_ROOT / "crlb_nlos_failure_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    md = [
        "# NLOS CRLB Report",
        "",
        "## Executive Summary",
        "NLOS CRLB figures were not generated. The current repository does not contain a defensible executable NLOS/Rayleigh CRLB path.",
        "",
        f"- Status: `{report['status']}`",
        f"- Manuscript ready: `{report['manuscript_ready']}`",
        "",
        "## Failure Reason",
        report["failure_reason"],
        "",
        "## Next Step",
        report["required_next_step"],
    ]
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "CRLB_NLOS_REPORT.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (REPORTS / "CRLB_NLOS_REPORT.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return report


def copy_clock_sweep() -> dict[str, Any]:
    """Copy full clock-sweep replay into canonical outputs."""

    src = SAT_SIM_ROOT / "v24_notebook_regression_outputs" / "executed_legacy" / "clock_sweep_replay_full"
    dst = OUTPUTS / "legacy_replay" / "clock_sweep_full"
    dst.mkdir(parents=True, exist_ok=True)
    for name in ["pos_vary_clock.pdf", "sync_vary_clock.pdf", "legacy_clock_sweep_raw.csv", "legacy_clock_sweep_summary.csv", "legacy_clock_sweep_arrays.npz", "legacy_clock_sweep_metadata.json", "legacy_clock_sweep_metadata.md"]:
        if (src / name).exists():
            shutil.copy2(src / name, dst / name)
    return {
        "status": "legacy_full_replayed_unverified_match",
        "output_root": str(dst.relative_to(SAT_SIM_ROOT)).replace("\\", "/"),
        "manuscript_ready": False,
    }


def build_output_index(status_report: dict[str, Any]) -> None:
    """Write canonical output index."""

    index = {
        "artifact_status": "canonical_output_index",
        "folders": [
            {"path": "outputs/gallery", "contains": "PNG previews and browsable Markdown/HTML/JSON gallery", "safe_to_cite": False, "safe_to_delete_regenerate": True},
            {"path": "outputs/legacy_replay", "contains": "legacy-compatible replay graphs and raw diagnostics", "safe_to_cite": False, "safe_to_delete_regenerate": True},
            {"path": "outputs/package_diagnostic", "contains": "package diagnostic aliases/status only", "safe_to_cite": False, "safe_to_delete_regenerate": True},
            {"path": "outputs/manuscript_candidate", "contains": "candidate-only graph provenance/status", "safe_to_cite": False, "safe_to_delete_regenerate": True},
            {"path": "outputs/human_review", "contains": "human-review diagnostics/status", "safe_to_cite": False, "safe_to_delete_regenerate": True},
            {"path": "outputs/migration_baseline", "contains": "frozen legacy behavior baseline for controlled migration comparisons", "safe_to_cite": False, "safe_to_delete_regenerate": True},
            {"path": "outputs/migration_ladder", "contains": "controlled legacy-to-V24 migration step outputs", "safe_to_cite": False, "safe_to_delete_regenerate": True},
            {"path": "outputs/cache", "contains": "validated replay cache/checkpoint entries", "safe_to_cite": False, "safe_to_delete_regenerate": True},
            {"path": "outputs/reports", "contains": "human-readable reports and machine JSON", "safe_to_cite": False, "safe_to_delete_regenerate": True},
        ],
        "legacy_provenance_paths": [
            "v24_notebook_regression_outputs",
            "v24_plot_gallery",
            "v24_figure_outputs",
            "v24_manuscript_candidate_outputs",
            "v24_human_review_outputs",
        ],
        "current_best_graphs": status_report["current_best_graphs"],
    }
    (OUTPUTS / "OUTPUT_INDEX.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    lines = [
        "# Output Index",
        "",
        "## Executive Summary",
        "Canonical graph-package outputs now live under `outputs/`. Existing `v24_*` folders remain as legacy/provenance paths.",
        "",
        "## Folders",
        "| Folder | Contains | Safe to cite? | Safe to delete/regenerate? |",
        "|---|---|---:|---:|",
    ]
    for folder in index["folders"]:
        lines.append(f"| `{folder['path']}` | {folder['contains']} | {folder['safe_to_cite']} | {folder['safe_to_delete_regenerate']} |")
    lines += ["", "## Current Best Graphs"]
    for graph in index["current_best_graphs"]:
        lines.append(f"- [{graph['name']}]({graph['path'].replace('outputs/', '')}) - {graph['status']}")
    lines += ["", "## Legacy/Provenance Paths"]
    for path in index["legacy_provenance_paths"]:
        lines.append(f"- `{path}` remains for provenance; prefer canonical `outputs/` links for review.")
    (OUTPUTS / "OUTPUT_INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_current_graph_status(los: dict[str, Any], nlos: dict[str, Any], clock: dict[str, Any]) -> dict[str, Any]:
    """Write current graph status report."""

    network_mode = "smoke"
    network_root = OUTPUTS / "legacy_replay" / "network_size"
    medium_root = OUTPUTS / "legacy_replay" / "network_size_medium"
    full_root = OUTPUTS / "legacy_replay" / "network_size_full"
    if (full_root / "pos_vary_ues.pdf").exists() and (full_root / "sync_vary_ues.pdf").exists():
        network_root = full_root
        network_mode = "full"
    elif (medium_root / "pos_vary_ues.pdf").exists() and (medium_root / "sync_vary_ues.pdf").exists():
        network_root = medium_root
        network_mode = "medium"
    network_graphs = []
    if (network_root / "pos_vary_ues.pdf").exists() and (network_root / "sync_vary_ues.pdf").exists():
        network_rel = str(network_root.relative_to(SAT_SIM_ROOT)).replace("\\", "/")
        network_label = "full" if network_mode == "full" else "medium" if network_mode == "medium" else "bounded smoke"
        network_graphs = [
            {
                "name": f"Legacy-compatible network-size localization {network_label} replay",
                "path": f"{network_rel}/pos_vary_ues.pdf",
                "status": f"{network_label} legacy replay, unverified match",
            },
            {
                "name": f"Legacy-compatible network-size synchronization {network_label} replay",
                "path": f"{network_rel}/sync_vary_ues.pdf",
                "status": f"{network_label} legacy replay, unverified match",
            },
        ]
    status = {
        "artifact_status": "current_graph_status",
        "overall": "legacy-compatible graphs are best available for visual review; none are manuscript-ready",
        "current_best_graphs": [
            {"name": "Corrected LOS localization CRLB replay", "path": "outputs/legacy_replay/crlb_los/pos_crlb_0dB_0dB.pdf", "status": "legacy replay, not V24-clean"},
            {"name": "Corrected LOS synchronization CRLB replay", "path": "outputs/legacy_replay/crlb_los/sync_crlb_0dB_0dB.pdf", "status": "legacy replay, not V24-clean"},
            {"name": "Full legacy clock-sweep localization replay", "path": "outputs/legacy_replay/clock_sweep_full/pos_vary_clock.pdf", "status": "legacy replay, unverified match"},
            {"name": "Full legacy clock-sweep synchronization replay", "path": "outputs/legacy_replay/clock_sweep_full/sync_vary_clock.pdf", "status": "legacy replay, unverified match"},
            *network_graphs,
        ],
        "suspect_graphs": [
            {"path": "v24_human_review_outputs", "reason": "package-native human-review Fig. 4--7 path can degrade at later JCLS stages; preserve as suspect diagnostics only"},
            {"path": "v24_figure_outputs", "reason": "package-native diagnostics are not legacy-compatible and not best available"},
        ],
        "nlos_status": nlos,
        "warnings": [
            "No graph is manuscript-ready.",
            "Legacy CRLB is all-clock/post-hoc and not V24-clean.",
            "Legacy estimator replays use truth-gated acceptance behavior and all-clock synchronization metrics.",
            "Controlled migration ladder outputs preserve legacy behavior first; use them to isolate breaking corrections, not as final figures.",
        ],
    }
    migration_root = OUTPUTS / "migration_ladder" / "step_a_no_display_smoothing" / "medium"
    if (migration_root / "pos_vary_ues.pdf").exists() and (migration_root / "sync_vary_ues.pdf").exists():
        status["current_best_graphs"].extend(
            [
                {
                    "name": "Migration Step A localization medium replay",
                    "path": "outputs/migration_ladder/step_a_no_display_smoothing/medium/pos_vary_ues.pdf",
                    "status": "controlled migration Step A, non-final",
                },
                {
                    "name": "Migration Step A synchronization medium replay",
                    "path": "outputs/migration_ladder/step_a_no_display_smoothing/medium/sync_vary_ues.pdf",
                    "status": "controlled migration Step A, non-final",
                },
            ]
        )
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "CURRENT_GRAPH_STATUS.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
    md = [
        "# Current Graph Status",
        "",
        "## Executive Summary",
        status["overall"],
        "",
        "## Best Available Graphs for Human Review",
    ]
    for graph in status["current_best_graphs"]:
        md.append(f"- [{graph['name']}](../{graph['path'].replace('outputs/', '')}) - {graph['status']}")
    md += ["", "## Suspect/Broken Graphs"]
    for graph in status["suspect_graphs"]:
        md.append(f"- `{graph['path']}`: {graph['reason']}")
    md += ["", "## Warnings"]
    md.extend(f"- {item}" for item in status["warnings"])
    (REPORTS / "CURRENT_GRAPH_STATUS.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return status


def main() -> int:
    los = build_los_crlb()
    nlos = build_nlos_failure_report()
    clock = copy_clock_sweep()
    status = build_current_graph_status(los, nlos, clock)
    build_output_index(status)
    print(json.dumps({"status": "built", "outputs": str(OUTPUTS.relative_to(SAT_SIM_ROOT))}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
