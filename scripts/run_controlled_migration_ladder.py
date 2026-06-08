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
from scripts.replay_legacy_clock_sweep_figures import NOTEBOOK_PATH, _execute_legacy_namespace, _hash_file, _selected_cell_hashes  # noqa: E402
from scripts.replay_legacy_network_size_figures import CACHE_SCHEMA_VERSION as NETWORK_CACHE_SCHEMA  # noqa: E402
from scripts.replay_legacy_network_size_figures import _mode_config  # noqa: E402


BASELINE_ROOT = SAT_SIM_ROOT / "outputs" / "migration_baseline" / "legacy_behavior_freeze"
LADDER_ROOT = SAT_SIM_ROOT / "outputs" / "migration_ladder"
REPORTS = SAT_SIM_ROOT / "outputs" / "reports"
MIGRATION_CACHE_ROOT = SAT_SIM_ROOT / "outputs" / "cache" / "migration_ladder"
SOURCE_NETWORK_ROOT = SAT_SIM_ROOT / "outputs" / "legacy_replay" / "network_size_medium"
SOURCE_CLOCK_ROOT = SAT_SIM_ROOT / "outputs" / "legacy_replay" / "clock_sweep_full"
MIGRATION_CACHE_SCHEMA_VERSION = "controlled-migration-ladder-v1"
STEP_B_NAME = "step_b_lm_residual_acceptance"
STEP_B_STEP_NORM_LIMIT = 1.0e6
STEP_B_COST_TOLERANCE = 1.0e-9


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


def _safe_inverse(matrix: np.ndarray) -> np.ndarray:
    """Return an inverse, falling back to a pseudoinverse for singular inputs."""

    try:
        return np.linalg.inv(matrix)
    except np.linalg.LinAlgError:
        return np.linalg.pinv(matrix)


def _residual_cost(scenario: Any, x: np.ndarray, z: np.ndarray) -> float:
    """Return weighted residual cost using observable model quantities only."""

    residual = np.asarray(z - scenario.h(x), dtype=float)
    covariance = np.asarray(scenario.get_measurement_covariance(), dtype=float)
    precision = _safe_inverse(covariance)
    return float(residual.T @ precision @ residual)


