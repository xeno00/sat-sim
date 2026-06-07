"""Safely replay the legacy notebook CRLB figure pair.

This script parses ``JCLS_Simulation.ipynb`` and executes only selected class
and helper definitions needed for the CRLB figure pair. It does not execute
Colab setup, workspace pickle save/load, notebook figure folders, PSFrag, or
the original notebook source as a whole.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from scipy.ndimage import gaussian_filter  # noqa: E402


SAT_SIM_ROOT = Path(__file__).resolve().parents[1]
if str(SAT_SIM_ROOT) not in sys.path:
    sys.path.insert(0, str(SAT_SIM_ROOT))
REPO_ROOT = SAT_SIM_ROOT.parent

NOTEBOOK_PATH = SAT_SIM_ROOT / "JCLS_Simulation.ipynb"
OUTPUT_ROOT = SAT_SIM_ROOT / "v24_notebook_regression_outputs" / "executed_legacy" / "crlb_replay"
TARGET_FIGURES = ("pos_crlb_0dB_0dB.pdf", "sync_crlb_0dB_0dB.pdf")


class _ProgressBar:
    """Tiny tqdm-compatible progress placeholder for deterministic replay."""

    def __init__(self, total: int, desc: str = "") -> None:
        self.total = total
        self.desc = desc
        self.count = 0

    def set_description(self, desc: str) -> None:
        self.desc = desc

    def update(self, count: int) -> None:
        self.count += count

    def close(self) -> None:
        return None


def _tqdm(*, total: int, desc: str = "") -> _ProgressBar:
    """Return a deterministic no-output progress bar."""

    return _ProgressBar(total=total, desc=desc)


def _load_notebook() -> dict[str, Any]:
    """Load the notebook JSON without mutating it."""

    return json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))


def _code_cells() -> list[tuple[int, str]]:
    """Return zero-based notebook code-cell sources."""

    notebook = _load_notebook()
    return [
        (index, "".join(cell.get("source", [])))
        for index, cell in enumerate(notebook["cells"])
        if cell.get("cell_type") == "code"
    ]


def _find_cell_containing(needle: str) -> tuple[int, str]:
    """Return the first code cell containing ``needle``."""

    for index, source in _code_cells():
        if needle in source:
            return index, source
    raise ValueError(f"Could not find notebook cell containing {needle!r}.")


def _safe_crlb_helper_source() -> tuple[int, str]:
    """Return CRLB helper source without global notebook execution lines."""

    cell_index, source = _find_cell_containing("def generate_FIM_data")
    lines = source.splitlines()
    safe_lines = []
    for line in lines:
        if line.startswith("#num_satellites_range"):
            break
        safe_lines.append(line)
    return cell_index, "\n".join(safe_lines)


def _safe_fit_source() -> tuple[int, str]:
    """Return the curve-fit helper cell source."""

    return _find_cell_containing("def fit_and_resample_power_law")


def _selected_class_sources() -> list[tuple[int, str, str]]:
    """Return selected safe class definition cells."""

    targets = [
        ("Node", "class Node"),
        ("User", "class User"),
        ("Satellite", "class Satellite"),
        ("Datalink", "class Datalink"),
        ("Scenario", "class Scenario"),
    ]
    selected: list[tuple[int, str, str]] = []
    for name, needle in targets:
        index, source = _find_cell_containing(needle)
        selected.append((index, name, source))
    return selected


def _execute_legacy_namespace() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Execute only selected legacy class/helper definitions."""

    import itertools
    from copy import copy

    import sympy as sp
    from scipy.optimize import curve_fit
    from scipy.stats import rv_continuous

    namespace: dict[str, Any] = {
        "np": np,
        "sp": sp,
        "itertools": itertools,
        "copy": copy,
        "rv_continuous": rv_continuous,
        "curve_fit": curve_fit,
        "gaussian_filter": gaussian_filter,
        "tqdm": _tqdm,
    }
    executed: list[dict[str, Any]] = []
    for cell_index, name, source in _selected_class_sources():
        exec(compile(source, f"{NOTEBOOK_PATH}:cell{cell_index}", "exec"), namespace)
        executed.append(
            {
                "cell_index_zero_based": cell_index,
                "cell_number_one_based": cell_index + 1,
                "kind": "class_definition",
                "name": name,
            }
        )
    fit_index, fit_source = _safe_fit_source()
    exec(compile(fit_source, f"{NOTEBOOK_PATH}:cell{fit_index}", "exec"), namespace)
    executed.append(
        {
            "cell_index_zero_based": fit_index,
            "cell_number_one_based": fit_index + 1,
            "kind": "fit_helper_definitions",
            "name": "fit_and_resample_power_law",
        }
    )
    crlb_index, crlb_source = _safe_crlb_helper_source()
    exec(compile(crlb_source, f"{NOTEBOOK_PATH}:cell{crlb_index}", "exec"), namespace)
    executed.append(
        {
            "cell_index_zero_based": crlb_index,
            "cell_number_one_based": crlb_index + 1,
            "kind": "crlb_helper_definitions",
            "name": "generate_FIM_data",
            "global_invocation_stripped": True,
        }
    )
    return namespace, executed


