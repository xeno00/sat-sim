"""Package-native V24 figure-generation helpers for Figs. 4--7.

The routines in this module are deterministic, notebook-free, and intended to
replace unsafe legacy figure provenance with reproducible package outputs. They
write package-native review artifacts only; manuscript figure directories are
not touched.
"""

from __future__ import annotations

import csv
import json
import math
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np
from scipy.optimize import least_squares

from .bounds import manuscript_crlb_reportability_from_fim
from .configs import V24ScenarioConfig, directed_sidelink_links, downlink_links
from .constants import C_KM_PER_S
from .fim import gaussian_fim_from_jacobian
from .gauge import expected_v24_parameter_dim, reference_satellite_node_id
from .geometry import GroundReference, manuscript_candidate_geometry
from .io import json_ready
from .jacobian import analytic_toa_jacobian_km, toa_range_vector_from_theta_km
from .metrics import clock_error_relative_to_reference, position_error_m
from .noise import LinkBudgetConfig, range_sigmas_for_links
from .parameters import pack_v24_theta, unpack_v24_theta

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SAT_SIM_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_WARNING = "Diagnostic-only package-native output; not a manuscript-grade reproduction and not for TAES submission."
DIAGNOSTIC_ARTIFACT_FLAGS = {
    "diagnostic_only": True,
    "candidate_only": False,
    "non_final": True,
    "manuscript_ready": False,
    "not_for_manuscript_submission": True,
}
CANDIDATE_ARTIFACT_WARNING = (
    "Manuscript-candidate package-native output; geometry/noise assumptions are closer to V24 "
    "but algorithm fidelity and final human signoff are still required before TAES submission."
)
CANDIDATE_ARTIFACT_FLAGS = {
    "diagnostic_only": False,
    "candidate_only": True,
    "non_final": True,
    "manuscript_ready": False,
    "not_for_manuscript_submission": True,
}
UNSAFE_OUTPUT_ROOT_PARTS = {
    "work-in-progress",
    "psfrag",
    "generatepsfrag",
    "jcls_simulation",
    "jcls_simulation.ipynb",
    "legacy",
    "notebook",
    "manuscript",
    "response",
    "response-letter",
    "bibliography",
}
WINDOWS_RESERVED_FILENAMES = {"CON", "PRN", "AUX", "NUL", *(f"COM{index}" for index in range(1, 10)), *(f"LPT{index}" for index in range(1, 10))}
FIGURE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


BASELINE_DEFINITIONS: dict[str, dict[str, Any]] = {
    "without_cooperation": {
        "label": "Without cooperation",
        "state_estimated": "UE position per receiver only",
        "satellite_clocks": "ignored/fixed to zero",
        "ue_clocks": "ignored/fixed to zero",
        "uses_sl": False,
        "uses_multiple_satellite_dl": True,
        "bias_note": (
            "This conventional TOA baseline is intentionally vulnerable to "
            "residual UE and satellite clock offsets because it does not "
            "estimate clock states."
        ),
    },
    "coarse_jcls": {
        "label": "Coarse JCLS",
        "state_estimated": "full V24 theta: UE positions, UE clocks, non-reference satellite clocks",
        "satellite_clocks": "non-reference satellite clocks estimated; first satellite fixed",
        "ue_clocks": "estimated",
        "uses_sl": True,
        "uses_multiple_satellite_dl": True,
        "bias_note": "Clock offsets are estimated jointly with UE positions using one measurement epoch.",
    },
    "refined_jcls": {
        "label": "Refined JCLS, 0.5 s",
        "state_estimated": "full V24 theta over repeated static-geometry measurement epochs",
        "satellite_clocks": "non-reference satellite clocks estimated; first satellite fixed",
        "ue_clocks": "estimated",
        "uses_sl": True,
        "uses_multiple_satellite_dl": True,
        "bias_note": (
            "Uses the coarse JCLS solution as initialization and fuses multiple "
            "independent measurement epochs over the configured refinement window."
        ),
    },
}


@dataclass(frozen=True)
class FigureRunResult:
    """Paths and metadata produced by one figure run."""

    figure_id: str
    output_dir: Path
    raw_csv: Path
    summary_csv: Path
    raw_npz: Path
    pdf: Path
    metadata_json: Path
    provenance_json: Path


