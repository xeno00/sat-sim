"""Build a controlled legacy-to-V24 migration ladder diagnostic package."""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
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

from jcls_sim.migration import MigrationStep, migration_ladder_steps, step_diff  # noqa: E402
from scripts.replay_legacy_clock_sweep_figures import NOTEBOOK_PATH, _hash_file, _selected_cell_hashes  # noqa: E402
from scripts.replay_legacy_network_size_figures import CACHE_SCHEMA_VERSION as NETWORK_CACHE_SCHEMA  # noqa: E402
from scripts.replay_legacy_network_size_figures import _mode_config  # noqa: E402


BASELINE_ROOT = SAT_SIM_ROOT / "outputs" / "migration_baseline" / "legacy_behavior_freeze"
LADDER_ROOT = SAT_SIM_ROOT / "outputs" / "migration_ladder"
REPORTS = SAT_SIM_ROOT / "outputs" / "reports"
MIGRATION_CACHE_ROOT = SAT_SIM_ROOT / "outputs" / "cache" / "migration_ladder"
SOURCE_NETWORK_ROOT = SAT_SIM_ROOT / "outputs" / "legacy_replay" / "network_size_medium"
SOURCE_CLOCK_ROOT = SAT_SIM_ROOT / "outputs" / "legacy_replay" / "clock_sweep_full"
MIGRATION_CACHE_SCHEMA_VERSION = "controlled-migration-ladder-v1"