def _install_residual_lm_acceptance(namespace: dict[str, Any]) -> None:
    """Patch the extracted legacy Optimizer with residual-only LM acceptance."""

    Optimizer = namespace["Optimizer"]
    original_run = Optimizer.run

    def lm_step_residual_trust_region(self: Any, scenario: Any, x: np.ndarray, z: np.ndarray, damping_factor: float, nu: float) -> tuple[np.ndarray, float, float, bool]:
        h_x = np.asarray(scenario.h(x), dtype=float)
        J_x = np.asarray(scenario.evaluate_jacobian(x), dtype=float)
        covariance = np.asarray(scenario.get_measurement_covariance(), dtype=float)
        self.check_step_inputs(x, h_x, J_x, z, covariance)

        precision = _safe_inverse(covariance)
        residual = np.asarray(z - h_x, dtype=float)
        current_cost = float(residual.T @ precision @ residual)
        normal_matrix = J_x.T @ precision @ J_x
        gradient = J_x.T @ precision @ residual
        damping_matrix = damping_factor * np.eye(x.shape[0])
        step = _safe_inverse(normal_matrix + damping_matrix) @ gradient
        x_new = np.asarray(x + step, dtype=float)
        step_norm = float(np.linalg.norm(step))
        relative_step_norm = step_norm / max(1.0, float(np.linalg.norm(x)))

        reasons: list[str] = []
        finite_candidate = bool(np.all(np.isfinite(x_new)))
        if not finite_candidate:
            reasons.append("nonfinite_candidate")
        bounded_step = bool(np.isfinite(relative_step_norm) and relative_step_norm <= STEP_B_STEP_NORM_LIMIT)
        if not bounded_step:
            reasons.append("relative_step_norm_exceeded")

        if finite_candidate:
            residual_new = np.asarray(z - scenario.h(x_new), dtype=float)
            candidate_cost = float(residual_new.T @ precision @ residual_new)
        else:
            candidate_cost = float("inf")
        finite_costs = bool(np.isfinite(current_cost) and np.isfinite(candidate_cost))
        if not finite_costs:
            reasons.append("nonfinite_residual_cost")

        predicted_denominator = float(step.T @ (damping_matrix @ step + gradient))
        rho = (
            float((current_cost - candidate_cost) / predicted_denominator)
            if np.isfinite(predicted_denominator) and abs(predicted_denominator) > 0.0
            else float("nan")
        )
        residual_decreased = bool(candidate_cost <= current_cost + STEP_B_COST_TOLERANCE * max(1.0, abs(current_cost)))
        if not residual_decreased:
            reasons.append("residual_cost_increased")
        positive_trust_ratio = bool(np.isfinite(rho) and rho > 0.0)
        if not positive_trust_ratio:
            reasons.append("nonpositive_trust_ratio")

        accepted = bool(finite_candidate and bounded_step and finite_costs and residual_decreased and positive_trust_ratio)
        if accepted:
            next_x = x_new
            next_damping = damping_factor * max(1.0 / 3.0, 1.0 - (2.0 * rho - 1.0) ** 3)
            next_nu = 2.0
        else:
            next_x = x
            next_damping = damping_factor * nu
            next_nu = 2.0 * nu

        trace = getattr(self, "_step_b_lm_trace", [])
        trace.append(
            {
                "iteration": len(trace),
                "accepted": accepted,
                "current_residual_cost": current_cost,
                "candidate_residual_cost": candidate_cost,
                "cost_decrease": current_cost - candidate_cost if finite_costs else None,
                "damping_before": float(damping_factor),
                "damping_after": float(next_damping),
                "nu_before": float(nu),
                "nu_after": float(next_nu),
                "rho": rho,
                "step_norm": step_norm,
                "relative_step_norm": relative_step_norm,
                "rejection_reasons": reasons,
            }
        )
        self._step_b_lm_trace = trace
        self._truth_state_used_for_lm_acceptance = False
        return next_x, next_damping, next_nu, accepted

    def run_residual_lm(self: Any, algorithm: str, scenario: Any, x: np.ndarray, z: np.ndarray, num_steps: int = 10, tol: float = 1e-10, lr: float = 1e14, verbose: bool = False) -> np.ndarray:
        if algorithm != "LM":
            return original_run(self, algorithm, scenario, x, z, num_steps=num_steps, tol=tol, lr=lr, verbose=verbose)

        import warnings

        assert len(x) == len(scenario.symbolic_parameter_vector)
        assert len(z) == len(scenario.get_links())
        x = np.asarray(x, dtype=float)
        self._step_b_lm_trace = []
        self._truth_state_used_for_lm_acceptance = False
        initial_cost = _residual_cost(scenario, x, z)
        damp = 1.5
        nu = 1.9
        converged = False
        updated = False
        for iteration in range(num_steps + 1):
            x_new, damp, nu, updated = self.lm_step(scenario=scenario, x=x, z=z, damping_factor=damp, nu=nu)
            if self.converged(x, x_new, tol=tol) and updated:
                converged = True
                x = x_new
                break
            x = x_new
        else:
            warnings.warn(f"Maximum number of iterations reached without convergence for: {algorithm}, {num_steps}", RuntimeWarning)

        final_cost = _residual_cost(scenario, x, z)
        if not np.all(np.isfinite(x)) or not np.isfinite(final_cost):
            raise ValueError(algorithm, "encountered nonfinite residual-gated output")
        accepted_steps = sum(1 for item in self._step_b_lm_trace if item["accepted"])
        rejected_steps = len(self._step_b_lm_trace) - accepted_steps
        self._last_lm_diagnostics = {
            "lm_acceptance_mode": "residual_trust_region",
            "truth_state_used_for_lm_acceptance": False,
            "initial_residual_cost": float(initial_cost),
            "final_residual_cost": float(final_cost),
            "cost_decrease": float(initial_cost - final_cost),
            "accepted_step_count": int(accepted_steps),
            "rejected_step_count": int(rejected_steps),
            "final_damping": float(damp),
            "convergence_status": "converged" if converged else "max_iterations_reached",
            "iteration_count": len(self._step_b_lm_trace),
            "rejection_reasons": [
                reason
                for item in self._step_b_lm_trace
                for reason in item["rejection_reasons"]
            ],
            "step_trace": self._step_b_lm_trace,
        }
        return np.asarray(x, dtype=float)

    Optimizer.lm_step = lm_step_residual_trust_region
    Optimizer.run = run_residual_lm


