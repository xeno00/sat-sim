"""Sparse Step 3 gate exploration for legacy-compatible JCLS diagnostics.

This script evaluates a small set of observable Step 3 gate/covariance controls
against three representative network-size cases. It does not run the migration
ladder, does not execute manuscript figure workflows, and writes only non-final
diagnostics under ``outputs/step3_gate_exploration``.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


SAT_SIM_ROOT = Path(__file__).resolve().parents[1]
if str(SAT_SIM_ROOT) not in sys.path:
    sys.path.insert(0, str(SAT_SIM_ROOT))

from scripts.replay_legacy_clock_sweep_figures import NOTEBOOK_PATH, _execute_legacy_namespace, _selected_cell_hashes  # noqa: E402
from scripts.replay_legacy_network_size_figures import _mode_config  # noqa: E402
from scripts.run_controlled_migration_ladder import (  # noqa: E402
    STEP_B_COST_TOLERANCE,
    _install_residual_lm_acceptance,
    _parameter_update_norms,
    _repo_rel,
    _safe_inverse,
)


OUTPUT_ROOT = SAT_SIM_ROOT / "outputs" / "step3_gate_exploration"
REPORTS = SAT_SIM_ROOT / "outputs" / "reports"
CASES = [(3, 8), (7, 8), (7, 12)]
BASE_SEED = 240531
ALPHAS = [1.0, 0.5, 0.25, 0.125, 0.0625, 0.03125]
HUBER_THRESHOLD = 1.5
NIS_UPPER_MULTIPLIER = 3.0
NULLSPACE_RATIO_LIMIT = 0.40
CLOCK_POSITION_RATIO_LIMIT = 1.0


@dataclass(frozen=True)
class GateConfig:
    """Configuration for one sparse Step 3 gate experiment."""

    name: str
    use_nis_gate: bool = False
    use_nullspace_gate: bool = False
    use_clock_position_gate: bool = False
    use_huber_weighting: bool = False
    covariance_inflation: float = 1.0
    measurement_inflation: float = 1.0


GATES = [
    GateConfig("line_search"),
    GateConfig("nis_line_search", use_nis_gate=True),
    GateConfig("nullspace_line_search", use_nullspace_gate=True),
    GateConfig("clock_position_line_search", use_clock_position_gate=True),
    GateConfig("covariance_k10", covariance_inflation=10.0),
    GateConfig("covariance_k100", covariance_inflation=100.0),
    GateConfig("measurement_lambda10", measurement_inflation=10.0),
    GateConfig("covariance_k10_measurement_lambda10", covariance_inflation=10.0, measurement_inflation=10.0),
    GateConfig("huber_line_search", use_huber_weighting=True),
    GateConfig(
        "combined_nis_null_clock",
        use_nis_gate=True,
        use_nullspace_gate=True,
        use_clock_position_gate=True,
        covariance_inflation=10.0,
    ),
]


def _sha256(path: Path) -> str:
    """Return SHA256 for an existing file."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _case_seed(case_index: int) -> int:
    """Return deterministic seed for a representative case."""

    return BASE_SEED + 1009 * case_index


def _clock_indices(symbols: list[str]) -> list[int]:
    """Return all legacy clock-parameter indices."""

    return [idx for idx, symbol in enumerate(symbols) if "delta" in symbol]


def _position_indices(symbols: list[str]) -> list[int]:
    """Return all legacy position-parameter indices."""

    clock = set(_clock_indices(symbols))
    return [idx for idx in range(len(symbols)) if idx not in clock]


def _state_covariance(symbols: list[str], covariance_inflation: float) -> np.ndarray:
    """Return a conservative diagonal all-clock state covariance in km units."""

    variances = [
        0.1**2 if "delta" in symbol else 10.0**2
        for symbol in symbols
    ]
    return float(covariance_inflation) * np.diag(np.asarray(variances, dtype=float))


def _robust_measurement_covariance(residual: np.ndarray, covariance: np.ndarray) -> np.ndarray:
    """Return Huber-inflated covariance for large whitened residual entries."""

    diag = np.maximum(np.diag(covariance), 1.0e-18)
    whitened = np.abs(residual) / np.sqrt(diag)
    weights = np.ones_like(whitened)
    large = whitened > HUBER_THRESHOLD
    weights[large] = HUBER_THRESHOLD / np.maximum(whitened[large], 1.0e-18)
    return np.diag(diag / np.maximum(weights, 1.0e-6))


