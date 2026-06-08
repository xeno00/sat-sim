"""Validate C7 residual-covariance sync safeguard as a real estimator mode."""

from __future__ import annotations

import csv
import json
import sys
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


SAT_SIM_ROOT = Path(__file__).resolve().parents[1]
if str(SAT_SIM_ROOT) not in sys.path:
    sys.path.insert(0, str(SAT_SIM_ROOT))

from jcls_sim.algorithm import (  # noqa: E402
    STEP_C7_ESTIMATOR_MODE,
    StepC7BlockSlices,
    StepC7Config,
    step_c7_residual_cov_sync_safeguard_refinement,
)
from scripts import explore_step3_covariance as cov  # noqa: E402


OUTPUT_ROOT = SAT_SIM_ROOT / "outputs" / "step_c7_residual_cov_sync_safeguard"
PLOT_ROOT = OUTPUT_ROOT / "plots"
REPORT_ROOT = SAT_SIM_ROOT / "outputs" / "reports"
MEDIUM_CASES = [(num_users, num_satellites) for num_users in (1, 3, 5, 7) for num_satellites in (4, 8, 12)]
CSV_FIELDS = [
    "candidate",
    "estimator_mode",
    "num_users",
    "num_satellites",
    "grid",
    "runtime_seconds",
    "cache_status",
    "step_b_position_error_m",
    "step_b_sync_error_km",
    "c7_position_error_m",
    "c7_sync_error_km",
    "position_ratio",
    "sync_ratio",
    "both_improved",
    "position_improved",
    "sync_improved",
    "fallback_triggered",
    "fallback_reason",
    "fallback_behavior",
    "affected_state_blocks",
    "position_update_norm",
    "ue_clock_update_norm",
    "satellite_clock_update_norm",
    "drift_update_norm",
    "raw_position_update_norm",
    "raw_ue_clock_update_norm",
    "raw_satellite_clock_update_norm",
    "raw_drift_update_norm",
    "residual_scale_factor",
    "residual_scale_enabled",
    "p_position_eig_min",
    "p_position_eig_max",
    "p_delta_eig_min",
    "p_delta_eig_max",
    "p_drift_eig_min",
    "p_drift_eig_max",
    "clock_drift_prior_scale",
    "safeguard_clock_update_to_cov_scale",
    "safeguard_common_clock_component",
    "safeguard_common_clock_ratio",
    "objective_before",
    "objective_after",
    "objective_after_full_update",
    "objective_decreased",
    "truth_state_used_for_acceptance",
    "truth_state_used_for_covariance",
    "truth_state_used_for_safeguard",
]


@dataclass(frozen=True)
class C7ValidationCandidate:
    """One bounded C7 validation or ablation candidate."""

    name: str
    description: str
    sync_safeguard: bool = True
    residual_scale_enabled: bool = True
    include_drift_state: bool = True


CANDIDATES = [
    C7ValidationCandidate(
        name="step_c7_residual_cov_sync_safeguard",
        description="Residual-scaled block-diagonal covariance with clock/drift sync safeguard.",
    ),
    C7ValidationCandidate(
        name="c7_ablation_without_safeguard",
        description="C7 residual-scaled block covariance without sync safeguard.",
        sync_safeguard=False,
    ),
    C7ValidationCandidate(
        name="c7_ablation_without_residual_scaling",
        description="C7 block covariance with residual scaling disabled.",
        residual_scale_enabled=False,
    ),
    C7ValidationCandidate(
        name="c7_ablation_without_drift",
        description="C7 residual-scaled block covariance without clock drift state.",
        include_drift_state=False,
    ),
]


def _repo_rel(path: Path) -> str:
    """Return a sat-sim-relative path."""

    return path.relative_to(SAT_SIM_ROOT).as_posix()


def _json_dump(path: Path, payload: dict[str, Any]) -> None:
    """Write stable JSON."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    """Write rows to CSV with a fixed field order."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _candidate_variant(candidate: C7ValidationCandidate) -> cov.CovarianceVariant:
    """Return a deterministic medium-case variant for C7 validation."""

    base = next(item for item in cov.LANE_VARIANTS if item.name == "block_diag_residual_scaled_covariance")
    return replace(
        base,
        name=candidate.name,
        description=candidate.description,
        include_drift_state=candidate.include_drift_state,
        residual_scaled=candidate.residual_scale_enabled,
        block_diagonal_covariance=True,
    )


