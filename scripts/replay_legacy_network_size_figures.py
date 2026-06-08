"""Replay legacy-compatible network-size estimator diagnostics.

This runner preserves the safe extracted-notebook path used by the clock-sweep
replay and writes non-final diagnostics under ``outputs/legacy_replay``. It is
not a manuscript figure generator and does not edit the notebook.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


SAT_SIM_ROOT = Path(__file__).resolve().parents[1]
if str(SAT_SIM_ROOT) not in sys.path:
    sys.path.insert(0, str(SAT_SIM_ROOT))

try:  # noqa: SIM105 - support script execution and package import.
    from replay_legacy_clock_sweep_figures import (  # type: ignore  # noqa: E402
        NOTEBOOK_PATH,
        _cache_key,
        _canonical_json,
        _execute_legacy_namespace,
        _git_metadata,
        _hash_file,
        _hash_text,
        _scenario_result,
        _selected_cell_hashes,
    )
except ModuleNotFoundError:  # pragma: no cover - exercised by unittest package imports.
    from scripts.replay_legacy_clock_sweep_figures import (  # type: ignore  # noqa: E402
        NOTEBOOK_PATH,
        _cache_key,
        _canonical_json,
        _execute_legacy_namespace,
        _git_metadata,
        _hash_file,
        _hash_text,
        _scenario_result,
        _selected_cell_hashes,
    )


DEFAULT_OUTPUT_ROOT = SAT_SIM_ROOT / "outputs" / "legacy_replay" / "network_size_medium"
DEFAULT_CACHE_ROOT = SAT_SIM_ROOT / "outputs" / "cache"
CACHE_SCHEMA_VERSION = "legacy-network-size-grid-row-v2"
TARGET_FIGURES = ("pos_vary_ues.pdf", "sync_vary_ues.pdf")


def _mode_config(mode: str) -> dict[str, Any]:
    """Return deterministic replay configuration for a mode."""

    if mode == "smoke":
        return {
            "mode": "smoke",
            "num_users_range": [1, 3],
            "num_satellites_range": [4, 8, 12],
            "clock_std_dev": 0.5e-9,
            "num_iterations": 2,
            "error_range": 100.0,
            "seed": 2042,
            "estimator_mode": "legacy_il_lm_map_filter_iteration",
            "single_ue_policy": "noncooperative_clockless_baseline_only",
        }
    if mode == "medium":
        return {
            "mode": "medium",
            "num_users_range": [1, 3, 5, 7],
            "num_satellites_range": [4, 8, 12],
            "clock_std_dev": 0.5e-9,
            "num_iterations": 5,
            "requested_num_iterations_note": "25 MAP iterations requested where feasible; medium diagnostic uses 5 to keep runtime bounded.",
            "error_range": 100.0,
            "seed": 2042,
            "estimator_mode": "legacy_il_lm_map_filter_iteration",
            "single_ue_policy": "noncooperative_clockless_baseline_only",
        }
    if mode == "full":
        return {
            "mode": "full",
            "num_users_range": [1, 3, 5, 7],
            "num_satellites_range": list(range(3, 16)),
            "clock_std_dev": 0.5e-9,
            "num_iterations": 25,
            "error_range": 100.0,
            "seed": 2042,
            "estimator_mode": "legacy_il_lm_map_filter_iteration",
            "single_ue_policy": "noncooperative_clockless_baseline_only",
        }
    raise ValueError(f"Unsupported network-size replay mode: {mode}")


def _default_output_root(mode: str) -> Path:
    """Return canonical output root for a replay mode."""

    suffix = {"smoke": "network_size", "medium": "network_size_medium", "full": "network_size_full"}[mode]
    return SAT_SIM_ROOT / "outputs" / "legacy_replay" / suffix


def _identity(config: dict[str, Any], num_users: int, num_satellites: int) -> dict[str, Any]:
    """Return deterministic row cache identity."""

    return {
        "cache_schema_version": CACHE_SCHEMA_VERSION,
        "script_name": Path(__file__).name,
        "script_sha256": _hash_file(Path(__file__).resolve()),
        "notebook_sha256": _hash_file(NOTEBOOK_PATH),
        "extracted_cell_hashes": _selected_cell_hashes(),
        "config": {
            **config,
            "num_users": int(num_users),
            "num_satellites": int(num_satellites),
        },
    }


def _cache_paths(cache_root: Path, key: str) -> dict[str, Path]:
    """Return row cache paths."""

    row_dir = cache_root / "legacy_network_size" / key[:16]
    return {"dir": row_dir, "metadata": row_dir / "metadata.json", "row": row_dir / "row.json"}


def _row_hash(row: dict[str, Any]) -> str:
    """Return row hash."""

    return _hash_text(_canonical_json(row))


def _load_cache(cache_root: Path, identity: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Load a valid row cache entry."""

    key = _cache_key(identity)
    paths = _cache_paths(cache_root, key)
    cfg = identity["config"]
    event = {
        "cache_key": key,
        "mode": cfg["mode"],
        "num_users": cfg["num_users"],
        "num_satellites": cfg["num_satellites"],
        "hit": False,
        "fresh": False,
        "invalidation_reason": None,
    }
    if not paths["metadata"].exists() or not paths["row"].exists():
        event["invalidation_reason"] = "missing_cache_entry"
        events.append(event)
        return None
    metadata = json.loads(paths["metadata"].read_text(encoding="utf-8"))
    if metadata.get("status") != "complete":
        event["invalidation_reason"] = f"cache_status_{metadata.get('status')}"
        events.append(event)
        return None
    row = json.loads(paths["row"].read_text(encoding="utf-8"))
    if metadata.get("cache_key") != key or metadata.get("identity") != identity:
        event["invalidation_reason"] = "metadata_identity_mismatch"
        events.append(event)
        return None
    if metadata.get("raw_result_hash") != _row_hash(row):
        event["invalidation_reason"] = "raw_result_hash_mismatch"
        events.append(event)
        return None
    event.update({"hit": True, "fresh": True, "cache_path": str(paths["metadata"].relative_to(SAT_SIM_ROOT)).replace("\\", "/")})
    events.append(event)
    row["cache_used"] = True
    return row


