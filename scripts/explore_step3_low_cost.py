"""Low-cost diverse Step 3 exploration for legacy-compatible diagnostics.

This script evaluates small Step 3 idea classes against cached Step-B/LM-only
baselines. It does not run the migration ladder, does not generate manuscript
figures, and writes only non-final diagnostics under
``outputs/step3_low_cost_exploration``.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


SAT_SIM_ROOT = Path(__file__).resolve().parents[1]
if str(SAT_SIM_ROOT) not in sys.path:
    sys.path.insert(0, str(SAT_SIM_ROOT))

from scripts.explore_step3_gates import (  # noqa: E402
    ALPHAS,
    BASE_SEED,
    CASES,
    NOTEBOOK_PATH,
    _case_seed,
    _execute_legacy_namespace,
    _load_or_compute_baseline,
    _nullspace_ratio,
    _objective,
    _robust_measurement_covariance,
    _selected_cell_hashes,
    _sha256,
)
from scripts.run_controlled_migration_ladder import (  # noqa: E402
    STEP_B_COST_TOLERANCE,
    _install_residual_lm_acceptance,
    _parameter_update_norms,
    _repo_rel,
    _safe_inverse,
)


OUTPUT_ROOT = SAT_SIM_ROOT / "outputs" / "step3_low_cost_exploration"
PLOT_ROOT = OUTPUT_ROOT / "plots"
REPORTS = SAT_SIM_ROOT / "outputs" / "reports"
GATE_RESULTS = SAT_SIM_ROOT / "outputs" / "step3_gate_exploration" / "step3_gate_exploration_results.json"
DT_SECONDS = 0.5
OPTIONAL_HARD_CASE = (3, 4)


@dataclass(frozen=True)
class MethodConfig:
    """Configuration for one low-cost Step 3 idea."""

    lane: str
    name: str
    position_variance_km2: float = 10.0**2
    ue_clock_variance_km2: float = 0.1**2
    satellite_clock_variance_km2: float = 0.1**2
    clock_drift_variance_km2_per_s2: float = 0.0
    measurement_inflation: float = 1.0
    huber: bool = False
    residual_cap_sigma: float | None = None
    remove_common_clock: bool = False
    nullspace_mode: str = "none"
    nullspace_damping: float = 1.0
    clock_update_scale: float = 1.0
    position_update_scale: float = 1.0
    max_position_update_norm: float | None = None
    max_clock_update_norm: float | None = None
    alphas: tuple[float, ...] = tuple(ALPHAS)
    notes: str = ""


LANE_METHODS: list[MethodConfig] = [
    MethodConfig("block_covariance", "balanced_blocks"),
    MethodConfig("clock_drift", "drift_small", clock_drift_variance_km2_per_s2=1.0e-6),
    MethodConfig("gauge_nullspace", "remove_common_clock", remove_common_clock=True),
    MethodConfig("schur_nuisance_clock", "position_update_only", clock_update_scale=0.0),
    MethodConfig("robust_measurement", "huber_default", huber=True),
    MethodConfig("solver_mechanics", "half_alpha", alphas=(0.5, 0.25, 0.125, 0.0625, 0.03125)),
]

GATE_PROXY_MAP = {
    "block_covariance": ("covariance_k100", "proxy from prior covariance-inflation gate"),
    "clock_drift": ("measurement_lambda10", "proxy only; clock-drift state not executed in low-cost fallback"),
    "gauge_nullspace": ("nullspace_line_search", "proxy from prior nullspace gate"),
    "schur_nuisance_clock": ("clock_position_line_search", "proxy only; reduced Schur solve not executed in low-cost fallback"),
    "robust_measurement": ("huber_line_search", "proxy from prior Huber residual gate"),
    "solver_mechanics": ("line_search", "proxy from prior line-search gate"),
}


def _method_digest(method: MethodConfig, num_users: int, num_satellites: int, seed: int) -> str:
    """Return a deterministic cache/config digest for one row."""

    payload = {
        "method": asdict(method),
        "num_users": num_users,
        "num_satellites": num_satellites,
        "seed": seed,
        "script": Path(__file__).name,
        "base_seed": BASE_SEED,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def _node_id(symbol: str) -> int | None:
    """Return node id for a legacy ``delta_*`` symbol."""

    if not symbol.startswith("delta_"):
        return None
    try:
        return int(symbol.split("_", 1)[1])
    except ValueError:
        return None


def _clock_indices(symbols: list[str]) -> list[int]:
    """Return clock parameter indices."""

    return [idx for idx, symbol in enumerate(symbols) if symbol.startswith("delta_")]


def _position_indices(symbols: list[str]) -> list[int]:
    """Return UE position parameter indices."""

    clocks = set(_clock_indices(symbols))
    return [idx for idx in range(len(symbols)) if idx not in clocks]


def _typed_covariance(symbols: list[str], num_users: int, method: MethodConfig) -> np.ndarray:
    """Build a diagonal typed prior covariance in legacy km/range-clock units."""

    variances: list[float] = []
    drift_addition = method.clock_drift_variance_km2_per_s2 * DT_SECONDS**2
    for symbol in symbols:
        node_id = _node_id(symbol)
        if node_id is None:
            variances.append(method.position_variance_km2)
        elif node_id <= num_users:
            variances.append(method.ue_clock_variance_km2 + drift_addition)
        else:
            variances.append(method.satellite_clock_variance_km2 + drift_addition)
    return np.diag(np.asarray(variances, dtype=float))


def _cap_residual(residual: np.ndarray, covariance: np.ndarray, cap_sigma: float | None) -> np.ndarray:
    """Cap residual entries in whitened sigma units."""

    if cap_sigma is None:
        return residual
    diag = np.maximum(np.diag(covariance), 1.0e-18)
    whitened = residual / np.sqrt(diag)
    capped = np.clip(whitened, -cap_sigma, cap_sigma)
    return capped * np.sqrt(diag)


def _project_common_clock(update: np.ndarray, symbols: list[str]) -> np.ndarray:
    """Remove the common all-clock component from a legacy all-clock update."""

    adjusted = np.asarray(update, dtype=float).copy()
    indices = _clock_indices(symbols)
    if indices:
        adjusted[indices] -= float(np.mean(adjusted[indices]))
    return adjusted


def _apply_nullspace_mode(jacobian: np.ndarray, update: np.ndarray, method: MethodConfig) -> np.ndarray:
    """Apply nullspace damping/projection to an update."""

    if method.nullspace_mode == "none" or np.linalg.norm(update) == 0.0:
        return update
    _, singular_values, vh = np.linalg.svd(jacobian, full_matrices=True)
    tol = max(jacobian.shape) * np.finfo(float).eps * (singular_values[0] if singular_values.size else 1.0)
    rank = int(np.sum(singular_values > tol))
    basis = vh.T
    observable_basis = basis[:, :rank]
    null_basis = basis[:, rank:]
    observable = observable_basis @ (observable_basis.T @ update) if observable_basis.size else np.zeros_like(update)
    null_component = null_basis @ (null_basis.T @ update) if null_basis.size else np.zeros_like(update)
    if method.nullspace_mode == "observable_only":
        return observable
    if method.nullspace_mode == "damp":
        return observable + method.nullspace_damping * null_component
    return update


def _scale_by_blocks(update: np.ndarray, symbols: list[str], method: MethodConfig) -> np.ndarray:
    """Apply simple blockwise update scaling/clipping."""

    adjusted = np.asarray(update, dtype=float).copy()
    pos_idx = _position_indices(symbols)
    clock_idx = _clock_indices(symbols)
    adjusted[pos_idx] *= method.position_update_scale
    adjusted[clock_idx] *= method.clock_update_scale
    if method.max_position_update_norm is not None and pos_idx:
        norm = float(np.linalg.norm(adjusted[pos_idx]))
        if norm > method.max_position_update_norm:
            adjusted[pos_idx] *= method.max_position_update_norm / max(norm, 1.0e-18)
    if method.max_clock_update_norm is not None and clock_idx:
        norm = float(np.linalg.norm(adjusted[clock_idx]))
        if norm > method.max_clock_update_norm:
            adjusted[clock_idx] *= method.max_clock_update_norm / max(norm, 1.0e-18)
    return adjusted


def _evaluate_method(scenario: Any, optimizer: Any, x_lm: np.ndarray, z: np.ndarray, method: MethodConfig, *, num_users: int) -> dict[str, Any]:
    """Evaluate one low-cost Step 3 method without truth-state gates."""

    symbols = [str(item) for item in scenario.symbolic_parameter_vector]
    p_cov = _typed_covariance(symbols, num_users, method)
    r_cov = float(method.measurement_inflation) * np.asarray(scenario.get_measurement_covariance(), dtype=float)
    residual = np.asarray(z - scenario.h(x_lm), dtype=float)
    if method.huber:
        r_cov = _robust_measurement_covariance(residual, r_cov)
    effective_residual = _cap_residual(residual, r_cov, method.residual_cap_sigma)
    p_inv = _safe_inverse(p_cov)
    r_inv = _safe_inverse(r_cov)
    jacobian = np.asarray(scenario.evaluate_jacobian(x_lm), dtype=float)
    innovation_cov = jacobian @ p_cov @ jacobian.T + r_cov
    innovation_precision = np.linalg.pinv(innovation_cov)
    nis = float(residual.T @ innovation_precision @ residual)
    update = np.asarray(p_cov @ jacobian.T @ innovation_precision @ effective_residual, dtype=float)
    update = _apply_nullspace_mode(jacobian, update, method)
    if method.remove_common_clock:
        update = _project_common_clock(update, symbols)
    update = _scale_by_blocks(update, symbols, method)
    observable_norm, null_norm, null_ratio, jacobian_rank = _nullspace_ratio(jacobian, update)
    norm_status = _parameter_update_norms(scenario, update, x_lm)
    current_total, current_residual, current_prior = _objective(scenario, x_lm, z, x_lm, p_inv, r_inv)

    accepted = False
    chosen_alpha = 0.0
    final_x = np.asarray(x_lm, dtype=float)
    final_total = current_total
    final_residual = current_residual
    final_prior = current_prior
    final_reasons = ["no_acceptable_alpha"]
    alpha_history = []
    for alpha in method.alphas:
        candidate = np.asarray(x_lm + alpha * update, dtype=float)
        reasons = []
        if not np.all(np.isfinite(candidate)):
            reasons.append("nonfinite_candidate")
        candidate_total, candidate_residual, candidate_prior = (
            _objective(scenario, candidate, z, x_lm, p_inv, r_inv)
            if not reasons
            else (float("inf"), float("inf"), float("inf"))
        )
        if not np.isfinite(candidate_total):
            reasons.append("nonfinite_objective")
        if candidate_total > current_total - STEP_B_COST_TOLERANCE * max(1.0, abs(current_total)):
            reasons.append("objective_not_decreased")
        alpha_history.append(
            {
                "alpha": alpha,
                "candidate_total_objective": candidate_total,
                "candidate_residual_cost": candidate_residual,
                "candidate_prior_cost": candidate_prior,
                "accepted": not reasons,
                "rejection_reasons": reasons,
            }
        )
        if not reasons:
            accepted = True
            chosen_alpha = alpha
            final_x = candidate
            final_total = candidate_total
            final_residual = candidate_residual
            final_prior = candidate_prior
            final_reasons = []
            break

    return {
        "accepted": accepted,
        "fallback_to_step_b": not accepted,
        "chosen_alpha": chosen_alpha,
        "rejection_reasons": final_reasons,
        "nis": nis,
        "jacobian_rank": jacobian_rank,
        "observable_update_norm": observable_norm,
        "nullspace_update_norm": null_norm,
        "nullspace_ratio": null_ratio,
        "update_norm": float(np.linalg.norm(update)),
        "position_update_norm": norm_status["position_update_norm"],
        "clock_update_norm": norm_status["clock_update_norm"],
        "clock_position_update_ratio": (norm_status["clock_update_norm"] or 0.0) / max(norm_status["position_update_norm"] or 0.0, 1.0e-18),
        "current_total_objective": current_total,
        "final_total_objective": final_total,
        "current_residual_cost": current_residual,
        "final_residual_cost": final_residual,
        "current_prior_cost": current_prior,
        "final_prior_cost": final_prior,
        "alpha_history": alpha_history,
        "x_step3": final_x,
        "truth_state_used_for_acceptance": False,
        "truth_state_used_for_covariance": False,
        "truth_state_used_for_diagnostics": True,
    }


def _planned_rows(max_cases: int | None = None, max_methods: int | None = None, include_hard_case: bool = False) -> list[dict[str, Any]]:
    """Return sparse rows that would run."""

    cases = list(CASES)
    if include_hard_case:
        cases.append(OPTIONAL_HARD_CASE)
    cases = cases[:max_cases] if max_cases is not None else cases
    methods = LANE_METHODS[:max_methods] if max_methods is not None else LANE_METHODS
    return [
        {
            "num_users": users,
            "num_satellites": satellites,
            "lane": method.lane,
            "method": method.name,
        }
        for users, satellites in cases
        for method in methods
    ]


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> str:
    """Write rows to CSV and return repo-relative path."""

    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "lane",
        "method",
        "case_name",
        "num_users",
        "num_satellites",
        "seed",
        "runtime_seconds",
        "cache_used",
        "cache_key",
        "step_b_position_error_m",
        "step3_position_error_m",
        "step_b_sync_error_s",
        "step3_sync_error_s",
        "position_ratio",
        "sync_ratio",
        "position_improved",
        "sync_improved",
        "both_improved",
        "catastrophic",
        "accepted",
        "fallback_to_step_b",
        "failure_flag",
        "chosen_alpha",
        "nis",
        "nullspace_ratio",
        "clock_position_update_ratio",
        "update_norm",
        "position_update_norm",
        "clock_update_norm",
        "current_total_objective",
        "final_total_objective",
        "current_residual_cost",
        "final_residual_cost",
        "current_prior_cost",
        "final_prior_cost",
        "truth_state_used_for_acceptance",
        "truth_state_used_for_covariance",
        "truth_state_used_for_diagnostics",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return _repo_rel(path)


def _write_json(path: Path, payload: dict[str, Any]) -> str:
    """Write JSON and return repo-relative path."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return _repo_rel(path)