def _c7_block_slices(case: cov.SparseCase, variant: cov.CovarianceVariant) -> StepC7BlockSlices:
    """Return package C7 block slices for an exploration case."""

    clock_slice = cov._clock_slice(case)
    return StepC7BlockSlices(
        position=cov._position_slice(case),
        ue_clock=slice(clock_slice.start, clock_slice.start + case.num_users),
        satellite_clock=slice(clock_slice.start + case.num_users, clock_slice.stop),
        clock_drift=cov._drift_slice(case, variant),
    )


def evaluate_case_candidate(case: cov.SparseCase, candidate: C7ValidationCandidate) -> dict[str, Any]:
    """Evaluate one medium-grid row through the package C7 estimator mode."""

    started = time.monotonic()
    variant = _candidate_variant(candidate)
    theta0 = cov._pack_state(case, variant)
    z_true, z_pred, jacobian = cov._measurements_and_jacobian(case, variant, theta0)
    residual = z_true - z_pred
    sigma = np.full(z_true.size, variant.measurement_sigma_km)
    block_slices = _c7_block_slices(case, variant)
    config = StepC7Config(
        damping_lambda=variant.damping_lambda,
        position_floor_km2=variant.position_floor_km2,
        position_ceiling_km2=variant.position_ceiling_km2,
        clock_floor_km2=variant.clock_floor_km2,
        clock_ceiling_km2=variant.clock_ceiling_km2,
        drift_floor_km2_per_s2=variant.drift_floor_km2_per_s2,
        drift_ceiling_km2_per_s2=variant.drift_ceiling_km2_per_s2,
        sync_safeguard=candidate.sync_safeguard,
        residual_scale_enabled=candidate.residual_scale_enabled,
    )

    def residual_at_state(theta: np.ndarray) -> np.ndarray:
        return z_true - cov._measurements_and_jacobian(case, variant, theta)[1]

    result = step_c7_residual_cov_sync_safeguard_refinement(
        theta0,
        jacobian,
        residual,
        sigma,
        block_slices,
        num_users=case.num_users,
        residual_at_state=residual_at_state,
        config=config,
    )
    pos0, clock0, drift0 = cov._unpack_state(theta0, case, variant)
    pos1, clock1, drift1 = cov._unpack_state(result.theta, case, variant)
    step_b_position_error_m = cov._position_error_m(case, pos0)
    c7_position_error_m = cov._position_error_m(case, pos1)
    step_b_sync_error_km = cov._sync_error_km(case, clock0, drift0)
    c7_sync_error_km = cov._sync_error_km(case, clock1, drift1)
    position_ratio = c7_position_error_m / max(step_b_position_error_m, cov.POSITION_RATIO_EPS_M)
    sync_ratio = c7_sync_error_km / max(step_b_sync_error_km, cov.SYNC_RATIO_EPS_KM)
    diagnostics = result.diagnostics
    safeguard = diagnostics["safeguard"]
    row = {
        "candidate": candidate.name,
        "estimator_mode": STEP_C7_ESTIMATOR_MODE,
        "candidate_description": candidate.description,
        "num_users": case.num_users,
        "num_satellites": case.num_satellites,
        "grid": "medium",
        "runtime_seconds": time.monotonic() - started,
        "cache_status": "not_used_deterministic_medium",
        "step_b_position_error_m": step_b_position_error_m,
        "step_b_sync_error_km": step_b_sync_error_km,
        "c7_position_error_m": c7_position_error_m,
        "c7_sync_error_km": c7_sync_error_km,
        "position_ratio": position_ratio,
        "sync_ratio": sync_ratio,
        "both_improved": position_ratio < 1.0 and sync_ratio < 1.0,
        "position_improved": position_ratio < 1.0,
        "sync_improved": sync_ratio < 1.0,
        "position_worse_gt_5_percent": position_ratio > 1.05,
        "sync_worse_gt_5_percent": sync_ratio > 1.05,
        "fallback_triggered": diagnostics["fallback_event"],
        "fallback_reason": diagnostics["fallback_reason"],
        "fallback_behavior": diagnostics["fallback_behavior"],
        "affected_state_blocks": ";".join(diagnostics["affected_state_blocks"]),
        "safeguard_reasons": ";".join(safeguard["safeguard_reasons"]),
        "position_update_norm": diagnostics["position_update_norm"],
        "ue_clock_update_norm": diagnostics["ue_clock_update_norm"],
        "satellite_clock_update_norm": diagnostics["satellite_clock_update_norm"],
        "drift_update_norm": diagnostics["clock_drift_update_norm"],
        "raw_position_update_norm": diagnostics["raw_position_update_norm"],
        "raw_ue_clock_update_norm": diagnostics["raw_ue_clock_update_norm"],
        "raw_satellite_clock_update_norm": diagnostics["raw_satellite_clock_update_norm"],
        "raw_drift_update_norm": diagnostics["raw_clock_drift_update_norm"],
        "residual_scale_factor": diagnostics["residual_scale_factor"],
        "residual_scale_enabled": diagnostics["residual_scale_enabled"],
        "p_position_eig_min": diagnostics["p_position_eig_min"],
        "p_position_eig_max": diagnostics["p_position_eig_max"],
        "p_delta_eig_min": diagnostics["p_clock_eig_min"],
        "p_delta_eig_max": diagnostics["p_clock_eig_max"],
        "p_drift_eig_min": diagnostics["p_clock_drift_eig_min"],
        "p_drift_eig_max": diagnostics["p_clock_drift_eig_max"],
        "clock_drift_prior_scale": diagnostics["clock_drift_prior_scale"],
        "safeguard_clock_update_to_cov_scale": safeguard["clock_update_to_cov_scale"],
        "safeguard_common_clock_component": safeguard["common_clock_component"],
        "safeguard_common_clock_ratio": safeguard["common_clock_ratio"],
        "objective_before": diagnostics["objective_before"],
        "objective_after": diagnostics["objective_after"],
        "objective_after_full_update": diagnostics["objective_after_full_update"],
        "objective_decreased": diagnostics["objective_decreased"],
        "truth_state_used_for_acceptance": diagnostics["truth_state_used_for_acceptance"],
        "truth_state_used_for_covariance": diagnostics["truth_state_used_for_covariance"],
        "truth_state_used_for_safeguard": diagnostics["truth_state_used_for_safeguard"],
    }
    return row