def _objective(scenario: Any, x: np.ndarray, z: np.ndarray, x_prior: np.ndarray, p_inv: np.ndarray, r_inv: np.ndarray) -> tuple[float, float, float]:
    """Return total, residual, and prior MAP objective terms."""

    residual = np.asarray(z - scenario.h(x), dtype=float)
    delta = np.asarray(x - x_prior, dtype=float)
    residual_cost = float(residual.T @ r_inv @ residual)
    prior_cost = float(delta.T @ p_inv @ delta)
    return residual_cost + prior_cost, residual_cost, prior_cost


def _nullspace_ratio(jacobian: np.ndarray, update: np.ndarray) -> tuple[float, float, float, int]:
    """Return observable/nullspace update norms and ratio from the local Jacobian."""

    if update.size == 0 or np.linalg.norm(update) == 0.0:
        return 0.0, 0.0, 0.0, int(np.linalg.matrix_rank(jacobian))
    _, singular_values, vh = np.linalg.svd(jacobian, full_matrices=True)
    tol = max(jacobian.shape) * np.finfo(float).eps * (singular_values[0] if singular_values.size else 1.0)
    rank = int(np.sum(singular_values > tol))
    basis = vh.T
    observable_basis = basis[:, :rank]
    null_basis = basis[:, rank:]
    observable = observable_basis @ (observable_basis.T @ update) if observable_basis.size else np.zeros_like(update)
    null_component = null_basis @ (null_basis.T @ update) if null_basis.size else np.zeros_like(update)
    observable_norm = float(np.linalg.norm(observable))
    null_norm = float(np.linalg.norm(null_component))
    ratio = null_norm / max(float(np.linalg.norm(update)), 1.0e-18)
    return observable_norm, null_norm, ratio, rank


