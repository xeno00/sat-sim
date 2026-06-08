"""Audit residual-scaled Step 3 covariance failures and robust candidates.

This diagnostic is intentionally narrow. It uses the existing residual-scaled
covariance medium-validation rows, then tests a small C7 candidate family on the
medium grid only. Outputs are non-final and not manuscript figures.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import time
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


SAT_SIM_ROOT = Path(__file__).resolve().parents[1]
if str(SAT_SIM_ROOT) not in sys.path:
    sys.path.insert(0, str(SAT_SIM_ROOT))

from scripts import explore_step3_covariance as cov  # noqa: E402


FAILURE_AUDIT_ROOT = SAT_SIM_ROOT / "outputs" / "step3_residual_cov_failure_audit"
ROBUST_ROOT = SAT_SIM_ROOT / "outputs" / "step3_residual_cov_robust_candidates"
REPORT_ROOT = SAT_SIM_ROOT / "outputs" / "reports"
PLOT_ROOT = ROBUST_ROOT / "plots"
TARGET_VARIANTS = ("block_diag_residual_scaled_covariance", "full_residual_scaled_covariance")


@dataclass(frozen=True)
class RobustCandidate:
    """One bounded C7 residual-scaled covariance candidate."""

    name: str
    description: str
    position_update_scale: float = 1.0
    sync_safeguard: bool = False
    clock_only_fallback: bool = False


CANDIDATES = [
    RobustCandidate(
        name="residual_scaled_block_diag_base",
        description="Current best block-diagonal residual-scaled covariance candidate.",
    ),
    RobustCandidate(
        name="residual_scaled_block_diag_with_sync_safeguard",
        description="Revert clock/drift update to Step B when non-truth diagnostics flag likely sync risk.",
        sync_safeguard=True,
    ),
    RobustCandidate(
        name="residual_scaled_block_diag_clock_only_fallback",
        description="If non-truth diagnostics fail, keep Step B positions and keep only safe clock/drift updates.",
        clock_only_fallback=True,
    ),
    RobustCandidate(
        name="residual_scaled_block_diag_position_damped",
        description="Residual-scaled covariance with damped position update.",
        position_update_scale=0.25,
    ),
]


def _repo_rel(path: Path) -> str:
    """Return a sat-sim-relative path."""

    return path.relative_to(SAT_SIM_ROOT).as_posix()


def _write_json(path: Path, payload: Any) -> str:
    """Write JSON and return a sat-sim-relative path."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return _repo_rel(path)


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> str:
    """Write CSV and return a sat-sim-relative path."""

    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return _repo_rel(path)
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return _repo_rel(path)


def _read_csv_rows(path: Path) -> list[dict[str, Any]]:
    """Read CSV rows with best-effort numeric conversion."""

    rows = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            converted: dict[str, Any] = {}
            for key, value in row.items():
                if value in {"True", "False"}:
                    converted[key] = value == "True"
                    continue
                try:
                    if value.strip() == "":
                        converted[key] = value
                    elif any(token in value.lower() for token in (".", "e", "inf", "nan")):
                        converted[key] = float(value)
                    else:
                        converted[key] = int(value)
                except (ValueError, AttributeError):
                    converted[key] = value
            rows.append(converted)
    return rows


def _target_medium_rows() -> list[dict[str, Any]]:
    """Load or regenerate the two target residual-scaled medium row sets."""

    rows: list[dict[str, Any]] = []
    for variant_name in TARGET_VARIANTS:
        path = (
            SAT_SIM_ROOT
            / "outputs"
            / "step3_covariance_exploration"
            / "medium_validation"
            / variant_name
            / "raw.csv"
        )
        if path.exists():
            rows.extend(_read_csv_rows(path))
            continue
        variant = next(item for item in cov.LANE_VARIANTS if item.name == variant_name)
        rows.extend(cov._evaluate_case_variant(case, variant, grid="medium") for case in cov.medium_cases())
    return rows


def _total_update_norm(row: dict[str, Any]) -> float:
    """Return combined update norm from recorded block norms."""

    return float(
        math.sqrt(
            float(row.get("position_update_norm", 0.0)) ** 2
            + float(row.get("ue_clock_update_norm", 0.0)) ** 2
            + float(row.get("satellite_clock_update_norm", 0.0)) ** 2
            + float(row.get("clock_drift_update_norm", 0.0)) ** 2
        )
    )