def _scenario_result_step_b(
    *,
    namespace: dict[str, Any],
    config: dict[str, Any],
    num_users: int,
    num_satellites: int,
) -> dict[str, Any]:
    """Run one Step B row with residual-gated LM acceptance."""

    Scenario = namespace["Scenario"]
    Optimizer = namespace["Optimizer"]
    global_map_filter_iteration = namespace["map_filter_iteration"]
    row: dict[str, Any] = {
        "num_users": int(num_users),
        "num_satellites": int(num_satellites),
        "clock_std_dev_seconds": float(config["clock_std_dev"]),
        "map_iteration_count": 0 if int(num_users) == 1 else int(config["num_iterations"]),
        "truth_centered_initialization": False,
        "true_state_acceptance_gates_used": False,
        "truth_state_used_for_lm_acceptance": False,
        "lm_acceptance_mode": "residual_trust_region",
        "all_clock_state": True,
        "v24_gauged_state": False,
        "fallbacks": [],
        "failures": [],
    }
    scenario = Scenario(
        num_users=int(num_users),
        num_satellites=int(num_satellites),
        clock_std_dev_seconds=float(config["clock_std_dev"]),
    )
    optimizer = Optimizer()
    x_init = optimizer.initialize_state(scenario, error_range=float(config["error_range"]))
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
    except Exception as exc:  # noqa: BLE001 - preserve legacy broad fallback behavior.
        x_il = x_init.copy()
        row["il_status"] = "failed_fallback_to_initial_state"
        row["failures"].append({"stage": "IL", "error_type": type(exc).__name__, "error": str(exc)})
        row["fallbacks"].append("IL_failed_to_initial_state")
    row["il_position_error_m"] = float(optimizer.calculate_average_position_error(scenario, x_il))
    row["il_sync_error_s"] = float(optimizer.calculate_average_clock_error(scenario, x_il))

    if int(num_users) == 1:
        row["single_ue_policy"] = config["single_ue_policy"]
        row["cooperative_jcls_attempted"] = False
        row["lm_status"] = "not_attempted_single_ue_baseline"
        row["map_status"] = "not_attempted_single_ue_baseline"
        row["lm_position_error_m"] = row["il_position_error_m"]
        row["map_position_error_m"] = row["il_position_error_m"]
        row["lm_sync_error_s"] = row["il_sync_error_s"]
        row["map_sync_error_s"] = row["il_sync_error_s"]
        row["success"] = bool(row["il_status"] == "passed")
        row["fallbacks"].append({"stage": "LM/MAP", "reason": "single_ue_noncooperative_baseline_only"})
        row["lm_diagnostics"] = {
            "lm_acceptance_mode": "not_attempted_single_ue_baseline",
            "truth_state_used_for_lm_acceptance": False,
            "accepted_step_count": 0,
            "rejected_step_count": 0,
            "initial_residual_cost": None,
            "final_residual_cost": None,
            "cost_decrease": None,
            "final_damping": None,
            "convergence_status": "not_attempted",
            "rejection_reasons": [],
            "step_trace": [],
        }
        row["fallback_count"] = len(row["fallbacks"])
        row["failure_count"] = len(row["failures"])
        row["cache_used"] = False
        return row

    row["single_ue_policy"] = "not_applicable"
    row["cooperative_jcls_attempted"] = True
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
    except Exception as exc:  # noqa: BLE001 - preserve legacy LM fallback shape.
        x_lm = x_il.copy()
        row["lm_status"] = "failed_fallback_to_il"
        row["failures"].append({"stage": "LM", "error_type": type(exc).__name__, "error": str(exc)})
        row["fallbacks"].append("LM_failed_to_IL")
    lm_diagnostics = getattr(optimizer, "_last_lm_diagnostics", {
        "lm_acceptance_mode": "residual_trust_region",
        "truth_state_used_for_lm_acceptance": False,
        "accepted_step_count": 0,
        "rejected_step_count": 0,
        "initial_residual_cost": None,
        "final_residual_cost": None,
        "cost_decrease": None,
        "final_damping": None,
        "convergence_status": "not_recorded",
        "rejection_reasons": [],
        "step_trace": [],
    })
    row["lm_diagnostics"] = lm_diagnostics
    row["lm_position_error_m"] = float(optimizer.calculate_average_position_error(scenario, x_lm))
    row["lm_sync_error_s"] = float(optimizer.calculate_average_clock_error(scenario, x_lm))

    x_map = x_lm.copy()
    p_matrix = optimizer.calculate_state_covariance(scenario, x_lm) / 1.1
    map_fallback_count = 0
    map_failure_count = 0
    for iteration in range(int(config["num_iterations"])):
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
    row["fallback_count"] = len(row["fallbacks"])
    row["failure_count"] = len(row["failures"])
    row["cache_used"] = False
    return row