def _evaluate_gate_update(scenario: Any, optimizer: Any, x_lm: np.ndarray, z: np.ndarray, gate: GateConfig) -> dict[str, Any]:
    """Evaluate one observable Step 3 gate candidate without truth-state gates."""

    symbols = [str(item) for item in scenario.symbolic_parameter_vector]
    covariance = _state_covariance(symbols, gate.covariance_inflation)
    measurement_covariance = float(gate.measurement_inflation) * np.asarray(scenario.get_measurement_covariance(), dtype=float)
    residual = np.asarray(z - scenario.h(x_lm), dtype=float)
    if gate.use_huber_weighting:
        measurement_covariance = _robust_measurement_covariance(residual, measurement_covariance)
    p_inv = _safe_inverse(covariance)
    r_inv = _safe_inverse(measurement_covariance)
    jacobian = np.asarray(scenario.evaluate_jacobian(x_lm), dtype=float)
    innovation_covariance = jacobian @ covariance @ jacobian.T + measurement_covariance
    innovation_precision = np.linalg.pinv(innovation_covariance)
    nis = float(residual.T @ innovation_precision @ residual)
    nis_upper = NIS_UPPER_MULTIPLIER * float(len(residual))
    gain = covariance @ jacobian.T @ innovation_precision
    update = np.asarray(gain @ residual, dtype=float)
    observable_norm, null_norm, null_ratio, jacobian_rank = _nullspace_ratio(jacobian, update)
    norm_status = _parameter_update_norms(scenario, update, x_lm)
    clock_position_ratio = (norm_status["clock_update_norm"] or 0.0) / max(norm_status["position_update_norm"] or 0.0, 1.0e-18)
    current_total, current_residual, current_prior = _objective(scenario, x_lm, z, x_lm, p_inv, r_inv)

    pre_line_reasons: list[str] = []
    if gate.use_nis_gate and nis > nis_upper:
        pre_line_reasons.append("nis_above_upper_bound")
    if gate.use_nullspace_gate and null_ratio > NULLSPACE_RATIO_LIMIT:
        pre_line_reasons.append("nullspace_ratio_exceeded")
    if gate.use_clock_position_gate and clock_position_ratio > CLOCK_POSITION_RATIO_LIMIT:
        pre_line_reasons.append("clock_position_update_ratio_exceeded")

    alpha_history = []
    chosen_alpha = 0.0
    accepted = False
    final_x = np.asarray(x_lm, dtype=float)
    final_total = current_total
    final_residual = current_residual
    final_prior = current_prior
    final_reasons = list(pre_line_reasons)
    if not pre_line_reasons:
        for alpha in ALPHAS:
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
                chosen_alpha = alpha
                accepted = True
                final_x = candidate
                final_total = candidate_total
                final_residual = candidate_residual
                final_prior = candidate_prior
                break
        if not accepted:
            final_reasons = sorted({reason for item in alpha_history for reason in item["rejection_reasons"]})

    before_position_error_m = float(optimizer.calculate_average_position_error(scenario, x_lm))
    before_sync_error_s = float(optimizer.calculate_average_clock_error(scenario, x_lm))
    after_position_error_m = float(optimizer.calculate_average_position_error(scenario, final_x))
    after_sync_error_s = float(optimizer.calculate_average_clock_error(scenario, final_x))
    return {
        "gate_name": gate.name,
        "gate": asdict(gate),
        "accepted": bool(accepted),
        "chosen_alpha": chosen_alpha,
        "rejection_reasons": final_reasons,
        "nis": nis,
        "nis_upper_bound": nis_upper,
        "jacobian_rank": jacobian_rank,
        "observable_update_norm": observable_norm,
        "nullspace_update_norm": null_norm,
        "nullspace_ratio": null_ratio,
        "update_norm": float(np.linalg.norm(update)),
        "position_update_norm": norm_status["position_update_norm"],
        "clock_update_norm": norm_status["clock_update_norm"],
        "clock_position_update_ratio": clock_position_ratio,
        "current_total_objective": current_total,
        "final_total_objective": final_total,
        "current_residual_cost": current_residual,
        "final_residual_cost": final_residual,
        "current_prior_cost": current_prior,
        "final_prior_cost": final_prior,
        "alpha_history": alpha_history,
        "position_error_before_m": before_position_error_m,
        "position_error_after_m": after_position_error_m,
        "sync_error_before_s": before_sync_error_s,
        "sync_error_after_s": after_sync_error_s,
        "position_error_ratio": after_position_error_m / before_position_error_m if before_position_error_m > 0 else float("nan"),
        "sync_error_ratio": after_sync_error_s / before_sync_error_s if before_sync_error_s > 0 else float("nan"),
        "position_improved": bool(after_position_error_m < before_position_error_m),
        "sync_improved": bool(after_sync_error_s < before_sync_error_s),
        "both_improved": bool(after_position_error_m < before_position_error_m and after_sync_error_s < before_sync_error_s),
        "truth_state_used_for_acceptance": False,
        "truth_state_used_for_diagnostics": True,
    }


def _baseline_cache_path(num_users: int, num_satellites: int, seed: int) -> Path:
    """Return row-level baseline cache path."""

    return OUTPUT_ROOT / "cache" / f"baseline_Nu{num_users}_Ns{num_satellites}_seed{seed}.npz"


