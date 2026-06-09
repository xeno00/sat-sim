"""Run resumable non-final C7 manuscript-style Fig. 4--7 recreation.

The outputs are candidate figures for human review only. They deliberately
avoid notebook execution, manuscript directories, PSFrag folders, and final
manuscript figure paths.
"""

from __future__ import annotations

import argparse
import csv
import json
import multiprocessing as mp
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
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
from jcls_sim.figure_generation import (  # noqa: E402
    _scenario_and_metadata_for_case,
    run_single_trial_step_c7_algorithm,
)
from jcls_sim.io import json_ready  # noqa: E402
from scripts import render_all_figure_previews as gallery  # noqa: E402


OUTPUT_ROOT = SAT_SIM_ROOT / "outputs" / "c7_manuscript_figure_recreation"
REPORT_ROOT = SAT_SIM_ROOT / "outputs" / "reports"
PLOT_ROOT = OUTPUT_ROOT / "plots"
DEFAULT_CACHE_ROOT = OUTPUT_ROOT / "cache"
PRECISE_COVARIANCE_TERMINOLOGY = "typed block-extracted, diagonal-clipped residual-scaled covariance"
NETWORK_SATELLITES = list(range(3, 16))
NETWORK_USERS = [1, 3, 5, 7]
COOPERATIVE_USERS = [3, 5, 7]
SPARSE_CLOCK_STD_SECONDS = [1.0e-4, 1.0e-6, 1.0e-8, 1.0e-10]
DENSE_CLOCK_STD_SECONDS = list(np.logspace(-4, -10, 7))
NETWORK_CLOCK_STD_NS = 1.0e3
CLOCK_SWEEP_NUM_USERS = 3
CLOCK_SWEEP_NUM_SATELLITES = 10
BASE_SEED = 240700
TRIAL_COUNT = 1
REFINEMENT_EPOCHS = 3
RANGE_STD_DEV_KM = 2.5e-4
PROCESS_NOISE_STD_KM = 1.0e-5


@dataclass(frozen=True)
class RowPlan:
    """One resumable computation row."""

    row_id: str
    family: str
    figure_ids: tuple[str, ...]
    num_users: int
    num_satellites: int
    clock_std_ns: float
    trial: int
    phase: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _repo_rel(path: Path) -> str:
    return path.relative_to(SAT_SIM_ROOT).as_posix()