def _write_cache(cache_root: Path, identity: dict[str, Any], row: dict[str, Any]) -> None:
    """Write a row cache entry."""

    key = _cache_key(identity)
    paths = _cache_paths(cache_root, key)
    paths["dir"].mkdir(parents=True, exist_ok=True)
    cached = dict(row)
    cached["cache_used"] = False
    cached["cache_key"] = key
    paths["row"].write_text(json.dumps(cached, indent=2), encoding="utf-8")
    metadata = {
        "status": "complete",
        "cache_key": key,
        "identity": identity,
        "raw_result_hash": _row_hash(cached),
        "row_json": str(paths["row"].relative_to(SAT_SIM_ROOT)).replace("\\", "/"),
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        **_git_metadata(),
    }
    paths["metadata"].write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def _write_cache_manifest(cache_root: Path, events: list[dict[str, Any]], mode: str) -> dict[str, Any]:
    """Write canonical cache manifest."""

    cache_root.mkdir(parents=True, exist_ok=True)
    manifest = {
        "artifact_status": "non_final_cache_manifest",
        "cache_schema_version": CACHE_SCHEMA_VERSION,
        "mode": mode,
        "events": events,
        "fresh_hit_count": sum(1 for event in events if event.get("fresh")),
        "miss_or_stale_count": sum(1 for event in events if not event.get("fresh")),
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        **_git_metadata(),
    }
    (cache_root / "CACHE_MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    md = [
        "# Cache Manifest",
        "",
        f"- Schema: `{CACHE_SCHEMA_VERSION}`",
        f"- Mode: `{mode}`",
        f"- Fresh hits: {manifest['fresh_hit_count']}",
        f"- Miss/stale: {manifest['miss_or_stale_count']}",
        "",
        "| Users | Satellites | Hit | Fresh | Reason |",
        "|---:|---:|---:|---:|---|",
    ]
    for event in events:
        md.append(
            f"| {event.get('num_users')} | {event.get('num_satellites')} | {event.get('hit')} | {event.get('fresh')} | {event.get('invalidation_reason') or ''} |"
        )
    (cache_root / "CACHE_MANIFEST.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return manifest


def _single_ue_baseline_row(namespace: dict[str, Any], config: dict[str, Any], num_satellites: int) -> dict[str, Any]:
    """Run only the noncooperative/clockless baseline for the single-UE row."""

    row = _scenario_result(
        namespace=namespace,
        clock_std_dev=float(config["clock_std_dev"]),
        num_iterations=0,
        num_users=1,
        num_satellites=int(num_satellites),
        error_range=float(config["error_range"]),
    )
    row["num_users"] = 1
    row["num_satellites"] = int(num_satellites)
    row["single_ue_policy"] = config["single_ue_policy"]
    row["cooperative_jcls_attempted"] = False
    row["lm_status"] = "not_attempted_single_ue_baseline"
    row["map_status"] = "not_attempted_single_ue_baseline"
    row["lm_position_error_m"] = row["il_position_error_m"]
    row["map_position_error_m"] = row["il_position_error_m"]
    row["lm_sync_error_s"] = row["il_sync_error_s"]
    row["map_sync_error_s"] = row["il_sync_error_s"]
    row["success"] = bool(row.get("il_status") == "passed")
    row.setdefault("fallbacks", []).append({"stage": "LM/MAP", "reason": "single_ue_noncooperative_baseline_only"})
    return row


def _run_row(namespace: dict[str, Any], config: dict[str, Any], num_users: int, num_satellites: int) -> dict[str, Any]:
    """Run or emulate one legacy network-size row."""

    if int(num_users) == 1:
        return _single_ue_baseline_row(namespace, config, int(num_satellites))
    row = _scenario_result(
        namespace=namespace,
        clock_std_dev=float(config["clock_std_dev"]),
        num_iterations=int(config["num_iterations"]),
        num_users=int(num_users),
        num_satellites=int(num_satellites),
        error_range=float(config["error_range"]),
    )
    row["num_users"] = int(num_users)
    row["num_satellites"] = int(num_satellites)
    row["single_ue_policy"] = "not_applicable"
    row["cooperative_jcls_attempted"] = True
    return row


def _plot(x: np.ndarray, series: dict[str, np.ndarray], output_path: Path, ylabel: str) -> None:
    """Write a diagnostic line plot."""

    fig, ax = plt.subplots(figsize=(4.4, 3.2), dpi=240)
    for label, values in series.items():
        ax.plot(x, values, marker="o", label=label)
    ax.set_xlabel("Number of satellites")
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best", fontsize=7, frameon=True)
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path)
    plt.close(fig)