def _failure_audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Return target-row failure audit payload."""

    norms = np.asarray([_total_update_norm(row) for row in rows], dtype=float)
    unusual_threshold = float(np.quantile(norms, 0.90)) if norms.size else 0.0
    failures = []
    for row in rows:
        position_ratio = float(row["position_ratio"])
        sync_ratio = float(row["sync_ratio"])
        total_update_norm = _total_update_norm(row)
        flags = {
            "sync_ratio_gt_1": sync_ratio > 1.0,
            "position_ratio_gt_1": position_ratio > 1.0,
            "sync_worse_gt_5_percent": sync_ratio > 1.05,
            "position_worse_gt_5_percent": position_ratio > 1.05,
            "objective_decreases_but_metric_worsens": bool(row.get("objective_decreased", False))
            and (sync_ratio > 1.0 or position_ratio > 1.0),
            "unusually_large_update_norm": total_update_norm >= unusual_threshold,
        }
        if any(flags.values()):
            failures.append(
                {
                    "variant": row["variant"],
                    "num_users": int(row["num_users"]),
                    "num_satellites": int(row["num_satellites"]),
                    "step_b_position_error_m": float(row["step_b_position_error_m"]),
                    "step3_position_error_m": float(row["step3_position_error_m"]),
                    "step_b_sync_error_km": float(row["step_b_sync_error_km"]),
                    "step3_sync_error_km": float(row["step3_sync_error_km"]),
                    "position_ratio": position_ratio,
                    "sync_ratio": sync_ratio,
                    "position_update_norm": float(row["position_update_norm"]),
                    "ue_clock_update_norm": float(row["ue_clock_update_norm"]),
                    "satellite_clock_update_norm": float(row["satellite_clock_update_norm"]),
                    "clock_drift_update_norm": float(row.get("clock_drift_update_norm", 0.0)),
                    "total_update_norm": total_update_norm,
                    "p_position_eig_min": float(row["p_position_eig_min"]),
                    "p_position_eig_max": float(row["p_position_eig_max"]),
                    "p_clock_eig_min": float(row["p_clock_eig_min"]),
                    "p_clock_eig_max": float(row["p_clock_eig_max"]),
                    "normal_condition": float(row["normal_condition"]),
                    "objective_before": float(row["objective_before"]),
                    "objective_after": float(row["objective_after"]),
                    "residual_cost_before": float(row["residual_cost_before"]),
                    "residual_cost_after": float(row["residual_cost_after"]),
                    "prior_cost": float(row["prior_cost"]),
                    "accepted_update_count": int(row["accepted_update_count"]),
                    "rejected_update_count": int(row["rejected_update_count"]),
                    "flags": flags,
                }
            )
    by_case: dict[str, set[str]] = {}
    for item in failures:
        key = f"Nu{item['num_users']}_Ns{item['num_satellites']}"
        by_case.setdefault(key, set()).add(item["variant"])
    same_failure_cases = sorted(
        case for case, variants in by_case.items() if set(TARGET_VARIANTS).issubset(variants)
    )
    return {
        "artifact_status": "non_final_step3_residual_cov_failure_audit",
        "manuscript_ready": False,
        "target_variants": list(TARGET_VARIANTS),
        "row_count": len(rows),
        "failure_count": len(failures),
        "unusual_update_norm_threshold": unusual_threshold,
        "failure_rows": failures,
        "same_failure_cases": same_failure_cases,
    }


def _compare_target_variants(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Compare block-diagonal and full residual-scaled covariance target rows."""

    by_key = {
        (row["variant"], int(row["num_users"]), int(row["num_satellites"])): row
        for row in rows
    }
    comparisons = []
    numeric_fields = [
        "position_ratio",
        "sync_ratio",
        "position_update_norm",
        "ue_clock_update_norm",
        "satellite_clock_update_norm",
        "clock_drift_update_norm",
        "p_position_trace",
        "p_clock_trace",
        "objective_after",
        "normal_condition",
    ]
    max_abs_difference = 0.0
    for case in cov.medium_cases():
        left = by_key[(TARGET_VARIANTS[0], case.num_users, case.num_satellites)]
        right = by_key[(TARGET_VARIANTS[1], case.num_users, case.num_satellites)]
        diffs = {
            field: abs(float(left[field]) - float(right[field]))
            for field in numeric_fields
        }
        max_abs_difference = max(max_abs_difference, max(diffs.values()))
        comparisons.append(
            {
                "num_users": case.num_users,
                "num_satellites": case.num_satellites,
                "max_abs_difference": max(diffs.values()),
                "field_differences": diffs,
                "block_diag_position_ratio": float(left["position_ratio"]),
                "full_position_ratio": float(right["position_ratio"]),
                "block_diag_sync_ratio": float(left["sync_ratio"]),
                "full_sync_ratio": float(right["sync_ratio"]),
            }
        )
    return {
        "artifact_status": "non_final_step3_residual_cov_block_vs_full_comparison",
        "row_count": len(comparisons),
        "max_abs_difference": max_abs_difference,
        "effectively_identical": max_abs_difference <= 1.0e-12,
        "full_cross_covariance_used": False,
        "full_cross_covariance_note": "The upstream covariance builder diagonal-clips both residual-scaled variants, so off-diagonal position-clock covariance is not used in either target row set.",
        "preferred_variant": "block_diag_residual_scaled_covariance",
        "preference_reason": "Effective row equality plus simpler/interpretable block-diagonal intent.",
        "row_comparisons": comparisons,
    }