def load_figure_config(config_path: str | Path) -> dict[str, Any]:
    """Load and validate a package-native figure config."""

    path = Path(config_path)
    config = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "figure_id",
        "sweep_type",
        "base_seed",
        "monte_carlo_trials",
        "num_users_values",
        "num_satellites_values",
        "clock_std_devs_ns",
        "refinement_epochs",
    }
    missing = sorted(required - set(config))
    if missing:
        raise ValueError(f"Figure config {path} is missing field(s): {missing}.")
    validate_figure_id(str(config["figure_id"]))
    if int(config["monte_carlo_trials"]) < 1:
        raise ValueError("monte_carlo_trials must be at least 1.")
    if int(config["base_seed"]) < 0:
        raise ValueError("base_seed must be nonnegative.")
    if int(config["refinement_epochs"]) < 1:
        raise ValueError("refinement_epochs must be at least 1.")
    if str(config["metric_field"]) not in {"position_error_mean_m", "sync_error_mean_s"}:
        raise ValueError(f"Unsupported metric_field: {config['metric_field']!r}.")
    if str(config.get("scenario_model", "diagnostic_static_flat_noise")) == "manuscript_candidate_mit_stata_synthetic_leo":
        for field in ("reference_location", "ue_disk_radius_m", "minimum_elevation_deg", "link_budget"):
            if field not in config:
                raise ValueError(f"Manuscript-candidate config is missing field: {field}.")
    elif float(config.get("range_std_dev_km", 0.0)) <= 0.0:
        raise ValueError("range_std_dev_km must be positive for diagnostic flat-noise configs.")
    return config


def validate_figure_id(figure_id: str) -> str:
    """Validate and return a path-safe figure identifier."""

    if not FIGURE_ID_PATTERN.fullmatch(figure_id):
        raise ValueError(
            "figure_id must be a path-safe identifier containing only letters, "
            "numbers, underscores, and hyphens."
        )
    if figure_id.upper() in WINDOWS_RESERVED_FILENAMES:
        raise ValueError(f"figure_id uses a Windows reserved filename: {figure_id!r}.")
    lowered = figure_id.lower()
    if any(part in lowered for part in ("work-in-progress", "psfrag", "jcls_simulation", "notebook", "legacy")):
        raise ValueError(f"figure_id contains an unsafe provenance term: {figure_id!r}.")
    return figure_id


def repo_relative_path(path: str | Path) -> str:
    """Return a repository-relative path string for paths under ``sat-sim``."""

    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(SAT_SIM_ROOT).as_posix()
    except ValueError as exc:
        raise ValueError(f"Path is outside sat-sim and cannot be recorded as repo-relative: {path}") from exc


def validate_output_root(output_root: str | Path, *, allow_unsafe_output_root: bool = False) -> Path:
    """Validate and return an output root for diagnostic-only figure artifacts."""

    path = Path(output_root)
    if not allow_unsafe_output_root and any(part == ".." for part in path.parts):
        raise ValueError(f"Refusing output root with parent-directory traversal: {output_root}")

    resolved = path.resolve()
    if allow_unsafe_output_root:
        return path

    try:
        resolved.relative_to(SAT_SIM_ROOT)
    except ValueError as exc:
        raise ValueError(
            "Refusing output root outside sat-sim. Use a repo-local diagnostic output root "
            "or the developer-only unsafe override."
        ) from exc

    lowered_parts = {part.lower() for part in resolved.parts}
    unsafe_parts = sorted(lowered_parts & UNSAFE_OUTPUT_ROOT_PARTS)
    if unsafe_parts:
        raise ValueError(f"Refusing unsafe diagnostic output root containing {unsafe_parts}: {output_root}")
    return path


def _all_links(num_users: int, num_satellites: int) -> tuple[tuple[int, int], ...]:
    """Return all downlink and directed sidelink measurements."""

    return downlink_links(num_users, num_satellites) + directed_sidelink_links(num_users)


def _scenario_for_case(
    *,
    num_users: int,
    num_satellites: int,
    seed: int,
    clock_std_ns: float,
    range_std_dev_km: float,
) -> V24ScenarioConfig:
    """Return a deterministic static scenario for one figure case."""

    if num_users < 1:
        raise ValueError("num_users must be at least 1.")
    if num_satellites < 2:
        raise ValueError("num_satellites must be at least 2.")
    rng = np.random.default_rng(int(seed))

    user_angles = np.linspace(0.2, 2.0 * np.pi + 0.2, num_users, endpoint=False)
    user_radii_km = np.linspace(0.05, 0.5, num_users)
    ue_positions = np.column_stack(
        [
            user_radii_km * np.cos(user_angles),
            user_radii_km * np.sin(user_angles),
            0.02 * np.arange(num_users, dtype=float),
        ]
    )
    ue_positions += rng.normal(0.0, 0.005, size=ue_positions.shape)

    satellite_angles = np.linspace(0.0, 2.0 * np.pi, num_satellites, endpoint=False)
    satellite_positions = np.column_stack(
        [
            9.0 * np.cos(satellite_angles),
            7.0 * np.sin(satellite_angles),
            18.0 + 1.2 * np.arange(num_satellites, dtype=float),
        ]
    )
    satellite_positions += rng.normal(0.0, 0.01, size=satellite_positions.shape)

    clock_std_km = float(clock_std_ns) * 1e-9 * C_KM_PER_S
    ue_clocks = rng.normal(0.0, clock_std_km, size=num_users)
    non_reference_satellite_clocks = rng.normal(0.0, clock_std_km, size=num_satellites - 1)
    links = _all_links(num_users, num_satellites)
    return V24ScenarioConfig(
        scenario_name=f"fig_case_nu{num_users}_ns{num_satellites}_clock{clock_std_ns:g}ns",
        num_users=num_users,
        num_satellites=num_satellites,
        seed=int(seed),
        ue_positions_km=ue_positions,
        satellite_positions_km=satellite_positions,
        ue_clock_offsets_km=ue_clocks,
        non_reference_satellite_clock_offsets_km=non_reference_satellite_clocks,
        links=links,
        range_std_devs_km=np.full(len(links), float(range_std_dev_km), dtype=float),
    )