def _legacy_plot(
    x_values: np.ndarray,
    y_series: list[np.ndarray],
    labels: list[str],
    *,
    xlabel: str,
    ylabel: str,
    title: str,
    output_path: Path,
    log_y: bool,
    legend_loc: str,
) -> None:
    """Write a safe approximation of the legacy IEEE scatter plot."""

    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.size": 10,
            "axes.labelsize": 10,
            "legend.fontsize": 6,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "lines.linewidth": 1,
            "lines.markersize": 5,
            "text.usetex": False,
            "pdf.fonttype": 42,
        }
    )
    fig = plt.figure(dpi=300, figsize=(3.5, 3), constrained_layout=False)
    ax = fig.add_axes([0.2, 0.167, 0.75, 0.75])
    markers = ["o", "s", "^", "v", "d", "*", "x", "+"]
    linestyles = ["-", "--", ":", "-."]
    for index, values in enumerate(y_series):
        ax.scatter(
            x_values,
            values,
            s=12,
            marker=markers[index % len(markers)],
            facecolor="white",
            label=labels[index],
            zorder=3,
            clip_on=False,
        )
        ax.plot(
            x_values,
            values,
            linestyle=linestyles[index % len(linestyles)],
            linewidth=1.0,
            zorder=2,
        )
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_xticks([1, 3, 5, 7, 9, 11, 13, 15])
    ax.set_xlim(right=15)
    if log_y:
        ax.set_yscale("log")
    if legend_loc == "below upper right":
        ax.legend(loc="upper right", bbox_to_anchor=(1, 0.9), frameon=True, edgecolor="black")
    else:
        ax.legend(loc=legend_loc, frameon=True, edgecolor="black")
    ax.tick_params(which="both", direction="in", top=True, bottom=True, left=True, right=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, format="pdf")
    plt.close(fig)


def _hash_file(path: Path) -> str | None:
    """Return a SHA256 hash for an existing file."""

    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _find_existing_artifacts() -> list[dict[str, Any]]:
    """Inventory existing target CRLB artifacts without modifying them."""

    artifacts = []
    for figure in TARGET_FIGURES:
        matches = [
            path
            for path in REPO_ROOT.rglob(figure)
            if OUTPUT_ROOT not in path.parents
        ]
        artifacts.append(
            {
                "figure": figure,
                "matches": [
                    {
                        "path": str(path.relative_to(REPO_ROOT)),
                        "size_bytes": path.stat().st_size,
                        "sha256": _hash_file(path),
                    }
                    for path in matches
                ],
                "match_count": len(matches),
            }
        )
    return artifacts


def _write_csv_matrix(path: Path, row_labels: list[int], column_labels: list[int], matrix: np.ndarray) -> None:
    """Write a matrix as CSV with row/column labels."""

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["num_users\\num_satellites", *column_labels])
        for row_label, row in zip(row_labels, matrix):
            writer.writerow([row_label, *[float(value) for value in row]])