def _robust_variant(candidate: RobustCandidate) -> cov.CovarianceVariant:
    """Return the base residual-scaled block-diagonal covariance variant."""

    base = next(item for item in cov.LANE_VARIANTS if item.name == "block_diag_residual_scaled_covariance")
    return replace(
        base,
        name=candidate.name,
        description=candidate.description,
        position_update_scale=candidate.position_update_scale,
    )


def _safe_nontruth_diagnostics(
    case: cov.SparseCase,
    variant: cov.CovarianceVariant,
    update: np.ndarray,
    covariance: np.ndarray,
    objective_before: float,
    objective_after: float,
    finite_output: bool,
) -> dict[str, Any]:
    """Return non-truth safeguard diagnostics for one candidate update."""

    clock = cov._clock_slice(case)
    drift = cov._drift_slice(case, variant)
    clock_update = update[clock]
    drift_update = update[drift] if drift.stop > drift.start else np.asarray([], dtype=float)
    p_clock_trace = float(np.trace(covariance[clock, clock]))
    clock_update_norm = float(np.linalg.norm(clock_update))
    drift_update_norm = float(np.linalg.norm(drift_update))
    common_clock_component = abs(float(np.mean(clock_update))) if clock_update.size else 0.0
    clock_update_to_cov_scale = clock_update_norm / max(math.sqrt(max(p_clock_trace, 1.0e-18)), 1.0e-18)
    common_ratio = common_clock_component / max(clock_update_norm / max(math.sqrt(clock_update.size), 1.0), 1.0e-18)
    reasons = []
    if not finite_output:
        reasons.append("nonfinite_update")
    if objective_after > objective_before + 1.0e-9:
        reasons.append("observable_objective_not_decreased")
    if case.num_users < 2 and clock_update_norm > 0.0:
        reasons.append("single_user_clock_update_not_observable")
    if clock_update_to_cov_scale > 3.0:
        reasons.append("clock_update_exceeds_covariance_scale")
    if common_ratio > 0.95 and common_clock_component > 0.0:
        reasons.append("large_common_clock_component")
    return {
        "nis": objective_before,
        "clock_update_to_cov_scale": clock_update_to_cov_scale,
        "common_clock_component": common_clock_component,
        "common_clock_ratio": common_ratio,
        "drift_update_norm_before_fallback": drift_update_norm,
        "safeguard_failed": bool(reasons),
        "safeguard_reasons": reasons,
    }