def _link_budget_from_config(config: dict[str, Any]) -> LinkBudgetConfig:
    """Return manuscript-candidate link-budget config from figure config."""

    values = dict(config.get("link_budget", {}))
    return LinkBudgetConfig(**values)


def _reference_from_config(config: dict[str, Any]) -> GroundReference:
    """Return manuscript-candidate ground reference from figure config."""

    reference = dict(config["reference_location"])
    return GroundReference(
        latitude_deg=float(reference["latitude_deg"]),
        longitude_deg=float(reference["longitude_deg"]),
        altitude_m=float(reference.get("altitude_m", 0.0)),
    )


def _manuscript_candidate_scenario_for_case(
    *,
    config: dict[str, Any],
    num_users: int,
    num_satellites: int,
    seed: int,
    clock_std_ns: float,
) -> tuple[V24ScenarioConfig, dict[str, Any]]:
    """Return a V24 scenario using manuscript-candidate geometry and link sigmas."""

    geometry = manuscript_candidate_geometry(
        num_users=num_users,
        num_satellites=num_satellites,
        seed=seed,
        reference=_reference_from_config(config),
        ue_radius_m=float(config["ue_disk_radius_m"]),
        minimum_elevation_deg=float(config["minimum_elevation_deg"]),
        satellite_pool_size=int(config.get("satellite_pool_size", max(24, num_satellites))),
        satellite_altitude_km=float(config.get("satellite_altitude_km", 550.0)),
    )
    clock_std_km = float(clock_std_ns) * 1e-9 * C_KM_PER_S
    rng = np.random.default_rng(int(seed) + 7919)
    ue_clocks = rng.normal(0.0, clock_std_km, size=num_users)
    non_reference_satellite_clocks = rng.normal(0.0, clock_std_km, size=num_satellites - 1)
    links = _all_links(num_users, num_satellites)
    sigmas, link_records, link_summary = range_sigmas_for_links(
        ue_positions_km=geometry.ue_positions_km,
        satellite_positions_km=geometry.satellite_positions_km,
        links=links,
        num_users=num_users,
        config=_link_budget_from_config(config),
    )
    scenario = V24ScenarioConfig(
        scenario_name=f"manuscript_candidate_nu{num_users}_ns{num_satellites}_clock{clock_std_ns:g}ns",
        num_users=num_users,
        num_satellites=num_satellites,
        seed=int(seed),
        ue_positions_km=geometry.ue_positions_km,
        satellite_positions_km=geometry.satellite_positions_km,
        ue_clock_offsets_km=ue_clocks,
        non_reference_satellite_clock_offsets_km=non_reference_satellite_clocks,
        links=links,
        range_std_devs_km=sigmas,
    )
    return scenario, {
        "case_seed": int(seed),
        "num_users": int(num_users),
        "num_satellites": int(num_satellites),
        "clock_std_ns": float(clock_std_ns),
        "clock_std_range_km": float(clock_std_km),
        "geometry": geometry.metadata,
        "link_noise": {
            "summary": link_summary,
            "links": link_records,
        },
    }


def _scenario_and_metadata_for_case(
    *,
    config: dict[str, Any],
    case: dict[str, Any],
    seed: int,
) -> tuple[V24ScenarioConfig, dict[str, Any]]:
    """Return scenario plus case metadata for a config/case pair."""

    scenario_model = str(config.get("scenario_model", "diagnostic_static_flat_noise"))
    if scenario_model == "manuscript_candidate_mit_stata_synthetic_leo":
        return _manuscript_candidate_scenario_for_case(
            config=config,
            num_users=case["num_users"],
            num_satellites=case["num_satellites"],
            seed=seed,
            clock_std_ns=case["clock_std_ns"],
        )

    scenario = _scenario_for_case(
        num_users=case["num_users"],
        num_satellites=case["num_satellites"],
        seed=seed,
        clock_std_ns=case["clock_std_ns"],
        range_std_dev_km=float(config["range_std_dev_km"]),
    )
    return scenario, {
        "case_seed": int(seed),
        "num_users": int(case["num_users"]),
        "num_satellites": int(case["num_satellites"]),
        "clock_std_ns": float(case["clock_std_ns"]),
        "scenario_model": "diagnostic_static_flat_noise",
        "flat_range_std_dev_km": float(config["range_std_dev_km"]),
    }