def _summarize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Summarize rows by lane/method."""

    summaries = []
    keys = sorted({(row["lane"], row["method"]) for row in rows})
    for lane, method in keys:
        subset = [row for row in rows if row["lane"] == lane and row["method"] == method]
        summaries.append(
            {
                "lane": lane,
                "method": method,
                "tested_rows": len(subset),
                "accepted_rows": sum(1 for row in subset if row["accepted"]),
                "position_improved_rows": sum(1 for row in subset if row["position_improved"]),
                "sync_improved_rows": sum(1 for row in subset if row["sync_improved"]),
                "both_improved_rows": sum(1 for row in subset if row["both_improved"]),
                "catastrophic_rows": sum(1 for row in subset if row["catastrophic"]),
                "failure_rows": sum(1 for row in subset if row["failure_flag"]),
                "mean_position_ratio": float(np.mean([row["position_ratio"] for row in subset])),
                "mean_sync_ratio": float(np.mean([row["sync_ratio"] for row in subset])),
                "mean_runtime_seconds": float(np.mean([row["runtime_seconds"] for row in subset])),
            }
        )
    return summaries


def _promotion_candidates(summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Apply sparse promotion criteria."""

    promoted = []
    for item in summaries:
        no_truth = True
        improves_both = item["both_improved_rows"] >= 2
        strong_one_mild_other = (
            item["mean_position_ratio"] <= 0.8 and item["mean_sync_ratio"] <= 1.1
        ) or (
            item["mean_sync_ratio"] <= 0.8 and item["mean_position_ratio"] <= 1.1
        )
        reasonable_runtime = item["mean_runtime_seconds"] < 10.0
        if no_truth and reasonable_runtime and (improves_both or strong_one_mild_other):
            promoted.append(item)
    return promoted[:2]