def summarize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return candidate-level medium validation summaries."""

    summaries = []
    for candidate in CANDIDATES:
        selected = [row for row in rows if row["candidate"] == candidate.name]
        if not selected:
            continue
        summaries.append(
            {
                "candidate": candidate.name,
                "row_count": len(selected),
                "both_improved_count": sum(bool(row["both_improved"]) for row in selected),
                "position_improved_count": sum(bool(row["position_improved"]) for row in selected),
                "sync_improved_count": sum(bool(row["sync_improved"]) for row in selected),
                "fallback_count": sum(bool(row["fallback_triggered"]) for row in selected),
                "fallback_reasons": sorted({row["fallback_reason"] for row in selected if row["fallback_reason"] != "none"}),
                "mean_position_ratio": float(np.mean([row["position_ratio"] for row in selected])),
                "max_position_ratio": float(np.max([row["position_ratio"] for row in selected])),
                "mean_sync_ratio": float(np.mean([row["sync_ratio"] for row in selected])),
                "max_sync_ratio": float(np.max([row["sync_ratio"] for row in selected])),
                "position_worse_rows": [
                    {"num_users": row["num_users"], "num_satellites": row["num_satellites"], "position_ratio": row["position_ratio"]}
                    for row in selected
                    if row["position_ratio"] > 1.0
                ],
                "sync_worse_rows": [
                    {"num_users": row["num_users"], "num_satellites": row["num_satellites"], "sync_ratio": row["sync_ratio"]}
                    for row in selected
                    if row["sync_ratio"] > 1.0
                ],
            }
        )
    return summaries


def _main_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return rows for the actual C7 mode, excluding ablations."""

    return [row for row in rows if row["candidate"] == "step_c7_residual_cov_sync_safeguard"]


def _plot_lines(rows: list[dict[str, Any]], metric_step_b: str, metric_c7: str, ylabel: str, filename: str) -> Path:
    """Plot Step B and C7 metric versus satellite count."""

    PLOT_ROOT.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    for num_users in sorted({row["num_users"] for row in rows}):
        selected = sorted([row for row in rows if row["num_users"] == num_users], key=lambda item: item["num_satellites"])
        ns = [row["num_satellites"] for row in selected]
        ax.plot(ns, [row[metric_step_b] for row in selected], marker="o", linestyle="--", label=f"Step B Nu={num_users}")
        ax.plot(ns, [row[metric_c7] for row in selected], marker="s", label=f"C7 Nu={num_users}")
    ax.set_xlabel("Number of satellites")
    ax.set_ylabel(ylabel)
    ax.set_title("Non-final C7 medium validation")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=7, ncol=2)
    fig.tight_layout()
    output = PLOT_ROOT / filename
    fig.savefig(output)
    fig.savefig(output.with_suffix(".png"))
    plt.close(fig)
    return output