def replay_legacy_crlb_figures(*, output_root: Path = OUTPUT_ROOT) -> dict[str, Any]:
    """Replay the legacy notebook CRLB figure pair into ``output_root``."""

    output_root.mkdir(parents=True, exist_ok=True)
    np.random.seed(2026)
    namespace, executed_cells = _execute_legacy_namespace()
    num_satellites_range = range(3, 15 + 1)
    num_users_range = [1, 3, 5, 7]
    loc, sync = namespace["generate_FIM_data"](num_satellites_range, num_users_range)
    loc = np.asarray(loc, dtype=float)
    sync = np.asarray(sync, dtype=float)

    loc_mat = gaussian_filter(loc, sigma=0.0)
    loc_series = [loc_mat[index, :] for index in range(len(loc_mat))]
    loc_fitted = [
        np.asarray(namespace["fit_and_resample_power_law"](np.asarray(list(num_satellites_range)), values, np.asarray(list(num_satellites_range))), dtype=float)
        for values in loc_series
    ]
    sync_mat = gaussian_filter(sync * 1.0e9, sigma=0.0)
    sync_series = [sync_mat[index, :] for index in range(len(sync_mat))]
    sync_fitted_computed_but_not_plotted = [
        np.asarray(namespace["fit_and_resample_power_law"](np.asarray(list(num_satellites_range)), values, np.asarray(list(num_satellites_range))), dtype=float)
        for values in sync_series
    ]

    satellite_counts = list(num_satellites_range)
    loc_labels = ["Without cooperation"] + [
        f"JCLS, N_u = {num_users_range[index]}" for index in range(1, len(loc_series))
    ]
    sync_labels = ["Without Cooperation"] + [
        f"JCLS, N_u = {num_users_range[index]}" for index in range(1, len(sync_series))
    ]
    pos_pdf = output_root / "pos_crlb_0dB_0dB.pdf"
    sync_pdf = output_root / "sync_crlb_0dB_0dB.pdf"
    _legacy_plot(
        np.asarray(satellite_counts),
        loc_fitted,
        loc_labels,
        xlabel=r"Number of Satellites ($N_\mathrm{s}$)",
        ylabel="CRLB on average UE position error [m]",
        title="pos_crlb_0dB_0dB",
        output_path=pos_pdf,
        log_y=True,
        legend_loc="best",
    )
    _legacy_plot(
        np.asarray(satellite_counts),
        sync_series,
        sync_labels,
        xlabel=r"Number of Satellites ($N_\mathrm{s}$)",
        ylabel=r"CRLB on average clock error [ns]",
        title="sync_crlb_0dB_0dB",
        output_path=sync_pdf,
        log_y=True,
        legend_loc="below upper right",
    )

    _write_csv_matrix(output_root / "legacy_loc_mat_km2_per_user.csv", num_users_range, satellite_counts, loc)
    _write_csv_matrix(output_root / "legacy_sync_mat_km2_per_clock.csv", num_users_range, satellite_counts, sync)
    _write_csv_matrix(output_root / "legacy_pos_plot_y_m.csv", num_users_range, satellite_counts, np.vstack(loc_fitted))
    _write_csv_matrix(output_root / "legacy_sync_plot_y_ns.csv", num_users_range, satellite_counts, np.vstack(sync_series))
    np.savez(
        output_root / "legacy_crlb_replay_arrays.npz",
        loc=loc,
        sync=sync,
        pos_plot_y=np.vstack(loc_fitted),
        sync_plot_y=np.vstack(sync_series),
        sync_fitted_computed_but_not_plotted=np.vstack(sync_fitted_computed_but_not_plotted),
        num_satellites=np.asarray(satellite_counts),
        num_users=np.asarray(num_users_range),
    )

    existing_artifacts = _find_existing_artifacts()
    replayed = [
        {
            "figure": "pos_crlb_0dB_0dB.pdf",
            "replayed_pdf": str(pos_pdf.relative_to(SAT_SIM_ROOT)),
            "sha256": _hash_file(pos_pdf),
            "status": "legacy_replayed_unverified_match",
            "legacy_replay": True,
            "manuscript_ready": False,
            "comparison_basis": "file inventory/hash only; no source artifact visual match claimed",
        },
        {
            "figure": "sync_crlb_0dB_0dB.pdf",
            "replayed_pdf": str(sync_pdf.relative_to(SAT_SIM_ROOT)),
            "sha256": _hash_file(sync_pdf),
            "status": "legacy_replayed_unverified_match",
            "legacy_replay": True,
            "manuscript_ready": False,
            "comparison_basis": "file inventory/hash only; no source artifact visual match claimed",
        },
    ]
    report = {
        "status": "legacy_crlb_replayed_unverified_match",
        "artifact_status": "non_final_legacy_crlb_replay",
        "legacy_replay": True,
        "manuscript_ready": False,
        "notebook_source_modified": False,
        "full_notebook_executed": False,
        "colab_setup_executed": False,
        "workspace_pickle_executed": False,
        "manuscript_output_paths_written": False,
        "output_root": str(output_root.relative_to(SAT_SIM_ROOT)),
        "seed": 2026,
        "num_satellites_range": satellite_counts,
        "num_users_range": num_users_range,
        "executed_cells": executed_cells,
        "cells_functions_extracted": [
            "Node",
            "User",
            "Satellite",
            "Datalink",
            "Scenario",
            "build_sigma_matrix_from_snr",
            "remove_dependent_measurements",
            "generate_FIM_data",
            "fit_and_resample_power_law",
        ],
        "legacy_caveats": {
            "uses_all_clock_symbolic_state": True,
            "v24_gauged_state": False,
            "removes_dependent_rows_by_qr": True,
            "forms_full_fim_but_does_not_use_full_covariance_for_bounds": True,
            "posthoc_position_clock_slicing": True,
            "localization_bound_uses_inv": True,
            "synchronization_bound_uses_pinv": True,
            "sync_bound_averages_all_clock_symbols_including_reference": True,
            "pos_plot_uses_power_law_fit": True,
            "sync_power_law_fit_computed_but_raw_series_plotted": True,
            "classification": "legacy_only_unsafe_for_v24_claims_without_replacement_or_human_review",
        },
        "raw_outputs": {
            "loc_csv": str((output_root / "legacy_loc_mat_km2_per_user.csv").relative_to(SAT_SIM_ROOT)),
            "sync_csv": str((output_root / "legacy_sync_mat_km2_per_clock.csv").relative_to(SAT_SIM_ROOT)),
            "pos_plot_csv": str((output_root / "legacy_pos_plot_y_m.csv").relative_to(SAT_SIM_ROOT)),
            "sync_plot_csv": str((output_root / "legacy_sync_plot_y_ns.csv").relative_to(SAT_SIM_ROOT)),
            "arrays_npz": str((output_root / "legacy_crlb_replay_arrays.npz").relative_to(SAT_SIM_ROOT)),
        },
        "plot_outputs": [entry["replayed_pdf"] for entry in replayed],
        "existing_artifact_comparison": {
            "existing_artifacts": existing_artifacts,
            "comparison_status": "unverified_match",
            "claim_match": False,
            "note": (
                "Existing target artifact paths were inventoried and replay PDFs were generated, "
                "but this sprint does not claim visual or data equality."
            ),
        },
        "replayed_figures": replayed,
        "finite_checks": {
            "loc_all_finite": bool(np.all(np.isfinite(loc))),
            "sync_all_finite": bool(np.all(np.isfinite(sync))),
            "pos_plot_all_positive": bool(np.all(np.vstack(loc_fitted) > 0.0)),
            "sync_plot_all_positive": bool(np.all(np.vstack(sync_series) > 0.0)),
        },
        "commands_to_rerun": [
            "python scripts/replay_legacy_crlb_figures.py",
            "python -m unittest tests.test_legacy_crlb_replay",
        ],
        "next_recommended_figure_family": "pos_vary_clock.pdf and sync_vary_clock.pdf",
    }
    (output_root / "legacy_crlb_replay_metadata.json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )
    (output_root / "legacy_crlb_replay_metadata.md").write_text(
        "\n".join(
            [
                "# Legacy CRLB Replay Metadata",
                "",
                f"- Status: `{report['status']}`",
                f"- Output root: `{report['output_root']}`",
                f"- Manuscript ready: `{report['manuscript_ready']}`",
                f"- V24 compatible: `{report['legacy_caveats']['classification']}`",
                "",
                "## Replayed Figures",
                "",
                *[
                    f"- `{entry['figure']}` -> `{entry['replayed_pdf']}` ({entry['status']})"
                    for entry in replayed
                ],
                "",
                "## Caveats",
                "",
                *[
                    f"- `{key}`: {value}"
                    for key, value in report["legacy_caveats"].items()
                ],
            ]
        ),
        encoding="utf-8",
    )
    return report


def _update_figure_regression_table(report: dict[str, Any]) -> None:
    """Update figure-regression table statuses for replayed CRLB figures."""

    table_path = SAT_SIM_ROOT / "v24_notebook_regression_outputs" / "FIGURE_REGRESSION_TABLE.json"
    if not table_path.exists():
        return
    table = json.loads(table_path.read_text(encoding="utf-8"))
    status_by_figure = {
        entry["figure"]: entry["status"]
        for entry in report["replayed_figures"]
    }
    for entry in table.get("target_figure_statuses", []):
        if entry.get("figure") in status_by_figure:
            entry["status"] = status_by_figure[entry["figure"]]
            entry["legacy_replay"] = True
            entry["manuscript_ready"] = False
            entry["replayed_output_root"] = report["output_root"]
            entry["reason"] = (
                "Legacy notebook CRLB logic replayed safely into diagnostics, "
                "but match to existing artifact is unverified and V24 caveats remain."
            )
    table["crlb_replay_report"] = str(
        (OUTPUT_ROOT / "legacy_crlb_replay_metadata.json").relative_to(SAT_SIM_ROOT)
    )
    table["reproduction_status"] = "legacy_crlb_replayed_unverified_match"
    table_path.write_text(json.dumps(table, indent=2), encoding="utf-8")

    md_path = table_path.with_suffix(".md")
    lines = [
        "# Figure Regression Table",
        "",
        "- Existing static mapping records are preserved in the JSON.",
        "- CRLB target figures have safe legacy replay outputs, but are not manuscript-ready.",
        "",
        "| Figure | Status | Legacy replay | Manuscript ready | Reason |",
        "|---|---|---:|---:|---|",
    ]
    for entry in table.get("target_figure_statuses", []):
        lines.append(
            "| {figure} | {status} | {legacy_replay} | {manuscript_ready} | {reason} |".format(
                figure=entry["figure"],
                status=entry["status"],
                legacy_replay=entry.get("legacy_replay", False),
                manuscript_ready=entry.get("manuscript_ready", False),
                reason=entry.get("reason", ""),
            )
        )
    lines.extend(
        [
            "",
            f"- Existing static record count: {len(table.get('records', []))}",
            f"- Notebook executed: {table.get('notebook_executed')}",
            f"- CRLB replay report: `{table.get('crlb_replay_report')}`",
        ]
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_top_level_report(report: dict[str, Any]) -> None:
    """Write top-level paired replay reports."""

    output_dir = SAT_SIM_ROOT / "v24_notebook_regression_outputs"
    payload = dict(report)
    payload["report_type"] = "legacy_crlb_replay_report"
    json_path = output_dir / "LEGACY_CRLB_REPLAY_REPORT.json"
    md_path = output_dir / "LEGACY_CRLB_REPLAY_REPORT.md"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md_lines = [
        "# Legacy CRLB Replay Report",
        "",
        f"- Status: `{payload['status']}`",
        f"- Output root: `{payload['output_root']}`",
        f"- Manuscript ready: `{payload['manuscript_ready']}`",
        f"- Full notebook executed: `{payload['full_notebook_executed']}`",
        "",
        "## Replayed Figures",
        "",
    ]
    for entry in payload["replayed_figures"]:
        md_lines.append(
            f"- `{entry['figure']}` -> `{entry['replayed_pdf']}`; status `{entry['status']}`"
        )
    md_lines.extend(
        [
            "",
            "## Legacy Caveats",
            "",
            *[
                f"- `{key}`: {value}"
                for key, value in payload["legacy_caveats"].items()
            ],
            "",
            "## Existing Artifact Comparison",
            "",
            f"- Comparison status: `{payload['existing_artifact_comparison']['comparison_status']}`",
            f"- Claim match: `{payload['existing_artifact_comparison']['claim_match']}`",
            "",
            "## Commands",
            "",
            *[f"- `{command}`" for command in payload["commands_to_rerun"]],
        ]
    )
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if SAT_SIM_ROOT not in args.output_root.resolve().parents and args.output_root.resolve() != SAT_SIM_ROOT:
        raise ValueError("output-root must be inside sat-sim.")
    report = replay_legacy_crlb_figures(output_root=args.output_root)
    _update_figure_regression_table(report)
    _write_top_level_report(report)
    print(json.dumps({"status": report["status"], "output_root": report["output_root"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