def _run_step_b_rows(grid: str) -> list[dict[str, Any]]:
    """Run Step B rows for the requested tiny or medium grid."""

    config = _mode_config("medium")
    if grid == "tiny":
        users = [1, 3]
        satellites = [4, 8]
    elif grid == "medium":
        users = [1, 3, 5, 7]
        satellites = [4, 8, 12]
    else:
        raise ValueError(f"unknown Step B grid: {grid}")
    np.random.seed(int(config["seed"]))
    namespace, _executed_cells = _execute_legacy_namespace()
    _install_residual_lm_acceptance(namespace)
    rows = []
    for user in users:
        for sat in satellites:
            rows.append(_scenario_result_step_b(namespace=namespace, config=config, num_users=user, num_satellites=sat))
    return rows


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
        "measurement_count",
        "state_dimension",
        "cooperative_jcls_attempted",
        "il_position_error_m",
        "lm_position_error_m",
        "map_position_error_m",
        "il_sync_error_s",
        "lm_sync_error_s",
        "map_sync_error_s",
        "fallback_count",
        "failure_count",
        "success",
        "single_ue_policy",
        "lm_acceptance_mode",
        "truth_state_used_for_lm_acceptance",
        "lm_initial_residual_cost",
        "lm_final_residual_cost",
        "lm_cost_decrease",
        "lm_final_damping",
        "lm_convergence_status",
        "lm_accepted_step_count",
        "lm_rejected_step_count",
        "lm_rejection_reasons",
    ]
    with raw.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            lm = row.get("lm_diagnostics", {})
            record = {key: row.get(key) for key in fieldnames}
            record.update(
                {
                    "lm_acceptance_mode": lm.get("lm_acceptance_mode"),
                    "truth_state_used_for_lm_acceptance": lm.get("truth_state_used_for_lm_acceptance"),
                    "lm_initial_residual_cost": lm.get("initial_residual_cost"),
                    "lm_final_residual_cost": lm.get("final_residual_cost"),
                    "lm_cost_decrease": lm.get("cost_decrease"),
                    "lm_final_damping": lm.get("final_damping"),
                    "lm_convergence_status": lm.get("convergence_status"),
                    "lm_accepted_step_count": lm.get("accepted_step_count"),
                    "lm_rejected_step_count": lm.get("rejected_step_count"),
                    "lm_rejection_reasons": json.dumps(lm.get("rejection_reasons", [])),
                }
            )
            writer.writerow(record)
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
    def _float_or_nan(value: Any) -> float:
        return float(value) if value is not None else float("nan")

    np.savez(
        path,
        num_users=np.asarray([row["num_users"] for row in rows], dtype=int),
        num_satellites=np.asarray([row["num_satellites"] for row in rows], dtype=int),
        lm_accepted_step_count=np.asarray([row.get("lm_diagnostics", {}).get("accepted_step_count", 0) or 0 for row in rows], dtype=int),
        lm_rejected_step_count=np.asarray([row.get("lm_diagnostics", {}).get("rejected_step_count", 0) or 0 for row in rows], dtype=int),
        lm_initial_residual_cost=np.asarray([_float_or_nan(row.get("lm_diagnostics", {}).get("initial_residual_cost")) for row in rows], dtype=float),
        lm_final_residual_cost=np.asarray([_float_or_nan(row.get("lm_diagnostics", {}).get("final_residual_cost")) for row in rows], dtype=float),
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
    lm_cost_increases = sum(
        1
        for row in rows
        if row.get("cooperative_jcls_attempted")
        and row.get("lm_diagnostics", {}).get("cost_decrease") is not None
        and float(row.get("lm_diagnostics", {}).get("cost_decrease", 0.0)) < -STEP_B_COST_TOLERANCE
    )
    cooperative_rows = [row for row in rows if row.get("cooperative_jcls_attempted")]
    lm_or_map_worse_than_il = sum(
        1
        for row in cooperative_rows
        if float(row["lm_position_error_m"]) > float(row["il_position_error_m"])
        or float(row["map_position_error_m"]) > float(row["il_position_error_m"])
    )
    healthy = bool(comparisons) and len(pos_wins) == len(comparisons) and len(sync_wins) == len(comparisons) and failed_rows == 0
    status = "healthy" if healthy else "partially_degraded"
    catastrophic = (
        failed_rows > len(rows) / 2
        or lm_cost_increases > 0
        or (bool(cooperative_rows) and lm_or_map_worse_than_il > len(cooperative_rows) / 2)
    )
    if catastrophic:
        status = "failed"
    degraded = False
    if previous is not None:
        degraded = (
            len(pos_wins) < previous["position_improvement_count"]
            or len(sync_wins) < previous["sync_improvement_count"]
            or failed_rows > previous["failed_rows"]
        )
        if degraded and not catastrophic:
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
        "lm_cost_increase_rows": lm_cost_increases,
        "lm_or_map_worse_than_il_rows": lm_or_map_worse_than_il,
        "catastrophic_failure": catastrophic,
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
    row_hash = hashlib.sha256(json.dumps(rows, sort_keys=True).encode("utf-8")).hexdigest()
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
        "lm_acceptance_mode": step.acceptance_mode,
        "truth_state_used_for_lm_acceptance": False if step.name == STEP_B_NAME else True,
        "plot_outputs": plot_outputs,
        "raw_outputs": {**csvs, "arrays_npz": arrays},
        "health": health,
        "lm_acceptance_diagnostics": _lm_acceptance_summary(rows),
        "change_vs_previous": None,
    }
    if step.name != STEP_B_NAME:
        metadata["lm_acceptance_diagnostics"]["truth_state_used_for_lm_acceptance"] = True
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


