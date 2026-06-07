"""Safely replay the legacy notebook clock-sweep figure pair.

The replay executes selected class/helper definitions from ``JCLS_Simulation``
and redirects all outputs under ``v24_notebook_regression_outputs``. It preserves
legacy all-clock, IL/LM/MAP, broad fallback, and plotting behavior as diagnostic
provenance. It does not edit or execute the notebook source as a whole.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
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
OUTPUT_ROOT = (
    SAT_SIM_ROOT
    / "v24_notebook_regression_outputs"
    / "executed_legacy"
    / "clock_sweep_replay"
)
FULL_OUTPUT_ROOT = (
    SAT_SIM_ROOT
    / "v24_notebook_regression_outputs"
    / "executed_legacy"
    / "clock_sweep_replay_full"
)
EXECUTED_LEGACY_ROOT = SAT_SIM_ROOT / "v24_notebook_regression_outputs" / "executed_legacy"
TARGET_FIGURES = ("pos_vary_clock.pdf", "sync_vary_clock.pdf")


class _ProgressBar:
    """Small tqdm-compatible placeholder."""

    def __init__(self, iterable: Any = None, *, total: int | None = None, desc: str = "") -> None:
        self.iterable = iterable
        self.total = total
        self.desc = desc

    def __iter__(self) -> Any:
        return iter(self.iterable)

    def set_description(self, desc: str) -> None:
        self.desc = desc

    def update(self, _count: int) -> None:
        return None

    def close(self) -> None:
        return None


def _tqdm(iterable: Any = None, *args: Any, total: int | None = None, desc: str = "", **_kwargs: Any) -> _ProgressBar:
    """Return a deterministic no-output progress placeholder."""

    return _ProgressBar(iterable, total=total, desc=desc)


def _load_notebook() -> dict[str, Any]:
    """Load notebook JSON without mutating it."""

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
    """Return the first code cell containing a string."""

    for index, source in _code_cells():
        if needle in source:
            return index, source
    raise ValueError(f"Could not find notebook cell containing {needle!r}.")


def _selected_sources() -> list[tuple[int, str, str]]:
    """Return safe class/helper cells needed for clock replay."""

    targets = [
        ("Node", "class Node"),
        ("User", "class User"),
        ("Satellite", "class Satellite"),
        ("Datalink", "class Datalink"),
        ("Scenario", "class Scenario"),
        ("Optimizer", "class Optimizer"),
        ("fit_helpers", "def fit_and_resample_power_law"),
    ]
    sources: list[tuple[int, str, str]] = []
    for name, needle in targets:
        index, source = _find_cell_containing(needle)
        sources.append((index, name, source))
    return sources


def _execute_legacy_namespace() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Execute selected safe definitions in an isolated namespace."""

    import itertools
    import warnings
    from copy import copy

    import sympy as sp
    from scipy.optimize import curve_fit
    from scipy.stats import rv_continuous

    namespace: dict[str, Any] = {
        "np": np,
        "sp": sp,
        "itertools": itertools,
        "copy": copy,
        "warnings": warnings,
        "rv_continuous": rv_continuous,
        "curve_fit": curve_fit,
        "gaussian_filter": gaussian_filter,
        "tqdm": _tqdm,
    }
    executed: list[dict[str, Any]] = []
    for index, name, source in _selected_sources():
        exec(compile(source, f"{NOTEBOOK_PATH}:cell{index}", "exec"), namespace)
        executed.append(
            {
                "cell_index_zero_based": index,
                "cell_number_one_based": index + 1,
                "name": name,
            }
        )
    return namespace, executed


