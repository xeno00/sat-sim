"""Run a focused coarse-prior-region initialization diagnostic.

This continuation starts from the legacy surgical truth-gate removal branch and
replaces the remaining truth-centered initialization caveat with an explicit
coarse prior-region simulation model.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
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
from scripts.run_legacy_surgical_truth_gate_removal import (  # noqa: E402
    _install_legacy_lm_trace,
    _json_default,
    _metric_or_none,
    _stage_map,
)


OUTPUT_ROOT = SAT_SIM_ROOT / "outputs" / "legacy_surgical_prior_region_initialization"
FIGURE_ROOT = OUTPUT_ROOT / "figures"
REPORTS_ROOT = SAT_SIM_ROOT / "outputs" / "reports"
REPORT_MD = REPORTS_ROOT / "LEGACY_SURGICAL_PRIOR_REGION_INITIALIZATION_REPORT.md"
REPORT_JSON = REPORTS_ROOT / "LEGACY_SURGICAL_PRIOR_REGION_INITIALIZATION_REPORT.json"

PRIOR_RADII_M = [10.0, 100.0, 1_000.0, 10_000.0, 100_000.0]
DEFAULT_SEEDS = [0]


@dataclass(frozen=True)
class StandardCase:
    """One bounded standard case."""

    case_id: str
    num_users: int
    num_satellites: int
    clock_std_dev_seconds: float
    seed: int
    map_iterations: int = 2
    legacy_error_range_km: float = 100.0
    sidelink_topology: str = "fullmesh"
    propagation: str = "legacy_los_rician"


@dataclass(frozen=True)
class PriorConfig:
    """Simulation prior-region model."""

    mode: str
    label: str
    scale_m: float

    @property
    def scale_km(self) -> float:
        return self.scale_m / 1000.0


@dataclass(frozen=True)
class PipelineSpec:
    """One pipeline in the prior-region diagnostic."""

    label: str
    description: str
    residual_lm: bool
    map_enabled: bool
    nontruth_map: bool
    uses_prior_region: bool
    truth_state_used_for_stage_a_acceptance: bool
    truth_state_used_for_lm_acceptance: bool
    truth_state_used_for_map_covariance: bool
    truth_state_used_for_map_acceptance: bool
    truth_state_used_for_prior_simulation: bool
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
        case_id="std_nu3_ns10_fullmesh_los_clock10ns_seed0",
        num_users=3,
        num_satellites=10,
        clock_std_dev_seconds=10.0e-9,
        seed=0,
    ),
    StandardCase(
        case_id="std_nu3_ns4_fullmesh_los_clock1us_seed0",
        num_users=3,
        num_satellites=4,
        clock_std_dev_seconds=1.0e-6,
        seed=0,
    ),
]

PIPELINES = [
    PipelineSpec(
        label="legacy_exact_truth_gated",
        description="Exact legacy provenance baseline with legacy cube initialization, truth-gated LM, and truth-derived MAP covariance.",
        residual_lm=False,
        map_enabled=True,
        nontruth_map=False,
        uses_prior_region=False,
        truth_state_used_for_stage_a_acceptance=True,
        truth_state_used_for_lm_acceptance=True,
        truth_state_used_for_map_covariance=True,
        truth_state_used_for_map_acceptance=True,
        truth_state_used_for_prior_simulation=False,
    ),
    PipelineSpec(
        label="legacy_nontruth_lm",
        description="Legacy staged flow using coarse prior-region initialization and residual/trust-region LM acceptance.",
        residual_lm=True,
        map_enabled=False,
        nontruth_map=False,
        uses_prior_region=True,
        truth_state_used_for_stage_a_acceptance=False,
        truth_state_used_for_lm_acceptance=False,
        truth_state_used_for_map_covariance=False,
        truth_state_used_for_map_acceptance=False,
        truth_state_used_for_prior_simulation=True,
    ),
    PipelineSpec(
        label="legacy_surgical_nontruth",
        description="Coarse prior-region initialization with non-truth LM and residual-scaled information MAP covariance.",
        residual_lm=True,
        map_enabled=True,
        nontruth_map=True,
        uses_prior_region=True,
        truth_state_used_for_stage_a_acceptance=False,
        truth_state_used_for_lm_acceptance=False,
        truth_state_used_for_map_covariance=False,
        truth_state_used_for_map_acceptance=False,
        truth_state_used_for_prior_simulation=True,
    ),
]

UNITS_LEDGER = [
    {
        "item": "Prior radius/sigma",
        "unit": "meters in outputs, converted to km before insertion into legacy state",
        "policy": "declared prior-region size; not a truth gate",
    },
    {
        "item": "Legacy state",
        "unit": "positions/ranges and clock deltas are km internally",
        "policy": "preserved from legacy branch",
    },
    {
        "item": "Localization metric",
        "unit": "meters",
        "policy": "legacy mean UE position norm error converted from km to m",
    },
    {
        "item": "Synchronization metric",
        "unit": "nanoseconds",
        "policy": "legacy all-clock mean absolute delta error converted back to time; not V24 reference-relative RMSE",
    },
]

SCIENTIFIC_JUSTIFICATION = [
    "last known UE position",
    "satellite beam footprint",
    "network registration area",
    "inertial/dead-reckoning propagation",
    "mission operating area",
    "coarse GNSS before outage",
    "map/geofence constraints",
    "user/service-region knowledge",
]

SUGGESTED_MANUSCRIPT_WORDING = (
    "The nonlinear JCLS estimator requires coarse initialization. In the numerical study, "
    "each UE is initialized from a coarse prior region with radius R_0, representing context "
    "information such as last-known position, satellite beam footprint, network registration "
    "area, or mission-region knowledge. This prior is used only to initialize the iterative "
    "estimator; true state information is not used in the LM acceptance rule, covariance "
    "construction, or dynamic refinement safeguard."
)


def _set_seed(seed: int) -> None:
    np.random.seed(seed)
    random.seed(seed)


def _json_dumps(value: Any) -> str:
    return json.dumps(value, default=_json_default, sort_keys=True)


def _long_path(path: Path) -> str:
    resolved = str(path.resolve())
    if os.name == "nt" and not resolved.startswith("\\\\?\\"):
        return "\\\\?\\" + resolved
    return resolved


def _savefig(fig: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(_long_path(path))


def _prior_configs(mode: str, radii_m: list[float]) -> list[PriorConfig]:
    if mode == "ball":
        return [PriorConfig(mode="prior_ball_R0", label=f"prior_ball_R0_{radius:g}m", scale_m=radius) for radius in radii_m]
    if mode == "gaussian":
        return [
            PriorConfig(mode="prior_gaussian_sigma0", label=f"prior_gaussian_sigma0_{radius:g}m", scale_m=radius)
            for radius in radii_m
        ]
    raise ValueError(mode)


def _sample_prior_offset_km(prior: PriorConfig) -> np.ndarray:
    if prior.mode == "prior_ball_R0":
        direction = np.random.normal(size=3)
        norm = float(np.linalg.norm(direction))
        if norm == 0.0:
            direction = np.array([1.0, 0.0, 0.0])
        else:
            direction = direction / norm
        radius = prior.scale_km * float(np.random.random() ** (1.0 / 3.0))
        return direction * radius
    if prior.mode == "prior_gaussian_sigma0":
        return np.random.normal(loc=0.0, scale=prior.scale_km, size=3)
    raise ValueError(prior.mode)


def _install_prior_region_initializer(namespace: dict[str, Any], prior: PriorConfig) -> None:
    """Patch legacy initialization to sample a declared prior region."""

    Optimizer = namespace["Optimizer"]

    def initialize_state_prior_region(self: Any, scenario: Any, error_range: float | None = None) -> np.ndarray:
        state_dict: dict[str, float] = {}
        offsets_km: list[list[float]] = []
        for i in range(scenario.num_users):
            offset = _sample_prior_offset_km(prior)
            offsets_km.append(offset.tolist())
            position = np.asarray(scenario.nodes[i].position, dtype=float) + offset
            state_dict[f"x_{i + 1}"] = float(position[0])
            state_dict[f"y_{i + 1}"] = float(position[1])
            state_dict[f"z_{i + 1}"] = float(position[2])
        for node in scenario.nodes:
            state_dict[f"delta_{node.node_id}"] = 0.0
        state = np.array([state_dict[param.name] for param in scenario.symbolic_parameter_vector], dtype=np.float64)
        offset_norms_m = [float(np.linalg.norm(offset) * 1000.0) for offset in np.asarray(offsets_km, dtype=float)]
        self._last_prior_region_initialization = {
            "initializer": "coarse_prior_region_initialization",
            "prior_mode": prior.mode,
            "prior_label": prior.label,
            "prior_scale_m": prior.scale_m,
            "prior_scale_km": prior.scale_km,
            "truth_state_used_for_prior_simulation": True,
            "truth_state_used_for_acceptance_covariance_or_fallback": False,
            "offset_norms_m": offset_norms_m,
            "initial_average_position_error_m": float(np.mean(offset_norms_m)),
            "initial_max_position_error_m": float(np.max(offset_norms_m)),
        }
        return state

    Optimizer.initialize_state = initialize_state_prior_region


def _install_nontruth_stage_a_completion(namespace: dict[str, Any]) -> None:
    """Patch IL completion so L1/L2 do not use true-state output rejection."""

    Optimizer = namespace["Optimizer"]
    previous_run = Optimizer.run

    def run_without_truth_stage_a(
        self: Any,
        algorithm: str,
        scenario: Any,
        x: np.ndarray,
        z: np.ndarray,
        num_steps: int = 10,
        tol: float = 1e-10,
        lr: float = 1e14,
        verbose: bool = False,
    ) -> np.ndarray:
        if algorithm != "IL":
            return previous_run(self, algorithm, scenario, x, z, num_steps=num_steps, tol=tol, lr=lr, verbose=verbose)

        assert len(x) == len(scenario.symbolic_parameter_vector)
        assert len(z) == len(scenario.get_links())
        x_current = np.asarray(x, dtype=np.float64)
        initial_cost = _residual_cost(scenario, x_current, z)
        converged = False
        for _ in range(num_steps + 1):
            x_new = np.asarray(self.il_step(scenario, x_current, z), dtype=np.float64)
            if self.converged(x_current, x_new, tol=tol):
                x_current = x_new
                converged = True
                break
            x_current = x_new
        final_cost = _residual_cost(scenario, x_current, z)
        if not np.all(np.isfinite(x_current)) or not np.isfinite(final_cost):
            raise ValueError(algorithm, "encountered nonfinite output")
        self._last_stage_a_diagnostics = {
            "stage_a_completion_mode": "finite_residual_no_truth_reversion",
            "truth_state_used_for_stage_a_acceptance": False,
            "initial_residual_cost": float(initial_cost),
            "final_residual_cost": float(final_cost),
            "residual_cost_decrease": float(initial_cost - final_cost),
            "convergence_status": "converged" if converged else "max_iterations_reached",
        }
        return x_current

    Optimizer.run = run_without_truth_stage_a


def _prepare_namespace(pipeline: PipelineSpec, prior: PriorConfig | None) -> tuple[dict[str, Any], list[int]]:
    namespace, executed_cells = _execute_legacy_namespace()
    if pipeline.uses_prior_region:
        if prior is None:
            raise ValueError(f"{pipeline.label} requires a prior region")
        _install_prior_region_initializer(namespace, prior)
    if not pipeline.residual_lm:
        _install_legacy_lm_trace(namespace)
    if pipeline.residual_lm:
        _install_residual_lm_acceptance(namespace)
        _install_nontruth_stage_a_completion(namespace)
    if pipeline.nontruth_map:
        _install_map_diagnosis(namespace, step_c3_cov_residual_scaled())
    return namespace, executed_cells


def _run_case(
    *,
    namespace: dict[str, Any],
    pipeline: PipelineSpec,
    case: StandardCase,
    prior: PriorConfig | None,
    effective_seed: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    Scenario = namespace["Scenario"]
    Optimizer = namespace["Optimizer"]
    _set_seed(effective_seed)
    start = time.perf_counter()
    row: dict[str, Any] = {
        "pipeline": pipeline.label,
        "case_id": case.case_id,
        "num_users": case.num_users,
        "num_satellites": case.num_satellites,
        "clock_std_dev_seconds": case.clock_std_dev_seconds,
        "seed": effective_seed,
        "base_case_seed": case.seed,
        "sidelink_topology": case.sidelink_topology,
        "propagation": case.propagation,
        "initializer": "coarse_prior_region_initialization" if pipeline.uses_prior_region else "legacy_truth_centered_cube",
        "prior_mode": prior.mode if prior is not None else "legacy_uniform_cube_error_range",
        "prior_label": prior.label if prior is not None else "legacy_cube_100km",
        "prior_radius_m": prior.scale_m if prior is not None and prior.mode == "prior_ball_R0" else None,
        "prior_sigma_m": prior.scale_m if prior is not None and prior.mode == "prior_gaussian_sigma0" else None,
        "legacy_error_range_km": case.legacy_error_range_km if not pipeline.uses_prior_region else None,
        "stage_c_applicable": pipeline.map_enabled,
        "truth_state_used_for_prior_simulation": pipeline.truth_state_used_for_prior_simulation,
        "truth_state_used_for_stage_a_acceptance": pipeline.truth_state_used_for_stage_a_acceptance,
        "truth_state_used_for_lm_acceptance": pipeline.truth_state_used_for_lm_acceptance,
        "truth_state_used_for_map_covariance": pipeline.truth_state_used_for_map_covariance,
        "truth_state_used_for_map_acceptance": pipeline.truth_state_used_for_map_acceptance,
        "truth_state_used_for_metrics": pipeline.truth_state_used_for_metrics,
        "truth_used_algorithmically": bool(
            pipeline.truth_state_used_for_stage_a_acceptance
            or pipeline.truth_state_used_for_lm_acceptance
            or pipeline.truth_state_used_for_map_covariance
            or pipeline.truth_state_used_for_map_acceptance
        ),
        "truth_use_label": (
            "prior_simulation_and_metrics_only"
            if pipeline.uses_prior_region
            else "legacy_reproduction_truth_gated"
        ),
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
    row["symbolic_parameter_order"] = [str(param) for param in scenario.symbolic_parameter_vector]
    row["stage_b_residual_cost_before"] = None
    row["stage_b_residual_cost_after"] = None

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
    except Exception as exc:  # noqa: BLE001 - preserve legacy fallback shape while recording it.
        x_il = x_init.copy()
        row["stage_a_status"] = "failed_fallback_to_initial_state"
        row["failures"].append({"stage": "IL", "error_type": type(exc).__name__, "error": str(exc)})
        row["fallbacks"].append("IL_failed_to_initial_state")

    stage_a_diag = getattr(optimizer, "_last_stage_a_diagnostics", {})
    row["stage_a_completion_mode"] = stage_a_diag.get(
        "stage_a_completion_mode",
        "legacy_check_output_truth_reversion" if pipeline.label == "legacy_exact_truth_gated" else "not_recorded",
    )
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
    except Exception as exc:  # noqa: BLE001 - legacy-compatible fallback.
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
            "accepted_step_count": int(sum(1 for item in lm_trace if item.get("accepted"))),
            "rejected_step_count": int(sum(1 for item in lm_trace if not item.get("accepted"))),
            "rejection_reasons": [reason for item in lm_trace for reason in item.get("rejection_reasons", [])],
            "step_trace": lm_trace,
        },
    )
    row["lm_acceptance_mode"] = lm_diagnostics.get("lm_acceptance_mode", "truth_gated_legacy")
    row["lm_accepted_steps"] = int(lm_diagnostics.get("accepted_step_count", 0))
    row["lm_rejected_steps"] = int(lm_diagnostics.get("rejected_step_count", 0))
    row["lm_rejection_reasons"] = sorted(set(lm_diagnostics.get("rejection_reasons", [])))

    x_map: np.ndarray | None = None
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
    row["convergence_boolean"] = bool(
        row["stage_a_status"] == "passed"
        and row["stage_b_status"] == "passed"
        and (not pipeline.map_enabled or row["stage_c_status"] == "passed")
    )
    row["runtime_s"] = time.perf_counter() - start
    row["failure_reason"] = "; ".join(item.get("error", item.get("global_error", "")) for item in row["failures"]) or ""
    row["fallback_count"] = len(row["fallbacks"])
    row["failure_count"] = len(row["failures"])
    row["prior_diagnostics_json"] = _json_dumps(prior_diag)
    row["stage_a_diagnostics_json"] = _json_dumps(stage_a_diag)
    row["lm_diagnostics_json"] = _json_dumps(lm_diagnostics)
    row["map_diagnostics_json"] = _json_dumps(map_diagnostics)
    row["fallbacks_json"] = _json_dumps(row["fallbacks"])
    row["failures_json"] = _json_dumps(row["failures"])

    trace = {
        "pipeline": pipeline.label,
        "case_id": case.case_id,
        "seed": effective_seed,
        "prior_mode": row["prior_mode"],
        "prior_radius_m": row["prior_radius_m"],
        "prior_sigma_m": row["prior_sigma_m"],
        "prior_diagnostics": prior_diag,
        "stage_a_diagnostics": stage_a_diag,
        "lm_trace": lm_diagnostics.get("step_trace", lm_trace),
        "map_trace": map_diagnostics.get("step_trace", []),
        "truth_flags": {
            "truth_state_used_for_prior_simulation": row["truth_state_used_for_prior_simulation"],
            "truth_state_used_for_stage_a_acceptance": row["truth_state_used_for_stage_a_acceptance"],
            "truth_state_used_for_lm_acceptance": row["truth_state_used_for_lm_acceptance"],
            "truth_state_used_for_map_covariance": row["truth_state_used_for_map_covariance"],
            "truth_state_used_for_map_acceptance": row["truth_state_used_for_map_acceptance"],
            "truth_state_used_for_metrics": row["truth_state_used_for_metrics"],
        },
    }
    return row, trace


def _rows_for_cases(cases: list[StandardCase], priors: list[PriorConfig], seeds: list[int]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    traces: list[dict[str, Any]] = []
    l0 = PIPELINES[0]
    l1_l2 = PIPELINES[1:]
    for case in cases:
        namespace, _ = _prepare_namespace(l0, prior=None)
        row, trace = _run_case(namespace=namespace, pipeline=l0, case=case, prior=None, effective_seed=case.seed)
        rows.append(row)
        traces.append(trace)
    for case in cases:
        for seed in seeds:
            for prior in priors:
                for pipeline in l1_l2:
                    namespace, _ = _prepare_namespace(pipeline, prior=prior)
                    row, trace = _run_case(
                        namespace=namespace,
                        pipeline=pipeline,
                        case=case,
                        prior=prior,
                        effective_seed=seed,
                    )
                    rows.append(row)
                    traces.append(trace)
    return rows, traces


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row.keys()})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summary: list[dict[str, Any]] = []
    l0_by_case = {
        row["case_id"]: row
        for row in rows
        if row["pipeline"] == "legacy_exact_truth_gated"
    }
    grouped: dict[tuple[str, float, str], list[dict[str, Any]]] = {}
    for row in rows:
        if row["pipeline"] == "legacy_exact_truth_gated":
            continue
        radius = row["prior_radius_m"] if row["prior_radius_m"] is not None else row["prior_sigma_m"]
        grouped.setdefault((row["case_id"], float(radius), row["pipeline"]), []).append(row)
    for (case_id, radius_m, pipeline), items in sorted(grouped.items()):
        l0 = l0_by_case[case_id]
        stage_b_values = np.array([float(item["stage_b_localization_error_m"]) for item in items], dtype=float)
        stage_c_values = np.array(
            [
                np.nan if item["stage_c_localization_error_m"] is None else float(item["stage_c_localization_error_m"])
                for item in items
            ],
            dtype=float,
        )
        l0_b = float(l0["stage_b_localization_error_m"])
        l0_c = float(l0["stage_c_localization_error_m"]) if l0["stage_c_localization_error_m"] is not None else l0_b
        stage_b_mean = float(np.nanmean(stage_b_values))
        stage_c_mean = float(np.nanmean(stage_c_values)) if np.any(~np.isnan(stage_c_values)) else None
        convergence_probability = float(np.mean([item["convergence_boolean"] for item in items]))
        stage_b_manuscript_like = bool(stage_b_mean <= max(1.0, 2.0 * l0_b))
        stage_c_useful = bool(stage_c_mean is not None and stage_c_mean <= max(2.0, 3.0 * l0_c))
        summary.append(
            {
                "case_id": case_id,
                "pipeline": pipeline,
                "prior_radius_m": radius_m,
                "seed_count": len(items),
                "stage_b_localization_error_m_mean": stage_b_mean,
                "stage_b_localization_error_m_max": float(np.nanmax(stage_b_values)),
                "stage_c_localization_error_m_mean": stage_c_mean,
                "stage_c_localization_error_m_max": float(np.nanmax(stage_c_values)) if stage_c_mean is not None else None,
                "l0_stage_b_reference_m": l0_b,
                "l0_stage_c_reference_m": l0_c,
                "stage_b_ratio_to_l0": stage_b_mean / max(l0_b, 1.0e-12),
                "stage_c_ratio_to_l0": None if stage_c_mean is None else stage_c_mean / max(l0_c, 1.0e-12),
                "convergence_probability": convergence_probability,
                "stage_b_manuscript_like": stage_b_manuscript_like,
                "stage_c_useful": stage_c_useful,
            }
        )
    return summary


def _largest_radius(summary: list[dict[str, Any]], pipeline: str, field: str, *, primary_only: bool = True) -> float | None:
    filtered = [row for row in summary if row["pipeline"] == pipeline and bool(row[field])]
    if primary_only:
        filtered = [row for row in filtered if row["case_id"] == "std_nu3_ns10_fullmesh_los_clock1us_seed0"]
    if not filtered:
        return None
    return float(max(row["prior_radius_m"] for row in filtered))


def _write_npz(rows: list[dict[str, Any]]) -> None:
    labels = np.array([row["pipeline"] for row in rows])
    cases = np.array([row["case_id"] for row in rows])
    radii = np.array([np.nan if row["prior_radius_m"] in {None, ""} else float(row["prior_radius_m"]) for row in rows], dtype=float)
    stage_b = np.array([float(row["stage_b_localization_error_m"]) for row in rows], dtype=float)
    stage_c = np.array(
        [np.nan if row["stage_c_localization_error_m"] is None else float(row["stage_c_localization_error_m"]) for row in rows],
        dtype=float,
    )
    np.savez(
        OUTPUT_ROOT / "arrays.npz",
        pipelines=labels,
        cases=cases,
        prior_radius_m=radii,
        stage_b_localization_error_m=stage_b,
        stage_c_localization_error_m=stage_c,
    )


def _plot_radius_metric(summary: list[dict[str, Any]], metric: str, filename: str, ylabel: str) -> list[str]:
    FIGURE_ROOT.mkdir(parents=True, exist_ok=True)
    primary = [row for row in summary if row["case_id"] == "std_nu3_ns10_fullmesh_los_clock1us_seed0"]
    fig, ax = plt.subplots(figsize=(6.7, 3.8), dpi=180)
    for pipeline in ["legacy_nontruth_lm", "legacy_surgical_nontruth"]:
        rows = [row for row in primary if row["pipeline"] == pipeline]
        if not rows:
            continue
        x = [float(row["prior_radius_m"]) for row in rows]
        y = [np.nan if row[metric] is None else float(row[metric]) for row in rows]
        ax.plot(x, y, marker="o", label=pipeline)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Prior radius R0 [m]")
    ax.set_ylabel(ylabel)
    ax.set_title("Diagnostic only - coarse prior-region sweep")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend()
    paths = []
    for suffix in ["png", "pdf"]:
        path = FIGURE_ROOT / f"{filename}.{suffix}"
        fig.tight_layout()
        _savefig(fig, path)
        paths.append(str(path.relative_to(SAT_SIM_ROOT)))
    plt.close(fig)
    return paths


def _plot_convergence_probability(summary: list[dict[str, Any]], seed_count: int) -> list[str]:
    if seed_count <= 1:
        return []
    return _plot_radius_metric(
        summary,
        metric="convergence_probability",
        filename="prior_radius_vs_convergence_probability",
        ylabel="Convergence probability",
    )


def _plot_truth_use_map() -> list[str]:
    FIGURE_ROOT.mkdir(parents=True, exist_ok=True)
    components = ["Prior sim", "Stage A accept", "LM accept", "Covariance", "MAP accept", "Metrics"]
    values = np.array(
        [
            [
                int(pipeline.truth_state_used_for_prior_simulation),
                int(pipeline.truth_state_used_for_stage_a_acceptance),
                int(pipeline.truth_state_used_for_lm_acceptance),
                int(pipeline.truth_state_used_for_map_covariance),
                int(pipeline.truth_state_used_for_map_acceptance),
                int(pipeline.truth_state_used_for_metrics),
            ]
            for pipeline in PIPELINES
        ],
        dtype=float,
    )
    fig, ax = plt.subplots(figsize=(8.0, 3.4), dpi=180)
    image = ax.imshow(values, cmap="Reds", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(np.arange(len(components)))
    ax.set_xticklabels(components, rotation=15, ha="right")
    ax.set_yticks(np.arange(len(PIPELINES)))
    ax.set_yticklabels([pipeline.label for pipeline in PIPELINES])
    for i in range(values.shape[0]):
        for j in range(values.shape[1]):
            ax.text(j, i, "yes" if values[i, j] else "no", ha="center", va="center", fontsize=8)
    ax.set_title("Diagnostic only - prior-region truth-use map")
    fig.colorbar(image, ax=ax, fraction=0.04, pad=0.02)
    paths = []
    for suffix in ["png", "pdf"]:
        path = FIGURE_ROOT / f"prior_region_truth_use_map.{suffix}"
        fig.tight_layout()
        _savefig(fig, path)
        paths.append(str(path.relative_to(SAT_SIM_ROOT)))
    plt.close(fig)
    return paths


def _figure_outputs(summary: list[dict[str, Any]], seed_count: int) -> dict[str, list[str] | str]:
    figures: dict[str, list[str] | str] = {
        "prior_radius_vs_stage_b_localization": _plot_radius_metric(
            summary,
            metric="stage_b_localization_error_m_mean",
            filename="prior_radius_vs_stage_b_localization",
            ylabel="Stage B localization error [m]",
        ),
        "prior_radius_vs_stage_c_localization": _plot_radius_metric(
            summary,
            metric="stage_c_localization_error_m_mean",
            filename="prior_radius_vs_stage_c_localization",
            ylabel="Stage C localization error [m]",
        ),
        "prior_region_truth_use_map": _plot_truth_use_map(),
    }
    convergence_paths = _plot_convergence_probability(summary, seed_count)
    figures["prior_radius_vs_convergence_probability"] = (
        convergence_paths if convergence_paths else "unavailable: seed_count <= 1"
    )
    return figures


def _build_report(
    *,
    rows: list[dict[str, Any]],
    summary: list[dict[str, Any]],
    figures: dict[str, list[str] | str],
    priors: list[PriorConfig],
    seeds: list[int],
    runtime_s: float,
) -> dict[str, Any]:
    largest_l1_b = _largest_radius(summary, "legacy_nontruth_lm", "stage_b_manuscript_like")
    largest_l2_b = _largest_radius(summary, "legacy_surgical_nontruth", "stage_b_manuscript_like")
    largest_l2_c = _largest_radius(summary, "legacy_surgical_nontruth", "stage_c_useful")
    largest_stage_b = min(value for value in [largest_l1_b, largest_l2_b] if value is not None) if largest_l1_b and largest_l2_b else None
    if largest_stage_b is not None and largest_stage_b >= 1000.0 and largest_l2_c is not None and largest_l2_c >= 1000.0:
        decision = "green"
        defensible = True
        next_action = "Promote legacy-surgical plus prior-region initialization to candidate figure generation."
    elif largest_stage_b is not None and largest_stage_b >= 100.0:
        decision = "yellow"
        defensible = True
        next_action = "Use the prior-region path only with explicit R0 sensitivity and conservative wording."
    else:
        decision = "red"
        defensible = False
        next_action = "Do not promote until a stronger coarse initializer is implemented."
    return {
        "manuscript_ready": False,
        "non_final_diagnostic": True,
        "decision": decision,
        "prior_region_initialization_defensible": defensible,
        "runtime_s": runtime_s,
        "seed_count": len(seeds),
        "seeds": seeds,
        "multi_seed_sensitivity": "not_run; seed 0 only" if len(seeds) == 1 else "run",
        "prior_configs": [asdict(prior) for prior in priors],
        "pipelines": [asdict(pipeline) for pipeline in PIPELINES],
        "units_ledger": UNITS_LEDGER,
        "scientific_justification": SCIENTIFIC_JUSTIFICATION,
        "initialization_model": {
            "implemented_modes": ["prior_ball_R0", "prior_gaussian_sigma0"],
            "executed_mode": priors[0].mode if priors else None,
            "description": "UE initial positions are sampled from a declared coarse prior region centered on truth only for simulation construction.",
        },
        "summary": summary,
        "largest_stage_b_radius_m_primary": largest_stage_b,
        "largest_l1_stage_b_radius_m_primary": largest_l1_b,
        "largest_l2_stage_b_radius_m_primary": largest_l2_b,
        "largest_stage_c_radius_m_primary": largest_l2_c,
        "truth_centered_initialization_caveat_removed": True,
        "truth_use": {
            "prior_simulation_construction": True,
            "stage_a_acceptance_l1_l2": False,
            "lm_acceptance_l1_l2": False,
            "covariance_l2": False,
            "map_acceptance_l2": False,
            "metrics": True,
        },
        "what_remains_unsafe": [
            "Do not call the prior construction truth-free; truth centers the simulated prior region.",
            "Do not claim broad robustness because the default run is seed 0 only.",
            "Do not claim V24-gauged metric equivalence; these remain legacy all-clock metrics.",
            "Do not use L0 as deployable algorithm evidence.",
        ],
        "safe_claims": [
            "The L1/L2 estimator decisions do not use true-state error for Stage A completion, LM acceptance, covariance, or MAP acceptance.",
            "The prior-region assumption is explicit and parameterized by R0.",
            "On bounded seed-0 rows, the primary case remains manuscript-like through at least the reported largest R0.",
        ],
        "unsafe_claims": [
            "Do not claim no truth is used anywhere; truth is used for simulation prior construction and offline metrics.",
            "Do not claim multi-seed convergence probability when seed_count is 1.",
            "Do not claim final manuscript readiness.",
        ],
        "suggested_manuscript_wording": SUGGESTED_MANUSCRIPT_WORDING,
        "recommended_next_action": next_action,
        "figures": figures,
    }


def _write_report_md(report: dict[str, Any]) -> None:
    lines = [
        "# Legacy Surgical Prior-Region Initialization Report",
        "",
        "> Diagnostic only; not manuscript-ready.",
        "",
        "## 1. Executive summary",
        "",
        f"- Decision: `{report['decision']}`.",
        f"- Prior-region initialization defensible on bounded rows: `{report['prior_region_initialization_defensible']}`.",
        f"- Multi-seed sensitivity: {report['multi_seed_sensitivity']}.",
        "",
        "## 2. Prior-region scientific justification",
        "",
    ]
    lines.extend(f"- {item}" for item in report["scientific_justification"])
    lines.extend(
        [
            "",
            "## 3. Initialization model",
            "",
            report["initialization_model"]["description"],
            "",
            "- `prior_ball_R0`: uniform sample inside a 3-D ball of radius `R0`.",
            "- `prior_gaussian_sigma0`: Gaussian sample with isotropic standard deviation `sigma0`.",
            "",
            "## 4. Prior-radius sweep results",
            "",
            "| Case | Pipeline | R0 [m] | Stage B [m] | Stage C [m] | Conv. prob. |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for row in report["summary"]:
        c_value = row["stage_c_localization_error_m_mean"]
        c_text = "n/a" if c_value is None else f"{c_value:.4g}"
        lines.append(
            f"| `{row['case_id']}` | `{row['pipeline']}` | {row['prior_radius_m']:.4g} | "
            f"{row['stage_b_localization_error_m_mean']:.4g} | {c_text} | {row['convergence_probability']:.3g} |"
        )
    lines.extend(
        [
            "",
            "## 5. Largest prior radius retaining manuscript-like Stage B behavior",
            "",
            f"- Primary case: `{report['largest_stage_b_radius_m_primary']}` m.",
            f"- L1 primary: `{report['largest_l1_stage_b_radius_m_primary']}` m.",
            f"- L2 primary: `{report['largest_l2_stage_b_radius_m_primary']}` m.",
            "",
            "## 6. Largest prior radius retaining useful Stage C behavior",
            "",
            f"- L2 primary: `{report['largest_stage_c_radius_m_primary']}` m.",
            "",
            "## 7. Whether this removes the truth-centered initialization caveat",
            "",
            f"- Removed as an algorithm description caveat: `{report['truth_centered_initialization_caveat_removed']}`.",
            "- Remaining truth use is explicitly labeled as prior-region simulation construction and offline metrics.",
            "",
            "## 8. What remains unsafe",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in report["what_remains_unsafe"])
    lines.extend(
        [
            "",
            "## 9. Suggested manuscript wording",
            "",
            report["suggested_manuscript_wording"],
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
        if isinstance(paths, list):
            lines.append(f"- `{name}`: " + ", ".join(f"`{path}`" for path in paths))
        else:
            lines.append(f"- `{name}`: {paths}")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_outputs(rows: list[dict[str, Any]], traces: list[dict[str, Any]], summary: list[dict[str, Any]], report: dict[str, Any]) -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    REPORTS_ROOT.mkdir(parents=True, exist_ok=True)
    _write_csv(OUTPUT_ROOT / "raw.csv", rows)
    _write_csv(OUTPUT_ROOT / "summary.csv", summary)
    with (OUTPUT_ROOT / "trace.jsonl").open("w", encoding="utf-8") as handle:
        for trace in traces:
            handle.write(json.dumps(trace, default=_json_default) + "\n")
    _write_npz(rows)
    metadata = {
        "manuscript_ready": False,
        "non_final_diagnostic": True,
        "output_root": str(OUTPUT_ROOT.relative_to(SAT_SIM_ROOT)),
        "script": str(Path(__file__).relative_to(SAT_SIM_ROOT)),
        "script_sha256": _hash_file(Path(__file__).resolve()),
        "notebook_path": str(NOTEBOOK_PATH.relative_to(SAT_SIM_ROOT)),
        "notebook_sha256": _hash_file(NOTEBOOK_PATH),
        "extracted_cell_hashes": _selected_cell_hashes(),
        "prior_radii_m": PRIOR_RADII_M,
        "truth_use": report["truth_use"],
        "protected_file_policy": {
            "notebook_edited": False,
            "manuscript_files_edited": False,
            "existing_manuscript_result_files_edited": False,
        },
    }
    (OUTPUT_ROOT / "metadata.json").write_text(json.dumps(metadata, indent=2, default=_json_default), encoding="utf-8")
    REPORT_JSON.write_text(json.dumps(report, indent=2, default=_json_default), encoding="utf-8")
    _write_report_md(report)


def run(*, prior_mode: str, seeds: list[int], cases: list[StandardCase]) -> dict[str, Any]:
    start = time.perf_counter()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    FIGURE_ROOT.mkdir(parents=True, exist_ok=True)
    REPORTS_ROOT.mkdir(parents=True, exist_ok=True)
    priors = _prior_configs(prior_mode, PRIOR_RADII_M)
    rows, traces = _rows_for_cases(cases, priors, seeds)
    summary = _summarize(rows)
    figures = _figure_outputs(summary, seed_count=len(seeds))
    runtime_s = time.perf_counter() - start
    report = _build_report(rows=rows, summary=summary, figures=figures, priors=priors, seeds=seeds, runtime_s=runtime_s)
    _write_outputs(rows, traces, summary, report)
    return report


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prior-mode", choices=["ball", "gaussian"], default="ball")
    parser.add_argument("--multi-seed", action="store_true", help="Run seeds 0-9 instead of seed 0 only.")
    parser.add_argument("--primary-only", action="store_true", help="Run only the primary standard case.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    seeds = list(range(10)) if args.multi_seed else DEFAULT_SEEDS
    cases = [STANDARD_CASES[0]] if args.primary_only else STANDARD_CASES
    report = run(prior_mode=args.prior_mode, seeds=seeds, cases=cases)
    print(
        json.dumps(
            {
                "decision": report["decision"],
                "largest_stage_b_radius_m_primary": report["largest_stage_b_radius_m_primary"],
                "largest_stage_c_radius_m_primary": report["largest_stage_c_radius_m_primary"],
                "multi_seed_sensitivity": report["multi_seed_sensitivity"],
            },
            indent=2,
            default=_json_default,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