def _evaluate_candidate(case: cov.SparseCase, candidate: RobustCandidate) -> dict[str, Any]:
    """Evaluate one robust C7 candidate on one medium-grid case."""

    started = time.monotonic()
    variant = _robust_variant(candidate)
    theta0 = cov._pack_state(case, variant)
    z_true, z_pred, jacobian = cov._measurements_and_jacobian(case, variant, theta0)
    residual = z_true - z_pred
    sigma = np.full(z_true.size, variant.measurement_sigma_km)
    covariance, covariance_info = cov._covariance_from_mode(case, variant, jacobian, residual, sigma)
    p_inv = np.linalg.pinv(covariance, rcond=1.0e-10)
    r_inv_diag = 1.0 / np.square(sigma)
    normal = jacobian.T @ (jacobian * r_inv_diag[:, None]) + p_inv
    rhs = jacobian.T @ (r_inv_diag * residual)
    update, reduced = cov._candidate_update(case, variant, normal, rhs)
    raw_update = update.copy()
    update = cov._project_or_damp_common_clock(case, variant, update)
    update, clipping = cov._scale_and_clip_update(case, variant, update)
    theta_full = theta0 + update
    residual_full_after = z_true - cov._measurements_and_jacobian(case, variant, theta_full)[1]
    residual_cost_before = float(np.sum(np.square(residual / sigma)))
    residual_cost_after_full = float(np.sum(np.square(residual_full_after / sigma)))
    prior_cost_full = float(update.T @ p_inv @ update)
    objective_after_full = residual_cost_after_full + prior_cost_full
    finite_full = bool(np.all(np.isfinite(theta_full)) and np.isfinite(objective_after_full))
    diagnostics = _safe_nontruth_diagnostics(
        case,
        variant,
        update,
        covariance,
        residual_cost_before,
        objective_after_full,
        finite_full,
    )
    fallback_behavior = "none"
    if candidate.sync_safeguard and diagnostics["safeguard_failed"]:
        clock = cov._clock_slice(case)
        drift = cov._drift_slice(case, variant)
        update[clock] = 0.0
        if drift.stop > drift.start:
            update[drift] = 0.0
        fallback_behavior = "clock_and_drift_reverted_to_step_b"
    elif candidate.clock_only_fallback and diagnostics["safeguard_failed"]:
        clock_update_safe = "single_user_clock_update_not_observable" not in diagnostics["safeguard_reasons"]
        pos = cov._position_slice(case)
        if clock_update_safe:
            update[pos] = 0.0
            fallback_behavior = "positions_reverted_clock_update_kept"
        else:
            update[:] = 0.0
            fallback_behavior = "all_step3_update_reverted"

    theta1 = theta0 + update
    pos0, clock0, drift0 = cov._unpack_state(theta0, case, variant)
    pos1, clock1, drift1 = cov._unpack_state(theta1, case, variant)
    residual_after = z_true - cov._measurements_and_jacobian(case, variant, theta1)[1]
    residual_cost_after = float(np.sum(np.square(residual_after / sigma)))
    prior_cost = float(update.T @ p_inv @ update)
    objective_after = residual_cost_after + prior_cost
    pos_before = cov._position_error_m(case, pos0)
    pos_after = cov._position_error_m(case, pos1)
    sync_before = cov._sync_error_km(case, clock0, drift0)
    sync_after = cov._sync_error_km(case, clock1, drift1)
    position_ratio = pos_after / max(pos_before, cov.POSITION_RATIO_EPS_M)
    sync_ratio = sync_after / max(sync_before, cov.SYNC_RATIO_EPS_KM)
    pos_stats = cov._matrix_block_stats(covariance, cov._position_slice(case))
    clock_stats = cov._matrix_block_stats(covariance, cov._clock_slice(case))
    drift_stats = cov._matrix_block_stats(covariance, cov._drift_slice(case, variant))
    row = {
        "candidate": candidate.name,
        "variant_description": candidate.description,
        "num_users": case.num_users,
        "num_satellites": case.num_satellites,
        "grid": "medium",
        "runtime_seconds": time.monotonic() - started,
        "cache_status": "not_used_deterministic_medium",
        "step_b_position_error_m": pos_before,
        "step3_position_error_m": pos_after,
        "step_b_sync_error_km": sync_before,
        "step3_sync_error_km": sync_after,
        "position_ratio": position_ratio,
        "sync_ratio": sync_ratio,
        "both_improved": position_ratio < 1.0 and sync_ratio < 1.0,
        "position_improved": position_ratio < 1.0,
        "sync_improved": sync_ratio < 1.0,
        "position_worse_gt_5_percent": position_ratio > 1.05,
        "sync_worse_gt_5_percent": sync_ratio > 1.05,
        "position_update_norm": float(np.linalg.norm(update[cov._position_slice(case)])),
        "ue_clock_update_norm": float(np.linalg.norm(update[cov._clock_slice(case)][: case.num_users])),
        "satellite_clock_update_norm": float(np.linalg.norm(update[cov._clock_slice(case)][case.num_users :])),
        "clock_drift_update_norm": float(np.linalg.norm(update[cov._drift_slice(case, variant)])),
        "raw_position_update_norm": float(np.linalg.norm(raw_update[cov._position_slice(case)])),
        "raw_clock_update_norm": float(np.linalg.norm(raw_update[cov._clock_slice(case)])),
        "objective_before": residual_cost_before,
        "objective_after": objective_after,
        "objective_after_full_update": objective_after_full,
        "objective_decreased": objective_after <= residual_cost_before + 1.0e-9,
        "residual_cost_before": residual_cost_before,
        "residual_cost_after": residual_cost_after,
        "prior_cost": prior_cost,
        "accepted_update_count": int(objective_after <= residual_cost_before + 1.0e-9),
        "rejected_update_count": int(objective_after > residual_cost_before + 1.0e-9),
        "fallback_behavior": fallback_behavior,
        "fallback_used": fallback_behavior != "none",
        "safeguard_enabled": candidate.sync_safeguard or candidate.clock_only_fallback,
        "safeguard_used_truth_metrics": False,
        "truth_state_used_for_acceptance": False,
        "truth_state_used_for_covariance": False,
        "truth_state_used_for_diagnostics": True,
        "p_position_trace": pos_stats["trace"],
        "p_position_eig_min": pos_stats["eig_min"],
        "p_position_eig_max": pos_stats["eig_max"],
        "p_clock_trace": clock_stats["trace"],
        "p_clock_eig_min": clock_stats["eig_min"],
        "p_clock_eig_max": clock_stats["eig_max"],
        "p_drift_trace": drift_stats["trace"],
        "p_drift_eig_min": drift_stats["eig_min"],
        "p_drift_eig_max": drift_stats["eig_max"],
        "normal_rank": int(np.linalg.matrix_rank(normal)),
        "normal_condition": cov._condition_number(normal),
        "finite_output": bool(np.all(np.isfinite(theta1)) and np.isfinite(objective_after)),
        "manuscript_ready": False,
        "not_for_manuscript_submission": True,
        **diagnostics,
        **covariance_info,
        **cov._block_norms(case, variant, update, jacobian),
        **clipping,
        **reduced,
    }
    return row