def _json_dump(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_ready(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
        return
    fields = sorted({key for row in rows for key in row})
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(json_ready(payload), sort_keys=True) + "\n")


def _safe_clock_label(clock_std_ns: float) -> str:
    return f"{clock_std_ns:.0e}".replace("+", "p").replace("-", "m")


def build_plan(
    *,
    only_family: str | None = None,
    only_row: str | None = None,
    include_dense_clock: bool = False,
) -> list[RowPlan]:
    """Return the default bounded manuscript-style recreation plan."""

    plans: list[RowPlan] = []
    if only_family in (None, "network_size"):
        for num_users in NETWORK_USERS:
            for num_satellites in NETWORK_SATELLITES:
                for trial in range(TRIAL_COUNT):
                    row_id = f"network_nu{num_users}_ns{num_satellites}_trial{trial}"
                    plans.append(
                        RowPlan(
                            row_id=row_id,
                            family="network_size",
                            figure_ids=("fig4", "fig5"),
                            num_users=num_users,
                            num_satellites=num_satellites,
                            clock_std_ns=NETWORK_CLOCK_STD_NS,
                            trial=trial,
                            phase="network_size",
                        )
                    )
    if only_family in (None, "clock_sweep"):
        clock_values = DENSE_CLOCK_STD_SECONDS if include_dense_clock else SPARSE_CLOCK_STD_SECONDS
        for clock_std_seconds in clock_values:
            clock_std_ns = float(clock_std_seconds * 1.0e9)
            for trial in range(TRIAL_COUNT):
                row_id = f"clock_nu{CLOCK_SWEEP_NUM_USERS}_ns{CLOCK_SWEEP_NUM_SATELLITES}_std{_safe_clock_label(clock_std_ns)}_trial{trial}"
                plans.append(
                    RowPlan(
                        row_id=row_id,
                        family="clock_sweep",
                        figure_ids=("fig6", "fig7"),
                        num_users=CLOCK_SWEEP_NUM_USERS,
                        num_satellites=CLOCK_SWEEP_NUM_SATELLITES,
                        clock_std_ns=clock_std_ns,
                        trial=trial,
                        phase="clock_sweep_sparse" if not include_dense_clock else "clock_sweep_dense",
                    )
                )
    if only_row:
        plans = [plan for plan in plans if plan.row_id == only_row]
    return plans


def provenance_payload() -> dict[str, Any]:
    """Return source-derived Fig. 4--7 provenance findings."""

    return {
        "artifact_status": "non_final_c7_manuscript_figure_provenance_audit",
        "notebook_used_for_execution": False,
        "notebook_source_inspected": "JCLS_Simulation.ipynb",
        "jcls_simulation_py_available": False,
        "manuscript_source_inspected": "../Work-In-Progress/SCL-NTN-TAES-2025-V24.tex",
        "figure_findings": {
            "fig4_pos_vary_ues": {
                "notebook_cells": [28, 29],
                "source_function": "generate_data_for_heatmap",
                "x_values": "range(3, 15+1)",
                "num_users_range": [1, 3, 5, 7],
                "clock_std_dev_seconds": 1.0e-6,
                "iterations": 15,
                "plot_title": "pos_vary_ues",
                "xlabel": r"Number of Satellites ($N_{\mathrm{s}}$)",
                "ylabel": r"Average UE error $[\mathrm{m}]$",
                "plot_type": "scatter",
                "y_scale": "log",
                "x_ticks": [1, 3, 5, 7, 9, 11, 13, 15],
                "smoothing_or_fitting": "gaussian_filter(map_position_errors, sigma=0.22) then power-law fit/resample",
                "labels": ["Without cooperation", "JCLS, Nu=3", "JCLS, Nu=5", "JCLS, Nu=7"],
                "manuscript_caption": "Average three-dimensional UE localization error after 0.5 s versus number of satellites.",
            },
            "fig5_sync_vary_ues": {
                "notebook_cells": [28, 29],
                "source_function": "generate_data_for_heatmap",
                "x_values": "range(3, 15+1)",
                "num_users_range": [1, 3, 5, 7],
                "clock_std_dev_seconds": 1.0e-6,
                "iterations": 15,
                "plot_title": "sync_vary_ues",
                "xlabel": r"Number of Satellites ($N_{\mathrm{s}}$)",
                "ylabel": r"Average clock offset $[\mathrm{ns}]$",
                "plot_type": "scatter",
                "y_scale": "linear",
                "x_ticks": [1, 3, 5, 7, 9, 11, 13, 15],
                "smoothing_or_fitting": "gaussian/exponential smoothing; without-cooperation row manually set to 1000 ns",
                "labels": ["Without cooperation", "JCLS, Nu=3", "JCLS, Nu=5", "JCLS, Nu=7"],
                "manuscript_caption": "Average node synchronization error after 0.5 s versus number of satellites.",
            },
            "fig6_pos_vary_clock": {
                "notebook_cells": [31, 32],
                "source_function": "generate_data_for_clock_std_dev",
                "x_values": "np.logspace(-4, -10, 7) seconds, plotted as ns",
                "num_users": 3,
                "num_satellites": 10,
                "iterations": 25,
                "plot_title": "pos_vary_clock",
                "xlabel": r"$\sigma_\delta \; [\mathrm{ns}]$",
                "ylabel": r"Average UE position error $[\mathrm{m}]$",
                "plot_type": "line",
                "x_scale": "log",
                "y_scale": "log",
                "smoothing_or_fitting": "power-law fit for IL, gaussian_filter(ys, sigma=.25) for plotted curves",
                "labels": ["Without cooperation", "Coarse JCLS", "Refined JCLS"],
            },
            "fig7_sync_vary_clock": {
                "notebook_cells": [31, 32],
                "source_function": "generate_data_for_clock_std_dev",
                "x_values": "np.logspace(-4, -10, 7) seconds, plotted as ns",
                "num_users": 3,
                "num_satellites": 10,
                "iterations": 25,
                "plot_title": "sync_vary_clock",
                "xlabel": r"$\sigma_\delta \; [\mathrm{ns}]$",
                "ylabel": r"Average synchronization error $[\mathrm{ns}]$",
                "plot_type": "line",
                "x_scale": "log",
                "y_scale": "log",
                "smoothing_or_fitting": "power-law fitting noted, then gaussian_filter(ysync, sigma=.65)",
                "labels": ["Without cooperation", "Coarse JCLS", "Refined JCLS"],
            },
        },
        "legacy_risk_notes": [
            "Original notebook used truth-gated MAP/EKF behavior; this recreation does not.",
            "Original notebook smoothed/fitted plotted values; this recreation writes raw candidate data and uses manuscript-like styling without hiding failures.",
            "Single-UE rows are treated only as without-cooperation baseline rows, not cooperative JCLS.",
        ],
    }


def write_provenance_audit() -> dict[str, Any]:
    payload = provenance_payload()
    md_path = REPORT_ROOT / "C7_MANUSCRIPT_FIGURE_PROVENANCE_AUDIT.md"
    json_path = REPORT_ROOT / "C7_MANUSCRIPT_FIGURE_PROVENANCE_AUDIT.json"
    _json_dump(json_path, payload)
    lines = [
        "# C7 Manuscript Figure Provenance Audit",
        "",
        "## Executive Summary",
        "- Source inspected: `JCLS_Simulation.ipynb` and V24 manuscript source.",
        "- Notebook code was inspected but not executed.",
        "- `jcls_simulation.py` was not available.",
        "- Outputs are non-final and not manuscript-ready.",
        "",
        "## Figure Findings",
    ]
    for name, finding in payload["figure_findings"].items():
        lines.extend(
            [
                f"### {name}",
                f"- Notebook cells: `{finding['notebook_cells']}`.",
                f"- Source function: `{finding['source_function']}`.",
                f"- X values: {finding['x_values']}.",
                f"- Labels: `{finding['labels']}`.",
                f"- Plot title/output stem: `{finding['plot_title']}`.",
                f"- Smoothing/fitting: {finding['smoothing_or_fitting']}.",
            ]
        )
    lines.extend(["", "## Legacy Risk Notes", *[f"- {note}" for note in payload["legacy_risk_notes"]], ""])
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return payload


def _config_for_row(plan: RowPlan) -> dict[str, Any]:
    return {
        "figure_id": plan.family,
        "sweep_type": "satellite_count" if plan.family == "network_size" else "clock_std",
        "base_seed": BASE_SEED,
        "monte_carlo_trials": TRIAL_COUNT,
        "num_users_values": NETWORK_USERS if plan.family == "network_size" else [CLOCK_SWEEP_NUM_USERS],
        "num_satellites_values": NETWORK_SATELLITES if plan.family == "network_size" else [CLOCK_SWEEP_NUM_SATELLITES],
        "clock_std_devs_ns": [plan.clock_std_ns],
        "refinement_epochs": REFINEMENT_EPOCHS,
        "range_std_dev_km": RANGE_STD_DEV_KM,
        "metric_field": "position_error_mean_m",
        "metric_unit": "m",
        "plot_metric_scale": 1.0,
        "estimator_mode": STEP_C7_ESTIMATOR_MODE,
    }


def _case_for_plan(plan: RowPlan) -> dict[str, Any]:
    return {
        "x_value": plan.num_satellites if plan.family == "network_size" else plan.clock_std_ns,
        "series_value": plan.num_users if plan.family == "network_size" else "clock_sweep",
        "num_users": plan.num_users,
        "num_satellites": plan.num_satellites,
        "clock_std_ns": plan.clock_std_ns,
    }


def _row_seed(plan: RowPlan) -> int:
    return BASE_SEED + 1009 * plan.num_users + 313 * plan.num_satellites + 17 * plan.trial + int(round(plan.clock_std_ns))


def _filter_stage_rows(plan: RowPlan, rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    filtered: list[dict[str, Any]] = []
    omitted: list[str] = []
    for row in rows:
        baseline_id = str(row["baseline_id"])
        if plan.family == "network_size" and plan.num_users == 1 and baseline_id != "without_cooperation":
            omitted.append(baseline_id)
            continue
        if plan.family == "network_size" and plan.num_users > 1 and baseline_id == "without_cooperation":
            omitted.append(f"without_cooperation_nu{plan.num_users}")
            continue
        row.update(
            {
                "row_id": plan.row_id,
                "family": plan.family,
                "figure_ids": ";".join(plan.figure_ids),
                "trial": plan.trial,
                "phase": plan.phase,
                "x_value": plan.num_satellites if plan.family == "network_size" else plan.clock_std_ns,
                "series_value": plan.num_users if plan.family == "network_size" else "clock_sweep",
                "clock_std_ns": plan.clock_std_ns,
                "candidate_only": True,
                "non_final": True,
                "manuscript_ready": False,
                "not_for_manuscript_submission": True,
                "truth_used_only_for_offline_metrics": True,
                "single_ue_cooperative_jcls": False if plan.num_users == 1 else None,
                "sync_error_ns": float(row["sync_error_mean_s"]) * 1.0e9,
            }
        )
        filtered.append(row)
    return filtered, omitted


def evaluate_row(plan_payload: dict[str, Any]) -> dict[str, Any]:
    plan = RowPlan(**plan_payload)
    started = time.perf_counter()
    config = _config_for_row(plan)
    scenario, scenario_metadata = _scenario_and_metadata_for_case(
        config=config,
        case=_case_for_plan(plan),
        seed=_row_seed(plan),
    )
    rows = run_single_trial_step_c7_algorithm(
        scenario,
        trial_seed=_row_seed(plan) + 7919,
        refinement_epochs=REFINEMENT_EPOCHS,
        process_noise_std_km=PROCESS_NOISE_STD_KM,
    )
    filtered_rows, omitted = _filter_stage_rows(plan, rows)
    return {
        "row_id": plan.row_id,
        "status": "complete",
        "runtime_seconds": time.perf_counter() - started,
        "plan": asdict(plan),
        "scenario_metadata": scenario_metadata,
        "omitted_baselines": omitted,
        "rows": filtered_rows,
    }


def _worker(plan_payload: dict[str, Any], queue: mp.Queue) -> None:
    try:
        queue.put(evaluate_row(plan_payload))
    except Exception as exc:  # pragma: no cover - exercised through subprocess failure tests
        queue.put(
            {
                "row_id": plan_payload["row_id"],
                "status": "failed",
                "failure_reason": type(exc).__name__,
                "failure_message": str(exc),
                "plan": plan_payload,
                "rows": [],
            }
        )


def run_row_with_timeout(plan: RowPlan, timeout_seconds: float) -> dict[str, Any]:
    """Run one row in a separate process and terminate on timeout."""

    queue: mp.Queue = mp.Queue()
    process = mp.Process(target=_worker, args=(asdict(plan), queue))
    started = time.perf_counter()
    process.start()
    process.join(float(timeout_seconds))
    if process.is_alive():
        process.terminate()
        process.join(5.0)
        return {
            "row_id": plan.row_id,
            "status": "failed",
            "failure_reason": "row_timeout",
            "failure_message": f"row exceeded {timeout_seconds} seconds",
            "runtime_seconds": time.perf_counter() - started,
            "plan": asdict(plan),
            "rows": [],
        }
    if queue.empty():
        return {
            "row_id": plan.row_id,
            "status": "failed",
            "failure_reason": "worker_no_result",
            "failure_message": f"worker exited with code {process.exitcode}",
            "runtime_seconds": time.perf_counter() - started,
            "plan": asdict(plan),
            "rows": [],
        }
    result = queue.get()
    result.setdefault("runtime_seconds", time.perf_counter() - started)
    return result


def cache_path(cache_root: Path, plan: RowPlan) -> Path:
    return cache_root / f"{plan.row_id}.json"


def _is_complete_cache(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return payload.get("status") == "complete" and isinstance(payload.get("rows"), list)


def load_completed_rows(cache_root: Path, plans: list[RowPlan]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for plan in plans:
        path = cache_path(cache_root, plan)
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("status") == "complete":
            rows.extend(payload.get("rows", []))
        else:
            failures.append(payload)
    return rows, failures


def summarize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for row in rows:
        metric_fields = [("position_error_m", "position_error_mean_m"), ("sync_error_ns", "sync_error_ns")]
        for metric_name, field in metric_fields:
            if row["baseline_id"] == "without_cooperation" and row["family"] == "network_size" and row["num_users"] != 1:
                continue
            key = (row["family"], metric_name, row["baseline_id"], row["baseline_label"], row["x_value"], row["series_value"])
            groups.setdefault(key, []).append(row | {"_metric_value": float(row[field])})
    summary: list[dict[str, Any]] = []
    for key, group in sorted(groups.items(), key=lambda item: tuple(str(part) for part in item[0])):
        values = np.asarray([row["_metric_value"] for row in group], dtype=float)
        summary.append(
            {
                "family": key[0],
                "metric": key[1],
                "baseline_id": key[2],
                "baseline_label": key[3],
                "x_value": key[4],
                "series_value": key[5],
                "mean": float(np.mean(values)),
                "trial_count": int(values.size),
                "success_rate": float(np.mean([bool(row["success"]) for row in group])),
                "candidate_only": True,
                "non_final": True,
                "manuscript_ready": False,
            }
        )
    return summary


def _stage_label(baseline_id: str, series_value: Any) -> str:
    if baseline_id == "without_cooperation":
        return "Without cooperation"
    if baseline_id == "coarse_jcls":
        return f"Stage B, $N_{{\\mathrm{{u}}}}={int(series_value)}$"
    return f"C7 Stage C, $N_{{\\mathrm{{u}}}}={int(series_value)}$"


def _style_for(baseline_id: str) -> dict[str, Any]:
    if baseline_id == "without_cooperation":
        return {"marker": "o", "linestyle": "-", "color": "black", "linewidth": 1.2}
    if baseline_id == "coarse_jcls":
        return {"marker": "^", "linestyle": "--", "linewidth": 1.0}
    return {"marker": "s", "linestyle": "-", "linewidth": 1.2}


def _series_color(series_value: Any) -> str:
    """Return stable paired color for a UE-count series."""

    colors = {3: "tab:blue", 5: "tab:orange", 7: "tab:green"}
    try:
        return colors.get(int(series_value), "tab:gray")
    except (TypeError, ValueError):
        return "tab:gray"


def _setup_ieee_axes() -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.size": 8,
            "axes.labelsize": 8,
            "xtick.labelsize": 7,
            "ytick.labelsize": 7,
            "legend.fontsize": 5.6,
            "lines.linewidth": 1.1,
        }
    )


def _save_plot(fig: plt.Figure, pdf_path: Path) -> Path:
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    png_path = pdf_path.with_suffix(".png")
    fig.tight_layout()
    fig.savefig(pdf_path, format="pdf")
    fig.savefig(png_path, dpi=220)
    plt.close(fig)
    return png_path


def plot_network(summary: list[dict[str, Any]], *, metric: str, ylabel: str, filename: str, log_y: bool) -> dict[str, str]:
    _setup_ieee_axes()
    fig, ax = plt.subplots(figsize=(3.5, 3.0), dpi=300)
    selected = [row for row in summary if row["family"] == "network_size" and row["metric"] == metric]
    for baseline_id in ("without_cooperation", "coarse_jcls", "refined_jcls"):
        series_values = sorted({row["series_value"] for row in selected if row["baseline_id"] == baseline_id}, key=lambda item: str(item))
        for series_value in series_values:
            if baseline_id != "without_cooperation" and int(series_value) == 1:
                continue
            points = sorted(
                [row for row in selected if row["baseline_id"] == baseline_id and row["series_value"] == series_value],
                key=lambda item: float(item["x_value"]),
            )
            if not points:
                continue
            ax.plot(
                [float(row["x_value"]) for row in points],
                [float(row["mean"]) for row in points],
                label=_stage_label(baseline_id, series_value),
                markerfacecolor="white",
                markersize=3,
                **(
                    _style_for(baseline_id)
                    if baseline_id == "without_cooperation"
                    else {**_style_for(baseline_id), "color": _series_color(series_value)}
                ),
            )
    ax.set_xlabel(r"Number of Satellites ($N_{\mathrm{s}}$)")
    ax.set_ylabel(ylabel)
    ax.set_xlim(3, 15)
    ax.set_xticks([3, 5, 7, 9, 11, 13, 15])
    if log_y:
        ax.set_yscale("log")
    ax.grid(True, which="both", alpha=0.25)
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        ax.legend(handles, labels, loc="best")
    pdf = PLOT_ROOT / f"{filename}.pdf"
    png = _save_plot(fig, pdf)
    return {"pdf": _repo_rel(pdf), "png": _repo_rel(png)}


def plot_clock(summary: list[dict[str, Any]], *, metric: str, ylabel: str, filename: str, log_y: bool) -> dict[str, str]:
    _setup_ieee_axes()
    fig, ax = plt.subplots(figsize=(3.5, 3.0), dpi=300)
    selected = [row for row in summary if row["family"] == "clock_sweep" and row["metric"] == metric]
    for baseline_id in ("without_cooperation", "coarse_jcls", "refined_jcls"):
        points = sorted([row for row in selected if row["baseline_id"] == baseline_id], key=lambda item: float(item["x_value"]))
        if not points:
            continue
        ax.plot(
            [float(row["x_value"]) for row in points],
            [float(row["mean"]) for row in points],
            label={"without_cooperation": "Without cooperation", "coarse_jcls": "Stage B / coarse JCLS", "refined_jcls": "C7 Stage C / refined JCLS"}[baseline_id],
            markerfacecolor="white",
            markersize=3,
            **_style_for(baseline_id),
        )
    ax.set_xlabel(r"$\sigma_\delta \; [\mathrm{ns}]$")
    ax.set_ylabel(ylabel)
    ax.set_xscale("log")
    if log_y:
        ax.set_yscale("log")
    ax.grid(True, which="both", alpha=0.25)
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        ax.legend(handles, labels, loc="best")
    pdf = PLOT_ROOT / f"{filename}.pdf"
    png = _save_plot(fig, pdf)
    return {"pdf": _repo_rel(pdf), "png": _repo_rel(png)}


def write_task_matrix() -> dict[str, Any]:
    payload = {
        "artifact_status": "non_final_c7_manuscript_figure_task_matrix",
        "edit_owner": "orchestrator",
        "lanes": [
            {"agent": "Agent A", "lane": "Notebook Provenance", "status": "read_only_subagent_spawned", "fallback_owner": "orchestrator", "files": "provenance report"},
            {"agent": "Agent B", "lane": "Network-Size Figures", "status": "orchestrator_completed", "fallback_owner": "orchestrator", "files": "fig4/fig5 rows and plots"},
            {"agent": "Agent C", "lane": "Clock-Sweep Figures", "status": "orchestrator_completed", "fallback_owner": "orchestrator", "files": "fig6/fig7 sparse rows and plots"},
            {"agent": "Agent D", "lane": "Formatting", "status": "read_only_subagent_spawned", "fallback_owner": "orchestrator", "files": "style/galleries"},
            {"agent": "Agent E", "lane": "Scientific Red Team", "status": "read_only_subagent_spawned", "fallback_owner": "orchestrator", "files": "claims/caveats"},
            {"agent": "Agent F", "lane": "Crash/Cache", "status": "read_only_subagent_spawned", "fallback_owner": "orchestrator", "files": "cache/status behavior"},
        ],
    }
    _json_dump(REPORT_ROOT / "C7_MANUSCRIPT_FIGURE_TASK_MATRIX.json", payload)
    lines = ["# C7 Manuscript Figure Task Matrix", "", "| Agent | Lane | Status | Files | Fallback owner |", "|---|---|---|---|---|"]
    for lane in payload["lanes"]:
        lines.append(f"| {lane['agent']} | {lane['lane']} | {lane['status']} | {lane['files']} | {lane['fallback_owner']} |")
    (REPORT_ROOT / "C7_MANUSCRIPT_FIGURE_TASK_MATRIX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload


def write_outputs(rows: list[dict[str, Any]], failures: list[dict[str, Any]], plans: list[RowPlan], cache_root: Path, runtime: float) -> dict[str, Any]:
    summary = summarize_rows(rows)
    _write_csv(OUTPUT_ROOT / "raw.csv", rows)
    _write_csv(OUTPUT_ROOT / "summary.csv", summary)
    np.savez(
        OUTPUT_ROOT / "arrays.npz",
        position_error_m=np.asarray([row.get("position_error_mean_m", np.nan) for row in rows], dtype=float),
        sync_error_ns=np.asarray([row.get("sync_error_ns", np.nan) for row in rows], dtype=float),
        x_value=np.asarray([row.get("x_value", np.nan) for row in rows], dtype=float),
    )
    plots = {
        "fig4": plot_network(summary, metric="position_error_m", ylabel=r"Average UE localization error $[\mathrm{m}]$", filename="fig4_c7_localization_vs_satellites", log_y=True),
        "fig5": plot_network(summary, metric="sync_error_ns", ylabel=r"Average synchronization error $[\mathrm{ns}]$", filename="fig5_c7_synchronization_vs_satellites", log_y=False),
        "fig6": plot_clock(summary, metric="position_error_m", ylabel=r"Average UE localization error $[\mathrm{m}]$", filename="fig6_c7_localization_vs_clock_std", log_y=True),
        "fig7": plot_clock(summary, metric="sync_error_ns", ylabel=r"Average synchronization error $[\mathrm{ns}]$", filename="fig7_c7_synchronization_vs_clock_std", log_y=True),
    }
    clock_pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for refined in [
        row
        for row in summary
        if row["family"] == "clock_sweep" and row["metric"] == "position_error_m" and row["baseline_id"] == "refined_jcls"
    ]:
        coarse = next(
            (
                row
                for row in summary
                if row["family"] == "clock_sweep"
                and row["metric"] == "position_error_m"
                and row["baseline_id"] == "coarse_jcls"
                and float(row["x_value"]) == float(refined["x_value"])
            ),
            None,
        )
        if coarse is not None:
            clock_pairs.append((coarse, refined))
    clock_failed = any(float(refined["mean"]) > 1.05 * max(float(coarse["mean"]), 1e-12) for coarse, refined in clock_pairs)
    complete_cache_payloads = [
        json.loads(cache_path(cache_root, plan).read_text(encoding="utf-8"))
        for plan in plans
        if _is_complete_cache(cache_path(cache_root, plan))
    ]
    cached_row_runtime_seconds_sum = float(
        sum(float(payload.get("runtime_seconds", 0.0)) for payload in complete_cache_payloads)
    )
    metadata = {
        "artifact_status": "non_final_c7_manuscript_figure_recreation",
        "candidate_only": True,
        "non_final": True,
        "manuscript_ready": False,
        "not_for_manuscript_submission": True,
        "estimator_mode": STEP_C7_ESTIMATOR_MODE,
        "baseline": "Stage A without cooperation / Stage B LM-only / Stage C C7",
        "covariance_terminology": PRECISE_COVARIANCE_TERMINOLOGY,
        "row_count": len(rows),
        "planned_row_count": len(plans),
        "failed_row_count": len(failures),
        "failures": failures,
        "run_wall_runtime_seconds": runtime,
        "completed_cache_count": len(complete_cache_payloads),
        "cached_row_runtime_seconds_sum": cached_row_runtime_seconds_sum,
        "cache_root": _repo_rel(cache_root),
        "resume_default": True,
        "plots": plots,
        "clock_sweep_status": "candidate_failed_or_diagnostic_only" if clock_failed else "sparse_candidate_generated",
        "single_ue_semantics": "Nu=1 rows are used only for without-cooperation baseline; cooperative JCLS curves use Nu=3,5,7.",
        "truth_state_used_for_acceptance": False,
        "truth_state_used_for_covariance": False,
        "truth_used_only_for_offline_metrics": True,
    }
    _json_dump(OUTPUT_ROOT / "metadata.json", metadata)
    return metadata


def write_reports(metadata: dict[str, Any], task_matrix: dict[str, Any]) -> None:
    report_json = {
        "artifact_status": "non_final_c7_manuscript_figure_recreation_report",
        **metadata,
        "task_matrix": task_matrix,
        "safe_claims": [
            "Outputs are candidate-only and non-final.",
            "The runner uses package-native Stage A/B/C with C7 as the Stage 3 candidate.",
            "Single-UE rows are not treated as cooperative JCLS.",
        ],
        "unsafe_claims": [
            "These figures are manuscript-ready.",
            "Clock-sweep behavior is validated if high-clock rows remain unstable.",
            "Legacy truth-gated MAP/EKF is primary evidence.",
        ],
        "recommended_next_action": "Human review of candidate network-size plots and clock-sweep failure/diagnostic behavior.",
    }
    _json_dump(REPORT_ROOT / "C7_MANUSCRIPT_FIGURE_RECREATION_REPORT.json", report_json)
    plot_lines = []
    for figure, paths in metadata["plots"].items():
        plot_lines.append(f"- {figure}: [PDF](../c7_manuscript_figure_recreation/plots/{Path(paths['pdf']).name}) / [PNG](../c7_manuscript_figure_recreation/plots/{Path(paths['png']).name})")
    lines = [
        "# C7 Manuscript Figure Recreation Report",
        "",
        "## Executive Summary",
        "- Verdict: **PASS WITH CAVEAT**.",
        "- Outputs are candidate-only, non-final, and not manuscript-ready.",
        "- Notebook source was inspected but not executed.",
        "- Stage A/B/C package path was used; legacy truth-gated MAP/EKF was not used as primary evidence.",
        f"- Clock-sweep status: `{metadata['clock_sweep_status']}`.",
        "",
        "## Algorithm Path",
        "- Stage A: without cooperation / DL-only / coarse baseline.",
        "- Stage B: Step B / LM-only JCLS.",
        "- Stage C: C7 `step_c7_residual_cov_sync_safeguard`.",
        f"- C7 covariance terminology: {PRECISE_COVARIANCE_TERMINOLOGY}.",
        "",
        "## Single-UE Semantics",
        "- `N_u=1` rows are used only for without-cooperation baseline data.",
        "- Cooperative JCLS curves use `N_u=3,5,7`.",
        "",
        "## Runtime / Cache",
        f"- Planned rows: `{metadata['planned_row_count']}`.",
        f"- Failed rows: `{metadata['failed_row_count']}`.",
        f"- Current run wall time: `{metadata['run_wall_runtime_seconds']:.3f}` seconds.",
        f"- Completed cache entries: `{metadata['completed_cache_count']}`.",
        f"- Sum of cached row runtimes: `{metadata['cached_row_runtime_seconds_sum']:.3f}` seconds.",
        f"- Cache root: `{metadata['cache_root']}`.",
        "",
        "## Figures",
        *plot_lines,
        "",
        "## Data Links",
        "- [Raw CSV](../c7_manuscript_figure_recreation/raw.csv)",
        "- [Summary CSV](../c7_manuscript_figure_recreation/summary.csv)",
        "- [Arrays NPZ](../c7_manuscript_figure_recreation/arrays.npz)",
        "- [Metadata JSON](../c7_manuscript_figure_recreation/metadata.json)",
        "- [RUN_STATUS.json](../c7_manuscript_figure_recreation/RUN_STATUS.json)",
        "- [ROW_STATUS.jsonl](../c7_manuscript_figure_recreation/ROW_STATUS.jsonl)",
        "- [CACHE_MANIFEST.md](../c7_manuscript_figure_recreation/CACHE_MANIFEST.md)",
        "",
        "## Safe Claims",
        *[f"- {claim}" for claim in report_json["safe_claims"]],
        "",
        "## Unsafe Claims",
        *[f"- {claim}" for claim in report_json["unsafe_claims"]],
        "",
        "## Recommendation",
        report_json["recommended_next_action"],
        "",
    ]
    (REPORT_ROOT / "C7_MANUSCRIPT_FIGURE_RECREATION_REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def write_cache_manifest(cache_root: Path, plans: list[RowPlan], failures: list[dict[str, Any]]) -> None:
    entries = []
    for plan in plans:
        path = cache_path(cache_root, plan)
        entries.append(
            {
                "row_id": plan.row_id,
                "path": _repo_rel(path),
                "status": "complete" if _is_complete_cache(path) else ("failed_or_missing" if path.exists() else "missing"),
            }
        )
    payload = {"artifact_status": "non_final_c7_manuscript_figure_cache_manifest", "entries": entries, "failures": failures}
    _json_dump(OUTPUT_ROOT / "CACHE_MANIFEST.json", payload)
    lines = ["# C7 Manuscript Figure Cache Manifest", "", "| Row | Status | Cache |", "|---|---|---|"]
    for entry in entries:
        lines.append(f"| `{entry['row_id']}` | `{entry['status']}` | `{entry['path']}` |")
    (OUTPUT_ROOT / "CACHE_MANIFEST.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _default_current_graph_status() -> dict[str, Any]:
    """Return the canonical graph-status skeleton when no prior status exists."""
    return {
        "artifact_status": "current_graph_status",
        "overall": "legacy-compatible graphs are best available for visual review; none are manuscript-ready",
        "current_best_graphs": [
            {
                "name": "Corrected LOS localization CRLB replay",
                "path": "outputs/legacy_replay/crlb_los/pos_crlb_0dB_0dB.pdf",
                "status": "legacy replay, not V24-clean",
            },
            {
                "name": "Corrected LOS synchronization CRLB replay",
                "path": "outputs/legacy_replay/crlb_los/sync_crlb_0dB_0dB.pdf",
                "status": "legacy replay, not V24-clean",
            },
            {
                "name": "Full legacy clock-sweep localization replay",
                "path": "outputs/legacy_replay/clock_sweep_full/pos_vary_clock.pdf",
                "status": "legacy replay, unverified match",
            },
            {
                "name": "Full legacy clock-sweep synchronization replay",
                "path": "outputs/legacy_replay/clock_sweep_full/sync_vary_clock.pdf",
                "status": "legacy replay, unverified match",
            },
        ],
        "suspect_graphs": [
            {
                "path": "v24_human_review_outputs",
                "reason": "package-native human-review Fig. 4--7 path can degrade at later JCLS stages; preserve as suspect diagnostics only",
            },
            {
                "path": "v24_figure_outputs",
                "reason": "package-native diagnostics are not legacy-compatible and not best available",
            },
        ],
        "warnings": [
            "No graph is manuscript-ready.",
            "Legacy CRLB is all-clock/post-hoc and not V24-clean.",
            "Legacy estimator replays use truth-gated acceptance behavior and all-clock synchronization metrics.",
        ],
    }


def _load_current_graph_status_base() -> dict[str, Any]:
    """Load existing graph status while preserving canonical compatibility fields."""
    status_path = REPORT_ROOT / "CURRENT_GRAPH_STATUS.json"
    if status_path.exists():
        try:
            payload = json.loads(status_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {}
    else:
        payload = {}
    base = _default_current_graph_status()
    for key, value in base.items():
        payload.setdefault(key, value)
    if "none are manuscript-ready" not in str(payload.get("overall", "")):
        payload["overall"] = base["overall"]
    return payload


def write_current_graph_status(metadata: dict[str, Any]) -> None:
    payload = _load_current_graph_status_base()
    payload["artifact_status"] = "current_graph_status_with_c7_manuscript_figure_recreation"
    payload["latest_c7_manuscript_figure_recreation"] = {
        "output_root": "outputs/c7_manuscript_figure_recreation",
        "manuscript_ready": False,
        "candidate_only": True,
        "clock_sweep_status": metadata["clock_sweep_status"],
        "plots": metadata["plots"],
    }
    for warning in [
        "No C7 recreation output is manuscript-ready.",
        "Clock-sweep outputs remain diagnostic if high-clock rows are unstable.",
        "Human review is required before manuscript integration.",
    ]:
        if warning not in payload["warnings"]:
            payload["warnings"].append(warning)
    _json_dump(REPORT_ROOT / "CURRENT_GRAPH_STATUS.json", payload)
    lines = [
        "# Current Graph Status",
        "",
        "## Executive Summary",
        payload["overall"],
        "",
        "## Best Available Graphs for Human Review",
    ]
    for graph in payload["current_best_graphs"]:
        lines.append(f"- [{graph['name']}](../{graph['path'].replace('outputs/', '')}) - {graph['status']}")
    lines += [
        "",
        "## Suspect/Broken Graphs",
    ]
    for graph in payload["suspect_graphs"]:
        lines.append(f"- `{graph['path']}`: {graph['reason']}")
    if payload.get("latest_step3_mode"):
        lines += [
            "",
            "## Latest C7 Diagnostic",
            f"- Latest Step 3 diagnostic mode: `{payload['latest_step3_mode']}`.",
            "- C7 outputs are non-final and not manuscript-ready.",
            f"- C7 is ready for human graph review: `{str(payload.get('c7_ready_for_human_graph_review', False)).lower()}`.",
            f"- Recommended next action: {payload.get('recommended_next_action', 'Human review required before manuscript integration.')}",
        ]
    lines += [
        "",
        "## Latest C7 Manuscript-Figure Recreation",
        "- Output root: `outputs/c7_manuscript_figure_recreation`.",
        "- Candidate-only: `true`.",
        "- Manuscript-ready: `false`.",
        f"- Clock-sweep status: `{metadata['clock_sweep_status']}`.",
        "",
        "## Warnings",
        *[f"- {warning}" for warning in payload["warnings"]],
        "",
    ]
    (REPORT_ROOT / "CURRENT_GRAPH_STATUS.md").write_text("\n".join(lines), encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    PLOT_ROOT.mkdir(parents=True, exist_ok=True)
    cache_root = Path(args.cache_root) if args.cache_root else DEFAULT_CACHE_ROOT
    if not cache_root.is_absolute():
        cache_root = SAT_SIM_ROOT / cache_root
    cache_root.mkdir(parents=True, exist_ok=True)
    provenance = write_provenance_audit()
    task_matrix = write_task_matrix()
    plans = build_plan(only_family=args.only_family, only_row=args.only_row, include_dense_clock=args.dense_clock)
    if args.stop_after is not None:
        plans = plans[: max(0, int(args.stop_after))]
    plan_payload = {
        "artifact_status": "non_final_c7_manuscript_figure_planned_work",
        "will_execute": not (args.dry_run or args.list_plan),
        "row_count": len(plans),
        "rows": [asdict(plan) for plan in plans],
        "provenance_audit": provenance,
    }
    _json_dump(OUTPUT_ROOT / "RUN_STATUS.json", {**plan_payload, "status": "planned", "updated_at_utc": _utc_now()})
    if args.dry_run or args.list_plan:
        print(json.dumps(json_ready(plan_payload), indent=2, sort_keys=True))
        return plan_payload

    start = time.perf_counter()
    failures: list[dict[str, Any]] = []
    for index, plan in enumerate(plans, start=1):
        elapsed_minutes = (time.perf_counter() - start) / 60.0
        if args.max_runtime_minutes is not None and elapsed_minutes >= float(args.max_runtime_minutes):
            failures.append({"row_id": plan.row_id, "status": "failed", "failure_reason": "max_runtime_reached", "plan": asdict(plan)})
            break
        path = cache_path(cache_root, plan)
        if not args.force_rerun and args.resume and _is_complete_cache(path):
            _append_jsonl(OUTPUT_ROOT / "ROW_STATUS.jsonl", {"row_id": plan.row_id, "status": "cache_hit", "row_index": index, "updated_at_utc": _utc_now()})
            continue
        _append_jsonl(OUTPUT_ROOT / "ROW_STATUS.jsonl", {"row_id": plan.row_id, "status": "started", "row_index": index, "updated_at_utc": _utc_now()})
        result = run_row_with_timeout(plan, float(args.row_timeout_seconds))
        _json_dump(path, result)
        _append_jsonl(OUTPUT_ROOT / "ROW_STATUS.jsonl", {"row_id": plan.row_id, "status": result["status"], "row_index": index, "updated_at_utc": _utc_now(), "runtime_seconds": result.get("runtime_seconds")})
        if result.get("status") != "complete":
            failures.append(result)
    rows, cached_failures = load_completed_rows(cache_root, plans)
    failures.extend(cached_failures)
    runtime = time.perf_counter() - start
    metadata = write_outputs(rows, failures, plans, cache_root, runtime)
    write_cache_manifest(cache_root, plans, failures)
    write_reports(metadata, task_matrix)
    write_current_graph_status(metadata)
    gallery.render_gallery(force=False)
    _json_dump(OUTPUT_ROOT / "RUN_STATUS.json", {"status": "complete", "updated_at_utc": _utc_now(), **metadata})
    print(json.dumps(json_ready({"status": "complete", "metadata": metadata}), indent=2, sort_keys=True))
    return metadata


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resume", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--force-rerun", action="store_true")
    parser.add_argument("--max-runtime-minutes", type=float, default=None)
    parser.add_argument("--row-timeout-seconds", type=float, default=120.0)
    parser.add_argument("--stop-after", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--list-plan", action="store_true")
    parser.add_argument("--only-family", choices=["network_size", "clock_sweep"], default=None)
    parser.add_argument("--only-row", default=None)
    parser.add_argument("--cache-root", default=None)
    parser.add_argument("--dense-clock", action="store_true")
    return parser.parse_args(argv)


if __name__ == "__main__":
    mp.freeze_support()
    run(parse_args())