def _initial_theta(scenario: V24ScenarioConfig, rng: np.random.Generator) -> np.ndarray:
    """Return deterministic perturbed initial theta for full JCLS estimators."""

    position_perturbation = rng.normal(0.0, 0.08, size=scenario.ue_positions_km.shape)
    ue_clock_init = np.zeros(scenario.num_users, dtype=float)
    sat_clock_init = np.zeros(scenario.num_satellites - 1, dtype=float)
    return pack_v24_theta(
        scenario.ue_positions_km + position_perturbation,
        ue_clock_init,
        sat_clock_init,
    )


def _full_clock_dict_from_theta(
    theta: np.ndarray,
    num_users: int,
    num_satellites: int,
) -> dict[int, float]:
    """Return a full clock dictionary from V24 theta."""

    _positions, ue_clocks, non_reference_satellite_clocks = unpack_v24_theta(
        theta,
        num_users,
        num_satellites,
    )
    reference_id = reference_satellite_node_id(num_users)
    clocks = {node_id: float(ue_clocks[node_id - 1]) for node_id in range(1, num_users + 1)}
    clocks[reference_id] = 0.0
    for offset, value in enumerate(non_reference_satellite_clocks, start=1):
        clocks[reference_id + offset] = float(value)
    return clocks


def _measurement_vector(
    scenario: V24ScenarioConfig,
    rng: np.random.Generator,
    *,
    noise_scale: float = 1.0,
) -> np.ndarray:
    """Return one synthetic noisy range-domain measurement vector."""

    truth = toa_range_vector_from_theta_km(
        scenario.theta(),
        scenario.links,
        scenario.satellite_positions_km,
        scenario.num_users,
        scenario.num_satellites,
    )
    if noise_scale == 0.0:
        return truth.copy()
    return truth + rng.normal(0.0, scenario.range_std_devs_km * float(noise_scale))