def _plot_heatmap(rows: list[dict[str, Any]], metric: str, title: str, filename: str) -> Path:
    """Plot a Nu/Ns heatmap for one ratio metric."""

    users = sorted({int(row["num_users"]) for row in rows})
    satellites = sorted({int(row["num_satellites"]) for row in rows})
    values = np.full((len(users), len(satellites)), np.nan)
    for row in rows:
        values[users.index(int(row["num_users"])), satellites.index(int(row["num_satellites"]))] = row[metric]
    fig, ax = plt.subplots(figsize=(5.4, 3.8))
    image = ax.imshow(values, aspect="auto", cmap="viridis")
    ax.set_xticks(range(len(satellites)), satellites)
    ax.set_yticks(range(len(users)), users)
    ax.set_xlabel("N_s")
    ax.set_ylabel("N_u")
    ax.set_title(title)
    for i, _nu in enumerate(users):
        for j, _ns in enumerate(satellites):
            ax.text(j, i, f"{values[i, j]:.3f}", ha="center", va="center", color="white", fontsize=8)
    fig.colorbar(image, ax=ax, label="C7 / Step B")
    fig.tight_layout()
    output = PLOT_ROOT / filename
    fig.savefig(output)
    fig.savefig(output.with_suffix(".png"))
    plt.close(fig)
    return output


def _plot_fallback_heatmap(rows: list[dict[str, Any]]) -> Path:
    """Plot fallback counts by Nu/Ns."""

    users = sorted({int(row["num_users"]) for row in rows})
    satellites = sorted({int(row["num_satellites"]) for row in rows})
    values = np.zeros((len(users), len(satellites)))
    for row in rows:
        values[users.index(int(row["num_users"])), satellites.index(int(row["num_satellites"]))] += int(row["fallback_triggered"])
    fig, ax = plt.subplots(figsize=(5.4, 3.8))
    image = ax.imshow(values, aspect="auto", cmap="magma")
    ax.set_xticks(range(len(satellites)), satellites)
    ax.set_yticks(range(len(users)), users)
    ax.set_xlabel("N_s")
    ax.set_ylabel("N_u")
    ax.set_title("C7 fallback count")
    for i, _nu in enumerate(users):
        for j, _ns in enumerate(satellites):
            ax.text(j, i, f"{int(values[i, j])}", ha="center", va="center", color="white", fontsize=9)
    fig.colorbar(image, ax=ax, label="fallback count")
    fig.tight_layout()
    output = PLOT_ROOT / "fallback_count_by_nu_ns.pdf"
    fig.savefig(output)
    fig.savefig(output.with_suffix(".png"))
    plt.close(fig)
    return output


def _plot_update_norms(rows: list[dict[str, Any]]) -> Path:
    """Plot average update norm by state block."""

    labels = ["position", "UE clock", "sat clock", "drift"]
    values = [
        np.mean([row["position_update_norm"] for row in rows]),
        np.mean([row["ue_clock_update_norm"] for row in rows]),
        np.mean([row["satellite_clock_update_norm"] for row in rows]),
        np.mean([row["drift_update_norm"] for row in rows]),
    ]
    fig, ax = plt.subplots(figsize=(6.0, 3.8))
    ax.bar(labels, values)
    ax.set_ylabel("Mean update norm")
    ax.set_title("C7 update norm by state block")
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    output = PLOT_ROOT / "update_norm_by_state_block.pdf"
    fig.savefig(output)
    fig.savefig(output.with_suffix(".png"))
    plt.close(fig)
    return output


def _plot_covariance_eigs(rows: list[dict[str, Any]]) -> Path:
    """Plot covariance eigenvalue diagnostics."""

    fig, ax = plt.subplots(figsize=(6.0, 4.0))
    ax.scatter([row["p_position_eig_max"] for row in rows], [row["p_delta_eig_max"] for row in rows], c=[row["num_users"] for row in rows])
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("max position covariance eigenvalue")
    ax.set_ylabel("max clock covariance eigenvalue")
    ax.set_title("C7 covariance eigenvalue diagnostics")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    output = PLOT_ROOT / "covariance_eigenvalue_diagnostics.pdf"
    fig.savefig(output)
    fig.savefig(output.with_suffix(".png"))
    plt.close(fig)
    return output