def _hash_file(path: Path) -> str | None:
    """Return SHA256 for an existing file."""

    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _find_existing_artifacts() -> list[dict[str, Any]]:
    """Inventory existing target clock-sweep artifacts without modifying them."""

    artifacts = []
    for figure in TARGET_FIGURES:
        matches = [
            path
            for path in REPO_ROOT.rglob(figure)
            if EXECUTED_LEGACY_ROOT not in path.parents
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


def _generated_artifacts(output_root: Path) -> list[dict[str, Any]]:
    """Return file metadata for replay-generated target PDFs."""

    artifacts = []
    for figure in TARGET_FIGURES:
        path = output_root / figure
        artifacts.append(
            {
                "figure": figure,
                "path": str(path.relative_to(SAT_SIM_ROOT)),
                "exists": path.exists(),
                "size_bytes": path.stat().st_size if path.exists() else None,
                "sha256": _hash_file(path),
            }
        )
    return artifacts


def _series_range(values: np.ndarray) -> dict[str, float | None]:
    """Return finite min/max for a numeric diagnostic series."""

    finite = np.asarray(values, dtype=float)
    finite = finite[np.isfinite(finite)]
    if finite.size == 0:
        return {"min": None, "max": None}
    return {"min": float(np.min(finite)), "max": float(np.max(finite))}


def _legacy_plot(
    x_values: np.ndarray,
    y_series: np.ndarray,
    labels: list[str],
    *,
    xlabel: str,
    ylabel: str,
    output_path: Path,
    log_x: bool,
    log_y: bool,
    y_ticks: list[float] | None,
) -> None:
    """Write a safe approximation of the legacy line plot."""

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
    markers = ["o", "s", "^", "v", "d", "*"]
    linestyles = ["-", "--", ":"]
    for index, values in enumerate(y_series):
        ax.plot(
            x_values,
            values,
            marker=markers[index % len(markers)],
            markerfacecolor="white",
            markersize=3,
            linestyle=linestyles[index % len(linestyles)],
            label=labels[index],
            clip_on=False,
            zorder=3,
        )
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if log_x:
        ax.set_xscale("log")
    if log_y:
        ax.set_yscale("log")
    if y_ticks is not None:
        ax.set_yticks(y_ticks)
    ax.set_xlim(right=1.0e5)
    ax.legend(loc="best", frameon=True, edgecolor="black")
    ax.tick_params(which="both", direction="in", top=True, bottom=True, left=True, right=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, format="pdf")
    plt.close(fig)


def _scenario_result(
    *,
    namespace: dict[str, Any],
    clock_std_dev: float,
    num_iterations: int,
    num_users: int,
    num_satellites: int,
    error_range: float,
) -> dict[str, Any]:
    """Run one legacy clock-sweep row with explicit fallback records."""

    Scenario = namespace["Scenario"]
    Optimizer = namespace["Optimizer"]
    global_map_filter_iteration = namespace["map_filter_iteration"]
    row: dict[str, Any] = {
        "clock_std_dev_seconds": float(clock_std_dev),
        "num_users": num_users,
        "num_satellites": num_satellites,
        "map_iteration_count": num_iterations,
        "truth_centered_initialization": False,
        "true_state_acceptance_gates_used": True,
        "all_clock_state": True,
        "v24_gauged_state": False,
        "fallbacks": [],
        "failures": [],
    }
    scenario = Scenario(
        num_users=num_users,
        num_satellites=num_satellites,
        clock_std_dev_seconds=float(clock_std_dev),
    )
    optimizer = Optimizer()
    x_init = optimizer.initialize_state(scenario, error_range=error_range)
    z = scenario.query_measurements()
    row["state_dimension"] = int(len(scenario.symbolic_parameter_vector))
    row["measurement_count"] = int(len(scenario.get_links()))
    row["symbolic_parameter_order"] = [str(param) for param in scenario.symbolic_parameter_vector]

    try:
        x_il = optimizer.run(
            algorithm="IL",
            scenario=scenario,
            x=x_init,
            z=z,
            num_steps=15,
            tol=1.0e-8,
            verbose=False,
        )
        row["il_status"] = "passed"
    except Exception as exc:  # noqa: BLE001 - legacy replay records broad failure.
        x_il = x_init.copy()
        row["il_status"] = "failed_fallback_to_initial_state"
        row["failures"].append(
            {
                "stage": "IL",
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
        )
        row["fallbacks"].append("IL_failed_to_initial_state")
    row["il_position_error_m"] = float(optimizer.calculate_average_position_error(scenario, x_il))
    row["il_sync_error_s"] = float(optimizer.calculate_average_clock_error(scenario, x_il))

    try:
        x_lm = optimizer.run(
            algorithm="LM",
            scenario=scenario,
            x=x_il,
            z=z,
            num_steps=20,
            verbose=False,
        )
        row["lm_status"] = "passed"
    except Exception as exc:  # noqa: BLE001 - mirrors notebook broad LM fallback.
        x_lm = x_il.copy()
        row["lm_status"] = "failed_fallback_to_il"
        row["failures"].append(
            {
                "stage": "LM",
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
        )
        row["fallbacks"].append("LM_failed_to_IL")
    row["lm_position_error_m"] = float(optimizer.calculate_average_position_error(scenario, x_lm))
    row["lm_sync_error_s"] = float(optimizer.calculate_average_clock_error(scenario, x_lm))

    x_map = x_lm.copy()
    p_matrix = optimizer.calculate_state_covariance(scenario, x_lm) / 1.1
    map_fallback_count = 0
    map_failure_count = 0
    for iteration in range(num_iterations):
        z = scenario.query_measurements()
        try:
            p_matrix, x_map = optimizer.map_filter_iteration(scenario, p_matrix, x_map, z, verbose=False)
            row[f"map_iteration_{iteration}_path"] = "optimizer_method"
        except Exception as method_exc:  # noqa: BLE001 - notebook expects this fallback.
            try:
                p_matrix, x_map = global_map_filter_iteration(None, scenario, p_matrix, x_map, z, verbose=False)
                map_fallback_count += 1
                row["fallbacks"].append("MAP_optimizer_method_missing_global_fallback")
                row[f"map_iteration_{iteration}_path"] = "global_fallback"
            except Exception as global_exc:  # noqa: BLE001 - record and keep prior MAP state.
                map_failure_count += 1
                row[f"map_iteration_{iteration}_path"] = "failed_keep_previous"
                row["failures"].append(
                    {
                        "stage": "MAP",
                        "iteration": iteration,
                        "method_error_type": type(method_exc).__name__,
                        "method_error": str(method_exc),
                        "global_error_type": type(global_exc).__name__,
                        "global_error": str(global_exc),
                    }
                )
                row["fallbacks"].append("MAP_failed_keep_previous")
                break
    row["map_fallback_count"] = map_fallback_count
    row["map_failure_count"] = map_failure_count
    row["map_position_error_m"] = float(optimizer.calculate_average_position_error(scenario, x_map))
    row["map_sync_error_s"] = float(optimizer.calculate_average_clock_error(scenario, x_map))
    row["success"] = row["il_status"] == "passed" and row["lm_status"] == "passed" and map_failure_count == 0
    return row


def _mode_config(mode: str) -> dict[str, Any]:
    """Return replay configuration for smoke or full mode."""

    if mode == "full":
        return {
            "mode": "full",
            "clock_std_devs": np.logspace(-4, -10, 7),
            "num_iterations": 25,
            "num_users": 3,
            "num_satellites": 10,
            "error_range": 100.0,
            "seed": 2031,
        }
    return {
        "mode": "smoke",
        "clock_std_devs": np.array([1.0e-4, 1.0e-7, 1.0e-10]),
        "num_iterations": 2,
        "num_users": 3,
        "num_satellites": 5,
        "error_range": 100.0,
        "seed": 2030,
    }


def _write_raw_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write raw row diagnostics."""

    fieldnames = [
        "clock_std_dev_seconds",
        "num_users",
        "num_satellites",
        "map_iteration_count",
        "state_dimension",
        "measurement_count",
        "il_status",
        "lm_status",
        "map_fallback_count",
        "map_failure_count",
        "il_position_error_m",
        "lm_position_error_m",
        "map_position_error_m",
        "il_sync_error_s",
        "lm_sync_error_s",
        "map_sync_error_s",
        "success",
        "fallbacks",
        "failures",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    field: json.dumps(row[field]) if field in {"fallbacks", "failures"} else row.get(field)
                    for field in fieldnames
                }
            )


def _write_summary_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write compact summary diagnostics."""

    total = len(rows)
    failures = sum(1 for row in rows if row["failures"])
    fallbacks = sum(len(row["fallbacks"]) for row in rows)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "mode",
                "row_count",
                "successful_rows",
                "rows_with_failures",
                "total_fallback_events",
                "il_failures",
                "lm_failures",
                "map_failures",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "mode": rows[0].get("mode", "unknown") if rows else "unknown",
                "row_count": total,
                "successful_rows": sum(1 for row in rows if row["success"]),
                "rows_with_failures": failures,
                "total_fallback_events": fallbacks,
                "il_failures": sum(1 for row in rows if row["il_status"] != "passed"),
                "lm_failures": sum(1 for row in rows if row["lm_status"] != "passed"),
                "map_failures": sum(row["map_failure_count"] for row in rows),
            }
        )


def replay_legacy_clock_sweep(*, mode: str = "smoke", output_root: Path = OUTPUT_ROOT) -> dict[str, Any]:
    """Replay the legacy clock-sweep figure pair in smoke or full mode."""

    start_time = time.perf_counter()
    output_root.mkdir(parents=True, exist_ok=True)
    config = _mode_config(mode)
    np.random.seed(int(config["seed"]))
    namespace, executed_cells = _execute_legacy_namespace()
    rows = []
    for clock_std_dev in config["clock_std_devs"]:
        row = _scenario_result(
            namespace=namespace,
            clock_std_dev=float(clock_std_dev),
            num_iterations=int(config["num_iterations"]),
            num_users=int(config["num_users"]),
            num_satellites=int(config["num_satellites"]),
            error_range=float(config["error_range"]),
        )
        row["mode"] = mode
        rows.append(row)

    clock_std_devs = np.asarray([row["clock_std_dev_seconds"] for row in rows], dtype=float)
    il_pos = np.asarray([row["il_position_error_m"] for row in rows], dtype=float)
    lm_pos = np.asarray([row["lm_position_error_m"] for row in rows], dtype=float)
    map_pos = np.asarray([row["map_position_error_m"] for row in rows], dtype=float)
    il_sync = np.asarray([row["il_sync_error_s"] for row in rows], dtype=float)
    lm_sync = np.asarray([row["lm_sync_error_s"] for row in rows], dtype=float)
    map_sync = np.asarray([row["map_sync_error_s"] for row in rows], dtype=float)

    fit = namespace["fit_and_resample_power_law"]
    il_pos_fitted = np.asarray(fit(clock_std_devs, il_pos, clock_std_devs), dtype=float)
    pos_y = gaussian_filter(np.vstack([il_pos_fitted, lm_pos, map_pos]), sigma=0.25)
    sync_y = gaussian_filter(np.vstack([il_sync, lm_sync, map_sync]), sigma=0.65) * 1.0e9
    x_values_ns = clock_std_devs * 1.0e9

    labels = ["Without cooperation", "Coarse JCLS", "Refined JCLS, $.5\\,$ns"]
    pos_xlabel = r"$\sigma_\delta \; [\mathrm{ns}]$"
    pos_ylabel = r"Average UE position error $[\mathrm{m}]$"
    _legacy_plot(
        x_values_ns,
        pos_y,
        labels,
        xlabel=pos_xlabel,
        ylabel=pos_ylabel,
        output_path=output_root / "pos_vary_clock.pdf",
        log_x=True,
        log_y=True,
        y_ticks=[1.0e-2, 1.0e0, 1.0e2, 1.0e4],
    )
    sync_labels = ["Without cooperation", "Coarse JCLS", "Refined JCLS, $.5\\,$s"]
    sync_xlabel = r"$\sigma_\delta \; [\mathrm{ns}]$"
    sync_ylabel = r"Average synchronization error $[\mathrm{ns}]$"
    _legacy_plot(
        x_values_ns,
        sync_y,
        sync_labels,
        xlabel=sync_xlabel,
        ylabel=sync_ylabel,
        output_path=output_root / "sync_vary_clock.pdf",
        log_x=True,
        log_y=True,
        y_ticks=[1.0, 1.0e2, 1.0e4],
    )

    _write_raw_csv(output_root / "legacy_clock_sweep_raw.csv", rows)
    _write_summary_csv(output_root / "legacy_clock_sweep_summary.csv", rows)
    np.savez(
        output_root / "legacy_clock_sweep_arrays.npz",
        clock_std_devs=clock_std_devs,
        il_pos=il_pos,
        lm_pos=lm_pos,
        map_pos=map_pos,
        il_sync=il_sync,
        lm_sync=lm_sync,
        map_sync=map_sync,
        pos_plot_y_m=pos_y,
        sync_plot_y_ns=sync_y,
    )

    runtime_seconds = time.perf_counter() - start_time
    failures = [failure for row in rows for failure in row["failures"]]
    if failures:
        (output_root / "legacy_clock_sweep_failures.json").write_text(
            json.dumps(failures, indent=2),
            encoding="utf-8",
        )
        (output_root / "legacy_clock_sweep_failures.md").write_text(
            "\n".join(
                [
                    "# Legacy Clock-Sweep Failure Log",
                    "",
                    *[
                        f"- {failure.get('stage')} {failure.get('error_type', failure.get('global_error_type'))}: {failure}"
                        for failure in failures
                    ],
                    "",
                ]
            ),
            encoding="utf-8",
        )

    status = "legacy_full_replayed_unverified_match" if mode == "full" else "legacy_replayed_unverified_match"
    artifact_status = (
        "non_final_legacy_clock_sweep_full_replay"
        if mode == "full"
        else "non_final_legacy_clock_sweep_replay"
    )
    comparison_status = "full_unverified_match" if mode == "full" else "unverified_match"
    report = {
        "status": status,
        "artifact_status": artifact_status,
        "legacy_replay": True,
        "manuscript_ready": False,
        "not_for_manuscript_submission": True,
        "mode": mode,
        "full_mode_completed": mode == "full",
        "runtime_seconds": runtime_seconds,
        "output_root": str(output_root.relative_to(SAT_SIM_ROOT)),
        "notebook_source_modified": False,
        "full_notebook_executed": False,
        "colab_setup_executed": False,
        "workspace_pickle_executed": False,
        "manuscript_output_paths_written": False,
        "seed": int(config["seed"]),
        "rng_seed_status": "deterministic_np_random_seed_set_before_replay",
        "clock_std_devs": clock_std_devs.tolist(),
        "num_iterations": int(config["num_iterations"]),
        "num_users": int(config["num_users"]),
        "num_satellites": int(config["num_satellites"]),
        "error_range": float(config["error_range"]),
        "executed_cells": executed_cells,
        "cells_functions_extracted": [
            "Node",
            "User",
            "Satellite",
            "Datalink",
            "Scenario",
            "Optimizer",
            "map_filter_iteration",
            "fit_and_resample_power_law",
            "cell31_generate_data_for_clock_std_dev_logic_reimplemented_with_logging",
            "cell32_plotting_transform_logic_replayed",
        ],
        "legacy_caveats": {
            "truth_centered_initialization": False,
            "true_state_acceptance_gates_used": True,
            "lm_reverts_or_accepts_based_on_true_state_error": True,
            "map_reverts_based_on_true_state_error": True,
            "exceptions_fall_back_to_il_or_previous_state": True,
            "all_clock_symbolic_state": True,
            "v24_gauging_absent": True,
            "smoothing_fitting_manual_transforms_applied": True,
            "legacy_sync_metric_averages_all_clock_symbols": True,
            "classification": "legacy_only_unsafe_for_v24_claims_without_replacement_or_human_review",
        },
        "counts": {
            "row_count": len(rows),
            "successful_rows": sum(1 for row in rows if row["success"]),
            "rows_with_failures": sum(1 for row in rows if row["failures"]),
            "total_fallback_events": sum(len(row["fallbacks"]) for row in rows),
            "il_failures": sum(1 for row in rows if row["il_status"] != "passed"),
            "lm_failures": sum(1 for row in rows if row["lm_status"] != "passed"),
            "map_failures": sum(row["map_failure_count"] for row in rows),
            "map_global_fallback_count": sum(row["map_fallback_count"] for row in rows),
        },
        "per_clock_std_results": rows,
        "data_ranges": {
            "clock_std_dev_ns": _series_range(x_values_ns),
            "raw_position_error_m": {
                "without_cooperation": _series_range(il_pos),
                "coarse_jcls": _series_range(lm_pos),
                "refined_jcls": _series_range(map_pos),
            },
            "raw_sync_error_s": {
                "without_cooperation": _series_range(il_sync),
                "coarse_jcls": _series_range(lm_sync),
                "refined_jcls": _series_range(map_sync),
            },
            "plotted_position_error_m": {
                "without_cooperation": _series_range(pos_y[0]),
                "coarse_jcls": _series_range(pos_y[1]),
                "refined_jcls": _series_range(pos_y[2]),
            },
            "plotted_sync_error_ns": {
                "without_cooperation": _series_range(sync_y[0]),
                "coarse_jcls": _series_range(sync_y[1]),
                "refined_jcls": _series_range(sync_y[2]),
            },
        },
        "plot_axis_labels": {
            "pos_vary_clock.pdf": {
                "xlabel": pos_xlabel,
                "ylabel": pos_ylabel,
                "xscale": "log",
                "yscale": "log",
            },
            "sync_vary_clock.pdf": {
                "xlabel": sync_xlabel,
                "ylabel": sync_ylabel,
                "xscale": "log",
                "yscale": "log",
            },
        },
        "raw_outputs": {
            "raw_csv": str((output_root / "legacy_clock_sweep_raw.csv").relative_to(SAT_SIM_ROOT)),
            "summary_csv": str((output_root / "legacy_clock_sweep_summary.csv").relative_to(SAT_SIM_ROOT)),
            "arrays_npz": str((output_root / "legacy_clock_sweep_arrays.npz").relative_to(SAT_SIM_ROOT)),
        },
        "plot_outputs": [
            str((output_root / "pos_vary_clock.pdf").relative_to(SAT_SIM_ROOT)),
            str((output_root / "sync_vary_clock.pdf").relative_to(SAT_SIM_ROOT)),
        ],
        "existing_artifact_comparison": {
            "replayed_artifacts": _generated_artifacts(output_root),
            "existing_artifacts": _find_existing_artifacts(),
            "comparison_status": comparison_status,
            "claim_match": False,
            "note": "Existing artifacts are inventoried but no visual/data equality is claimed.",
        },
        "commands_to_rerun": [
            "python scripts/replay_legacy_clock_sweep_figures.py --smoke",
            "python scripts/replay_legacy_clock_sweep_figures.py --full",
        ],
        "next_recommended_figure_family": "pos_vary_ues.pdf and sync_vary_ues.pdf",
    }
    (output_root / "legacy_clock_sweep_metadata.json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )
    (output_root / "legacy_clock_sweep_metadata.md").write_text(
        "\n".join(
            [
                "# Legacy Clock-Sweep Replay Metadata",
                "",
                f"- Status: `{report['status']}`",
                f"- Mode: `{mode}`",
                f"- Output root: `{report['output_root']}`",
                f"- Manuscript ready: `{report['manuscript_ready']}`",
                f"- Row count: {report['counts']['row_count']}",
                f"- Rows with failures: {report['counts']['rows_with_failures']}",
                f"- Total fallback events: {report['counts']['total_fallback_events']}",
                "",
                "## Caveats",
                "",
                *[
                    f"- `{key}`: {value}"
                    for key, value in report["legacy_caveats"].items()
                ],
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return report


def _update_figure_regression_table(report: dict[str, Any]) -> None:
    """Update target figure statuses for the clock-sweep pair."""

    table_path = SAT_SIM_ROOT / "v24_notebook_regression_outputs" / "FIGURE_REGRESSION_TABLE.json"
    if not table_path.exists():
        return
    table = json.loads(table_path.read_text(encoding="utf-8"))
    status = report["status"]
    for entry in table.get("target_figure_statuses", []):
        if entry.get("figure") in TARGET_FIGURES:
            entry["status"] = status
            entry["legacy_replay"] = True
            entry["full_legacy_replay"] = report["mode"] == "full"
            entry["manuscript_ready"] = False
            entry["replayed_output_root"] = report["output_root"]
            if report["mode"] == "full":
                entry["reason"] = (
                    "Full legacy notebook clock-sweep logic replayed in redirected diagnostics; "
                    "match is unverified and legacy caveats remain."
                )
            else:
                entry["reason"] = (
                    "Legacy notebook clock-sweep logic replayed in redirected diagnostics; "
                    "match is unverified and legacy caveats remain."
                )
    table["clock_sweep_replay_report"] = str(
        (Path(report["output_root"]) / "legacy_clock_sweep_metadata.json")
    )
    table["reproduction_status"] = (
        "legacy_clock_sweep_full_replayed_unverified_match"
        if report["mode"] == "full"
        else "legacy_clock_sweep_replayed_unverified_match"
    )
    table_path.write_text(json.dumps(table, indent=2), encoding="utf-8")

    lines = [
        "# Figure Regression Table",
        "",
        "- Existing static mapping records are preserved in the JSON.",
        "- CRLB and clock-sweep target figures have safe legacy replay outputs, but are not manuscript-ready.",
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
            f"- Clock-sweep replay report: `{table.get('clock_sweep_replay_report')}`",
        ]
    )
    table_path.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_top_level_report(report: dict[str, Any]) -> None:
    """Write top-level paired report files."""

    output_dir = SAT_SIM_ROOT / "v24_notebook_regression_outputs"
    payload = dict(report)
    if payload["mode"] == "full":
        payload["report_type"] = "legacy_clock_sweep_full_replay_report"
        json_path = output_dir / "LEGACY_CLOCK_SWEEP_FULL_REPLAY_REPORT.json"
        md_path = output_dir / "LEGACY_CLOCK_SWEEP_FULL_REPLAY_REPORT.md"
        title = "Legacy Clock-Sweep Full Replay Report"
    else:
        payload["report_type"] = "legacy_clock_sweep_replay_report"
        json_path = output_dir / "LEGACY_CLOCK_SWEEP_REPLAY_REPORT.json"
        md_path = output_dir / "LEGACY_CLOCK_SWEEP_REPLAY_REPORT.md"
        title = "Legacy Clock-Sweep Replay Report"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md_lines = [
        f"# {title}",
        "",
        f"- Status: `{payload['status']}`",
        f"- Mode: `{payload['mode']}`",
        f"- Runtime seconds: {payload['runtime_seconds']:.3f}",
        f"- Output root: `{payload['output_root']}`",
        f"- Manuscript ready: `{payload['manuscript_ready']}`",
        "",
        "## Outputs",
        "",
        *[f"- `{path}`" for path in payload["raw_outputs"].values()],
        *[f"- `{path}`" for path in payload["plot_outputs"]],
        "",
        "## Counts",
        "",
        *[f"- `{key}`: {value}" for key, value in payload["counts"].items()],
        "",
        "## Caveats",
        "",
        *[f"- `{key}`: {value}" for key, value in payload["legacy_caveats"].items()],
        "",
        "## Commands",
        "",
        *[f"- `{command}`" for command in payload["commands_to_rerun"]],
    ]
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--smoke", action="store_true", help="Run reduced deterministic smoke replay.")
    group.add_argument("--full", action="store_true", help="Run legacy-sized replay for human use.")
    parser.add_argument("--output-root", type=Path, default=None)
    return parser.parse_args()


def _write_execution_failure(mode: str, output_root: Path, error: Exception) -> None:
    """Write precise failure diagnostics for a failed replay."""

    output_root.mkdir(parents=True, exist_ok=True)
    payload = {
        "mode": mode,
        "legacy_replay": True,
        "manuscript_ready": False,
        "not_for_manuscript_submission": True,
        "artifact_status": "non_final_legacy_clock_sweep_replay_failure",
        "status": "legacy_full_replay_failed" if mode == "full" else "legacy_replay_failed",
        "error_type": type(error).__name__,
        "error_message": str(error),
        "output_root": str(output_root.relative_to(SAT_SIM_ROOT)),
    }
    (output_root / "legacy_clock_sweep_execution_failure.json").write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )
    (output_root / "legacy_clock_sweep_execution_failure.md").write_text(
        "\n".join(
            [
                "# Legacy Clock-Sweep Replay Execution Failure",
                "",
                f"- Mode: `{mode}`",
                f"- Status: `{payload['status']}`",
                f"- Error type: `{payload['error_type']}`",
                f"- Error message: {payload['error_message']}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> int:
    args = _parse_args()
    mode = "full" if args.full else "smoke"
    output_root = args.output_root or (FULL_OUTPUT_ROOT if mode == "full" else OUTPUT_ROOT)
    if SAT_SIM_ROOT not in output_root.resolve().parents and output_root.resolve() != SAT_SIM_ROOT:
        raise ValueError("output-root must be inside sat-sim.")
    try:
        report = replay_legacy_clock_sweep(mode=mode, output_root=output_root)
    except Exception as error:
        _write_execution_failure(mode, output_root, error)
        raise
    _update_figure_regression_table(report)
    _write_top_level_report(report)
    print(
        json.dumps(
            {
                "status": report["status"],
                "mode": mode,
                "runtime_seconds": report["runtime_seconds"],
                "output_root": report["output_root"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