def _load_or_compute_baseline(namespace: dict[str, Any], num_users: int, num_satellites: int, seed: int, use_cache: bool) -> dict[str, Any]:
    """Return Step-B/LM-only baseline state and scenario for a sparse case."""

    Scenario = namespace["Scenario"]
    Optimizer = namespace["Optimizer"]
    config = _mode_config("medium")
    np.random.seed(seed)
    scenario = Scenario(num_users=num_users, num_satellites=num_satellites, clock_std_dev_seconds=float(config["clock_std_dev"]))
    optimizer = Optimizer()
    cache_path = _baseline_cache_path(num_users, num_satellites, seed)
    if use_cache and cache_path.exists():
        cached = np.load(cache_path, allow_pickle=True)
        return {
            "scenario": scenario,
            "optimizer": optimizer,
            "x_il": cached["x_il"],
            "x_lm": cached["x_lm"],
            "z_step3": cached["z_step3"],
            "il_position_error_m": float(cached["il_position_error_m"]),
            "il_sync_error_s": float(cached["il_sync_error_s"]),
            "lm_position_error_m": float(cached["lm_position_error_m"]),
            "lm_sync_error_s": float(cached["lm_sync_error_s"]),
            "cache_used": True,
        }
    x_init = optimizer.initialize_state(scenario, error_range=float(config["error_range"]))
    z0 = scenario.query_measurements()
    x_il = optimizer.run(algorithm="IL", scenario=scenario, x=x_init, z=z0, num_steps=15, tol=1.0e-8, verbose=False)
    x_lm = optimizer.run(algorithm="LM", scenario=scenario, x=x_il, z=z0, num_steps=20, verbose=False)
    z_step3 = scenario.query_measurements()
    il_position = float(optimizer.calculate_average_position_error(scenario, x_il))
    il_sync = float(optimizer.calculate_average_clock_error(scenario, x_il))
    lm_position = float(optimizer.calculate_average_position_error(scenario, x_lm))
    lm_sync = float(optimizer.calculate_average_clock_error(scenario, x_lm))
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        cache_path,
        x_il=x_il,
        x_lm=x_lm,
        z_step3=z_step3,
        il_position_error_m=il_position,
        il_sync_error_s=il_sync,
        lm_position_error_m=lm_position,
        lm_sync_error_s=lm_sync,
        symbolic_parameter_order=np.asarray([str(item) for item in scenario.symbolic_parameter_vector], dtype=object),
    )
    return {
        "scenario": scenario,
        "optimizer": optimizer,
        "x_il": x_il,
        "x_lm": x_lm,
        "z_step3": z_step3,
        "il_position_error_m": il_position,
        "il_sync_error_s": il_sync,
        "lm_position_error_m": lm_position,
        "lm_sync_error_s": lm_sync,
        "cache_used": False,
    }


def _planned_rows(max_cases: int | None = None, max_gates: int | None = None) -> list[dict[str, Any]]:
    """Return the sparse exploration rows that would be evaluated."""

    cases = CASES[:max_cases] if max_cases is not None else CASES
    gates = GATES[:max_gates] if max_gates is not None else GATES
    return [
        {"num_users": num_users, "num_satellites": num_satellites, "gate_name": gate.name}
        for num_users, num_satellites in cases
        for gate in gates
    ]


def _write_csv(rows: list[dict[str, Any]]) -> str:
    """Write raw gate exploration CSV."""

    path = OUTPUT_ROOT / "step3_gate_exploration_raw.csv"
    fieldnames = [
        "case_name",
        "num_users",
        "num_satellites",
        "gate_name",
        "accepted",
        "chosen_alpha",
        "nis",
        "nis_upper_bound",
        "jacobian_rank",
        "observable_update_norm",
        "nullspace_update_norm",
        "nullspace_ratio",
        "update_norm",
        "position_update_norm",
        "clock_update_norm",
        "clock_position_update_ratio",
        "current_total_objective",
        "final_total_objective",
        "current_residual_cost",
        "final_residual_cost",
        "current_prior_cost",
        "final_prior_cost",
        "il_position_error_m",
        "lm_position_error_m",
        "position_error_after_m",
        "il_sync_error_s",
        "lm_sync_error_s",
        "sync_error_after_s",
        "position_error_ratio",
        "sync_error_ratio",
        "position_improved",
        "sync_improved",
        "both_improved",
        "baseline_cache_used",
        "rejection_reasons",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            record = {key: row.get(key) for key in fieldnames}
            record["rejection_reasons"] = json.dumps(row.get("rejection_reasons", []))
            writer.writerow(record)
    return _repo_rel(path)


def _write_json(path: Path, payload: dict[str, Any]) -> str:
    """Write JSON and return repo-relative path."""

    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return _repo_rel(path)


def _plot_scatter(rows: list[dict[str, Any]], x_key: str, y_key: str, xlabel: str, ylabel: str, filename: str) -> list[str]:
    """Write one scatter plot as PDF and PNG."""

    fig, ax = plt.subplots(figsize=(4.8, 3.5), dpi=220)
    for gate in GATES:
        subset = [row for row in rows if row["gate_name"] == gate.name]
        if not subset:
            continue
        ax.scatter([row[x_key] for row in subset], [row[y_key] for row in subset], s=28, label=gate.name)
    ax.axhline(1.0, color="0.5", linewidth=0.8, linestyle="--")
    if y_key != "sync_error_ratio":
        ax.axhline(0.0, color="0.8", linewidth=0.8)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=5, ncol=2, frameon=True)
    fig.tight_layout()
    pdf = OUTPUT_ROOT / f"{filename}.pdf"
    png = OUTPUT_ROOT / f"{filename}.png"
    fig.savefig(pdf)
    fig.savefig(png)
    plt.close(fig)
    return [_repo_rel(pdf), _repo_rel(png)]


