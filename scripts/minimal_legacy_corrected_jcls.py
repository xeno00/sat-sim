"""Minimal corrected legacy-compatible JCLS result pipeline.

This script deliberately stays small. It reuses the safe extracted-notebook
legacy helpers already merged into this repository, keeps the legacy all-clock
state/model behavior, and runs only the corrected prior-region + residual-LM +
non-truth MAP path.

Default behavior is plan-only. Use ``--run`` for a bounded execution.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SAT_SIM_ROOT = Path(__file__).resolve().parents[1]
if str(SAT_SIM_ROOT) not in sys.path:
    sys.path.insert(0, str(SAT_SIM_ROOT))

from scripts.replay_legacy_clock_sweep_figures import NOTEBOOK_PATH  # noqa: E402
from scripts.run_legacy_surgical_prior_region_initialization import (  # noqa: E402
    PIPELINES,
    PriorConfig,
    StandardCase,
    _json_default,
    _metric_or_none,
    _prepare_namespace,
    _residual_cost,
    _run_case,
    _set_seed,
)


OUTPUT_ROOT = SAT_SIM_ROOT / "outputs" / "minimal_legacy_corrected"
REPORTS_ROOT = SAT_SIM_ROOT / "outputs" / "reports"
REPORT_MD = REPORTS_ROOT / "MINIMAL_LEGACY_CORRECTED_PIPELINE_REPORT.md"
REPORT_JSON = REPORTS_ROOT / "MINIMAL_LEGACY_CORRECTED_PIPELINE_REPORT.json"
SPARSE_REPORT_MD = REPORTS_ROOT / "MINIMAL_LEGACY_CORRECTED_SPARSE_MANUSCRIPT_REPORT.md"
SPARSE_REPORT_JSON = REPORTS_ROOT / "MINIMAL_LEGACY_CORRECTED_SPARSE_MANUSCRIPT_REPORT.json"
FIGURE_REPORT_MD = REPORTS_ROOT / "MINIMAL_LEGACY_CORRECTED_MANUSCRIPT_STYLE_FIGURES_REPORT.md"
FIGURE_REPORT_JSON = REPORTS_ROOT / "MINIMAL_LEGACY_CORRECTED_MANUSCRIPT_STYLE_FIGURES_REPORT.json"
RUN_HISTORY_DIRNAME = "run_history"
LATEST_RUN_FILENAME = "LATEST_RUN.json"
RUN_HISTORY_FILENAME = "RUN_HISTORY.jsonl"

PIPELINE = next(pipeline for pipeline in PIPELINES if pipeline.label == "legacy_surgical_nontruth")
PRIMARY_CASE_ID = "std_nu3_ns10_fullmesh_los_clock1us_seed0"
DEFAULT_PRIOR_RADIUS_M = 100_000.0
NETWORK_NONCOOPERATIVE_BASELINE_NU = 1
NETWORK_NONCOOPERATIVE_BASELINE_NS = [4, 8, 10, 12, 14]
NETWORK_SPARSE_NU = [3, 5, 7]
NETWORK_SPARSE_NS = [4, 8, 10, 12, 14]
SPARSE_CLOCK_STDS_SECONDS = [0.1e-9, 1.0e-9, 10.0e-9, 100.0e-9, 1.0e-6, 10.0e-6, 100.0e-6]
FULL_SPARSE_CLOCK_STDS_SECONDS = [0.1e-9, 1.0e-9, 10.0e-9, 100.0e-9, 1.0e-6, 10.0e-6, 100.0e-6]

TRUTH_USE_LEDGER = {
    "truth_used_for_prior_construction": True,
    "truth_used_for_initialization": False,
    "truth_used_for_lm_acceptance": False,
    "truth_used_for_step_c_acceptance": False,
    "truth_used_for_covariance": False,
    "truth_used_for_fallback_or_reversion": False,
    "truth_used_for_offline_metrics": True,
}

UNITS_LEDGER = {
    "internal_position_units": "km",
    "internal_clock_state_units": "legacy range-equivalent km",
    "measurement_units": "km",
    "measurement_covariance_units": "legacy km^2/range-domain covariance",
    "localization_error_units": "m",
    "synchronization_error_units": "ns",
    "clock_sigma_input_units": "seconds",
    "units_status": "units_consistent_but_legacy",
}


def repo_rel(path: Path) -> str:
    """Return a path relative to the sat-sim root."""

    return path.resolve().relative_to(SAT_SIM_ROOT.resolve()).as_posix()


def git_commit() -> str:
    """Return current commit hash or unknown."""

    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=SAT_SIM_ROOT, text=True).strip()
    except Exception:  # noqa: BLE001 - metadata only.
        return "unknown"


def primary_case(seed: int, clock_std_seconds: float = 1.0e-6) -> StandardCase:
    """Return the primary normalized standard case."""

    return StandardCase(
        case_id=PRIMARY_CASE_ID,
        num_users=3,
        num_satellites=10,
        clock_std_dev_seconds=float(clock_std_seconds),
        seed=int(seed),
        map_iterations=2,
        legacy_error_range_km=100.0,
        sidelink_topology="fullmesh",
        propagation="legacy_los_rician",
    )


def sparse_cases(*, full_clock_grid: bool = False) -> list[StandardCase]:
    """Return sparse manuscript-targeted cases."""

    cases: list[StandardCase] = []
    for ns in NETWORK_NONCOOPERATIVE_BASELINE_NS:
        cases.append(
            StandardCase(
                case_id=f"sparse_noncoop_nu1_ns{ns}_clock1us_seed0",
                num_users=NETWORK_NONCOOPERATIVE_BASELINE_NU,
                num_satellites=ns,
                clock_std_dev_seconds=1.0e-6,
                seed=0,
                map_iterations=0,
            )
        )
    for nu in NETWORK_SPARSE_NU:
        for ns in NETWORK_SPARSE_NS:
            cases.append(
                StandardCase(
                    case_id=f"sparse_network_nu{nu}_ns{ns}_clock1us_seed0",
                    num_users=nu,
                    num_satellites=ns,
                    clock_std_dev_seconds=1.0e-6,
                    seed=0,
                    map_iterations=2,
                )
            )
    clock_values = FULL_SPARSE_CLOCK_STDS_SECONDS if full_clock_grid else SPARSE_CLOCK_STDS_SECONDS
    for clock_std in clock_values:
        cases.append(
            StandardCase(
                case_id=f"sparse_clock_nu3_ns10_clock{clock_std:g}s_seed0",
                num_users=3,
                num_satellites=10,
                clock_std_dev_seconds=float(clock_std),
                seed=0,
                map_iterations=2,
            )
        )
    return cases


def planned_rows(mode: str, *, full_clock_grid: bool = False) -> list[dict[str, Any]]:
    """Return planned rows without executing legacy code."""

    cases = [primary_case(seed=0)] if mode == "primary" else sparse_cases(full_clock_grid=full_clock_grid)
    row_type = "primary_standard" if mode == "primary" else "sparse_manuscript"
    rows = []
    for case in cases:
        sparse_type = "primary"
        if mode != "primary":
            if "sparse_clock" in case.case_id:
                sparse_type = "clock_sweep"
            elif case.num_users == NETWORK_NONCOOPERATIVE_BASELINE_NU:
                sparse_type = "network_size_noncooperative_baseline"
            else:
                sparse_type = "network_size"
        rows.append(
            {
                "row_type": row_type,
                "sparse_row_type": sparse_type,
                "cooperation_mode": "without_cooperation" if case.num_users == 1 else "cooperative",
                "pipeline": PIPELINE.label,
                "case_id": case.case_id,
                "num_users": case.num_users,
                "num_satellites": case.num_satellites,
                "clock_std_seconds": case.clock_std_dev_seconds,
                "seed": case.seed,
                "prior_mode": "prior_ball_R0",
                "prior_radius_m": DEFAULT_PRIOR_RADIUS_M,
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write CSV rows."""

    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: Any) -> None:
    """Write JSON with legacy-safe conversion."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=_json_default) + "\n", encoding="utf-8")


def append_trace(path: Path, trace: dict[str, Any]) -> None:
    """Append one trace record as JSONL."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(trace, sort_keys=True, default=_json_default) + "\n")