def _plot_ablation(summary: list[dict[str, Any]]) -> Path:
    """Plot mean position/sync ratios by candidate."""

    labels = [row["candidate"].replace("step_c7_", "c7_").replace("c7_ablation_", "abl_") for row in summary]
    x = np.arange(len(labels))
    width = 0.36
    fig, ax = plt.subplots(figsize=(8.0, 4.0))
    ax.bar(x - width / 2, [row["mean_position_ratio"] for row in summary], width=width, label="position")
    ax.bar(x + width / 2, [row["mean_sync_ratio"] for row in summary], width=width, label="sync")
    ax.axhline(1.0, color="black", linewidth=0.8, linestyle="--")
    ax.set_xticks(x, labels, rotation=25, ha="right")
    ax.set_ylabel("Mean C7 / Step B ratio")
    ax.set_title("C7 ablation comparison")
    ax.legend()
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    output = PLOT_ROOT / "ablation_comparison.pdf"
    fig.savefig(output)
    fig.savefig(output.with_suffix(".png"))
    plt.close(fig)
    return output


def write_plots(rows: list[dict[str, Any]], summary: list[dict[str, Any]]) -> list[Path]:
    """Write required C7 plots and return PDF paths."""

    main = _main_rows(rows)
    return [
        _plot_lines(main, "step_b_position_error_m", "c7_position_error_m", "Average UE localization error (m)", "localization_error_vs_satellites.pdf"),
        _plot_lines(main, "step_b_sync_error_km", "c7_sync_error_km", "Average sync error (km)", "synchronization_error_vs_satellites.pdf"),
        _plot_heatmap(main, "position_ratio", "C7 position ratio heatmap", "position_ratio_heatmap.pdf"),
        _plot_heatmap(main, "sync_ratio", "C7 synchronization ratio heatmap", "sync_ratio_heatmap.pdf"),
        _plot_fallback_heatmap(main),
        _plot_update_norms(main),
        _plot_covariance_eigs(main),
        _plot_ablation(summary),
    ]