def _plot_bars(rows: list[dict[str, Any]]) -> list[str]:
    """Write per-gate count of rows where both metrics improved."""

    counts = [sum(1 for row in rows if row["gate_name"] == gate.name and row["both_improved"]) for gate in GATES]
    fig, ax = plt.subplots(figsize=(6.2, 3.6), dpi=220)
    ax.bar(range(len(GATES)), counts)
    ax.set_xticks(range(len(GATES)))
    ax.set_xticklabels([gate.name for gate in GATES], rotation=45, ha="right", fontsize=6)
    ax.set_ylabel("Both-improved row count")
    ax.set_ylim(0, len(CASES))
    ax.grid(True, axis="y", alpha=0.25)
    fig.tight_layout()
    pdf = OUTPUT_ROOT / "gate_both_improved_bar.pdf"
    png = OUTPUT_ROOT / "gate_both_improved_bar.png"
    fig.savefig(pdf)
    fig.savefig(png)
    plt.close(fig)
    return [_repo_rel(pdf), _repo_rel(png)]


def _write_plots(rows: list[dict[str, Any]]) -> list[str]:
    """Write compact diagnostic plots."""

    outputs: list[str] = []
    outputs.extend(_plot_scatter(rows, "position_error_ratio", "sync_error_ratio", "Position-error ratio after/before", "Sync-error ratio after/before", "position_sync_ratio_scatter"))
    outputs.extend(_plot_scatter(rows, "update_norm", "position_error_ratio", "Update norm", "Position-error ratio", "update_norm_vs_error_improvement"))
    outputs.extend(_plot_scatter(rows, "nullspace_ratio", "position_error_ratio", "Nullspace update ratio", "Position-error ratio", "nullspace_ratio_vs_error_improvement"))
    outputs.extend(_plot_scatter(rows, "nis", "position_error_ratio", "NIS", "Position-error ratio", "nis_vs_error_improvement"))
    outputs.extend(_plot_bars(rows))
    return outputs