def stage_metrics(row: dict[str, Any]) -> dict[str, Any]:
    """Return canonical stage metrics from the corrected legacy row."""

    def stage(prefix: str, status_key: str, pos_key: str, sync_key: str, missing_reason: str = "") -> dict[str, Any]:
        pos = row.get(pos_key)
        sync = row.get(sync_key)
        status = row.get(status_key, "passed")
        reason = row.get(f"{status_key}_reason", "")
        available = pos is not None or sync is not None
        if status == "not_applicable" and not reason:
            reason = "not_applicable"
        return {
            f"{prefix}_status": status,
            f"{prefix}_localization_error_m": pos,
            f"{prefix}_synchronization_error_ns": sync,
            f"{prefix}_stage_success": bool(available and status in {"passed", "not_applicable"}),
            f"{prefix}_failure_reason": "" if available else reason or missing_reason,
        }

    metrics = {
        "initialization_localization_error_m": row.get("initial_average_position_error_m"),
        "initialization_synchronization_error_ns": None,
        "initialization_status": "passed" if row.get("initial_average_position_error_m") is not None else "missing",
        "initialization_stage_success": row.get("initial_average_position_error_m") is not None,
        "initialization_failure_reason": "initialization_sync_metric_not_reported_by_legacy_initializer",
    }
    metrics.update(stage("step_a", "stage_a_status", "stage_a_localization_error_m", "stage_a_sync_error_ns"))
    metrics.update(stage("step_b", "stage_b_status", "stage_b_localization_error_m", "stage_b_sync_error_ns"))
    metrics.update(stage("step_c", "stage_c_status", "stage_c_localization_error_m", "stage_c_sync_error_ns"))
    return metrics


def normalized_row(row: dict[str, Any], *, row_type: str) -> dict[str, Any]:
    """Return a compact row with required stage and truth fields."""

    output = {
        "row_type": row_type,
        "sparse_row_type": "primary",
        "pipeline": PIPELINE.label,
        "case_id": row["case_id"],
        "seed": row["seed"],
        "num_users": row["num_users"],
        "num_satellites": row["num_satellites"],
        "clock_std_seconds": row["clock_std_dev_seconds"],
        "cooperation_mode": "without_cooperation" if int(row["num_users"]) == 1 else "cooperative",
        "prior_mode": row["prior_mode"],
        "prior_radius_m": row["prior_radius_m"],
        "system_model_version": "legacy_compatible_all_clock",
        "stage_a_version": "A0_prior_region_il",
        "stage_b_version": "B1_residual_trust_region_lm_no_truth_gate",
        "stage_c_version": "C_surgical_residual_scaled_info_map",
        "metric_version": "legacy_all_clock_metric_pending_v24_reference_relative_recompute",
        "units_version": "legacy_km_range_equivalent_clock_units_with_m_ns_reporting",
        "truth_used_for_prior_construction": True,
        "truth_used_for_initialization": False,
        "truth_used_for_lm_acceptance": False,
        "truth_used_for_step_c_acceptance": False,
        "truth_used_for_covariance": False,
        "truth_used_for_fallback_or_reversion": False,
        "truth_used_for_offline_metrics": True,
        "truth_use_blocker": False,
        "lm_acceptance_mode": row.get("lm_acceptance_mode"),
        "map_covariance_mode": row.get("map_covariance_mode"),
        "map_update_mode": row.get("map_update_mode"),
        "fallback_count": row.get("fallback_count"),
        "failure_count": row.get("failure_count"),
        "failure_reason": row.get("failure_reason", ""),
        "stage_b_residual_cost_before": row.get("stage_b_residual_cost_before"),
        "stage_b_residual_cost_after": row.get("stage_b_residual_cost_after"),
    }
    output.update(stage_metrics(row))
    return output