def _summarize_candidates(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Summarize robust candidate validation rows."""

    output = []
    for candidate in [item.name for item in CANDIDATES]:
        subset = [row for row in rows if row["candidate"] == candidate]
        output.append(
            {
                "candidate": candidate,
                "tested_cases": len(subset),
                "both_improved_count": sum(bool(row["both_improved"]) for row in subset),
                "position_improved_count": sum(bool(row["position_improved"]) for row in subset),
                "sync_improved_count": sum(bool(row["sync_improved"]) for row in subset),
                "mean_position_ratio": float(np.mean([row["position_ratio"] for row in subset])),
                "max_position_ratio": float(np.max([row["position_ratio"] for row in subset])),
                "mean_sync_ratio": float(np.mean([row["sync_ratio"] for row in subset])),
                "max_sync_ratio": float(np.max([row["sync_ratio"] for row in subset])),
                "failure_row_count": sum(row["position_ratio"] > 1.05 or row["sync_ratio"] > 1.05 for row in subset),
                "fallback_count": sum(bool(row["fallback_used"]) for row in subset),
                "passes_strict_promotion_criterion": all(
                    row["position_ratio"] <= 1.05 and row["sync_ratio"] <= 1.05 for row in subset
                ),
            }
        )
    return output


def _best_candidate(summary: list[dict[str, Any]]) -> dict[str, Any]:
    """Return best robust candidate summary."""

    strict = [row for row in summary if row["passes_strict_promotion_criterion"]]
    pool = strict or summary
    return min(
        pool,
        key=lambda row: (
            not row["passes_strict_promotion_criterion"],
            row["mean_position_ratio"] + row["mean_sync_ratio"],
            row["max_sync_ratio"],
            row["candidate"],
        ),
    )


def _save_plot(fig: Any, stem: str) -> list[str]:
    """Save one plot as PDF and PNG."""

    PLOT_ROOT.mkdir(parents=True, exist_ok=True)
    outputs = []
    for suffix in (".pdf", ".png"):
        path = PLOT_ROOT / f"{stem}{suffix}"
        fig.savefig(path, bbox_inches="tight")
        outputs.append(_repo_rel(path))
    plt.close(fig)
    return outputs


def _plot_medium_heatmap(rows: list[dict[str, Any]]) -> list[str]:
    """Plot target medium row position/sync ratios."""

    fig, ax = plt.subplots(figsize=(8.0, 4.2))
    labels = [f"{row['variant']}\nNu{row['num_users']} Ns{row['num_satellites']}" for row in rows]
    data = np.asarray([[float(row["position_ratio"]), float(row["sync_ratio"])] for row in rows], dtype=float)
    image = ax.imshow(data.T, aspect="auto", cmap="viridis")
    ax.set_yticks([0, 1], labels=["position", "sync"])
    ax.set_xticks(range(len(labels)), labels=labels, rotation=90, fontsize=7)
    ax.set_title("Residual-scaled medium row ratios")
    fig.colorbar(image, ax=ax, label="Step 3 / Step B")
    return _save_plot(fig, "medium_row_position_sync_ratio_heatmap")


def _plot_failure_update_norms(failures: list[dict[str, Any]]) -> list[str]:
    """Plot failure-row update norms by block."""

    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    labels = [f"{row['variant']}\nNu{row['num_users']} Ns{row['num_satellites']}" for row in failures]
    blocks = ["position_update_norm", "ue_clock_update_norm", "satellite_clock_update_norm", "clock_drift_update_norm"]
    bottom = np.zeros(len(failures))
    for block in blocks:
        values = np.asarray([float(row[block]) for row in failures])
        ax.bar(range(len(failures)), values, bottom=bottom, label=block.replace("_update_norm", ""))
        bottom += values
    ax.set_xticks(range(len(labels)), labels=labels, rotation=90, fontsize=7)
    ax.set_ylabel("Update norm")
    ax.set_title("Failure-row update norms by block")
    ax.legend(fontsize=7)
    return _save_plot(fig, "failure_row_update_norm_by_block")


def _plot_block_vs_full(comparison: dict[str, Any]) -> list[str]:
    """Plot row comparison between target block and full variants."""

    rows = comparison["row_comparisons"]
    fig, ax = plt.subplots(figsize=(5.2, 4.2))
    ax.scatter(
        [row["block_diag_sync_ratio"] for row in rows],
        [row["full_sync_ratio"] for row in rows],
        label="sync ratio",
    )
    ax.scatter(
        [row["block_diag_position_ratio"] for row in rows],
        [row["full_position_ratio"] for row in rows],
        label="position ratio",
    )
    limit = max(
        [1.0]
        + [row["block_diag_sync_ratio"] for row in rows]
        + [row["full_sync_ratio"] for row in rows]
    )
    ax.plot([0, limit], [0, limit], "k--", linewidth=1.0)
    ax.set_xlabel("Block-diagonal")
    ax.set_ylabel("Full")
    ax.set_title("Block-diagonal vs full residual-scaled rows")
    ax.legend(fontsize=8)
    return _save_plot(fig, "block_diag_vs_full_covariance_row_comparison")


def _plot_candidate_ratios(summary: list[dict[str, Any]], *, pos_key: str, sync_key: str, stem: str, ylabel: str) -> list[str]:
    """Plot robust candidate position/sync ratio summary."""

    fig, ax = plt.subplots(figsize=(7.0, 4.0))
    labels = [row["candidate"].replace("residual_scaled_block_diag_", "") for row in summary]
    x = np.arange(len(labels))
    width = 0.38
    ax.bar(x - width / 2.0, [float(row[pos_key]) for row in summary], width=width, label="position")
    ax.bar(x + width / 2.0, [float(row[sync_key]) for row in summary], width=width, label="sync")
    ax.axhline(1.05, color="r", linestyle="--", linewidth=1.0, label="1.05 guardrail")
    ax.set_xticks(x, labels=labels, rotation=30, ha="right", fontsize=8)
    ax.set_ylabel(ylabel)
    ax.set_title(ylabel)
    ax.legend(fontsize=8)
    return _save_plot(fig, stem)


def _write_failure_report(audit: dict[str, Any], comparison: dict[str, Any]) -> tuple[str, str]:
    """Write failure-audit report files."""

    payload = {**audit, "block_vs_full_comparison": comparison}
    json_path = _write_json(REPORT_ROOT / "STEP3_RESIDUAL_COV_FAILURE_AUDIT.json", payload)
    md = [
        "# Step 3 Residual Covariance Failure Audit",
        "",
        f"- Artifact status: `{payload['artifact_status']}`",
        f"- Target variants: `{payload['target_variants']}`",
        f"- Failure rows: `{payload['failure_count']}` / `{payload['row_count']}`",
        f"- Same failure cases: `{payload['same_failure_cases']}`",
        f"- Block/full effectively identical: `{comparison['effectively_identical']}`",
        f"- Full cross-covariance used: `{comparison['full_cross_covariance_used']}`",
        f"- Preferred variant: `{comparison['preferred_variant']}`",
        "",
        "## Failure Rows",
        "",
        "| Variant | Nu | Ns | Position ratio | Sync ratio | Objective before | Objective after | Reasons |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in payload["failure_rows"]:
        reasons = ", ".join(name for name, active in row["flags"].items() if active)
        md.append(
            f"| `{row['variant']}` | {row['num_users']} | {row['num_satellites']} | "
            f"{row['position_ratio']:.4g} | {row['sync_ratio']:.4g} | "
            f"{row['objective_before']:.4g} | {row['objective_after']:.4g} | {reasons} |"
        )
    md += [
        "",
        "## Block-Diagonal vs Full Covariance",
        "",
        comparison["full_cross_covariance_note"],
    ]
    md_path = REPORT_ROOT / "STEP3_RESIDUAL_COV_FAILURE_AUDIT.md"
    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")
    return _repo_rel(md_path), json_path


def _write_candidate_report(payload: dict[str, Any]) -> tuple[str, str]:
    """Write robust-candidate report files."""

    json_path = _write_json(REPORT_ROOT / "STEP3_RESIDUAL_COV_ROBUST_CANDIDATE_REPORT.json", payload)
    md = [
        "# Step 3 Residual Covariance Robust Candidate Report",
        "",
        f"- Artifact status: `{payload['artifact_status']}`",
        f"- Best robust candidate: `{payload['best_candidate']['candidate']}`",
        f"- Medium rows: `{payload['row_count']}`",
        f"- Truth-state acceptance: `{payload['truth_state_used_for_acceptance']}`",
        f"- Truth-derived covariance: `{payload['truth_state_used_for_covariance']}`",
        "",
        "## Candidate Summary",
        "",
        "| Candidate | Both improved | Mean position | Max position | Mean sync | Max sync | Fallbacks | Strict pass |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in payload["summary"]:
        md.append(
            f"| `{row['candidate']}` | {row['both_improved_count']}/{row['tested_cases']} | "
            f"{row['mean_position_ratio']:.4g} | {row['max_position_ratio']:.4g} | "
            f"{row['mean_sync_ratio']:.4g} | {row['max_sync_ratio']:.4g} | "
            f"{row['fallback_count']} | `{row['passes_strict_promotion_criterion']}` |"
        )
    md += [
        "",
        "## Output Paths",
        "",
        f"- Raw CSV: `{payload['raw_csv']}`",
        f"- Summary CSV: `{payload['summary_csv']}`",
        f"- Metadata JSON: `{payload['metadata_json']}`",
        "- Plots:",
        *[f"  - `{path}`" for path in payload["plots"]],
    ]
    md_path = REPORT_ROOT / "STEP3_RESIDUAL_COV_ROBUST_CANDIDATE_REPORT.md"
    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")
    return _repo_rel(md_path), json_path


def run_audit_and_candidates() -> dict[str, Any]:
    """Run failure audit and robust candidate validation."""

    started = time.monotonic()
    target_rows = _target_medium_rows()
    audit = _failure_audit(target_rows)
    comparison = _compare_target_variants(target_rows)
    failure_report_md, failure_report_json = _write_failure_report(audit, comparison)
    _write_csv(FAILURE_AUDIT_ROOT / "target_medium_rows.csv", target_rows)
    _write_csv(FAILURE_AUDIT_ROOT / "failure_rows.csv", audit["failure_rows"])
    _write_json(FAILURE_AUDIT_ROOT / "metadata.json", {**audit, "block_vs_full_comparison": comparison})

    rows = [_evaluate_candidate(case, candidate) for candidate in CANDIDATES for case in cov.medium_cases()]
    summary = _summarize_candidates(rows)
    best = _best_candidate(summary)
    raw_csv = _write_csv(ROBUST_ROOT / "raw.csv", rows)
    summary_csv = _write_csv(ROBUST_ROOT / "summary.csv", summary)
    plots: list[str] = []
    plots.extend(_plot_medium_heatmap(target_rows))
    plots.extend(_plot_failure_update_norms(audit["failure_rows"]))
    plots.extend(_plot_block_vs_full(comparison))
    plots.extend(_plot_candidate_ratios(summary, pos_key="max_position_ratio", sync_key="max_sync_ratio", stem="robust_candidate_max_ratio_comparison", ylabel="Max Step3 / StepB ratio"))
    plots.extend(_plot_candidate_ratios(summary, pos_key="mean_position_ratio", sync_key="mean_sync_ratio", stem="robust_candidate_mean_ratio_comparison", ylabel="Mean Step3 / StepB ratio"))
    metadata = {
        "artifact_status": "non_final_step3_residual_cov_robust_candidate_validation",
        "manuscript_ready": False,
        "not_for_manuscript_submission": True,
        "target_variants": list(TARGET_VARIANTS),
        "candidates": [asdict(candidate) for candidate in CANDIDATES],
        "row_count": len(rows),
        "summary": summary,
        "best_candidate": best,
        "rows": rows,
        "truth_state_used_for_acceptance": False,
        "truth_state_used_for_covariance": False,
        "truth_state_used_for_diagnostics": True,
        "medium_grid_only": True,
        "broad_exploration_rerun": False,
        "full_ladder_run": False,
        "runtime_seconds": time.monotonic() - started,
        "raw_csv": raw_csv,
        "summary_csv": summary_csv,
        "plots": plots,
        "failure_audit_report_md": failure_report_md,
        "failure_audit_report_json": failure_report_json,
    }
    metadata_json = _write_json(ROBUST_ROOT / "metadata.json", metadata)
    metadata["metadata_json"] = metadata_json
    _write_json(ROBUST_ROOT / "metadata.json", metadata)
    report_md, report_json = _write_candidate_report(metadata)
    metadata["report_md"] = report_md
    metadata["report_json"] = report_json
    _write_json(ROBUST_ROOT / "metadata.json", metadata)
    return metadata


def _planned_work() -> dict[str, Any]:
    """Return planned work without execution."""

    return {
        "artifact_status": "non_final_step3_residual_cov_audit_planned_work",
        "will_execute": False,
        "target_variants": list(TARGET_VARIANTS),
        "candidates": [candidate.name for candidate in CANDIDATES],
        "medium_cases": [{"num_users": nu, "num_satellites": ns} for nu, ns in cov.MEDIUM_CASES],
        "broad_exploration_rerun": False,
        "full_ladder_run": False,
        "notebook_run": False,
        "manuscript_figures_generated": False,
    }


def main(argv: list[str] | None = None) -> dict[str, Any]:
    """Run the audit unless dry-run is requested."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="List planned residual covariance audit work.")
    args = parser.parse_args(argv)
    if args.dry_run:
        payload = _planned_work()
        print(json.dumps(payload, indent=2))
        return payload
    payload = run_audit_and_candidates()
    print(json.dumps({key: payload[key] for key in ("artifact_status", "row_count", "best_candidate", "runtime_seconds")}, indent=2))
    return payload


if __name__ == "__main__":
    main()