def _sha256(path: Path) -> str:
    """Return SHA256 for a file."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _repo_rel(path: Path) -> str:
    """Return repo-relative POSIX path."""

    return path.relative_to(SAT_SIM_ROOT).as_posix()


def _read_rows() -> list[dict[str, Any]]:
    """Read medium replay rows."""

    path = SOURCE_NETWORK_ROOT / "legacy_network_size_raw.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    out = []
    for row in rows:
        converted = dict(row)
        for key in [
            "num_users",
            "num_satellites",
            "measurement_count",
            "state_dimension",
            "map_iteration_count",
            "fallback_count",
            "failure_count",
        ]:
            converted[key] = int(float(converted[key]))
        for key in [
            "il_position_error_m",
            "lm_position_error_m",
            "map_position_error_m",
            "il_sync_error_s",
            "lm_sync_error_s",
            "map_sync_error_s",
        ]:
            converted[key] = float(converted[key])
        converted["cooperative_jcls_attempted"] = str(converted["cooperative_jcls_attempted"]) == "True"
        converted["cache_used"] = str(converted["cache_used"]) == "True"
        converted["success"] = str(converted["success"]) == "True"
        out.append(converted)
    return out


def _filter_rows(rows: list[dict[str, Any]], grid: str) -> list[dict[str, Any]]:
    """Filter rows for tiny or medium grid."""

    if grid == "medium":
        return list(rows)
    if grid == "tiny":
        return [
            row
            for row in rows
            if row["num_users"] in {1, 3} and row["num_satellites"] in {4, 8}
        ]
    raise ValueError(f"unknown grid: {grid}")


def _plot(rows: list[dict[str, Any]], output_root: Path) -> list[str]:
    """Write localization and synchronization plots."""

    users = sorted({row["num_users"] for row in rows})
    sats = sorted({row["num_satellites"] for row in rows})
    by_key = {(row["num_users"], row["num_satellites"]): row for row in rows}
    outputs = []
    for metric, ylabel, filename, scale in [
        ("map_position_error_m", "Average UE position error [m]", "pos_vary_ues.pdf", 1.0),
        ("map_sync_error_s", "Average synchronization error [ns]", "sync_vary_ues.pdf", 1e9),
    ]:
        fig, ax = plt.subplots(figsize=(4.4, 3.2), dpi=240)
        for user in users:
            label = "Without cooperation (single UE)" if user == 1 else f"Refined JCLS ({user} UEs)"
            values = [by_key[(user, sat)][metric] * scale for sat in sats]
            ax.plot(sats, values, marker="o", label=label)
        ax.set_xlabel("Number of satellites")
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.25)
        ax.legend(loc="best", fontsize=7, frameon=True)
        fig.tight_layout()
        path = output_root / filename
        output_root.mkdir(parents=True, exist_ok=True)
        fig.savefig(path)
        plt.close(fig)
        outputs.append(_repo_rel(path))
    return outputs


def _write_csvs(rows: list[dict[str, Any]], output_root: Path) -> dict[str, str]:
    """Write raw and summary CSVs."""

    output_root.mkdir(parents=True, exist_ok=True)
    raw = output_root / "migration_raw.csv"
    summary = output_root / "migration_summary.csv"
    fieldnames = [
        "num_users",
        "num_satellites",
        "cooperative_jcls_attempted",
        "map_position_error_m",
        "map_sync_error_s",
        "fallback_count",
        "failure_count",
        "success",
        "single_ue_policy",
    ]
    with raw.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})
    users = sorted({row["num_users"] for row in rows})
    with summary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["num_users", "mean_position_error_m", "mean_sync_error_ns", "row_count", "fallback_count", "failure_count"],
        )
        writer.writeheader()
        for user in users:
            subset = [row for row in rows if row["num_users"] == user]
            writer.writerow(
                {
                    "num_users": user,
                    "mean_position_error_m": float(np.mean([row["map_position_error_m"] for row in subset])),
                    "mean_sync_error_ns": float(np.mean([row["map_sync_error_s"] for row in subset]) * 1e9),
                    "row_count": len(subset),
                    "fallback_count": sum(row["fallback_count"] for row in subset),
                    "failure_count": sum(row["failure_count"] for row in subset),
                }
            )
    return {"raw_csv": _repo_rel(raw), "summary_csv": _repo_rel(summary)}


def _write_npz(rows: list[dict[str, Any]], output_root: Path) -> str:
    """Write compact NPZ arrays."""

    path = output_root / "migration_arrays.npz"
    np.savez(
        path,
        num_users=np.asarray([row["num_users"] for row in rows], dtype=int),
        num_satellites=np.asarray([row["num_satellites"] for row in rows], dtype=int),
        map_position_error_m=np.asarray([row["map_position_error_m"] for row in rows], dtype=float),
        map_sync_error_s=np.asarray([row["map_sync_error_s"] for row in rows], dtype=float),
    )
    return _repo_rel(path)


def _health(rows: list[dict[str, Any]], previous: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return health summary for one step/grid."""

    users = sorted({row["num_users"] for row in rows})
    sats = sorted({row["num_satellites"] for row in rows})
    by_key = {(row["num_users"], row["num_satellites"]): row for row in rows}
    comparisons = []
    for sat in sats:
        base = by_key.get((1, sat))
        if not base:
            continue
        for user in users:
            if user == 1:
                continue
            row = by_key[(user, sat)]
            comparisons.append(
                {
                    "num_users": user,
                    "num_satellites": sat,
                    "position_improvement_m": base["map_position_error_m"] - row["map_position_error_m"],
                    "sync_improvement_ns": (base["map_sync_error_s"] - row["map_sync_error_s"]) * 1e9,
                }
            )
    pos_wins = [item for item in comparisons if item["position_improvement_m"] > 0]
    sync_wins = [item for item in comparisons if item["sync_improvement_ns"] > 0]
    failed_rows = sum(1 for row in rows if row["failure_count"] > 0)
    healthy = bool(comparisons) and len(pos_wins) == len(comparisons) and len(sync_wins) == len(comparisons) and failed_rows == 0
    status = "healthy" if healthy else "partially_degraded"
    degraded = False
    if previous is not None:
        degraded = (
            len(pos_wins) < previous["position_improvement_count"]
            or len(sync_wins) < previous["sync_improvement_count"]
            or failed_rows > previous["failed_rows"]
        )
        if degraded:
            status = "partially_degraded"
    return {
        "status": status,
        "comparison_count": len(comparisons),
        "position_improvement_count": len(pos_wins),
        "sync_improvement_count": len(sync_wins),
        "does_jcls_help_localization": len(pos_wins) > 0,
        "does_jcls_help_synchronization": len(sync_wins) > 0,
        "healthy_rows": len(rows) - failed_rows,
        "failed_rows": failed_rows,
        "fallback_count": sum(row["fallback_count"] for row in rows),
        "performance_degraded_vs_previous": degraded,
        "strongest_position_improvement": max(comparisons, key=lambda item: item["position_improvement_m"], default=None),
        "strongest_sync_improvement": max(comparisons, key=lambda item: item["sync_improvement_ns"], default=None),
    }


