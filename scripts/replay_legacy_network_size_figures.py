"""Replay a small legacy-compatible network-size estimator diagnostic.

This script preserves the safe extracted-notebook path used by the clock-sweep
replay and writes non-final diagnostics under ``outputs/legacy_replay``. It is
not a manuscript figure generator.
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


SAT_SIM_ROOT = Path(__file__).resolve().parents[1]
if str(SAT_SIM_ROOT) not in sys.path:
    sys.path.insert(0, str(SAT_SIM_ROOT))

from replay_legacy_clock_sweep_figures import (  # noqa: E402
    CACHE_ROOT,
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


OUTPUT_ROOT = SAT_SIM_ROOT / "outputs" / "legacy_replay" / "network_size"
CACHE_SCHEMA_VERSION = "legacy-network-size-row-v1"


def _config() -> dict[str, Any]:
    """Return the bounded network-size smoke replay config."""

    return {
        "mode": "network_size_smoke",
        "num_satellites": [4, 8, 12],
        "num_users": 3,
        "clock_std_dev": 0.5e-9,
        "num_iterations": 2,
        "error_range": 100.0,
        "seed": 2042,
        "estimator_mode": "legacy_il_lm_map_filter_iteration",
    }


def _identity(config: dict[str, Any], num_satellites: int) -> dict[str, Any]:
    """Return deterministic row cache identity."""

    return {
        "cache_schema_version": CACHE_SCHEMA_VERSION,
        "script_name": Path(__file__).name,
        "script_sha256": _hash_file(Path(__file__).resolve()),
        "notebook_sha256": _hash_file(NOTEBOOK_PATH),
        "extracted_cell_hashes": _selected_cell_hashes(),
        "config": {
            **config,
            "num_satellites": int(num_satellites),
        },
    }


def _cache_paths(cache_root: Path, key: str) -> dict[str, Path]:
    """Return row cache paths."""

    row_dir = cache_root / "legacy_network_size" / key[:16]
    return {
        "dir": row_dir,
        "metadata": row_dir / "metadata.json",
        "row": row_dir / "row.json",
    }


def _row_hash(row: dict[str, Any]) -> str:
    """Return row hash."""

    return _hash_text(_canonical_json(row))


def _load_cache(cache_root: Path, identity: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Load a valid row cache entry."""

    key = _cache_key(identity)
    paths = _cache_paths(cache_root, key)
    event = {
        "cache_key": key,
        "num_satellites": identity["config"]["num_satellites"],
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


def _write_cache_manifest(cache_root: Path, events: list[dict[str, Any]]) -> dict[str, Any]:
    """Write canonical cache manifest."""

    cache_root.mkdir(parents=True, exist_ok=True)
    manifest = {
        "artifact_status": "non_final_cache_manifest",
        "cache_schema_version": CACHE_SCHEMA_VERSION,
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
        f"- Fresh hits: {manifest['fresh_hit_count']}",
        f"- Miss/stale: {manifest['miss_or_stale_count']}",
        "",
        "| Satellites | Hit | Fresh | Reason |",
        "|---:|---:|---:|---|",
    ]
    for event in events:
        md.append(f"| {event.get('num_satellites')} | {event.get('hit')} | {event.get('fresh')} | {event.get('invalidation_reason') or ''} |")
    (cache_root / "CACHE_MANIFEST.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return manifest


def _update_figure_regression_table(report: dict[str, Any]) -> None:
    """Mark the network-size target pair as smoke-replayed in the figure table."""

    table_path = SAT_SIM_ROOT / "v24_notebook_regression_outputs" / "FIGURE_REGRESSION_TABLE.json"
    if not table_path.exists():
        return
    table = json.loads(table_path.read_text(encoding="utf-8"))
    targets = {"pos_vary_ues.pdf", "sync_vary_ues.pdf"}
    for entry in table.get("target_figure_statuses", []):
        if entry.get("figure") in targets:
            entry["status"] = report["status"]
            entry["legacy_replay"] = True
            entry["bounded_smoke_replay"] = True
            entry["manuscript_ready"] = False
            entry["replayed_output_root"] = report["output_root"]
            entry["reason"] = (
                "Bounded safe legacy-compatible network-size smoke replay completed under canonical outputs; "
                "match is unverified, full notebook-size replay was not attempted, and legacy caveats remain."
            )
    table["network_size_replay_report"] = "outputs/reports/LEGACY_NETWORK_SIZE_REPLAY_REPORT.json"
    table["reproduction_status"] = "legacy_network_size_smoke_replayed_unverified_match"
    table_path.write_text(json.dumps(table, indent=2), encoding="utf-8")

    lines = [
        "# Figure Regression Table",
        "",
        "- Existing static mapping records are preserved in the JSON.",
        "- CRLB, clock-sweep, and bounded network-size target figures have safe legacy-compatible replay outputs, but none are manuscript-ready.",
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
    (table_path.with_suffix(".md")).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _plot(x: np.ndarray, series: dict[str, np.ndarray], output_path: Path, ylabel: str) -> None:
    """Write a diagnostic line plot."""

    fig, ax = plt.subplots(figsize=(4.0, 3.0), dpi=240)
    for label, values in series.items():
        ax.plot(x, values, marker="o", label=label)
    ax.set_xlabel("Number of satellites")
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best", fontsize=7)
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path)
    plt.close(fig)


def run_network_size_replay(
    *,
    output_root: Path = OUTPUT_ROOT,
    cache_root: Path = SAT_SIM_ROOT / "outputs" / "cache",
    use_cache: bool = True,
    force_rerun: bool = False,
) -> dict[str, Any]:
    """Run the bounded legacy-compatible network-size replay."""

    start = time.perf_counter()
    config = _config()
    np.random.seed(int(config["seed"]))
    namespace, executed_cells = _execute_legacy_namespace()
    rows: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    for num_satellites in config["num_satellites"]:
        identity = _identity(config, int(num_satellites))
        row = None
        if use_cache and not force_rerun:
            row = _load_cache(cache_root, identity, events)
        if row is None:
            row = _scenario_result(
                namespace=namespace,
                clock_std_dev=float(config["clock_std_dev"]),
                num_iterations=int(config["num_iterations"]),
                num_users=int(config["num_users"]),
                num_satellites=int(num_satellites),
                error_range=float(config["error_range"]),
            )
            row["num_satellites"] = int(num_satellites)
            row["cache_used"] = False
            if use_cache:
                _write_cache(cache_root, identity, row)
        row["num_satellites"] = int(num_satellites)
        rows.append(row)
    output_root.mkdir(parents=True, exist_ok=True)
    raw_csv = output_root / "legacy_network_size_raw.csv"
    fields = [
        "num_satellites",
        "num_users",
        "measurement_count",
        "state_dimension",
        "il_position_error_m",
        "lm_position_error_m",
        "map_position_error_m",
        "il_sync_error_s",
        "lm_sync_error_s",
        "map_sync_error_s",
        "success",
        "cache_used",
        "fallbacks",
        "failures",
    ]
    with raw_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: json.dumps(row[field]) if field in {"fallbacks", "failures"} else row.get(field) for field in fields})
    x = np.asarray([row["num_satellites"] for row in rows], dtype=float)
    pos_pdf = output_root / "pos_vary_ues.pdf"
    sync_pdf = output_root / "sync_vary_ues.pdf"
    _plot(
        x,
        {
            "Without cooperation": np.asarray([row["il_position_error_m"] for row in rows], dtype=float),
            "Coarse JCLS": np.asarray([row["lm_position_error_m"] for row in rows], dtype=float),
            "Refined JCLS": np.asarray([row["map_position_error_m"] for row in rows], dtype=float),
        },
        pos_pdf,
        "Average UE position error [m]",
    )
    _plot(
        x,
        {
            "Without cooperation": np.asarray([row["il_sync_error_s"] for row in rows], dtype=float) * 1e9,
            "Coarse JCLS": np.asarray([row["lm_sync_error_s"] for row in rows], dtype=float) * 1e9,
            "Refined JCLS": np.asarray([row["map_sync_error_s"] for row in rows], dtype=float) * 1e9,
        },
        sync_pdf,
        "Average synchronization error [ns]",
    )
    np.savez(
        output_root / "legacy_network_size_arrays.npz",
        num_satellites=x,
        il_position_error_m=np.asarray([row["il_position_error_m"] for row in rows], dtype=float),
        lm_position_error_m=np.asarray([row["lm_position_error_m"] for row in rows], dtype=float),
        map_position_error_m=np.asarray([row["map_position_error_m"] for row in rows], dtype=float),
        il_sync_error_s=np.asarray([row["il_sync_error_s"] for row in rows], dtype=float),
        lm_sync_error_s=np.asarray([row["lm_sync_error_s"] for row in rows], dtype=float),
        map_sync_error_s=np.asarray([row["map_sync_error_s"] for row in rows], dtype=float),
    )
    manifest = _write_cache_manifest(cache_root, events)
    report = {
        "artifact_status": "non_final_legacy_network_size_replay",
        "status": "legacy_network_size_smoke_replayed_unverified_match",
        "legacy_replay": True,
        "manuscript_ready": False,
        "not_for_manuscript_submission": True,
        "output_root": str(output_root.relative_to(SAT_SIM_ROOT)).replace("\\", "/"),
        "runtime_seconds": time.perf_counter() - start,
        "config": config,
        "executed_cells": executed_cells,
        "counts": {
            "row_count": len(rows),
            "cache_hit_count": sum(1 for row in rows if row.get("cache_used")),
            "cache_miss_count": sum(1 for row in rows if not row.get("cache_used")),
            "total_fallback_events": sum(len(row["fallbacks"]) for row in rows),
            "rows_with_failures": sum(1 for row in rows if row["failures"]),
        },
        "legacy_caveats": {
            "bounded_smoke_replay_only": True,
            "all_clock_symbolic_state": True,
            "v24_gauging_absent": True,
            "truth_error_acceptance_gates_used": True,
            "legacy_sync_metric_averages_all_clock_symbols": True,
            "not_claimed_to_match_manuscript_figures": True,
            "first_user_row_without_cooperation_convention_not_used_in_this_smoke": True,
        },
        "raw_outputs": {
            "raw_csv": str(raw_csv.relative_to(SAT_SIM_ROOT)).replace("\\", "/"),
            "arrays_npz": str((output_root / "legacy_network_size_arrays.npz").relative_to(SAT_SIM_ROOT)).replace("\\", "/"),
        },
        "plot_outputs": [
            str(pos_pdf.relative_to(SAT_SIM_ROOT)).replace("\\", "/"),
            str(sync_pdf.relative_to(SAT_SIM_ROOT)).replace("\\", "/"),
        ],
        "cache_manifest": {
            "json": str((cache_root / "CACHE_MANIFEST.json").relative_to(SAT_SIM_ROOT)).replace("\\", "/"),
            "md": str((cache_root / "CACHE_MANIFEST.md").relative_to(SAT_SIM_ROOT)).replace("\\", "/"),
            "fresh_hit_count": manifest["fresh_hit_count"],
            "miss_or_stale_count": manifest["miss_or_stale_count"],
        },
    }
    (output_root / "legacy_network_size_metadata.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    md = [
        "# Legacy-Compatible Network-Size Replay Report",
        "",
        "## Executive Summary",
        "This is a bounded smoke replay of the legacy staged estimator path for network-size graphs. It is not manuscript-ready.",
        "",
        "## Generated Plots",
        f"- [Localization PDF]({pos_pdf.name})",
        f"- [Synchronization PDF]({sync_pdf.name})",
        "",
        "## Raw Outputs",
        f"- [Raw CSV]({raw_csv.name})",
        f"- [Arrays NPZ](legacy_network_size_arrays.npz)",
        "",
        "## Caveats",
        *[f"- `{key}`: {value}" for key, value in report["legacy_caveats"].items()],
    ]
    (output_root / "legacy_network_size_metadata.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    reports = SAT_SIM_ROOT / "outputs" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    report_md = [
        "# Legacy-Compatible Network-Size Replay Report",
        "",
        "## Executive Summary",
        "This bounded smoke replay generated legacy-compatible localization and synchronization graphs versus number of satellites. It is diagnostic only, not manuscript-ready, and not a full reproduction of the notebook's manuscript figure grid.",
        "",
        "## Generated Plots",
        "- [Localization PDF](../legacy_replay/network_size/pos_vary_ues.pdf)",
        "- [Synchronization PDF](../legacy_replay/network_size/sync_vary_ues.pdf)",
        "",
        "## Raw Outputs",
        "- [Raw CSV](../legacy_replay/network_size/legacy_network_size_raw.csv)",
        "- [Arrays NPZ](../legacy_replay/network_size/legacy_network_size_arrays.npz)",
        "- [Metadata JSON](../legacy_replay/network_size/legacy_network_size_metadata.json)",
        "",
        "## What The Plots Mean",
        "The plots exercise the safe extracted legacy staged algorithm path on a tiny deterministic network-size smoke grid. They are useful for visual regression and failure/fallback accounting, not for TAES submission.",
        "",
        "## Caveats",
        *[f"- `{key}`: {value}" for key, value in report["legacy_caveats"].items()],
    ]
    (reports / "LEGACY_NETWORK_SIZE_REPLAY_REPORT.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (reports / "LEGACY_NETWORK_SIZE_REPLAY_REPORT.md").write_text("\n".join(report_md) + "\n", encoding="utf-8")
    _update_figure_regression_table(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--use-cache", action="store_true", default=True)
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--force-rerun", action="store_true")
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--cache-root", type=Path, default=SAT_SIM_ROOT / "outputs" / "cache")
    args = parser.parse_args()
    report = run_network_size_replay(
        output_root=args.output_root,
        cache_root=args.cache_root,
        use_cache=not args.no_cache,
        force_rerun=args.force_rerun,
    )
    from render_all_figure_previews import GALLERY_ROOT, render_gallery

    gallery = render_gallery(force=False)
    print(json.dumps({
        "status": report["status"],
        "output_root": report["output_root"],
        "cache_hit_count": report["counts"]["cache_hit_count"],
        "cache_miss_count": report["counts"]["cache_miss_count"],
        "gallery": str((GALLERY_ROOT / "PLOT_GALLERY.html").relative_to(SAT_SIM_ROOT)).replace("\\", "/"),
        "preview_pngs": gallery.get("preview_pngs", []),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