def _estimate_without_cooperation(
    scenario: V24ScenarioConfig,
    z: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    """Estimate UE positions independently from downlinks while ignoring clocks."""

    estimated_positions = []
    links = list(scenario.links)
    for user_id in range(1, scenario.num_users + 1):
        row_indices = [
            index
            for index, (receiver_node_id, transmitter_node_id) in enumerate(links)
            if receiver_node_id == user_id and transmitter_node_id > scenario.num_users
        ]
        x0 = scenario.ue_positions_km[user_id - 1] + rng.normal(0.0, 0.12, size=3)
        satellite_positions = scenario.satellite_positions_km

        def residual(position: np.ndarray) -> np.ndarray:
            values = []
            for row_index in row_indices:
                _receiver, transmitter = links[row_index]
                satellite_position = satellite_positions[transmitter - scenario.num_users - 1]
                values.append((np.linalg.norm(position - satellite_position) - z[row_index]) / scenario.range_std_devs_km[row_index])
            return np.asarray(values, dtype=float)

        result = least_squares(residual, x0, method="trf", max_nfev=200)
        estimated_positions.append(result.x)
    return np.asarray(estimated_positions, dtype=float)


def _stacked_links_and_measurements(
    scenario: V24ScenarioConfig,
    measurements: list[np.ndarray],
) -> tuple[list[tuple[int, int]], np.ndarray, np.ndarray]:
    """Return repeated links, stacked measurements, and stacked sigmas."""

    links: list[tuple[int, int]] = []
    sigmas: list[float] = []
    for _measurement in measurements:
        links.extend(scenario.links)
        sigmas.extend(scenario.range_std_devs_km.tolist())
    return links, np.concatenate(measurements), np.asarray(sigmas, dtype=float)


def _estimate_full_jcls(
    scenario: V24ScenarioConfig,
    measurements: list[np.ndarray],
    x0: np.ndarray,
) -> tuple[np.ndarray, bool, float, int]:
    """Return full V24 JCLS estimate, success flag, cost, and evaluations."""

    links, z_stack, sigma_stack = _stacked_links_and_measurements(scenario, measurements)

    def residual(theta: np.ndarray) -> np.ndarray:
        prediction = toa_range_vector_from_theta_km(
            theta,
            links,
            scenario.satellite_positions_km,
            scenario.num_users,
            scenario.num_satellites,
        )
        return (prediction - z_stack) / sigma_stack

    def jacobian(theta: np.ndarray) -> np.ndarray:
        jac = analytic_toa_jacobian_km(
            theta,
            links,
            scenario.satellite_positions_km,
            scenario.num_users,
            scenario.num_satellites,
        )
        return jac / sigma_stack[:, np.newaxis]

    result = least_squares(
        residual,
        x0,
        jac=jacobian,
        method="trf",
        max_nfev=200,
        xtol=1e-10,
        ftol=1e-10,
        gtol=1e-10,
    )
    return result.x, bool(result.success), float(result.cost), int(result.nfev)


def _rank_diagnostics(scenario: V24ScenarioConfig, epoch_count: int) -> dict[str, Any]:
    """Return FIM rank diagnostics for a repeated-epoch measurement set."""

    links = list(scenario.links) * int(epoch_count)
    sigmas = np.tile(scenario.range_std_devs_km, int(epoch_count))
    jac = analytic_toa_jacobian_km(
        scenario.theta(),
        links,
        scenario.satellite_positions_km,
        scenario.num_users,
        scenario.num_satellites,
    )
    fim = gaussian_fim_from_jacobian(jac, sigmas)
    reportability = manuscript_crlb_reportability_from_fim(
        fim,
        scenario.num_users,
        scenario.num_satellites,
    )
    return {
        "fim_rank": int(reportability["rank"]),
        "fim_nullity": int(reportability["nullity"]),
        "parameter_dim": expected_v24_parameter_dim(scenario.num_users, scenario.num_satellites),
        "measurement_count": len(links),
        "is_full_rank": bool(reportability["is_full_rank"]),
        "crlb_status": str(reportability["crlb_status"]),
        "condition_number": float(np.linalg.cond(fim)) if fim.size else math.inf,
    }


def run_single_trial(
    scenario: V24ScenarioConfig,
    *,
    trial_seed: int,
    refinement_epochs: int,
    noise_scale: float = 1.0,
) -> list[dict[str, Any]]:
    """Run all package-native baselines for one Monte Carlo trial."""

    rng = np.random.default_rng(int(trial_seed))
    measurements = [
        _measurement_vector(scenario, rng, noise_scale=noise_scale)
        for _ in range(max(1, int(refinement_epochs)))
    ]
    first_measurement = measurements[0]
    true_positions = scenario.ue_positions_km
    true_clocks = scenario.full_clock_dict_km()

    rows: list[dict[str, Any]] = []
    no_coop_positions = _estimate_without_cooperation(scenario, first_measurement, rng)
    no_coop_clock_estimate = {node_id: 0.0 for node_id in true_clocks}
    rows.append(
        _metric_row(
            scenario,
            "without_cooperation",
            no_coop_positions,
            no_coop_clock_estimate,
            true_positions,
            true_clocks,
            success=True,
            cost=None,
            nfev=None,
            rank=_rank_diagnostics(scenario, 1),
        )
    )

    x0 = _initial_theta(scenario, rng)
    coarse_theta, coarse_success, coarse_cost, coarse_nfev = _estimate_full_jcls(
        scenario,
        [first_measurement],
        x0,
    )
    coarse_positions, _, _ = unpack_v24_theta(
        coarse_theta,
        scenario.num_users,
        scenario.num_satellites,
    )
    rows.append(
        _metric_row(
            scenario,
            "coarse_jcls",
            coarse_positions,
            _full_clock_dict_from_theta(coarse_theta, scenario.num_users, scenario.num_satellites),
            true_positions,
            true_clocks,
            success=coarse_success,
            cost=coarse_cost,
            nfev=coarse_nfev,
            rank=_rank_diagnostics(scenario, 1),
        )
    )

    refined_theta, refined_success, refined_cost, refined_nfev = _estimate_full_jcls(
        scenario,
        measurements,
        coarse_theta,
    )
    refined_positions, _, _ = unpack_v24_theta(
        refined_theta,
        scenario.num_users,
        scenario.num_satellites,
    )
    rows.append(
        _metric_row(
            scenario,
            "refined_jcls",
            refined_positions,
            _full_clock_dict_from_theta(refined_theta, scenario.num_users, scenario.num_satellites),
            true_positions,
            true_clocks,
            success=refined_success,
            cost=refined_cost,
            nfev=refined_nfev,
            rank=_rank_diagnostics(scenario, max(1, int(refinement_epochs))),
        )
    )
    return rows


def _metric_row(
    scenario: V24ScenarioConfig,
    baseline_id: str,
    estimated_positions_km: np.ndarray,
    estimated_clocks_km: dict[int, float],
    true_positions_km: np.ndarray,
    true_clocks_km: dict[int, float],
    *,
    success: bool,
    cost: float | None,
    nfev: int | None,
    rank: dict[str, Any],
) -> dict[str, Any]:
    """Return one metric row for a baseline estimate."""

    pos_errors_m = position_error_m(true_positions_km, estimated_positions_km)
    clock_error_km = clock_error_relative_to_reference(
        true_clocks_km,
        estimated_clocks_km,
        scenario.num_users,
        scenario.num_satellites,
    )
    return {
        "baseline_id": baseline_id,
        "baseline_label": BASELINE_DEFINITIONS[baseline_id]["label"],
        "num_users": scenario.num_users,
        "num_satellites": scenario.num_satellites,
        "position_error_mean_m": float(np.mean(pos_errors_m)),
        "position_error_median_m": float(np.median(pos_errors_m)),
        "position_error_rmse_m": float(np.sqrt(np.mean(pos_errors_m**2))),
        "sync_error_mean_s": float(clock_error_km / C_KM_PER_S),
        "success": bool(success),
        "cost": cost,
        "nfev": nfev,
        **rank,
    }


def _case_values(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Return figure case values from a config."""

    cases = []
    sweep_type = str(config["sweep_type"])
    if sweep_type == "satellite_count":
        clock_ns = float(config["clock_std_devs_ns"][0])
        for num_users in config["num_users_values"]:
            for num_satellites in config["num_satellites_values"]:
                cases.append(
                    {
                        "num_users": int(num_users),
                        "num_satellites": int(num_satellites),
                        "clock_std_ns": clock_ns,
                        "x_value": int(num_satellites),
                        "series_value": int(num_users),
                    }
                )
    elif sweep_type == "clock_std":
        num_users = int(config["num_users_values"][0])
        num_satellites = int(config["num_satellites_values"][0])
        for clock_ns in config["clock_std_devs_ns"]:
            cases.append(
                {
                    "num_users": num_users,
                    "num_satellites": num_satellites,
                    "clock_std_ns": float(clock_ns),
                    "x_value": float(clock_ns),
                    "series_value": "clock_sweep",
                }
            )
    else:
        raise ValueError(f"Unsupported sweep_type: {sweep_type!r}.")
    return cases


def run_figure_config(
    config_path: str | Path,
    output_root: str | Path,
    *,
    overwrite: bool = False,
    allow_unsafe_output_root: bool = False,
) -> FigureRunResult:
    """Run one package-native Fig. 4--7 config and write all outputs."""

    config = load_figure_config(config_path)
    figure_id = str(config["figure_id"])
    safe_output_root = validate_output_root(
        output_root,
        allow_unsafe_output_root=allow_unsafe_output_root,
    )
    output_dir = safe_output_root / figure_id
    if output_dir.exists() and any(output_dir.iterdir()) and not overwrite:
        raise FileExistsError(
            f"Refusing to overwrite existing non-empty diagnostic output directory: {output_dir}. "
            "Pass overwrite=True or use the CLI --overwrite flag."
        )
    output_dir.mkdir(parents=True, exist_ok=True)

    start = time.perf_counter()
    rows: list[dict[str, Any]] = []
    case_metadata: list[dict[str, Any]] = []
    case_values = _case_values(config)
    for case_index, case in enumerate(case_values):
        case_seed = int(config["base_seed"]) + 1009 * case_index
        scenario, metadata_for_case = _scenario_and_metadata_for_case(
            config=config,
            case=case,
            seed=case_seed,
        )
        metadata_for_case.update({"case_index": case_index, "x_value": case["x_value"], "series_value": case["series_value"]})
        case_metadata.append(metadata_for_case)
        for trial in range(int(config["monte_carlo_trials"])):
            trial_seed = case_seed + 7919 * (trial + 1)
            trial_rows = run_single_trial(
                scenario,
                trial_seed=trial_seed,
                refinement_epochs=int(config["refinement_epochs"]),
            )
            for row in trial_rows:
                row.update(
                    {
                        "figure_id": figure_id,
                        "case_index": case_index,
                        "trial": trial,
                        "trial_seed": trial_seed,
                        "x_value": case["x_value"],
                        "series_value": case["series_value"],
                        "clock_std_ns": case["clock_std_ns"],
                        "range_std_dev_km": float(config["range_std_dev_km"]) if "range_std_dev_km" in config else None,
                    }
                )
                rows.append(row)

    summary_rows = summarize_rows(rows, metric_field=str(config["metric_field"]))
    raw_csv = output_dir / f"{figure_id}_raw.csv"
    summary_csv = output_dir / f"{figure_id}_summary.csv"
    raw_npz = output_dir / f"{figure_id}_raw.npz"
    pdf = output_dir / f"{figure_id}.pdf"
    metadata_json = output_dir / f"{figure_id}_metadata.json"
    provenance_json = output_dir / f"{figure_id}_provenance.json"

    _write_csv(raw_csv, rows)
    _write_csv(summary_csv, summary_rows)
    _write_npz(raw_npz, rows)
    _write_plot(pdf, config, summary_rows)
    runtime_s = time.perf_counter() - start
    metadata = _metadata_payload(
        config=config,
        config_path=Path(config_path),
        output_dir=output_dir,
        rows=rows,
        summary_rows=summary_rows,
        runtime_s=runtime_s,
        overwrite_used=overwrite,
        case_metadata=case_metadata,
    )
    metadata_json.write_text(json.dumps(json_ready(metadata), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    provenance_json.write_text(
        json.dumps(json_ready(_provenance_payload(config, metadata)), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return FigureRunResult(
        figure_id=figure_id,
        output_dir=output_dir,
        raw_csv=raw_csv,
        summary_csv=summary_csv,
        raw_npz=raw_npz,
        pdf=pdf,
        metadata_json=metadata_json,
        provenance_json=provenance_json,
    )


def summarize_rows(rows: list[dict[str, Any]], *, metric_field: str) -> list[dict[str, Any]]:
    """Return grouped Monte Carlo summary rows."""

    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for row in rows:
        key = (
            row["figure_id"],
            row["baseline_id"],
            row["baseline_label"],
            row["x_value"],
            row["series_value"],
            row["num_users"],
            row["num_satellites"],
            row["clock_std_ns"],
        )
        groups.setdefault(key, []).append(row)
    summaries = []
    for key, group_rows in sorted(groups.items(), key=lambda item: tuple(str(part) for part in item[0])):
        values = np.asarray([float(row[metric_field]) for row in group_rows], dtype=float)
        success_rate = float(np.mean([bool(row["success"]) for row in group_rows]))
        summaries.append(
            {
                "figure_id": key[0],
                "baseline_id": key[1],
                "baseline_label": key[2],
                "x_value": key[3],
                "series_value": key[4],
                "num_users": key[5],
                "num_satellites": key[6],
                "clock_std_ns": key[7],
                "metric_field": metric_field,
                "mean": float(np.mean(values)),
                "median": float(np.median(values)),
                "rmse": float(np.sqrt(np.mean(values**2))),
                "std": float(np.std(values, ddof=1)) if values.size > 1 else 0.0,
                "standard_error": float(np.std(values, ddof=1) / math.sqrt(values.size)) if values.size > 1 else 0.0,
                "trial_count": int(values.size),
                "success_rate": success_rate,
                "failure_rate": 1.0 - success_rate,
                "min_fim_rank": int(min(row["fim_rank"] for row in group_rows)),
                "max_fim_nullity": int(max(row["fim_nullity"] for row in group_rows)),
                "all_full_rank": bool(all(row["is_full_rank"] for row in group_rows)),
                "max_condition_number": float(max(row["condition_number"] for row in group_rows)),
            }
        )
    return summaries


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write rows to CSV."""

    if not rows:
        raise ValueError("Cannot write empty CSV.")
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_npz(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write compact raw arrays to NPZ."""

    np.savez(
        path,
        position_error_mean_m=np.asarray([row["position_error_mean_m"] for row in rows], dtype=float),
        sync_error_mean_s=np.asarray([row["sync_error_mean_s"] for row in rows], dtype=float),
        x_value=np.asarray([row["x_value"] for row in rows], dtype=float),
        num_users=np.asarray([row["num_users"] for row in rows], dtype=int),
        num_satellites=np.asarray([row["num_satellites"] for row in rows], dtype=int),
        fim_rank=np.asarray([row["fim_rank"] for row in rows], dtype=int),
        fim_nullity=np.asarray([row["fim_nullity"] for row in rows], dtype=int),
        success=np.asarray([row["success"] for row in rows], dtype=bool),
        baseline_id=np.asarray([row["baseline_id"] for row in rows]),
    )


def _write_plot(path: Path, config: dict[str, Any], summary_rows: list[dict[str, Any]]) -> None:
    """Write a deterministic PDF plot for one figure config."""

    metric_field = str(config["metric_field"])
    plot_scale = float(config.get("plot_metric_scale", 1.0))
    plt.figure(figsize=(3.5, 2.65), dpi=300)
    baselines = ["without_cooperation", "coarse_jcls", "refined_jcls"]
    if str(config["sweep_type"]) == "satellite_count":
        for series_value in config["num_users_values"]:
            for baseline in baselines:
                points = [
                    row
                    for row in summary_rows
                    if row["baseline_id"] == baseline and row["series_value"] == int(series_value)
                ]
                if not points:
                    continue
                points = sorted(points, key=lambda row: float(row["x_value"]))
                label = f"{BASELINE_DEFINITIONS[baseline]['label']}, Nu={series_value}"
                plt.errorbar(
                    [row["x_value"] for row in points],
                    [row["mean"] * plot_scale for row in points],
                    yerr=[row["standard_error"] * plot_scale for row in points],
                    marker="o",
                    linewidth=1.1,
                    markersize=3,
                    capsize=2,
                    label=label,
                )
    else:
        for baseline in baselines:
            points = [row for row in summary_rows if row["baseline_id"] == baseline]
            points = sorted(points, key=lambda row: float(row["x_value"]))
            plt.errorbar(
                [row["x_value"] for row in points],
                [row["mean"] * plot_scale for row in points],
                yerr=[row["standard_error"] * plot_scale for row in points],
                marker="o",
                linewidth=1.2,
                markersize=3,
                capsize=2,
                label=BASELINE_DEFINITIONS[baseline]["label"],
            )
    plt.xlabel(str(config["x_label"]))
    plt.ylabel(str(config["y_label"]))
    if bool(config.get("log_y", True)):
        plt.yscale("log")
    if str(config["sweep_type"]) == "clock_std":
        plt.xscale("log")
    plt.grid(True, which="both", alpha=0.28)
    plt.legend(fontsize=5.2)
    plt.title(str(config.get("title", config["figure_id"])), fontsize=8)
    plt.tight_layout()
    plt.savefig(path, format="pdf")
    plt.close()


def _git_commit_hash() -> str:
    """Return current git commit hash, or unknown if unavailable."""

    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=Path(__file__).resolve().parents[1], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _metadata_payload(
    *,
    config: dict[str, Any],
    config_path: Path,
    output_dir: Path,
    rows: list[dict[str, Any]],
    summary_rows: list[dict[str, Any]],
    runtime_s: float,
    overwrite_used: bool,
    case_metadata: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return figure metadata for provenance."""

    flags, warning, artifact_kind = _artifact_policy(config)
    return {
        "metadata_type": "package_native_v24_figure_metadata",
        **flags,
        "artifact_warning": warning,
        "artifact_kind": artifact_kind,
        "figure_id": config["figure_id"],
        "scenario_model": config.get("scenario_model", "diagnostic_static_flat_noise"),
        "commit_hash": _git_commit_hash(),
        "config_path": repo_relative_path(config_path),
        "output_dir": repo_relative_path(output_dir),
        "base_seed": int(config["base_seed"]),
        "monte_carlo_trials": int(config["monte_carlo_trials"]),
        "refinement_epochs": int(config["refinement_epochs"]),
        "range_std_dev_km": float(config["range_std_dev_km"]) if "range_std_dev_km" in config else None,
        "units": {
            "positions_internal": "km",
            "clock_offsets_internal": "range-domain km",
            "toa_measurements": "range-domain km",
            "position_metric": "m",
            "synchronization_metric_raw": "s",
            "plot_metric_scale": float(config.get("plot_metric_scale", 1.0)),
            "plot_metric_unit": config.get("plot_metric_unit", config.get("metric_unit", "raw")),
        },
        "overwrite_used": bool(overwrite_used),
        "runtime_seconds": float(runtime_s),
        "raw_row_count": len(rows),
        "summary_row_count": len(summary_rows),
        "case_metadata": case_metadata,
        "baselines": BASELINE_DEFINITIONS,
        "code_path": [
            "jcls_sim.figure_generation",
            "jcls_sim.measurements",
            "jcls_sim.jacobian",
            "jcls_sim.fim",
            "jcls_sim.metrics",
        ],
        "notebook_used": False,
        "manuscript_directories_touched": False,
    }


def _provenance_payload(config: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    """Return manuscript figure provenance mapping for one figure."""

    figure_id = str(config["figure_id"])
    flags, warning, artifact_kind = _artifact_policy(config)
    return {
        "provenance_type": f"package_native_v24_{artifact_kind}_figure_provenance",
        **flags,
        "artifact_warning": warning,
        "artifact_kind": artifact_kind,
        "figure_id": figure_id,
        "manuscript_figure": config.get("manuscript_figure_label", figure_id),
        "command": (
            "python scripts/run_v24_figures_4_7.py "
            f"--config {metadata['config_path']} --output-root v24_figure_outputs --overwrite"
        ),
        "config_file": metadata["config_path"],
        "raw_output_file": f"{metadata['output_dir']}/{figure_id}_raw.csv",
        "npz_output_file": f"{metadata['output_dir']}/{figure_id}_raw.npz",
        "summary_output_file": f"{metadata['output_dir']}/{figure_id}_summary.csv",
        "plot_output_file": f"{metadata['output_dir']}/{figure_id}.pdf",
        "metadata_file": f"{metadata['output_dir']}/{figure_id}_metadata.json",
        "test_coverage": [
            "tests/test_figure_generation.py",
            "tests/test_estimators.py",
            "tests/test_measurements.py",
            "tests/test_jacobian.py",
            "tests/test_metrics.py",
        ],
        "assumptions": config.get("assumptions", []),
        "known_discrepancy_from_v24": config.get(
            "known_discrepancy_from_v24",
            "Package-native deterministic provenance; not forced to match legacy notebook curves.",
        ),
    }


def _artifact_policy(config: dict[str, Any]) -> tuple[dict[str, bool], str, str]:
    """Return artifact flags, warning, and kind for a figure config."""

    profile = str(config.get("artifact_profile", "diagnostic"))
    if profile == "diagnostic":
        return DIAGNOSTIC_ARTIFACT_FLAGS, ARTIFACT_WARNING, "diagnostic"
    if profile == "manuscript_candidate":
        return CANDIDATE_ARTIFACT_FLAGS, CANDIDATE_ARTIFACT_WARNING, "manuscript_candidate"
    raise ValueError(f"Unsupported artifact_profile: {profile!r}.")