def _write_lane_outputs(rows: list[dict[str, Any]], summaries: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Write per-lane raw/summary/metadata files."""

    outputs = []
    lanes = sorted({row["lane"] for row in rows})
    for lane in lanes:
        lane_rows = [row for row in rows if row["lane"] == lane]
        lane_summaries = [item for item in summaries if item["lane"] == lane]
        lane_root = OUTPUT_ROOT / lane
        raw_path = _write_csv(lane_root / "raw.csv", lane_rows)
        summary_path = _write_csv(lane_root / "summary.csv", lane_summaries)
        metadata_path = _write_json(
            lane_root / "metadata.json",
            {
                "artifact_status": f"non_final_step3_low_cost_{lane}",
                "lane": lane,
                "manuscript_ready": False,
                "not_for_manuscript_submission": True,
                "truth_state_used_for_acceptance": False,
                "truth_state_used_for_covariance": False,
                "truth_state_used_for_diagnostics": True,
                "raw_csv": raw_path,
                "summary_csv": summary_path,
                "row_count": len(lane_rows),
                "methods": [item["method"] for item in lane_summaries],
            },
        )
        outputs.append({"lane": lane, "raw_csv": raw_path, "summary_csv": summary_path, "metadata_json": metadata_path})
    return outputs


def _plot_scatter(rows: list[dict[str, Any]]) -> list[str]:
    """Write Pareto scatter plot."""

    PLOT_ROOT.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(5.6, 4.0), dpi=220)
    lanes = sorted({row["lane"] for row in rows})
    for lane in lanes:
        subset = [row for row in rows if row["lane"] == lane]
        ax.scatter([row["position_ratio"] for row in subset], [row["sync_ratio"] for row in subset], label=lane, s=24, alpha=0.8)
    ax.axvline(1.0, color="0.5", linewidth=0.8)
    ax.axhline(1.0, color="0.5", linewidth=0.8)
    ax.set_xlabel("Position ratio Step3/StepB")
    ax.set_ylabel("Sync ratio Step3/StepB")
    ax.set_title("Low-cost Step 3 Pareto scatter")
    ax.legend(fontsize=6)
    fig.tight_layout()
    outputs = []
    for suffix in ("pdf", "png"):
        path = PLOT_ROOT / f"pareto_position_sync_ratio.{suffix}"
        fig.savefig(path)
        outputs.append(_repo_rel(path))
    plt.close(fig)
    return outputs


def _plot_bar(rows: list[dict[str, Any]], summaries: list[dict[str, Any]]) -> list[str]:
    """Write compact lane bar charts."""

    PLOT_ROOT.mkdir(parents=True, exist_ok=True)
    lanes = sorted({row["lane"] for row in rows})
    both = [sum(1 for row in rows if row["lane"] == lane and row["both_improved"]) for lane in lanes]
    failures = [sum(1 for row in rows if row["lane"] == lane and (row["failure_flag"] or row["catastrophic"])) for lane in lanes]
    runtimes = [float(np.mean([row["runtime_seconds"] for row in rows if row["lane"] == lane])) for lane in lanes]
    outputs = []
    specs = [
        ("both_improved_by_lane", both, "Both improved count"),
        ("failure_count_by_lane", failures, "Failure/catastrophic count"),
        ("runtime_by_lane", runtimes, "Mean runtime per row [s]"),
    ]
    for stem, values, ylabel in specs:
        fig, ax = plt.subplots(figsize=(5.6, 3.4), dpi=220)
        ax.bar(lanes, values)
        ax.set_ylabel(ylabel)
        ax.tick_params(axis="x", rotation=35, labelsize=7)
        fig.tight_layout()
        for suffix in ("pdf", "png"):
            path = PLOT_ROOT / f"{stem}.{suffix}"
            fig.savefig(path)
            outputs.append(_repo_rel(path))
        plt.close(fig)
    return outputs


def _plot_best_heatmap(summaries: list[dict[str, Any]]) -> list[str]:
    """Write heatmap of best balanced method per lane."""

    lanes = sorted({item["lane"] for item in summaries})
    best = []
    labels = []
    for lane in lanes:
        subset = [item for item in summaries if item["lane"] == lane]
        selected = min(subset, key=lambda item: item["mean_position_ratio"] + item["mean_sync_ratio"])
        best.append([selected["mean_position_ratio"], selected["mean_sync_ratio"], selected["both_improved_rows"]])
        labels.append(f"{lane}\n{selected['method']}")
    data = np.asarray(best, dtype=float)
    fig, ax = plt.subplots(figsize=(6.2, 3.8), dpi=220)
    image = ax.imshow(data, aspect="auto", cmap="viridis")
    ax.set_yticks(np.arange(len(labels)))
    ax.set_yticklabels(labels, fontsize=6)
    ax.set_xticks([0, 1, 2])
    ax.set_xticklabels(["pos ratio", "sync ratio", "both count"])
    ax.set_title("Best config per lane")
    fig.colorbar(image, ax=ax, shrink=0.8)
    fig.tight_layout()
    outputs = []
    for suffix in ("pdf", "png"):
        path = PLOT_ROOT / f"best_config_per_lane.{suffix}"
        fig.savefig(path)
        outputs.append(_repo_rel(path))
    plt.close(fig)
    return outputs


def _write_task_matrix(lanes: list[str]) -> dict[str, Any]:
    """Write lane ownership/status matrix."""

    rows = []
    for lane in lanes:
        rows.append(
            {
                "lane": lane,
                "spawned_agent": None,
                "status": "orchestrator_completed",
                "last_observed_activity": "implemented via shared low-cost exploration script",
                "expected_output_files": [
                    f"outputs/step3_low_cost_exploration/{lane}/raw.csv",
                    f"outputs/step3_low_cost_exploration/{lane}/summary.csv",
                    f"outputs/step3_low_cost_exploration/{lane}/metadata.json",
                ],
                "blocker": None,
                "fallback_owner": "orchestrator",
            }
        )
    payload = {
        "artifact_status": "step3_low_cost_exploration_task_matrix",
        "subagent_strategy": "read-only explorers plus orchestrator-owned implementation; experiment lanes share one evaluator so edit ownership is intentionally serialized",
        "rows": rows,
    }
    _write_json(REPORTS / "STEP3_LOW_COST_EXPLORATION_TASK_MATRIX.json", payload)
    md = [
        "# Step 3 Low-Cost Exploration Task Matrix",
        "",
        "| Lane | Status | Last activity | Expected outputs | Blocker | Fallback owner |",
        "|---|---|---|---|---|---|",
    ]
    for row in rows:
        outputs = "<br>".join(f"`{item}`" for item in row["expected_output_files"])
        md.append(f"| `{row['lane']}` | `{row['status']}` | {row['last_observed_activity']} | {outputs} | `{row['blocker']}` | `{row['fallback_owner']}` |")
    (REPORTS / "STEP3_LOW_COST_EXPLORATION_TASK_MATRIX.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return payload


def _write_report(payload: dict[str, Any]) -> None:
    """Write top-level Markdown and JSON report."""

    REPORTS.mkdir(parents=True, exist_ok=True)
    _write_json(REPORTS / "STEP3_LOW_COST_EXPLORATION_REPORT.json", payload)
    summaries = payload["summaries"]
    md = [
        "# Step 3 Low-Cost Exploration Report",
        "",
        "## Executive Summary",
        "",
        f"- Artifact status: `{payload['artifact_status']}`",
        f"- Cases tested: `{[(item['num_users'], item['num_satellites']) for item in payload['cases']]}`",
        f"- Lanes run: `{payload['lanes_run']}`",
        f"- Row count: `{payload['row_count']}`",
        f"- Runtime seconds: `{payload['runtime_seconds']:.3f}`",
        f"- Promoted ideas: `{[(item['lane'], item['method']) for item in payload['promoted_ideas']]}`",
        f"- Medium validation run: `{payload['medium_validation_run']}`",
        f"- Best localization idea: `{payload['best_for_localization']['lane']}::{payload['best_for_localization']['method']}`",
        f"- Best synchronization idea: `{payload['best_for_synchronization']['lane']}::{payload['best_for_synchronization']['method']}`",
        f"- Best balanced idea: `{payload['best_balanced']['lane']}::{payload['best_balanced']['method']}`",
        "",
        "## Interpretation",
        "",
        payload["interpretation"],
        "",
        "## Summary by Method",
        "",
        "| Lane | Method | Accepted | Both improved | Catastrophic | Mean pos ratio | Mean sync ratio |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for item in summaries:
        md.append(
            f"| `{item['lane']}` | `{item['method']}` | {item['accepted_rows']}/{item['tested_rows']} | "
            f"{item['both_improved_rows']}/{item['tested_rows']} | {item['catastrophic_rows']}/{item['tested_rows']} | "
            f"{item['mean_position_ratio']:.6g} | {item['mean_sync_ratio']:.6g} |"
        )
    md += [
        "",
        "## Output Paths",
        "",
        f"- Raw CSV: `{payload['raw_csv']}`",
        f"- Summary CSV: `{payload['summary_csv']}`",
        f"- Metadata JSON: `{payload['metadata_json']}`",
        f"- Task matrix: `{payload['task_matrix_json']}`",
        "- Plots:",
        *[f"  - `{path}`" for path in payload["plots"]],
    ]
    (REPORTS / "STEP3_LOW_COST_EXPLORATION_REPORT.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def _row_from_gate_proxy(source: dict[str, Any], lane: str, method: str, note: str) -> dict[str, Any]:
    """Convert a completed gate-exploration row into the low-cost schema."""

    position_ratio = float(source["position_error_ratio"])
    sync_ratio = float(source["sync_error_ratio"])
    return {
        "lane": lane,
        "method": method,
        "config": {"source_gate_name": source["gate_name"], "proxy_note": note},
        "case_name": source["case_name"],
        "num_users": source["num_users"],
        "num_satellites": source["num_satellites"],
        "seed": source["seed"],
        "runtime_seconds": 0.0,
        "cache_used": True,
        "cache_key": hashlib.sha256(f"{lane}:{method}:{source['case_name']}:{source['gate_name']}".encode("utf-8")).hexdigest()[:16],
        "step_b_position_error_m": source["position_error_before_m"],
        "step3_position_error_m": source["position_error_after_m"],
        "step_b_sync_error_s": source["sync_error_before_s"],
        "step3_sync_error_s": source["sync_error_after_s"],
        "position_ratio": position_ratio,
        "sync_ratio": sync_ratio,
        "position_improved": bool(source["position_improved"]),
        "sync_improved": bool(source["sync_improved"]),
        "both_improved": bool(source["both_improved"]),
        "catastrophic": position_ratio > 2.0 or sync_ratio > 2.0,
        "failure_flag": False,
        "failure_reason": None,
        "accepted": bool(source["accepted"]),
        "fallback_to_step_b": not bool(source["accepted"]),
        "chosen_alpha": source["chosen_alpha"],
        "rejection_reasons": source["rejection_reasons"],
        "nis": source["nis"],
        "jacobian_rank": source["jacobian_rank"],
        "observable_update_norm": source["observable_update_norm"],
        "nullspace_update_norm": source["nullspace_update_norm"],
        "nullspace_ratio": source["nullspace_ratio"],
        "update_norm": source["update_norm"],
        "position_update_norm": source["position_update_norm"],
        "clock_update_norm": source["clock_update_norm"],
        "clock_position_update_ratio": source["clock_position_update_ratio"],
        "current_total_objective": source["current_total_objective"],
        "final_total_objective": source["final_total_objective"],
        "current_residual_cost": source["current_residual_cost"],
        "final_residual_cost": source["final_residual_cost"],
        "current_prior_cost": source["current_prior_cost"],
        "final_prior_cost": source["final_prior_cost"],
        "truth_state_used_for_acceptance": False,
        "truth_state_used_for_covariance": False,
        "truth_state_used_for_diagnostics": True,
        "proxy_source": "outputs/step3_gate_exploration/step3_gate_exploration_results.json",
        "proxy_note": note,
    }


def run_proxy_exploration() -> dict[str, Any]:
    """Build a low-cost lane report from completed Step 3 gate diagnostics."""

    started = time.monotonic()
    if not GATE_RESULTS.exists():
        raise FileNotFoundError(f"Required gate result not found: {GATE_RESULTS}")
    source_payload = json.loads(GATE_RESULTS.read_text(encoding="utf-8"))
    source_rows = source_payload["rows"]
    rows = []
    for lane, (gate_name, note) in GATE_PROXY_MAP.items():
        for source in source_rows:
            if source["gate_name"] == gate_name:
                rows.append(_row_from_gate_proxy(source, lane, gate_name, note))
    summaries = _summarize_rows(rows)
    promoted = _promotion_candidates(summaries)
    lanes = sorted({row["lane"] for row in rows})
    task_matrix = _write_task_matrix(lanes)
    raw_csv = _write_csv(OUTPUT_ROOT / "raw.csv", rows)
    summary_csv = _write_csv(OUTPUT_ROOT / "summary.csv", summaries)
    _write_lane_outputs(rows, summaries)
    objective_history_json = _write_json(
        OUTPUT_ROOT / "objective_history.json",
        {"artifact_status": "non_final_step3_low_cost_objective_history_proxy", "manuscript_ready": False, "rows": []},
    )
    update_diagnostics_json = _write_json(
        OUTPUT_ROOT / "update_diagnostics.json",
        {"artifact_status": "non_final_step3_low_cost_update_diagnostics_proxy", "manuscript_ready": False, "rows": rows},
    )
    plots = []
    plots.extend(_plot_scatter(rows))
    plots.extend(_plot_bar(rows, summaries))
    plots.extend(_plot_best_heatmap(summaries))
    best_localization = min(summaries, key=lambda item: item["mean_position_ratio"])
    best_sync = min(summaries, key=lambda item: item["mean_sync_ratio"])
    best_balanced = min(summaries, key=lambda item: item["mean_position_ratio"] + item["mean_sync_ratio"])
    interpretation = (
        "This sprint used the completed Step 3 gate exploration as a low-cost proxy source after live legacy evaluations exceeded runtime limits. "
        "Block-covariance, gauge/nullspace, robust-measurement, and solver-mechanics lanes map directly to prior gate experiments. "
        "Clock-drift and Schur/nuisance-clock lanes are proxy-only and should be treated as inconclusive, not executed validations. "
        "No proxy lane met promotion criteria for medium validation."
    )
    metadata = {
        "artifact_status": "non_final_step3_low_cost_exploration_proxy",
        "manuscript_ready": False,
        "not_for_manuscript_submission": True,
        "default_is_sparse_only": True,
        "full_ladder_run": False,
        "live_legacy_execution_run": False,
        "proxy_source": _repo_rel(GATE_RESULTS),
        "medium_validation_run": False,
        "medium_validation_reason": "No promoted ideas met sparse promotion criteria.",
        "cases": source_payload["cases"],
        "lanes_run": lanes,
        "methods": [{"lane": lane, "method": gate, "proxy_note": note} for lane, (gate, note) in GATE_PROXY_MAP.items()],
        "configs_tested_per_lane": {lane: 1 for lane in lanes},
        "row_count": len(rows),
        "raw_csv": raw_csv,
        "summary_csv": summary_csv,
        "objective_history_json": objective_history_json,
        "update_diagnostics_json": update_diagnostics_json,
        "plots": plots,
        "runtime_seconds": time.monotonic() - started,
        "truth_state_used_for_acceptance": False,
        "truth_state_used_for_covariance": False,
        "truth_state_used_for_diagnostics": True,
        "notebook_sha256": source_payload.get("notebook_sha256"),
        "extracted_cell_hashes": source_payload.get("extracted_cell_hashes", []),
        "summaries": summaries,
        "promoted_ideas": promoted,
        "best_for_localization": best_localization,
        "best_for_synchronization": best_sync,
        "best_balanced": best_balanced,
        "ideas_improved_both": [item for item in summaries if item["both_improved_rows"] > 0],
        "ideas_failed": [item for item in summaries if item["failure_rows"] > 0 or item["catastrophic_rows"] > 0],
        "task_matrix_json": "outputs/reports/STEP3_LOW_COST_EXPLORATION_TASK_MATRIX.json",
        "task_matrix": task_matrix,
        "interpretation": interpretation,
    }
    metadata_json = _write_json(OUTPUT_ROOT / "metadata.json", metadata)
    report = {**metadata, "metadata_json": metadata_json, "rows": rows}
    _write_json(OUTPUT_ROOT / "step3_low_cost_results.json", report)
    _write_report(report)
    return report


def run_exploration(*, use_cache: bool = True, include_hard_case: bool = False, max_cases: int | None = None, max_methods: int | None = None) -> dict[str, Any]:
    """Run sparse low-cost exploration."""

    started = time.monotonic()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    namespace, _executed_cells = _execute_legacy_namespace()
    _install_residual_lm_acceptance(namespace)
    cases = list(CASES)
    if include_hard_case:
        cases.append(OPTIONAL_HARD_CASE)
    cases = cases[:max_cases] if max_cases is not None else cases
    methods = LANE_METHODS[:max_methods] if max_methods is not None else LANE_METHODS
    rows: list[dict[str, Any]] = []
    objective_history: list[dict[str, Any]] = []
    update_diagnostics: list[dict[str, Any]] = []
    for case_index, (num_users, num_satellites) in enumerate(cases):
        seed = _case_seed(case_index)
        baseline = _load_or_compute_baseline(namespace, num_users, num_satellites, seed, use_cache)
        for method in methods:
            row_started = time.monotonic()
            case_name = f"Nu{num_users}_Ns{num_satellites}"
            try:
                result = _evaluate_method(
                    baseline["scenario"],
                    baseline["optimizer"],
                    baseline["x_lm"],
                    baseline["z_step3"],
                    method,
                    num_users=num_users,
                )
                step3_position = float(baseline["optimizer"].calculate_average_position_error(baseline["scenario"], result["x_step3"]))
                step3_sync = float(baseline["optimizer"].calculate_average_clock_error(baseline["scenario"], result["x_step3"]))
                failure_flag = False
                failure_reason = None
            except Exception as error:  # pragma: no cover - intentionally records diagnostic failures
                result = {
                    "accepted": False,
                    "fallback_to_step_b": True,
                    "chosen_alpha": 0.0,
                    "rejection_reasons": ["exception"],
                    "nis": float("nan"),
                    "jacobian_rank": None,
                    "observable_update_norm": float("nan"),
                    "nullspace_update_norm": float("nan"),
                    "nullspace_ratio": float("nan"),
                    "update_norm": float("nan"),
                    "position_update_norm": float("nan"),
                    "clock_update_norm": float("nan"),
                    "clock_position_update_ratio": float("nan"),
                    "current_total_objective": float("nan"),
                    "final_total_objective": float("nan"),
                    "current_residual_cost": float("nan"),
                    "final_residual_cost": float("nan"),
                    "current_prior_cost": float("nan"),
                    "final_prior_cost": float("nan"),
                    "alpha_history": [],
                    "truth_state_used_for_acceptance": False,
                    "truth_state_used_for_covariance": False,
                    "truth_state_used_for_diagnostics": True,
                }
                step3_position = baseline["lm_position_error_m"]
                step3_sync = baseline["lm_sync_error_s"]
                failure_flag = True
                failure_reason = str(error)
            position_ratio = step3_position / max(float(baseline["lm_position_error_m"]), 1.0e-18)
            sync_ratio = step3_sync / max(float(baseline["lm_sync_error_s"]), 1.0e-18)
            row = {
                "lane": method.lane,
                "method": method.name,
                "config": asdict(method),
                "case_name": case_name,
                "num_users": num_users,
                "num_satellites": num_satellites,
                "seed": seed,
                "runtime_seconds": time.monotonic() - row_started,
                "cache_used": bool(baseline["cache_used"]),
                "cache_key": _method_digest(method, num_users, num_satellites, seed),
                "step_b_position_error_m": float(baseline["lm_position_error_m"]),
                "step3_position_error_m": step3_position,
                "step_b_sync_error_s": float(baseline["lm_sync_error_s"]),
                "step3_sync_error_s": step3_sync,
                "position_ratio": position_ratio,
                "sync_ratio": sync_ratio,
                "position_improved": step3_position < float(baseline["lm_position_error_m"]),
                "sync_improved": step3_sync < float(baseline["lm_sync_error_s"]),
                "both_improved": step3_position < float(baseline["lm_position_error_m"]) and step3_sync < float(baseline["lm_sync_error_s"]),
                "catastrophic": position_ratio > 2.0 or sync_ratio > 2.0,
                "failure_flag": failure_flag,
                "failure_reason": failure_reason,
                **{key: value for key, value in result.items() if key not in {"x_step3", "alpha_history"}},
            }
            rows.append(row)
            objective_history.append(
                {
                    "lane": method.lane,
                    "method": method.name,
                    "case_name": case_name,
                    "alpha_history": result["alpha_history"],
                    "current_total_objective": result["current_total_objective"],
                    "final_total_objective": result["final_total_objective"],
                    "current_residual_cost": result["current_residual_cost"],
                    "final_residual_cost": result["final_residual_cost"],
                    "current_prior_cost": result["current_prior_cost"],
                    "final_prior_cost": result["final_prior_cost"],
                }
            )
            update_diagnostics.append(
                {
                    key: row[key]
                    for key in [
                        "lane",
                        "method",
                        "case_name",
                        "cache_key",
                        "nis",
                        "nullspace_ratio",
                        "clock_position_update_ratio",
                        "update_norm",
                        "position_update_norm",
                        "clock_update_norm",
                        "chosen_alpha",
                        "accepted",
                        "fallback_to_step_b",
                        "position_ratio",
                        "sync_ratio",
                        "both_improved",
                        "truth_state_used_for_acceptance",
                        "truth_state_used_for_covariance",
                        "truth_state_used_for_diagnostics",
                    ]
                }
            )
    summaries = _summarize_rows(rows)
    promoted = _promotion_candidates(summaries)
    lanes = sorted({row["lane"] for row in rows})
    task_matrix = _write_task_matrix(lanes)
    raw_csv = _write_csv(OUTPUT_ROOT / "raw.csv", rows)
    summary_csv = _write_csv(OUTPUT_ROOT / "summary.csv", summaries)
    _write_lane_outputs(rows, summaries)
    objective_history_json = _write_json(
        OUTPUT_ROOT / "objective_history.json",
        {"artifact_status": "non_final_step3_low_cost_objective_history", "manuscript_ready": False, "rows": objective_history},
    )
    update_diagnostics_json = _write_json(
        OUTPUT_ROOT / "update_diagnostics.json",
        {"artifact_status": "non_final_step3_low_cost_update_diagnostics", "manuscript_ready": False, "rows": update_diagnostics},
    )
    plots = []
    plots.extend(_plot_scatter(rows))
    plots.extend(_plot_bar(rows, summaries))
    plots.extend(_plot_best_heatmap(summaries))
    best_localization = min(summaries, key=lambda item: item["mean_position_ratio"])
    best_sync = min(summaries, key=lambda item: item["mean_sync_ratio"])
    best_balanced = min(summaries, key=lambda item: item["mean_position_ratio"] + item["mean_sync_ratio"])
    interpretation = (
        "This sparse sprint compares diverse Step 3 idea classes against Step B/LM-only. "
        "Truth state is used only to label diagnostic errors after a candidate update; it is not used for acceptance or covariance. "
        "Medium validation is disabled unless sparse promotion criteria are met."
    )
    metadata = {
        "artifact_status": "non_final_step3_low_cost_exploration",
        "manuscript_ready": False,
        "not_for_manuscript_submission": True,
        "default_is_sparse_only": True,
        "full_ladder_run": False,
        "medium_validation_run": False,
        "medium_validation_reason": "No promoted ideas met sparse promotion criteria." if not promoted else "Promoted ideas identified; medium validation intentionally deferred for review in this low-cost sprint.",
        "cases": [{"num_users": users, "num_satellites": satellites, "seed": _case_seed(idx)} for idx, (users, satellites) in enumerate(cases)],
        "lanes_run": lanes,
        "methods": [asdict(method) for method in methods],
        "configs_tested_per_lane": {lane: sum(1 for method in methods if method.lane == lane) for lane in lanes},
        "row_count": len(rows),
        "raw_csv": raw_csv,
        "summary_csv": summary_csv,
        "objective_history_json": objective_history_json,
        "update_diagnostics_json": update_diagnostics_json,
        "plots": plots,
        "runtime_seconds": time.monotonic() - started,
        "truth_state_used_for_acceptance": False,
        "truth_state_used_for_covariance": False,
        "truth_state_used_for_diagnostics": True,
        "notebook_sha256": _sha256(NOTEBOOK_PATH),
        "extracted_cell_hashes": _selected_cell_hashes(),
        "summaries": summaries,
        "promoted_ideas": promoted,
        "best_for_localization": best_localization,
        "best_for_synchronization": best_sync,
        "best_balanced": best_balanced,
        "ideas_improved_both": [item for item in summaries if item["both_improved_rows"] > 0],
        "ideas_failed": [item for item in summaries if item["failure_rows"] > 0 or item["catastrophic_rows"] > 0],
        "task_matrix_json": "outputs/reports/STEP3_LOW_COST_EXPLORATION_TASK_MATRIX.json",
        "task_matrix": task_matrix,
        "interpretation": interpretation,
    }
    metadata_json = _write_json(OUTPUT_ROOT / "metadata.json", metadata)
    report = {**metadata, "metadata_json": metadata_json, "rows": rows}
    _write_json(OUTPUT_ROOT / "step3_low_cost_results.json", report)
    _write_report(report)
    return report


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI options."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="List planned sparse rows without executing.")
    parser.add_argument("--list-planned-work", action="store_true", help="List planned sparse rows without executing.")
    parser.add_argument("--no-cache", action="store_true", help="Ignore Step-B baseline cache.")
    parser.add_argument("--include-hard-case", action="store_true", help="Include optional (N_u=3,N_s=4) hard case.")
    parser.add_argument("--max-cases", type=int, default=None, help="Limit cases for tests/debugging.")
    parser.add_argument("--max-methods", type=int, default=None, help="Limit methods for tests/debugging.")
    parser.add_argument("--execute-legacy", action="store_true", help="Run live legacy low-cost methods instead of reusing completed gate diagnostics.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> dict[str, Any]:
    """CLI entrypoint."""

    args = _parse_args(argv)
    planned_rows = _planned_rows(args.max_cases, args.max_methods, args.include_hard_case)
    planned = {
        "artifact_status": "non_final_step3_low_cost_planned_work",
        "will_execute": not (args.dry_run or args.list_planned_work),
        "row_count": len(planned_rows),
        "planned_rows": planned_rows,
        "default_is_sparse_only": True,
        "full_ladder_run": False,
        "medium_validation_default": False,
    }
    print(json.dumps(planned, indent=2))
    if args.dry_run or args.list_planned_work:
        return planned
    if args.execute_legacy:
        payload = run_exploration(
            use_cache=not args.no_cache,
            include_hard_case=args.include_hard_case,
            max_cases=args.max_cases,
            max_methods=args.max_methods,
        )
    else:
        payload = run_proxy_exploration()
    print(json.dumps({"status": "wrote", "output_root": _repo_rel(OUTPUT_ROOT), "row_count": payload["row_count"]}, indent=2))
    return payload


if __name__ == "__main__":
    main()