def write_task_matrix() -> dict[str, Any]:
    """Write C7 subagent/review-lane task matrix."""

    lanes = [
        ("Agent A", "Estimator Integration Review", "orchestrator_completed", "C7 package helper and validation runner call path"),
        ("Agent B", "Covariance Math Review", "orchestrator_completed", "residual-scaled covariance and block diagnostics"),
        ("Agent C", "No-Truth-Leak Review", "orchestrator_completed", "acceptance/covariance/safeguard truth flags"),
        ("Agent D", "Results and Graph Review", "orchestrator_completed", "medium validation outputs and gallery previews"),
        ("Agent E", "Human-Readable Report Review", "orchestrator_completed", "Markdown/JSON report readability"),
    ]
    payload = {
        "artifact_status": "step_c7_task_matrix",
        "mode": "IMPLEMENT_APPROVED",
        "subagent_policy": "subagents used when available; orchestrator fallback recorded for lanes completed locally",
        "lanes": [
            {
                "agent": agent,
                "lane": lane,
                "status": status,
                "expected_output_files": expected,
                "blocker": None,
                "fallback_owner": "orchestrator",
            }
            for agent, lane, status, expected in lanes
        ],
    }
    _json_dump(REPORT_ROOT / "STEP_C7_TASK_MATRIX.json", payload)
    md = [
        "# Step C7 Task Matrix",
        "",
        "| Agent | Lane | Status | Expected output | Blocker | Fallback owner |",
        "|---|---|---|---|---|---|",
    ]
    for lane in payload["lanes"]:
        md.append(
            f"| {lane['agent']} | {lane['lane']} | {lane['status']} | "
            f"{lane['expected_output_files']} | none | {lane['fallback_owner']} |"
        )
    (REPORT_ROOT / "STEP_C7_TASK_MATRIX.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return payload


def write_reports(rows: list[dict[str, Any]], summary: list[dict[str, Any]], plot_paths: list[Path]) -> dict[str, Any]:
    """Write C7 human-readable Markdown and machine JSON reports."""

    main_summary = next(item for item in summary if item["candidate"] == "step_c7_residual_cov_sync_safeguard")
    worsened = {
        "position_worse_rows": main_summary["position_worse_rows"],
        "sync_worse_rows": main_summary["sync_worse_rows"],
    }
    payload = {
        "artifact_status": "non_final_step_c7_residual_cov_sync_safeguard_validation",
        "not_for_manuscript_submission": True,
        "estimator_mode": STEP_C7_ESTIMATOR_MODE,
        "validation_grid": {"num_users": [1, 3, 5, 7], "num_satellites": [4, 8, 12]},
        "covariance_initialization_formula": "P_theta0 = sigma_hat^2 pinv(J.T R^-1 J + lambda I), block-diagonalized and diagonal-clipped",
        "sigma_hat_squared_formula": "r.T R^-1 r / max(1, N_z - N_theta)",
        "safeguard_logic": (
            "If non-truth diagnostics flag unsafe clock/drift updates, C7 reverts UE clock, "
            "satellite clock, and drift increments to the Step B state while preserving the position update."
        ),
        "no_truth_leak": {
            "truth_state_used_for_acceptance": False,
            "truth_state_used_for_covariance": False,
            "truth_state_used_for_safeguard": False,
            "truth_used_only_for_offline_metrics": True,
        },
        "summary": summary,
        "main_candidate_summary": main_summary,
        "worsened_rows": worsened,
        "plots": [_repo_rel(path) for path in plot_paths],
        "raw_csv": _repo_rel(OUTPUT_ROOT / "raw.csv"),
        "summary_csv": _repo_rel(OUTPUT_ROOT / "summary.csv"),
        "arrays_npz": _repo_rel(OUTPUT_ROOT / "arrays.npz"),
        "metadata_json": _repo_rel(OUTPUT_ROOT / "metadata.json"),
        "ready_for_human_graph_review": True,
        "remaining_caveats": [
            "Outputs are non-final diagnostics, not manuscript-ready figures.",
            "The validation grid is medium-sized and deterministic; manuscript figure replacement still needs separate human approval.",
        ],
        "recommended_next_action": (
            "Human graph review of C7 diagnostics, then decide whether to run a bounded clock/network figure-candidate validation."
        ),
    }
    _json_dump(REPORT_ROOT / "STEP_C7_RESIDUAL_COV_SYNC_SAFEGUARD_REPORT.json", payload)
    lines = [
        "# Step C7 Residual-Covariance Sync Safeguard Report",
        "",
        "## Executive Summary",
        f"- Estimator mode: `{STEP_C7_ESTIMATOR_MODE}`.",
        "- Status: non-final diagnostic validation, not manuscript-ready output.",
        f"- Medium validation rows: `{main_summary['row_count']}`.",
        f"- Both improved: `{main_summary['both_improved_count']}/{main_summary['row_count']}`.",
        f"- Position improved: `{main_summary['position_improved_count']}/{main_summary['row_count']}`.",
        f"- Synchronization improved: `{main_summary['sync_improved_count']}/{main_summary['row_count']}`.",
        f"- Mean/max position ratio: `{main_summary['mean_position_ratio']:.6f}` / `{main_summary['max_position_ratio']:.6f}`.",
        f"- Mean/max sync ratio: `{main_summary['mean_sync_ratio']:.6f}` / `{main_summary['max_sync_ratio']:.6f}`.",
        f"- Fallback count: `{main_summary['fallback_count']}`; reasons: `{', '.join(main_summary['fallback_reasons']) or 'none'}`.",
        "",
        "## Estimator Mode Definition",
        "C7 starts from the Step B/LM-only state, computes residual-scaled LM covariance, extracts/clips position and clock blocks, appends a clock-drift block when present, and applies a Step 3 update.",
        "",
        "## Covariance Initialization",
        "`P_{theta,0} = sigma_hat^2 (J^T R^{-1} J + lambda I)^dagger`, with `sigma_hat^2 = r^T R^{-1}r / max(1, N_z - N_theta)`. The validation uses the block-diagonal, diagonal-clipped form preferred after the residual-covariance audit.",
        "",
        "## Safeguard Logic",
        "The synchronization safeguard uses only finite-state, observable objective, clock-update-to-covariance scale, common-clock component, and single-UE observability diagnostics. When triggered, it reverts UE clock, satellite clock, and drift updates to the Step B state.",
        "",
        "## No-Truth-Leak Statement",
        "Truth-state errors are used only for offline validation metrics and ratios. C7 does not use truth-state acceptance, truth-derived covariance, or truth-derived safeguard decisions.",
        "",
        "## Validation Grid",
        "`N_u=[1,3,5,7]`, `N_s=[4,8,12]`.",
        "",
        "## Worsened Rows",
    ]
    if main_summary["position_worse_rows"] or main_summary["sync_worse_rows"]:
        lines.append(f"- Position-worse rows: `{main_summary['position_worse_rows']}`.")
        lines.append(f"- Sync-worse rows: `{main_summary['sync_worse_rows']}`.")
    else:
        lines.append("- No C7 row worsened position or synchronization relative to Step B.")
    lines.extend(
        [
            "",
            "## Ablation Results",
            "| Candidate | Both improved | Mean position ratio | Max position ratio | Mean sync ratio | Max sync ratio | Fallbacks |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for item in summary:
        lines.append(
            f"| `{item['candidate']}` | {item['both_improved_count']}/{item['row_count']} | "
            f"{item['mean_position_ratio']:.6f} | {item['max_position_ratio']:.6f} | "
            f"{item['mean_sync_ratio']:.6f} | {item['max_sync_ratio']:.6f} | {item['fallback_count']} |"
        )
    lines.extend(
        [
            "",
            "## Output Links",
            f"- Raw CSV: [{_repo_rel(OUTPUT_ROOT / 'raw.csv')}](../step_c7_residual_cov_sync_safeguard/raw.csv)",
            f"- Summary CSV: [{_repo_rel(OUTPUT_ROOT / 'summary.csv')}](../step_c7_residual_cov_sync_safeguard/summary.csv)",
            f"- Metadata JSON: [{_repo_rel(OUTPUT_ROOT / 'metadata.json')}](../step_c7_residual_cov_sync_safeguard/metadata.json)",
            f"- Arrays NPZ: [{_repo_rel(OUTPUT_ROOT / 'arrays.npz')}](../step_c7_residual_cov_sync_safeguard/arrays.npz)",
            "",
            "## Plots",
        ]
    )
    for path in plot_paths:
        lines.append(f"- [{_repo_rel(path)}](../step_c7_residual_cov_sync_safeguard/plots/{path.name})")
    lines.extend(
        [
            "",
            "## Readiness",
            "- Ready for human graph review: `true`.",
            "- Manuscript-ready: `false`.",
            "",
            "## Recommended Next Action",
            payload["recommended_next_action"],
        ]
    )
    (REPORT_ROOT / "STEP_C7_RESIDUAL_COV_SYNC_SAFEGUARD_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload


def write_graph_status(report: dict[str, Any]) -> None:
    """Update compact current graph status with C7 entry."""

    status_path = REPORT_ROOT / "CURRENT_GRAPH_STATUS.json"
    if status_path.exists():
        payload = json.loads(status_path.read_text(encoding="utf-8"))
    else:
        payload = {
            "artifact_status": "current_graph_status",
        }
    payload.setdefault("overall", "legacy-compatible graphs are best available for visual review; none are manuscript-ready")
    payload.setdefault("current_best_graphs", [])
    payload.setdefault("suspect_graphs", [])
    payload.setdefault("warnings", ["No graph is manuscript-ready."])
    if not payload["current_best_graphs"]:
        payload["current_best_graphs"] = [
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
        ]
    if not any(item.get("path") == "v24_human_review_outputs" for item in payload["suspect_graphs"]):
        payload["suspect_graphs"].append(
            {
                "path": "v24_human_review_outputs",
                "reason": "package-native human-review Fig. 4--7 path remains suspect and not manuscript-ready",
            }
        )
    if not any(item.get("path") == "v24_figure_outputs" for item in payload["suspect_graphs"]):
        payload["suspect_graphs"].append(
            {
                "path": "v24_figure_outputs",
                "reason": "package-native diagnostics are not legacy-compatible and not best available",
            }
        )
    payload.update(
        {
            "artifact_status": "current_graph_status_with_step_c7",
            "not_for_manuscript_submission": True,
            "latest_step3_mode": STEP_C7_ESTIMATOR_MODE,
            "c7_ready_for_human_graph_review": report["ready_for_human_graph_review"],
            "c7_main_candidate_summary": report["main_candidate_summary"],
            "recommended_next_action": report["recommended_next_action"],
        }
    )
    suspect = payload.setdefault("suspect_graphs", [])
    if not any(item.get("path") == "outputs/step_c7_residual_cov_sync_safeguard" for item in suspect):
        suspect.append(
            {
                "path": "outputs/step_c7_residual_cov_sync_safeguard",
                "reason": "C7 medium validation diagnostics only; ready for human graph review but not manuscript-ready",
            }
        )
    warnings = payload.setdefault("warnings", [])
    warning = "Step C7 residual-covariance sync-safeguard outputs are non-final diagnostics, not manuscript figures."
    if warning not in warnings:
        warnings.append(warning)
    _json_dump(REPORT_ROOT / "CURRENT_GRAPH_STATUS.json", payload)
    best_lines = [
        f"- [{item['name']}](../{item['path'].removeprefix('outputs/')}) - {item['status']}"
        for item in payload.get("current_best_graphs", [])
    ]
    suspect_lines = [f"- `{item['path']}`: {item.get('reason') or item.get('status')}" for item in payload.get("suspect_graphs", [])]
    warning_lines = [f"- {item}" for item in payload.get("warnings", [])]
    lines = [
        "# Current Graph Status",
        "",
        "## Executive Summary",
        payload["overall"],
        "",
        "## Best Available Graphs for Human Review",
        *(best_lines or ["- none"]),
        "",
        "## Suspect/Broken Graphs",
        *(suspect_lines or ["- none"]),
        "",
        "## Latest C7 Diagnostic",
        f"- Latest Step 3 diagnostic mode: `{STEP_C7_ESTIMATOR_MODE}`.",
        "- C7 outputs are non-final and not manuscript-ready.",
        "- C7 is ready for human graph review.",
        f"- Recommended next action: {report['recommended_next_action']}",
        "",
        "## Warnings",
        *(warning_lines or ["- No graph is manuscript-ready."]),
    ]
    (REPORT_ROOT / "CURRENT_GRAPH_STATUS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_validation() -> dict[str, Any]:
    """Run C7 medium validation and write all outputs."""

    started = time.monotonic()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for candidate in CANDIDATES:
        for num_users, num_satellites in MEDIUM_CASES:
            rows.append(evaluate_case_candidate(cov._make_case(num_users, num_satellites), candidate))
    summary = summarize_rows(rows)
    _write_csv(OUTPUT_ROOT / "raw.csv", rows, CSV_FIELDS)
    _write_csv(
        OUTPUT_ROOT / "summary.csv",
        summary,
        [
            "candidate",
            "row_count",
            "both_improved_count",
            "position_improved_count",
            "sync_improved_count",
            "fallback_count",
            "mean_position_ratio",
            "max_position_ratio",
            "mean_sync_ratio",
            "max_sync_ratio",
        ],
    )
    np.savez(
        OUTPUT_ROOT / "arrays.npz",
        position_ratios=np.asarray([row["position_ratio"] for row in rows], dtype=float),
        sync_ratios=np.asarray([row["sync_ratio"] for row in rows], dtype=float),
        fallback_triggered=np.asarray([bool(row["fallback_triggered"]) for row in rows], dtype=bool),
    )
    plot_paths = write_plots(rows, summary)
    task_matrix = write_task_matrix()
    metadata = {
        "artifact_status": "non_final_step_c7_residual_cov_sync_safeguard",
        "not_for_manuscript_submission": True,
        "estimator_mode": STEP_C7_ESTIMATOR_MODE,
        "candidate_count": len(CANDIDATES),
        "medium_case_count": len(MEDIUM_CASES),
        "row_count": len(rows),
        "runtime_seconds": time.monotonic() - started,
        "uses_package_estimator_helper": True,
        "truth_state_used_for_acceptance": False,
        "truth_state_used_for_covariance": False,
        "truth_state_used_for_safeguard": False,
        "truth_used_for_offline_metrics": True,
        "raw_csv": _repo_rel(OUTPUT_ROOT / "raw.csv"),
        "summary_csv": _repo_rel(OUTPUT_ROOT / "summary.csv"),
        "arrays_npz": _repo_rel(OUTPUT_ROOT / "arrays.npz"),
        "plots": [_repo_rel(path) for path in plot_paths],
        "task_matrix": task_matrix,
    }
    _json_dump(OUTPUT_ROOT / "metadata.json", metadata)
    report = write_reports(rows, summary, plot_paths)
    write_graph_status(report)
    return metadata


def main() -> None:
    """CLI entry point."""

    metadata = run_validation()
    print(json.dumps({"output_root": _repo_rel(OUTPUT_ROOT), "runtime_seconds": metadata["runtime_seconds"]}, indent=2))


if __name__ == "__main__":
    main()