def _lm_acceptance_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize LM acceptance diagnostics over rows."""

    diagnostics = [row.get("lm_diagnostics", {}) for row in rows]
    return {
        "truth_state_used_for_lm_acceptance": any(bool(item.get("truth_state_used_for_lm_acceptance")) for item in diagnostics),
        "accepted_step_count": int(sum(int(item.get("accepted_step_count") or 0) for item in diagnostics)),
        "rejected_step_count": int(sum(int(item.get("rejected_step_count") or 0) for item in diagnostics)),
        "rows_with_residual_cost_increase": int(
            sum(1 for item in diagnostics if item.get("cost_decrease") is not None and float(item["cost_decrease"]) < -STEP_B_COST_TOLERANCE)
        ),
        "rejection_reasons": sorted(
            {
                reason
                for item in diagnostics
                for reason in item.get("rejection_reasons", [])
            }
        ),
    }


def _read_ladder_raw(path: Path) -> dict[tuple[int, int], dict[str, Any]]:
    """Read a ladder raw CSV keyed by users and satellites."""

    with path.open(newline="", encoding="utf-8") as handle:
        rows = []
        for row in csv.DictReader(handle):
            converted = dict(row)
            for key in ["num_users", "num_satellites", "measurement_count", "state_dimension", "fallback_count", "failure_count"]:
                if converted.get(key) not in {None, ""}:
                    converted[key] = int(float(converted[key]))
            for key in [
                "il_position_error_m",
                "lm_position_error_m",
                "map_position_error_m",
                "il_sync_error_s",
                "lm_sync_error_s",
                "map_sync_error_s",
                "lm_initial_residual_cost",
                "lm_final_residual_cost",
                "lm_cost_decrease",
                "lm_final_damping",
            ]:
                if converted.get(key) not in {None, ""}:
                    converted[key] = float(converted[key])
            for key in ["lm_accepted_step_count", "lm_rejected_step_count"]:
                if converted.get(key) not in {None, ""}:
                    converted[key] = int(float(converted[key]))
            converted["cooperative_jcls_attempted"] = str(converted.get("cooperative_jcls_attempted")) == "True"
            converted["success"] = str(converted.get("success")) == "True"
            rows.append(converted)
    return {(row["num_users"], row["num_satellites"]): row for row in rows}


def _classify_step_b_row(step_a: dict[str, Any], step_b: dict[str, Any]) -> str:
    """Classify Step B behavior for one row."""

    if step_b.get("failure_count", 0) > 0 or not np.isfinite(float(step_b["map_position_error_m"])):
        return "failed"
    if step_b.get("cooperative_jcls_attempted") and (
        float(step_b["map_position_error_m"]) > float(step_b["il_position_error_m"])
        or float(step_b["map_sync_error_s"]) > float(step_b["il_sync_error_s"])
    ):
        return "major_degradation"
    position_ratio = (
        float(step_b["map_position_error_m"]) / float(step_a["map_position_error_m"])
        if float(step_a["map_position_error_m"]) > 0
        else 1.0
    )
    sync_ratio = (
        float(step_b["map_sync_error_s"]) / float(step_a["map_sync_error_s"])
        if float(step_a["map_sync_error_s"]) > 0
        else 1.0
    )
    if position_ratio > 2.0 or sync_ratio > 2.0:
        return "major_degradation"
    if position_ratio > 1.10 or sync_ratio > 1.10:
        return "mild_degradation"
    return "healthy"


def _write_step_b_comparison() -> dict[str, Any] | None:
    """Compare Step B medium results against Step A medium results."""

    step_a_path = LADDER_ROOT / "step_a_no_display_smoothing" / "medium" / "migration_raw.csv"
    step_b_path = LADDER_ROOT / STEP_B_NAME / "medium" / "migration_raw.csv"
    if not step_a_path.exists() or not step_b_path.exists():
        return None
    step_a_rows = _read_ladder_raw(step_a_path)
    step_b_rows = _read_ladder_raw(step_b_path)
    comparisons = []
    for key in sorted(step_b_rows):
        a = step_a_rows[key]
        b = step_b_rows[key]
        comparisons.append(
            {
                "num_users": key[0],
                "num_satellites": key[1],
                "step_a": {
                    "il_position_error_m": a["il_position_error_m"],
                    "lm_position_error_m": a["lm_position_error_m"],
                    "map_position_error_m": a["map_position_error_m"],
                    "il_sync_error_s": a["il_sync_error_s"],
                    "lm_sync_error_s": a["lm_sync_error_s"],
                    "map_sync_error_s": a["map_sync_error_s"],
                },
                "step_b": {
                    "il_position_error_m": b["il_position_error_m"],
                    "lm_position_error_m": b["lm_position_error_m"],
                    "map_position_error_m": b["map_position_error_m"],
                    "il_sync_error_s": b["il_sync_error_s"],
                    "lm_sync_error_s": b["lm_sync_error_s"],
                    "map_sync_error_s": b["map_sync_error_s"],
                    "lm_accepted_step_count": b.get("lm_accepted_step_count"),
                    "lm_rejected_step_count": b.get("lm_rejected_step_count"),
                    "lm_initial_residual_cost": b.get("lm_initial_residual_cost"),
                    "lm_final_residual_cost": b.get("lm_final_residual_cost"),
                    "lm_cost_decrease": b.get("lm_cost_decrease"),
                },
                "does_jcls_still_help_localization": (
                    not b["cooperative_jcls_attempted"]
                    or float(b["map_position_error_m"]) < float(step_b_rows[(1, key[1])]["map_position_error_m"])
                ),
                "does_jcls_still_help_synchronization": (
                    not b["cooperative_jcls_attempted"]
                    or float(b["map_sync_error_s"]) < float(step_b_rows[(1, key[1])]["map_sync_error_s"])
                ),
                "status": _classify_step_b_row(a, b),
            }
        )
    status_counts = {status: sum(1 for item in comparisons if item["status"] == status) for status in ["healthy", "mild_degradation", "major_degradation", "failed"]}
    payload = {
        "artifact_status": "non_final_step_b_lm_acceptance_comparison",
        "manuscript_ready": False,
        "step_a": "step_a_no_display_smoothing",
        "step_b": STEP_B_NAME,
        "status_counts": status_counts,
        "overall_status": "healthy" if status_counts["major_degradation"] == 0 and status_counts["failed"] == 0 else "major_degradation",
        "comparisons": comparisons,
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "STEP_B_LM_ACCEPTANCE_COMPARISON.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md = [
        "# Step B LM Acceptance Comparison",
        "",
        "## Executive Summary",
        "Step B replaces LM truth-state acceptance with residual/trust-region checks while preserving the rest of the legacy-compatible pipeline.",
        "",
        f"- Overall status: `{payload['overall_status']}`",
        f"- Healthy rows: {status_counts['healthy']}",
        f"- Mild degradation rows: {status_counts['mild_degradation']}",
        f"- Major degradation rows: {status_counts['major_degradation']}",
        f"- Failed rows: {status_counts['failed']}",
        "",
        "| Users | Satellites | Status | Step A MAP pos [m] | Step B MAP pos [m] | Step A MAP sync [s] | Step B MAP sync [s] | LM accept/reject | Residual cost decrease |",
        "|---:|---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    for item in comparisons:
        md.append(
            f"| {item['num_users']} | {item['num_satellites']} | `{item['status']}` | "
            f"{item['step_a']['map_position_error_m']:.6g} | {item['step_b']['map_position_error_m']:.6g} | "
            f"{item['step_a']['map_sync_error_s']:.6g} | {item['step_b']['map_sync_error_s']:.6g} | "
            f"{item['step_b']['lm_accepted_step_count']}/{item['step_b']['lm_rejected_step_count']} | "
            f"{item['step_b']['lm_cost_decrease']} |"
        )
    (REPORTS / "STEP_B_LM_ACCEPTANCE_COMPARISON.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return payload


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
        "current_best_migration_step": steps[-1]["step"]["name"] if first_degraded is None and steps else "step_a_no_display_smoothing",
        "stop_rule_triggered": first_degraded is not None,
        "manuscript_ready": False,
    }
    (REPORTS / "CONTROLLED_MIGRATION_LADDER.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md = [
        "# Controlled Migration Ladder",
        "",
        "## Executive Summary",
        "This ladder starts from frozen legacy-compatible behavior and changes one migration axis at a time. No figure is manuscript-ready.",
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
            if step.name == STEP_B_NAME:
                if grid == "medium":
                    tiny_report = next(
                        (report for report in step_reports if report["step"]["name"] == STEP_B_NAME and report["grid"] == "tiny"),
                        None,
                    )
                    if tiny_report is not None and tiny_report["health"].get("catastrophic_failure"):
                        continue
                grid_rows = _run_step_b_rows(grid)
            else:
                grid_rows = _filter_rows(rows, grid)
            report = _write_step(step, grid, grid_rows, previous_by_grid[grid])
            previous_by_grid[grid] = report["health"]
            step_reports.append(report)
            cache_entries.append({"step": step.name, "grid": grid, **report["cache"]})
    _write_cache_manifest(cache_entries)
    ladder = _write_ladder_report(step_reports, baseline)
    step_b_comparison = _write_step_b_comparison()
    if step_b_comparison is not None:
        ladder["step_b_comparison"] = {
            "path": "outputs/reports/STEP_B_LM_ACCEPTANCE_COMPARISON.md",
            "overall_status": step_b_comparison["overall_status"],
        }
    from scripts.render_all_figure_previews import render_gallery

    from scripts.build_legacy_graph_package import main as build_graph_package

    build_graph_package()
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
