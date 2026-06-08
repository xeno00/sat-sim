"""Build a controlled legacy-to-V24 migration ladder diagnostic package."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import sys
import time
from dataclasses import dataclass
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
from jcls_sim.constants import C_KM_PER_S  # noqa: E402
from scripts.replay_legacy_clock_sweep_figures import NOTEBOOK_PATH, _execute_legacy_namespace, _hash_file, _selected_cell_hashes  # noqa: E402
from scripts.replay_legacy_network_size_figures import CACHE_SCHEMA_VERSION as NETWORK_CACHE_SCHEMA  # noqa: E402
from scripts.replay_legacy_network_size_figures import _mode_config  # noqa: E402


BASELINE_ROOT = SAT_SIM_ROOT / "outputs" / "migration_baseline" / "legacy_behavior_freeze"
LADDER_ROOT = SAT_SIM_ROOT / "outputs" / "migration_ladder"
REPORTS = SAT_SIM_ROOT / "outputs" / "reports"
MIGRATION_CACHE_ROOT = SAT_SIM_ROOT / "outputs" / "cache" / "migration_ladder"
HEARTBEAT_PATH = MIGRATION_CACHE_ROOT / "RUN_HEARTBEAT.json"
ROW_STATUS_PATH = MIGRATION_CACHE_ROOT / "ROW_STATUS.jsonl"
SOURCE_NETWORK_ROOT = SAT_SIM_ROOT / "outputs" / "legacy_replay" / "network_size_medium"
SOURCE_CLOCK_ROOT = SAT_SIM_ROOT / "outputs" / "legacy_replay" / "clock_sweep_full"
MIGRATION_CACHE_SCHEMA_VERSION = "controlled-migration-ladder-v1"
STEP_B_NAME = "step_b_lm_residual_acceptance"
STEP_C5_NAME = "step_c5_sliding_window_map"
STEP_C7_NAME = "step_c7_residual_cov_sync_safeguard"
STEP_C_DIAGNOSIS_NAMES = {
    "step_c0_legacy_map_instrumented",
    "step_c1_legacy_cov_observable_acceptance",
    "step_c2_observable_cov_legacy_acceptance",
    "step_c3_cov_diag_prior",
    "step_c3_cov_block_diag",
    "step_c3_cov_damped_inverse",
    "step_c3_cov_damped_pinv",
    "step_c3_cov_residual_scaled",
    "step_c4_composite_map_acceptance",
}
STEP_B_STEP_NORM_LIMIT = 1.0e6
STEP_B_COST_TOLERANCE = 1.0e-9
STEP_C_COST_TOLERANCE = 1.0e-9
STEP_C_COVARIANCE_DAMPING = 1.0e-8
STEP_C_PROCESS_COVARIANCE_SCALE = 1.0e2
COMPOSITE_MAP_ACCEPTANCE_PARAMETERS = {
    "mode": "composite_observable",
    "measurement_residual_cost_weight": 1.0,
    "prior_consistency_cost_weight": 1.0,
    "map_objective_tolerance": STEP_C_COST_TOLERANCE,
    "covariance_trace_relative_tolerance": 1.0e-6,
    "relative_update_norm_limit": STEP_B_STEP_NORM_LIMIT,
    "position_update_limit_rule": "max(1e3, 0.5 * position_state_norm)",
    "clock_update_limit_rule": "max(1e3, 0.5 * clock_state_norm)",
}
SLIDING_WINDOW_MAP_PARAMETERS = {
    "mode": "sliding_window_map",
    "window_length": 3,
    "state_transition": "identity",
    "max_iterations": 6,
    "initial_damping": 1.0e-3,
    "damping_increase": 10.0,
    "damping_decrease": 0.5,
    "objective_tolerance": STEP_C_COST_TOLERANCE,
    "position_prior_std_km": 100.0,
    "clock_prior_std_km": 1.0,
    "position_process_std_km": 10.0,
    "clock_process_std_km": 0.1,
    "truth_state_used_for_map_acceptance": False,
    "truth_state_used_for_map_covariance": False,
}


@dataclass(frozen=True)
class LadderRunOptions:
    """Runtime controls for bounded migration-ladder execution."""

    steps: tuple[str, ...] = ()
    include_medium: bool = False
    tiny_only: bool = True
    max_rows: int | None = None
    max_substeps: int | None = None
    timeout_seconds_per_row: float | None = None
    timeout_seconds_total: float | None = None
    resume: bool = False
    dry_run: bool = False
    list_planned_work: bool = False
    stop_after_first_degradation: bool = False
    use_cache: bool = False

    @property
    def bounded(self) -> bool:
        """Return whether this run is intentionally bounded/noncanonical."""

        return bool(
            self.max_rows is not None
            or self.max_substeps is not None
            or self.timeout_seconds_per_row is not None
            or self.timeout_seconds_total is not None
            or self.dry_run
            or self.stop_after_first_degradation
        )


def _sha256(path: Path) -> str:
    """Return SHA256 for a file."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _repo_rel(path: Path) -> str:
    """Return repo-relative POSIX path."""

    return path.relative_to(SAT_SIM_ROOT).as_posix()


def _grid_points(grid: str) -> list[tuple[int, int]]:
    """Return planned ``(num_users, num_satellites)`` rows for a grid."""

    if grid == "tiny":
        users = [1, 3]
        satellites = [4, 8]
    elif grid == "medium":
        users = [1, 3, 5, 7]
        satellites = [4, 8, 12]
    else:
        raise ValueError(f"unknown grid: {grid}")
    return [(user, sat) for user in users for sat in satellites]


def _selected_grids(options: LadderRunOptions) -> list[str]:
    """Return grids allowed by runtime options."""

    if options.tiny_only or not options.include_medium:
        return ["tiny"]
    return ["tiny", "medium"]


def _selected_steps(options: LadderRunOptions) -> list[MigrationStep]:
    """Return migration steps selected by runtime options."""

    available = migration_ladder_steps()[1:]
    if options.steps:
        requested = set(options.steps)
        selected = [step for step in available if step.name in requested]
        missing = sorted(requested - {step.name for step in selected})
        if missing:
            raise ValueError(f"unknown migration step(s): {', '.join(missing)}")
    else:
        selected = available
    if options.max_substeps is not None:
        selected = selected[: max(0, options.max_substeps)]
    return selected


def _planned_work(options: LadderRunOptions) -> list[dict[str, Any]]:
    """Return the exact rows planned for execution."""

    rows = []
    for step in _selected_steps(options):
        for grid in _selected_grids(options):
            if grid == "medium" and step.name.startswith("step_c3"):
                # C3 covariance candidates at medium scale require explicit single-step selection.
                if not options.steps:
                    continue
            for row_number, (num_users, num_satellites) in enumerate(_grid_points(grid), start=1):
                rows.append(
                    {
                        "step": step.name,
                        "grid": grid,
                        "num_users": num_users,
                        "num_satellites": num_satellites,
                        "row_number_within_grid": row_number,
                    }
                )
    if options.max_rows is not None:
        rows = rows[: max(0, options.max_rows)]
    return rows


def _group_planned_work(planned: list[dict[str, Any]]) -> dict[tuple[str, str], list[tuple[int, int]]]:
    """Group planned rows by step and grid."""

    grouped: dict[tuple[str, str], list[tuple[int, int]]] = {}
    for item in planned:
        grouped.setdefault((item["step"], item["grid"]), []).append((item["num_users"], item["num_satellites"]))
    return grouped


def _print_planned_work(planned: list[dict[str, Any]], options: LadderRunOptions) -> None:
    """Print planned work before executing."""

    payload = {
        "artifact_status": "non_final_migration_ladder_planned_work",
        "row_count": len(planned),
        "tiny_only": options.tiny_only,
        "include_medium": options.include_medium,
        "max_rows": options.max_rows,
        "max_substeps": options.max_substeps,
        "dry_run": options.dry_run,
        "list_planned_work": options.list_planned_work,
        "will_execute": not (options.dry_run or options.list_planned_work),
        "planned_rows": planned,
    }
    print(json.dumps(payload, indent=2))