def run_exploration(*, use_cache: bool = True, max_cases: int | None = None, max_gates: int | None = None) -> dict[str, Any]:
    """Run the sparse Step 3 gate exploration."""

    started = time.monotonic()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    namespace, _executed_cells = _execute_legacy_namespace()
    _install_residual_lm_acceptance(namespace)
    rows: list[dict[str, Any]] = []
    objective_history_rows = []
    update_diagnostic_rows = []
    cases = CASES[:max_cases] if max_cases is not None else CASES
    gates = GATES[:max_gates] if max_gates is not None else GATES
    for case_index, (num_users, num_satellites) in enumerate(cases):
        seed = _case_seed(case_index)
        baseline = _load_or_compute_baseline(namespace, num_users, num_satellites, seed, use_cache)
        case_name = f"Nu{num_users}_Ns{num_satellites}"
        for gate in gates:
            result = _evaluate_gate_update(
                baseline["scenario"],
                baseline["optimizer"],
                baseline["x_lm"],
                baseline["z_step3"],
                gate,
            )
            result.update(
                {
                    "case_name": case_name,
                    "num_users": num_users,
                    "num_satellites": num_satellites,
                    "seed": seed,
                    "il_position_error_m": baseline["il_position_error_m"],
                    "lm_position_error_m": baseline["lm_position_error_m"],
                    "il_sync_error_s": baseline["il_sync_error_s"],
                    "lm_sync_error_s": baseline["lm_sync_error_s"],
                    "baseline_cache_used": bool(baseline["cache_used"]),
                }
            )
            rows.append(result)
            objective_history_rows.append(
                {
                    "case_name": case_name,
                    "gate_name": gate.name,
                    "alpha_history": result["alpha_history"],
                    "current_total_objective": result["current_total_objective"],
                    "final_total_objective": result["final_total_objective"],
                }
            )
            update_diagnostic_rows.append(
                {
                    key: result[key]
                    for key in [
                        "case_name",
                        "gate_name",
                        "nis",
                        "nis_upper_bound",
                        "observable_update_norm",
                        "nullspace_update_norm",
                        "nullspace_ratio",
                        "clock_position_update_ratio",
                        "update_norm",
                        "position_update_norm",
                        "clock_update_norm",
                        "chosen_alpha",
                        "accepted",
                        "rejection_reasons",
                        "position_error_ratio",
                        "sync_error_ratio",
                        "position_improved",
                        "sync_improved",
                        "both_improved",
                        "truth_state_used_for_acceptance",
                        "truth_state_used_for_diagnostics",
                    ]
                }
            )
    raw_csv = _write_csv(rows)
    objective_history = _write_json(
        OUTPUT_ROOT / "objective_history.json",
        {
            "artifact_status": "non_final_step3_gate_objective_history",
            "manuscript_ready": False,
            "rows": objective_history_rows,
        },
    )
    update_diagnostics = _write_json(
        OUTPUT_ROOT / "update_diagnostics.json",
        {
            "artifact_status": "non_final_step3_gate_update_diagnostics",
            "manuscript_ready": False,
            "rows": update_diagnostic_rows,
        },
    )
    plots = _write_plots(rows)
    gate_summaries = []
    for gate in gates:
        subset = [row for row in rows if row["gate_name"] == gate.name]
        gate_summaries.append(
            {
                "gate_name": gate.name,
                "tested_rows": len(subset),
                "accepted_rows": sum(1 for row in subset if row["accepted"]),
                "position_improved_rows": sum(1 for row in subset if row["position_improved"]),
                "sync_improved_rows": sum(1 for row in subset if row["sync_improved"]),
                "both_improved_rows": sum(1 for row in subset if row["both_improved"]),
                "mean_position_error_ratio": float(np.mean([row["position_error_ratio"] for row in subset])) if subset else None,
                "mean_sync_error_ratio": float(np.mean([row["sync_error_ratio"] for row in subset])) if subset else None,
            }
        )
    best_position = min(gate_summaries, key=lambda item: item["mean_position_error_ratio"] if item["mean_position_error_ratio"] is not None else float("inf"), default=None)
    best_sync = min(gate_summaries, key=lambda item: item["mean_sync_error_ratio"] if item["mean_sync_error_ratio"] is not None else float("inf"), default=None)
    best_both = max(gate_summaries, key=lambda item: item["both_improved_rows"], default=None)
    promising = [
        item["gate_name"]
        for item in gate_summaries
        if item["both_improved_rows"] == len(cases) and item["tested_rows"] == len(cases)
    ]
    runtime = time.monotonic() - started
    metadata = {
        "artifact_status": "non_final_step3_gate_exploration",
        "manuscript_ready": False,
        "not_for_manuscript_submission": True,
        "branch_policy": "sparse_cases_only_no_full_ladder",
        "cases": [{"num_users": users, "num_satellites": sats, "seed": _case_seed(idx)} for idx, (users, sats) in enumerate(cases)],
        "gates": [asdict(gate) for gate in gates],
        "row_count": len(rows),
        "raw_csv": raw_csv,
        "objective_history_json": objective_history,
        "update_diagnostics_json": update_diagnostics,
        "plots": plots,
        "runtime_seconds": runtime,
        "truth_state_used_for_acceptance": False,
        "truth_state_used_for_diagnostics": True,
        "notebook_sha256": _sha256(NOTEBOOK_PATH),
        "extracted_cell_hashes": _selected_cell_hashes(),
        "best_gate_for_position": best_position,
        "best_gate_for_sync": best_sync,
        "best_gate_for_both": best_both,
        "promising_gates_for_medium_validation": promising,
        "medium_validation_run": False,
        "medium_validation_reason": "No gate improved both position and synchronization in all sparse cases." if not promising else "Promising gates identified but medium validation is intentionally deferred for review.",
        "gate_summaries": gate_summaries,
    }
    metadata_path = _write_json(OUTPUT_ROOT / "metadata.json", metadata)
    report = {
        **metadata,
        "metadata_json": metadata_path,
        "rows": rows,
    }
    _write_json(OUTPUT_ROOT / "step3_gate_exploration_results.json", report)
    _write_report(report)
    return report