def _series(rows: list[dict[str, Any]], users: list[int], sats: list[int], metric: str) -> dict[str, np.ndarray]:
    """Return plot series from rows."""

    by_key = {(int(row["num_users"]), int(row["num_satellites"])): row for row in rows}
    out: dict[str, np.ndarray] = {}
    for user in users:
        label = "Without cooperation (single UE)" if user == 1 else f"Refined JCLS ({user} UEs)"
        out[label] = np.asarray([float(by_key[(user, sat)][metric]) for sat in sats], dtype=float)
    return out


def _write_outputs(output_root: Path, rows: list[dict[str, Any]], config: dict[str, Any], manifest: dict[str, Any], runtime: float) -> dict[str, Any]:
    """Write CSV, NPZ, plots, metadata, and reports."""

    output_root.mkdir(parents=True, exist_ok=True)
    users = [int(x) for x in config["num_users_range"]]
    sats = [int(x) for x in config["num_satellites_range"]]
    raw_csv = output_root / "legacy_network_size_raw.csv"
    summary_csv = output_root / "legacy_network_size_summary.csv"
    fields = [
        "mode", "num_users", "num_satellites", "clock_std_dev_seconds", "map_iteration_count",
        "measurement_count", "state_dimension", "cooperative_jcls_attempted", "single_ue_policy",
        "il_position_error_m", "lm_position_error_m", "map_position_error_m",
        "il_sync_error_s", "lm_sync_error_s", "map_sync_error_s",
        "success", "cache_used", "fallback_count", "failure_count", "fallbacks", "failures",
    ]
    with raw_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            record = {field: row.get(field) for field in fields}
            record["mode"] = config["mode"]
            record["fallback_count"] = len(row.get("fallbacks", []))
            record["failure_count"] = len(row.get("failures", []))
            record["fallbacks"] = json.dumps(row.get("fallbacks", []))
            record["failures"] = json.dumps(row.get("failures", []))
            writer.writerow(record)
    with summary_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["mode", "num_users", "mean_position_error_m", "mean_sync_error_ns", "row_count", "fallback_count", "failure_count"])
        writer.writeheader()
        for user in users:
            subset = [row for row in rows if int(row["num_users"]) == user]
            writer.writerow({
                "mode": config["mode"],
                "num_users": user,
                "mean_position_error_m": float(np.mean([row["map_position_error_m"] for row in subset])),
                "mean_sync_error_ns": float(np.mean([row["map_sync_error_s"] for row in subset]) * 1e9),
                "row_count": len(subset),
                "fallback_count": sum(len(row.get("fallbacks", [])) for row in subset),
                "failure_count": sum(len(row.get("failures", [])) for row in subset),
            })
    x = np.asarray(sats, dtype=float)
    pos_series = _series(rows, users, sats, "map_position_error_m")
    sync_series = {label: values * 1e9 for label, values in _series(rows, users, sats, "map_sync_error_s").items()}
    pos_pdf = output_root / "pos_vary_ues.pdf"
    sync_pdf = output_root / "sync_vary_ues.pdf"
    _plot(x, pos_series, pos_pdf, "Average UE position error [m]")
    _plot(x, sync_series, sync_pdf, "Average synchronization error [ns]")
    arrays = {
        "num_users": np.asarray(users, dtype=int),
        "num_satellites": np.asarray(sats, dtype=int),
        "map_position_error_m": np.vstack([pos_series["Without cooperation (single UE)"] if user == 1 else pos_series[f"Refined JCLS ({user} UEs)"] for user in users]),
        "map_sync_error_ns": np.vstack([sync_series["Without cooperation (single UE)"] if user == 1 else sync_series[f"Refined JCLS ({user} UEs)"] for user in users]),
    }
    np.savez(output_root / "legacy_network_size_arrays.npz", **arrays)
    improvement = _trend_summary(rows, users, sats)
    report = {
        "artifact_status": f"non_final_legacy_network_size_{config['mode']}_replay",
        "status": f"legacy_network_size_{config['mode']}_replayed_unverified_match",
        "mode": config["mode"],
        "legacy_replay": True,
        "manuscript_ready": False,
        "not_for_manuscript_submission": True,
        "output_root": str(output_root.relative_to(SAT_SIM_ROOT)).replace("\\", "/"),
        "runtime_seconds": runtime,
        "config": config,
        "counts": {
            "row_count": len(rows),
            "cache_hit_count": sum(1 for row in rows if row.get("cache_used")),
            "cache_miss_count": sum(1 for row in rows if not row.get("cache_used")),
            "total_fallback_events": sum(len(row.get("fallbacks", [])) for row in rows),
            "rows_with_failures": sum(1 for row in rows if row.get("failures")),
        },
        "trend_summary": improvement,
        "legacy_caveats": {
            "all_clock_symbolic_state": True,
            "v24_gauging_absent": True,
            "truth_error_acceptance_gates_used": True,
            "legacy_sync_metric_averages_all_clock_symbols": True,
            "single_ue_is_noncooperative_baseline_only": True,
            "not_claimed_to_match_manuscript_figures": True,
        },
        "raw_outputs": {
            "raw_csv": str(raw_csv.relative_to(SAT_SIM_ROOT)).replace("\\", "/"),
            "summary_csv": str(summary_csv.relative_to(SAT_SIM_ROOT)).replace("\\", "/"),
            "arrays_npz": str((output_root / "legacy_network_size_arrays.npz").relative_to(SAT_SIM_ROOT)).replace("\\", "/"),
        },
        "plot_outputs": [str(pos_pdf.relative_to(SAT_SIM_ROOT)).replace("\\", "/"), str(sync_pdf.relative_to(SAT_SIM_ROOT)).replace("\\", "/")],
        "cache_manifest": {
            "json": str((DEFAULT_CACHE_ROOT / "CACHE_MANIFEST.json").relative_to(SAT_SIM_ROOT)).replace("\\", "/"),
            "md": str((DEFAULT_CACHE_ROOT / "CACHE_MANIFEST.md").relative_to(SAT_SIM_ROOT)).replace("\\", "/"),
            "fresh_hit_count": manifest["fresh_hit_count"],
            "miss_or_stale_count": manifest["miss_or_stale_count"],
        },
        **_git_metadata(),
    }
    (output_root / "legacy_network_size_metadata.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    _write_network_size_markdown(output_root, report)
    reports = SAT_SIM_ROOT / "outputs" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "LEGACY_NETWORK_SIZE_REPLAY_REPORT.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    _write_network_size_report(reports / "LEGACY_NETWORK_SIZE_REPLAY_REPORT.md", report)
    _update_figure_regression_table(report)
    return report


def _trend_summary(rows: list[dict[str, Any]], users: list[int], sats: list[int]) -> dict[str, Any]:
    """Summarize where JCLS improves over the single-UE baseline."""

    by_key = {(int(row["num_users"]), int(row["num_satellites"])): row for row in rows}
    comparisons = []
    for sat in sats:
        base = by_key.get((1, sat))
        if not base:
            continue
        for user in users:
            if user == 1:
                continue
            row = by_key[(user, sat)]
            comparisons.append({
                "num_users": user,
                "num_satellites": sat,
                "position_improvement_m": float(base["map_position_error_m"] - row["map_position_error_m"]),
                "sync_improvement_ns": float((base["map_sync_error_s"] - row["map_sync_error_s"]) * 1e9),
                "position_ratio_jcls_over_baseline": float(row["map_position_error_m"] / base["map_position_error_m"]) if base["map_position_error_m"] else None,
                "sync_ratio_jcls_over_baseline": float(row["map_sync_error_s"] / base["map_sync_error_s"]) if base["map_sync_error_s"] else None,
            })
    pos_wins = [item for item in comparisons if item["position_improvement_m"] > 0]
    sync_wins = [item for item in comparisons if item["sync_improvement_ns"] > 0]
    strongest_pos = max(comparisons, key=lambda item: item["position_improvement_m"], default=None)
    strongest_sync = max(comparisons, key=lambda item: item["sync_improvement_ns"], default=None)
    return {
        "comparison_count": len(comparisons),
        "position_improvement_count": len(pos_wins),
        "sync_improvement_count": len(sync_wins),
        "does_jcls_help_localization": len(pos_wins) > 0,
        "does_jcls_help_synchronization": len(sync_wins) > 0,
        "strongest_position_improvement": strongest_pos,
        "strongest_sync_improvement": strongest_sync,
    }


def _write_network_size_markdown(output_root: Path, report: dict[str, Any]) -> None:
    """Write local network-size metadata Markdown."""

    md = [
        "# Legacy-Compatible Network-Size Replay Metadata",
        "",
        "## Executive Summary",
        f"Mode `{report['mode']}` generated non-final network-size graphs with {report['counts']['row_count']} grid rows.",
        "",
        "## Generated Plots",
        "- [Localization PDF](pos_vary_ues.pdf)",
        "- [Synchronization PDF](sync_vary_ues.pdf)",
        "",
        "## Raw Outputs",
        "- [Raw CSV](legacy_network_size_raw.csv)",
        "- [Summary CSV](legacy_network_size_summary.csv)",
        "- [Arrays NPZ](legacy_network_size_arrays.npz)",
        "",
        "## Caveats",
        *[f"- `{key}`: {value}" for key, value in report["legacy_caveats"].items()],
    ]
    (output_root / "legacy_network_size_metadata.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def _write_network_size_report(path: Path, report: dict[str, Any]) -> None:
    """Write canonical network-size Markdown report."""

    root = report["output_root"].replace("outputs/", "../")
    trend = report["trend_summary"]
    md = [
        "# Legacy-Compatible Network-Size Replay Report",
        "",
        "## Executive Summary",
        f"Mode `{report['mode']}` generated non-final legacy-compatible localization and synchronization graphs versus number of satellites. These are not manuscript-ready.",
        "",
        "## Generated Plots",
        f"- [Localization PDF]({root}/pos_vary_ues.pdf)",
        f"- [Synchronization PDF]({root}/sync_vary_ues.pdf)",
        "",
        "## Raw Outputs",
        f"- [Raw CSV]({root}/legacy_network_size_raw.csv)",
        f"- [Summary CSV]({root}/legacy_network_size_summary.csv)",
        f"- [Arrays NPZ]({root}/legacy_network_size_arrays.npz)",
        f"- [Metadata JSON]({root}/legacy_network_size_metadata.json)",
        "",
        "## Trend Summary",
        f"- JCLS helps localization in {trend['position_improvement_count']} of {trend['comparison_count']} baseline comparisons.",
        f"- JCLS helps synchronization in {trend['sync_improvement_count']} of {trend['comparison_count']} baseline comparisons.",
        f"- Strongest localization improvement: `{trend['strongest_position_improvement']}`",
        f"- Strongest synchronization improvement: `{trend['strongest_sync_improvement']}`",
        "",
        "## Caveats",
        *[f"- `{key}`: {value}" for key, value in report["legacy_caveats"].items()],
    ]
    path.write_text("\n".join(md) + "\n", encoding="utf-8")


def _update_figure_regression_table(report: dict[str, Any]) -> None:
    """Mark the network-size target pair as replayed in the figure table."""

    table_path = SAT_SIM_ROOT / "v24_notebook_regression_outputs" / "FIGURE_REGRESSION_TABLE.json"
    if not table_path.exists():
        return
    table = json.loads(table_path.read_text(encoding="utf-8"))
    targets = {"pos_vary_ues.pdf", "sync_vary_ues.pdf"}
    for entry in table.get("target_figure_statuses", []):
        if entry.get("figure") in targets:
            entry["status"] = report["status"]
            entry["legacy_replay"] = True
            entry["bounded_smoke_replay"] = report["mode"] == "smoke"
            entry["medium_legacy_replay"] = report["mode"] == "medium"
            entry["full_legacy_replay"] = report["mode"] == "full"
            entry["manuscript_ready"] = False
            entry["replayed_output_root"] = report["output_root"]
            entry["reason"] = (
                f"Legacy-compatible network-size {report['mode']} replay completed under canonical outputs; "
                "match is unverified and legacy caveats remain."
            )
    table["network_size_replay_report"] = "outputs/reports/LEGACY_NETWORK_SIZE_REPLAY_REPORT.json"
    table["reproduction_status"] = report["status"]
    table_path.write_text(json.dumps(table, indent=2), encoding="utf-8")
    lines = [
        "# Figure Regression Table",
        "",
        "- Existing static mapping records are preserved in the JSON.",
        "- CRLB, clock-sweep, and network-size target figures have safe legacy-compatible replay outputs, but none are manuscript-ready.",
        "",
        "| Figure | Status | Legacy replay | Manuscript ready | Reason |",
        "|---|---|---:|---:|---|",
    ]
    for entry in table.get("target_figure_statuses", []):
        lines.append(
            "| {figure} | {status} | {legacy_replay} | {manuscript_ready} | {reason} |".format(
                figure=entry.get("figure", ""),
                status=entry.get("status", ""),
                legacy_replay=entry.get("legacy_replay", False),
                manuscript_ready=entry.get("manuscript_ready", False),
                reason=entry.get("reason", ""),
            )
        )
    table_path.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_network_size_replay(
    *,
    mode: str = "medium",
    output_root: Path | None = None,
    cache_root: Path = DEFAULT_CACHE_ROOT,
    use_cache: bool = True,
    force_rerun: bool = False,
    cache_status_only: bool = False,
) -> dict[str, Any]:
    """Run the legacy-compatible network-size replay."""

    config = _mode_config(mode)
    output_root = output_root or _default_output_root(mode)
    events: list[dict[str, Any]] = []
    identities = [_identity(config, user, sat) for user in config["num_users_range"] for sat in config["num_satellites_range"]]
    if cache_status_only:
        for identity in identities:
            _load_cache(cache_root, identity, events)
        manifest = _write_cache_manifest(cache_root, events, mode)
        return {"mode": mode, "cache_manifest": manifest, "status": "cache_status_only"}

    start = time.perf_counter()
    np.random.seed(int(config["seed"]))
    namespace, executed_cells = _execute_legacy_namespace()
    rows: list[dict[str, Any]] = []
    for user in config["num_users_range"]:
        for sat in config["num_satellites_range"]:
            identity = _identity(config, int(user), int(sat))
            row = None
            if use_cache and not force_rerun:
                row = _load_cache(cache_root, identity, events)
            if row is None:
                row = _run_row(namespace, config, int(user), int(sat))
                row["cache_used"] = False
                if use_cache:
                    _write_cache(cache_root, identity, row)
            row["num_users"] = int(user)
            row["num_satellites"] = int(sat)
            rows.append(row)
    manifest = _write_cache_manifest(cache_root, events, mode)
    report = _write_outputs(output_root, rows, {**config, "executed_cells": executed_cells}, manifest, time.perf_counter() - start)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["smoke", "medium", "full"], default="medium")
    parser.add_argument("--medium", action="store_true", help="Alias for --mode medium.")
    parser.add_argument("--full", action="store_true", help="Alias for --mode full.")
    parser.add_argument("--use-cache", action="store_true", default=True)
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--force-rerun", action="store_true")
    parser.add_argument("--cache-status", action="store_true")
    parser.add_argument("--output-root", type=Path, default=None)
    parser.add_argument("--cache-root", type=Path, default=DEFAULT_CACHE_ROOT)
    args = parser.parse_args()
    mode = "full" if args.full else "medium" if args.medium else args.mode
    report = run_network_size_replay(
        mode=mode,
        output_root=args.output_root,
        cache_root=args.cache_root,
        use_cache=not args.no_cache,
        force_rerun=args.force_rerun,
        cache_status_only=args.cache_status,
    )
    if not args.cache_status:
        from build_legacy_graph_package import main as build_graph_package
        from render_all_figure_previews import GALLERY_ROOT, render_gallery

        build_graph_package()
        gallery = render_gallery(force=False)
        report = json.loads((SAT_SIM_ROOT / "outputs" / "reports" / "LEGACY_NETWORK_SIZE_REPLAY_REPORT.json").read_text(encoding="utf-8"))
        print(json.dumps({
            "status": report["status"],
            "mode": report["mode"],
            "runtime_seconds": report["runtime_seconds"],
            "output_root": report["output_root"],
            "cache_hit_count": report["counts"]["cache_hit_count"],
            "cache_miss_count": report["counts"]["cache_miss_count"],
            "gallery": str((GALLERY_ROOT / "PLOT_GALLERY.html").relative_to(SAT_SIM_ROOT)).replace("\\", "/"),
            "preview_pngs": gallery.get("preview_pngs", []),
        }, indent=2))
    else:
        print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