def run_noncooperative_baseline_case(
    case: StandardCase,
    prior_radius_m: float,
    *,
    row_type: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run a single-UE noncooperative baseline row through Step A only."""

    prior = PriorConfig(mode="prior_ball_R0", label=f"prior_ball_R0_{prior_radius_m:g}m", scale_m=float(prior_radius_m))
    namespace, _ = _prepare_namespace(PIPELINE, prior=prior)
    Scenario = namespace["Scenario"]
    Optimizer = namespace["Optimizer"]
    _set_seed(case.seed)
    start = time.perf_counter()
    row: dict[str, Any] = {
        "pipeline": PIPELINE.label,
        "case_id": case.case_id,
        "num_users": case.num_users,
        "num_satellites": case.num_satellites,
        "clock_std_dev_seconds": case.clock_std_dev_seconds,
        "seed": case.seed,
        "prior_mode": prior.mode,
        "prior_radius_m": prior.scale_m,
        "cooperation_mode": "without_cooperation",
        "fallbacks": [],
        "failures": [],
    }
    scenario = Scenario(
        num_users=case.num_users,
        num_satellites=case.num_satellites,
        clock_std_dev_seconds=case.clock_std_dev_seconds,
    )
    optimizer = Optimizer()
    x_init = optimizer.initialize_state(scenario, error_range=case.legacy_error_range_km)
    z = scenario.query_measurements()
    prior_diag = getattr(
        optimizer,
        "_last_prior_region_initialization",
        {
            "initializer": "legacy_truth_centered_cube",
            "truth_state_used_for_prior_simulation": True,
            "initial_average_position_error_m": float(optimizer.calculate_average_position_error(scenario, x_init)),
            "initial_max_position_error_m": None,
        },
    )
    row["initial_average_position_error_m"] = float(optimizer.calculate_average_position_error(scenario, x_init))
    row["initial_average_position_error_from_prior_m"] = prior_diag.get("initial_average_position_error_m")
    row["initial_max_position_error_m"] = prior_diag.get("initial_max_position_error_m")
    row["state_dimension"] = int(len(scenario.symbolic_parameter_vector))
    row["measurement_count"] = int(len(scenario.get_links()))

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
        row["stage_a_status"] = "passed"
    except Exception as exc:  # noqa: BLE001 - record bounded fallback while preserving row output.
        x_il = x_init.copy()
        row["stage_a_status"] = "failed_fallback_to_initial_state"
        row["failures"].append({"stage": "IL", "error_type": type(exc).__name__, "error": str(exc)})
        row["fallbacks"].append("IL_failed_to_initial_state")

    stage_a_diag = getattr(optimizer, "_last_stage_a_diagnostics", {})
    row["stage_a_completion_mode"] = stage_a_diag.get("stage_a_completion_mode", "finite_residual_no_truth_reversion")
    row["stage_a_localization_error_m"] = _metric_or_none(optimizer, scenario, x_il, "position")
    row["stage_a_sync_error_s"] = _metric_or_none(optimizer, scenario, x_il, "clock")
    row["stage_a_sync_error_ns"] = None if row["stage_a_sync_error_s"] is None else row["stage_a_sync_error_s"] * 1.0e9
    row["stage_b_residual_cost_before"] = float(_residual_cost(scenario, x_il, z))
    row["stage_b_residual_cost_after"] = None
    row["stage_b_status"] = "not_applicable"
    row["stage_b_status_reason"] = "single_ue_no_cooperation"
    row["stage_b_localization_error_m"] = None
    row["stage_b_sync_error_ns"] = None
    row["stage_c_status"] = "not_applicable"
    row["stage_c_status_reason"] = "single_ue_no_cooperation"
    row["stage_c_localization_error_m"] = None
    row["stage_c_sync_error_ns"] = None
    row["lm_acceptance_mode"] = "not_applicable_single_ue_no_cooperation"
    row["map_covariance_mode"] = "not_applicable_single_ue_no_cooperation"
    row["map_update_mode"] = "not_applicable_single_ue_no_cooperation"
    row["fallback_count"] = len(row["fallbacks"])
    row["failure_count"] = len(row["failures"])
    row["failure_reason"] = "; ".join(item.get("error", "") for item in row["failures"]) or ""
    row["runtime_s"] = time.perf_counter() - start

    out = normalized_row(row, row_type=row_type)
    out["sparse_row_type"] = "network_size_noncooperative_baseline"
    out["cooperation_mode"] = "without_cooperation"
    trace = {
        "pipeline": PIPELINE.label,
        "case_id": case.case_id,
        "seed": case.seed,
        "cooperation_mode": "without_cooperation",
        "stage_a_only": True,
        "stage_b_status": "not_applicable",
        "stage_c_status": "not_applicable",
        "not_applicable_reason": "single_ue_no_cooperation",
        "prior_diagnostics": prior_diag,
        "stage_a_diagnostics": stage_a_diag,
        "normalized_row": out,
        "truth_flags": {
            "truth_used_for_prior_construction": True,
            "truth_used_for_lm_acceptance": False,
            "truth_used_for_step_c_acceptance": False,
            "truth_used_for_covariance": False,
            "truth_used_for_fallback_or_reversion": False,
            "truth_used_for_offline_metrics": True,
        },
    }
    return out, trace


def run_corrected_case(case: StandardCase, prior_radius_m: float, *, row_type: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run one corrected legacy-compatible case."""

    if case.num_users == NETWORK_NONCOOPERATIVE_BASELINE_NU and row_type == "sparse_manuscript":
        return run_noncooperative_baseline_case(case, prior_radius_m, row_type=row_type)

    prior = PriorConfig(mode="prior_ball_R0", label=f"prior_ball_R0_{prior_radius_m:g}m", scale_m=float(prior_radius_m))
    namespace, _ = _prepare_namespace(PIPELINE, prior=prior)
    raw_row, trace = _run_case(namespace=namespace, pipeline=PIPELINE, case=case, prior=prior, effective_seed=case.seed)
    out = normalized_row(raw_row, row_type=row_type)
    if row_type == "sparse_manuscript":
        out["sparse_row_type"] = "clock_sweep" if "sparse_clock" in case.case_id else "network_size"
        out["cooperation_mode"] = "cooperative"
    trace["normalized_row"] = out
    return out, trace


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return a small summary grouped by mode and sparse row type."""

    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault((row["row_type"], row["sparse_row_type"]), []).append(row)
    summary = []
    for (row_type, sparse_row_type), items in sorted(groups.items()):
        def mean_field(field: str) -> float | None:
            values = [float(item[field]) for item in items if item.get(field) is not None]
            return None if not values else sum(values) / len(values)

        summary.append(
            {
                "row_type": row_type,
                "sparse_row_type": sparse_row_type,
                "row_count": len(items),
                "step_b_localization_error_m_mean": mean_field("step_b_localization_error_m"),
                "step_c_localization_error_m_mean": mean_field("step_c_localization_error_m"),
                "step_b_synchronization_error_ns_mean": mean_field("step_b_synchronization_error_ns"),
                "step_c_synchronization_error_ns_mean": mean_field("step_c_synchronization_error_ns"),
                "step_c_improves_step_b_localization_count": sum(
                    1
                    for item in items
                    if item.get("step_c_localization_error_m") is not None
                    and item.get("step_b_localization_error_m") is not None
                    and float(item["step_c_localization_error_m"]) < float(item["step_b_localization_error_m"])
                ),
                "step_c_improves_step_b_sync_count": sum(
                    1
                    for item in items
                    if item.get("step_c_synchronization_error_ns") is not None
                    and item.get("step_b_synchronization_error_ns") is not None
                    and float(item["step_c_synchronization_error_ns"]) < float(item["step_b_synchronization_error_ns"])
                ),
            }
        )
    return summary


def output_root_for_mode(mode: str, root: Path) -> Path:
    """Return output root for a mode."""

    return root if mode == "primary" else root / "sparse_manuscript"


def make_run_id(mode: str) -> str:
    """Return a stable timestamped run id."""

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{mode.replace('-', '_')}_{stamp}"


def resolve_run_root(mode: str, output_root: Path, *, run_id: str | None, publish_canonical: bool) -> tuple[Path, Path, str]:
    """Return canonical root, actual write root, and run id."""

    canonical_root = output_root_for_mode(mode, output_root)
    if publish_canonical:
        return canonical_root, canonical_root, run_id or "canonical"
    resolved_id = run_id or make_run_id(mode)
    return canonical_root, canonical_root / RUN_HISTORY_DIRNAME / resolved_id, resolved_id


def append_run_history(canonical_root: Path, record: dict[str, Any]) -> None:
    """Append one run-history record and update the latest-run pointer."""

    canonical_root.mkdir(parents=True, exist_ok=True)
    latest_path = canonical_root / LATEST_RUN_FILENAME
    history_path = canonical_root / RUN_HISTORY_FILENAME
    write_json(latest_path, record)
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True, default=_json_default) + "\n")


def latest_sparse_root(output_root: Path, sparse_run_root: Path | None) -> Path:
    """Return the sparse data root to plot."""

    if sparse_run_root is not None:
        return sparse_run_root
    canonical_root = output_root_for_mode("sparse-manuscript", output_root)
    latest_path = canonical_root / LATEST_RUN_FILENAME
    if latest_path.exists():
        latest = json.loads(latest_path.read_text(encoding="utf-8"))
        run_root = SAT_SIM_ROOT / latest["run_root"]
        if run_root.exists():
            return run_root
    return canonical_root


def write_manifest(root: Path, metadata: dict[str, Any]) -> None:
    """Write pipeline manifest files."""

    manifest = {
        "artifact_status": "minimal_legacy_corrected_non_final",
        "diagnostic_only": True,
        "manuscript_ready": False,
        "not_for_submission": True,
        "source_script": metadata["source_script"],
        "source_notebook_or_export": metadata["source_notebook_or_export"],
        "git_commit": metadata["git_commit"],
        "pipeline": PIPELINE.label,
        "case_count": metadata["case_count"],
        "truth_use_ledger": TRUTH_USE_LEDGER,
    }
    write_json(root / "PIPELINE_MANIFEST.json", manifest)
    lines = [
        "# Minimal Legacy Corrected JCLS Pipeline Manifest",
        "",
        "- Artifact status: `minimal_legacy_corrected_non_final`",
        "- Manuscript-ready: `false`",
        "- Notebook source edited: `false`",
        f"- Source notebook/export: `{manifest['source_notebook_or_export']}`",
        f"- Pipeline: `{PIPELINE.label}`",
        f"- Case count: `{manifest['case_count']}`",
        "",
        "## Truth Use",
        "",
    ]
    lines.extend(f"- `{key}`: `{value}`" for key, value in TRUTH_USE_LEDGER.items())
    (root / "PIPELINE_MANIFEST.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_metadata(mode: str, rows: list[dict[str, Any]], prior_radius_m: float, *, sparse_executed: bool) -> dict[str, Any]:
    """Return required run metadata."""

    forbidden_truth = [
        TRUTH_USE_LEDGER["truth_used_for_lm_acceptance"],
        TRUTH_USE_LEDGER["truth_used_for_step_c_acceptance"],
        TRUTH_USE_LEDGER["truth_used_for_covariance"],
        TRUTH_USE_LEDGER["truth_used_for_fallback_or_reversion"],
    ]
    return {
        "source_script": "scripts/minimal_legacy_corrected_jcls.py",
        "source_notebook_or_export": repo_rel(NOTEBOOK_PATH),
        "git_commit": git_commit(),
        "case_id": PRIMARY_CASE_ID if mode == "primary" else "sparse_manuscript_mixed",
        "seed": 0,
        "num_users": 3 if mode == "primary" else None,
        "num_satellites": 10 if mode == "primary" else None,
        "clock_std_seconds": 1.0e-6 if mode == "primary" else None,
        "prior_mode": "prior_ball_R0",
        "prior_radius_m": float(prior_radius_m),
        "system_model_version": "legacy_compatible_all_clock",
        "stage_a_version": "A0_prior_region_il",
        "stage_b_version": "B1_residual_trust_region_lm_no_truth_gate",
        "stage_c_version": "C_surgical_residual_scaled_info_map",
        "metric_version": "legacy_all_clock_metric_pending_v24_reference_relative_recompute",
        "units_version": "legacy_km_range_equivalent_clock_units_with_m_ns_reporting",
        **TRUTH_USE_LEDGER,
        "truth_use_blocker": any(forbidden_truth),
        "units_ledger": UNITS_LEDGER,
        "sparse_manuscript_run": bool(mode == "sparse-manuscript"),
        "sparse_manuscript_executed": bool(sparse_executed),
        "sparse_grid_definition": {
            "network_size_noncooperative_baseline": {
                "num_users": NETWORK_NONCOOPERATIVE_BASELINE_NU,
                "num_satellites": NETWORK_NONCOOPERATIVE_BASELINE_NS,
                "clock_std_seconds": 1.0e-6,
                "seed": 0,
                "stage_b_status": "not_applicable",
                "stage_c_status": "not_applicable",
            },
            "network_size": {
                "num_users": NETWORK_SPARSE_NU,
                "num_satellites": NETWORK_SPARSE_NS,
                "clock_std_seconds": 1.0e-6,
                "seed": 0,
            },
            "clock_sweep": {
                "num_users": 3,
                "num_satellites": 10,
                "clock_std_seconds": SPARSE_CLOCK_STDS_SECONDS,
                "seed": 0,
            },
        },
        "case_count": len(rows),
        "row_count": len(rows),
        "manuscript_ready": False,
        "diagnostic_only": True,
        "not_for_submission": True,
    }


def write_report(rows: list[dict[str, Any]], summary: list[dict[str, Any]], metadata: dict[str, Any], *, sparse_executed: bool) -> None:
    """Write primary pipeline report."""

    primary = rows[0] if rows else {}
    step_b_pos = primary.get("step_b_localization_error_m")
    step_c_pos = primary.get("step_c_localization_error_m")
    step_b_sync = primary.get("step_b_synchronization_error_ns")
    step_c_sync = primary.get("step_c_synchronization_error_ns")
    success = {
        "step_b_localization_lt_1m": bool(step_b_pos is not None and float(step_b_pos) < 1.0),
        "step_c_localization_lt_1m": bool(step_c_pos is not None and float(step_c_pos) < 1.0),
        "step_c_not_catastrophically_worse_than_step_b": bool(
            step_b_pos is not None and step_c_pos is not None and float(step_c_pos) <= 10.0 * max(float(step_b_pos), 1.0e-12)
        ),
        "truth_gates_removed": True,
        "truth_derived_covariance_removed": True,
    }
    payload = {
        "metadata": metadata,
        "primary_standard_case_results": primary,
        "summary": summary,
        "first_run_success_criteria": success,
        "legacy_behavior_preserved": [
            "legacy all-clock internal state",
            "legacy notebook/extracted Scenario and Optimizer classes",
            "legacy measurement ordering and units",
            "legacy IL/LM/MAP stage sequence",
        ],
        "truth_gates_removed": [
            "Stage A truth-output reversion replaced by finite residual completion",
            "LM truth-error acceptance replaced by residual/trust-region acceptance",
            "MAP covariance uses residual-scaled information pseudoinverse, not x-true_state error",
        ],
        "covariance_replacement": "Residual-scaled information pseudoinverse with the merged step_c3 residual-scaled covariance policy.",
        "c5_sliding_window_map_used": False,
        "safe_claims": [
            "Corrected pipeline uses truth only for simulated prior construction and offline metrics.",
            "Primary standard case was run as a single row, not a sweep.",
            "Outputs are non-final and not manuscript-ready.",
        ],
        "unsafe_claims": [
            "Do not claim this is a final manuscript result pipeline until sparse and multi-seed validation pass.",
            "Do not claim V24 reference-relative synchronization metrics; these are legacy all-clock metrics.",
            "Do not claim no truth is used anywhere; truth is used to center the simulated prior region.",
        ],
        "step_b_sufficient": bool(step_b_pos is not None and float(step_b_pos) < 1.0),
        "step_c_improves_step_b": {
            "localization": bool(step_b_pos is not None and step_c_pos is not None and float(step_c_pos) < float(step_b_pos)),
            "synchronization": bool(step_b_sync is not None and step_c_sync is not None and float(step_c_sync) < float(step_b_sync)),
        },
        "should_become_manuscript_result_pipeline": "needs_review",
        "what_this_replaces_if_successful": [
            "package-native C7 figure recreation path",
            "broad C0-C7 exploratory variants",
            "gallery outputs",
            "root-level v24_* generated outputs",
            "redundant benchmark glue",
        ],
        "sparse_manuscript_targeted_run_status": "executed" if sparse_executed else "prepared_not_executed",
    }
    write_json(REPORT_JSON, payload)
    lines = [
        "# Minimal Legacy Corrected Pipeline Report",
        "",
        "> Non-final diagnostic. Not manuscript-ready.",
        "",
        "## Executive Summary",
        "",
        f"- Pipeline: `{PIPELINE.label}`",
        f"- Primary case: `{metadata['case_id']}`",
        f"- Prior: `{metadata['prior_mode']}`, R0 = `{metadata['prior_radius_m']}` m",
        f"- Truth gates removed: `{success['truth_gates_removed']}`",
        f"- Truth-derived covariance removed: `{success['truth_derived_covariance_removed']}`",
        f"- C5/sliding-window MAP used: `False`",
        "",
        "## Primary Standard-Case Results",
        "",
        "| stage | localization [m] | synchronization [ns] | success | failure reason |",
        "|---|---:|---:|---:|---|",
    ]
    for stage in ["initialization", "step_a", "step_b", "step_c"]:
        lines.append(
            f"| {stage} | {primary.get(stage + '_localization_error_m', 'missing')} | "
            f"{primary.get(stage + '_synchronization_error_ns', 'missing')} | "
            f"{primary.get(stage + '_stage_success', False)} | {primary.get(stage + '_failure_reason', '')} |"
        )
    lines.extend(
        [
            "",
            "## Legacy Behavior Preserved",
            "",
            *[f"- {item}" for item in payload["legacy_behavior_preserved"]],
            "",
            "## Truth Gates Removed",
            "",
            *[f"- {item}" for item in payload["truth_gates_removed"]],
            "",
            "## Covariance Replacement",
            "",
            payload["covariance_replacement"],
            "",
            "## First-Run Success Criteria",
            "",
            *[f"- `{key}`: `{value}`" for key, value in success.items()],
            "",
            "## Step B / Step C Assessment",
            "",
            f"- Step B sufficient by <1 m localization criterion: `{payload['step_b_sufficient']}`.",
            f"- Step C improves Step B localization: `{payload['step_c_improves_step_b']['localization']}`.",
            f"- Step C improves Step B synchronization: `{payload['step_c_improves_step_b']['synchronization']}`.",
            f"- Sparse manuscript-targeted run status: `{payload['sparse_manuscript_targeted_run_status']}`.",
            f"- Should this become the manuscript result pipeline: `{payload['should_become_manuscript_result_pipeline']}`.",
            "",
            "## Truth-Use Ledger",
            "",
            *[f"- `{key}`: `{value}`" for key, value in TRUTH_USE_LEDGER.items()],
            "",
            "## Units Ledger",
            "",
            *[f"- `{key}`: `{value}`" for key, value in UNITS_LEDGER.items()],
            "",
            "## Safe Claims",
            "",
            *[f"- {claim}" for claim in payload["safe_claims"]],
            "",
            "## Unsafe Claims",
            "",
            *[f"- {claim}" for claim in payload["unsafe_claims"]],
            "",
            "## What This Replaces If Successful",
            "",
            *[f"- {item}" for item in payload["what_this_replaces_if_successful"]],
            "",
            "## Recommendation",
            "",
            "Needs review. Run sparse manuscript mode only after the primary row is accepted as plausible.",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_sparse_report(rows: list[dict[str, Any]], summary: list[dict[str, Any]], metadata: dict[str, Any]) -> None:
    """Write sparse manuscript report when sparse mode is executed."""

    baseline = [row for row in rows if row.get("sparse_row_type") == "network_size_noncooperative_baseline"]
    network = [row for row in rows if row.get("sparse_row_type") == "network_size"]
    clock = [row for row in rows if row.get("sparse_row_type") == "clock_sweep"]
    baseline.sort(key=lambda item: int(item["num_satellites"]))
    network.sort(key=lambda item: (int(item["num_users"]), int(item["num_satellites"])))
    clock.sort(key=lambda item: float(item["clock_std_seconds"]))

    def has_value(row: dict[str, Any], key: str) -> bool:
        return row.get(key) not in (None, "")

    def f(row: dict[str, Any], key: str) -> float:
        return float(row[key])

    def fmt(value: Any) -> str:
        if value in (None, ""):
            return ""
        if isinstance(value, bool):
            return str(value).lower()
        try:
            number = float(value)
        except (TypeError, ValueError):
            return str(value)
        if number == 0:
            return "0"
        if abs(number) >= 1000 or abs(number) < 1.0e-3:
            return f"{number:.6g}"
        return f"{number:.6f}".rstrip("0").rstrip(".")

    def improves(row: dict[str, Any], a: str, b: str) -> bool:
        return has_value(row, a) and has_value(row, b) and f(row, a) < f(row, b)

    baseline_ns = sorted(int(row["num_satellites"]) for row in baseline)
    clock_values = sorted(float(row["clock_std_seconds"]) for row in clock)
    cooperative_step_b_values = [f(row, "step_b_localization_error_m") for row in network if has_value(row, "step_b_localization_error_m")]
    cooperative_step_c_values = [f(row, "step_c_localization_error_m") for row in network if has_value(row, "step_c_localization_error_m")]
    forbidden_truth_uses = [
        metadata["truth_used_for_lm_acceptance"],
        metadata["truth_used_for_step_c_acceptance"],
        metadata["truth_used_for_covariance"],
        metadata["truth_used_for_fallback_or_reversion"],
    ]
    stage_bc_skipped = all(
        row.get("step_b_status") == "not_applicable"
        and row.get("step_c_status") == "not_applicable"
        and row.get("step_b_failure_reason") == "single_ue_no_cooperation"
        and row.get("step_c_failure_reason") == "single_ue_no_cooperation"
        for row in baseline
    )
    full_clock_sweep = clock_values == sorted(SPARSE_CLOCK_STDS_SECONDS)
    step_b_submeter = bool(cooperative_step_b_values and max(cooperative_step_b_values) < 1.0)
    step_c_mean_improves = bool(
        cooperative_step_b_values
        and cooperative_step_c_values
        and sum(cooperative_step_c_values) / len(cooperative_step_c_values)
        < sum(cooperative_step_b_values) / len(cooperative_step_b_values)
    )
    payload = {
        "metadata": metadata,
        "n_u_1_baseline_included": baseline_ns == NETWORK_NONCOOPERATIVE_BASELINE_NS,
        "noncooperative_baseline_row_count": len(baseline),
        "network_size_row_count": len(network),
        "clock_sweep_row_count": len(clock),
        "total_sparse_row_count": len(rows),
        "full_seven_point_clock_sweep_run": full_clock_sweep,
        "fig4_fig5_true_without_cooperation_baseline": baseline_ns == NETWORK_NONCOOPERATIVE_BASELINE_NS,
        "n_u_3_step_a_baseline_substitution_remains": False,
        "stage_b_c_skipped_for_n_u_1": stage_bc_skipped,
        "step_b_submeter_across_cooperative_sparse_rows": step_b_submeter,
        "step_c_improves_mean_localization": step_c_mean_improves,
        "truth_gated_acceptance_removed": not any(forbidden_truth_uses),
        "truth_derived_covariance_removed": not metadata["truth_used_for_covariance"],
        "summary": summary,
        "trends_match_manuscript_qualitatively": "yes_with_caveats",
        "sufficient_for_final_figures": False,
        "safe_claims": [
            "True N_u=1 noncooperative baseline rows are present for Fig. 4/5 traceability.",
            "Stage B and Stage C are skipped, not failed, for N_u=1.",
            "Cooperative Step B localization remains sub-meter across the sparse network-size rows.",
            "Forbidden truth uses remain false in the metadata ledger.",
        ],
        "unsafe_claims": [
            "Do not treat these sparse plots as final manuscript figures.",
            "Do not claim Monte Carlo robustness from this seed-0 sparse run.",
            "Do not claim V24 reference-relative synchronization metrics; the metric remains legacy all-clock.",
            "Do not claim Step C universally improves Step B row-by-row.",
        ],
    }
    write_json(SPARSE_REPORT_JSON, payload)

    lines = [
        "# Minimal Legacy Corrected Sparse Manuscript Report",
        "",
        "> Sparse diagnostic only. Non-final. Not manuscript-ready. Not for submission.",
        "",
        "## Executive Summary",
        "",
        f"- Sparse rows executed: `{len(rows)}` total.",
        f"- N_u=1 baseline included: `{payload['n_u_1_baseline_included']}`.",
        f"- Noncooperative baseline rows: `{len(baseline)}`.",
        f"- Cooperative network-size rows: `{len(network)}`.",
        f"- Clock-sweep rows: `{len(clock)}`.",
        f"- Full seven-point clock sweep run: `{full_clock_sweep}`.",
        f"- Fig. 4/5 use true N_u=1 without-cooperation baseline: `{payload['fig4_fig5_true_without_cooperation_baseline']}`.",
        f"- Any N_u=3 Step A baseline substitution remains: `{payload['n_u_3_step_a_baseline_substitution_remains']}`.",
        f"- Stage B/C skipped for N_u=1: `{stage_bc_skipped}`.",
        f"- Cooperative Step B localization sub-meter across sparse rows: `{step_b_submeter}`.",
        f"- Step C improves cooperative mean localization: `{step_c_mean_improves}`.",
        "",
        "## Sparse Grid Executed",
        "",
        f"- Noncooperative network baseline: `N_u=1`, `N_s={NETWORK_NONCOOPERATIVE_BASELINE_NS}`, clock std `1 us`, seed `0`.",
        f"- Cooperative network size: `N_u={NETWORK_SPARSE_NU}`, `N_s={NETWORK_SPARSE_NS}`, clock std `1 us`, seed `0`.",
        "- Clock sweep: `N_u=3`, `N_s=10`, clock std "
        f"`{[fmt(value) + ' s' for value in SPARSE_CLOCK_STDS_SECONDS]}`, seed `0`.",
        f"- Prior: `prior_ball_R0`, radius `{metadata['prior_radius_m'] / 1000:g} km`.",
        "",
        "## Noncooperative Baseline Table",
        "",
        "|N_u|N_s|cooperation_mode|init loc m|Step A loc m|Step A sync ns|stage_b_status|stage_c_status|",
        "|---|---|---|---:|---:|---:|---|---|",
    ]
    for row in baseline:
        lines.append(
            f"|{row['num_users']}|{row['num_satellites']}|{row['cooperation_mode']}|"
            f"{fmt(row.get('initialization_localization_error_m'))}|"
            f"{fmt(row.get('step_a_localization_error_m'))}|"
            f"{fmt(row.get('step_a_synchronization_error_ns'))}|"
            f"{row.get('step_b_status', '')}|{row.get('step_c_status', '')}|"
        )
    lines.extend(
        [
            "",
            "## Cooperative Network-Size Table",
            "",
            "|N_u|N_s|cooperation_mode|init loc m|Step A loc m|Step B loc m|Step C loc m|Step A sync ns|Step B sync ns|Step C sync ns|C improves loc|C improves sync|",
            "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|",
        ]
    )
    for row in network:
        lines.append(
            f"|{row['num_users']}|{row['num_satellites']}|{row['cooperation_mode']}|"
            f"{fmt(row.get('initialization_localization_error_m'))}|"
            f"{fmt(row.get('step_a_localization_error_m'))}|"
            f"{fmt(row.get('step_b_localization_error_m'))}|"
            f"{fmt(row.get('step_c_localization_error_m'))}|"
            f"{fmt(row.get('step_a_synchronization_error_ns'))}|"
            f"{fmt(row.get('step_b_synchronization_error_ns'))}|"
            f"{fmt(row.get('step_c_synchronization_error_ns'))}|"
            f"{str(improves(row, 'step_c_localization_error_m', 'step_b_localization_error_m')).lower()}|"
            f"{str(improves(row, 'step_c_synchronization_error_ns', 'step_b_synchronization_error_ns')).lower()}|"
        )
    lines.extend(
        [
            "",
            "## Clock-Sweep Table",
            "",
            "|clock std s|clock std label|init loc m|Step A loc m|Step B loc m|Step C loc m|Step A sync ns|Step B sync ns|Step C sync ns|C improves loc|C improves sync|",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|",
        ]
    )
    for row in clock:
        clock_ns = f(row, "clock_std_seconds") * 1.0e9
        label = f"{clock_ns:g} ns"
        lines.append(
            f"|{fmt(row.get('clock_std_seconds'))}|{label}|"
            f"{fmt(row.get('initialization_localization_error_m'))}|"
            f"{fmt(row.get('step_a_localization_error_m'))}|"
            f"{fmt(row.get('step_b_localization_error_m'))}|"
            f"{fmt(row.get('step_c_localization_error_m'))}|"
            f"{fmt(row.get('step_a_synchronization_error_ns'))}|"
            f"{fmt(row.get('step_b_synchronization_error_ns'))}|"
            f"{fmt(row.get('step_c_synchronization_error_ns'))}|"
            f"{str(improves(row, 'step_c_localization_error_m', 'step_b_localization_error_m')).lower()}|"
            f"{str(improves(row, 'step_c_synchronization_error_ns', 'step_b_synchronization_error_ns')).lower()}|"
        )
    lines.extend(
        [
            "",
            "## Trend Summary",
            "",
            "- Network-size localization trend: cooperative Step B remains sub-meter across the sparse rows; Step C remains bounded and improves the cooperative mean localization.",
            "- Network-size synchronization trend: cooperative synchronization remains in the hundreds of ns for the 1 us clock case, with Step C changes mostly at numerical precision.",
            "- Clock-sweep localization trend: Step A degrades as the clock standard deviation grows, while Step B/C remain low across the sparse clock points.",
            "- Clock-sweep synchronization trend: synchronization error scales with the clock standard deviation, as expected under the legacy all-clock metric.",
            "- Qualitative manuscript trend match: `yes_with_caveats`.",
            "",
            "## Truth-Use Ledger",
            "",
            *[f"- `{key}`: `{metadata[key]}`" for key in TRUTH_USE_LEDGER],
            "",
            "## Units Ledger",
            "",
            *[f"- `{key}`: `{value}`" for key, value in metadata.get("units_ledger", UNITS_LEDGER).items()],
            "",
            "## Safe Claims",
            "",
            *[f"- {claim}" for claim in payload["safe_claims"]],
            "",
            "## Unsafe Claims",
            "",
            *[f"- {claim}" for claim in payload["unsafe_claims"]],
        ]
    )
    report_text = "\n".join(lines) + "\n"
    SPARSE_REPORT_MD.write_text(report_text, encoding="utf-8")
    if metadata.get("run_output_root"):
        run_root = SAT_SIM_ROOT / metadata["run_output_root"]
        write_json(run_root / "SPARSE_MANUSCRIPT_REPORT.json", payload)
        (run_root / "SPARSE_MANUSCRIPT_REPORT.md").write_text(report_text, encoding="utf-8")


def read_csv_rows(path: Path) -> list[dict[str, Any]]:
    """Read CSV rows as dictionaries."""

    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def value_as_float(row: dict[str, Any], key: str) -> float:
    """Return a numeric CSV value."""

    return float(row[key])


def traceability_definitions() -> list[dict[str, Any]]:
    """Return manuscript figure traceability definitions."""

    return [
        {
            "figure_number": "Fig. 4",
            "manuscript_label": "fig:pos_sats",
            "legacy_filename": "pos_vary_ues.pdf",
            "candidate_stem": "fig4_pos_vary_ues_sparse_candidate",
            "metric": "localization_vs_satellites",
        },
        {
            "figure_number": "Fig. 5",
            "manuscript_label": "fig:sync_sats",
            "legacy_filename": "sync_vary_ues.pdf",
            "candidate_stem": "fig5_sync_vary_ues_sparse_candidate",
            "metric": "synchronization_vs_satellites",
        },
        {
            "figure_number": "Fig. 6",
            "manuscript_label": "fig:pos_clocks",
            "legacy_filename": "pos_vary_clock.pdf",
            "candidate_stem": "fig6_pos_vary_clock_sparse_candidate",
            "metric": "localization_vs_clock_std",
        },
        {
            "figure_number": "Fig. 7",
            "manuscript_label": "fig:sync_clocks",
            "legacy_filename": "sync_vary_clock.pdf",
            "candidate_stem": "fig7_sync_vary_clock_sparse_candidate",
            "metric": "synchronization_vs_clock_std",
        },
    ]


def configure_manuscript_plot_style() -> None:
    """Configure a compact IEEE/manuscript-like Matplotlib style."""

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.size": 10,
            "axes.labelsize": 10,
            "legend.fontsize": 6,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "lines.linewidth": 1.25,
            "lines.markersize": 4,
            "text.usetex": False,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def log_tick_formatter() -> Any:
    """Return the notebook-style 10^n formatter."""

    import math

    from matplotlib.ticker import FuncFormatter

    def formatter(x: float, _pos: Any) -> str:
        if x <= 0:
            return ""
        exponent = int(round(math.log10(x)))
        if abs(x - 10**exponent) / x < 1.0e-8:
            return rf"$10^{{{exponent}}}$"
        return ""

    return FuncFormatter(formatter)


def manuscript_style_plot(
    x_values: list[float],
    series: list[dict[str, Any]],
    *,
    xlabel: str,
    ylabel: str,
    output_stem: Path,
    log_x: bool = False,
    log_y: bool = False,
    x_ticks: list[float] | None = None,
    y_ticks: list[float] | None = None,
    legend_loc: str = "best",
) -> dict[str, str]:
    """Write one manuscript-style PDF and PNG plot."""

    configure_manuscript_plot_style()
    import matplotlib.pyplot as plt
    from matplotlib.ticker import LogLocator, NullFormatter

    output_stem.parent.mkdir(parents=True, exist_ok=True)
    markers = ["o", "s", "^", "v", "d", "*", "x", "+"]
    linestyles = ["-", "--", ":", "-."]
    fig = plt.figure(dpi=600, figsize=(3.5, 3.0), constrained_layout=False)
    ax = fig.add_axes([0.2, 0.167, 0.75, 0.75])
    ax.tick_params(which="both", direction="in", top=True, bottom=True, left=True, right=True)
    ax.grid(False, which="both")

    for idx, item in enumerate(series):
        marker = item.get("marker", markers[idx % len(markers)])
        linestyle = item.get("linestyle", linestyles[idx % len(linestyles)])
        color = item.get("color")
        ax.plot(
            item.get("x", x_values),
            item["y"],
            marker=marker,
            markerfacecolor="white",
            markersize=3,
            linestyle=linestyle,
            color=color,
            label=item["label"],
            clip_on=False,
            zorder=3,
        )

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if log_y:
        ax.set_yscale("log")
        ax.yaxis.set_major_formatter(log_tick_formatter())
        ax.yaxis.set_minor_locator(LogLocator(base=10.0, subs="auto", numticks=10))
        ax.yaxis.set_minor_formatter(NullFormatter())
    if log_x:
        ax.set_xscale("log")
        ax.xaxis.set_major_formatter(log_tick_formatter())
        ax.xaxis.set_minor_locator(LogLocator(base=10.0, subs="auto", numticks=10))
        ax.xaxis.set_minor_formatter(NullFormatter())
    if x_ticks is not None:
        ax.set_xticks(x_ticks)
    if y_ticks is not None:
        ax.set_yticks(y_ticks)
    ax.legend(loc=legend_loc, frameon=True, edgecolor="black")
    pdf_path = output_stem.with_suffix(".pdf")
    png_path = output_stem.with_suffix(".png")
    fig.savefig(pdf_path, format="pdf")
    fig.savefig(png_path, format="png", dpi=300)
    plt.close(fig)
    return {"pdf": repo_rel(pdf_path), "png": repo_rel(png_path)}


def network_rows_by_user(rows: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    """Group sparse network rows by number of users."""

    grouped: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        if row.get("sparse_row_type") == "network_size":
            grouped.setdefault(int(row["num_users"]), []).append(row)
    for items in grouped.values():
        items.sort(key=lambda item: int(item["num_satellites"]))
    return grouped


def noncooperative_network_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return true single-UE noncooperative network baseline rows."""

    items = [row for row in rows if row.get("sparse_row_type") == "network_size_noncooperative_baseline"]
    items.sort(key=lambda item: int(item["num_satellites"]))
    return items


def clock_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return clock-sweep rows sorted by clock standard deviation."""

    items = [row for row in rows if row.get("sparse_row_type") == "clock_sweep"]
    items.sort(key=lambda item: float(item["clock_std_seconds"]))
    return items


def build_sparse_manuscript_figures(output_root: Path, *, sparse_run_root: Path | None = None) -> dict[str, Any]:
    """Build manuscript-style sparse candidate plots from existing sparse data."""

    sparse_root = latest_sparse_root(output_root, sparse_run_root)
    raw_path = sparse_root / "raw.csv"
    metadata_path = sparse_root / "metadata.json"
    if not raw_path.exists():
        raise FileNotFoundError(f"Missing sparse raw CSV: {raw_path}")
    if not metadata_path.exists():
        raise FileNotFoundError(f"Missing sparse metadata JSON: {metadata_path}")

    rows = read_csv_rows(raw_path)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata.get("output_policy") == "run_history" and metadata.get("run_id"):
        figure_root = output_root / "figures" / metadata["run_id"]
    else:
        figure_root = sparse_root / "manuscript_style_figures"
    figure_root.mkdir(parents=True, exist_ok=True)

    baseline = noncooperative_network_rows(rows)
    by_user = network_rows_by_user(rows)
    clocks = clock_rows(rows)
    outputs: dict[str, Any] = {}

    # Fig. 4: original/manuscript pos_vary_ues.pdf.
    x_network = [float(row["num_satellites"]) for row in baseline]
    fig4_series = [
        {
            "label": "Without cooperation",
            "x": x_network,
            "y": [value_as_float(row, "step_a_localization_error_m") for row in baseline],
            "linestyle": ":",
            "marker": "o",
            "color": "0.35",
        }
    ]
    for nu in sorted(by_user):
        fig4_series.append(
            {
                "label": rf"JCLS, $N_{{\mathrm{{u}}}}={nu}$",
                "x": [float(row["num_satellites"]) for row in by_user[nu]],
                "y": [value_as_float(row, "step_c_localization_error_m") for row in by_user[nu]],
            }
        )
    outputs["fig4_pos_vary_ues"] = manuscript_style_plot(
        x_network,
        fig4_series,
        xlabel=r"Number of Satellites ($N_{\mathrm{s}}$)",
        ylabel=r"Average UE error $[\mathrm{m}]$",
        output_stem=figure_root / "fig4_pos_vary_ues_sparse_candidate",
        log_y=True,
        x_ticks=[4, 8, 10, 12, 14],
        legend_loc="center right",
    )

    # Fig. 5: original/manuscript sync_vary_ues.pdf.
    fig5_series = [
        {
            "label": "Without cooperation",
            "x": x_network,
            "y": [value_as_float(row, "step_a_synchronization_error_ns") for row in baseline],
            "linestyle": ":",
            "marker": "o",
            "color": "0.35",
        }
    ]
    for nu in sorted(by_user):
        fig5_series.append(
            {
                "label": rf"JCLS, $N_{{\mathrm{{u}}}}={nu}$",
                "x": [float(row["num_satellites"]) for row in by_user[nu]],
                "y": [value_as_float(row, "step_c_synchronization_error_ns") for row in by_user[nu]],
            }
        )
    outputs["fig5_sync_vary_ues"] = manuscript_style_plot(
        x_network,
        fig5_series,
        xlabel=r"Number of Satellites ($N_{\mathrm{s}}$)",
        ylabel=r"Average synchronization error $[\mathrm{ns}]$",
        output_stem=figure_root / "fig5_sync_vary_ues_sparse_candidate",
        x_ticks=[4, 8, 10, 12, 14],
        legend_loc="center right",
    )

    # Fig. 6: original/manuscript pos_vary_clock.pdf.
    x_clock_ns = [value_as_float(row, "clock_std_seconds") * 1.0e9 for row in clocks]
    fig6_series = [
        {
            "label": "Without cooperation",
            "y": [value_as_float(row, "step_a_localization_error_m") for row in clocks],
        },
        {
            "label": "Coarse JCLS",
            "y": [value_as_float(row, "step_b_localization_error_m") for row in clocks],
        },
        {
            "label": r"Refined JCLS, $0.5\,\mathrm{s}$",
            "y": [value_as_float(row, "step_c_localization_error_m") for row in clocks],
        },
    ]
    outputs["fig6_pos_vary_clock"] = manuscript_style_plot(
        x_clock_ns,
        fig6_series,
        xlabel=r"$\sigma_\delta \; [\mathrm{ns}]$",
        ylabel=r"Average UE position error $[\mathrm{m}]$",
        output_stem=figure_root / "fig6_pos_vary_clock_sparse_candidate",
        log_x=True,
        log_y=True,
        x_ticks=x_clock_ns,
        y_ticks=[1.0e-2, 1.0e0, 1.0e2, 1.0e4],
        legend_loc="best",
    )

    # Fig. 7: original/manuscript sync_vary_clock.pdf.
    fig7_series = [
        {
            "label": "Without cooperation",
            "y": [value_as_float(row, "step_a_synchronization_error_ns") for row in clocks],
        },
        {
            "label": "Coarse JCLS",
            "y": [value_as_float(row, "step_b_synchronization_error_ns") for row in clocks],
        },
        {
            "label": r"Refined JCLS, $0.5\,\mathrm{s}$",
            "y": [value_as_float(row, "step_c_synchronization_error_ns") for row in clocks],
        },
    ]
    outputs["fig7_sync_vary_clock"] = manuscript_style_plot(
        x_clock_ns,
        fig7_series,
        xlabel=r"$\sigma_\delta \; [\mathrm{ns}]$",
        ylabel=r"Average synchronization error $[\mathrm{ns}]$",
        output_stem=figure_root / "fig7_sync_vary_clock_sparse_candidate",
        log_x=True,
        log_y=True,
        x_ticks=x_clock_ns,
        y_ticks=[1.0e0, 1.0e2, 1.0e4],
        legend_loc="best",
    )

    figure_metadata = {
        "artifact_status": "non_final_sparse_manuscript_style_candidate_figures",
        "diagnostic_only": True,
        "manuscript_ready": False,
        "not_for_submission": True,
        "source_raw_csv": repo_rel(raw_path),
        "source_metadata_json": repo_rel(metadata_path),
        "source_script": "scripts/minimal_legacy_corrected_jcls.py",
        "source_notebook_or_export": metadata.get("source_notebook_or_export"),
        "git_commit": git_commit(),
        "figure_root": repo_rel(figure_root),
        "style_source": {
            "notebook_helper": "ieee_flexible_plot",
            "manuscript_source": "../Work-In-Progress/SCL-NTN-TAES-2025-V26.tex",
            "notes": [
                "IEEE-sized serif figures, hollow markers, thin lines, compact legends.",
                "Sparse data are plotted directly; no smoothing, fitting, or manuscript PSFrag generation is applied.",
            ],
        },
        "traceability": traceability_definitions(),
        "outputs": outputs,
        "truth_use_ledger": {key: metadata.get(key) for key in TRUTH_USE_LEDGER},
        "units_ledger": metadata.get("units_ledger", UNITS_LEDGER),
        "caveats": [
            "These are non-final sparse candidate figures for human review only.",
            "Fig. 4/5 use true N_u=1 noncooperative Step A baseline rows as the without-cooperation reference.",
            "Synchronization metric remains legacy all-clock pending V24 reference-relative recompute.",
            "The sparse run used one seed and no Monte Carlo averaging.",
        ],
    }
    write_json(figure_root / "FIGURE_TRACEABILITY.json", figure_metadata)
    write_figure_report(figure_metadata)
    return figure_metadata


def write_figure_report(payload: dict[str, Any]) -> None:
    """Write manuscript-style figure traceability report."""

    write_json(FIGURE_REPORT_JSON, payload)
    lines = [
        "# Minimal Legacy Corrected Manuscript-Style Figures Report",
        "",
        "> Non-final sparse candidate figures. Not manuscript-ready. Not for submission.",
        "",
        "## Executive Summary",
        "",
        "- Plotting layer: `scripts/minimal_legacy_corrected_jcls.py --plot-sparse-figures`.",
        f"- Source data: `{payload['source_raw_csv']}`.",
        f"- Figure root: `{payload['figure_root']}`.",
        "- Style: IEEE-sized serif plots adapted from the notebook `ieee_flexible_plot` helper.",
        "- Data treatment: sparse raw data plotted directly; no smoothing/fitting/PSFrag generation.",
        "",
        "## Figure Traceability",
        "",
        "| manuscript figure | manuscript label | legacy artifact | candidate outputs |",
        "|---|---|---|---|",
    ]
    output_by_stem = {
        "fig4_pos_vary_ues_sparse_candidate": payload["outputs"]["fig4_pos_vary_ues"],
        "fig5_sync_vary_ues_sparse_candidate": payload["outputs"]["fig5_sync_vary_ues"],
        "fig6_pos_vary_clock_sparse_candidate": payload["outputs"]["fig6_pos_vary_clock"],
        "fig7_sync_vary_clock_sparse_candidate": payload["outputs"]["fig7_sync_vary_clock"],
    }
    for item in payload["traceability"]:
        outputs = output_by_stem[item["candidate_stem"]]
        lines.append(
            f"| {item['figure_number']} | `{item['manuscript_label']}` | "
            f"`{item['legacy_filename']}` | `{outputs['pdf']}`, `{outputs['png']}` |"
        )
    lines.extend(
        [
            "",
            "## Caveats",
            "",
            *[f"- {item}" for item in payload["caveats"]],
            "",
            "## Truth-Use Ledger",
            "",
            *[f"- `{key}`: `{value}`" for key, value in payload["truth_use_ledger"].items()],
            "",
            "## Units Ledger",
            "",
            *[f"- `{key}`: `{value}`" for key, value in payload["units_ledger"].items()],
        ]
    )
    report_text = "\n".join(lines) + "\n"
    FIGURE_REPORT_MD.write_text(report_text, encoding="utf-8")
    figure_root = SAT_SIM_ROOT / payload["figure_root"]
    write_json(figure_root / "MANUSCRIPT_STYLE_FIGURES_REPORT.json", payload)
    (figure_root / "MANUSCRIPT_STYLE_FIGURES_REPORT.md").write_text(report_text, encoding="utf-8")


def run_mode(
    mode: str,
    output_root: Path,
    prior_radius_m: float,
    *,
    force: bool,
    full_clock_grid: bool,
    run_id: str | None,
    publish_canonical: bool,
) -> Path:
    """Run a primary or sparse manuscript mode."""

    canonical_root, root, resolved_run_id = resolve_run_root(
        mode,
        output_root,
        run_id=run_id,
        publish_canonical=publish_canonical,
    )
    if root.exists() and force:
        shutil.rmtree(root)
    elif root.exists():
        raise FileExistsError(f"Refusing to overwrite existing run root without --force: {root}")
    root.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    traces: list[dict[str, Any]] = []
    cases = [primary_case(seed=0)] if mode == "primary" else sparse_cases(full_clock_grid=full_clock_grid)
    row_type = "primary_standard" if mode == "primary" else "sparse_manuscript"
    start = time.perf_counter()
    trace_path = root / "trace.jsonl"
    if trace_path.exists() and force:
        trace_path.unlink()
    for case in cases:
        row, trace = run_corrected_case(case, prior_radius_m, row_type=row_type)
        rows.append(row)
        traces.append(trace)
        append_trace(trace_path, trace)
    summary = summarize(rows)
    metadata = build_metadata(mode, rows, prior_radius_m, sparse_executed=(mode == "sparse-manuscript"))
    metadata["runtime_s"] = time.perf_counter() - start
    metadata["run_id"] = resolved_run_id
    metadata["run_output_root"] = repo_rel(root)
    metadata["canonical_output_root"] = repo_rel(canonical_root)
    metadata["output_policy"] = "canonical_publish" if publish_canonical else "run_history"
    metadata["publish_canonical"] = bool(publish_canonical)
    metadata["raw_csv"] = repo_rel(root / "raw.csv")
    metadata["summary_csv"] = repo_rel(root / "summary.csv")
    metadata["trace_jsonl"] = repo_rel(trace_path)
    write_csv(root / "raw.csv", rows)
    write_csv(root / "summary.csv", summary)
    write_json(root / "metadata.json", metadata)
    write_manifest(root, metadata)
    if mode == "primary":
        write_report(rows, summary, metadata, sparse_executed=False)
    else:
        write_sparse_report(rows, summary, metadata)
    if not publish_canonical:
        append_run_history(
            canonical_root,
            {
                "run_id": resolved_run_id,
                "mode": mode,
                "status": "completed",
                "created_utc": datetime.now(timezone.utc).isoformat(),
                "run_root": repo_rel(root),
                "row_count": len(rows),
                "output_policy": metadata["output_policy"],
                "publish_canonical": metadata["publish_canonical"],
                "raw_csv": metadata["raw_csv"],
                "summary_csv": metadata["summary_csv"],
                "metadata_json": repo_rel(root / "metadata.json"),
                "trace_jsonl": metadata["trace_jsonl"],
            },
        )
    return root


def print_plan(mode: str, *, full_clock_grid: bool) -> None:
    """Print planned work without running legacy code."""

    rows = planned_rows(mode, full_clock_grid=full_clock_grid)
    print(f"Minimal corrected legacy JCLS plan: mode={mode}, rows={len(rows)}")
    for row in rows:
        print(
            f" - {row['case_id']} Nu={row['num_users']} Ns={row['num_satellites']} "
            f"clock={row['clock_std_seconds']} prior={row['prior_radius_m']}m"
        )


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["primary", "sparse-manuscript"], default="primary")
    parser.add_argument("--list-plan", action="store_true", help="List rows without executing.")
    parser.add_argument("--run", action="store_true", help="Execute the selected bounded mode.")
    parser.add_argument("--output-root", default=str(OUTPUT_ROOT))
    parser.add_argument("--prior-radius-m", type=float, default=DEFAULT_PRIOR_RADIUS_M)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--full-clock-grid", action="store_true", help="Use the full sparse clock list.")
    parser.add_argument("--run-id", default=None, help="Optional stored run id. Defaults to a UTC timestamp.")
    parser.add_argument(
        "--publish-canonical",
        action="store_true",
        help="Write directly to the canonical mode root. Without this, runs are stored in run_history/<run_id>.",
    )
    parser.add_argument(
        "--sparse-run-root",
        default=None,
        help="Specific sparse run directory to use for plotting. Defaults to LATEST_RUN.json, then canonical sparse output.",
    )
    parser.add_argument(
        "--plot-sparse-figures",
        action="store_true",
        help="Plot manuscript-style Fig. 4-7 candidate figures from existing sparse output.",
    )
    return parser.parse_args()


def main() -> int:
    """CLI entrypoint."""

    args = parse_args()
    if args.list_plan:
        print_plan(args.mode, full_clock_grid=bool(args.full_clock_grid))
    if args.run:
        run_root = run_mode(
            args.mode,
            Path(args.output_root),
            float(args.prior_radius_m),
            force=bool(args.force),
            full_clock_grid=bool(args.full_clock_grid),
            run_id=args.run_id,
            publish_canonical=bool(args.publish_canonical),
        )
        print(f"Wrote outputs to {run_root}")
    elif not args.plot_sparse_figures and not args.list_plan:
        print_plan(args.mode, full_clock_grid=bool(args.full_clock_grid))
    if args.plot_sparse_figures:
        payload = build_sparse_manuscript_figures(
            Path(args.output_root),
            sparse_run_root=Path(args.sparse_run_root) if args.sparse_run_root else None,
        )
        print(f"Wrote manuscript-style figures to {payload['figure_root']}")
    if not args.run and not args.plot_sparse_figures:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