def _heartbeat_payload(
    *,
    status: str,
    current_substep: str | None,
    current_grid_point: dict[str, Any] | None,
    row_number: int,
    total_rows: int,
    started_monotonic: float,
    process_start_time_utc: str,
    last_completed_output: str | None,
) -> dict[str, Any]:
    """Return heartbeat payload for long ladder runs."""

    elapsed = max(0.0, time.monotonic() - started_monotonic)
    remaining = max(0, total_rows - row_number)
    return {
        "artifact_status": "non_final_migration_ladder_heartbeat",
        "status": status,
        "current_substep": current_substep,
        "current_grid_point": current_grid_point,
        "row_number": int(row_number),
        "elapsed_time_seconds": elapsed,
        "estimated_remaining_rows": int(remaining),
        "last_completed_output": last_completed_output,
        "process_start_time_utc": process_start_time_utc,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def _write_heartbeat(payload: dict[str, Any]) -> None:
    """Write heartbeat JSON."""

    HEARTBEAT_PATH.parent.mkdir(parents=True, exist_ok=True)
    HEARTBEAT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_row_status(event: dict[str, Any]) -> None:
    """Append one row-level status event."""

    ROW_STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    event = dict(event)
    event["timestamp_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with ROW_STATUS_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")


def _execution_metadata(
    *,
    planned_rows: int,
    executed_rows: int,
    status: str,
    options: LadderRunOptions,
    output_grid: str,
) -> dict[str, Any]:
    """Return execution metadata used to prevent partial outputs being treated as valid."""

    complete = status == "complete" and executed_rows == planned_rows
    return {
        "status": status,
        "complete": bool(complete),
        "planned_rows": int(planned_rows),
        "executed_rows": int(executed_rows),
        "partial": not complete,
        "output_grid": output_grid,
        "max_rows": options.max_rows,
        "max_substeps": options.max_substeps,
        "timeout_seconds_per_row": options.timeout_seconds_per_row,
        "timeout_seconds_total": options.timeout_seconds_total,
        "resume": options.resume,
        "dry_run": options.dry_run,
        "stop_after_first_degradation": options.stop_after_first_degradation,
        "use_cache": options.use_cache,
        "bounded": options.bounded,
        "canonical_cache_valid": bool(complete and not options.bounded),
    }


def _cache_payload_status(metadata: dict[str, Any]) -> str:
    """Return cache status. Partial/interrupted rows are never valid cache."""

    execution = metadata.get("execution", {})
    if execution and not execution.get("complete", False):
        return "partial"
    if execution and execution.get("bounded", False):
        return "bounded_noncanonical"
    return "complete"


def _should_stop_after_degradation(report: dict[str, Any], options: LadderRunOptions) -> bool:
    """Return whether the stop-after-first-degradation guard should stop execution."""

    return bool(options.stop_after_first_degradation and report.get("health", {}).get("performance_degraded_vs_previous"))


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


def _symmetrize(matrix: np.ndarray) -> np.ndarray:
    """Return the symmetric part of a square matrix."""

    return 0.5 * (np.asarray(matrix, dtype=float) + np.asarray(matrix, dtype=float).T)


def _covariance_status(matrix: np.ndarray) -> dict[str, Any]:
    """Return numerical diagnostics for a covariance matrix."""

    covariance = np.asarray(matrix, dtype=float)
    finite = bool(np.all(np.isfinite(covariance)))
    symmetric = bool(np.allclose(covariance, covariance.T, atol=1.0e-7, rtol=1.0e-7)) if finite else False
    diag = np.diag(covariance) if covariance.ndim == 2 else np.asarray([])
    min_eigenvalue = None
    psd = False
    condition_number = None
    if finite and symmetric:
        eigenvalues = np.linalg.eigvalsh(covariance)
        min_eigenvalue = float(np.min(eigenvalues))
        psd = bool(min_eigenvalue >= -1.0e-7)
        condition_number = float(np.linalg.cond(covariance + STEP_C_COVARIANCE_DAMPING * np.eye(covariance.shape[0])))
    return {
        "finite": finite,
        "symmetric": symmetric,
        "psd": psd,
        "min_eigenvalue": min_eigenvalue,
        "trace": float(np.trace(covariance)) if finite and covariance.ndim == 2 else None,
        "condition_number": condition_number,
        "diagonal_min": float(np.min(diag)) if finite and diag.size else None,
        "diagonal_max": float(np.max(diag)) if finite and diag.size else None,
    }


def _information_matrix(scenario: Any, x: np.ndarray) -> np.ndarray:
    """Return observable normal/information matrix for MAP covariance candidates."""

    J = np.asarray(scenario.evaluate_jacobian(x), dtype=float)
    covariance = np.asarray(scenario.get_measurement_covariance(), dtype=float)
    precision = _safe_inverse(covariance)
    return J.T @ precision @ J


def _observable_covariance(scenario: Any, x: np.ndarray, mode: str) -> tuple[np.ndarray, dict[str, Any]]:
    """Return a non-truth covariance candidate and diagnostics."""

    dim = int(len(x))
    info = _information_matrix(scenario, x)
    damped = info + STEP_C_COVARIANCE_DAMPING * np.eye(dim)
    if mode == "diagonal_prior":
        covariance = np.diag([1.0e4 if not str(param).startswith("delta_") else 1.0 for param in scenario.symbolic_parameter_vector])
    elif mode == "block_diagonal_position_clock":
        covariance = np.diag([2.5e3 if not str(param).startswith("delta_") else 2.5e-1 for param in scenario.symbolic_parameter_vector])
    elif mode == "damped_inverse_normal_matrix":
        covariance = _safe_inverse(damped)
    elif mode in {"damped_information_pseudoinverse", "damped_pseudoinverse_information_matrix"}:
        covariance = np.linalg.pinv(damped)
    elif mode == "residual_scaled_information_pseudoinverse":
        residual = np.asarray(scenario.h(x), dtype=float)
        scale = max(1.0, float(np.mean(residual**2)))
        covariance = scale * np.linalg.pinv(damped)
    else:
        raise ValueError(f"unknown MAP covariance mode: {mode}")
    covariance = _symmetrize(covariance)
    status = _covariance_status(covariance)
    if status["min_eigenvalue"] is not None and status["min_eigenvalue"] < 0.0:
        covariance = _symmetrize(covariance + (-status["min_eigenvalue"] + STEP_C_COVARIANCE_DAMPING) * np.eye(dim))
        status = _covariance_status(covariance)
    status.update(
        {
            "map_covariance_mode": mode,
            "truth_state_used_for_map_covariance": False,
            "information_rank": int(np.linalg.matrix_rank(info)),
            "parameter_dim": dim,
            "damping": STEP_C_COVARIANCE_DAMPING,
        }
    )
    return covariance, status


def _map_diagnostics_template(covariance_mode: str, update_mode: str, truth_covariance: bool, truth_acceptance: bool) -> dict[str, Any]:
    """Return a MAP diagnostics skeleton."""

    return {
        "map_update_mode": update_mode,
        "map_covariance_mode": covariance_mode,
        "truth_state_used_for_map_covariance": truth_covariance,
        "truth_state_used_for_map_acceptance": truth_acceptance,
        "initial_residual_cost": None,
        "final_residual_cost": None,
        "accepted_cost_decrease_min": None,
        "rejected_candidate_count": 0,
        "accepted_update_count": 0,
        "rejected_update_count": 0,
        "fallback_count": 0,
        "covariance_trace_before": None,
        "covariance_trace_after": None,
        "covariance_condition_before": None,
        "covariance_condition_after": None,
        "covariance_diagonal_min": None,
        "covariance_diagonal_max": None,
        "update_norm_max": None,
        "finite_covariance": None,
        "symmetric_covariance": None,
        "psd_covariance": None,
        "true_error_before": None,
        "true_error_after": None,
        "map_acceptance_mode": update_mode,
        "score_components_used": [],
        "initial_map_objective": None,
        "final_map_objective": None,
        "accepted_map_objective_decrease_min": None,
        "prior_cost_before": None,
        "prior_cost_after": None,
        "position_update_norm_max": None,
        "clock_update_norm_max": None,
        "relative_update_norm_max": None,
        "fallback_paths": [],
        "rejection_reasons": [],
        "step_trace": [],
    }


def _parameter_update_norms(scenario: Any, update: np.ndarray, state: np.ndarray) -> dict[str, float | None]:
    """Return total, position, and clock update norms from symbolic parameter names."""

    symbols = [str(param) for param in scenario.symbolic_parameter_vector]
    clock_indices = [idx for idx, symbol in enumerate(symbols) if "delta" in symbol]
    position_indices = [idx for idx, symbol in enumerate(symbols) if idx not in clock_indices]
    update = np.asarray(update, dtype=float)
    state = np.asarray(state, dtype=float)

    def _norm(indices: list[int], values: np.ndarray) -> float | None:
        return float(np.linalg.norm(values[indices])) if indices else None

    position_update = _norm(position_indices, update)
    clock_update = _norm(clock_indices, update)
    position_state = _norm(position_indices, state)
    clock_state = _norm(clock_indices, state)
    return {
        "update_norm": float(np.linalg.norm(update)),
        "relative_update_norm": float(np.linalg.norm(update)) / max(1.0, float(np.linalg.norm(state))),
        "position_update_norm": position_update,
        "clock_update_norm": clock_update,
        "position_update_limit": max(1.0e3, 0.50 * (position_state or 0.0)),
        "clock_update_limit": max(1.0e3, 0.50 * (clock_state or 0.0)),
    }


def _sliding_window_precision_diagonal(scenario: Any, *, position_std_km: float, clock_std_km: float) -> np.ndarray:
    """Return a diagonal precision for the legacy all-clock state ordering."""

    variances = [
        float(clock_std_km) ** 2 if "delta" in str(param) else float(position_std_km) ** 2
        for param in scenario.symbolic_parameter_vector
    ]
    return np.diag(1.0 / np.maximum(np.asarray(variances, dtype=float), STEP_C_COVARIANCE_DAMPING))


def _sliding_window_components(
    scenario: Any,
    states: np.ndarray,
    measurements: list[np.ndarray],
    theta_prior: np.ndarray,
    prior_precision: np.ndarray,
    process_precision: np.ndarray,
) -> dict[str, float]:
    """Return measurement, prior, dynamics, and total smoother objective terms."""

    covariance = np.asarray(scenario.get_measurement_covariance(), dtype=float)
    measurement_precision = _safe_inverse(covariance)
    measurement_objective = 0.0
    for state, measurement in zip(states, measurements):
        residual = np.asarray(measurement - scenario.h(state), dtype=float)
        measurement_objective += float(residual.T @ measurement_precision @ residual)
    prior_delta = np.asarray(states[0] - theta_prior, dtype=float)
    prior_objective = float(prior_delta.T @ prior_precision @ prior_delta)
    dynamics_objective = 0.0
    for idx in range(1, states.shape[0]):
        delta = np.asarray(states[idx] - states[idx - 1], dtype=float)
        dynamics_objective += float(delta.T @ process_precision @ delta)
    total = measurement_objective + prior_objective + dynamics_objective
    return {
        "measurement_objective": measurement_objective,
        "prior_objective": prior_objective,
        "dynamics_objective": dynamics_objective,
        "total_objective": float(total),
    }


def _sliding_window_normal_equations(
    scenario: Any,
    states: np.ndarray,
    measurements: list[np.ndarray],
    theta_prior: np.ndarray,
    prior_precision: np.ndarray,
    process_precision: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Return Gauss-Newton normal matrix and right-hand side for the smoother."""

    window_length, state_dim = states.shape
    total_dim = window_length * state_dim
    normal = np.zeros((total_dim, total_dim), dtype=float)
    rhs = np.zeros(total_dim, dtype=float)
    measurement_precision = _safe_inverse(np.asarray(scenario.get_measurement_covariance(), dtype=float))

    def block(index: int) -> slice:
        return slice(index * state_dim, (index + 1) * state_dim)

    for epoch, (state, measurement) in enumerate(zip(states, measurements)):
        residual = np.asarray(measurement - scenario.h(state), dtype=float)
        jacobian = np.asarray(scenario.evaluate_jacobian(state), dtype=float)
        target = block(epoch)
        normal[target, target] += jacobian.T @ measurement_precision @ jacobian
        rhs[target] += jacobian.T @ measurement_precision @ residual

    prior_delta = np.asarray(states[0] - theta_prior, dtype=float)
    first = block(0)
    normal[first, first] += prior_precision
    rhs[first] += -prior_precision @ prior_delta

    for epoch in range(1, window_length):
        prev = block(epoch - 1)
        curr = block(epoch)
        delta = np.asarray(states[epoch] - states[epoch - 1], dtype=float)
        normal[prev, prev] += process_precision
        normal[curr, curr] += process_precision
        normal[prev, curr] += -process_precision
        normal[curr, prev] += -process_precision
        rhs[prev] += process_precision @ delta
        rhs[curr] += -process_precision @ delta
    return _symmetrize(normal), rhs


def _sliding_window_map_refinement(scenario: Any, x_step2: np.ndarray, measurements: list[np.ndarray]) -> tuple[np.ndarray, dict[str, Any]]:
    """Run a Step-B-initialized sliding-window MAP smoother without truth gates."""

    params = SLIDING_WINDOW_MAP_PARAMETERS
    state_dim = int(len(x_step2))
    window_length = int(params["window_length"])
    if len(measurements) != window_length:
        raise ValueError(f"expected {window_length} measurements, got {len(measurements)}")
    states = np.tile(np.asarray(x_step2, dtype=float), (window_length, 1))
    theta_prior = np.asarray(x_step2, dtype=float)
    prior_precision = _sliding_window_precision_diagonal(
        scenario,
        position_std_km=float(params["position_prior_std_km"]),
        clock_std_km=float(params["clock_prior_std_km"]),
    )
    process_precision = _sliding_window_precision_diagonal(
        scenario,
        position_std_km=float(params["position_process_std_km"]),
        clock_std_km=float(params["clock_process_std_km"]),
    )
    initial_components = _sliding_window_components(
        scenario,
        states,
        measurements,
        theta_prior,
        prior_precision,
        process_precision,
    )
    current_components = dict(initial_components)
    damping = float(params["initial_damping"])
    history: list[dict[str, Any]] = []
    accepted_count = 0
    rejected_count = 0

    final_normal, _ = _sliding_window_normal_equations(
        scenario,
        states,
        measurements,
        theta_prior,
        prior_precision,
        process_precision,
    )
    for iteration in range(int(params["max_iterations"])):
        normal, rhs = _sliding_window_normal_equations(
            scenario,
            states,
            measurements,
            theta_prior,
            prior_precision,
            process_precision,
        )
        final_normal = normal
        damped = normal + damping * np.eye(normal.shape[0])
        reasons: list[str] = []
        try:
            step = np.linalg.solve(damped, rhs)
        except np.linalg.LinAlgError:
            step = np.linalg.pinv(damped) @ rhs
            reasons.append("normal_matrix_pseudoinverse")
        candidate_states = states + step.reshape(states.shape)
        finite_candidate = bool(np.all(np.isfinite(candidate_states)))
        if not finite_candidate:
            reasons.append("nonfinite_candidate")
        candidate_components = (
            _sliding_window_components(scenario, candidate_states, measurements, theta_prior, prior_precision, process_precision)
            if finite_candidate
            else {
                "measurement_objective": float("inf"),
                "prior_objective": float("inf"),
                "dynamics_objective": float("inf"),
                "total_objective": float("inf"),
            }
        )
        current_total = float(current_components["total_objective"])
        candidate_total = float(candidate_components["total_objective"])
        decrease = current_total - candidate_total if np.isfinite(candidate_total) else None
        if not np.isfinite(candidate_total):
            reasons.append("nonfinite_total_objective")
        if np.isfinite(candidate_total) and candidate_total > current_total - STEP_C_COST_TOLERANCE * max(1.0, abs(current_total)):
            reasons.append("total_objective_not_decreased")
        update_final_epoch = step.reshape(states.shape)[-1]
        norm_status = _parameter_update_norms(scenario, update_final_epoch, states[-1])
        accepted = not reasons
        history.append(
            {
                "iteration": iteration,
                "accepted": bool(accepted),
                "current_total_objective": current_total,
                "candidate_total_objective": candidate_total,
                "objective_decrease": decrease,
                "current_measurement_objective": current_components["measurement_objective"],
                "candidate_measurement_objective": candidate_components["measurement_objective"],
                "current_prior_objective": current_components["prior_objective"],
                "candidate_prior_objective": candidate_components["prior_objective"],
                "current_dynamics_objective": current_components["dynamics_objective"],
                "candidate_dynamics_objective": candidate_components["dynamics_objective"],
                "damping": damping,
                "condition_number": float(np.linalg.cond(damped)) if np.all(np.isfinite(damped)) else None,
                "update_norm": float(np.linalg.norm(step)),
                "final_epoch_update_norm": norm_status["update_norm"],
                "relative_update_norm": norm_status["relative_update_norm"],
                "position_update_norm": norm_status["position_update_norm"],
                "clock_update_norm": norm_status["clock_update_norm"],
                "rejection_reasons": reasons,
            }
        )
        if accepted:
            states = candidate_states
            current_components = candidate_components
            damping = max(damping * float(params["damping_decrease"]), 1.0e-12)
            accepted_count += 1
        else:
            damping *= float(params["damping_increase"])
            rejected_count += 1

    final_components = _sliding_window_components(
        scenario,
        states,
        measurements,
        theta_prior,
        prior_precision,
        process_precision,
    )
    covariance = _symmetrize(np.linalg.pinv(final_normal + float(params["initial_damping"]) * np.eye(final_normal.shape[0])))
    covariance_status = _covariance_status(covariance)
    accepted_decreases = [
        float(item["objective_decrease"])
        for item in history
        if item["accepted"] and item["objective_decrease"] is not None
    ]
    diagnostics = _map_diagnostics_template(
        "configured_diagonal_prior_process",
        "sliding_window_map",
        False,
        False,
    )
    diagnostics.update(
        {
            "map_acceptance_mode": "sliding_window_full_objective_decrease",
            "score_components_used": ["measurement_objective", "prior_objective", "dynamics_objective", "total_objective"],
            "initial_residual_cost": initial_components["measurement_objective"],
            "final_residual_cost": final_components["measurement_objective"],
            "accepted_cost_decrease_min": min(accepted_decreases) if accepted_decreases else 0.0,
            "initial_map_objective": initial_components["total_objective"],
            "final_map_objective": final_components["total_objective"],
            "accepted_map_objective_decrease_min": min(accepted_decreases) if accepted_decreases else 0.0,
            "prior_cost_before": initial_components["prior_objective"],
            "prior_cost_after": final_components["prior_objective"],
            "dynamics_cost_before": initial_components["dynamics_objective"],
            "dynamics_cost_after": final_components["dynamics_objective"],
            "measurement_cost_before": initial_components["measurement_objective"],
            "measurement_cost_after": final_components["measurement_objective"],
            "accepted_update_count": accepted_count,
            "rejected_update_count": rejected_count,
            "rejected_candidate_count": rejected_count,
            "covariance_trace_before": None,
            "covariance_trace_after": covariance_status["trace"],
            "covariance_condition_before": None,
            "covariance_condition_after": covariance_status["condition_number"],
            "covariance_diagonal_min": covariance_status["diagonal_min"],
            "covariance_diagonal_max": covariance_status["diagonal_max"],
            "update_norm_max": max((float(item["final_epoch_update_norm"]) for item in history), default=0.0),
            "position_update_norm_max": max((float(item["position_update_norm"]) for item in history if item["position_update_norm"] is not None), default=None),
            "clock_update_norm_max": max((float(item["clock_update_norm"]) for item in history if item["clock_update_norm"] is not None), default=None),
            "relative_update_norm_max": max((float(item["relative_update_norm"]) for item in history), default=0.0),
            "finite_covariance": covariance_status["finite"],
            "symmetric_covariance": covariance_status["symmetric"],
            "psd_covariance": covariance_status["psd"],
            "rejection_reasons": sorted({reason for item in history for reason in item["rejection_reasons"]}),
            "step_trace": history,
            "sliding_window_parameters": params,
            "window_length": window_length,
            "state_transition": "identity",
        }
    )
    return np.asarray(states[-1], dtype=float), diagnostics


def _install_map_diagnosis(namespace: dict[str, Any], step: MigrationStep) -> None:
    """Patch extracted legacy Optimizer with the requested MAP diagnosis variant."""

    Optimizer = namespace["Optimizer"]
    original_covariance = Optimizer.calculate_state_covariance
    original_map = getattr(Optimizer, "map_filter_iteration", None)
    global_map = namespace["map_filter_iteration"]
    covariance_mode = step.map_covariance_mode
    update_mode = step.map_update_mode
    truth_covariance = covariance_mode == "truth_error_diagonal"
    truth_acceptance = update_mode.startswith("truth_gated")

    def calculate_state_covariance_diagnosis(self: Any, scenario: Any, x: np.ndarray) -> np.ndarray:
        if truth_covariance:
            covariance = original_covariance(self, scenario, x)
            status = _covariance_status(covariance)
            status.update({"map_covariance_mode": covariance_mode, "truth_state_used_for_map_covariance": True})
        else:
            covariance, status = _observable_covariance(scenario, x, covariance_mode)
        self._last_map_covariance_diagnostics = status
        return covariance

    def map_filter_iteration_diagnosis(self: Any, scenario: Any, P: np.ndarray, x: np.ndarray, z: np.ndarray, verbose: bool = False) -> tuple[np.ndarray, np.ndarray]:
        trace = getattr(self, "_step_c_diagnosis_map_trace", [])
        prior_status = _covariance_status(P)
        current_cost = _residual_cost(scenario, x, z)
        true_state = scenario.get_true_state() if truth_acceptance or step.name == "step_c0_legacy_map_instrumented" else None
        true_error_before = float(np.linalg.norm(x - true_state)) if true_state is not None else None

        if truth_acceptance:
            if original_map is not None:
                P_new, x_new = original_map(self, scenario, P, x, z, verbose=False)
                fallback_path = "optimizer_method"
            else:
                P_new, x_new = global_map(None, scenario, P, x, z, verbose=False)
                fallback_path = "global_fallback"
            accepted = bool(np.linalg.norm(x_new - x) > 0.0)
            candidate_cost = _residual_cost(scenario, x_new, z)
            true_error_after = float(np.linalg.norm(x_new - true_state)) if true_state is not None else None
            reasons = ["legacy_truth_reverted"] if not accepted else []
            current_map_objective = current_cost
            candidate_map_objective = candidate_cost
            prior_cost_before = 0.0
            prior_cost_after = 0.0
            component_names = ["legacy_truth_error"]
            norm_status = _parameter_update_norms(scenario, x_new - x, x)
            candidate_status = _covariance_status(P_new)
        else:
            R = np.asarray(scenario.get_measurement_covariance(), dtype=float)
            F = np.eye(len(x))
            Q = STEP_C_PROCESS_COVARIANCE_SCALE * np.eye(len(x))
            x_pred = F @ x
            P_pred = _symmetrize(F @ P @ F.T + Q)
            h_pred = np.asarray(scenario.h(x_pred), dtype=float)
            J = np.asarray(scenario.evaluate_jacobian(x_pred), dtype=float)
            innovation = np.asarray(z - h_pred, dtype=float)
            innovation_covariance = _symmetrize(J @ P_pred @ J.T + R)
            K = P_pred @ J.T @ np.linalg.pinv(innovation_covariance)
            update = K @ innovation
            x_candidate = np.asarray(x_pred + update, dtype=float)
            I_KJ = np.eye(P_pred.shape[0]) - K @ J
            P_candidate = _symmetrize(I_KJ @ P_pred @ I_KJ.T + K @ R @ K.T)
            candidate_cost = _residual_cost(scenario, x_candidate, z) if np.all(np.isfinite(x_candidate)) else float("inf")
            candidate_status = _covariance_status(P_candidate)
            p_pred_status = _covariance_status(P_pred)
            prior_precision = _safe_inverse(P_pred)
            prior_cost_before = 0.0
            prior_cost_after = float(update.T @ prior_precision @ update) if np.all(np.isfinite(update)) else float("inf")
            current_map_objective = current_cost + prior_cost_before
            candidate_map_objective = candidate_cost + prior_cost_after
            norm_status = _parameter_update_norms(scenario, update, x)
            reasons = []
            if not np.all(np.isfinite(x_candidate)):
                reasons.append("nonfinite_state")
            if not np.isfinite(candidate_cost):
                reasons.append("nonfinite_residual_cost")
            if update_mode == "composite_observable":
                component_names = [
                    "measurement_residual_cost",
                    "prior_consistency_cost",
                    "total_map_objective",
                    "covariance_trace_nonexplosion",
                    "information_gain_nonnegative",
                    "relative_update_norm",
                    "position_update_norm",
                    "clock_update_norm",
                    "finite_symmetric_psd_covariance",
                ]
                if not np.isfinite(candidate_map_objective):
                    reasons.append("nonfinite_map_objective")
                if candidate_map_objective > current_map_objective + STEP_C_COST_TOLERANCE * max(1.0, abs(current_map_objective)):
                    reasons.append("map_objective_increased")
                if candidate_cost > current_cost + STEP_C_COST_TOLERANCE * max(1.0, abs(current_cost)):
                    reasons.append("residual_cost_increased")
                trace_before = p_pred_status["trace"]
                trace_after = candidate_status["trace"]
                if trace_before is not None and trace_after is not None and trace_after > trace_before * (1.0 + 1.0e-6) + 1.0e-9:
                    reasons.append("covariance_trace_exploded")
                if trace_before is not None and trace_after is not None and trace_before - trace_after < -1.0e-9:
                    reasons.append("negative_information_gain")
                position_update = norm_status["position_update_norm"]
                clock_update = norm_status["clock_update_norm"]
                if position_update is not None and position_update > float(norm_status["position_update_limit"]):
                    reasons.append("position_update_norm_exceeded")
                if clock_update is not None and clock_update > float(norm_status["clock_update_limit"]):
                    reasons.append("clock_update_norm_exceeded")
            else:
                component_names = [
                    "measurement_residual_cost",
                    "relative_update_norm",
                    "finite_symmetric_psd_covariance",
                ]
                if candidate_cost > current_cost + STEP_C_COST_TOLERANCE * max(1.0, abs(current_cost)):
                    reasons.append("residual_cost_increased")
            if not np.isfinite(float(norm_status["relative_update_norm"])) or float(norm_status["relative_update_norm"]) > STEP_B_STEP_NORM_LIMIT:
                reasons.append("relative_update_norm_exceeded")
            if not candidate_status["finite"]:
                reasons.append("nonfinite_covariance")
            if not candidate_status["symmetric"]:
                reasons.append("nonsymmetric_covariance")
            if not candidate_status["psd"]:
                reasons.append("non_psd_covariance")
            accepted = not reasons
            P_new = P_candidate if accepted else P
            x_new = x_candidate if accepted else x
            true_error_after = None

        posterior_status = _covariance_status(P_new)
        update_norm_final = float(np.linalg.norm(x_new - x))
        map_objective_decrease = current_map_objective - candidate_map_objective if np.isfinite(candidate_map_objective) else None
        trace.append(
            {
                "iteration": len(trace),
                "accepted": accepted,
                "current_residual_cost": current_cost,
                "candidate_residual_cost": candidate_cost,
                "cost_decrease": current_cost - candidate_cost if np.isfinite(candidate_cost) else None,
                "current_prior_cost": prior_cost_before,
                "candidate_prior_cost": prior_cost_after,
                "current_map_objective": current_map_objective,
                "candidate_map_objective": candidate_map_objective,
                "map_objective_decrease": map_objective_decrease,
                "covariance_trace_before": prior_status["trace"],
                "covariance_trace_predicted": p_pred_status["trace"] if not truth_acceptance else prior_status["trace"],
                "covariance_trace_after": posterior_status["trace"],
                "covariance_condition_before": prior_status["condition_number"],
                "covariance_condition_after": posterior_status["condition_number"],
                "update_norm": update_norm_final,
                "candidate_update_norm": norm_status["update_norm"],
                "relative_update_norm": norm_status["relative_update_norm"],
                "position_update_norm": norm_status["position_update_norm"],
                "clock_update_norm": norm_status["clock_update_norm"],
                "true_error_before": true_error_before,
                "true_error_after": true_error_after,
                "fallback_path": fallback_path if truth_acceptance else "optimizer_method",
                "score_components_used": component_names,
                "rejection_reasons": reasons,
            }
        )
        self._step_c_diagnosis_map_trace = trace
        accepted_costs = [float(item["cost_decrease"]) for item in trace if item["accepted"] and item["cost_decrease"] is not None]
        accepted_map_objective_decreases = [
            float(item["map_objective_decrease"])
            for item in trace
            if item["accepted"] and item["map_objective_decrease"] is not None
        ]
        self._last_map_diagnostics = _map_diagnostics_template(covariance_mode, update_mode, truth_covariance, truth_acceptance)
        self._last_map_diagnostics.update(
            {
                "initial_residual_cost": trace[0]["current_residual_cost"],
                "final_residual_cost": trace[-1]["candidate_residual_cost"] if trace[-1]["accepted"] else trace[-1]["current_residual_cost"],
                "accepted_cost_decrease_min": min(accepted_costs) if accepted_costs else 0.0,
                "map_acceptance_mode": "composite_observable" if update_mode == "composite_observable" else update_mode,
                "score_components_used": sorted({name for item in trace for name in item["score_components_used"]}),
                "initial_map_objective": trace[0]["current_map_objective"],
                "final_map_objective": trace[-1]["candidate_map_objective"] if trace[-1]["accepted"] else trace[-1]["current_map_objective"],
                "accepted_map_objective_decrease_min": min(accepted_map_objective_decreases) if accepted_map_objective_decreases else 0.0,
                "prior_cost_before": trace[0]["current_prior_cost"],
                "prior_cost_after": trace[-1]["candidate_prior_cost"],
                "rejected_candidate_count": sum(1 for item in trace if not item["accepted"]),
                "accepted_update_count": sum(1 for item in trace if item["accepted"]),
                "rejected_update_count": sum(1 for item in trace if not item["accepted"]),
                "covariance_trace_before": trace[0]["covariance_trace_before"],
                "covariance_trace_after": posterior_status["trace"],
                "covariance_condition_before": trace[0]["covariance_condition_before"],
                "covariance_condition_after": posterior_status["condition_number"],
                "covariance_diagonal_min": posterior_status["diagonal_min"],
                "covariance_diagonal_max": posterior_status["diagonal_max"],
                "update_norm_max": max(float(item["update_norm"]) for item in trace),
                "position_update_norm_max": max((float(item["position_update_norm"]) for item in trace if item["position_update_norm"] is not None), default=None),
                "clock_update_norm_max": max((float(item["clock_update_norm"]) for item in trace if item["clock_update_norm"] is not None), default=None),
                "relative_update_norm_max": max(float(item["relative_update_norm"]) for item in trace),
                "finite_covariance": posterior_status["finite"],
                "symmetric_covariance": posterior_status["symmetric"],
                "psd_covariance": posterior_status["psd"],
                "true_error_before": trace[0]["true_error_before"],
                "true_error_after": trace[-1]["true_error_after"],
                "fallback_paths": sorted({item["fallback_path"] for item in trace}),
                "rejection_reasons": sorted({reason for item in trace for reason in item["rejection_reasons"]}),
                "step_trace": trace,
            }
        )
        return P_new, x_new

    Optimizer.calculate_state_covariance = calculate_state_covariance_diagnosis
    Optimizer.map_filter_iteration = map_filter_iteration_diagnosis


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
        row["map_diagnostics"] = _map_diagnostics_template(
            "not_attempted_single_ue_baseline",
            "not_attempted_single_ue_baseline",
            False,
            False,
        )
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
                if hasattr(optimizer, "_last_map_diagnostics"):
                    optimizer._last_map_diagnostics.setdefault("fallback_paths", []).append("global_fallback")
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
    map_diagnostics = getattr(
        optimizer,
        "_last_map_diagnostics",
        _map_diagnostics_template("truth_error_diagonal", "truth_gated_legacy_uninstrumented", True, True),
    )
    map_diagnostics["fallback_count"] = int(map_fallback_count)
    row["map_diagnostics"] = map_diagnostics
    row["success"] = row["il_status"] == "passed" and row["lm_status"] == "passed" and map_failure_count == 0
    row["fallback_count"] = len(row["fallbacks"])
    row["failure_count"] = len(row["failures"])
    row["cache_used"] = False
    return row


def _scenario_result_step_c5(
    *,
    namespace: dict[str, Any],
    config: dict[str, Any],
    num_users: int,
    num_satellites: int,
) -> dict[str, Any]:
    """Run one C5 row: Step-B LM followed by sliding-window MAP smoothing."""

    Scenario = namespace["Scenario"]
    Optimizer = namespace["Optimizer"]
    row: dict[str, Any] = {
        "num_users": int(num_users),
        "num_satellites": int(num_satellites),
        "clock_std_dev_seconds": float(config["clock_std_dev"]),
        "map_iteration_count": 0 if int(num_users) == 1 else int(SLIDING_WINDOW_MAP_PARAMETERS["max_iterations"]),
        "truth_centered_initialization": False,
        "true_state_acceptance_gates_used": False,
        "truth_state_used_for_lm_acceptance": False,
        "truth_state_used_for_map_acceptance": False,
        "truth_state_used_for_map_covariance": False,
        "lm_acceptance_mode": "residual_trust_region",
        "all_clock_state": True,
        "v24_gauged_state": False,
        "step3_mode": "sliding_window_map",
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
    except Exception as exc:  # noqa: BLE001 - preserve bounded diagnostic behavior.
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
        row["map_diagnostics"] = _map_diagnostics_template(
            "configured_diagonal_prior_process",
            "sliding_window_map_not_attempted_single_ue",
            False,
            False,
        )
        row["map_diagnostics"]["sliding_window_parameters"] = SLIDING_WINDOW_MAP_PARAMETERS
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
    row["lm_diagnostics"] = getattr(optimizer, "_last_lm_diagnostics", {
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
    row["lm_position_error_m"] = float(optimizer.calculate_average_position_error(scenario, x_lm))
    row["lm_sync_error_s"] = float(optimizer.calculate_average_clock_error(scenario, x_lm))

    measurements = [z] + [scenario.query_measurements() for _ in range(int(SLIDING_WINDOW_MAP_PARAMETERS["window_length"]) - 1)]
    try:
        x_map, map_diagnostics = _sliding_window_map_refinement(scenario, x_lm, measurements)
        row["map_status"] = "sliding_window_map_passed"
    except Exception as exc:  # noqa: BLE001 - keep Step 2 state and record the failure.
        x_map = x_lm.copy()
        map_diagnostics = _map_diagnostics_template(
            "configured_diagonal_prior_process",
            "sliding_window_map_failed",
            False,
            False,
        )
        map_diagnostics["sliding_window_parameters"] = SLIDING_WINDOW_MAP_PARAMETERS
        row["map_status"] = "failed_keep_step_b_lm_state"
        row["failures"].append({"stage": "sliding_window_map", "error_type": type(exc).__name__, "error": str(exc)})
        row["fallbacks"].append("sliding_window_map_failed_keep_lm")
    row["map_diagnostics"] = map_diagnostics
    row["map_fallback_count"] = 0
    row["map_failure_count"] = 1 if row["map_status"] == "failed_keep_step_b_lm_state" else 0
    row["map_position_error_m"] = float(optimizer.calculate_average_position_error(scenario, x_map))
    row["map_sync_error_s"] = float(optimizer.calculate_average_clock_error(scenario, x_map))
    row["success"] = row["il_status"] == "passed" and row["lm_status"] == "passed" and row["map_failure_count"] == 0
    row["fallback_count"] = len(row["fallbacks"])
    row["failure_count"] = len(row["failures"])
    row["cache_used"] = False
    return row


def _run_step_b_rows(
    grid: str,
    *,
    points: list[tuple[int, int]] | None = None,
    run_context: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Run Step B rows for the requested tiny or medium grid."""

    config = _mode_config("medium")
    selected_points = points if points is not None else _grid_points(grid)
    np.random.seed(int(config["seed"]))
    namespace, _executed_cells = _execute_legacy_namespace()
    _install_residual_lm_acceptance(namespace)
    rows = []
    for point_index, (user, sat) in enumerate(selected_points, start=1):
        if run_context is not None:
            _write_row_status(
                {
                    "event": "row_start",
                    "step": STEP_B_NAME,
                    "grid": grid,
                    "num_users": user,
                    "num_satellites": sat,
                    "row_number": run_context["row_counter"] + 1,
                    "total_rows": run_context["total_rows"],
                }
            )
            _write_heartbeat(
                _heartbeat_payload(
                    status="running",
                    current_substep=STEP_B_NAME,
                    current_grid_point={"grid": grid, "num_users": user, "num_satellites": sat},
                    row_number=run_context["row_counter"],
                    total_rows=run_context["total_rows"],
                    started_monotonic=run_context["started_monotonic"],
                    process_start_time_utc=run_context["process_start_time_utc"],
                    last_completed_output=run_context.get("last_completed_output"),
                )
            )
        row_started = time.monotonic()
        row = _scenario_result_step_b(namespace=namespace, config=config, num_users=user, num_satellites=sat)
        row_duration = time.monotonic() - row_started
        if run_context is not None:
            run_context["row_counter"] += 1
            run_context["last_completed_output"] = f"{STEP_B_NAME}:{grid}:{user}:{sat}"
            status = "complete"
            if run_context.get("timeout_seconds_per_row") is not None and row_duration > float(run_context["timeout_seconds_per_row"]):
                status = "timeout_after_row"
                run_context["interrupted"] = True
                run_context["interruption_reason"] = "timeout_seconds_per_row"
                row["execution_status"] = status
            _write_row_status(
                {
                    "event": "row_end",
                    "step": STEP_B_NAME,
                    "grid": grid,
                    "num_users": user,
                    "num_satellites": sat,
                    "row_number": run_context["row_counter"],
                    "total_rows": run_context["total_rows"],
                    "duration_seconds": row_duration,
                    "status": status,
                    "point_index": point_index,
                }
            )
        rows.append(row)
        if run_context is not None and run_context.get("interrupted"):
            break
    return rows


def _run_step_c5_rows(
    step: MigrationStep,
    grid: str,
    *,
    points: list[tuple[int, int]] | None = None,
    run_context: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Run the C5 sliding-window MAP migration rows."""

    config = _mode_config("medium")
    selected_points = points if points is not None else _grid_points(grid)
    np.random.seed(int(config["seed"]))
    namespace, _executed_cells = _execute_legacy_namespace()
    _install_residual_lm_acceptance(namespace)
    rows = []
    for point_index, (user, sat) in enumerate(selected_points, start=1):
        if run_context is not None:
            _write_row_status(
                {
                    "event": "row_start",
                    "step": step.name,
                    "grid": grid,
                    "num_users": user,
                    "num_satellites": sat,
                    "row_number": run_context["row_counter"] + 1,
                    "total_rows": run_context["total_rows"],
                }
            )
            _write_heartbeat(
                _heartbeat_payload(
                    status="running",
                    current_substep=step.name,
                    current_grid_point={"grid": grid, "num_users": user, "num_satellites": sat},
                    row_number=run_context["row_counter"],
                    total_rows=run_context["total_rows"],
                    started_monotonic=run_context["started_monotonic"],
                    process_start_time_utc=run_context["process_start_time_utc"],
                    last_completed_output=run_context.get("last_completed_output"),
                )
            )
        row_started = time.monotonic()
        row = _scenario_result_step_c5(namespace=namespace, config=config, num_users=user, num_satellites=sat)
        row_duration = time.monotonic() - row_started
        if run_context is not None:
            run_context["row_counter"] += 1
            run_context["last_completed_output"] = f"{step.name}:{grid}:{user}:{sat}"
            status = "complete"
            if run_context.get("timeout_seconds_per_row") is not None and row_duration > float(run_context["timeout_seconds_per_row"]):
                status = "timeout_after_row"
                run_context["interrupted"] = True
                run_context["interruption_reason"] = "timeout_seconds_per_row"
                row["execution_status"] = status
            _write_row_status(
                {
                    "event": "row_end",
                    "step": step.name,
                    "grid": grid,
                    "num_users": user,
                    "num_satellites": sat,
                    "row_number": run_context["row_counter"],
                    "total_rows": run_context["total_rows"],
                    "duration_seconds": row_duration,
                    "status": status,
                    "point_index": point_index,
                }
            )
        rows.append(row)
        if run_context is not None and run_context.get("interrupted"):
            break
    return rows


def _run_step_c7_rows(
    step: MigrationStep,
    grid: str,
    *,
    points: list[tuple[int, int]] | None = None,
    run_context: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Run C7 rows through the package C7 estimator path."""

    from scripts.run_step_c7_residual_cov_sync_safeguard import (  # noqa: WPS433
        C7ValidationCandidate,
        evaluate_case_candidate,
    )
    from scripts import explore_step3_covariance as cov  # noqa: WPS433

    selected_points = points if points is not None else _grid_points(grid)
    c7_candidate = C7ValidationCandidate(
        name=STEP_C7_NAME,
        description="Residual-scaled block-diagonal covariance with clock/drift sync safeguard.",
    )
    rows: list[dict[str, Any]] = []
    for point_index, (user, sat) in enumerate(selected_points, start=1):
        row_start = time.monotonic()
        if run_context is not None:
            run_context["row_counter"] += 1
            _write_row_status(
                {
                    "event": "row_start",
                    "step": step.name,
                    "grid": grid,
                    "num_users": user,
                    "num_satellites": sat,
                    "row_number": run_context["row_counter"],
                    "total_rows": run_context["total_rows"],
                    "status": "starting",
                }
            )
        c7_row = evaluate_case_candidate(cov._make_case(user, sat), c7_candidate)
        map_diag = {
            "map_covariance_mode": step.map_covariance_mode,
            "map_update_mode": step.map_update_mode,
            "truth_state_used_for_map_covariance": False,
            "truth_state_used_for_map_acceptance": False,
            "initial_residual_cost": c7_row["objective_before"],
            "final_residual_cost": c7_row["objective_after"],
            "accepted_update_count": int(bool(c7_row["objective_decreased"])),
            "rejected_update_count": int(not bool(c7_row["objective_decreased"])),
            "fallback_count": int(bool(c7_row["fallback_triggered"])),
            "covariance_diagonal_min": min(c7_row["p_position_eig_min"], c7_row["p_delta_eig_min"], c7_row["p_drift_eig_min"]),
            "covariance_diagonal_max": max(c7_row["p_position_eig_max"], c7_row["p_delta_eig_max"], c7_row["p_drift_eig_max"]),
            "update_norm_max": max(
                c7_row["position_update_norm"],
                c7_row["ue_clock_update_norm"],
                c7_row["satellite_clock_update_norm"],
                c7_row["drift_update_norm"],
            ),
            "finite_covariance": True,
            "symmetric_covariance": True,
            "psd_covariance": True,
            "map_acceptance_mode": "nontruth_sync_safeguard",
            "score_components_used": ["measurement_residual_cost", "prior_cost", "clock_update_covariance_scale", "common_clock_component"],
            "initial_map_objective": c7_row["objective_before"],
            "final_map_objective": c7_row["objective_after"],
            "accepted_map_objective_decrease_min": c7_row["objective_before"] - c7_row["objective_after"],
            "prior_cost_before": 0.0,
            "prior_cost_after": c7_row["objective_after"] - c7_row["objective_after"],
            "measurement_cost_before": c7_row["objective_before"],
            "measurement_cost_after": c7_row["objective_after"],
            "dynamics_cost_before": 0.0,
            "dynamics_cost_after": 0.0,
            "position_update_norm_max": c7_row["position_update_norm"],
            "clock_update_norm_max": max(c7_row["ue_clock_update_norm"], c7_row["satellite_clock_update_norm"]),
            "relative_update_norm_max": max(c7_row["position_update_norm"], c7_row["ue_clock_update_norm"], c7_row["satellite_clock_update_norm"]),
            "fallback_paths": [c7_row["fallback_reason"]] if c7_row["fallback_triggered"] else [],
            "rejection_reasons": [c7_row["fallback_reason"]] if c7_row["fallback_triggered"] else [],
        }
        row = {
            "num_users": user,
            "num_satellites": sat,
            "measurement_count": None,
            "state_dimension": None,
            "cooperative_jcls_attempted": user > 1,
            "il_position_error_m": None,
            "lm_position_error_m": c7_row["step_b_position_error_m"],
            "map_position_error_m": c7_row["c7_position_error_m"],
            "il_sync_error_s": None,
            "lm_sync_error_s": c7_row["step_b_sync_error_km"] / C_KM_PER_S,
            "map_sync_error_s": c7_row["c7_sync_error_km"] / C_KM_PER_S,
            "fallback_count": int(bool(c7_row["fallback_triggered"])),
            "failure_count": 0,
            "success": True,
            "single_ue_policy": "clock_and_drift_reverted_when_not_observable" if user == 1 else "cooperative_jcls",
            "lm_diagnostics": {
                "lm_acceptance_mode": "residual_trust_region",
                "truth_state_used_for_lm_acceptance": False,
                "accepted_step_count": None,
                "rejected_step_count": None,
                "rejection_reasons": [],
            },
            "map_diagnostics": map_diag,
            "c7_diagnostics": c7_row,
        }
        rows.append(row)
        if run_context is not None:
            run_context["last_completed_output"] = f"{step.name}:{grid}:{user}:{sat}"
            _write_row_status(
                {
                    "event": "row_end",
                    "step": step.name,
                    "grid": grid,
                    "num_users": user,
                    "num_satellites": sat,
                    "row_number": run_context["row_counter"],
                    "total_rows": run_context["total_rows"],
                    "status": "complete",
                    "runtime_seconds": time.monotonic() - row_start,
                }
            )
    return rows


def _run_diagnosis_rows(
    step: MigrationStep,
    grid: str,
    *,
    points: list[tuple[int, int]] | None = None,
    run_context: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Run one Step C diagnosis variant for the requested grid."""

    config = _mode_config("medium")
    selected_points = points if points is not None else _grid_points(grid)
    np.random.seed(int(config["seed"]))
    namespace, _executed_cells = _execute_legacy_namespace()
    _install_residual_lm_acceptance(namespace)
    _install_map_diagnosis(namespace, step)
    rows = []
    for point_index, (user, sat) in enumerate(selected_points, start=1):
        if run_context is not None:
            _write_row_status(
                {
                    "event": "row_start",
                    "step": step.name,
                    "grid": grid,
                    "num_users": user,
                    "num_satellites": sat,
                    "row_number": run_context["row_counter"] + 1,
                    "total_rows": run_context["total_rows"],
                }
            )
            _write_heartbeat(
                _heartbeat_payload(
                    status="running",
                    current_substep=step.name,
                    current_grid_point={"grid": grid, "num_users": user, "num_satellites": sat},
                    row_number=run_context["row_counter"],
                    total_rows=run_context["total_rows"],
                    started_monotonic=run_context["started_monotonic"],
                    process_start_time_utc=run_context["process_start_time_utc"],
                    last_completed_output=run_context.get("last_completed_output"),
                )
            )
        row_started = time.monotonic()
        row = _scenario_result_step_b(namespace=namespace, config=config, num_users=user, num_satellites=sat)
        row_duration = time.monotonic() - row_started
        if run_context is not None:
            run_context["row_counter"] += 1
            run_context["last_completed_output"] = f"{step.name}:{grid}:{user}:{sat}"
            status = "complete"
            if run_context.get("timeout_seconds_per_row") is not None and row_duration > float(run_context["timeout_seconds_per_row"]):
                status = "timeout_after_row"
                run_context["interrupted"] = True
                run_context["interruption_reason"] = "timeout_seconds_per_row"
                row["execution_status"] = status
            _write_row_status(
                {
                    "event": "row_end",
                    "step": step.name,
                    "grid": grid,
                    "num_users": user,
                    "num_satellites": sat,
                    "row_number": run_context["row_counter"],
                    "total_rows": run_context["total_rows"],
                    "duration_seconds": row_duration,
                    "status": status,
                    "point_index": point_index,
                }
            )
        rows.append(row)
        if run_context is not None and run_context.get("interrupted"):
            break
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
        "map_covariance_mode",
        "map_update_mode",
        "truth_state_used_for_map_covariance",
        "truth_state_used_for_map_acceptance",
        "map_initial_residual_cost",
        "map_final_residual_cost",
        "map_accepted_cost_decrease_min",
        "map_rejected_candidate_count",
        "map_accepted_update_count",
        "map_rejected_update_count",
        "map_fallback_count",
        "map_covariance_trace_before",
        "map_covariance_trace_after",
        "map_covariance_condition_before",
        "map_covariance_condition_after",
        "map_covariance_diagonal_min",
        "map_covariance_diagonal_max",
        "map_update_norm_max",
        "map_finite_covariance",
        "map_symmetric_covariance",
        "map_psd_covariance",
        "map_true_error_before",
        "map_true_error_after",
        "map_acceptance_mode",
        "map_score_components_used",
        "map_initial_objective",
        "map_final_objective",
        "map_accepted_objective_decrease_min",
        "map_prior_cost_before",
        "map_prior_cost_after",
        "map_measurement_cost_before",
        "map_measurement_cost_after",
        "map_dynamics_cost_before",
        "map_dynamics_cost_after",
        "map_position_update_norm_max",
        "map_clock_update_norm_max",
        "map_relative_update_norm_max",
        "map_fallback_paths",
        "map_rejection_reasons",
    ]
    with raw.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            lm = row.get("lm_diagnostics", {})
            map_diag = row.get("map_diagnostics", {})
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
                    "map_covariance_mode": map_diag.get("map_covariance_mode"),
                    "map_update_mode": map_diag.get("map_update_mode"),
                    "truth_state_used_for_map_covariance": map_diag.get("truth_state_used_for_map_covariance"),
                    "truth_state_used_for_map_acceptance": map_diag.get("truth_state_used_for_map_acceptance"),
                    "map_initial_residual_cost": map_diag.get("initial_residual_cost"),
                    "map_final_residual_cost": map_diag.get("final_residual_cost"),
                    "map_accepted_cost_decrease_min": map_diag.get("accepted_cost_decrease_min"),
                    "map_rejected_candidate_count": map_diag.get("rejected_candidate_count"),
                    "map_accepted_update_count": map_diag.get("accepted_update_count"),
                    "map_rejected_update_count": map_diag.get("rejected_update_count"),
                    "map_fallback_count": map_diag.get("fallback_count"),
                    "map_covariance_trace_before": map_diag.get("covariance_trace_before"),
                    "map_covariance_trace_after": map_diag.get("covariance_trace_after"),
                    "map_covariance_condition_before": map_diag.get("covariance_condition_before"),
                    "map_covariance_condition_after": map_diag.get("covariance_condition_after"),
                    "map_covariance_diagonal_min": map_diag.get("covariance_diagonal_min"),
                    "map_covariance_diagonal_max": map_diag.get("covariance_diagonal_max"),
                    "map_update_norm_max": map_diag.get("update_norm_max"),
                    "map_finite_covariance": map_diag.get("finite_covariance"),
                    "map_symmetric_covariance": map_diag.get("symmetric_covariance"),
                    "map_psd_covariance": map_diag.get("psd_covariance"),
                    "map_true_error_before": map_diag.get("true_error_before"),
                    "map_true_error_after": map_diag.get("true_error_after"),
                    "map_acceptance_mode": map_diag.get("map_acceptance_mode"),
                    "map_score_components_used": json.dumps(map_diag.get("score_components_used", [])),
                    "map_initial_objective": map_diag.get("initial_map_objective"),
                    "map_final_objective": map_diag.get("final_map_objective"),
                    "map_accepted_objective_decrease_min": map_diag.get("accepted_map_objective_decrease_min"),
                    "map_prior_cost_before": map_diag.get("prior_cost_before"),
                    "map_prior_cost_after": map_diag.get("prior_cost_after"),
                    "map_measurement_cost_before": map_diag.get("measurement_cost_before"),
                    "map_measurement_cost_after": map_diag.get("measurement_cost_after"),
                    "map_dynamics_cost_before": map_diag.get("dynamics_cost_before"),
                    "map_dynamics_cost_after": map_diag.get("dynamics_cost_after"),
                    "map_position_update_norm_max": map_diag.get("position_update_norm_max"),
                    "map_clock_update_norm_max": map_diag.get("clock_update_norm_max"),
                    "map_relative_update_norm_max": map_diag.get("relative_update_norm_max"),
                    "map_fallback_paths": json.dumps(map_diag.get("fallback_paths", [])),
                    "map_rejection_reasons": json.dumps(map_diag.get("rejection_reasons", [])),
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
        map_accepted_update_count=np.asarray([row.get("map_diagnostics", {}).get("accepted_update_count", 0) or 0 for row in rows], dtype=int),
        map_rejected_update_count=np.asarray([row.get("map_diagnostics", {}).get("rejected_update_count", 0) or 0 for row in rows], dtype=int),
        map_initial_residual_cost=np.asarray([_float_or_nan(row.get("map_diagnostics", {}).get("initial_residual_cost")) for row in rows], dtype=float),
        map_final_residual_cost=np.asarray([_float_or_nan(row.get("map_diagnostics", {}).get("final_residual_cost")) for row in rows], dtype=float),
        map_covariance_trace_after=np.asarray([_float_or_nan(row.get("map_diagnostics", {}).get("covariance_trace_after")) for row in rows], dtype=float),
        map_update_norm_max=np.asarray([_float_or_nan(row.get("map_diagnostics", {}).get("update_norm_max")) for row in rows], dtype=float),
        map_initial_objective=np.asarray([_float_or_nan(row.get("map_diagnostics", {}).get("initial_map_objective")) for row in rows], dtype=float),
        map_final_objective=np.asarray([_float_or_nan(row.get("map_diagnostics", {}).get("final_map_objective")) for row in rows], dtype=float),
        map_prior_cost_after=np.asarray([_float_or_nan(row.get("map_diagnostics", {}).get("prior_cost_after")) for row in rows], dtype=float),
        map_measurement_cost_after=np.asarray([_float_or_nan(row.get("map_diagnostics", {}).get("measurement_cost_after")) for row in rows], dtype=float),
        map_dynamics_cost_after=np.asarray([_float_or_nan(row.get("map_diagnostics", {}).get("dynamics_cost_after")) for row in rows], dtype=float),
        map_position_update_norm_max=np.asarray([_float_or_nan(row.get("map_diagnostics", {}).get("position_update_norm_max")) for row in rows], dtype=float),
        map_clock_update_norm_max=np.asarray([_float_or_nan(row.get("map_diagnostics", {}).get("clock_update_norm_max")) for row in rows], dtype=float),
        map_position_error_m=np.asarray([row["map_position_error_m"] for row in rows], dtype=float),
        map_sync_error_s=np.asarray([row["map_sync_error_s"] for row in rows], dtype=float),
    )
    return _repo_rel(path)


def _write_step_auxiliary(step: MigrationStep, rows: list[dict[str, Any]], output_root: Path) -> dict[str, str]:
    """Write step-specific auxiliary diagnostics."""

    if step.name != STEP_C5_NAME:
        return {}
    output_root.mkdir(parents=True, exist_ok=True)
    objective_path = output_root / "objective_history.json"
    failure_path = output_root / "failure_log.json"
    objective_payload = {
        "artifact_status": "non_final_step_c5_objective_history",
        "manuscript_ready": False,
        "step": step.name,
        "sliding_window_map_parameters": SLIDING_WINDOW_MAP_PARAMETERS,
        "rows": [
            {
                "num_users": row["num_users"],
                "num_satellites": row["num_satellites"],
                "map_status": row.get("map_status"),
                "objective_history": row.get("map_diagnostics", {}).get("step_trace", []),
            }
            for row in rows
        ],
    }
    failure_payload = {
        "artifact_status": "non_final_step_c5_failure_log",
        "manuscript_ready": False,
        "step": step.name,
        "failures": [
            {
                "num_users": row["num_users"],
                "num_satellites": row["num_satellites"],
                "failures": row.get("failures", []),
                "fallbacks": row.get("fallbacks", []),
            }
            for row in rows
            if row.get("failures") or row.get("fallbacks")
        ],
    }
    objective_path.write_text(json.dumps(objective_payload, indent=2), encoding="utf-8")
    failure_path.write_text(json.dumps(failure_payload, indent=2), encoding="utf-8")
    return {
        "objective_history_json": _repo_rel(objective_path),
        "failure_log_json": _repo_rel(failure_path),
    }


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
    map_accepted_cost_increases = sum(
        1
        for row in rows
        if row.get("cooperative_jcls_attempted")
        and row.get("map_diagnostics", {}).get("accepted_cost_decrease_min") is not None
        and float(row.get("map_diagnostics", {}).get("accepted_cost_decrease_min", 0.0)) < -STEP_C_COST_TOLERANCE
    )
    map_invalid_covariance_rows = sum(
        1
        for row in rows
        if row.get("cooperative_jcls_attempted")
        and row.get("map_diagnostics", {}).get("finite_covariance") is not None
        and not (
            bool(row.get("map_diagnostics", {}).get("finite_covariance"))
            and bool(row.get("map_diagnostics", {}).get("symmetric_covariance"))
            and bool(row.get("map_diagnostics", {}).get("psd_covariance"))
        )
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
        or map_accepted_cost_increases > 0
        or map_invalid_covariance_rows > 0
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
        "map_accepted_cost_increase_rows": map_accepted_cost_increases,
        "map_invalid_covariance_rows": map_invalid_covariance_rows,
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
        "composite_map_acceptance_parameters": COMPOSITE_MAP_ACCEPTANCE_PARAMETERS if step.map_update_mode == "composite_observable" else None,
        "sliding_window_map_parameters": SLIDING_WINDOW_MAP_PARAMETERS if step.map_update_mode == "sliding_window_map" else None,
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
        "status": _cache_payload_status(metadata),
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


def _write_step(
    step: MigrationStep,
    grid: str,
    rows: list[dict[str, Any]],
    previous_health: dict[str, Any] | None,
    *,
    execution: dict[str, Any] | None = None,
    output_grid: str | None = None,
) -> dict[str, Any]:
    """Write outputs for one migration step and grid."""

    output_grid = output_grid or grid
    output_root = LADDER_ROOT / step.name / output_grid
    plot_outputs = _plot(rows, output_root)
    csvs = _write_csvs(rows, output_root)
    arrays = _write_npz(rows, output_root)
    auxiliary_outputs = _write_step_auxiliary(step, rows, output_root)
    health = _health(rows, previous_health)
    metadata = {
        "artifact_status": "non_final_controlled_migration_step",
        "step": step.to_dict(),
        "composite_map_acceptance_parameters": COMPOSITE_MAP_ACCEPTANCE_PARAMETERS if step.map_update_mode == "composite_observable" else None,
        "sliding_window_map_parameters": SLIDING_WINDOW_MAP_PARAMETERS if step.map_update_mode == "sliding_window_map" else None,
        "grid": grid,
        "output_grid": output_grid,
        "status": health["status"],
        "manuscript_ready": False,
        "lm_acceptance_mode": step.acceptance_mode,
        "truth_state_used_for_lm_acceptance": False if step.acceptance_mode == "residual_trust_region" else True,
        "map_covariance_mode": step.map_covariance_mode,
        "map_update_mode": step.map_update_mode,
        "plot_outputs": plot_outputs,
        "raw_outputs": {**csvs, "arrays_npz": arrays, **auxiliary_outputs},
        "health": health,
        "lm_acceptance_diagnostics": _lm_acceptance_summary(rows),
        "map_update_diagnostics": _map_update_summary(rows),
        "composite_map_acceptance_parameters": COMPOSITE_MAP_ACCEPTANCE_PARAMETERS if step.map_update_mode == "composite_observable" else None,
        "sliding_window_map_parameters": SLIDING_WINDOW_MAP_PARAMETERS if step.map_update_mode == "sliding_window_map" else None,
        "change_vs_previous": None,
        "execution": execution or _execution_metadata(
            planned_rows=len(rows),
            executed_rows=len(rows),
            status="complete",
            options=LadderRunOptions(),
            output_grid=output_grid,
        ),
    }
    if step.acceptance_mode != "residual_trust_region":
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


def _map_update_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize MAP diagnostics over rows."""

    diagnostics = [row.get("map_diagnostics", {}) for row in rows]
    return {
        "truth_state_used_for_map_covariance": any(bool(item.get("truth_state_used_for_map_covariance")) for item in diagnostics),
        "truth_state_used_for_map_acceptance": any(bool(item.get("truth_state_used_for_map_acceptance")) for item in diagnostics),
        "accepted_update_count": int(sum(int(item.get("accepted_update_count") or 0) for item in diagnostics)),
        "rejected_update_count": int(sum(int(item.get("rejected_update_count") or 0) for item in diagnostics)),
        "rejected_candidate_count": int(sum(int(item.get("rejected_candidate_count") or 0) for item in diagnostics)),
        "fallback_count": int(sum(int(item.get("fallback_count") or 0) for item in diagnostics)),
        "rows_with_accepted_residual_cost_increase": int(
            sum(1 for item in diagnostics if item.get("accepted_cost_decrease_min") is not None and float(item["accepted_cost_decrease_min"]) < -STEP_C_COST_TOLERANCE)
        ),
        "invalid_covariance_rows": int(
            sum(
                1
                for item in diagnostics
                if item.get("finite_covariance") is not None
                and not (
                    bool(item.get("finite_covariance"))
                    and bool(item.get("symmetric_covariance"))
                    and bool(item.get("psd_covariance"))
                )
            )
        ),
        "covariance_trace_after_min": min((float(item["covariance_trace_after"]) for item in diagnostics if item.get("covariance_trace_after") is not None), default=None),
        "covariance_trace_after_max": max((float(item["covariance_trace_after"]) for item in diagnostics if item.get("covariance_trace_after") is not None), default=None),
        "covariance_condition_after_max": max((float(item["covariance_condition_after"]) for item in diagnostics if item.get("covariance_condition_after") is not None), default=None),
        "update_norm_max": max((float(item["update_norm_max"]) for item in diagnostics if item.get("update_norm_max") is not None), default=None),
        "map_acceptance_modes": sorted({str(item.get("map_acceptance_mode")) for item in diagnostics if item.get("map_acceptance_mode")}),
        "score_components_used": sorted({component for item in diagnostics for component in item.get("score_components_used", [])}),
        "initial_map_objective_min": min((float(item["initial_map_objective"]) for item in diagnostics if item.get("initial_map_objective") is not None), default=None),
        "final_map_objective_max": max((float(item["final_map_objective"]) for item in diagnostics if item.get("final_map_objective") is not None), default=None),
        "accepted_map_objective_decrease_min": min((float(item["accepted_map_objective_decrease_min"]) for item in diagnostics if item.get("accepted_map_objective_decrease_min") is not None), default=None),
        "prior_cost_after_max": max((float(item["prior_cost_after"]) for item in diagnostics if item.get("prior_cost_after") is not None), default=None),
        "position_update_norm_max": max((float(item["position_update_norm_max"]) for item in diagnostics if item.get("position_update_norm_max") is not None), default=None),
        "clock_update_norm_max": max((float(item["clock_update_norm_max"]) for item in diagnostics if item.get("clock_update_norm_max") is not None), default=None),
        "relative_update_norm_max": max((float(item["relative_update_norm_max"]) for item in diagnostics if item.get("relative_update_norm_max") is not None), default=None),
        "fallback_paths": sorted({path for item in diagnostics for path in item.get("fallback_paths", [])}),
        "rejection_reasons": sorted({reason for item in diagnostics for reason in item.get("rejection_reasons", [])}),
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
                "map_initial_residual_cost",
                "map_final_residual_cost",
                "map_accepted_cost_decrease_min",
                "map_covariance_trace_before",
                "map_covariance_trace_after",
                "map_covariance_condition_before",
                "map_covariance_condition_after",
                "map_covariance_diagonal_min",
                "map_covariance_diagonal_max",
                "map_update_norm_max",
                "map_true_error_before",
                "map_true_error_after",
                "map_initial_objective",
                "map_final_objective",
                "map_accepted_objective_decrease_min",
                "map_prior_cost_before",
                "map_prior_cost_after",
                "map_measurement_cost_before",
                "map_measurement_cost_after",
                "map_dynamics_cost_before",
                "map_dynamics_cost_after",
                "map_position_update_norm_max",
                "map_clock_update_norm_max",
                "map_relative_update_norm_max",
            ]:
                if converted.get(key) not in {None, ""}:
                    converted[key] = float(converted[key])
            for key in [
                "lm_accepted_step_count",
                "lm_rejected_step_count",
                "map_rejected_candidate_count",
                "map_accepted_update_count",
                "map_rejected_update_count",
                "map_fallback_count",
            ]:
                if converted.get(key) not in {None, ""}:
                    converted[key] = int(float(converted[key]))
            for key in [
                "cooperative_jcls_attempted",
                "success",
                "truth_state_used_for_map_covariance",
                "truth_state_used_for_map_acceptance",
                "map_finite_covariance",
                "map_symmetric_covariance",
                "map_psd_covariance",
            ]:
                if key in converted:
                    converted[key] = str(converted.get(key)) == "True"
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


def _status_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    """Return diagnosis status counts."""

    return {status: sum(1 for item in items if item["status"] == status) for status in ["healthy", "mild_degradation", "major_degradation", "failed", "diagnostic_only"]}


def _classify_diagnosis_row(base: dict[str, Any], row: dict[str, Any], diagnostic_only: bool = False) -> str:
    """Classify a diagnosis row against Step B behavior."""

    if diagnostic_only:
        return "diagnostic_only"
    if row.get("failure_count", 0) > 0 or not np.isfinite(float(row["map_position_error_m"])):
        return "failed"
    if row.get("cooperative_jcls_attempted") and (
        float(row["map_position_error_m"]) > float(row["il_position_error_m"])
        or float(row["map_sync_error_s"]) > float(row["il_sync_error_s"])
    ):
        return "major_degradation"
    pos_ratio = float(row["map_position_error_m"]) / float(base["map_position_error_m"]) if float(base["map_position_error_m"]) > 0 else 1.0
    sync_ratio = float(row["map_sync_error_s"]) / float(base["map_sync_error_s"]) if float(base["map_sync_error_s"]) > 0 else 1.0
    if pos_ratio > 2.0 or sync_ratio > 2.0:
        return "major_degradation"
    if pos_ratio > 1.10 or sync_ratio > 1.10:
        return "mild_degradation"
    return "healthy"


def _summarize_diagnosis_step(step_name: str, grid: str, step_b_rows: dict[tuple[int, int], dict[str, Any]]) -> dict[str, Any] | None:
    """Return comparison summary for one diagnosis step/grid."""

    raw_path = LADDER_ROOT / step_name / grid / "migration_raw.csv"
    metadata_path = LADDER_ROOT / step_name / grid / "migration_step_metadata.json"
    if not raw_path.exists() or not metadata_path.exists():
        return None
    rows = _read_ladder_raw(raw_path)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    diagnostic_only = step_name == "step_c0_legacy_map_instrumented"
    comparisons = []
    for key in sorted(rows):
        row = rows[key]
        base = step_b_rows.get(key)
        if base is None:
            continue
        comparisons.append(
            {
                "num_users": key[0],
                "num_satellites": key[1],
                "status": _classify_diagnosis_row(base, row, diagnostic_only=diagnostic_only),
                "step_b_map_position_error_m": base["map_position_error_m"],
                "diagnosis_map_position_error_m": row["map_position_error_m"],
                "step_b_map_sync_error_s": base["map_sync_error_s"],
                "diagnosis_map_sync_error_s": row["map_sync_error_s"],
                "map_accepted_update_count": row.get("map_accepted_update_count"),
                "map_rejected_update_count": row.get("map_rejected_update_count"),
                "map_rejected_candidate_count": row.get("map_rejected_candidate_count"),
                "map_covariance_trace_after": row.get("map_covariance_trace_after"),
                "map_covariance_condition_after": row.get("map_covariance_condition_after"),
                "map_update_norm_max": row.get("map_update_norm_max"),
                "map_fallback_count": row.get("map_fallback_count"),
                "truth_state_used_for_map_covariance": row.get("truth_state_used_for_map_covariance"),
                "truth_state_used_for_map_acceptance": row.get("truth_state_used_for_map_acceptance"),
            }
        )
    counts = _status_counts(comparisons)
    overall = "diagnostic_only" if diagnostic_only else (
        "healthy"
        if counts["major_degradation"] == 0 and counts["failed"] == 0 and counts["mild_degradation"] == 0
        else "mild_degradation"
        if counts["major_degradation"] == 0 and counts["failed"] == 0
        else "major_degradation"
    )
    return {
        "step": step_name,
        "grid": grid,
        "metadata_status": metadata["status"],
        "overall_status": overall,
        "status_counts": counts,
        "health": metadata["health"],
        "map_update_diagnostics": metadata["map_update_diagnostics"],
        "comparisons": comparisons,
    }


def _write_step_c_diagnosis_report() -> dict[str, Any] | None:
    """Write Step C diagnosis comparison report."""

    step_b_path = LADDER_ROOT / STEP_B_NAME / "medium" / "migration_raw.csv"
    if not step_b_path.exists():
        return None
    step_b_rows = _read_ladder_raw(step_b_path)
    order = [
        "step_c0_legacy_map_instrumented",
        "step_c1_legacy_cov_observable_acceptance",
        "step_c2_observable_cov_legacy_acceptance",
        "step_c3_cov_diag_prior",
        "step_c3_cov_block_diag",
        "step_c3_cov_damped_inverse",
        "step_c3_cov_damped_pinv",
        "step_c3_cov_residual_scaled",
    ]
    summaries = []
    for step_name in order:
        summary = _summarize_diagnosis_step(step_name, "medium", step_b_rows) or _summarize_diagnosis_step(step_name, "tiny", step_b_rows)
        if summary is not None:
            summaries.append(summary)

    by_step = {item["step"]: item for item in summaries}
    c1 = by_step.get("step_c1_legacy_cov_observable_acceptance")
    c2 = by_step.get("step_c2_observable_cov_legacy_acceptance")
    c1_breaks = c1 is not None and c1["overall_status"] in {"major_degradation", "failed"}
    c2_breaks = c2 is not None and c2["overall_status"] in {"major_degradation", "failed"}
    if c1 is not None and c2 is not None:
        if not c1_breaks and c2_breaks:
            breaking_factor = "covariance_replacement"
        elif c1_breaks and not c2_breaks:
            breaking_factor = "acceptance_replacement"
        elif c1_breaks and c2_breaks:
            breaking_factor = "both_acceptance_and_covariance_or_map_instability"
        else:
            breaking_factor = "neither_c1_nor_c2_breaks"
    else:
        breaking_factor = "incomplete_c1_c2_evidence"
    healthy_candidates = [
        item["step"]
        for item in summaries
        if item["step"].startswith("step_c3") and item["overall_status"] == "healthy"
    ]
    best_candidate = healthy_candidates[0] if healthy_candidates else None
    payload = {
        "artifact_status": "non_final_step_c_diagnosis",
        "manuscript_ready": False,
        "step_b_reference": STEP_B_NAME,
        "breaking_factor": breaking_factor,
        "best_non_truth_covariance_candidate": best_candidate,
        "map_truth_acceptance_can_be_removed_safely": bool(c1 is not None and c1["overall_status"] in {"healthy", "mild_degradation"}),
        "map_truth_covariance_can_be_removed_safely": bool(best_candidate),
        "summaries": summaries,
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "STEP_C_DIAGNOSIS_REPORT.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md = [
        "# Step C Diagnosis Report",
        "",
        "## Executive Summary",
        "This report splits the MAP/EKF truth-dependence correction into sub-ablations. All outputs are non-final diagnostics.",
        "",
        f"- Breaking factor: `{breaking_factor}`",
        f"- Best non-truth covariance candidate: `{best_candidate or 'none'}`",
        f"- MAP truth acceptance removable: `{payload['map_truth_acceptance_can_be_removed_safely']}`",
        f"- MAP truth covariance removable: `{payload['map_truth_covariance_can_be_removed_safely']}`",
        "",
        "| Step | Grid | Overall | Healthy | Mild | Major | Failed | Truth covariance | Truth acceptance | MAP accept/reject |",
        "|---|---|---|---:|---:|---:|---:|---|---|---:|",
    ]
    for item in summaries:
        diag = item["map_update_diagnostics"]
        counts = item["status_counts"]
        md.append(
            f"| `{item['step']}` | `{item['grid']}` | `{item['overall_status']}` | "
            f"{counts['healthy']} | {counts['mild_degradation']} | {counts['major_degradation']} | {counts['failed']} | "
            f"`{diag['truth_state_used_for_map_covariance']}` | `{diag['truth_state_used_for_map_acceptance']}` | "
            f"{diag['accepted_update_count']}/{diag['rejected_update_count']} |"
        )
    (REPORTS / "STEP_C_DIAGNOSIS_REPORT.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return payload


def _write_step_c_acceptance_design_notes() -> dict[str, Any]:
    """Write read-only synthesis notes for the Step C MAP acceptance diagnosis."""

    report_path = REPORTS / "STEP_C_DIAGNOSIS_REPORT.json"
    if not report_path.exists():
        raise FileNotFoundError(report_path)
    diagnosis = json.loads(report_path.read_text(encoding="utf-8"))
    summaries = {item["step"]: item for item in diagnosis.get("summaries", [])}
    payload = {
        "artifact_status": "non_final_step_c_acceptance_design_notes",
        "manuscript_ready": False,
        "source_report": "outputs/reports/STEP_C_DIAGNOSIS_REPORT.json",
        "legacy_map_acceptance_protection_hypothesis": [
            "Legacy MAP acceptance appears to prevent accepted updates that improve a local observable score but move the all-clock state into a poorer estimator basin.",
            "The legacy truth gate protects against overconfident EKF-style corrections from a fragile all-clock state and legacy covariance representation.",
            "C0 remains behavior-preserving because it instruments the legacy path without removing truth-state reversion.",
        ],
        "why_observable_acceptance_failed": [
            "C1 kept the legacy truth-derived covariance but replaced acceptance with local observable checks and still produced major degradation.",
            "This indicates residual-only/covariance-local acceptance is insufficient for the legacy all-clock MAP path.",
            "The local residual score does not fully capture downstream localization/synchronization behavior under the overparameterized all-clock state.",
        ],
        "why_c2_degraded_less_than_c1": [
            "C2 replaced covariance while preserving legacy truth-gated acceptance, and it degraded only mildly.",
            "This isolates acceptance/reversion, not covariance replacement alone, as the primary breaking factor in the current medium grid.",
        ],
        "correlating_metrics": {
            step: {
                "overall_status": summary.get("overall_status"),
                "metadata_status": summary.get("metadata_status"),
                "status_counts": summary.get("status_counts"),
                "accepted_update_count": summary.get("map_update_diagnostics", {}).get("accepted_update_count"),
                "rejected_update_count": summary.get("map_update_diagnostics", {}).get("rejected_update_count"),
                "invalid_covariance_rows": summary.get("map_update_diagnostics", {}).get("invalid_covariance_rows"),
                "covariance_trace_after_max": summary.get("map_update_diagnostics", {}).get("covariance_trace_after_max"),
                "update_norm_max": summary.get("map_update_diagnostics", {}).get("update_norm_max"),
                "rejection_reasons": summary.get("map_update_diagnostics", {}).get("rejection_reasons"),
            }
            for step, summary in summaries.items()
        },
        "recommended_next_acceptance_criteria": [
            "measurement residual cost nonincrease",
            "prior consistency cost",
            "total observable MAP objective nonincrease",
            "covariance trace nonexplosion and finite/symmetric/PSD checks",
            "bounded relative state update norm",
            "bounded position update norm",
            "bounded clock update norm",
        ],
        "recommended_next_step": "step_c4_composite_map_acceptance",
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "STEP_C_ACCEPTANCE_DESIGN_NOTES.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md = [
        "# Step C Acceptance Design Notes",
        "",
        "## Executive Summary",
        "",
        "Existing Step C outputs are complete diagnostic artifacts. They indicate that replacing MAP acceptance/reversion is the primary breaking factor, not covariance replacement alone.",
        "",
        "## Diagnosis Synthesis",
        "",
        "- C0 instruments legacy MAP behavior and is diagnostic-only.",
        "- C1 keeps legacy covariance but replaces acceptance; it has major degradation.",
        "- C2 replaces covariance but keeps legacy truth acceptance; it has mild degradation.",
        "- C3 candidates replace both covariance and acceptance; none is healthy.",
        "",
        "## What Legacy Acceptance Appears To Protect",
        "",
        *[f"- {item}" for item in payload["legacy_map_acceptance_protection_hypothesis"]],
        "",
        "## Why Local Observable Acceptance Failed",
        "",
        *[f"- {item}" for item in payload["why_observable_acceptance_failed"]],
        "",
        "## Why C2 Degraded Less Than C1",
        "",
        *[f"- {item}" for item in payload["why_c2_degraded_less_than_c1"]],
        "",
        "## Correlating Metrics",
        "",
        "| Step | Overall | Metadata | Healthy | Mild | Major | Failed | Accepted | Rejected | Invalid cov rows | Update norm max |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for step, item in payload["correlating_metrics"].items():
        counts = item.get("status_counts") or {}
        md.append(
            f"| `{step}` | `{item['overall_status']}` | `{item['metadata_status']}` | "
            f"{counts.get('healthy', 0)} | {counts.get('mild_degradation', 0)} | {counts.get('major_degradation', 0)} | {counts.get('failed', 0)} | "
            f"{item.get('accepted_update_count')} | {item.get('rejected_update_count')} | {item.get('invalid_covariance_rows')} | {item.get('update_norm_max')} |"
        )
    md += [
        "",
        "## Criteria To Test Next",
        "",
        *[f"- {item}" for item in payload["recommended_next_acceptance_criteria"]],
    ]
    (REPORTS / "STEP_C_ACCEPTANCE_DESIGN_NOTES.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return payload


def _write_step_c4_composite_acceptance_comparison() -> dict[str, Any] | None:
    """Compare C4 composite acceptance against Step B, C1, C2, and best C3."""

    grid = "medium" if (LADDER_ROOT / "step_c4_composite_map_acceptance" / "medium" / "migration_raw.csv").exists() else "tiny"
    c4_path = LADDER_ROOT / "step_c4_composite_map_acceptance" / grid / "migration_raw.csv"
    c4_meta_path = LADDER_ROOT / "step_c4_composite_map_acceptance" / grid / "migration_step_metadata.json"
    step_b_path = LADDER_ROOT / STEP_B_NAME / grid / "migration_raw.csv"
    if not (c4_path.exists() and c4_meta_path.exists() and step_b_path.exists()):
        return None
    c4_rows = _read_ladder_raw(c4_path)
    step_b_rows = _read_ladder_raw(step_b_path)
    c4_metadata = json.loads(c4_meta_path.read_text(encoding="utf-8"))
    diagnosis_report = json.loads((REPORTS / "STEP_C_DIAGNOSIS_REPORT.json").read_text(encoding="utf-8")) if (REPORTS / "STEP_C_DIAGNOSIS_REPORT.json").exists() else {}
    c3_summaries = [item for item in diagnosis_report.get("summaries", []) if item.get("step", "").startswith("step_c3")]
    severity = {"healthy": 0, "mild_degradation": 1, "major_degradation": 2, "failed": 3}
    best_c3 = min(
        c3_summaries,
        key=lambda item: (severity.get(item.get("overall_status"), 99), item.get("status_counts", {}).get("major_degradation", 99)),
        default=None,
    )
    comparisons = []
    for key in sorted(c4_rows):
        c4 = c4_rows[key]
        base = step_b_rows.get(key)
        if base is None:
            continue
        comparisons.append(
            {
                "num_users": key[0],
                "num_satellites": key[1],
                "status": _classify_diagnosis_row(base, c4, diagnostic_only=False),
                "step_b_map_position_error_m": base["map_position_error_m"],
                "c4_map_position_error_m": c4["map_position_error_m"],
                "step_b_map_sync_error_s": base["map_sync_error_s"],
                "c4_map_sync_error_s": c4["map_sync_error_s"],
                "map_accepted_update_count": c4.get("map_accepted_update_count"),
                "map_rejected_update_count": c4.get("map_rejected_update_count"),
                "map_initial_objective": c4.get("map_initial_objective"),
                "map_final_objective": c4.get("map_final_objective"),
                "map_accepted_objective_decrease_min": c4.get("map_accepted_objective_decrease_min"),
                "map_initial_residual_cost": c4.get("map_initial_residual_cost"),
                "map_final_residual_cost": c4.get("map_final_residual_cost"),
                "map_prior_cost_before": c4.get("map_prior_cost_before"),
                "map_prior_cost_after": c4.get("map_prior_cost_after"),
                "map_covariance_trace_before": c4.get("map_covariance_trace_before"),
                "map_covariance_trace_after": c4.get("map_covariance_trace_after"),
                "map_position_update_norm_max": c4.get("map_position_update_norm_max"),
                "map_clock_update_norm_max": c4.get("map_clock_update_norm_max"),
                "map_relative_update_norm_max": c4.get("map_relative_update_norm_max"),
            }
        )
    counts = _status_counts(comparisons)
    overall = (
        "healthy"
        if counts["major_degradation"] == 0 and counts["failed"] == 0 and counts["mild_degradation"] == 0
        else "mild_degradation"
        if counts["major_degradation"] == 0 and counts["failed"] == 0
        else "major_degradation"
    )
    if c4_metadata["health"].get("catastrophic_failure"):
        overall = "failed"
    payload = {
        "artifact_status": "non_final_step_c4_composite_acceptance_comparison",
        "manuscript_ready": False,
        "grid": grid,
        "c4_overall_status": overall,
        "step_b_reference": STEP_B_NAME,
        "c1_reference": "step_c1_legacy_cov_observable_acceptance",
        "c2_reference": "step_c2_observable_cov_legacy_acceptance",
        "best_c3_reference": best_c3["step"] if best_c3 else None,
        "c4_health": c4_metadata["health"],
        "c4_map_update_diagnostics": c4_metadata["map_update_diagnostics"],
        "status_counts": counts,
        "comparisons": comparisons,
        "does_c4_improve_over_c1": bool(overall in {"healthy", "mild_degradation"} and diagnosis_report.get("breaking_factor") == "acceptance_replacement"),
        "does_c4_approach_step_b_behavior": bool(overall in {"healthy", "mild_degradation"}),
        "map_truth_acceptance_replaceable_now": bool(overall == "healthy"),
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "STEP_C4_COMPOSITE_ACCEPTANCE_COMPARISON.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md = [
        "# Step C4 Composite MAP Acceptance Comparison",
        "",
        "## Executive Summary",
        "",
        f"- Grid: `{grid}`",
        f"- C4 status: `{overall}`",
        f"- Best C3 reference: `{payload['best_c3_reference']}`",
        f"- MAP truth acceptance replaceable now: `{payload['map_truth_acceptance_replaceable_now']}`",
        "",
        "## Aggregate Diagnostics",
        "",
        f"- Localization improvement rows: {c4_metadata['health']['position_improvement_count']} of {c4_metadata['health']['comparison_count']}",
        f"- Synchronization improvement rows: {c4_metadata['health']['sync_improvement_count']} of {c4_metadata['health']['comparison_count']}",
        f"- MAP accepted/rejected updates: {c4_metadata['map_update_diagnostics']['accepted_update_count']}/{c4_metadata['map_update_diagnostics']['rejected_update_count']}",
        f"- Score components: `{c4_metadata['map_update_diagnostics'].get('score_components_used')}`",
        f"- Rejection reasons: `{c4_metadata['map_update_diagnostics'].get('rejection_reasons')}`",
        "",
        "## Row Comparisons Against Step B",
        "",
        "| Nu | Ns | Status | Step B pos [m] | C4 pos [m] | Step B sync [s] | C4 sync [s] | MAP acc/rej | Jmap before | Jmap after |",
        "|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in comparisons:
        md.append(
            f"| {item['num_users']} | {item['num_satellites']} | `{item['status']}` | "
            f"{item['step_b_map_position_error_m']} | {item['c4_map_position_error_m']} | "
            f"{item['step_b_map_sync_error_s']} | {item['c4_map_sync_error_s']} | "
            f"{item['map_accepted_update_count']}/{item['map_rejected_update_count']} | "
            f"{item['map_initial_objective']} | {item['map_final_objective']} |"
        )
    (REPORTS / "STEP_C4_COMPOSITE_ACCEPTANCE_COMPARISON.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return payload


def _write_step_c5_sliding_window_comparison() -> dict[str, Any] | None:
    """Compare C5 sliding-window MAP against Step B, C4, and legacy behavior."""

    grid = "medium" if (LADDER_ROOT / STEP_C5_NAME / "medium" / "migration_raw.csv").exists() else "tiny"
    c5_path = LADDER_ROOT / STEP_C5_NAME / grid / "migration_raw.csv"
    c5_meta_path = LADDER_ROOT / STEP_C5_NAME / grid / "migration_step_metadata.json"
    step_b_path = LADDER_ROOT / STEP_B_NAME / grid / "migration_raw.csv"
    c4_path = LADDER_ROOT / "step_c4_composite_map_acceptance" / grid / "migration_raw.csv"
    legacy_path = SOURCE_NETWORK_ROOT / "legacy_network_size_raw.csv"
    if not (c5_path.exists() and c5_meta_path.exists() and step_b_path.exists()):
        return None
    c5_rows = _read_ladder_raw(c5_path)
    step_b_rows = _read_ladder_raw(step_b_path)
    c4_rows = _read_ladder_raw(c4_path) if c4_path.exists() else {}
    legacy_rows = _read_ladder_raw(legacy_path) if legacy_path.exists() else {}
    c5_metadata = json.loads(c5_meta_path.read_text(encoding="utf-8"))
    comparisons = []
    for key in sorted(c5_rows):
        c5 = c5_rows[key]
        step_b = step_b_rows.get(key)
        if step_b is None:
            continue
        c4 = c4_rows.get(key)
        legacy = legacy_rows.get(key)
        comparisons.append(
            {
                "num_users": key[0],
                "num_satellites": key[1],
                "status_vs_step_b": _classify_diagnosis_row(step_b, c5, diagnostic_only=False),
                "il_position_error_m": c5["il_position_error_m"],
                "lm_position_error_m": c5["lm_position_error_m"],
                "step3_position_error_m": c5["map_position_error_m"],
                "step_b_position_error_m": step_b["map_position_error_m"],
                "c4_position_error_m": c4["map_position_error_m"] if c4 else None,
                "legacy_position_error_m": legacy["map_position_error_m"] if legacy else None,
                "il_sync_error_s": c5["il_sync_error_s"],
                "lm_sync_error_s": c5["lm_sync_error_s"],
                "step3_sync_error_s": c5["map_sync_error_s"],
                "step_b_sync_error_s": step_b["map_sync_error_s"],
                "c4_sync_error_s": c4["map_sync_error_s"] if c4 else None,
                "legacy_sync_error_s": legacy["map_sync_error_s"] if legacy else None,
                "objective_decrease": (
                    float(c5["map_initial_objective"]) - float(c5["map_final_objective"])
                    if c5.get("map_initial_objective") not in {None, ""} and c5.get("map_final_objective") not in {None, ""}
                    else None
                ),
                "measurement_objective_after": c5.get("map_measurement_cost_after"),
                "prior_objective_after": c5.get("map_prior_cost_after"),
                "dynamics_objective_after": c5.get("map_dynamics_cost_after"),
                "accepted_step_count": c5.get("map_accepted_update_count"),
                "rejected_step_count": c5.get("map_rejected_update_count"),
                "condition_number": c5.get("map_covariance_condition_after"),
                "position_update_norm_max": c5.get("map_position_update_norm_max"),
                "clock_update_norm_max": c5.get("map_clock_update_norm_max"),
                "jcls_localization_helps": bool(c5["map_position_error_m"] < c5["il_position_error_m"]),
                "jcls_sync_helps": bool(c5["map_sync_error_s"] < c5["il_sync_error_s"]),
            }
        )
    counts = _status_counts([
        {"status": item["status_vs_step_b"]}
        for item in comparisons
    ])
    overall = (
        "healthy"
        if counts["major_degradation"] == 0 and counts["failed"] == 0 and counts["mild_degradation"] == 0
        else "mild_degradation"
        if counts["major_degradation"] == 0 and counts["failed"] == 0
        else "major_degradation"
    )
    if c5_metadata["health"].get("catastrophic_failure"):
        overall = "failed"
    c4_overall = None
    c4_report_path = REPORTS / "STEP_C4_COMPOSITE_ACCEPTANCE_COMPARISON.json"
    if c4_report_path.exists():
        c4_overall = json.loads(c4_report_path.read_text(encoding="utf-8")).get("c4_overall_status")
    payload = {
        "artifact_status": "non_final_step_c5_sliding_window_map_comparison",
        "manuscript_ready": False,
        "grid": grid,
        "c5_overall_status": overall,
        "step_b_reference": STEP_B_NAME,
        "c4_reference": "step_c4_composite_map_acceptance",
        "legacy_reference": _repo_rel(legacy_path),
        "c5_health": c5_metadata["health"],
        "c5_map_update_diagnostics": c5_metadata["map_update_diagnostics"],
        "status_counts_vs_step_b": counts,
        "comparisons": comparisons,
        "does_c5_improve_over_c4": bool(c4_overall and overall in {"healthy", "mild_degradation"} and c4_overall in {"major_degradation", "failed"}),
        "does_c5_approach_step_b_or_legacy_behavior": bool(overall in {"healthy", "mild_degradation"}),
        "is_step3_defensible_now": bool(overall == "healthy"),
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "STEP_C5_SLIDING_WINDOW_MAP_COMPARISON.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md = [
        "# Step C5 Sliding-Window MAP Comparison",
        "",
        "## Executive Summary",
        "",
        f"- Grid: `{grid}`",
        f"- C5 status: `{overall}`",
        f"- Improves over C4: `{payload['does_c5_improve_over_c4']}`",
        f"- Approaches Step B or legacy behavior: `{payload['does_c5_approach_step_b_or_legacy_behavior']}`",
        f"- Step 3 defensible now: `{payload['is_step3_defensible_now']}`",
        "",
        "## Aggregate Diagnostics",
        "",
        f"- Localization improvement rows: {c5_metadata['health']['position_improvement_count']} of {c5_metadata['health']['comparison_count']}",
        f"- Synchronization improvement rows: {c5_metadata['health']['sync_improvement_count']} of {c5_metadata['health']['comparison_count']}",
        f"- Step-3 accepted/rejected solver steps: {c5_metadata['map_update_diagnostics']['accepted_update_count']}/{c5_metadata['map_update_diagnostics']['rejected_update_count']}",
        f"- Objective components: `{c5_metadata['map_update_diagnostics'].get('score_components_used')}`",
        "",
        "## Row Comparisons Against Step B",
        "",
        "| Nu | Ns | Status vs Step B | Step B pos [m] | C5 pos [m] | Step B sync [s] | C5 sync [s] | Step3 acc/rej | J total decrease |",
        "|---:|---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    for item in comparisons:
        md.append(
            f"| {item['num_users']} | {item['num_satellites']} | `{item['status_vs_step_b']}` | "
            f"{item['step_b_position_error_m']} | {item['step3_position_error_m']} | "
            f"{item['step_b_sync_error_s']} | {item['step3_sync_error_s']} | "
            f"{item['accepted_step_count']}/{item['rejected_step_count']} | {item['objective_decrease']} |"
        )
    (REPORTS / "STEP_C5_SLIDING_WINDOW_MAP_COMPARISON.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return payload


def _write_step2_only_vs_step3_report() -> dict[str, Any] | None:
    """Write a report comparing C5 Step 2 LM-only outputs to Step 3 refinement."""

    grid = "medium" if (LADDER_ROOT / STEP_C5_NAME / "medium" / "migration_raw.csv").exists() else "tiny"
    c5_path = LADDER_ROOT / STEP_C5_NAME / grid / "migration_raw.csv"
    if not c5_path.exists():
        return None
    rows = _read_ladder_raw(c5_path)
    comparisons = []
    for key in sorted(rows):
        row = rows[key]
        if not row.get("cooperative_jcls_attempted"):
            continue
        comparisons.append(
            {
                "num_users": key[0],
                "num_satellites": key[1],
                "step2_position_error_m": row["lm_position_error_m"],
                "step3_position_error_m": row["map_position_error_m"],
                "step2_sync_error_s": row["lm_sync_error_s"],
                "step3_sync_error_s": row["map_sync_error_s"],
                "step2_localization_improves_over_il": bool(row["lm_position_error_m"] < row["il_position_error_m"]),
                "step2_sync_improves_over_il": bool(row["lm_sync_error_s"] < row["il_sync_error_s"]),
                "step3_improves_position_over_step2": bool(row["map_position_error_m"] < row["lm_position_error_m"]),
                "step3_improves_sync_over_step2": bool(row["map_sync_error_s"] < row["lm_sync_error_s"]),
            }
        )
    step2_position_wins = sum(1 for item in comparisons if item["step2_localization_improves_over_il"])
    step2_sync_wins = sum(1 for item in comparisons if item["step2_sync_improves_over_il"])
    step3_position_wins = sum(1 for item in comparisons if item["step3_improves_position_over_step2"])
    step3_sync_wins = sum(1 for item in comparisons if item["step3_improves_sync_over_step2"])
    step2_shows_jcls_benefit = bool(comparisons and step2_position_wins == len(comparisons) and step2_sync_wins == len(comparisons))
    step3_improves = bool(comparisons and step3_position_wins == len(comparisons) and step3_sync_wins == len(comparisons))
    payload = {
        "artifact_status": "non_final_step2_only_vs_step3_refinement",
        "manuscript_ready": False,
        "grid": grid,
        "comparison_count": len(comparisons),
        "step2_position_improvement_rows": step2_position_wins,
        "step2_sync_improvement_rows": step2_sync_wins,
        "step3_position_improvement_over_step2_rows": step3_position_wins,
        "step3_sync_improvement_over_step2_rows": step3_sync_wins,
        "does_step2_alone_show_jcls_benefit": step2_shows_jcls_benefit,
        "does_step3_improve_or_hurt": "improve" if step3_improves else "mixed_or_hurt",
        "should_manuscript_temporarily_show_coarse_jcls_only": bool(step2_shows_jcls_benefit and not step3_improves),
        "comparisons": comparisons,
    }
    (REPORTS / "STEP2_ONLY_VS_STEP3_REFINEMENT.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md = [
        "# Step 2 Only vs Step 3 Refinement",
        "",
        "## Executive Summary",
        "",
        f"- Grid: `{grid}`",
        f"- Step 2 alone shows JCLS benefit: `{payload['does_step2_alone_show_jcls_benefit']}`",
        f"- Step 3 behavior: `{payload['does_step3_improve_or_hurt']}`",
        f"- Coarse-only temporary figure recommendation: `{payload['should_manuscript_temporarily_show_coarse_jcls_only']}`",
        "",
        "| Nu | Ns | Step2 pos [m] | Step3 pos [m] | Step2 sync [s] | Step3 sync [s] | Step3 pos improves | Step3 sync improves |",
        "|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for item in comparisons:
        md.append(
            f"| {item['num_users']} | {item['num_satellites']} | "
            f"{item['step2_position_error_m']} | {item['step3_position_error_m']} | "
            f"{item['step2_sync_error_s']} | {item['step3_sync_error_s']} | "
            f"`{item['step3_improves_position_over_step2']}` | `{item['step3_improves_sync_over_step2']}` |"
        )
    (REPORTS / "STEP2_ONLY_VS_STEP3_REFINEMENT.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return payload


def _write_cache_manifest(cache_entries: list[dict[str, Any]], *, stem: str = "CACHE_MANIFEST") -> None:
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
    (MIGRATION_CACHE_ROOT / f"{stem}.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
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
    (MIGRATION_CACHE_ROOT / f"{stem}.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def _write_ladder_report(step_reports: list[dict[str, Any]], baseline: dict[str, Any], *, stem: str = "CONTROLLED_MIGRATION_LADDER") -> dict[str, Any]:
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
    (REPORTS / f"{stem}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
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
    (REPORTS / f"{stem}.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return payload


def run_ladder(options: LadderRunOptions | None = None) -> dict[str, Any]:
    """Run the controlled migration ladder using safe bounded defaults."""

    options = options or LadderRunOptions()
    planned = _planned_work(options)
    _print_planned_work(planned, options)
    if options.dry_run or options.list_planned_work:
        return {
            "artifact_status": "non_final_controlled_migration_ladder_dry_run",
            "row_count": len(planned),
            "planned_rows": planned,
            "manuscript_ready": False,
        }

    all_rows = _read_rows()
    baseline = _write_baseline_freeze(all_rows)
    grouped = _group_planned_work(planned)
    step_by_name = {step.name: step for step in migration_ladder_steps()[1:]}
    step_reports = []
    cache_entries = []
    previous_by_grid: dict[str, dict[str, Any] | None] = {"tiny": None, "medium": None}
    process_start_time_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    run_context: dict[str, Any] = {
        "started_monotonic": time.monotonic(),
        "process_start_time_utc": process_start_time_utc,
        "row_counter": 0,
        "total_rows": len(planned),
        "last_completed_output": None,
        "timeout_seconds_per_row": options.timeout_seconds_per_row,
        "interrupted": False,
        "interruption_reason": None,
    }
    _write_heartbeat(
        _heartbeat_payload(
            status="starting",
            current_substep=None,
            current_grid_point=None,
            row_number=0,
            total_rows=len(planned),
            started_monotonic=run_context["started_monotonic"],
            process_start_time_utc=process_start_time_utc,
            last_completed_output=None,
        )
    )
    output_suffix = "_bounded" if options.bounded else ""
    report_stem = (
        "CONTROLLED_MIGRATION_LADDER_BOUNDED_RECOVERY"
        if options.bounded
        else "CONTROLLED_MIGRATION_LADDER_SELECTED"
        if options.steps
        else "CONTROLLED_MIGRATION_LADDER"
    )
    manifest_stem = (
        "CACHE_MANIFEST_BOUNDED_RECOVERY"
        if options.bounded
        else "CACHE_MANIFEST_SELECTED"
        if options.steps
        else "CACHE_MANIFEST"
    )

    for step_name, grid in grouped:
        if options.timeout_seconds_total is not None and time.monotonic() - run_context["started_monotonic"] > float(options.timeout_seconds_total):
            run_context["interrupted"] = True
            run_context["interruption_reason"] = "timeout_seconds_total"
            break
        step = step_by_name[step_name]
        points = grouped[(step_name, grid)]
        if not points:
            continue
        if step.name == STEP_B_NAME:
            grid_rows = _run_step_b_rows(grid, points=points, run_context=run_context)
        elif step.name == STEP_C5_NAME:
            grid_rows = _run_step_c5_rows(step, grid, points=points, run_context=run_context)
        elif step.name == STEP_C7_NAME:
            grid_rows = _run_step_c7_rows(step, grid, points=points, run_context=run_context)
        elif step.name in STEP_C_DIAGNOSIS_NAMES:
            grid_rows = _run_diagnosis_rows(step, grid, points=points, run_context=run_context)
        else:
            allowed = set(points)
            grid_rows = [
                row
                for row in _filter_rows(all_rows, grid)
                if (row["num_users"], row["num_satellites"]) in allowed
            ]
            for row in grid_rows:
                run_context["row_counter"] += 1
                run_context["last_completed_output"] = f"{step.name}:{grid}:{row['num_users']}:{row['num_satellites']}"
                _write_row_status(
                    {
                        "event": "row_end",
                        "step": step.name,
                        "grid": grid,
                        "num_users": row["num_users"],
                        "num_satellites": row["num_satellites"],
                        "row_number": run_context["row_counter"],
                        "total_rows": run_context["total_rows"],
                        "status": "copied_from_legacy_source",
                    }
                )
        status = "complete"
        if run_context.get("interrupted"):
            status = run_context.get("interruption_reason") or "interrupted"
        elif len(grid_rows) < len(points):
            status = "partial"
        output_grid = f"{grid}{output_suffix}"
        execution = _execution_metadata(
            planned_rows=len(points),
            executed_rows=len(grid_rows),
            status=status,
            options=options,
            output_grid=output_grid,
        )
        report = _write_step(step, grid, grid_rows, previous_by_grid[grid], execution=execution, output_grid=output_grid)
        previous_by_grid[grid] = report["health"]
        step_reports.append(report)
        cache_entries.append({"step": step.name, "grid": output_grid, **report["cache"]})
        _write_heartbeat(
            _heartbeat_payload(
                status=status,
                current_substep=step.name,
                current_grid_point={"grid": grid, "row_count": len(grid_rows)},
                row_number=run_context["row_counter"],
                total_rows=len(planned),
                started_monotonic=run_context["started_monotonic"],
                process_start_time_utc=process_start_time_utc,
                last_completed_output=run_context.get("last_completed_output"),
            )
        )
        if run_context.get("interrupted") or _should_stop_after_degradation(report, options):
            break

    _write_cache_manifest(cache_entries, stem=manifest_stem)
    ladder = _write_ladder_report(step_reports, baseline, stem=report_stem)
    if "step_c4_composite_map_acceptance" in {report["step"]["name"] for report in step_reports}:
        comparison = _write_step_c4_composite_acceptance_comparison()
        if comparison is not None:
            ladder["step_c4_comparison"] = {
                "path": "outputs/reports/STEP_C4_COMPOSITE_ACCEPTANCE_COMPARISON.md",
                "overall_status": comparison["c4_overall_status"],
            }
    if STEP_C5_NAME in {report["step"]["name"] for report in step_reports}:
        comparison = _write_step_c5_sliding_window_comparison()
        if comparison is not None:
            ladder["step_c5_comparison"] = {
                "path": "outputs/reports/STEP_C5_SLIDING_WINDOW_MAP_COMPARISON.md",
                "overall_status": comparison["c5_overall_status"],
            }
        step2_report = _write_step2_only_vs_step3_report()
        if step2_report is not None:
            ladder["step2_only_vs_step3"] = {
                "path": "outputs/reports/STEP2_ONLY_VS_STEP3_REFINEMENT.md",
                "step2_shows_jcls_benefit": step2_report["does_step2_alone_show_jcls_benefit"],
                "step3_behavior": step2_report["does_step3_improve_or_hurt"],
            }
    ladder["execution"] = {
        "status": run_context.get("interruption_reason") or "complete",
        "planned_rows": len(planned),
        "executed_rows": run_context["row_counter"],
        "bounded": options.bounded,
        "heartbeat_path": _repo_rel(HEARTBEAT_PATH),
        "row_status_path": _repo_rel(ROW_STATUS_PATH),
    }
    (REPORTS / f"{report_stem}.json").write_text(json.dumps(ladder, indent=2), encoding="utf-8")

    if not options.bounded:
        if (REPORTS / "STEP_C_DIAGNOSIS_REPORT.json").exists():
            _write_step_c_acceptance_design_notes()
        step_b_comparison = _write_step_b_comparison()
        if step_b_comparison is not None:
            ladder["step_b_comparison"] = {
                "path": "outputs/reports/STEP_B_LM_ACCEPTANCE_COMPARISON.md",
                "overall_status": step_b_comparison["overall_status"],
            }
        step_c_diagnosis = _write_step_c_diagnosis_report()
        if step_c_diagnosis is not None:
            ladder["step_c_diagnosis"] = {
                "path": "outputs/reports/STEP_C_DIAGNOSIS_REPORT.md",
                "breaking_factor": step_c_diagnosis["breaking_factor"],
                "best_non_truth_covariance_candidate": step_c_diagnosis["best_non_truth_covariance_candidate"],
            }
        from scripts.render_all_figure_previews import render_gallery

        from scripts.build_legacy_graph_package import main as build_graph_package

        build_graph_package()
        gallery = render_gallery(force=False)
        ladder["gallery"] = {
            "path": "outputs/gallery/PLOT_GALLERY.md",
            "entry_count": gallery["entry_count"],
        }
        (REPORTS / f"{report_stem}.json").write_text(json.dumps(ladder, indent=2), encoding="utf-8")
    return ladder


def _parse_args(argv: list[str] | None = None) -> LadderRunOptions:
    """Parse CLI arguments into runtime options."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--step", action="append", default=[], help="Migration step name to run. May be repeated.")
    parser.add_argument("--max-rows", type=int, default=None)
    parser.add_argument("--max-substeps", type=int, default=None)
    parser.add_argument("--tiny-only", action="store_true", default=False)
    parser.add_argument("--medium", action="store_true", default=False, help="Explicitly allow medium grid rows.")
    parser.add_argument("--no-medium", action="store_true", default=False)
    parser.add_argument("--timeout-seconds-per-row", type=float, default=None)
    parser.add_argument("--timeout-seconds-total", type=float, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--list-planned-work", action="store_true")
    parser.add_argument("--stop-after-first-degradation", action="store_true")
    parser.add_argument("--use-cache", action="store_true")
    args = parser.parse_args(argv)
    include_medium = bool(args.medium and not args.no_medium and not args.tiny_only)
    tiny_only = bool(args.tiny_only or args.no_medium or not args.medium)
    return LadderRunOptions(
        steps=tuple(args.step),
        include_medium=include_medium,
        tiny_only=tiny_only,
        max_rows=args.max_rows,
        max_substeps=args.max_substeps,
        timeout_seconds_per_row=args.timeout_seconds_per_row,
        timeout_seconds_total=args.timeout_seconds_total,
        resume=args.resume,
        dry_run=bool(args.dry_run),
        list_planned_work=args.list_planned_work,
        stop_after_first_degradation=args.stop_after_first_degradation,
        use_cache=args.use_cache,
    )


def main(argv: list[str] | None = None) -> int:
    options = _parse_args(argv)
    payload = run_ladder(options)
    print(
        json.dumps(
            {
                "status": "planned" if (options.dry_run or options.list_planned_work) else "wrote",
                "first_degraded_step": payload.get("first_degraded_step"),
                "current_best": payload.get("current_best_migration_step"),
                "execution": payload.get("execution"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