def _write_report(payload: dict[str, Any]) -> None:
    """Write Markdown/JSON top-level report."""

    REPORTS.mkdir(parents=True, exist_ok=True)
    report_json = REPORTS / "STEP3_GATE_EXPLORATION_REPORT.json"
    report_md = REPORTS / "STEP3_GATE_EXPLORATION_REPORT.md"
    report_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md = [
        "# Step 3 Gate Exploration Report",
        "",
        "## Executive Summary",
        "",
        "- Artifact status: `non_final_step3_gate_exploration`",
        f"- Cases tested: `{[(case['num_users'], case['num_satellites']) for case in payload['cases']]}`",
        f"- Gates tested: `{[gate['name'] for gate in payload['gates']]}`",
        f"- Runtime seconds: `{payload['runtime_seconds']:.3f}`",
        f"- Best gate for position: `{payload['best_gate_for_position']['gate_name'] if payload['best_gate_for_position'] else None}`",
        f"- Best gate for sync: `{payload['best_gate_for_sync']['gate_name'] if payload['best_gate_for_sync'] else None}`",
        f"- Best gate for both: `{payload['best_gate_for_both']['gate_name'] if payload['best_gate_for_both'] else None}`",
        f"- Promising gates for medium validation: `{payload['promising_gates_for_medium_validation']}`",
        f"- Medium validation run: `{payload['medium_validation_run']}`",
        "",
        "## Interpretation",
        "",
        "Truth state is used only for diagnostic error labels after each candidate update; it is not used for acceptance, covariance, or fallback decisions.",
        "Sparse exploration is intended to identify candidate gates, not to validate manuscript figures.",
        "",
        "## Gate Summary",
        "",
        "| Gate | Accepted | Position improved | Sync improved | Both improved | Mean pos ratio | Mean sync ratio |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for item in payload["gate_summaries"]:
        md.append(
            f"| `{item['gate_name']}` | {item['accepted_rows']}/{item['tested_rows']} | "
            f"{item['position_improved_rows']}/{item['tested_rows']} | {item['sync_improved_rows']}/{item['tested_rows']} | "
            f"{item['both_improved_rows']}/{item['tested_rows']} | {item['mean_position_error_ratio']:.6g} | {item['mean_sync_error_ratio']:.6g} |"
        )
    md += [
        "",
        "## Output Paths",
        "",
        f"- Raw CSV: `{payload['raw_csv']}`",
        f"- Metadata JSON: `{payload['metadata_json']}`",
        f"- Objective history: `{payload['objective_history_json']}`",
        f"- Update diagnostics: `{payload['update_diagnostics_json']}`",
        "- Plots:",
        *[f"  - `{path}`" for path in payload["plots"]],
    ]
    report_md.write_text("\n".join(md) + "\n", encoding="utf-8")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI options."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="List planned sparse rows without executing.")
    parser.add_argument("--list-planned-work", action="store_true", help="Print planned sparse rows without executing.")
    parser.add_argument("--no-cache", action="store_true", help="Ignore row-level baseline cache.")
    parser.add_argument("--max-cases", type=int, default=None, help="Limit representative cases for tests/debugging.")
    parser.add_argument("--max-gates", type=int, default=None, help="Limit gate modes for tests/debugging.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> dict[str, Any]:
    """CLI entrypoint."""

    args = _parse_args(argv)
    planned = {
        "artifact_status": "non_final_step3_gate_exploration_planned_work",
        "will_execute": not (args.dry_run or args.list_planned_work),
        "row_count": len(_planned_rows(args.max_cases, args.max_gates)),
        "planned_rows": _planned_rows(args.max_cases, args.max_gates),
        "default_is_sparse_only": True,
        "full_ladder_run": False,
    }
    print(json.dumps(planned, indent=2))
    if args.dry_run or args.list_planned_work:
        return planned
    payload = run_exploration(use_cache=not args.no_cache, max_cases=args.max_cases, max_gates=args.max_gates)
    print(json.dumps({"status": "wrote", "output_root": _repo_rel(OUTPUT_ROOT), "row_count": payload["row_count"]}, indent=2))
    return payload


if __name__ == "__main__":
    main()
