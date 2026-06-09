"""Generate non-final JCLS wave-results exploration diagnostics.

The runner is intentionally diagnostic-only. It writes package-native evidence
products under ``outputs/wave_results`` and human-readable reports under
``outputs/reports`` without touching notebook, manuscript, PSFrag, or existing
manuscript-result files.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

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
    coarse_individual_localization,
    joint_lm_jcls,
    step_c7_residual_cov_sync_safeguard_refinement,
)
from jcls_sim.bounds import (  # noqa: E402
    average_clock_bound_from_covariance,
    average_ue_peb_from_covariance,
    covariance_from_fim,
    manuscript_crlb_reportability_from_fim,
)
from jcls_sim.configs import V24ScenarioConfig, directed_sidelink_links, downlink_links  # noqa: E402
from jcls_sim.constants import C_KM_PER_S  # noqa: E402
from jcls_sim.fim import gaussian_fim_from_jacobian  # noqa: E402
from jcls_sim.geometry import GroundReference, manuscript_candidate_geometry  # noqa: E402
from jcls_sim.jacobian import analytic_toa_jacobian_km, toa_range_vector_from_theta_km  # noqa: E402
from jcls_sim.metrics import all_non_reference_clock_error, position_error_m  # noqa: E402
from jcls_sim.noise import LinkBudgetConfig, range_sigmas_for_links  # noqa: E402
from jcls_sim.parameters import pack_v24_theta, unpack_v24_theta  # noqa: E402


PRODUCTS = (
    "observability",
    "satellite_substitution",
    "clock_tolerance",
    "sparse_sidelink",
    "time_to_accuracy",
    "literature_comparison",
)
THRESHOLDS_M = (10.0, 1.0, 0.2, 0.1)
DEFAULT_CLOCK_SIGMA_SECONDS = 0.5e-6 * 15.0
DEFAULT_REFERENCE = GroundReference(latitude_deg=42.361145, longitude_deg=-71.090289, altitude_m=30.0)
NONFINAL_FLAGS = {
    "non_final": True,
    "candidate_diagnostic": True,
    "not_for_manuscript_submission": True,
    "manuscript_ready": False,
    "human_signoff_required": True,
}


@dataclass(frozen=True)
class WaveOptions:
    """Runtime options for the wave-results runner."""

    cache_root: Path = SAT_SIM_ROOT / "outputs" / "wave_results"
    dry_run: bool = False
    list_plan: bool = False
    resume: bool = True
    force_rerun: bool = False
    max_runtime_minutes: float | None = None
    row_timeout_seconds: float | None = None
    trial_timeout_seconds: float | None = None
    max_trials: int | None = None
    only_product: str | None = None
    only_row: str | None = None
    pilot: bool = False
    full: bool = False
    render_plots: bool = True


@dataclass(frozen=True)
class WavePaths:
    """Derived output paths for one cache root."""

    output_root: Path
    report_root: Path

    @classmethod
    def from_cache_root(cls, cache_root: Path) -> "WavePaths":
        root = cache_root.resolve()
        if root.name == "wave_results":
            return cls(output_root=root, report_root=root.parent / "reports")
        return cls(output_root=root, report_root=root / "reports")


@dataclass(frozen=True)
class ProductResult:
    """Summary of one generated product."""

    name: str
    status: str
    row_count: int = 0
    summary: dict[str, Any] = field(default_factory=dict)
    files: dict[str, str] = field(default_factory=dict)
    failed_rows: list[str] = field(default_factory=list)


def _repo_rel(path: Path) -> str:
    """Return a stable sat-sim-relative path when possible."""

    try:
        return path.resolve().relative_to(SAT_SIM_ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _json_ready(value: Any) -> Any:
    """Convert numpy and nonfinite values to strict JSON-compatible objects."""

    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    if isinstance(value, np.ndarray):
        return _json_ready(value.tolist())
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, Path):
        return _repo_rel(value)
    return value


def _write_json(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_json_ready(payload), indent=2, sort_keys=True), encoding="utf-8")
    return _repo_rel(path)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: Iterable[str] | None = None) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        seen: list[str] = []
        for row in rows:
            for key in row:
                if key not in seen:
                    seen.append(key)
        fields = seen
    field_list = list(fields)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=field_list, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_value(row.get(key)) for key in field_list})
    return _repo_rel(path)


def _csv_value(value: Any) -> Any:
    if isinstance(value, (list, tuple)):
        return ";".join(str(item) for item in value)
    if isinstance(value, np.ndarray):
        return ";".join(str(item) for item in value.reshape(-1).tolist())
    if isinstance(value, (float, np.floating)) and not math.isfinite(float(value)):
        return ""
    if value is None:
        return ""
    return value


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(_json_ready(payload), sort_keys=True) + "\n")


def _save_plot(fig: Any, path: Path) -> list[str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    png = path.with_suffix(".png")
    fig.savefig(png, dpi=180)
    plt.close(fig)
    return [_repo_rel(path), _repo_rel(png)]


def _hash_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(_json_ready(payload), sort_keys=True).encode("utf-8")).hexdigest()[:16]


def _nanmean(values: Iterable[float | None]) -> float | None:
    array = np.asarray([float(value) for value in values if value is not None and math.isfinite(float(value))], dtype=float)
    if array.size == 0:
        return None
    return float(np.mean(array))


def _nanmin(values: Iterable[float | None]) -> float | None:
    array = np.asarray([float(value) for value in values if value is not None and math.isfinite(float(value))], dtype=float)
    if array.size == 0:
        return None
    return float(np.min(array))


def _safe_ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None:
        return None
    if not math.isfinite(float(numerator)) or not math.isfinite(float(denominator)) or abs(float(denominator)) < 1e-18:
        return None
    return float(numerator) / float(denominator)


def _clock_km_to_ns(value_km: float | None) -> float | None:
    if value_km is None or not math.isfinite(float(value_km)):
        return None
    return float(value_km) / C_KM_PER_S * 1.0e9


def _clock_seconds_to_km(value_s: float) -> float:
    return float(value_s) * C_KM_PER_S


def _full_clock_dict_from_theta(theta: np.ndarray, num_users: int, num_satellites: int) -> dict[int, float]:
    _positions, ue_clocks, sat_clocks = unpack_v24_theta(theta, num_users, num_satellites)
    clocks: dict[int, float] = {node_id: float(value) for node_id, value in enumerate(ue_clocks, start=1)}
    reference_id = num_users + 1
    clocks[reference_id] = 0.0
    for offset, value in enumerate(sat_clocks, start=1):
        clocks[reference_id + offset] = float(value)
    return clocks


def _position_rmse_m(true_theta: np.ndarray, est_theta: np.ndarray, num_users: int, num_satellites: int) -> tuple[float, list[float]]:
    true_positions, _true_ue_clock, _true_sat_clock = unpack_v24_theta(true_theta, num_users, num_satellites)
    est_positions, _est_ue_clock, _est_sat_clock = unpack_v24_theta(est_theta, num_users, num_satellites)
    errors = position_error_m(true_positions, est_positions)
    return float(np.sqrt(np.mean(np.square(errors)))), [float(item) for item in errors.tolist()]


def _sync_error_km(true_theta: np.ndarray, est_theta: np.ndarray, num_users: int, num_satellites: int) -> float:
    true_clocks = _full_clock_dict_from_theta(true_theta, num_users, num_satellites)
    est_clocks = _full_clock_dict_from_theta(est_theta, num_users, num_satellites)
    return all_non_reference_clock_error(true_clocks, est_clocks, num_users, num_satellites)


def _graph_components(num_users: int, undirected_edges: list[tuple[int, int]]) -> list[list[int]]:
    neighbors = {node_id: set() for node_id in range(1, num_users + 1)}
    for left, right in undirected_edges:
        neighbors[left].add(right)
        neighbors[right].add(left)
    seen: set[int] = set()
    components: list[list[int]] = []
    for node_id in range(1, num_users + 1):
        if node_id in seen:
            continue
        stack = [node_id]
        component: list[int] = []
        seen.add(node_id)
        while stack:
            current = stack.pop()
            component.append(current)
            for neighbor in sorted(neighbors[current]):
                if neighbor not in seen:
                    seen.add(neighbor)
                    stack.append(neighbor)
        components.append(sorted(component))
    return components


def _sidelink_graph(
    *,
    num_users: int,
    edge_probability: float,
    seed: int,
    full_mesh: bool = False,
) -> tuple[tuple[tuple[int, int], ...], list[tuple[int, int]], dict[str, Any]]:
    if num_users < 2 or edge_probability <= 0.0:
        directed: tuple[tuple[int, int], ...] = tuple()
        undirected: list[tuple[int, int]] = []
    elif full_mesh or edge_probability >= 1.0:
        directed = directed_sidelink_links(num_users)
        undirected = [(left, right) for left in range(1, num_users + 1) for right in range(left + 1, num_users + 1)]
    else:
        rng = np.random.default_rng(int(seed))
        undirected = []
        directed_list = []
        for left in range(1, num_users + 1):
            for right in range(left + 1, num_users + 1):
                if float(rng.random()) <= edge_probability:
                    undirected.append((left, right))
                    directed_list.extend([(left, right), (right, left)])
        directed = tuple(directed_list)
    components = _graph_components(num_users, undirected)
    possible_edges = num_users * (num_users - 1) / 2.0
    average_degree = 0.0 if num_users == 0 else 2.0 * len(undirected) / max(num_users, 1)
    metadata = {
        "sl_edge_probability": float(edge_probability),
        "undirected_edge_count": int(len(undirected)),
        "directed_sl_measurement_count": int(len(directed)),
        "possible_undirected_edges": int(possible_edges),
        "average_degree": float(average_degree),
        "connected_components": components,
        "connected_component_count": int(len(components)),
        "graph_connected": bool(len(components) == 1 if num_users >= 1 else False),
    }
    return directed, undirected, metadata


def _make_wave_scenario(
    *,
    num_users: int,
    num_satellites: int,
    seed: int,
    clock_sigma_seconds: float = DEFAULT_CLOCK_SIGMA_SECONDS,
    sl_edge_probability: float = 1.0,
    full_mesh: bool = True,
    sigma_scale: float = 1.0,
) -> tuple[V24ScenarioConfig, dict[str, Any]]:
    geometry = manuscript_candidate_geometry(
        num_users=num_users,
        num_satellites=num_satellites,
        seed=seed,
        reference=DEFAULT_REFERENCE,
        ue_radius_m=500.0,
        minimum_elevation_deg=30.0,
        satellite_pool_size=max(24, num_satellites + 8),
        satellite_altitude_km=550.0,
    )
    dl_links = downlink_links(num_users, num_satellites)
    sl_links, undirected_edges, graph = _sidelink_graph(
        num_users=num_users,
        edge_probability=sl_edge_probability,
        seed=seed + 991,
        full_mesh=full_mesh,
    )
    links = tuple(dl_links + sl_links)
    sigmas, link_records, noise_summary = range_sigmas_for_links(
        ue_positions_km=geometry.ue_positions_km,
        satellite_positions_km=geometry.satellite_positions_km,
        links=links,
        num_users=num_users,
        config=LinkBudgetConfig(),
    )
    sigmas = np.asarray(sigmas, dtype=float) * float(sigma_scale)
    rng = np.random.default_rng(seed + 2026)
    ue_clocks = rng.normal(0.0, _clock_seconds_to_km(clock_sigma_seconds), size=num_users)
    sat_clocks = rng.normal(0.0, _clock_seconds_to_km(clock_sigma_seconds), size=max(0, num_satellites - 1))
    scenario = V24ScenarioConfig(
        scenario_name=f"wave_nu{num_users}_ns{num_satellites}_seed{seed}",
        num_users=int(num_users),
        num_satellites=int(num_satellites),
        seed=int(seed),
        ue_positions_km=geometry.ue_positions_km,
        satellite_positions_km=geometry.satellite_positions_km,
        ue_clock_offsets_km=ue_clocks,
        non_reference_satellite_clock_offsets_km=sat_clocks,
        links=links,
        range_std_devs_km=sigmas,
    )
    metadata = {
        "seed": int(seed),
        "clock_sigma_seconds": float(clock_sigma_seconds),
        "clock_sigma_ns": float(clock_sigma_seconds * 1.0e9),
        "clock_sigma_km": float(_clock_seconds_to_km(clock_sigma_seconds)),
        "clock_drift_reference": "0.5 ppm over 15 s gives 7.5 us, approximately 2.25 km range-domain bias",
        "sl_graph": graph,
        "sl_undirected_edges": undirected_edges,
        "geometry": geometry.metadata,
        "noise": {**noise_summary, "sigma_scale": float(sigma_scale)},
        "link_records": link_records,
    }
    return scenario, metadata


def _dl_only_scenario(scenario: V24ScenarioConfig) -> V24ScenarioConfig:
    indices = [index for index, (_receiver, transmitter) in enumerate(scenario.links) if transmitter > scenario.num_users]
    return V24ScenarioConfig(
        scenario_name=f"{scenario.scenario_name}_dl_only",
        num_users=scenario.num_users,
        num_satellites=scenario.num_satellites,
        seed=scenario.seed,
        ue_positions_km=scenario.ue_positions_km,
        satellite_positions_km=scenario.satellite_positions_km,
        ue_clock_offsets_km=scenario.ue_clock_offsets_km,
        non_reference_satellite_clock_offsets_km=scenario.non_reference_satellite_clock_offsets_km,
        links=tuple(scenario.links[index] for index in indices),
        range_std_devs_km=np.asarray([scenario.range_std_devs_km[index] for index in indices], dtype=float),
    )


def _measurement_for_scenario(scenario: V24ScenarioConfig, rng: np.random.Generator) -> np.ndarray:
    theta = scenario.theta()
    mean = toa_range_vector_from_theta_km(theta, scenario.links, scenario.satellite_positions_km, scenario.num_users, scenario.num_satellites)
    return mean + rng.normal(0.0, np.asarray(scenario.range_std_devs_km, dtype=float), size=mean.size)


def _fim_diagnostics(scenario: V24ScenarioConfig) -> tuple[dict[str, Any], np.ndarray, np.ndarray]:
    theta = scenario.theta()
    jac = analytic_toa_jacobian_km(theta, scenario.links, scenario.satellite_positions_km, scenario.num_users, scenario.num_satellites)
    fim = gaussian_fim_from_jacobian(jac, scenario.range_std_devs_km)
    dim = int(fim.shape[0])
    rank = int(np.linalg.matrix_rank(fim))
    try:
        condition = float(np.linalg.cond(fim))
    except np.linalg.LinAlgError:
        condition = math.inf
    reportability = manuscript_crlb_reportability_from_fim(fim, scenario.num_users, scenario.num_satellites)
    full_rank = rank == dim
    crlb_position_m = None
    crlb_clock_ns = None
    covariance_method = None
    if full_rank:
        covariance, covariance_meta = covariance_from_fim(fim)
        covariance_method = covariance_meta["method"]
        crlb_position_m = 1000.0 * average_ue_peb_from_covariance(covariance, scenario.num_users, scenario.num_satellites)
        crlb_clock_ns = _clock_km_to_ns(average_clock_bound_from_covariance(covariance, scenario.num_users, scenario.num_satellites))
    diagnostics = {
        "fim_rank": rank,
        "state_dimension": dim,
        "rank_deficiency": int(dim - rank),
        "condition_number": condition,
        "log10_condition_number": math.log10(condition) if condition and math.isfinite(condition) and condition > 0.0 else None,
        "crlb_position_m": crlb_position_m,
        "crlb_clock_ns": crlb_clock_ns,
        "crlb_status": "finite_crlb" if full_rank else "rank_deficient_diagnostic",
        "crlb_full_rank": full_rank,
        "bounds_reportability_status_raw": reportability["crlb_status"],
        "ue_position_subspace_estimable": reportability["ue_position_subspace_estimable"],
        "clock_subspace_estimable": reportability["clock_subspace_estimable"],
        "covariance_method": covariance_method,
    }
    return diagnostics, jac, fim


def _run_empirical_trial(
    scenario: V24ScenarioConfig,
    z_full: np.ndarray,
    rng: np.random.Generator,
    *,
    graph_connected: bool,
    run_stage_c: bool,
) -> dict[str, Any]:
    true_theta = scenario.theta()
    dl_scenario = _dl_only_scenario(scenario)
    z_dl = z_full[: len(dl_scenario.links)]
    stage_a_failure = None
    stage_a_theta = None
    try:
        stage_a = coarse_individual_localization(dl_scenario, z_dl)
        stage_a_theta = stage_a.theta
        stage_a_position_rmse_m, stage_a_position_by_ue_m = _position_rmse_m(true_theta, stage_a.theta, scenario.num_users, scenario.num_satellites)
        stage_a_success = bool(stage_a.success)
        stage_a_status = "converged" if stage_a.success else "failed_or_rank_deficient"
    except Exception as exc:  # noqa: BLE001 - failure is recorded, not hidden.
        stage_a_failure = f"{type(exc).__name__}: {exc}"
        stage_a_position_rmse_m = None
        stage_a_position_by_ue_m = []
        stage_a_success = False
        stage_a_status = "failed"

    single_ue = scenario.num_users == 1
    jcls_applicable = bool((not single_ue) and graph_connected and len(scenario.links) > len(dl_scenario.links))
    stage_b = None
    stage_c = None
    stage_b_theta = None
    stage_b_failure = None
    stage_c_failure = None
    if jcls_applicable:
        initial_theta = stage_a_theta
        if initial_theta is None:
            initial_positions = np.asarray(scenario.ue_positions_km, dtype=float) + rng.normal(0.0, 0.25, size=(scenario.num_users, 3))
            initial_theta = pack_v24_theta(
                initial_positions,
                np.zeros(scenario.num_users, dtype=float),
                np.zeros(scenario.num_satellites - 1, dtype=float),
            )
        try:
            stage_b = joint_lm_jcls(scenario, z_full, initial_theta)
            stage_b_theta = stage_b.theta
        except Exception as exc:  # noqa: BLE001
            stage_b_failure = f"{type(exc).__name__}: {exc}"
        if run_stage_c and stage_b_theta is not None:
            try:
                prediction = toa_range_vector_from_theta_km(
                    stage_b_theta,
                    scenario.links,
                    scenario.satellite_positions_km,
                    scenario.num_users,
                    scenario.num_satellites,
                )
                residual = z_full - prediction
                jac = analytic_toa_jacobian_km(
                    stage_b_theta,
                    scenario.links,
                    scenario.satellite_positions_km,
                    scenario.num_users,
                    scenario.num_satellites,
                )
                block_slices = StepC7BlockSlices(
                    position=slice(0, 3 * scenario.num_users),
                    ue_clock=slice(3 * scenario.num_users, 4 * scenario.num_users),
                    satellite_clock=slice(4 * scenario.num_users, stage_b_theta.size),
                    clock_drift=slice(stage_b_theta.size, stage_b_theta.size),
                )

                def residual_at_state(theta: np.ndarray) -> np.ndarray:
                    return z_full - toa_range_vector_from_theta_km(
                        theta,
                        scenario.links,
                        scenario.satellite_positions_km,
                        scenario.num_users,
                        scenario.num_satellites,
                    )

                stage_c = step_c7_residual_cov_sync_safeguard_refinement(
                    stage_b_theta,
                    jac,
                    residual,
                    scenario.range_std_devs_km,
                    block_slices,
                    num_users=scenario.num_users,
                    residual_at_state=residual_at_state,
                    config=StepC7Config(),
                )
            except Exception as exc:  # noqa: BLE001
                stage_c_failure = f"{type(exc).__name__}: {exc}"

    def estimate_metrics(theta: np.ndarray | None) -> tuple[float | None, list[float], float | None, float | None]:
        if theta is None:
            return None, [], None, None
        pos, by_ue = _position_rmse_m(true_theta, theta, scenario.num_users, scenario.num_satellites)
        sync_km = _sync_error_km(true_theta, theta, scenario.num_users, scenario.num_satellites)
        return pos, by_ue, sync_km, _clock_km_to_ns(sync_km)

    stage_b_position_m, stage_b_position_by_ue_m, stage_b_sync_km, stage_b_sync_ns = estimate_metrics(stage_b_theta)
    stage_c_position_m, stage_c_position_by_ue_m, stage_c_sync_km, stage_c_sync_ns = estimate_metrics(stage_c.theta if stage_c is not None else None)
    failure_reasons = []
    if stage_a_failure:
        failure_reasons.append(f"stage_a:{stage_a_failure}")
    if single_ue:
        failure_reasons.append("single_ue_baseline_only")
    elif not graph_connected:
        failure_reasons.append("sidelink_graph_not_connected")
    if stage_b_failure:
        failure_reasons.append(f"stage_b:{stage_b_failure}")
    if stage_c_failure:
        failure_reasons.append(f"stage_c:{stage_c_failure}")
    return {
        "single_ue_baseline_only": single_ue,
        "jcls_applicable": jcls_applicable,
        "stage_a_success": stage_a_success,
        "stage_a_status": stage_a_status,
        "stage_a_position_rmse_m": stage_a_position_rmse_m,
        "stage_a_position_by_ue_m": stage_a_position_by_ue_m,
        "stage_b_success": bool(stage_b.success) if stage_b is not None else False,
        "stage_b_status": stage_b.diagnostics.get("status") if stage_b is not None else "not_applicable",
        "stage_b_position_rmse_m": stage_b_position_m,
        "stage_b_position_by_ue_m": stage_b_position_by_ue_m,
        "stage_b_sync_error_km": stage_b_sync_km,
        "stage_b_sync_error_ns": stage_b_sync_ns,
        "stage_c_used": bool(stage_c is not None),
        "stage_c_success": bool(stage_c.success) if stage_c is not None else False,
        "stage_c_status": stage_c.diagnostics.get("status") if stage_c is not None else "not_run",
        "stage_c_position_rmse_m": stage_c_position_m,
        "stage_c_position_by_ue_m": stage_c_position_by_ue_m,
        "stage_c_sync_error_km": stage_c_sync_km,
        "stage_c_sync_error_ns": stage_c_sync_ns,
        "convergence_boolean": bool(stage_b.success) if stage_b is not None else False,
        "failure_reason": ";".join(failure_reasons) if failure_reasons else "none",
        "initial_theta": stage_a_theta,
        "stage_a_estimate": stage_a_theta,
        "stage_b_estimate": stage_b_theta,
        "stage_c_estimate": stage_c.theta if stage_c is not None else None,
    }


def _execute_trial_row(
    *,
    paths: WavePaths,
    row_id: str,
    row_spec: dict[str, Any],
    options: WaveOptions,
) -> dict[str, Any]:
    """Execute or load one resumable trial row."""

    product = row_spec["product"]
    cache_dir = paths.output_root / product / "cache"
    cache_json = cache_dir / f"{row_id}.json"
    cache_npz = cache_dir / f"{row_id}.npz"
    if options.resume and not options.force_rerun and cache_json.exists():
        payload = _read_json(cache_json)
        payload["cache_status"] = "hit"
        _append_jsonl(paths.output_root / "ROW_STATUS.jsonl", {"row_id": row_id, "status": "cache_hit", "product": product})
        return payload

    started = time.monotonic()
    try:
        scenario, scenario_meta = _make_wave_scenario(
            num_users=row_spec["num_users"],
            num_satellites=row_spec["num_satellites"],
            seed=row_spec["seed"],
            clock_sigma_seconds=row_spec.get("clock_sigma_seconds", DEFAULT_CLOCK_SIGMA_SECONDS),
            sl_edge_probability=row_spec.get("sl_edge_probability", 1.0),
            full_mesh=row_spec.get("full_mesh", True),
            sigma_scale=row_spec.get("sigma_scale", 1.0),
        )
        true_theta = scenario.theta()
        fim_info, jac, fim = _fim_diagnostics(scenario)
        rng = np.random.default_rng(row_spec["seed"] + 70_001)
        z_full = _measurement_for_scenario(scenario, rng)
        empirical = _run_empirical_trial(
            scenario,
            z_full,
            rng,
            graph_connected=bool(scenario_meta["sl_graph"]["graph_connected"]),
            run_stage_c=bool(row_spec.get("run_stage_c", True)),
        )
        runtime = time.monotonic() - started
        if options.trial_timeout_seconds and runtime > options.trial_timeout_seconds:
            raise TimeoutError(f"trial exceeded timeout: {runtime:.3f}s > {options.trial_timeout_seconds:.3f}s")
        row = {
            "row_id": row_id,
            "product": product,
            "trial_id": row_spec.get("trial_id", 0),
            "random_seed": row_spec["seed"],
            "num_users": row_spec["num_users"],
            "num_satellites": row_spec["num_satellites"],
            "sl_edge_probability": row_spec.get("sl_edge_probability", 1.0),
            "graph_connected_components": scenario_meta["sl_graph"]["connected_component_count"],
            "graph_average_degree": scenario_meta["sl_graph"]["average_degree"],
            "clock_sigma_seconds": row_spec.get("clock_sigma_seconds", DEFAULT_CLOCK_SIGMA_SECONDS),
            "clock_sigma_ns": row_spec.get("clock_sigma_seconds", DEFAULT_CLOCK_SIGMA_SECONDS) * 1.0e9,
            "elapsed_time_s": row_spec.get("elapsed_time_s"),
            "runtime_seconds": runtime,
            "cache_status": "miss",
            "failure_recorded": False,
            **fim_info,
            **{key: value for key, value in empirical.items() if not key.endswith("_estimate") and key != "initial_theta"},
            **NONFINAL_FLAGS,
        }
        cache_dir.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            cache_npz,
            ue_positions_km=scenario.ue_positions_km,
            satellite_positions_km=scenario.satellite_positions_km,
            true_theta=true_theta,
            initial_theta=np.asarray(empirical["initial_theta"], dtype=float) if empirical["initial_theta"] is not None else np.asarray([], dtype=float),
            z=z_full,
            R_diag=np.square(scenario.range_std_devs_km),
            jacobian_at_true=jac,
            fim=fim,
            stage_a_estimate=np.asarray(empirical["stage_a_estimate"], dtype=float) if empirical["stage_a_estimate"] is not None else np.asarray([], dtype=float),
            stage_b_estimate=np.asarray(empirical["stage_b_estimate"], dtype=float) if empirical["stage_b_estimate"] is not None else np.asarray([], dtype=float),
            stage_c_estimate=np.asarray(empirical["stage_c_estimate"], dtype=float) if empirical["stage_c_estimate"] is not None else np.asarray([], dtype=float),
        )
        row.update(
            {
                "arrays_npz": _repo_rel(cache_npz),
                "satellite_geometry_id": f"seed{row_spec['seed']}_synthetic_visible_leo",
                "ue_positions_saved": True,
                "measurement_vector_saved": True,
                "fim_saved": True,
            }
        )
        _write_json(
            cache_json,
            {
                **row,
                "scenario_metadata": {
                    "sl_graph": scenario_meta["sl_graph"],
                    "sl_undirected_edges": scenario_meta["sl_undirected_edges"],
                    "clock_drift_reference": scenario_meta["clock_drift_reference"],
                    "noise": scenario_meta["noise"],
                    "geometry_model": scenario_meta["geometry"]["scenario_geometry_model"],
                },
            },
        )
        _append_jsonl(paths.output_root / "ROW_STATUS.jsonl", {"row_id": row_id, "status": "completed", "product": product, "runtime_seconds": runtime})
        return row
    except Exception as exc:  # noqa: BLE001 - runner must preserve failed rows.
        runtime = time.monotonic() - started
        row = {
            "row_id": row_id,
            "product": product,
            "trial_id": row_spec.get("trial_id", 0),
            "random_seed": row_spec.get("seed"),
            "num_users": row_spec.get("num_users"),
            "num_satellites": row_spec.get("num_satellites"),
            "sl_edge_probability": row_spec.get("sl_edge_probability", 1.0),
            "runtime_seconds": runtime,
            "cache_status": "failed",
            "failure_recorded": True,
            "failure_reason": f"{type(exc).__name__}: {exc}",
            "jcls_applicable": False,
            **NONFINAL_FLAGS,
        }
        _write_json(cache_json, row)
        _append_jsonl(paths.output_root / "ROW_STATUS.jsonl", {"row_id": row_id, "status": "failed", "product": product, "failure_reason": row["failure_reason"]})
        return row


def _grid_for_options(options: WaveOptions) -> tuple[list[int], list[int], int]:
    if options.full:
        trials = options.max_trials if options.max_trials is not None else 10
        return list(range(1, 11)), list(range(1, 16)), int(trials)
    trials = options.max_trials if options.max_trials is not None else 5
    return list(range(1, 6)), list(range(1, 9)), int(trials)


def _planned_rows(options: WaveOptions) -> list[dict[str, Any]]:
    users, satellites, trials = _grid_for_options(options)
    rows: list[dict[str, Any]] = []
    if options.only_product in {None, "observability", "satellite_substitution"}:
        for num_users in users:
            for num_satellites in satellites:
                for trial_id in range(trials):
                    rows.append(
                        {
                            "product": "observability",
                            "num_users": num_users,
                            "num_satellites": num_satellites,
                            "trial_id": trial_id,
                            "seed": 100_000 + 1000 * num_users + 31 * num_satellites + trial_id,
                            "clock_sigma_seconds": DEFAULT_CLOCK_SIGMA_SECONDS,
                            "sl_edge_probability": 1.0,
                            "full_mesh": True,
                            "run_stage_c": True,
                        }
                    )
    if options.only_product in {None, "clock_tolerance"}:
        clock_values = [1e-10, 1e-9, 1e-8, 1e-7, 1e-6, DEFAULT_CLOCK_SIGMA_SECONDS]
        for clock_index, clock_sigma in enumerate(clock_values):
            for trial_id in range(min(trials, 3)):
                rows.append(
                    {
                        "product": "clock_tolerance",
                        "num_users": 5 if not options.pilot else 3,
                        "num_satellites": 8,
                        "trial_id": trial_id,
                        "seed": 200_000 + 101 * clock_index + trial_id,
                        "clock_sigma_seconds": clock_sigma,
                        "sl_edge_probability": 1.0,
                        "full_mesh": True,
                        "run_stage_c": True,
                    }
                )
    if options.only_product in {None, "sparse_sidelink"}:
        p_values = [0.0, 0.5, 1.0] if not options.full else [round(0.1 * index, 1) for index in range(11)]
        cases = [(5, 4)] if options.pilot else [(5, 4), (7, 8), (10, 8)]
        for case_index, (num_users, num_satellites) in enumerate(cases):
            for p_index, edge_probability in enumerate(p_values):
                for trial_id in range(min(trials, 3)):
                    rows.append(
                        {
                            "product": "sparse_sidelink",
                            "num_users": num_users,
                            "num_satellites": num_satellites,
                            "trial_id": trial_id,
                            "seed": 300_000 + 1000 * case_index + 53 * p_index + trial_id,
                            "clock_sigma_seconds": DEFAULT_CLOCK_SIGMA_SECONDS,
                            "sl_edge_probability": edge_probability,
                            "full_mesh": False,
                            "run_stage_c": True,
                        }
                    )
    if options.only_product in {None, "time_to_accuracy"}:
        times = [0.0, 0.1, 0.2, 0.5, 1.0] if options.pilot else [round(0.1 * index, 1) for index in range(0, 51)]
        for time_index, elapsed_s in enumerate(times):
            if elapsed_s <= 0.0:
                sigma_scale = 10.0
            else:
                sigma_scale = math.sqrt(0.5 / elapsed_s)
            rows.append(
                {
                    "product": "time_to_accuracy",
                    "num_users": 5 if not options.pilot else 3,
                    "num_satellites": 8,
                    "trial_id": time_index,
                    "seed": 400_000 + time_index,
                    "clock_sigma_seconds": DEFAULT_CLOCK_SIGMA_SECONDS,
                    "sl_edge_probability": 1.0,
                    "full_mesh": True,
                    "sigma_scale": sigma_scale,
                    "elapsed_time_s": elapsed_s,
                    "run_stage_c": True,
                }
            )
    for index, row in enumerate(rows):
        row_id = (
            f"{row['product']}_nu{row['num_users']}_ns{row['num_satellites']}"
            f"_p{str(row.get('sl_edge_probability', 1.0)).replace('.', 'p')}"
            f"_c{row.get('clock_sigma_seconds', DEFAULT_CLOCK_SIGMA_SECONDS):.0e}"
            f"_t{row['trial_id']}"
        )
        if row["product"] == "time_to_accuracy":
            row_id += f"_time{str(row.get('elapsed_time_s', 0.0)).replace('.', 'p')}"
        row["row_id"] = row_id
        row["plan_index"] = index
    if options.only_row:
        rows = [row for row in rows if row["row_id"] == options.only_row]
    return rows


def _execute_rows(rows: list[dict[str, Any]], paths: WavePaths, options: WaveOptions) -> list[dict[str, Any]]:
    started = time.monotonic()
    outputs = []
    for spec in rows:
        if options.max_runtime_minutes is not None:
            elapsed_min = (time.monotonic() - started) / 60.0
            if elapsed_min >= options.max_runtime_minutes:
                _append_jsonl(
                    paths.output_root / "ROW_STATUS.jsonl",
                    {"row_id": spec["row_id"], "product": spec["product"], "status": "skipped_runtime_budget"},
                )
                continue
        row_started = time.monotonic()
        row = _execute_trial_row(paths=paths, row_id=spec["row_id"], row_spec=spec, options=options)
        if options.row_timeout_seconds and time.monotonic() - row_started > options.row_timeout_seconds:
            row["failure_recorded"] = True
            row["failure_reason"] = "row_timeout_exceeded_after_completion"
        outputs.append(row)
    return outputs


def _summarize_by_grid(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[int, int, str], list[dict[str, Any]]] = {}
    for row in rows:
        key = (int(row["num_users"]), int(row["num_satellites"]), str(row.get("product", "")))
        groups.setdefault(key, []).append(row)
    summaries = []
    for (num_users, num_satellites, product), group in sorted(groups.items()):
        summaries.append(
            {
                "product": product,
                "num_users": num_users,
                "num_satellites": num_satellites,
                "trial_count": len(group),
                "failure_count": sum(bool(row.get("failure_recorded")) for row in group),
                "single_ue_baseline_only": bool(num_users == 1),
                "jcls_applicable": bool(num_users >= 2),
                "fim_rank_mean": _nanmean(row.get("fim_rank") for row in group),
                "state_dimension": group[0].get("state_dimension"),
                "rank_deficiency_mean": _nanmean(row.get("rank_deficiency") for row in group),
                "condition_number_mean": _nanmean(row.get("condition_number") for row in group),
                "log10_condition_number_mean": _nanmean(row.get("log10_condition_number") for row in group),
                "crlb_position_m_mean": _nanmean(row.get("crlb_position_m") for row in group),
                "crlb_clock_ns_mean": _nanmean(row.get("crlb_clock_ns") for row in group),
                "stage_a_position_rmse_m_mean": _nanmean(row.get("stage_a_position_rmse_m") for row in group),
                "stage_b_position_rmse_m_mean": _nanmean(row.get("stage_b_position_rmse_m") for row in group),
                "stage_c_position_rmse_m_mean": _nanmean(row.get("stage_c_position_rmse_m") for row in group),
                "stage_b_sync_error_ns_mean": _nanmean(row.get("stage_b_sync_error_ns") for row in group),
                "stage_c_sync_error_ns_mean": _nanmean(row.get("stage_c_sync_error_ns") for row in group),
                "stage_b_convergence_probability": float(np.mean([bool(row.get("stage_b_success")) for row in group])),
                "stage_c_convergence_probability": float(np.mean([bool(row.get("stage_c_success")) for row in group])),
                "failure_reasons": sorted({str(row.get("failure_reason", "none")) for row in group if str(row.get("failure_reason", "none")) != "none"}),
            }
        )
    return summaries


def _matrix_from_summary(summaries: list[dict[str, Any]], metric: str) -> tuple[list[int], list[int], np.ndarray]:
    users = sorted({int(row["num_users"]) for row in summaries})
    sats = sorted({int(row["num_satellites"]) for row in summaries})
    matrix = np.full((len(users), len(sats)), np.nan)
    for row in summaries:
        value = row.get(metric)
        if value is not None:
            matrix[users.index(int(row["num_users"])), sats.index(int(row["num_satellites"]))] = float(value)
    return users, sats, matrix


def _plot_heatmap(summary: list[dict[str, Any]], metric: str, title: str, label: str, path: Path) -> list[str]:
    users, sats, matrix = _matrix_from_summary(summary, metric)
    fig, ax = plt.subplots(figsize=(8.0, 4.7))
    image = ax.imshow(matrix, aspect="auto", interpolation="nearest")
    ax.set_xticks(range(len(sats)), sats)
    ax.set_yticks(range(len(users)), users)
    ax.set_xlabel("Number of satellites (N_s)")
    ax.set_ylabel("Number of UEs (N_u)")
    ax.set_title(title)
    for i, _nu in enumerate(users):
        for j, _ns in enumerate(sats):
            value = matrix[i, j]
            text = "NA" if not math.isfinite(float(value)) else f"{value:.2g}"
            ax.text(j, i, text, ha="center", va="center", fontsize=6, color="white")
    fig.colorbar(image, ax=ax, label=label)
    fig.tight_layout()
    return _save_plot(fig, path)


def _write_observability_product(rows: list[dict[str, Any]], paths: WavePaths, options: WaveOptions) -> ProductResult:
    product_root = paths.output_root / "observability"
    selected = [row for row in rows if row.get("product") == "observability"]
    summary = _summarize_by_grid(selected)
    files = {
        "raw_csv": _write_csv(product_root / "raw.csv", selected),
        "summary_csv": _write_csv(product_root / "summary.csv", summary),
    }
    np.savez_compressed(
        product_root / "arrays.npz",
        rank=np.asarray([row.get("fim_rank", np.nan) for row in summary], dtype=float),
        rank_deficiency=np.asarray([row.get("rank_deficiency_mean", np.nan) for row in summary], dtype=float),
        crlb_position_m=np.asarray([row.get("crlb_position_m_mean", np.nan) or np.nan for row in summary], dtype=float),
        stage_b_rmse_m=np.asarray([row.get("stage_b_position_rmse_m_mean", np.nan) or np.nan for row in summary], dtype=float),
    )
    files["arrays_npz"] = _repo_rel(product_root / "arrays.npz")
    plot_paths = []
    if options.render_plots and summary:
        plot_paths.extend(_plot_heatmap(summary, "fim_rank_mean", "Wave observability rank heatmap", "FIM rank", product_root / "wave_observability_rank_heatmap.pdf"))
        plot_paths.extend(_plot_heatmap(summary, "log10_condition_number_mean", "Wave condition-number heatmap", "log10 cond(FIM)", product_root / "wave_condition_number_heatmap.pdf"))
        plot_paths.extend(_plot_heatmap(summary, "crlb_position_m_mean", "Wave CRLB position heatmap", "CRLB avg UE position (m)", product_root / "wave_crlb_position_heatmap.pdf"))
        plot_paths.extend(_plot_heatmap(summary, "stage_b_position_rmse_m_mean", "Wave empirical RMSE heatmap", "Stage B RMSE (m)", product_root / "wave_empirical_rmse_heatmap.pdf"))
    metadata = {
        "artifact_status": "non_final_wave_observability",
        **NONFINAL_FLAGS,
        "grid_mode": "full" if options.full else "pilot",
        "row_count": len(selected),
        "summary_count": len(summary),
        "required_figures": [
            "wave_observability_rank_heatmap",
            "wave_condition_number_heatmap",
            "wave_crlb_position_heatmap",
            "wave_empirical_rmse_heatmap",
        ],
        "plots": plot_paths,
        "stage_terms": {
            "stage_a": "without cooperation / DL-only / conventional TOA baseline",
            "stage_b": "cooperative JCLS LM-only",
            "stage_c": "refined JCLS / C7 residual-covariance sync safeguard",
        },
    }
    files["metadata_json"] = _write_json(product_root / "metadata.json", metadata)
    notes = _observability_notes(summary, metadata, files)
    files["notes_md"] = _write_markdown(product_root / "notes.md", notes)
    report_payload = _report_payload("phase_transition", selected, summary, files, metadata)
    _write_report_pair(paths, "WAVE_RESULTS_PHASE_TRANSITION_REPORT", report_payload, _phase_report_md(report_payload))
    return ProductResult("observability", "generated" if selected else "not_run", len(selected), metadata, files, [row["row_id"] for row in selected if row.get("failure_recorded")])


def _write_satellite_substitution_product(rows: list[dict[str, Any]], paths: WavePaths, options: WaveOptions) -> ProductResult:
    product_root = paths.output_root / "satellite_substitution"
    observation_summary = _summarize_by_grid([row for row in rows if row.get("product") == "observability"])
    iso_rows = []
    for threshold in THRESHOLDS_M:
        for num_users in sorted({int(row["num_users"]) for row in observation_summary}):
            subset = [row for row in observation_summary if int(row["num_users"]) == num_users]
            stage_a_min = _min_satellites_for_threshold(subset, "stage_a_position_rmse_m_mean", threshold)
            stage_b_min = _min_satellites_for_threshold(subset, "stage_b_position_rmse_m_mean", threshold)
            stage_c_min = _min_satellites_for_threshold(subset, "stage_c_position_rmse_m_mean", threshold)
            iso_rows.append(
                {
                    "threshold_m": threshold,
                    "num_users": num_users,
                    "stage_a_min_satellites": stage_a_min,
                    "stage_b_min_satellites": stage_b_min,
                    "stage_c_min_satellites": stage_c_min,
                    "stage_b_satellites_saved_vs_stage_a": _saved_satellites(stage_a_min, stage_b_min),
                    "stage_c_satellites_saved_vs_stage_a": _saved_satellites(stage_a_min, stage_c_min),
                    "single_ue_baseline_only": num_users == 1,
                }
            )
    files = {
        "raw_csv": _write_csv(product_root / "raw.csv", observation_summary),
        "summary_csv": _write_csv(product_root / "summary.csv", iso_rows),
        "wave_iso_accuracy_table_csv": _write_csv(product_root / "wave_iso_accuracy_table.csv", iso_rows),
    }
    np.savez_compressed(
        product_root / "arrays.npz",
        thresholds_m=np.asarray(THRESHOLDS_M, dtype=float),
        stage_a=np.asarray([row["stage_a_min_satellites"] or np.nan for row in iso_rows], dtype=float),
        stage_b=np.asarray([row["stage_b_min_satellites"] or np.nan for row in iso_rows], dtype=float),
        stage_c=np.asarray([row["stage_c_min_satellites"] or np.nan for row in iso_rows], dtype=float),
    )
    files["arrays_npz"] = _repo_rel(product_root / "arrays.npz")
    plot_paths = []
    if options.render_plots and iso_rows:
        plot_paths.extend(_plot_satellite_substitution(iso_rows, product_root / "wave_satellite_substitution_curve.pdf"))
    metadata = {
        "artifact_status": "non_final_wave_satellite_substitution",
        **NONFINAL_FLAGS,
        "thresholds_m": list(THRESHOLDS_M),
        "row_count": len(iso_rows),
        "plots": plot_paths,
        "claim_tested_not_assumed": "JCLS with cooperating UEs can match or exceed DL-only localization with more satellites.",
    }
    files["metadata_json"] = _write_json(product_root / "metadata.json", metadata)
    files["notes_md"] = _write_markdown(product_root / "notes.md", _satellite_notes(iso_rows, metadata, files))
    report_payload = _report_payload("satellite_substitution", observation_summary, iso_rows, files, metadata)
    _write_report_pair(paths, "WAVE_RESULTS_SATELLITE_SUBSTITUTION_REPORT", report_payload, _sat_report_md(report_payload))
    return ProductResult("satellite_substitution", "generated" if iso_rows else "not_run", len(iso_rows), metadata, files)


def _min_satellites_for_threshold(rows: list[dict[str, Any]], metric: str, threshold: float) -> int | None:
    candidates = []
    for row in rows:
        value = row.get(metric)
        if value is not None and math.isfinite(float(value)) and float(value) <= threshold:
            candidates.append(int(row["num_satellites"]))
    return min(candidates) if candidates else None


def _saved_satellites(stage_a: int | None, stage_other: int | None) -> int | None:
    if stage_a is None or stage_other is None:
        return None
    return int(stage_a - stage_other)


def _plot_satellite_substitution(rows: list[dict[str, Any]], path: Path) -> list[str]:
    fig, axes = plt.subplots(2, 2, figsize=(9.0, 6.5), sharex=True, sharey=True)
    for ax, threshold in zip(axes.reshape(-1), THRESHOLDS_M, strict=True):
        subset = sorted([row for row in rows if float(row["threshold_m"]) == threshold], key=lambda row: row["num_users"])
        users = [row["num_users"] for row in subset]
        for key, label, marker in (
            ("stage_a_min_satellites", "Stage A", "o"),
            ("stage_b_min_satellites", "Stage B", "s"),
            ("stage_c_min_satellites", "Stage C", "^"),
        ):
            y = [np.nan if row[key] is None else row[key] for row in subset]
            ax.plot(users, y, marker=marker, label=label)
        ax.set_title(f"<= {threshold:g} m")
        ax.grid(True, alpha=0.3)
    for ax in axes[:, 0]:
        ax.set_ylabel("Minimum N_s")
    for ax in axes[-1, :]:
        ax.set_xlabel("N_u")
    axes[0, 0].legend(fontsize=8)
    fig.suptitle("Wave satellite substitution curve")
    fig.tight_layout()
    return _save_plot(fig, path)


def _write_secondary_product(
    *,
    product: str,
    rows: list[dict[str, Any]],
    paths: WavePaths,
    options: WaveOptions,
) -> ProductResult:
    product_root = paths.output_root / product
    selected = [row for row in rows if row.get("product") == product]
    summary = _summarize_secondary(product, selected)
    files = {
        "raw_csv": _write_csv(product_root / "raw.csv", selected),
        "summary_csv": _write_csv(product_root / "summary.csv", summary),
    }
    np.savez_compressed(
        product_root / "arrays.npz",
        stage_a=np.asarray([row.get("stage_a_position_rmse_m", np.nan) or np.nan for row in selected], dtype=float),
        stage_b=np.asarray([row.get("stage_b_position_rmse_m", np.nan) or np.nan for row in selected], dtype=float),
        stage_c=np.asarray([row.get("stage_c_position_rmse_m", np.nan) or np.nan for row in selected], dtype=float),
    )
    files["arrays_npz"] = _repo_rel(product_root / "arrays.npz")
    plot_paths: list[str] = []
    if options.render_plots and selected:
        if product == "clock_tolerance":
            plot_paths.extend(_plot_metric_lines(summary, "clock_sigma_ns", product_root / "wave_clock_tolerance_position_plot.pdf", "Clock sigma (ns)", "Position RMSE (m)", logx=True))
            plot_paths.extend(_plot_metric_lines(summary, "clock_sigma_ns", product_root / "wave_clock_tolerance_sync_plot.pdf", "Clock sigma (ns)", "Sync error (ns)", logx=True, sync=True))
        elif product == "sparse_sidelink":
            plot_paths.extend(_plot_metric_lines(summary, "sl_edge_probability", product_root / "wave_sparse_sl_rmse_vs_density.pdf", "SL edge probability", "Position RMSE (m)"))
            plot_paths.extend(_plot_convergence(summary, product_root / "wave_sparse_sl_convergence_vs_density.pdf"))
            plot_paths.extend(_plot_rank_condition(summary, product_root / "wave_sparse_sl_rank_condition_vs_density.pdf"))
        elif product == "time_to_accuracy":
            plot_paths.extend(_plot_metric_lines(summary, "elapsed_time_s", product_root / "wave_time_to_accuracy_position.pdf", "Time (s)", "Position RMSE (m)"))
            plot_paths.extend(_plot_metric_lines(summary, "elapsed_time_s", product_root / "wave_time_to_accuracy_sync.pdf", "Time (s)", "Sync error (ns)", sync=True))
    metadata = {
        "artifact_status": f"non_final_wave_{product}",
        **NONFINAL_FLAGS,
        "row_count": len(selected),
        "summary_count": len(summary),
        "plots": plot_paths,
        "pilot_scope": bool(options.pilot and not options.full),
    }
    if product == "clock_tolerance":
        thresholds = _threshold_table(summary, x_key="clock_sigma_seconds", direction="max")
        files["wave_clock_tolerance_threshold_table_csv"] = _write_csv(product_root / "wave_clock_tolerance_threshold_table.csv", thresholds)
        metadata["threshold_rows"] = thresholds
    elif product == "time_to_accuracy":
        thresholds = _threshold_table(summary, x_key="elapsed_time_s", direction="min")
        files["wave_time_threshold_table_csv"] = _write_csv(product_root / "wave_time_threshold_table.csv", thresholds)
        metadata["threshold_rows"] = thresholds
    files["metadata_json"] = _write_json(product_root / "metadata.json", metadata)
    files["notes_md"] = _write_markdown(product_root / "notes.md", _secondary_notes(product, summary, metadata, files))
    report_names = {
        "clock_tolerance": "WAVE_RESULTS_CLOCK_TOLERANCE_REPORT",
        "sparse_sidelink": "WAVE_RESULTS_SPARSE_SL_REPORT",
        "time_to_accuracy": "WAVE_RESULTS_TIME_TO_ACCURACY_REPORT",
    }
    report_payload = _report_payload(product, selected, summary, files, metadata)
    _write_report_pair(paths, report_names[product], report_payload, _generic_report_md(product, report_payload))
    return ProductResult(product, "generated" if selected else "not_run", len(selected), metadata, files, [row["row_id"] for row in selected if row.get("failure_recorded")])


def _summarize_secondary(product: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for row in rows:
        if product == "clock_tolerance":
            key = (float(row.get("clock_sigma_seconds", 0.0)),)
        elif product == "sparse_sidelink":
            key = (int(row["num_users"]), int(row["num_satellites"]), float(row.get("sl_edge_probability", 0.0)))
        elif product == "time_to_accuracy":
            key = (float(row.get("elapsed_time_s", row.get("trial_id", 0))),)
        else:
            key = (row.get("row_id"),)
        groups.setdefault(key, []).append(row)
    output = []
    for key, group in sorted(groups.items()):
        base = {
            "product": product,
            "trial_count": len(group),
            "num_users": group[0].get("num_users"),
            "num_satellites": group[0].get("num_satellites"),
            "stage_a_position_rmse_m_mean": _nanmean(row.get("stage_a_position_rmse_m") for row in group),
            "stage_b_position_rmse_m_mean": _nanmean(row.get("stage_b_position_rmse_m") for row in group),
            "stage_c_position_rmse_m_mean": _nanmean(row.get("stage_c_position_rmse_m") for row in group),
            "stage_b_sync_error_ns_mean": _nanmean(row.get("stage_b_sync_error_ns") for row in group),
            "stage_c_sync_error_ns_mean": _nanmean(row.get("stage_c_sync_error_ns") for row in group),
            "stage_b_convergence_probability": float(np.mean([bool(row.get("stage_b_success")) for row in group])),
            "stage_c_convergence_probability": float(np.mean([bool(row.get("stage_c_success")) for row in group])),
            "fim_rank_mean": _nanmean(row.get("fim_rank") for row in group),
            "condition_number_mean": _nanmean(row.get("condition_number") for row in group),
            "log10_condition_number_mean": _nanmean(row.get("log10_condition_number") for row in group),
            "graph_average_degree_mean": _nanmean(row.get("graph_average_degree") for row in group),
            "graph_connected_probability": float(np.mean([int(row.get("graph_connected_components", 99)) == 1 for row in group])),
        }
        if product == "clock_tolerance":
            base["clock_sigma_seconds"] = key[0]
            base["clock_sigma_ns"] = key[0] * 1.0e9
        elif product == "sparse_sidelink":
            base["sl_edge_probability"] = key[2]
        elif product == "time_to_accuracy":
            base["elapsed_time_s"] = key[0]
        output.append(base)
    return output


def _plot_metric_lines(
    summary: list[dict[str, Any]],
    x_key: str,
    path: Path,
    xlabel: str,
    ylabel: str,
    *,
    logx: bool = False,
    sync: bool = False,
) -> list[str]:
    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    rows = sorted(summary, key=lambda row: float(row.get(x_key, 0.0)))
    x = [float(row.get(x_key, 0.0)) for row in rows]
    if sync:
        series = [
            ("stage_b_sync_error_ns_mean", "Stage B"),
            ("stage_c_sync_error_ns_mean", "Stage C"),
        ]
    else:
        series = [
            ("stage_a_position_rmse_m_mean", "Stage A"),
            ("stage_b_position_rmse_m_mean", "Stage B"),
            ("stage_c_position_rmse_m_mean", "Stage C"),
        ]
    for metric, label in series:
        y = [np.nan if row.get(metric) is None else float(row[metric]) for row in rows]
        ax.plot(x, y, marker="o", label=label)
    if logx:
        ax.set_xscale("log")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    return _save_plot(fig, path)


def _plot_convergence(summary: list[dict[str, Any]], path: Path) -> list[str]:
    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    rows = sorted(summary, key=lambda row: (int(row["num_users"]), float(row["sl_edge_probability"])))
    for case in sorted({(row["num_users"], row["num_satellites"]) for row in rows}):
        subset = [row for row in rows if (row["num_users"], row["num_satellites"]) == case]
        x = [float(row["sl_edge_probability"]) for row in subset]
        ax.plot(x, [float(row["stage_b_convergence_probability"]) for row in subset], marker="o", label=f"Stage B Nu={case[0]},Ns={case[1]}")
    ax.set_xlabel("SL edge probability")
    ax.set_ylabel("Convergence probability")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=7)
    fig.tight_layout()
    return _save_plot(fig, path)


def _plot_rank_condition(summary: list[dict[str, Any]], path: Path) -> list[str]:
    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    rows = sorted(summary, key=lambda row: (int(row["num_users"]), float(row["sl_edge_probability"])))
    for case in sorted({(row["num_users"], row["num_satellites"]) for row in rows}):
        subset = [row for row in rows if (row["num_users"], row["num_satellites"]) == case]
        x = [float(row["sl_edge_probability"]) for row in subset]
        ax.plot(x, [np.nan if row["log10_condition_number_mean"] is None else float(row["log10_condition_number_mean"]) for row in subset], marker="o", label=f"Nu={case[0]},Ns={case[1]}")
    ax.set_xlabel("SL edge probability")
    ax.set_ylabel("log10 condition number")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=7)
    fig.tight_layout()
    return _save_plot(fig, path)


def _threshold_table(summary: list[dict[str, Any]], *, x_key: str, direction: str) -> list[dict[str, Any]]:
    output = []
    for threshold in THRESHOLDS_M:
        for metric, method in (
            ("stage_a_position_rmse_m_mean", "Stage A"),
            ("stage_b_position_rmse_m_mean", "Stage B"),
            ("stage_c_position_rmse_m_mean", "Stage C"),
        ):
            candidates = [row for row in summary if row.get(metric) is not None and float(row[metric]) <= threshold]
            if direction == "max":
                value = max((float(row[x_key]) for row in candidates), default=None)
            else:
                value = min((float(row[x_key]) for row in candidates), default=None)
            output.append({"threshold_m": threshold, "method": method, x_key: value})
    return output


def _write_literature_product(paths: WavePaths) -> ProductResult:
    product_root = paths.output_root / "literature_comparison"
    rows = _literature_rows()
    files = {
        "raw_csv": _write_csv(product_root / "raw.csv", rows),
        "summary_csv": _write_csv(product_root / "summary.csv", rows),
    }
    np.savez_compressed(product_root / "arrays.npz", row_index=np.arange(len(rows), dtype=int))
    files["arrays_npz"] = _repo_rel(product_root / "arrays.npz")
    metadata = {
        "artifact_status": "non_final_wave_literature_comparison",
        **NONFINAL_FLAGS,
        "row_count": len(rows),
        "web_search_used_by_orchestrator": True,
        "comparability_caveat": "Rows are qualitative and assumption-sensitive; do not claim JCLS beats Starlink PNT from this table.",
    }
    files["metadata_json"] = _write_json(product_root / "metadata.json", metadata)
    files["notes_md"] = _write_markdown(product_root / "notes.md", _literature_md(rows))
    files["table_md"] = _write_markdown(paths.report_root / "WAVE_LITERATURE_COMPARISON_TABLE.md", _literature_md(rows))
    files["table_json"] = _write_json(paths.report_root / "WAVE_LITERATURE_COMPARISON_TABLE.json", {"rows": rows, **metadata})
    return ProductResult("literature_comparison", "generated", len(rows), metadata, files)


def _literature_rows() -> list[dict[str, Any]]:
    return [
        {
            "method": "JCLS wave diagnostic",
            "signals_used": "NTN downlink TOA plus UE sidelink TOA",
            "gnss_assistance": "No GNSS assumed in estimator state",
            "cooperation": "UE cooperation via sidelinks",
            "clock_correction_assumed": "Joint UE and non-reference satellite clock-offset estimation relative to reference satellite",
            "time_to_solution": "Diagnostic; snapshot defaults to 500 ms, time sweep is surrogate only",
            "position_error": "Computed in this branch; non-final",
            "scenario_realism": "MIT/Stata UE disk, synthetic Starlink-like LEO geometry, link-budget TOA sigma",
            "citation": "This diagnostic branch",
            "url": "",
            "comparability_caveat": "Not manuscript-ready; cannot be compared directly to field trials.",
        },
        {
            "method": "Starlink opportunistic carrier-phase PNT",
            "signals_used": "Ku-band Starlink signals of opportunity, carrier phase/Doppler style tracking",
            "gnss_assistance": "Often requires known ephemeris/receiver setup assumptions; GNSS-denied motivation",
            "cooperation": "No UE cooperation",
            "clock_correction_assumed": "Receiver/satellite signal structure handled by opportunistic receiver processing",
            "time_to_solution": "Field-trial batch/tracking dependent",
            "position_error": "Reported examples include meter-level to tens-of-meters field results",
            "scenario_realism": "Real Starlink signals; not 3GPP NTN PRS",
            "citation": "Kassas et al., first Starlink carrier-phase tracking and positioning results",
            "url": "https://ece.osu.edu/sites/default/files/2022-09/The_first_carrier_phase_tracking_and_positioning_results_with_Starlink_LEO_satellite_Signals.pdf",
            "comparability_caveat": "Different signal, receiver, and batching assumptions; do not frame as head-to-head.",
        },
        {
            "method": "Differential Doppler LEO opportunistic navigation",
            "signals_used": "Doppler or differential Doppler from LEO signals of opportunity",
            "gnss_assistance": "Usually reference receiver, ephemeris, or differential assumptions",
            "cooperation": "Reference-receiver style differential processing, not UE cooperative JCLS",
            "clock_correction_assumed": "Differencing mitigates common errors under baseline assumptions",
            "time_to_solution": "Pass/batch dependent",
            "position_error": "Baseline and propagation-error sensitive",
            "scenario_realism": "LEO SOP navigation literature",
            "citation": "Differential Doppler LEO opportunistic navigation literature",
            "url": "https://www.researchgate.net/publication/366981365_Analysis_of_Baseline_Impact_on_Differential_Doppler_Positioning_and_Performance_Improvement_Method_for_LEO_Opportunistic_Navigation",
            "comparability_caveat": "Doppler observable and reference-baseline assumptions differ from JCLS TOA+sidelink.",
        },
        {
            "method": "TOA NTN PRS without cooperation",
            "signals_used": "5G/NR positioning reference signals and timing measurements",
            "gnss_assistance": "May be UE-assisted/network-assisted depending architecture",
            "cooperation": "No UE sidelink cooperation",
            "clock_correction_assumed": "Network timing/synchronization assumptions vary",
            "time_to_solution": "3GPP procedure/configuration dependent",
            "position_error": "Not directly comparable; depends on PRS bandwidth, geometry, and timing",
            "scenario_realism": "3GPP NTN and Rel-18 positioning context",
            "citation": "3GPP NTN overview and Rel-18 positioning discussions",
            "url": "https://www.3gpp.org/technologies/ntn-overview",
            "comparability_caveat": "Standardization context, not an identical estimator result.",
        },
        {
            "method": "GNSS-aided NTN / LEO-PNT",
            "signals_used": "GNSS plus LEO/NTN augmentation or complementary signals",
            "gnss_assistance": "Yes",
            "cooperation": "Usually no UE-to-UE cooperation",
            "clock_correction_assumed": "GNSS or augmentation may supply timing/ephemeris support",
            "time_to_solution": "Architecture dependent",
            "position_error": "Surveyed; varies by design",
            "scenario_realism": "LEO-PNT survey category",
            "citation": "Survey on LEO-PNT systems",
            "url": "https://www.jpnt.org/a-survey-on-leo-pnt-systems/",
            "comparability_caveat": "GNSS assistance changes the ambiguity structure.",
        },
        {
            "method": "Terrestrial-anchor-aided NTN",
            "signals_used": "NTN plus terrestrial anchors or integrated terrestrial/non-terrestrial measurements",
            "gnss_assistance": "May or may not use GNSS",
            "cooperation": "Anchor assistance rather than UE cooperation",
            "clock_correction_assumed": "Anchor/network timing assumptions vary",
            "time_to_solution": "Architecture dependent",
            "position_error": "Scenario dependent",
            "scenario_realism": "Integrated TN/NTN positioning literature",
            "citation": "5G/6G positioning surveys and integrated NTN positioning work",
            "url": "https://www.mdpi.com/1424-8220/22/13/4757",
            "comparability_caveat": "Anchors provide external information that JCLS is trying not to require.",
        },
    ]


def _write_task_matrix(paths: WavePaths, subagent_status: dict[str, Any] | None = None) -> dict[str, Any]:
    lanes = [
        ("Agent A", "Provenance and Notebook Figure Audit", "read_only_subagent_or_orchestrator", "outputs/reports/WAVE_RESULTS_PROVENANCE_AUDIT.*"),
        ("Agent B", "Observability / CRLB Product", "orchestrator_completed", "outputs/wave_results/observability/"),
        ("Agent C", "Empirical RMSE Product", "orchestrator_completed", "raw trial rows and empirical heatmap"),
        ("Agent D", "Satellite Substitution Product", "orchestrator_completed", "outputs/wave_results/satellite_substitution/"),
        ("Agent E", "Clock Tolerance Product", "orchestrator_pilot_completed", "outputs/wave_results/clock_tolerance/"),
        ("Agent F", "Sparse Sidelink Product", "orchestrator_pilot_completed", "outputs/wave_results/sparse_sidelink/"),
        ("Agent G", "Time-to-Accuracy Product", "orchestrator_surrogate_pilot_completed", "outputs/wave_results/time_to_accuracy/"),
        ("Agent H", "Literature Comparison Product", "orchestrator_web_and_local_completed", "outputs/reports/WAVE_LITERATURE_COMPARISON_TABLE.*"),
        ("Agent I", "Crash/Cache/Resume Product", "orchestrator_completed", "RUN_STATUS, ROW_STATUS, cache manifests"),
        ("Agent J", "Scientific Red Team", "read_only_subagent_or_orchestrator", "safe/unsafe claims in reports"),
    ]
    payload = {
        "artifact_status": "non_final_wave_results_task_matrix",
        **NONFINAL_FLAGS,
        "subagent_status": subagent_status or {"mode": "orchestrator_with_read_only_sidecars", "edit_owner": "orchestrator"},
        "file_ownership": [
            {
                "workstream": "wave-results implementation",
                "branch_worktree": "codex/jcls-wave-results-exploration @ C:/codex-wt/jcls-wave-results-exploration",
                "subagent_role": "orchestrator",
                "files_allowed_to_edit": [
                    "scripts/run_wave_results_exploration.py",
                    "tests/test_wave_results_exploration.py",
                    "outputs/wave_results/**",
                    "outputs/reports/WAVE_*",
                    "PROJECT_STATUS.md",
                    "docs/tasks/NEXT.md",
                ],
                "read_only_files": [
                    "JCLS_Simulation.ipynb",
                    "Work-In-Progress/**",
                    "All-Version-Archive/**",
                    "existing manuscript result files",
                ],
                "stop_conditions": ["need for notebook edits", "need for manuscript edits", "expensive unbounded run"],
            }
        ],
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
    _write_json(paths.report_root / "WAVE_RESULTS_TASK_MATRIX.json", payload)
    lines = [
        "# Wave Results Task Matrix",
        "",
        "| Agent | Lane | Status | Expected output | Blocker | Fallback owner |",
        "|---|---|---|---|---|---|",
    ]
    for lane in payload["lanes"]:
        lines.append(
            f"| {lane['agent']} | {lane['lane']} | {lane['status']} | "
            f"{lane['expected_output_files']} | none | {lane['fallback_owner']} |"
        )
    lines.extend(
        [
            "",
            "## File Ownership",
            "",
            "| Workstream | Branch/worktree | Subagent role | Files allowed to edit | Read-only files | Stop conditions |",
            "|---|---|---|---|---|---|",
        ]
    )
    for owner in payload["file_ownership"]:
        lines.append(
            f"| {owner['workstream']} | {owner['branch_worktree']} | {owner['subagent_role']} | "
            f"{'; '.join(owner['files_allowed_to_edit'])} | {('; '.join(owner['read_only_files']))} | "
            f"{'; '.join(owner['stop_conditions'])} |"
        )
    _write_markdown(paths.report_root / "WAVE_RESULTS_TASK_MATRIX.md", "\n".join(lines) + "\n")
    return payload


def _write_provenance_audit(paths: WavePaths) -> dict[str, Any]:
    notebook = SAT_SIM_ROOT / "JCLS_Simulation.ipynb"
    exported = SAT_SIM_ROOT / "jcls_simulation.py"
    text = notebook.read_text(encoding="utf-8", errors="replace") if notebook.exists() else ""
    findings = {
        "artifact_status": "non_final_wave_results_provenance_audit",
        **NONFINAL_FLAGS,
        "notebook_present": notebook.exists(),
        "exported_script_present": exported.exists(),
        "legacy_network_size_grid": {
            "num_satellites_range": "range(3, 15+1) found in notebook text" if "range(3, 15+1)" in text else "not confirmed",
            "num_users_range": "[1, 3, 5, 7] found in notebook text" if "[1, 3, 5, 7]" in text else "not confirmed",
            "num_iterations": "15 found near generate_data_for_heatmap" if "num_iterations=15" in text else "not confirmed",
        },
        "legacy_clock_sweep": {
            "pos_vary_clock_pdf": "pos_vary_clock.pdf" in text,
            "sync_vary_clock_pdf": "sync_vary_clock.pdf" in text,
        },
        "legacy_crlb_figures": {
            "pos_crlb": "pos_crlb_0dB_0dB" in text,
            "sync_crlb": "sync_crlb_0dB_0dB" in text,
        },
        "legacy_risks": [
            "Notebook contains TODO comments for clock drift modeling.",
            "Notebook contains legacy all-clock and truth-gated behavior documented by existing project reports.",
            "This wave runner does not execute or edit the notebook.",
        ],
        "manuscript_settings_used_as_start": {
            "ue_area": "UEs around MIT Stata center via package candidate geometry helper",
            "leo_model": "synthetic Starlink-like visible LEO satellites",
            "minimum_elevation_deg": 30.0,
            "snapshot_time_s": 0.5,
            "clock_reference": "0.5 ppm over 15 s = 7.5 us ~= 2.25 km",
            "dl": "2.2 GHz, 20 MHz, 55 dBm, 20 dB Tx gain",
            "sl": "5.9 GHz, 40 MHz, 20 dBm, 3 dB Tx gain",
        },
    }
    _write_json(paths.report_root / "WAVE_RESULTS_PROVENANCE_AUDIT.json", findings)
    lines = [
        "# Wave Results Provenance Audit",
        "",
        "- Artifact status: non-final diagnostic audit.",
        f"- Notebook present: `{findings['notebook_present']}`.",
        f"- Exported `jcls_simulation.py` present: `{findings['exported_script_present']}`.",
        "- Notebook execution: `false`.",
        "- Manuscript/source edits: `false`.",
        "",
        "## Original Figure Logic Observed",
        f"- Network-size grid: `{findings['legacy_network_size_grid']}`.",
        f"- Clock-sweep PDFs referenced: `{findings['legacy_clock_sweep']}`.",
        f"- CRLB figures referenced: `{findings['legacy_crlb_figures']}`.",
        "",
        "## Starting Settings For This Branch",
        *[f"- `{key}`: {value}" for key, value in findings["manuscript_settings_used_as_start"].items()],
        "",
        "## Risks",
        *[f"- {item}" for item in findings["legacy_risks"]],
    ]
    _write_markdown(paths.report_root / "WAVE_RESULTS_PROVENANCE_AUDIT.md", "\n".join(lines) + "\n")
    return findings


def _write_manifest(paths: WavePaths, products: list[ProductResult], started: float, options: WaveOptions) -> None:
    files = sorted(_repo_rel(path) for path in paths.output_root.rglob("*") if path.is_file())
    payload = {
        "artifact_status": "non_final_wave_results_cache_manifest",
        **NONFINAL_FLAGS,
        "cache_root": _repo_rel(paths.output_root),
        "runtime_seconds": time.monotonic() - started,
        "options": {key: str(value) if isinstance(value, Path) else value for key, value in asdict(options).items()},
        "products": [asdict(product) for product in products],
        "file_count": len(files),
        "files": files,
    }
    _write_json(paths.output_root / "CACHE_MANIFEST.json", payload)
    lines = [
        "# Wave Results Cache Manifest",
        "",
        "- Artifact status: non-final diagnostic cache.",
        f"- Cache root: `{_repo_rel(paths.output_root)}`.",
        f"- Runtime seconds: `{payload['runtime_seconds']:.3f}`.",
        "",
        "## Products",
        "| Product | Status | Rows |",
        "|---|---|---:|",
    ]
    for product in products:
        lines.append(f"| `{product.name}` | `{product.status}` | {product.row_count} |")
    lines.extend(["", "## Files", *[f"- `{item}`" for item in files]])
    _write_markdown(paths.output_root / "CACHE_MANIFEST.md", "\n".join(lines) + "\n")


def _write_wave_gallery(paths: WavePaths, products: list[ProductResult]) -> dict[str, Any]:
    """Write a product-local gallery for wave diagnostic plots."""

    entries = []
    for product in products:
        plots = product.summary.get("plots", []) if isinstance(product.summary, dict) else []
        for plot_path in plots:
            if str(plot_path).endswith(".pdf"):
                entries.append(
                    {
                        "product": product.name,
                        "source_pdf_path": plot_path,
                        "preview_png_path": str(plot_path).removesuffix(".pdf") + ".png",
                        "status": "non_final_wave_diagnostic",
                        "manuscript_ready": False,
                    }
                )
    payload = {
        "artifact_status": "non_final_wave_plot_gallery",
        **NONFINAL_FLAGS,
        "entry_count": len(entries),
        "entries": entries,
    }
    _write_json(paths.output_root / "WAVE_PLOT_GALLERY.json", payload)
    lines = [
        "# Wave Plot Gallery",
        "",
        "- Status: non-final diagnostic gallery.",
        "- Manuscript ready: `false`.",
        "",
    ]
    if entries:
        for entry in entries:
            lines.append(f"- `{entry['product']}`: [{entry['source_pdf_path']}]({entry['source_pdf_path']})")
    else:
        lines.append("- No plot entries were generated for this run.")
    _write_markdown(paths.output_root / "WAVE_PLOT_GALLERY.md", "\n".join(lines) + "\n")
    return payload


def _write_run_status(paths: WavePaths, status: str, payload: dict[str, Any]) -> None:
    _write_json(paths.output_root / "RUN_STATUS.json", {"status": status, **payload})


def _write_markdown(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return _repo_rel(path)


def _report_payload(name: str, raw: list[dict[str, Any]], summary: list[dict[str, Any]], files: dict[str, str], metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact_status": f"non_final_wave_{name}_report",
        **NONFINAL_FLAGS,
        "raw_row_count": len(raw),
        "summary_row_count": len(summary),
        "files": files,
        "metadata": metadata,
        "what_was_generated": list(files.values()),
        "what_failed": sorted({str(row.get("failure_reason")) for row in raw if row.get("failure_recorded") and row.get("failure_reason")}),
        "what_is_not_comparable": [
            "Pilot and diagnostic outputs are not manuscript-ready.",
            "Synthetic LEO geometry is not an SGP4/TLE replay.",
            "Stage C is package C7 residual-covariance sync safeguard, not a final manuscript-approved dynamic estimator.",
        ],
        "safe_claims": [
            "The outputs test observability, rank, and estimator behavior under explicit non-final settings.",
            "Single-UE rows are marked baseline-only, not cooperative JCLS.",
        ],
        "unsafe_claims": [
            "These outputs are final manuscript figures.",
            "JCLS beats Starlink PNT or any field-trial method head-to-head.",
            "Clock drift is estimated by the static offset state.",
        ],
        "recommended_next_action": "Review pilot evidence, then expand only the promising products with higher Monte Carlo counts.",
    }


def _write_report_pair(paths: WavePaths, stem: str, payload: dict[str, Any], md_text: str) -> None:
    _write_json(paths.report_root / f"{stem}.json", payload)
    _write_markdown(paths.report_root / f"{stem}.md", md_text)


def _phase_report_md(payload: dict[str, Any]) -> str:
    return _generic_report_md("phase_transition", payload)


def _sat_report_md(payload: dict[str, Any]) -> str:
    return _generic_report_md("satellite_substitution", payload)


def _generic_report_md(title: str, payload: dict[str, Any]) -> str:
    lines = [
        f"# {title.replace('_', ' ').title()} Report",
        "",
        "- Artifact status: non-final diagnostic.",
        "- Manuscript ready: `false`.",
        f"- Raw rows: `{payload['raw_row_count']}`.",
        f"- Summary rows: `{payload['summary_row_count']}`.",
        "",
        "## What Was Generated",
        *[f"- `{item}`" for item in payload["what_was_generated"]],
        "",
        "## What Failed",
    ]
    lines.extend([f"- {item}" for item in payload["what_failed"]] or ["- No failed rows recorded."])
    lines.extend(
        [
            "",
            "## What Is Not Comparable",
            *[f"- {item}" for item in payload["what_is_not_comparable"]],
            "",
            "## Safe Claims",
            *[f"- {item}" for item in payload["safe_claims"]],
            "",
            "## Unsafe Claims",
            *[f"- {item}" for item in payload["unsafe_claims"]],
            "",
            "## Recommended Next Action",
            payload["recommended_next_action"],
        ]
    )
    return "\n".join(lines) + "\n"


def _observability_notes(summary: list[dict[str, Any]], metadata: dict[str, Any], files: dict[str, str]) -> str:
    full_rank_count = sum(1 for row in summary if row.get("rank_deficiency_mean") == 0)
    return "\n".join(
        [
            "# Wave Observability Notes",
            "",
            "- Status: non-final candidate diagnostic.",
            f"- Grid cells summarized: `{len(summary)}`.",
            f"- Full-rank mean cells: `{full_rank_count}`.",
            "- Single-UE rows are baseline-only and not cooperative JCLS.",
            "- CRLB values are emitted only for full-rank full-gauged FIM cases.",
            "",
            "## Files",
            *[f"- `{key}`: `{value}`" for key, value in files.items()],
        ]
    ) + "\n"


def _satellite_notes(rows: list[dict[str, Any]], metadata: dict[str, Any], files: dict[str, str]) -> str:
    finite_saved = [row["stage_b_satellites_saved_vs_stage_a"] for row in rows if row.get("stage_b_satellites_saved_vs_stage_a") is not None]
    best = max(finite_saved) if finite_saved else None
    return "\n".join(
        [
            "# Wave Satellite Substitution Notes",
            "",
            "- Status: non-final candidate diagnostic.",
            "- Claim tested, not assumed: cooperating UEs may reduce required satellite count.",
            f"- Best Stage B satellites-saved value in current data: `{best}`.",
            "- Missing threshold entries mean the threshold was not reached in the current grid.",
            "",
            "## Files",
            *[f"- `{key}`: `{value}`" for key, value in files.items()],
        ]
    ) + "\n"


def _secondary_notes(product: str, summary: list[dict[str, Any]], metadata: dict[str, Any], files: dict[str, str]) -> str:
    return "\n".join(
        [
            f"# Wave {product.replace('_', ' ').title()} Notes",
            "",
            "- Status: non-final pilot diagnostic.",
            f"- Summary rows: `{len(summary)}`.",
            "- This product was run after observability and satellite substitution outputs were created.",
            "- Treat as a direction-finding pilot unless expanded with higher Monte Carlo counts.",
            "",
            "## Files",
            *[f"- `{key}`: `{value}`" for key, value in files.items()],
        ]
    ) + "\n"


def _literature_md(rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Wave Literature Comparison Table",
        "",
        "- Status: non-final qualitative comparison.",
        "- Safe framing: JCLS provides a cooperative mechanism for resolving position-clock ambiguity without relying on batching, reference receivers, or terrestrial anchors.",
        "- Unsafe framing: JCLS beats Starlink PNT or other literature rows under non-comparable assumptions.",
        "",
        "| Method | Signals | GNSS assistance | Cooperation | Clock correction assumed | Position error | Citation | Caveat |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        citation = f"[{row['citation']}]({row['url']})" if row.get("url") else row["citation"]
        lines.append(
            f"| {row['method']} | {row['signals_used']} | {row['gnss_assistance']} | "
            f"{row['cooperation']} | {row['clock_correction_assumed']} | {row['position_error']} | "
            f"{citation} | {row['comparability_caveat']} |"
        )
    return "\n".join(lines) + "\n"


def _write_executive_summary(paths: WavePaths, products: list[ProductResult]) -> None:
    generated = {product.name: product for product in products}
    findings = _top_findings(generated)
    payload = {
        "artifact_status": "non_final_wave_results_executive_summary",
        **NONFINAL_FLAGS,
        "products": [asdict(product) for product in products],
        "top_three_wave_making_findings": findings,
        "safe_claims": [
            "Cooperation can be evaluated as an observability/rank and satellite-substitution mechanism, not just an RMSE improvement.",
            "Single-UE rows are baseline-only and are excluded from cooperative JCLS claims.",
            "Sparse and clock-tolerance pilots identify where more runtime should be spent next.",
        ],
        "unsafe_claims": [
            "Any plot is manuscript-ready.",
            "Static clock-offset estimates are clock-drift estimates.",
            "JCLS is proven superior to unrelated Starlink or Doppler PNT literature.",
        ],
        "recommended_next_action": "Continue with a full-grid observability/satellite-substitution expansion if the pilot findings survive human review.",
    }
    _write_json(paths.report_root / "WAVE_RESULTS_EXECUTIVE_SUMMARY.json", payload)
    lines = [
        "# Wave Results Executive Summary",
        "",
        "- Status: non-final diagnostic package.",
        "- Manuscript ready: `false`.",
        "",
        "## Products",
        "| Product | Status | Rows |",
        "|---|---|---:|",
    ]
    for product in products:
        lines.append(f"| `{product.name}` | `{product.status}` | {product.row_count} |")
    lines.extend(
        [
            "",
            "## Top Three Wave-Making Findings",
            *[f"- {item}" for item in findings],
            "",
            "## Safe Claims",
            *[f"- {item}" for item in payload["safe_claims"]],
            "",
            "## Unsafe Claims",
            *[f"- {item}" for item in payload["unsafe_claims"]],
            "",
            "## Recommendation",
            payload["recommended_next_action"],
        ]
    )
    _write_markdown(paths.report_root / "WAVE_RESULTS_EXECUTIVE_SUMMARY.md", "\n".join(lines) + "\n")


def _top_findings(products: dict[str, ProductResult]) -> list[str]:
    findings = []
    obs = products.get("observability")
    if obs and obs.files.get("summary_csv"):
        path = _path_from_report_value(obs.files["summary_csv"])
        if path.exists():
            rows = list(csv.DictReader(path.read_text(encoding="utf-8").splitlines()))
            full_rank = [row for row in rows if _float_or_none(row.get("rank_deficiency_mean")) == 0.0]
            min_full_by_user = {}
            for row in full_rank:
                num_users = int(row["num_users"])
                min_full_by_user[num_users] = min(
                    int(row["num_satellites"]),
                    min_full_by_user.get(num_users, int(row["num_satellites"])),
                )
            comparable = []
            for row in rows:
                stage_a = _float_or_none(row.get("stage_a_position_rmse_m_mean"))
                stage_b = _float_or_none(row.get("stage_b_position_rmse_m_mean"))
                if stage_a is not None and stage_b is not None and stage_a > 0.0:
                    comparable.append(stage_b / stage_a)
            if min_full_by_user:
                findings.append(f"FIM full-rank feasibility appears only for multi-UE cells in this pilot; minimum full-rank N_s by N_u is {min_full_by_user}.")
            if comparable:
                improved = sum(ratio < 1.0 for ratio in comparable)
                findings.append(f"Empirical Stage B/LM-only improves localization in {improved}/{len(comparable)} comparable pilot cells; most cells need estimator/initialization review before any accuracy claim.")
    sat = products.get("satellite_substitution")
    if sat and sat.files.get("wave_iso_accuracy_table_csv"):
        path = _path_from_report_value(sat.files["wave_iso_accuracy_table_csv"])
        if path.exists():
            rows = list(csv.DictReader(path.read_text(encoding="utf-8").splitlines()))
            reached = [
                row
                for row in rows
                if row.get("stage_a_min_satellites") or row.get("stage_b_min_satellites") or row.get("stage_c_min_satellites")
            ]
            if not reached:
                findings.append("No 10 m, 1 m, 0.2 m, or 0.1 m satellite-substitution threshold was reached in the current pilot; the table correctly preserves these gaps.")
            else:
                findings.append(f"Satellite-substitution thresholds were reached in {len(reached)} table rows; inspect the iso-accuracy CSV before forming claim language.")
    sparse = products.get("sparse_sidelink")
    if sparse and sparse.row_count:
        findings.append("Sparse-sidelink pilot rows record graph connectivity and convergence probability, making disconnected/cooperation-inapplicable cases explicit.")
    while len(findings) < 3:
        findings.append("Additional findings require higher Monte Carlo counts and human review before claim language.")
    return findings[:3]


def _path_from_report_value(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else SAT_SIM_ROOT / path


def _float_or_none(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def build_plan(options: WaveOptions) -> dict[str, Any]:
    rows = _planned_rows(options)
    return {
        "artifact_status": "non_final_wave_results_plan",
        **NONFINAL_FLAGS,
        "branch": "codex/jcls-wave-results-exploration",
        "grid_mode": "full" if options.full else "pilot",
        "row_count": len(rows),
        "products": list(PRODUCTS if options.only_product is None else [options.only_product]),
        "observability_grid": {
            "num_users": list(range(1, 11)) if options.full else list(range(1, 6)),
            "num_satellites": list(range(1, 16)) if options.full else list(range(1, 9)),
            "monte_carlo_trials": options.max_trials if options.max_trials is not None else (10 if options.full else 5),
        },
        "required_cli_options_supported": [
            "--dry-run",
            "--list-plan",
            "--resume",
            "--force-rerun",
            "--max-runtime-minutes",
            "--row-timeout-seconds",
            "--trial-timeout-seconds",
            "--max-trials",
            "--only-product",
            "--only-row",
            "--pilot",
            "--full",
            "--cache-root",
        ],
        "rows": [{"row_id": row["row_id"], **{key: row[key] for key in row if key != "row_id"}} for row in rows[:20]],
        "row_listing_truncated": len(rows) > 20,
    }


def run_wave_results(options: WaveOptions, subagent_status: dict[str, Any] | None = None) -> dict[str, Any]:
    paths = WavePaths.from_cache_root(options.cache_root)
    started = time.monotonic()
    paths.output_root.mkdir(parents=True, exist_ok=True)
    paths.report_root.mkdir(parents=True, exist_ok=True)
    plan = build_plan(options)
    _write_run_status(paths, "running", {"started_at_unix": started, "plan": plan})
    _write_task_matrix(paths, subagent_status=subagent_status)
    _write_provenance_audit(paths)
    if options.dry_run or options.list_plan:
        _write_json(paths.output_root / "RUN_PLAN.json", plan)
        _write_run_status(paths, "planned", {"plan": plan})
        return plan

    rows = _execute_rows(_planned_rows(options), paths, options)
    products: list[ProductResult] = []
    if options.only_product in {None, "observability"}:
        observability = _write_observability_product(rows, paths, options)
        products.append(observability)
    if options.only_product in {None, "satellite_substitution"}:
        products.append(_write_satellite_substitution_product(rows, paths, options))
    if options.only_product in {None, "clock_tolerance"}:
        products.append(_write_secondary_product(product="clock_tolerance", rows=rows, paths=paths, options=options))
    if options.only_product in {None, "sparse_sidelink"}:
        products.append(_write_secondary_product(product="sparse_sidelink", rows=rows, paths=paths, options=options))
    if options.only_product in {None, "time_to_accuracy"}:
        products.append(_write_secondary_product(product="time_to_accuracy", rows=rows, paths=paths, options=options))
    if options.only_product in {None, "literature_comparison"}:
        products.append(_write_literature_product(paths))
    gallery = _write_wave_gallery(paths, products)
    _write_executive_summary(paths, products)
    _write_manifest(paths, products, started, options)
    final_payload = {
        "artifact_status": "non_final_wave_results_complete",
        **NONFINAL_FLAGS,
        "runtime_seconds": time.monotonic() - started,
        "products": [asdict(product) for product in products],
        "failed_rows": [row for row in rows if row.get("failure_recorded")],
        "cache_root": _repo_rel(paths.output_root),
        "report_root": _repo_rel(paths.report_root),
        "gallery": gallery,
    }
    _write_run_status(paths, "complete", final_payload)
    return final_payload


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Write/list the plan without executing simulations.")
    parser.add_argument("--list-plan", action="store_true", help="List planned rows and exit.")
    parser.add_argument("--resume", action="store_true", help="Resume from row cache. Resume is also the default.")
    parser.add_argument("--force-rerun", action="store_true", help="Ignore cached row JSON and recompute.")
    parser.add_argument("--max-runtime-minutes", type=float, default=None)
    parser.add_argument("--row-timeout-seconds", type=float, default=None)
    parser.add_argument("--trial-timeout-seconds", type=float, default=None)
    parser.add_argument("--max-trials", type=int, default=None)
    parser.add_argument("--only-product", choices=PRODUCTS, default=None)
    parser.add_argument("--only-row", default=None)
    parser.add_argument("--pilot", action="store_true", help="Run the cheap pilot grid.")
    parser.add_argument("--full", action="store_true", help="Run the expanded grid.")
    parser.add_argument("--cache-root", type=Path, default=SAT_SIM_ROOT / "outputs" / "wave_results")
    parser.add_argument("--no-plots", action="store_true", help="Skip PDF/PNG rendering.")
    return parser.parse_args(argv)


def options_from_args(args: argparse.Namespace) -> WaveOptions:
    return WaveOptions(
        cache_root=args.cache_root,
        dry_run=bool(args.dry_run),
        list_plan=bool(args.list_plan),
        resume=True,
        force_rerun=bool(args.force_rerun),
        max_runtime_minutes=args.max_runtime_minutes,
        row_timeout_seconds=args.row_timeout_seconds,
        trial_timeout_seconds=args.trial_timeout_seconds,
        max_trials=args.max_trials,
        only_product=args.only_product,
        only_row=args.only_row,
        pilot=bool(args.pilot or not args.full),
        full=bool(args.full),
        render_plots=not bool(args.no_plots),
    )


def main(argv: list[str] | None = None) -> dict[str, Any]:
    args = _parse_args(argv)
    options = options_from_args(args)
    payload = run_wave_results(options)
    print(json.dumps(_json_ready(payload), indent=2, sort_keys=True))
    return payload


if __name__ == "__main__":
    main()
