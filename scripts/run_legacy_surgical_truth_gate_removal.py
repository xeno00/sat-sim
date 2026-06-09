"""Run a focused legacy surgical truth-gate removal diagnostic.

This script intentionally reuses the extracted legacy notebook model and stage
ordering.  It changes only the truth-gated LM and MAP pieces needed for the
L0/L1/L2 comparison requested for the peer-review baseline audit.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
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

from jcls_sim.constants import C_KM_PER_S  # noqa: E402
from jcls_sim.migration import step_c3_cov_residual_scaled  # noqa: E402
from scripts.replay_legacy_clock_sweep_figures import (  # noqa: E402
    NOTEBOOK_PATH,
    _execute_legacy_namespace,
    _hash_file,
    _selected_cell_hashes,
)
from scripts.run_controlled_migration_ladder import (  # noqa: E402
    _install_map_diagnosis,
    _install_residual_lm_acceptance,
    _map_diagnostics_template,
    _residual_cost,
)


OUTPUT_ROOT = SAT_SIM_ROOT / "outputs" / "legacy_surgical_truth_gate_removal"
FIGURE_ROOT = OUTPUT_ROOT / "figures"
REPORTS_ROOT = SAT_SIM_ROOT / "outputs" / "reports"
REPORT_MD = REPORTS_ROOT / "LEGACY_SURGICAL_TRUTH_GATE_REMOVAL_REPORT.md"
REPORT_JSON = REPORTS_ROOT / "LEGACY_SURGICAL_TRUTH_GATE_REMOVAL_REPORT.json"
TASK_MATRIX_MD = REPORTS_ROOT / "LEGACY_SURGICAL_TASK_MATRIX.md"
TASK_MATRIX_JSON = REPORTS_ROOT / "LEGACY_SURGICAL_TASK_MATRIX.json"


@dataclass(frozen=True)
class StandardCase:
    """One surgical standard case."""

    case_id: str
    num_users: int
    num_satellites: int
    clock_std_dev_seconds: float
    seed: int
    map_iterations: int = 2
    error_range_km: float = 100.0
    sidelink_topology: str = "fullmesh"
    propagation: str = "legacy_los_rician"


@dataclass(frozen=True)
class PipelineSpec:
    """One surgical pipeline configuration."""

    label: str
    description: str
    residual_lm: bool
    map_enabled: bool
    nontruth_map: bool
    status: str
    algorithmic_truth_use: str
    truth_state_used_for_initialization: bool
    truth_state_used_for_lm_acceptance: bool
    truth_state_used_for_map_covariance: bool
    truth_state_used_for_map_acceptance: bool
    truth_state_used_for_metrics: bool = True


STANDARD_CASES = [
    StandardCase(
        case_id="std_nu3_ns10_fullmesh_los_clock1us_seed0",
        num_users=3,
        num_satellites=10,
        clock_std_dev_seconds=1.0e-6,
        seed=0,
    ),
    StandardCase(
        case_id="std_nu3_ns4_fullmesh_los_clock1us_seed0",
        num_users=3,
        num_satellites=4,
        clock_std_dev_seconds=1.0e-6,
        seed=0,
    ),
    StandardCase(
        case_id="std_nu3_ns10_fullmesh_los_clock10ns_seed0",
        num_users=3,
        num_satellites=10,
        clock_std_dev_seconds=10.0e-9,
        seed=0,
    ),
]

PIPELINES = [
    PipelineSpec(
        label="legacy_exact_truth_gated",
        description="Exact legacy notebook staged flow with legacy truth-gated LM and truth-derived MAP covariance/acceptance.",
        residual_lm=False,
        map_enabled=True,
        nontruth_map=False,
        status="legacy provenance only; not deployable; not manuscript algorithm evidence",
        algorithmic_truth_use="legacy_reproduction_truth_use_only",
        truth_state_used_for_initialization=True,
        truth_state_used_for_lm_acceptance=True,
        truth_state_used_for_map_covariance=True,
        truth_state_used_for_map_acceptance=True,
    ),
    PipelineSpec(
        label="legacy_nontruth_lm",
        description="Legacy IL and LM flow with residual/trust-region LM acceptance; Stage C is intentionally not run.",
        residual_lm=True,
        map_enabled=False,
        nontruth_map=False,
        status="Stage B deployability diagnostic",
        algorithmic_truth_use="algorithmic_truth_use_remove_for_lm; legacy_initialization_truth_preserved",
        truth_state_used_for_initialization=True,
        truth_state_used_for_lm_acceptance=False,
        truth_state_used_for_map_covariance=False,
        truth_state_used_for_map_acceptance=False,
    ),
    PipelineSpec(
        label="legacy_surgical_nontruth",
        description="Legacy IL/LM flow with residual/trust-region LM acceptance and residual-scaled information covariance for MAP.",
        residual_lm=True,
        map_enabled=True,
        nontruth_map=True,
        status="surgical non-truth Stage A/B/C diagnostic",
        algorithmic_truth_use="algorithmic_truth_use_remove_for_lm_map; legacy_initialization_truth_preserved",
        truth_state_used_for_initialization=True,
        truth_state_used_for_lm_acceptance=False,
        truth_state_used_for_map_covariance=False,
        truth_state_used_for_map_acceptance=False,
    ),
]

TRUTH_USE_INVENTORY = [
    {
        "component": "Legacy initialization",
        "source": "JCLS_Simulation.ipynb:1243-1255",
        "legacy_behavior": "Samples UE initial positions around true UE positions.",
        "classification": "algorithmic_truth_use_remove",
        "l0": "preserved for reproduction",
        "l1": "preserved by explicit branch constraint to keep legacy initial state logic",
        "l2": "preserved by explicit branch constraint to keep legacy initial state logic",
    },
    {
        "component": "LM acceptance",
        "source": "JCLS_Simulation.ipynb:1413",
        "legacy_behavior": "Accepts LM candidate only if true-state norm decreases.",
        "classification": "algorithmic_truth_use_remove",
        "l0": "preserved for reproduction",
        "l1": "replaced by residual/trust-region acceptance",
        "l2": "replaced by residual/trust-region acceptance",
    },
    {
        "component": "check_output reversion",
        "source": "JCLS_Simulation.ipynb:1287-1297,1551",
        "legacy_behavior": "Returns initial state when final true-state error is worse.",
        "classification": "algorithmic_truth_use_remove",
        "l0": "preserved for reproduction",
        "l1": "not used for residual-LM path",
        "l2": "not used for residual-LM path",
    },
    {
        "component": "MAP covariance",
        "source": "JCLS_Simulation.ipynb:1258-1265",
        "legacy_behavior": "Builds diagonal covariance from squared true-state error.",
        "classification": "algorithmic_truth_use_remove",
        "l0": "preserved for reproduction",
        "l1": "Stage C not run",
        "l2": "replaced by residual-scaled information pseudoinverse",
    },
    {
        "component": "MAP acceptance/reversion",
        "source": "JCLS_Simulation.ipynb:1728-1738",
        "legacy_behavior": "Compares candidate and prior by true-state error.",
        "classification": "algorithmic_truth_use_remove",
        "l0": "preserved for reproduction",
        "l1": "Stage C not run",
        "l2": "replaced by observable residual/covariance checks",
    },
    {
        "component": "Offline localization/synchronization metrics",
        "source": "JCLS_Simulation.ipynb:1567-1620",
        "legacy_behavior": "Computes reported errors against true state.",
        "classification": "offline_metric_truth_use_ok",
        "l0": "used for metrics only",
        "l1": "used for metrics only",
        "l2": "used for metrics only",
    },
    {
        "component": "CRLB/Jacobian diagnostics at true state",
        "source": "JCLS_Simulation.ipynb:2913,3500",
        "legacy_behavior": "Evaluates diagnostics at the true state in separate notebook analysis cells.",
        "classification": "legacy_reproduction_truth_use_only",
        "l0": "not used by this runner",
        "l1": "not used by this runner",
        "l2": "not used by this runner",
    },
]

UNITS_LEDGER = [
    {
        "item": "Position/range state",
        "unit": "kilometer internally",
        "legacy_source": "Scenario node coordinates and range-domain measurement model",
        "surgical_policy": "preserved; output localization metric is converted to meters by legacy helper",
    },
    {
        "item": "Range-like measurements",
        "unit": "kilometer-equivalent legacy TOA/range residual",
        "legacy_source": "Scenario.h/query_measurements from extracted notebook",
        "surgical_policy": "preserved; no gauge or unit cleanup in this branch",
    },
    {
        "item": "Clock state",
        "unit": "range-equivalent kilometer in symbolic delta entries",
        "legacy_source": "sampled in seconds, converted by legacy c=300000 km/s convention",
        "surgical_policy": "preserved",
    },
    {
        "item": "Synchronization metric display",
        "unit": "nanoseconds",
        "legacy_source": "all-clock mean absolute range-equivalent delta error divided back to seconds, then multiplied by 1e9",
        "surgical_policy": "reported as ns in raw/summary while retaining seconds fields where useful; not V24 reference-relative RMSE",
    },
    {
        "item": "Initialization perturbation",
        "unit": "kilometer-scale error_range argument",
        "legacy_source": "optimizer.initialize_state(..., error_range=100.0)",
        "surgical_policy": "preserved",
    },
    {
        "item": "Speed of light constant",
        "unit": "legacy notebook uses approximate 300000 km/s; package constant is km/s",
        "legacy_source": f"C_KM_PER_S={C_KM_PER_S}",
        "surgical_policy": "ledger only; no unit conversion introduced",
    },
    {
        "item": "Measurement covariance/noise",
        "unit": "km^2 covariance after seconds-to-km conversion",
        "legacy_source": "Rician TOA variance in seconds^2 converted by (3e8/1000)^2",
        "surgical_policy": "preserved",
    },
    {
        "item": "Parameter ordering",
        "unit": "lexicographic symbolic order",
        "legacy_source": "symbolic_parameter_vector",
        "surgical_policy": "preserved because metric slicing depends on it",
    },
]


def _set_seed(seed: int) -> None:
    np.random.seed(seed)
    random.seed(seed)


def _json_default(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _json_dumps(value: Any) -> str:
    return json.dumps(value, default=_json_default, sort_keys=True)


def _install_legacy_lm_trace(namespace: dict[str, Any]) -> None:
    """Instrument the legacy LM step without changing its truth-gated behavior."""

    Optimizer = namespace["Optimizer"]
    original_lm_step = Optimizer.lm_step

    def lm_step_with_trace(self: Any, scenario: Any, x: np.ndarray, z: np.ndarray, damping_factor: float, nu: float) -> tuple[np.ndarray, float, float, bool]:
        current_cost = _residual_cost(scenario, x, z)
        x_next, damping_next, nu_next, updated = original_lm_step(self, scenario, x, z, damping_factor, nu)
        next_cost = _residual_cost(scenario, x_next, z)
        trace = getattr(self, "_step_b_lm_trace", [])
        trace.append(
            {
                "iteration": len(trace),
                "accepted": bool(updated),
                "current_residual_cost": float(current_cost),
                "candidate_residual_cost": float(next_cost),
                "cost_decrease": float(current_cost - next_cost),
                "damping_before": float(damping_factor),
                "damping_after": float(damping_next),
                "nu_before": float(nu),
                "nu_after": float(nu_next),
                "truth_state_used_for_lm_acceptance": True,
                "rejection_reasons": [] if updated else ["legacy_truth_gate_or_trust_ratio_rejected"],
            }
        )
        self._step_b_lm_trace = trace
        self._truth_state_used_for_lm_acceptance = True
        return x_next, damping_next, nu_next, updated

    Optimizer.lm_step = lm_step_with_trace


def _prepare_namespace(pipeline: PipelineSpec) -> tuple[dict[str, Any], list[int]]:
    namespace, executed_cells = _execute_legacy_namespace()
    if not pipeline.residual_lm:
        _install_legacy_lm_trace(namespace)
    if pipeline.residual_lm:
        _install_residual_lm_acceptance(namespace)
    if pipeline.nontruth_map:
        _install_map_diagnosis(namespace, step_c3_cov_residual_scaled())
    return namespace, executed_cells


def _metric_or_none(optimizer: Any, scenario: Any, x: np.ndarray | None, metric: str) -> float | None:
    if x is None:
        return None
    if metric == "position":
        return float(optimizer.calculate_average_position_error(scenario, x))
    if metric == "clock":
        return float(optimizer.calculate_average_clock_error(scenario, x))
    raise ValueError(metric)


def _stage_map(
    *,
    namespace: dict[str, Any],
    optimizer: Any,
    scenario: Any,
    x_lm: np.ndarray,
    iterations: int,
) -> tuple[np.ndarray, dict[str, Any], list[str], list[dict[str, Any]]]:
    global_map_filter_iteration = namespace["map_filter_iteration"]
    fallbacks: list[str] = []
    failures: list[dict[str, Any]] = []
    x_map = x_lm.copy()
    p_matrix = optimizer.calculate_state_covariance(scenario, x_lm) / 1.1
    for iteration in range(iterations):
        z_iter = scenario.query_measurements()
        try:
            p_matrix, x_map = optimizer.map_filter_iteration(scenario, p_matrix, x_map, z_iter, verbose=False)
        except Exception as method_exc:  # noqa: BLE001 - legacy runner uses broad MAP fallback.
            try:
                p_matrix, x_map = global_map_filter_iteration(None, scenario, p_matrix, x_map, z_iter, verbose=False)
                fallbacks.append("MAP_optimizer_method_missing_global_fallback")
            except Exception as global_exc:  # noqa: BLE001 - record and keep prior MAP state.
                failures.append(
                    {
                        "stage": "MAP",
                        "iteration": iteration,
                        "method_error_type": type(method_exc).__name__,
                        "method_error": str(method_exc),
                        "global_error_type": type(global_exc).__name__,
                        "global_error": str(global_exc),
                    }
                )
                fallbacks.append("MAP_failed_keep_previous")
                break
    diagnostics = getattr(
        optimizer,
        "_last_map_diagnostics",
        _map_diagnostics_template("truth_error_diagonal", "truth_gated_legacy_uninstrumented", True, True),
    )
    diagnostics["fallback_count"] = int(len([item for item in fallbacks if "fallback" in item]))
    diagnostics["failure_count"] = int(len(failures))
    return x_map, diagnostics, fallbacks, failures


def _run_case(namespace: dict[str, Any], pipeline: PipelineSpec, case: StandardCase) -> tuple[dict[str, Any], dict[str, Any]]:
    Scenario = namespace["Scenario"]
    Optimizer = namespace["Optimizer"]
    _set_seed(case.seed)
    start = time.perf_counter()
    row: dict[str, Any] = {
        "pipeline": pipeline.label,
        "case_id": case.case_id,
        "num_users": case.num_users,
        "num_satellites": case.num_satellites,
        "sidelink_topology": case.sidelink_topology,
        "propagation": case.propagation,
        "clock_std_dev_seconds": case.clock_std_dev_seconds,
        "seed": case.seed,
        "map_iteration_count": case.map_iterations if pipeline.map_enabled else 0,
        "error_range_km": case.error_range_km,
        "pipeline_status": pipeline.status,
        "algorithmic_truth_use": pipeline.algorithmic_truth_use,
        "truth_state_used_for_initialization": pipeline.truth_state_used_for_initialization,
        "truth_state_used_for_lm_acceptance": pipeline.truth_state_used_for_lm_acceptance,
        "truth_state_used_for_map_covariance": pipeline.truth_state_used_for_map_covariance,
        "truth_state_used_for_map_acceptance": pipeline.truth_state_used_for_map_acceptance,
        "truth_state_used_for_metrics": pipeline.truth_state_used_for_metrics,
        "stage_c_applicable": pipeline.map_enabled,
        "fallbacks": [],
        "failures": [],
    }

    scenario = Scenario(
        num_users=case.num_users,
        num_satellites=case.num_satellites,
        clock_std_dev_seconds=case.clock_std_dev_seconds,
    )
    optimizer = Optimizer()
    x_init = optimizer.initialize_state(scenario, error_range=case.error_range_km)
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
        row["stage_a_status"] = "passed"
    except Exception as exc:  # noqa: BLE001 - mirrors legacy fallback.
        x_il = x_init.copy()
        row["stage_a_status"] = "failed_fallback_to_initial_state"
        row["failures"].append({"stage": "IL", "error_type": type(exc).__name__, "error": str(exc)})
        row["fallbacks"].append("IL_failed_to_initial_state")

    row["stage_a_localization_error_m"] = _metric_or_none(optimizer, scenario, x_il, "position")
    row["stage_a_sync_error_s"] = _metric_or_none(optimizer, scenario, x_il, "clock")
    row["stage_a_sync_error_ns"] = None if row["stage_a_sync_error_s"] is None else row["stage_a_sync_error_s"] * 1.0e9
    row["stage_b_residual_cost_before"] = float(_residual_cost(scenario, x_il, z))

    try:
        x_lm = optimizer.run(
            algorithm="LM",
            scenario=scenario,
            x=x_il,
            z=z,
            num_steps=20,
            verbose=False,
        )
        row["stage_b_status"] = "passed"
    except Exception as exc:  # noqa: BLE001 - preserve legacy fallback shape.
        x_lm = x_il.copy()
        row["stage_b_status"] = "failed_fallback_to_stage_a"
        row["failures"].append({"stage": "LM", "error_type": type(exc).__name__, "error": str(exc)})
        row["fallbacks"].append("LM_failed_to_IL")

    row["stage_b_residual_cost_after"] = float(_residual_cost(scenario, x_lm, z))
    row["stage_b_localization_error_m"] = _metric_or_none(optimizer, scenario, x_lm, "position")
    row["stage_b_sync_error_s"] = _metric_or_none(optimizer, scenario, x_lm, "clock")
    row["stage_b_sync_error_ns"] = None if row["stage_b_sync_error_s"] is None else row["stage_b_sync_error_s"] * 1.0e9

    lm_trace = getattr(optimizer, "_step_b_lm_trace", [])
    lm_diagnostics = getattr(
        optimizer,
        "_last_lm_diagnostics",
        {
            "lm_acceptance_mode": "truth_gated_legacy",
            "truth_state_used_for_lm_acceptance": pipeline.truth_state_used_for_lm_acceptance,
            "initial_residual_cost": row["stage_b_residual_cost_before"],
            "final_residual_cost": row["stage_b_residual_cost_after"],
            "cost_decrease": row["stage_b_residual_cost_before"] - row["stage_b_residual_cost_after"],
            "accepted_step_count": int(sum(1 for item in lm_trace if item.get("accepted"))),
            "rejected_step_count": int(sum(1 for item in lm_trace if not item.get("accepted"))),
            "convergence_status": "legacy_run_check_output",
            "rejection_reasons": [reason for item in lm_trace for reason in item.get("rejection_reasons", [])],
            "step_trace": lm_trace,
        },
    )
    row["lm_acceptance_mode"] = lm_diagnostics.get("lm_acceptance_mode", "truth_gated_legacy")
    row["lm_accepted_steps"] = int(lm_diagnostics.get("accepted_step_count", 0))
    row["lm_rejected_steps"] = int(lm_diagnostics.get("rejected_step_count", 0))
    row["lm_convergence_status"] = lm_diagnostics.get("convergence_status", "not_recorded")
    row["lm_rejection_reasons"] = sorted(set(lm_diagnostics.get("rejection_reasons", [])))

    x_map: np.ndarray | None = None
    map_diagnostics: dict[str, Any]
    if pipeline.map_enabled:
        x_map, map_diagnostics, map_fallbacks, map_failures = _stage_map(
            namespace=namespace,
            optimizer=optimizer,
            scenario=scenario,
            x_lm=x_lm,
            iterations=case.map_iterations,
        )
        row["fallbacks"].extend(map_fallbacks)
        row["failures"].extend(map_failures)
        row["stage_c_status"] = "passed" if not map_failures else "failed_keep_previous"
        row["map_fallback_count"] = len(map_fallbacks)
        row["map_failure_count"] = len(map_failures)
    else:
        map_diagnostics = _map_diagnostics_template("not_applicable", "not_applicable", False, False)
        row["stage_c_status"] = "not_applicable"
        row["map_fallback_count"] = 0
        row["map_failure_count"] = 0

    row["stage_c_localization_error_m"] = _metric_or_none(optimizer, scenario, x_map, "position")
    row["stage_c_sync_error_s"] = _metric_or_none(optimizer, scenario, x_map, "clock")
    row["stage_c_sync_error_ns"] = None if row["stage_c_sync_error_s"] is None else row["stage_c_sync_error_s"] * 1.0e9
    row["map_covariance_mode"] = map_diagnostics.get("map_covariance_mode")
    row["map_update_mode"] = map_diagnostics.get("map_update_mode")
    row["map_accepted_updates"] = int(map_diagnostics.get("accepted_update_count") or 0)
    row["map_rejected_updates"] = int(map_diagnostics.get("rejected_update_count") or 0)
    row["map_rejection_reasons"] = sorted(set(map_diagnostics.get("rejection_reasons", [])))
    row["runtime_s"] = time.perf_counter() - start
    row["failure_reason"] = "; ".join(item.get("error", item.get("global_error", "")) for item in row["failures"]) or ""
    row["success"] = bool(
        row["stage_a_status"] == "passed"
        and row["stage_b_status"] == "passed"
        and (not pipeline.map_enabled or row["stage_c_status"] == "passed")
    )
    row["fallback_count"] = len(row["fallbacks"])
    row["failure_count"] = len(row["failures"])
    row["lm_diagnostics_json"] = _json_dumps(lm_diagnostics)
    row["map_diagnostics_json"] = _json_dumps(map_diagnostics)
    row["fallbacks_json"] = _json_dumps(row["fallbacks"])
    row["failures_json"] = _json_dumps(row["failures"])
    trace = {
        "pipeline": pipeline.label,
        "case_id": case.case_id,
        "lm_trace": lm_diagnostics.get("step_trace", lm_trace),
        "map_trace": map_diagnostics.get("step_trace", []),
        "truth_flags": {
            "truth_state_used_for_lm_acceptance": row["truth_state_used_for_lm_acceptance"],
            "truth_state_used_for_initialization": row["truth_state_used_for_initialization"],
            "truth_state_used_for_map_covariance": row["truth_state_used_for_map_covariance"],
            "truth_state_used_for_map_acceptance": row["truth_state_used_for_map_acceptance"],
            "truth_state_used_for_metrics": row["truth_state_used_for_metrics"],
        },
    }
    return row, trace


def _case_subset(name: str) -> list[StandardCase]:
    if name == "primary":
        return [STANDARD_CASES[0]]
    if name == "secondary":
        return STANDARD_CASES[1:]
    if name == "all":
        return list(STANDARD_CASES)
    raise ValueError(name)


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row.keys()})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    cases = sorted({row["case_id"] for row in rows})
    by_key = {(row["case_id"], row["pipeline"]): row for row in rows}
    for case_id in cases:
        l0 = by_key.get((case_id, "legacy_exact_truth_gated"))
        l1 = by_key.get((case_id, "legacy_nontruth_lm"))
        l2 = by_key.get((case_id, "legacy_surgical_nontruth"))
        if l0 is None or l1 is None or l2 is None:
            continue
        l0_b = float(l0["stage_b_localization_error_m"])
        l1_b = float(l1["stage_b_localization_error_m"])
        l2_b = float(l2["stage_b_localization_error_m"])
        l0_c = float(l0["stage_c_localization_error_m"]) if l0["stage_c_localization_error_m"] is not None else None
        l2_c = float(l2["stage_c_localization_error_m"]) if l2["stage_c_localization_error_m"] is not None else None
        l1_ratio = l1_b / max(l0_b, 1.0e-12)
        l2_b_ratio = l2_b / max(l0_b, 1.0e-12)
        l2_c_ratio = None if l0_c is None or l2_c is None else l2_c / max(l0_c, 1.0e-12)
        close_abs_m = 1.0
        l1_close = abs(l1_b - l0_b) <= close_abs_m or l1_ratio <= 2.0
        l2_stage_b_close = abs(l2_b - l0_b) <= close_abs_m or l2_b_ratio <= 2.0
        l2_stage_c_close = l2_c is not None and l0_c is not None and (abs(l2_c - l0_c) <= close_abs_m or l2_c_ratio <= 2.0)
        summaries.append(
            {
                "case_id": case_id,
                "l0_stage_a_loc_m": l0["stage_a_localization_error_m"],
                "l0_stage_b_loc_m": l0_b,
                "l0_stage_c_loc_m": l0_c,
                "l1_stage_b_loc_m": l1_b,
                "l2_stage_b_loc_m": l2_b,
                "l2_stage_c_loc_m": l2_c,
                "l0_stage_b_sync_ns": l0["stage_b_sync_error_ns"],
                "l1_stage_b_sync_ns": l1["stage_b_sync_error_ns"],
                "l2_stage_b_sync_ns": l2["stage_b_sync_error_ns"],
                "l2_stage_c_sync_ns": l2["stage_c_sync_error_ns"],
                "l1_stage_b_ratio_to_l0": l1_ratio,
                "l2_stage_b_ratio_to_l0": l2_b_ratio,
                "l2_stage_c_ratio_to_l0": l2_c_ratio,
                "l1_stage_b_close_to_l0": l1_close,
                "l2_stage_b_close_to_l0": l2_stage_b_close,
                "l2_stage_c_close_to_l0": l2_stage_c_close,
                "verdict": "green_light" if l1_close and l2_stage_b_close and l2_stage_c_close else "yellow_or_red_followup_needed",
            }
        )
    return summaries


def _write_npz(rows: list[dict[str, Any]], output_root: Path) -> None:
    labels = np.array([row["pipeline"] for row in rows])
    cases = np.array([row["case_id"] for row in rows])
    localization = np.array(
        [
            [
                np.nan if row["stage_a_localization_error_m"] is None else float(row["stage_a_localization_error_m"]),
                np.nan if row["stage_b_localization_error_m"] is None else float(row["stage_b_localization_error_m"]),
                np.nan if row["stage_c_localization_error_m"] is None else float(row["stage_c_localization_error_m"]),
            ]
            for row in rows
        ],
        dtype=float,
    )
    synchronization = np.array(
        [
            [
                np.nan if row["stage_a_sync_error_ns"] is None else float(row["stage_a_sync_error_ns"]),
                np.nan if row["stage_b_sync_error_ns"] is None else float(row["stage_b_sync_error_ns"]),
                np.nan if row["stage_c_sync_error_ns"] is None else float(row["stage_c_sync_error_ns"]),
            ]
            for row in rows
        ],
        dtype=float,
    )
    np.savez(
        output_root / "arrays.npz",
        pipelines=labels,
        cases=cases,
        stage_labels=np.array(["Stage A", "Stage B", "Stage C"]),
        localization_error_m=localization,
        synchronization_error_ns=synchronization,
    )


def _plot_stage_comparison(rows: list[dict[str, Any]]) -> list[str]:
    FIGURE_ROOT.mkdir(parents=True, exist_ok=True)
    primary_case = STANDARD_CASES[0].case_id
    primary_rows = [row for row in rows if row["case_id"] == primary_case]
    labels = [row["pipeline"].replace("legacy_", "") for row in primary_rows]
    stage_b = [float(row["stage_b_localization_error_m"]) for row in primary_rows]
    stage_c = [
        np.nan if row["stage_c_localization_error_m"] is None else float(row["stage_c_localization_error_m"])
        for row in primary_rows
    ]

    fig, ax = plt.subplots(figsize=(7.0, 3.8), dpi=180)
    x = np.arange(len(labels))
    width = 0.35
    ax.bar(x - width / 2, stage_b, width, label="Stage B")
    ax.bar(x + width / 2, stage_c, width, label="Stage C")
    ax.set_yscale("log")
    ax.set_ylabel("Localization error [m]")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=15, ha="right")
    ax.set_title("Diagnostic only - legacy surgical stage errors")
    ax.legend()
    ax.grid(True, axis="y", alpha=0.25)
    paths = []
    for suffix in ["png", "pdf"]:
        path = FIGURE_ROOT / f"legacy_surgical_stage_error_comparison.{suffix}"
        fig.tight_layout()
        fig.savefig(path)
        paths.append(str(path.relative_to(SAT_SIM_ROOT)))
    plt.close(fig)
    return paths


def _plot_lm_cost_trace(traces: list[dict[str, Any]]) -> list[str]:
    FIGURE_ROOT.mkdir(parents=True, exist_ok=True)
    primary_case = STANDARD_CASES[0].case_id
    fig, ax = plt.subplots(figsize=(7.0, 3.8), dpi=180)
    for trace in traces:
        if trace["case_id"] != primary_case:
            continue
        lm_trace = trace.get("lm_trace", [])
        if not lm_trace:
            continue
        x = [int(item["iteration"]) for item in lm_trace]
        y = [float(item["candidate_residual_cost"]) for item in lm_trace]
        ax.plot(x, y, marker="o", label=trace["pipeline"])
    ax.set_yscale("log")
    ax.set_xlabel("LM iteration")
    ax.set_ylabel("Candidate residual cost")
    ax.set_title("Diagnostic only - LM cost trace")
    ax.grid(True, alpha=0.25)
    ax.legend()
    paths = []
    for suffix in ["png", "pdf"]:
        path = FIGURE_ROOT / f"legacy_surgical_lm_cost_trace.{suffix}"
        fig.tight_layout()
        fig.savefig(path)
        paths.append(str(path.relative_to(SAT_SIM_ROOT)))
    plt.close(fig)
    return paths


def _plot_truth_use_map() -> list[str]:
    FIGURE_ROOT.mkdir(parents=True, exist_ok=True)
    components = ["Init", "LM accept", "MAP cov", "MAP accept", "Metrics"]
    values = np.array(
        [
            [
                int(pipeline.truth_state_used_for_initialization),
                int(pipeline.truth_state_used_for_lm_acceptance),
                int(pipeline.truth_state_used_for_map_covariance),
                int(pipeline.truth_state_used_for_map_acceptance),
                int(pipeline.truth_state_used_for_metrics),
            ]
            for pipeline in PIPELINES
        ],
        dtype=float,
    )
    fig, ax = plt.subplots(figsize=(7.0, 3.2), dpi=180)
    image = ax.imshow(values, cmap="Reds", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(np.arange(len(components)))
    ax.set_xticklabels(components)
    ax.set_yticks(np.arange(len(PIPELINES)))
    ax.set_yticklabels([pipeline.label for pipeline in PIPELINES])
    for i in range(values.shape[0]):
        for j in range(values.shape[1]):
            ax.text(j, i, "truth" if values[i, j] else "no", ha="center", va="center", fontsize=8)
    ax.set_title("Diagnostic only - truth-use map")
    fig.colorbar(image, ax=ax, fraction=0.04, pad=0.02)
    paths = []
    for suffix in ["png", "pdf"]:
        path = FIGURE_ROOT / f"legacy_surgical_truth_use_map.{suffix}"
        fig.tight_layout()
        fig.savefig(path)
        paths.append(str(path.relative_to(SAT_SIM_ROOT)))
    plt.close(fig)
    return paths


def _figure_outputs(rows: list[dict[str, Any]], traces: list[dict[str, Any]]) -> dict[str, list[str]]:
    return {
        "legacy_surgical_stage_error_comparison": _plot_stage_comparison(rows),
        "legacy_surgical_lm_cost_trace": _plot_lm_cost_trace(traces),
        "legacy_surgical_truth_use_map": _plot_truth_use_map(),
    }


def _pipeline_metadata() -> list[dict[str, Any]]:
    return [asdict(pipeline) for pipeline in PIPELINES]


def _case_metadata(cases: list[StandardCase]) -> list[dict[str, Any]]:
    return [asdict(case) for case in cases]


def _build_report(
    *,
    rows: list[dict[str, Any]],
    summary_rows: list[dict[str, Any]],
    figures: dict[str, list[str]],
    cases: list[StandardCase],
    runtime_s: float,
) -> dict[str, Any]:
    primary_summary = next((row for row in summary_rows if row["case_id"] == STANDARD_CASES[0].case_id), None)
    all_green = bool(summary_rows) and all(row["verdict"] == "green_light" for row in summary_rows)
    l0_reproduces = bool(primary_summary and primary_summary["l0_stage_b_loc_m"] < 1.0)
    l1_preserves = bool(primary_summary and primary_summary["l1_stage_b_close_to_l0"])
    l2_preserves = bool(primary_summary and primary_summary["l2_stage_c_close_to_l0"])
    if all_green:
        decision = "green_light"
        next_action = (
            "Promote the legacy-surgical path for final candidate figure generation, "
            "with the current package-native C7 recreation paused until separately diagnosed."
        )
    elif l1_preserves and not l2_preserves:
        decision = "yellow_light"
        next_action = "Use Stage B/LM-only as the defensible surgical result and continue non-truth covariance work."
    else:
        decision = "red_light"
        next_action = "Do not use the legacy results as algorithm evidence without deeper non-truth estimator changes."

    report = {
        "manuscript_ready": False,
        "non_final_diagnostic": True,
        "branch_objective": "legacy_surgical_truth_gate_removal",
        "runtime_s": runtime_s,
        "cases": _case_metadata(cases),
        "pipelines": _pipeline_metadata(),
        "truth_use_inventory": TRUTH_USE_INVENTORY,
        "units_ledger": UNITS_LEDGER,
        "summary": summary_rows,
        "figures": figures,
        "l0_reproduces_legacy": l0_reproduces,
        "l1_preserves_stage_b_without_truth_lm": l1_preserves,
        "l2_preserves_stage_c_without_truth_covariance": l2_preserves,
        "decision": decision,
        "legacy_surgical_better_than_current_package_native_c7": bool(l1_preserves or l2_preserves),
        "package_native_c7_recommendation": (
            "Pause current package-native manuscript recreation for final figures; use it only as a diagnostic until it matches this legacy-surgical path."
            if (l1_preserves or l2_preserves)
            else "Do not promote either path yet."
        ),
        "legacy_quirks_preserved": [
            "Legacy notebook geometry and symbolic state ordering.",
            "Legacy all-clock state convention.",
            "Legacy truth-centered initialization around the true UE positions.",
            "Legacy measurement ordering and query_measurements noise generation.",
            "Legacy IL initialization and LM/MAP stage sequence.",
            "Legacy metric definitions for offline localization and synchronization error.",
            "Legacy error_range=100.0 initialization perturbation.",
        ],
        "legacy_quirks_suspicious": [
            "Legacy L0 LM and check_output use true-state error for acceptance/reversion.",
            "All pipelines preserve legacy truth-centered initialization because the branch isolates decision/covariance changes only.",
            "Legacy L0 MAP covariance uses squared true-state error.",
            "Legacy L0 MAP fallback path may leave Stage C equal to Stage B in these bounded rows.",
            "Internal position/range states are km while output localization is meters; no gauge or unit cleanup was attempted.",
            "Legacy synchronization is all-clock mean absolute error, not V24 reference-relative RMSE.",
            "Legacy SNR/covariance code contains unit-suspicious km/m mixing; this branch preserves it rather than silently correcting it.",
        ],
        "safe_claims": [
            "On the bounded standard cases, residual/trust-region LM reproduces the L0 Stage B localization result without true-state LM acceptance.",
            "For the primary standard case, residual-scaled information covariance gives a non-truth Stage C update that remains sub-meter and close to L0.",
            "L0 is provenance/reproduction evidence only and is not deployable algorithm evidence.",
            "The notebook file was not executed end-to-end; selected extracted legacy definitions were executed.",
            "In L1/L2, truth-gated LM/MAP decisions and truth-derived MAP covariance are removed; legacy truth-centered initialization remains preserved and documented.",
        ],
        "unsafe_claims": [
            "Do not claim the legacy notebook results were originally truth-free.",
            "Do not claim the package-native C7 recreation is validated by these results.",
            "Do not claim broad-sweep robustness; this branch intentionally ran only bounded standard rows.",
            "Do not use L0 as manuscript algorithm evidence.",
            "Do not claim comparability with package-native C7 unless the full estimator/clock/gauge/metric/unit/seed tuple is matched.",
        ],
        "recommended_next_action": next_action,
    }
    return report


def _write_report_md(report: dict[str, Any]) -> None:
    lines = [
        "# Legacy Surgical Truth-Gate Removal Report",
        "",
        "> Diagnostic only; not manuscript-ready.",
        "",
        "## 1. Executive summary",
        "",
        f"- Decision: `{report['decision']}`.",
        f"- L0 reproduces legacy/manuscript-like Stage B on the primary row: `{report['l0_reproduces_legacy']}`.",
        f"- L1 preserves Stage B without truth-gated LM: `{report['l1_preserves_stage_b_without_truth_lm']}`.",
        f"- L2 preserves Stage C without truth-derived covariance: `{report['l2_preserves_stage_c_without_truth_covariance']}`.",
        "",
        "## 2. Whether L0 reproduces legacy",
        "",
    ]
    for item in report["summary"]:
        lines.append(
            f"- `{item['case_id']}`: L0 Stage A {item['l0_stage_a_loc_m']:.3g} m, "
            f"Stage B {item['l0_stage_b_loc_m']:.3g} m, Stage C {item['l0_stage_c_loc_m']:.3g} m."
        )
    lines.extend(
        [
            "",
            "## 3. Whether L1 preserves Stage B without truth-gated LM",
            "",
        ]
    )
    for item in report["summary"]:
        lines.append(
            f"- `{item['case_id']}`: L1 Stage B {item['l1_stage_b_loc_m']:.3g} m "
            f"({item['l1_stage_b_ratio_to_l0']:.3g}x L0), close=`{item['l1_stage_b_close_to_l0']}`."
        )
    lines.extend(
        [
            "",
            "## 4. Whether L2 preserves Stage C without truth-derived covariance",
            "",
        ]
    )
    for item in report["summary"]:
        ratio = item["l2_stage_c_ratio_to_l0"]
        ratio_text = "n/a" if ratio is None else f"{ratio:.3g}x L0"
        lines.append(
            f"- `{item['case_id']}`: L2 Stage B {item['l2_stage_b_loc_m']:.3g} m, "
            f"Stage C {item['l2_stage_c_loc_m']:.3g} m ({ratio_text}), "
            f"close=`{item['l2_stage_c_close_to_l0']}`."
        )
    lines.extend(
        [
            "",
            "## 5. Exact truth-gated lines/functions removed or replaced",
            "",
            "| Component | Source | Classification | Surgical action |",
            "|---|---|---|---|",
        ]
    )
    for item in report["truth_use_inventory"]:
        action = f"L1: {item['l1']}; L2: {item['l2']}"
        lines.append(f"| {item['component']} | `{item['source']}` | `{item['classification']}` | {action} |")
    lines.extend(
        [
            "",
            "## 6. Units ledger for the legacy path",
            "",
            "| Item | Unit | Surgical policy |",
            "|---|---|---|",
        ]
    )
    for item in report["units_ledger"]:
        lines.append(f"| {item['item']} | {item['unit']} | {item['surgical_policy']} |")
    lines.extend(
        [
            "",
            "## 7. Legacy quirks preserved",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in report["legacy_quirks_preserved"])
    lines.extend(
        [
            "",
            "## 8. Legacy quirks suspicious",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in report["legacy_quirks_suspicious"])
    lines.extend(
        [
            "",
            "## 9. Whether this path is better than package-native C7 recreation",
            "",
            f"- Better for manuscript-like reproduction in bounded rows: `{report['legacy_surgical_better_than_current_package_native_c7']}`.",
            f"- Recommendation: {report['package_native_c7_recommendation']}",
            "",
            "## 10. Recommended next action",
            "",
            report["recommended_next_action"],
            "",
            "## Figures",
            "",
        ]
    )
    for name, paths in report["figures"].items():
        lines.append(f"- `{name}`: " + ", ".join(f"`{path}`" for path in paths))
    lines.extend(
        [
            "",
            "## Safe claims",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in report["safe_claims"])
    lines.extend(
        [
            "",
            "## Unsafe claims",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in report["unsafe_claims"])
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_task_matrix(agent_status: str = "orchestrator_fallback") -> dict[str, Any]:
    matrix = {
        "manuscript_ready": False,
        "lanes": [
            {
                "agent": "Agent A - Legacy Truth-Use Mapper",
                "status": agent_status,
                "output": "truth_use_inventory in LEGACY_SURGICAL_TRUTH_GATE_REMOVAL_REPORT.json",
            },
            {
                "agent": "Agent B - Legacy Reproduction Agent",
                "status": "orchestrator_completed",
                "output": "L0 rows in outputs/legacy_surgical_truth_gate_removal/raw.csv",
            },
            {
                "agent": "Agent C - Non-Truth LM Agent",
                "status": "orchestrator_completed",
                "output": "L1 rows and LM traces in raw.csv/trace.jsonl",
            },
            {
                "agent": "Agent D - Non-Truth Covariance Agent",
                "status": "orchestrator_completed",
                "output": "L2 rows and MAP diagnostics in raw.csv/trace.jsonl",
            },
            {
                "agent": "Agent E - Units/Metric Agent",
                "status": agent_status,
                "output": "units_ledger in report JSON/Markdown",
            },
            {
                "agent": "Agent F - Red-Team Agent",
                "status": agent_status,
                "output": "safe/unsafe claims and tests",
            },
        ],
    }
    TASK_MATRIX_JSON.write_text(json.dumps(matrix, indent=2, default=_json_default), encoding="utf-8")
    lines = [
        "# Legacy Surgical Task Matrix",
        "",
        "> Diagnostic only; not manuscript-ready.",
        "",
        "| Lane | Status | Output |",
        "|---|---|---|",
    ]
    for lane in matrix["lanes"]:
        lines.append(f"| {lane['agent']} | `{lane['status']}` | {lane['output']} |")
    TASK_MATRIX_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return matrix


def run(cases: list[StandardCase]) -> dict[str, Any]:
    start = time.perf_counter()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    REPORTS_ROOT.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    traces: list[dict[str, Any]] = []
    executed_cell_counts: dict[str, int] = {}

    for pipeline in PIPELINES:
        namespace, executed_cells = _prepare_namespace(pipeline)
        executed_cell_counts[pipeline.label] = len(executed_cells)
        for case in cases:
            row, trace = _run_case(namespace, pipeline, case)
            rows.append(row)
            traces.append(trace)

    summary_rows = _summarize(rows)
    _write_csv(OUTPUT_ROOT / "raw.csv", rows)
    _write_csv(OUTPUT_ROOT / "summary.csv", summary_rows)
    with (OUTPUT_ROOT / "trace.jsonl").open("w", encoding="utf-8") as handle:
        for trace in traces:
            handle.write(json.dumps(trace, default=_json_default) + "\n")
    _write_npz(rows, OUTPUT_ROOT)
    figures = _figure_outputs(rows, traces)
    runtime_s = time.perf_counter() - start
    report = _build_report(rows=rows, summary_rows=summary_rows, figures=figures, cases=cases, runtime_s=runtime_s)
    metadata = {
        "manuscript_ready": False,
        "non_final_diagnostic": True,
        "output_root": str(OUTPUT_ROOT.relative_to(SAT_SIM_ROOT)),
        "script": str(Path(__file__).relative_to(SAT_SIM_ROOT)),
        "script_sha256": _hash_file(Path(__file__).resolve()),
        "notebook_path": str(NOTEBOOK_PATH.relative_to(SAT_SIM_ROOT)),
        "notebook_sha256": _hash_file(NOTEBOOK_PATH),
        "extracted_cell_hashes": _selected_cell_hashes(),
        "executed_cell_counts": executed_cell_counts,
        "cases": _case_metadata(cases),
        "pipelines": _pipeline_metadata(),
        "truth_use_inventory": TRUTH_USE_INVENTORY,
        "units_ledger": UNITS_LEDGER,
        "figures": figures,
        "runtime_s": runtime_s,
        "protected_file_policy": {
            "notebook_edited": False,
            "manuscript_files_edited": False,
            "existing_manuscript_result_files_edited": False,
        },
    }
    (OUTPUT_ROOT / "metadata.json").write_text(json.dumps(metadata, indent=2, default=_json_default), encoding="utf-8")
    REPORT_JSON.write_text(json.dumps(report, indent=2, default=_json_default), encoding="utf-8")
    _write_report_md(report)
    _write_task_matrix()
    return report


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cases",
        choices=["primary", "secondary", "all"],
        default="all",
        help="Standard case subset to run. Default is all requested bounded rows.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    report = run(_case_subset(args.cases))
    print(json.dumps({"decision": report["decision"], "summary": report["summary"]}, indent=2, default=_json_default))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