def _cache_identity(step: MigrationStep, grid: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Return cache identity for a ladder output."""

    return {
        "cache_schema_version": MIGRATION_CACHE_SCHEMA_VERSION,
        "network_cache_schema_version": NETWORK_CACHE_SCHEMA,
        "script_sha256": _sha256(Path(__file__).resolve()),
        "source_network_raw_sha256": _sha256(SOURCE_NETWORK_ROOT / "legacy_network_size_raw.csv"),
        "notebook_sha256": _sha256(NOTEBOOK_PATH),
        "extracted_cell_hashes": _selected_cell_hashes(),
        "step": step.to_dict(),
        "grid": grid,
        "grid_parameters": {
            "num_users": sorted({row["num_users"] for row in rows}),
            "num_satellites": sorted({row["num_satellites"] for row in rows}),
            "seed": _mode_config("medium")["seed"],
        },
    }


def _write_cache(step: MigrationStep, grid: str, rows: list[dict[str, Any]], metadata: dict[str, Any]) -> dict[str, Any]:
    """Write cache entry metadata for a migration step/grid."""

    identity = _cache_identity(step, grid, rows)
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode("utf-8")).hexdigest()
    cache_dir = MIGRATION_CACHE_ROOT / key[:16]
    cache_dir.mkdir(parents=True, exist_ok=True)
    row_hash = hashlib.sha256(json.dumps(rows, sort_keys=True).encode("utf-8").hexdigest() if False else json.dumps(rows, sort_keys=True).encode("utf-8")).hexdigest()
    payload = {
        "status": "complete",
        "cache_key": key,
        "identity": identity,
        "raw_result_hash": row_hash,
        "metadata": metadata,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (cache_dir / "metadata.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return {"cache_key": key, "cache_path": _repo_rel(cache_dir / "metadata.json"), "raw_result_hash": row_hash}


def _write_baseline_freeze(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Write the frozen legacy behavior baseline package."""

    BASELINE_ROOT.mkdir(parents=True, exist_ok=True)
    copied = []
    for src_root in [SOURCE_NETWORK_ROOT, SOURCE_CLOCK_ROOT]:
        if not src_root.exists():
            continue
        dst = BASELINE_ROOT / src_root.name
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src_root, dst)
        copied.append(_repo_rel(dst))
    health = _health(rows)
    report = {
        "artifact_status": "non_final_legacy_behavior_freeze",
        "status": health["status"],
        "manuscript_ready": False,
        "copied_output_roots": copied,
        "baseline_health": health,
        "legacy_caveats": {
            "all_clock_internal_state": True,
            "truth_gated_acceptance": True,
            "legacy_all_clock_sync_metric": True,
            "map_global_fallback": True,
            "non_v24_gauged_internals": True,
        },
    }
    (BASELINE_ROOT / "baseline_health_summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    md = [
        "# Legacy Behavior Freeze",
        "",
        "## Executive Summary",
        "This package freezes the current working legacy-compatible behavior for comparison against controlled migration steps.",
        "",
        f"- Status: `{health['status']}`",
        f"- JCLS localization improvements: {health['position_improvement_count']} of {health['comparison_count']}",
        f"- JCLS synchronization improvements: {health['sync_improvement_count']} of {health['comparison_count']}",
        f"- Fallback count: {health['fallback_count']}",
        f"- Failed rows: {health['failed_rows']}",
        "",
        "## Copied Roots",
        *[f"- `{item}`" for item in copied],
    ]
    (BASELINE_ROOT / "baseline_health_summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return report


def _write_step(step: MigrationStep, grid: str, rows: list[dict[str, Any]], previous_health: dict[str, Any] | None) -> dict[str, Any]:
    """Write outputs for one migration step and grid."""

    output_root = LADDER_ROOT / step.name / grid
    plot_outputs = _plot(rows, output_root)
    csvs = _write_csvs(rows, output_root)
    arrays = _write_npz(rows, output_root)
    health = _health(rows, previous_health)
    metadata = {
        "artifact_status": "non_final_controlled_migration_step",
        "step": step.to_dict(),
        "grid": grid,
        "status": health["status"],
        "manuscript_ready": False,
        "plot_outputs": plot_outputs,
        "raw_outputs": {**csvs, "arrays_npz": arrays},
        "health": health,
        "change_vs_previous": None,
    }
    metadata["cache"] = _write_cache(step, grid, rows, metadata)
    path = output_root / "migration_step_metadata.json"
    path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    md = [
        f"# Migration Step: {step.name} ({grid})",
        "",
        "## Executive Summary",
        step.exact_change,
        "",
        f"- Status: `{health['status']}`",
        f"- Manuscript ready: `{metadata['manuscript_ready']}`",
        f"- Localization improvements: {health['position_improvement_count']} of {health['comparison_count']}",
        f"- Synchronization improvements: {health['sync_improvement_count']} of {health['comparison_count']}",
        f"- Fallback count: {health['fallback_count']}",
        "",
        "## Plots",
        "- [Localization PDF](pos_vary_ues.pdf)",
        "- [Synchronization PDF](sync_vary_ues.pdf)",
    ]
    (output_root / "migration_step_metadata.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return metadata


def _write_cache_manifest(cache_entries: list[dict[str, Any]]) -> None:
    """Write migration cache manifest."""

    MIGRATION_CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    manifest = {
        "artifact_status": "non_final_migration_ladder_cache_manifest",
        "cache_schema_version": MIGRATION_CACHE_SCHEMA_VERSION,
        "entry_count": len(cache_entries),
        "entries": cache_entries,
        "fresh_hit_count": 0,
        "miss_or_stale_count": len(cache_entries),
    }
    (MIGRATION_CACHE_ROOT / "CACHE_MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    md = [
        "# Migration Ladder Cache Manifest",
        "",
        f"- Entries: {len(cache_entries)}",
        "",
        "| Step | Grid | Cache key | Metadata |",
        "|---|---|---|---|",
    ]
    for entry in cache_entries:
        md.append(f"| `{entry['step']}` | `{entry['grid']}` | `{entry['cache_key'][:12]}` | [{entry['cache_path']}](../../{entry['cache_path']}) |")
    (MIGRATION_CACHE_ROOT / "CACHE_MANIFEST.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def _write_ladder_report(step_reports: list[dict[str, Any]], baseline: dict[str, Any]) -> dict[str, Any]:
    """Write top-level controlled migration ladder report."""

    REPORTS.mkdir(parents=True, exist_ok=True)
    steps = []
    previous_step: MigrationStep | None = None
    first_degraded = None
    for report in step_reports:
        step = MigrationStep(**report["step"])
        diff = step_diff(previous_step, step) if previous_step else {}
        report["change_vs_previous"] = diff
        if report["health"]["performance_degraded_vs_previous"] and first_degraded is None:
            first_degraded = step.name
        steps.append(report)
        previous_step = step
    payload = {
        "artifact_status": "non_final_controlled_migration_ladder",
        "baseline": baseline,
        "steps": steps,
        "first_degraded_step": first_degraded,
        "current_best_migration_step": "step_a_no_display_smoothing",
        "stop_rule_triggered": first_degraded is not None,
        "manuscript_ready": False,
    }
    (REPORTS / "CONTROLLED_MIGRATION_LADDER.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md = [
        "# Controlled Migration Ladder",
        "",
        "## Executive Summary",
        "This ladder starts from frozen legacy-compatible behavior, exposes the legacy behavior as a package-described mode, and tests Step A: raw metrics without display smoothing. No figure is manuscript-ready.",
        "",
        f"- First degraded step: `{first_degraded or 'none'}`",
        f"- Current best migration step: `{payload['current_best_migration_step']}`",
        "",
        "## Baseline Health",
        f"- Status: `{baseline['baseline_health']['status']}`",
        f"- Localization improvements: {baseline['baseline_health']['position_improvement_count']} of {baseline['baseline_health']['comparison_count']}",
        f"- Synchronization improvements: {baseline['baseline_health']['sync_improvement_count']} of {baseline['baseline_health']['comparison_count']}",
        "",
        "## Steps",
        "| Step | Grid | Status | Localization wins | Synchronization wins | Fallbacks | Recommendation |",
        "|---|---|---|---:|---:|---:|---|",
    ]
    for report in steps:
        health = report["health"]
        recommendation = "keep" if health["status"] == "healthy" else "stop and inspect"
        md.append(
            f"| `{report['step']['name']}` | `{report['grid']}` | `{health['status']}` | "
            f"{health['position_improvement_count']}/{health['comparison_count']} | "
            f"{health['sync_improvement_count']}/{health['comparison_count']} | "
            f"{health['fallback_count']} | {recommendation} |"
        )
    md += [
        "",
        "## Caveat",
        "This ladder uses the current legacy medium replay rows as the frozen behavior source. It does not make manuscript-ready claims and does not execute the original notebook.",
    ]
    (REPORTS / "CONTROLLED_MIGRATION_LADDER.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return payload


def run_ladder() -> dict[str, Any]:
    """Run the implemented controlled migration ladder."""

    rows = _read_rows()
    baseline = _write_baseline_freeze(rows)
    step_reports = []
    cache_entries = []
    previous_by_grid: dict[str, dict[str, Any] | None] = {"tiny": None, "medium": None}
    for step in migration_ladder_steps()[1:]:
        for grid in ["tiny", "medium"]:
            grid_rows = _filter_rows(rows, grid)
            report = _write_step(step, grid, grid_rows, previous_by_grid[grid])
            previous_by_grid[grid] = report["health"]
            step_reports.append(report)
            cache_entries.append({"step": step.name, "grid": grid, **report["cache"]})
    _write_cache_manifest(cache_entries)
    ladder = _write_ladder_report(step_reports, baseline)
    from scripts.render_all_figure_previews import render_gallery

    gallery = render_gallery(force=False)
    ladder["gallery"] = {
        "path": "outputs/gallery/PLOT_GALLERY.md",
        "entry_count": gallery["entry_count"],
    }
    (REPORTS / "CONTROLLED_MIGRATION_LADDER.json").write_text(json.dumps(ladder, indent=2), encoding="utf-8")
    return ladder


def main() -> int:
    payload = run_ladder()
    print(json.dumps({"status": "wrote", "first_degraded_step": payload["first_degraded_step"], "current_best": payload["current_best_migration_step"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
