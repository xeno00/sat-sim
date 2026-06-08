"""Low-cost Step 3 covariance/dynamics exploration.

This diagnostic explores typed Step 3 covariance initialization and update
constraints on sparse deterministic network cases. It does not run notebook
code, full ladders, network-size graph generation, or manuscript figure
workflows.
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

from jcls_sim.constants import C_KM_PER_S  # noqa: E402
from scripts.explore_step3_near_winner_sparse import (  # noqa: E402
    MEDIUM_CASES,
    SPARSE_CASES,
    SparseCase,
    _clock_slice,
    _drift_slice,
    _make_case,
    _measurements_and_jacobian,
    _pack_state,
    _position_error_m,
    _position_slice,
    _repo_rel,
    _schur_update,
    _sync_error_km,
    _unpack_state,
)


OUTPUT_ROOT = SAT_SIM_ROOT / "outputs" / "step3_covariance_exploration"
PLOT_ROOT = OUTPUT_ROOT / "plots"
REPORT_ROOT = SAT_SIM_ROOT / "outputs" / "reports"
POSITION_RATIO_EPS_M = 1.0e-6
SYNC_RATIO_EPS_KM = 1.0e-9
DEFAULT_SUBAGENT_STATUS = {
    "mode": "sidecar_read_only_plus_orchestrator",
    "real_subagents": [
        {
            "nickname": "Locke",
            "role": "lane/schema risk reviewer",
            "status": "completed",
            "edits": "none",
        },
        {
            "nickname": "Banach",
            "role": "test/gallery integration reviewer",
            "status": "completed",
            "edits": "none",
        },
    ],
    "edit_owner": "orchestrator",
}


@dataclass(frozen=True)
class CovarianceVariant:
    """One covariance/dynamics exploration variant."""

    lane: str
    name: str
    description: str
    covariance_mode: str
    position_variance_km2: float = 0.20**2
    ue_clock_variance_km2: float = 0.0025**2
    satellite_clock_variance_km2: float = 0.0025**2
    drift_variance_km2_per_s2: float = 0.0012**2
    include_drift_state: bool = True
    damping_lambda: float = 1.0e-6
    block_diagonal_covariance: bool = False
    residual_scaled: bool = False
    position_floor_km2: float = 0.002**2
    position_ceiling_km2: float = 1.0**2
    clock_floor_km2: float = 0.0002**2
    clock_ceiling_km2: float = 0.020**2
    drift_floor_km2_per_s2: float = 0.00005**2
    drift_ceiling_km2_per_s2: float = 0.010**2
    q_position_scale: float = 0.0
    q_clock_scale: float = 0.0
    q_drift_scale: float = 0.0
    project_common_clock: bool = False
    common_clock_damping: float = 1.0
    position_update_scale: float = 1.0
    clock_update_scale: float = 1.0
    drift_update_scale: float = 1.0
    clock_only: bool = False
    position_only: bool = False
    schur_mode: str = "none"
    max_position_update_km: float | None = None
    max_clock_update_km: float | None = None
    max_drift_update_km_per_s: float | None = None
    measurement_sigma_km: float = 2.5e-4


LANE_VARIANTS: list[CovarianceVariant] = [
    CovarianceVariant("lm_curvature", "full_lm_covariance", "Full damped LM curvature covariance.", "lm_full", damping_lambda=1.0e-5),
    CovarianceVariant("lm_curvature", "block_diag_lm_covariance", "Block-diagonalized LM curvature covariance.", "lm_full", damping_lambda=1.0e-5, block_diagonal_covariance=True),
    CovarianceVariant("lm_curvature", "lm_covariance_floors_ceilings", "LM curvature covariance with block floors/ceilings.", "lm_full", damping_lambda=1.0e-5, block_diagonal_covariance=True, position_floor_km2=0.010**2, clock_floor_km2=0.0005**2),
    CovarianceVariant("residual_scaled_lm", "full_residual_scaled_covariance", "Residual-scaled damped curvature covariance.", "lm_full", residual_scaled=True, damping_lambda=1.0e-5),
    CovarianceVariant("residual_scaled_lm", "block_diag_residual_scaled_covariance", "Block-diagonal residual-scaled curvature covariance.", "lm_full", residual_scaled=True, block_diagonal_covariance=True, damping_lambda=1.0e-5),
    CovarianceVariant("residual_scaled_lm", "residual_scaled_floors_ceilings", "Residual-scaled covariance with block floors/ceilings.", "lm_full", residual_scaled=True, block_diagonal_covariance=True, damping_lambda=1.0e-5, position_floor_km2=0.010**2, clock_floor_km2=0.0005**2),
    CovarianceVariant("position_freeze_damping", "freeze_positions_clock_drift", "Freeze positions and update clocks/drifts only.", "block_scaled", clock_only=True),
    CovarianceVariant("position_freeze_damping", "position_update_damped_025", "Damp position update by 0.25.", "block_scaled", position_update_scale=0.25),
    CovarianceVariant("position_freeze_damping", "position_update_clipped", "Clip position updates.", "block_scaled", max_position_update_km=0.004),
    CovarianceVariant("position_freeze_damping", "position_damped_clock_loose", "Damp position and use looser clock prior.", "block_scaled", position_update_scale=0.25, ue_clock_variance_km2=0.006**2, satellite_clock_variance_km2=0.006**2, drift_variance_km2_per_s2=0.003**2),
    CovarianceVariant("block_scaled_drift_tuning", "block_drift_base", "Block-scaled drift base.", "block_scaled"),
    CovarianceVariant("block_scaled_drift_tuning", "block_drift_strong_clock", "Strong clock/drift priors.", "block_scaled", ue_clock_variance_km2=0.0010**2, satellite_clock_variance_km2=0.0010**2, drift_variance_km2_per_s2=0.0005**2),
    CovarianceVariant("block_scaled_drift_tuning", "block_drift_loose_clock", "Loose clock/drift priors.", "block_scaled", ue_clock_variance_km2=0.0060**2, satellite_clock_variance_km2=0.0060**2, drift_variance_km2_per_s2=0.0030**2),
    CovarianceVariant("block_scaled_drift_tuning", "block_drift_tight_position", "Tighter position prior.", "block_scaled", position_variance_km2=0.08**2),
    CovarianceVariant("block_scaled_drift_tuning", "block_drift_loose_position", "Looser position prior.", "block_scaled", position_variance_km2=0.50**2),
    CovarianceVariant("gauge_common_clock", "project_common_clock", "Project common-clock update component.", "block_scaled", project_common_clock=True),
    CovarianceVariant("gauge_common_clock", "damp_common_clock_025", "Damp common-clock component by 0.25.", "block_scaled", common_clock_damping=0.25),
    CovarianceVariant("gauge_common_clock", "no_drift_project_common_clock", "No-drift block covariance with common-clock projection.", "block_scaled", include_drift_state=False, drift_variance_km2_per_s2=0.0, project_common_clock=True),
    CovarianceVariant("schur_reduced", "schur_position_clock_backsolve", "Schur solve with clock nuisance block backsolve.", "block_scaled", include_drift_state=False, schur_mode="schur_full"),
    CovarianceVariant("schur_reduced", "schur_position_only", "Schur solve then keep position increment only.", "block_scaled", include_drift_state=False, schur_mode="position_only", position_only=True),
    CovarianceVariant("schur_reduced", "clock_only_reduced", "Joint solve then keep clock/drift increment only.", "block_scaled", clock_only=True),
    CovarianceVariant("schur_reduced", "clock_first_position_small", "Clock update with strongly damped position increment.", "block_scaled", position_update_scale=0.15),
]


REQUIRED_ROW_FIELDS = [
    "lane",
    "variant",
    "num_users",
    "num_satellites",
    "runtime_seconds",
    "cache_status",
    "step_b_position_error_m",
    "step3_position_error_m",
    "step_b_sync_error_km",
    "step3_sync_error_km",
    "position_ratio",
    "sync_ratio",
    "both_improved",
    "position_hurt_but_sync_helped",
    "sync_hurt_but_position_helped",
    "position_update_norm",
    "ue_clock_update_norm",
    "satellite_clock_update_norm",
    "clock_drift_update_norm",
    "p_position_trace",
    "p_position_eig_min",
    "p_position_eig_max",
    "p_clock_trace",
    "p_clock_eig_min",
    "p_clock_eig_max",
    "q_position_scale",
    "q_clock_scale",
    "q_drift_scale",
    "objective_before",
    "objective_after",
    "residual_cost_before",
    "residual_cost_after",
    "prior_cost",
    "accepted_update_count",
    "rejected_update_count",
    "finite_output",
    "normal_rank",
    "normal_condition",
    "nullspace_update_ratio",
    "truth_state_used_for_acceptance",
    "truth_state_used_for_covariance",
    "cache_key",
]


def sparse_cases(*, include_hard_case: bool = False) -> list[SparseCase]:
    """Return default sparse cases, optionally including the cheap hard case."""

    cases = [_make_case(num_users, num_satellites) for num_users, num_satellites in SPARSE_CASES]
    if include_hard_case:
        cases.append(_make_case(3, 4))
    return cases


def medium_cases() -> list[SparseCase]:
    """Return promoted-medium validation cases."""

    return [_make_case(num_users, num_satellites) for num_users, num_satellites in MEDIUM_CASES]


def _cache_key(case: SparseCase, variant: CovarianceVariant, grid: str) -> str:
    """Return deterministic cache/config key."""

    payload = {
        "script": Path(__file__).name,
        "grid": grid,
        "case": {"num_users": case.num_users, "num_satellites": case.num_satellites},
        "variant": asdict(variant),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def _base_block_variances(case: SparseCase, variant: CovarianceVariant) -> np.ndarray:
    """Return typed diagonal variances for position, clock, and optional drift."""

    position = np.full(2 * case.num_users, variant.position_variance_km2)
    clock = np.empty(case.num_users + case.num_satellites - 1, dtype=float)
    clock[: case.num_users] = variant.ue_clock_variance_km2
    clock[case.num_users :] = variant.satellite_clock_variance_km2
    pieces = [position, clock]
    if variant.include_drift_state:
        pieces.append(np.full_like(clock, variant.drift_variance_km2_per_s2))
    return np.concatenate(pieces)


def _clip_variances(case: SparseCase, variant: CovarianceVariant, variances: np.ndarray) -> np.ndarray:
    """Apply block floors and ceilings to diagonal covariance entries."""

    clipped = np.asarray(variances, dtype=float).copy()
    pos = _position_slice(case)
    clk = _clock_slice(case)
    clipped[pos] = np.clip(clipped[pos], variant.position_floor_km2, variant.position_ceiling_km2)
    clipped[clk] = np.clip(clipped[clk], variant.clock_floor_km2, variant.clock_ceiling_km2)
    if variant.include_drift_state:
        drift = _drift_slice(case, variant)
        clipped[drift] = np.clip(clipped[drift], variant.drift_floor_km2_per_s2, variant.drift_ceiling_km2_per_s2)
    return clipped


def _block_diagonalize(covariance: np.ndarray, case: SparseCase, variant: CovarianceVariant) -> np.ndarray:
    """Keep covariance blocks and zero cross-block coupling."""

    output = np.zeros_like(covariance)
    for slc in (_position_slice(case), _clock_slice(case), _drift_slice(case, variant)):
        if slc.stop > slc.start:
            output[slc, slc] = covariance[slc, slc]
    return output


def _covariance_from_mode(case: SparseCase, variant: CovarianceVariant, jacobian: np.ndarray, residual: np.ndarray, sigma: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
    """Build Step 3 prior covariance for one variant."""

    r_inv_diag = 1.0 / np.square(sigma)
    information = jacobian.T @ (jacobian * r_inv_diag[:, None])
    if variant.covariance_mode == "block_scaled":
        variances = _clip_variances(case, variant, _base_block_variances(case, variant))
        covariance = np.diag(variances)
        source = "typed_block_scaled"
    else:
        covariance = np.linalg.pinv(information + variant.damping_lambda * np.eye(information.shape[0]), rcond=1.0e-10)
        covariance = 0.5 * (covariance + covariance.T)
        source = "lm_curvature"
        if variant.residual_scaled:
            residual_cost = float(np.sum(np.square(residual / sigma)))
            dof = max(1, residual.size - jacobian.shape[1])
            covariance *= residual_cost / dof
            source = "residual_scaled_lm_curvature"
        if variant.block_diagonal_covariance:
            covariance = _block_diagonalize(covariance, case, variant)
            source += "_block_diagonal"
        variances = _clip_variances(case, variant, np.diag(covariance))
        covariance = np.diag(variances)
        source += "_diagonal_clipped"
    return covariance, {
        "covariance_source": source,
        "covariance_rank": int(np.linalg.matrix_rank(covariance)),
        "information_rank": int(np.linalg.matrix_rank(information)),
    }


def _matrix_block_stats(matrix: np.ndarray, slc: slice) -> dict[str, float]:
    """Return trace and eigenvalue range for a covariance block."""

    if slc.stop <= slc.start:
        return {"trace": 0.0, "eig_min": 0.0, "eig_max": 0.0}
    block = matrix[slc, slc]
    eigvals = np.linalg.eigvalsh(0.5 * (block + block.T))
    return {
        "trace": float(np.trace(block)),
        "eig_min": float(np.min(eigvals)),
        "eig_max": float(np.max(eigvals)),
    }


def _project_or_damp_common_clock(case: SparseCase, variant: CovarianceVariant, update: np.ndarray) -> np.ndarray:
    """Apply common-clock projection or damping to a candidate update."""

    adjusted = update.copy()
    clock = _clock_slice(case)
    mean = float(np.mean(adjusted[clock]))
    if variant.project_common_clock:
        adjusted[clock] -= mean
    elif variant.common_clock_damping < 1.0:
        adjusted[clock] -= (1.0 - variant.common_clock_damping) * mean
    if variant.include_drift_state:
        drift = _drift_slice(case, variant)
        if drift.stop > drift.start:
            drift_mean = float(np.mean(adjusted[drift]))
            if variant.project_common_clock:
                adjusted[drift] -= drift_mean
            elif variant.common_clock_damping < 1.0:
                adjusted[drift] -= (1.0 - variant.common_clock_damping) * drift_mean
    return adjusted


def _scale_and_clip_update(case: SparseCase, variant: CovarianceVariant, update: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
    """Apply block update scaling and clipping."""

    adjusted = update.copy()
    pos = _position_slice(case)
    clk = _clock_slice(case)
    drift = _drift_slice(case, variant)
    adjusted[pos] *= variant.position_update_scale
    adjusted[clk] *= variant.clock_update_scale
    if drift.stop > drift.start:
        adjusted[drift] *= variant.drift_update_scale
    if variant.clock_only:
        adjusted[pos] = 0.0
    if variant.position_only:
        adjusted[clk] = 0.0
        if drift.stop > drift.start:
            adjusted[drift] = 0.0

    def clip_block(slc: slice, limit: float | None) -> tuple[float, bool]:
        if limit is None or slc.stop <= slc.start:
            return 1.0, False
        norm = float(np.linalg.norm(adjusted[slc]))
        if norm == 0.0 or norm <= limit:
            return 1.0, False
        scale = float(limit / norm)
        adjusted[slc] *= scale
        return scale, True

    pos_scale, pos_clipped = clip_block(pos, variant.max_position_update_km)
    clock_scale, clock_clipped = clip_block(clk, variant.max_clock_update_km)
    drift_scale, drift_clipped = clip_block(drift, variant.max_drift_update_km_per_s)
    return adjusted, {
        "position_clip_scale": pos_scale,
        "clock_clip_scale": clock_scale,
        "drift_clip_scale": drift_scale,
        "position_clipped": pos_clipped,
        "clock_clipped": clock_clipped,
        "drift_clipped": drift_clipped,
        "floors_ceilings_applied": True,
    }


def _candidate_update(case: SparseCase, variant: CovarianceVariant, normal: np.ndarray, rhs: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
    """Return candidate update and reduced-solve diagnostics."""

    if variant.schur_mode in {"schur_full", "position_only"}:
        update, diagnostics = _schur_update(normal, rhs, case)
        return update, diagnostics
    update = np.linalg.pinv(normal, rcond=1.0e-10) @ rhs
    return update, {"schur_reduced_dimension": 0, "schur_nuisance_dimension": 0, "schur_reduced_rank": 0}


def _nullspace_stats(jacobian: np.ndarray, update: np.ndarray) -> dict[str, float]:
    """Return nullspace update diagnostics from the local Jacobian."""

    if update.size == 0 or np.linalg.norm(update) == 0.0:
        return {"nullspace_update_norm": 0.0, "nullspace_update_ratio": 0.0}
    _, singular_values, vh = np.linalg.svd(jacobian, full_matrices=True)
    tol = max(jacobian.shape) * np.finfo(float).eps * (singular_values[0] if singular_values.size else 1.0)
    rank = int(np.sum(singular_values > tol))
    null_basis = vh.T[:, rank:]
    null_component = null_basis @ (null_basis.T @ update) if null_basis.size else np.zeros_like(update)
    null_norm = float(np.linalg.norm(null_component))
    return {
        "nullspace_update_norm": null_norm,
        "nullspace_update_ratio": null_norm / max(float(np.linalg.norm(update)), 1.0e-18),
    }


def _condition_number(matrix: np.ndarray) -> float:
    """Return finite condition-number diagnostic when possible."""

    try:
        value = float(np.linalg.cond(matrix))
    except np.linalg.LinAlgError:
        return float("inf")
    return value


def _block_norms(case: SparseCase, variant: CovarianceVariant, update: np.ndarray, jacobian: np.ndarray) -> dict[str, float]:
    """Return update norms by state block."""

    clock_update = update[_clock_slice(case)]
    drift_update = update[_drift_slice(case, variant)] if variant.include_drift_state else np.asarray([], dtype=float)
    output = {
        "position_update_norm": float(np.linalg.norm(update[_position_slice(case)])),
        "ue_clock_update_norm": float(np.linalg.norm(clock_update[: case.num_users])),
        "satellite_clock_update_norm": float(np.linalg.norm(clock_update[case.num_users :])),
        "clock_drift_update_norm": float(np.linalg.norm(drift_update)),
        "common_clock_update_component": abs(float(np.mean(clock_update))) if clock_update.size else 0.0,
    }
    output.update(_nullspace_stats(jacobian, update))
    return output


def _evaluate_case_variant(case: SparseCase, variant: CovarianceVariant, *, grid: str) -> dict[str, Any]:
    """Evaluate one sparse/medium case and covariance variant."""

    started = time.monotonic()
    theta0 = _pack_state(case, variant)
    z_true, z_pred, jacobian = _measurements_and_jacobian(case, variant, theta0)
    residual = z_true - z_pred
    sigma = np.full(z_true.size, variant.measurement_sigma_km)
    covariance, covariance_info = _covariance_from_mode(case, variant, jacobian, residual, sigma)
    p_inv = np.linalg.pinv(covariance, rcond=1.0e-10)
    r_inv_diag = 1.0 / np.square(sigma)
    normal = jacobian.T @ (jacobian * r_inv_diag[:, None]) + p_inv
    rhs = jacobian.T @ (r_inv_diag * residual)
    update, reduced = _candidate_update(case, variant, normal, rhs)
    raw_common = abs(float(np.mean(update[_clock_slice(case)])))
    update = _project_or_damp_common_clock(case, variant, update)
    update, clipping = _scale_and_clip_update(case, variant, update)
    theta1 = theta0 + update
    pos0, clock0, drift0 = _unpack_state(theta0, case, variant)
    pos1, clock1, drift1 = _unpack_state(theta1, case, variant)
    pos_before = _position_error_m(case, pos0)
    pos_after = _position_error_m(case, pos1)
    sync_before = _sync_error_km(case, clock0, drift0)
    sync_after = _sync_error_km(case, clock1, drift1)
    residual_after = z_true - _measurements_and_jacobian(case, variant, theta1)[1]
    residual_cost_before = float(np.sum(np.square(residual / sigma)))
    residual_cost_after = float(np.sum(np.square(residual_after / sigma)))
    prior_cost = float(update.T @ p_inv @ update)
    objective_before = residual_cost_before
    objective_after = residual_cost_after + prior_cost
    pos_stats = _matrix_block_stats(covariance, _position_slice(case))
    clock_stats = _matrix_block_stats(covariance, _clock_slice(case))
    drift_stats = _matrix_block_stats(covariance, _drift_slice(case, variant))
    position_ratio = pos_after / max(pos_before, POSITION_RATIO_EPS_M)
    sync_ratio = sync_after / max(sync_before, SYNC_RATIO_EPS_KM)
    row = {
        "grid": grid,
        "lane": variant.lane,
        "variant": variant.name,
        "variant_description": variant.description,
        "num_users": case.num_users,
        "num_satellites": case.num_satellites,
        "runtime_seconds": time.monotonic() - started,
        "cache_status": "not_used_deterministic_sparse",
        "cache_key": _cache_key(case, variant, grid),
        "step_b_position_error_m": pos_before,
        "step3_position_error_m": pos_after,
        "step_b_sync_error_km": sync_before,
        "step3_sync_error_km": sync_after,
        "step_b_sync_error_s": sync_before / C_KM_PER_S,
        "step3_sync_error_s": sync_after / C_KM_PER_S,
        "position_ratio": position_ratio,
        "sync_ratio": sync_ratio,
        "both_improved": position_ratio < 1.0 and sync_ratio < 1.0,
        "position_improved": position_ratio < 1.0,
        "sync_improved": sync_ratio < 1.0,
        "position_hurt_but_sync_helped": position_ratio > 1.0 and sync_ratio < 1.0,
        "sync_hurt_but_position_helped": sync_ratio > 1.0 and position_ratio < 1.0,
        "objective_before": objective_before,
        "objective_after": objective_after,
        "objective_decreased": objective_after <= objective_before + 1.0e-9,
        "residual_cost_before": residual_cost_before,
        "residual_cost_after": residual_cost_after,
        "prior_cost": prior_cost,
        "dynamics_cost": 0.0,
        "accepted_update_count": int(objective_after <= objective_before + 1.0e-9),
        "rejected_update_count": int(objective_after > objective_before + 1.0e-9),
        "finite_output": bool(np.all(np.isfinite(theta1)) and np.isfinite(objective_after)),
        "normal_rank": int(np.linalg.matrix_rank(normal)),
        "normal_condition": _condition_number(normal),
        "p_position_trace": pos_stats["trace"],
        "p_position_eig_min": pos_stats["eig_min"],
        "p_position_eig_max": pos_stats["eig_max"],
        "p_clock_trace": clock_stats["trace"],
        "p_clock_eig_min": clock_stats["eig_min"],
        "p_clock_eig_max": clock_stats["eig_max"],
        "p_drift_trace": drift_stats["trace"],
        "p_drift_eig_min": drift_stats["eig_min"],
        "p_drift_eig_max": drift_stats["eig_max"],
        "raw_common_clock_update_component": raw_common,
        "truth_state_used_for_acceptance": False,
        "truth_state_used_for_covariance": False,
        "truth_state_used_for_diagnostics": True,
        "network_size_graph": False,
        "full_ladder_run": False,
        "medium_validation": grid == "medium",
        "manuscript_ready": False,
        "not_for_manuscript_submission": True,
        **asdict(variant),
        **covariance_info,
        **_block_norms(case, variant, update, jacobian),
        **clipping,
        **reduced,
    }
    missing = [field for field in REQUIRED_ROW_FIELDS if field not in row]
    if missing:
        raise RuntimeError(f"row missing required fields: {missing}")
    return row


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> str:
    """Write rows to CSV and return repo-relative path."""

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


def _write_json(path: Path, payload: Any) -> str:
    """Write JSON and return repo-relative path."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return _repo_rel(path)


def _summarize(rows: list[dict[str, Any]], *, group_fields: tuple[str, ...]) -> list[dict[str, Any]]:
    """Summarize rows by lane or variant."""

    keys = sorted({tuple(row[field] for field in group_fields) for row in rows})
    output = []
    for key in keys:
        subset = [row for row in rows if tuple(row[field] for field in group_fields) == key]
        item = {field: value for field, value in zip(group_fields, key)}
        item.update(
            {
                "tested_cases": len(subset),
                "both_improved_count": sum(1 for row in subset if row["both_improved"]),
                "position_improved_count": sum(1 for row in subset if row["position_improved"]),
                "sync_improved_count": sum(1 for row in subset if row["sync_improved"]),
                "mean_position_ratio": float(np.mean([row["position_ratio"] for row in subset])),
                "mean_sync_ratio": float(np.mean([row["sync_ratio"] for row in subset])),
                "max_position_ratio": float(np.max([row["position_ratio"] for row in subset])),
                "max_sync_ratio": float(np.max([row["sync_ratio"] for row in subset])),
                "mean_runtime_seconds": float(np.mean([row["runtime_seconds"] for row in subset])),
                "mean_p_position_trace": float(np.mean([row["p_position_trace"] for row in subset])),
                "mean_p_clock_trace": float(np.mean([row["p_clock_trace"] for row in subset])),
            }
        )
        output.append(item)
    return output


def _promotion_candidates(summary_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Promote at most two variants by sparse covariance exploration criteria."""

    candidates = []
    for row in summary_rows:
        qualifies = (
            row["both_improved_count"] >= 2
            or (row["sync_improved_count"] >= 2 and row["max_position_ratio"] <= 1.10)
            or (row["position_improved_count"] >= 2 and row["max_sync_ratio"] <= 1.10)
        )
        if row["variant"] == "freeze_positions_clock_drift":
            qualifies = row["sync_improved_count"] >= 2 and row["max_position_ratio"] <= 1.001
        if qualifies:
            score = row["mean_position_ratio"] + row["mean_sync_ratio"] - 0.20 * row["both_improved_count"]
            candidates.append({**row, "promotion_score": float(score)})
    return sorted(candidates, key=lambda item: (item["promotion_score"], item["variant"]))[:2]


def _best_variants(summary_rows: list[dict[str, Any]]) -> dict[str, str | None]:
    """Return best variants by position, sync, and balanced score."""

    if not summary_rows:
        return {"position": None, "sync": None, "balanced": None}
    return {
        "position": min(summary_rows, key=lambda row: (row["mean_position_ratio"], row["mean_sync_ratio"]))["variant"],
        "sync": min(summary_rows, key=lambda row: (row["mean_sync_ratio"], row["mean_position_ratio"]))["variant"],
        "balanced": min(summary_rows, key=lambda row: (row["mean_position_ratio"] + row["mean_sync_ratio"], row["variant"]))["variant"],
    }


def _write_lane_outputs(rows: list[dict[str, Any]], lane_summaries: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Write lane-specific raw, summary, and metadata files."""

    outputs = []
    for lane in sorted({row["lane"] for row in rows}):
        lane_rows = [row for row in rows if row["lane"] == lane]
        lane_summary = [row for row in lane_summaries if row["lane"] == lane]
        root = OUTPUT_ROOT / lane
        outputs.append(
            {
                "lane": lane,
                "raw_csv": _write_csv(root / "raw.csv", lane_rows),
                "summary_csv": _write_csv(root / "summary.csv", lane_summary),
                "metadata_json": _write_json(
                    root / "metadata.json",
                    {
                        "lane": lane,
                        "artifact_status": "non_final_step3_covariance_lane",
                        "manuscript_ready": False,
                        "variant_count": len({row["variant"] for row in lane_rows}),
                        "row_count": len(lane_rows),
                        "rows": lane_rows,
                        "summary": lane_summary,
                    },
                ),
            }
        )
    return outputs


def _write_red_team_outputs(summary_rows: list[dict[str, Any]], promoted: list[dict[str, Any]]) -> dict[str, str]:
    """Write red-team/triage lane outputs from aggregate summaries."""

    promoted_names = {row["variant"] for row in promoted}
    rows = []
    for row in summary_rows:
        if row["variant"] in promoted_names:
            classification = "promising"
        elif row["both_improved_count"] > 0:
            classification = "inconclusive"
        elif row["sync_improved_count"] > 0 or row["position_improved_count"] > 0:
            classification = "tradeoff"
        else:
            classification = "dead_end"
        rows.append(
            {
                "lane": "red_team_triage",
                "variant": row["variant"],
                "source_lane": row["lane"],
                "classification": classification,
                "both_improved_count": row["both_improved_count"],
                "mean_position_ratio": row["mean_position_ratio"],
                "mean_sync_ratio": row["mean_sync_ratio"],
                "promoted": row["variant"] in promoted_names,
                "recommendation": "review before medium/integration" if row["variant"] in promoted_names else "do not promote from this sprint",
            }
        )
    root = OUTPUT_ROOT / "red_team_triage"
    summary = _summarize(
        [
            {
                "lane": item["lane"],
                "variant": item["classification"],
                "both_improved": item["classification"] == "promising",
                "position_improved": item["mean_position_ratio"] < 1.0,
                "sync_improved": item["mean_sync_ratio"] < 1.0,
                "position_hurt_but_sync_helped": item["mean_position_ratio"] > 1.0 and item["mean_sync_ratio"] < 1.0,
                "sync_hurt_but_position_helped": item["mean_sync_ratio"] > 1.0 and item["mean_position_ratio"] < 1.0,
                "position_ratio": item["mean_position_ratio"],
                "sync_ratio": item["mean_sync_ratio"],
                "runtime_seconds": 0.0,
                "p_position_trace": 0.0,
                "p_clock_trace": 0.0,
            }
            for item in rows
        ],
        group_fields=("lane", "variant"),
    )
    return {
        "lane": "red_team_triage",
        "raw_csv": _write_csv(root / "raw.csv", rows),
        "summary_csv": _write_csv(root / "summary.csv", summary),
        "metadata_json": _write_json(
            root / "metadata.json",
            {
                "lane": "red_team_triage",
                "artifact_status": "non_final_step3_covariance_red_team_triage",
                "manuscript_ready": False,
                "rows": rows,
                "summary": summary,
            },
        ),
    }


def _write_task_matrix(lane_outputs: list[dict[str, str]], subagent_status: dict[str, Any]) -> tuple[str, str]:
    """Write task-matrix report files."""

    matrix = {
        "artifact_status": "step3_covariance_exploration_task_matrix",
        "subagents": subagent_status,
        "lanes": [
            {
                "lane": output["lane"],
                "owner": "orchestrator",
                "status": "completed",
                "output_files": [output["raw_csv"], output["summary_csv"], output["metadata_json"]],
                "blocker": None,
                "fallback_owner": "orchestrator",
            }
            for output in lane_outputs
        ],
    }
    json_path = _write_json(REPORT_ROOT / "STEP3_COVARIANCE_EXPLORATION_TASK_MATRIX.json", matrix)
    md = [
        "# Step 3 Covariance Exploration Task Matrix",
        "",
        "| Lane | Owner | Status | Output files | Blocker | Fallback owner |",
        "|---|---|---|---|---|---|",
    ]
    for lane in matrix["lanes"]:
        md.append(
            f"| `{lane['lane']}` | {lane['owner']} | {lane['status']} | "
            f"{', '.join(f'`{item}`' for item in lane['output_files'])} | "
            f"{lane['blocker'] or 'none'} | {lane['fallback_owner']} |"
        )
    md_path = REPORT_ROOT / "STEP3_COVARIANCE_EXPLORATION_TASK_MATRIX.md"
    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")
    return _repo_rel(md_path), json_path


def _plot_scatter(rows: list[dict[str, Any]]) -> list[str]:
    """Write position-ratio versus sync-ratio scatter."""

    PLOT_ROOT.mkdir(parents=True, exist_ok=True)
    sparse = [row for row in rows if row["grid"] == "sparse"]
    fig, ax = plt.subplots(figsize=(7.0, 4.8))
    for lane in sorted({row["lane"] for row in sparse}):
        subset = [row for row in sparse if row["lane"] == lane]
        ax.scatter([row["position_ratio"] for row in subset], [row["sync_ratio"] for row in subset], label=lane, s=24, alpha=0.78)
    ax.axvline(1.0, color="0.5", linewidth=0.8)
    ax.axhline(1.0, color="0.5", linewidth=0.8)
    ax.set_xlabel("Position ratio Step3 / StepB")
    ax.set_ylabel("Sync ratio Step3 / StepB")
    ax.set_title("Step 3 covariance exploration")
    ax.legend(fontsize=6)
    fig.tight_layout()
    return _save_plot(fig, "position_sync_ratio_scatter")


def _save_plot(fig: Any, stem: str) -> list[str]:
    """Save a plot as PDF and PNG."""

    outputs = []
    for suffix in ("pdf", "png"):
        path = PLOT_ROOT / f"{stem}.{suffix}"
        fig.savefig(path)
        outputs.append(_repo_rel(path))
    plt.close(fig)
    return outputs


def _plot_both_improved(summary_rows: list[dict[str, Any]]) -> list[str]:
    fig, ax = plt.subplots(figsize=(9.5, 4.4))
    labels = [f"{row['lane']}\n{row['variant']}" for row in summary_rows]
    values = [row["both_improved_count"] for row in summary_rows]
    ax.bar(range(len(labels)), values, color="#4C78A8")
    ax.set_xticks(range(len(labels)), labels, rotation=75, ha="right", fontsize=5)
    ax.set_ylabel("Both-improved sparse cases")
    ax.set_ylim(0, 3)
    ax.set_title("Both-improved count by lane/variant")
    fig.tight_layout()
    return _save_plot(fig, "both_improved_count_by_lane_variant")


def _plot_best_per_lane(summary_rows: list[dict[str, Any]]) -> list[str]:
    best = []
    for lane in sorted({row["lane"] for row in summary_rows}):
        subset = [row for row in summary_rows if row["lane"] == lane]
        best.append(min(subset, key=lambda row: row["mean_position_ratio"] + row["mean_sync_ratio"]))
    fig, ax = plt.subplots(figsize=(8.0, 4.0))
    labels = [row["lane"] for row in best]
    scores = [row["mean_position_ratio"] + row["mean_sync_ratio"] for row in best]
    ax.bar(range(len(labels)), scores, color="#F28E2B")
    ax.set_xticks(range(len(labels)), labels, rotation=25, ha="right")
    ax.set_ylabel("Mean position ratio + sync ratio")
    ax.set_title("Best variant per lane")
    fig.tight_layout()
    return _save_plot(fig, "best_variant_per_lane")


def _plot_covariance_scales(rows: list[dict[str, Any]], x_key: str, y_key: str, stem: str, xlabel: str, ylabel: str) -> list[str]:
    sparse = [row for row in rows if row["grid"] == "sparse"]
    fig, ax = plt.subplots(figsize=(6.5, 4.4))
    for lane in sorted({row["lane"] for row in sparse}):
        subset = [row for row in sparse if row["lane"] == lane]
        ax.scatter([row[x_key] for row in subset], [row[y_key] for row in subset], label=lane, s=24, alpha=0.75)
    ax.set_xscale("log")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(stem.replace("_", " "))
    ax.legend(fontsize=6)
    fig.tight_layout()
    return _save_plot(fig, stem)


def _plot_update_norms(rows: list[dict[str, Any]]) -> list[str]:
    sparse = [row for row in rows if row["grid"] == "sparse"]
    lanes = sorted({row["lane"] for row in sparse})
    matrix = []
    for lane in lanes:
        subset = [row for row in sparse if row["lane"] == lane]
        matrix.append(
            [
                np.mean([row["position_update_norm"] for row in subset]),
                np.mean([row["ue_clock_update_norm"] for row in subset]),
                np.mean([row["satellite_clock_update_norm"] for row in subset]),
                np.mean([row["clock_drift_update_norm"] for row in subset]),
            ]
        )
    matrix = np.asarray(matrix)
    fig, ax = plt.subplots(figsize=(8.2, 4.3))
    x = np.arange(len(lanes))
    width = 0.18
    for idx, label in enumerate(["position", "UE clock", "sat clock", "drift"]):
        ax.bar(x + (idx - 1.5) * width, matrix[:, idx], width=width, label=label)
    ax.set_xticks(x, lanes, rotation=25, ha="right", fontsize=7)
    ax.set_ylabel("Mean update norm")
    ax.set_title("Update norm by block")
    ax.legend(fontsize=7)
    fig.tight_layout()
    return _save_plot(fig, "update_norm_by_block")


def _plot_runtime(lane_summary: list[dict[str, Any]]) -> list[str]:
    fig, ax = plt.subplots(figsize=(7.0, 4.0))
    labels = [row["lane"] for row in lane_summary]
    values = [row["mean_runtime_seconds"] for row in lane_summary]
    ax.bar(range(len(labels)), values, color="#59A14F")
    ax.set_xticks(range(len(labels)), labels, rotation=25, ha="right")
    ax.set_ylabel("Mean runtime [s]")
    ax.set_title("Runtime by lane")
    fig.tight_layout()
    return _save_plot(fig, "runtime_by_lane")


def _write_plots(rows: list[dict[str, Any]], summary_rows: list[dict[str, Any]], lane_summary: list[dict[str, Any]]) -> list[str]:
    """Write compact exploration plots."""

    outputs = []
    outputs.extend(_plot_scatter(rows))
    outputs.extend(_plot_both_improved(summary_rows))
    outputs.extend(_plot_best_per_lane(summary_rows))
    outputs.extend(_plot_covariance_scales(rows, "p_position_trace", "position_ratio", "position_covariance_vs_position_ratio", "Position covariance trace", "Position ratio"))
    outputs.extend(_plot_covariance_scales(rows, "p_clock_trace", "sync_ratio", "clock_covariance_vs_sync_ratio", "Clock covariance trace", "Sync ratio"))
    outputs.extend(_plot_update_norms(rows))
    outputs.extend(_plot_runtime(lane_summary))
    return outputs


def _lane_assessment(summary_rows: list[dict[str, Any]], lane: str) -> bool:
    subset = [row for row in summary_rows if row["lane"] == lane]
    return any(row["both_improved_count"] >= 2 for row in subset)


def _write_report(payload: dict[str, Any]) -> None:
    """Write Markdown and JSON report pair."""

    _write_json(REPORT_ROOT / "STEP3_COVARIANCE_EXPLORATION_REPORT.json", payload)
    md = [
        "# Step 3 Covariance Exploration Report",
        "",
        "## Executive Summary",
        "",
        f"- Artifact status: `{payload['artifact_status']}`",
        f"- Runtime seconds: `{payload['runtime_seconds']:.3f}`",
        f"- Sparse cases: `{payload['sparse_cases_tested']}`",
        f"- Lanes run: `{payload['lanes_run']}`",
        f"- Promoted variants: `{payload['promoted_variants']}`",
        f"- Medium validation run: `{payload['medium_validation_run']}`",
        "",
        "## Best Variants",
        "",
        f"- Best position variant: `{payload['best_variants']['position']}`",
        f"- Best synchronization variant: `{payload['best_variants']['sync']}`",
        f"- Best balanced variant: `{payload['best_variants']['balanced']}`",
        "",
        "## Lane Findings",
        "",
        f"- LM-derived position covariance helped: `{payload['lm_covariance_helped']}`",
        f"- Residual-scaled covariance helped: `{payload['residual_scaled_covariance_helped']}`",
        f"- Position-freeze/damping helped: `{payload['position_freeze_damping_helped']}`",
        f"- Clock drift helped: `{payload['clock_drift_helped']}`",
        f"- Gauge projection helped: `{payload['gauge_projection_helped']}`",
        f"- Schur/reduced update helped: `{payload['schur_reduced_helped']}`",
        "",
        "## Variant Summary",
        "",
        "| Lane | Variant | Both improved | Mean pos ratio | Mean sync ratio |",
        "|---|---|---:|---:|---:|",
    ]
    for row in payload["summary"]:
        md.append(
            f"| `{row['lane']}` | `{row['variant']}` | "
            f"{row['both_improved_count']}/{row['tested_cases']} | "
            f"{row['mean_position_ratio']:.4g} | {row['mean_sync_ratio']:.4g} |"
        )
    if payload["medium_validation_summary"]:
        md += [
            "",
            "## Medium Validation Summary",
            "",
            "| Variant | Both improved | Mean pos ratio | Mean sync ratio |",
            "|---|---:|---:|---:|",
        ]
        for row in payload["medium_validation_summary"]:
            md.append(
                f"| `{row['variant']}` | {row['both_improved_count']}/{row['tested_cases']} | "
                f"{row['mean_position_ratio']:.4g} | {row['mean_sync_ratio']:.4g} |"
            )
    md += [
        "",
        "## Output Paths",
        "",
        f"- All raw CSV: `{payload['all_raw_csv']}`",
        f"- All summary CSV: `{payload['all_summary_csv']}`",
        f"- Metadata JSON: `{payload['metadata_json']}`",
        f"- Task matrix: `{payload['task_matrix_md']}`",
        "- Plots:",
        *[f"  - `{path}`" for path in payload["plots"]],
    ]
    (REPORT_ROOT / "STEP3_COVARIANCE_EXPLORATION_REPORT.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def _planned_work(*, include_hard_case: bool, run_promoted_medium: bool) -> dict[str, Any]:
    """Return planned work metadata without executing rows."""

    cases = SPARSE_CASES + ([(3, 4)] if include_hard_case else [])
    return {
        "artifact_status": "non_final_step3_covariance_exploration_planned_work",
        "will_execute": False,
        "sparse_cases": [{"num_users": nu, "num_satellites": ns} for nu, ns in cases],
        "lanes": sorted({variant.lane for variant in LANE_VARIANTS}),
        "variants": [variant.name for variant in LANE_VARIANTS],
        "variant_count_by_lane": {
            lane: sum(1 for variant in LANE_VARIANTS if variant.lane == lane)
            for lane in sorted({variant.lane for variant in LANE_VARIANTS})
        },
        "sparse_row_count": len(cases) * len(LANE_VARIANTS),
        "run_promoted_medium": run_promoted_medium,
        "medium_grid_default": False,
        "network_size_graphs_run": False,
        "full_ladder_run": False,
    }


def run_exploration(*, include_hard_case: bool = False, run_promoted_medium: bool = False, subagent_status: dict[str, Any] | None = None) -> dict[str, Any]:
    """Run sparse covariance exploration and optional promoted medium validation."""

    started = time.monotonic()
    cases = sparse_cases(include_hard_case=include_hard_case)
    sparse_rows = [_evaluate_case_variant(case, variant, grid="sparse") for case in cases for variant in LANE_VARIANTS]
    summary_rows = _summarize(sparse_rows, group_fields=("lane", "variant"))
    lane_summary = _summarize(sparse_rows, group_fields=("lane",))
    promoted = _promotion_candidates(summary_rows)
    medium_rows: list[dict[str, Any]] = []
    if run_promoted_medium and promoted:
        promoted_names = {row["variant"] for row in promoted}
        promoted_variants = [variant for variant in LANE_VARIANTS if variant.name in promoted_names]
        medium_rows = [_evaluate_case_variant(case, variant, grid="medium") for case in medium_cases() for variant in promoted_variants]
        for variant in promoted_variants:
            rows = [row for row in medium_rows if row["variant"] == variant.name]
            root = OUTPUT_ROOT / "medium_validation" / variant.name
            _write_csv(root / "raw.csv", rows)
            _write_json(root / "metadata.json", {"variant": variant.name, "rows": rows, "manuscript_ready": False})
    all_rows = sparse_rows + medium_rows
    medium_summary = _summarize(medium_rows, group_fields=("variant",)) if medium_rows else []
    lane_outputs = _write_lane_outputs(sparse_rows, lane_summary)
    lane_outputs.append(_write_red_team_outputs(summary_rows, promoted))
    task_matrix_md, task_matrix_json = _write_task_matrix(lane_outputs, subagent_status or DEFAULT_SUBAGENT_STATUS)
    all_raw = _write_csv(OUTPUT_ROOT / "all_raw.csv", all_rows)
    all_summary = _write_csv(OUTPUT_ROOT / "all_summary.csv", summary_rows)
    plots = _write_plots(all_rows, summary_rows, lane_summary)
    best = _best_variants(summary_rows)
    payload = {
        "artifact_status": "non_final_step3_covariance_exploration",
        "manuscript_ready": False,
        "not_for_manuscript_submission": True,
        "deterministic": True,
        "monte_carlo": False,
        "truth_state_used_for_acceptance": False,
        "truth_state_used_for_covariance": False,
        "truth_state_used_for_diagnostics": True,
        "network_size_graphs_run": False,
        "full_ladder_run": False,
        "medium_grid_default": False,
        "medium_validation_run": bool(medium_rows),
        "medium_validation_only_promoted_variants": True,
        "sparse_cases_tested": [case.name for case in cases],
        "medium_cases_tested": [f"Nu{nu}_Ns{ns}" for nu, ns in MEDIUM_CASES] if medium_rows else [],
        "lanes_run": sorted({variant.lane for variant in LANE_VARIANTS}) + ["red_team_triage"],
        "variants_tested": [variant.name for variant in LANE_VARIANTS],
        "variant_count_by_lane": {
            lane: sum(1 for variant in LANE_VARIANTS if variant.lane == lane)
            for lane in sorted({variant.lane for variant in LANE_VARIANTS})
        },
        "promoted_variants": [row["variant"] for row in promoted],
        "row_count": len(all_rows),
        "sparse_row_count": len(sparse_rows),
        "medium_row_count": len(medium_rows),
        "runtime_seconds": time.monotonic() - started,
        "all_raw_csv": all_raw,
        "all_summary_csv": all_summary,
        "lane_outputs": lane_outputs,
        "task_matrix_md": task_matrix_md,
        "task_matrix_json": task_matrix_json,
        "plots": plots,
        "summary": summary_rows,
        "lane_summary": lane_summary,
        "medium_validation_summary": medium_summary,
        "rows": all_rows,
        "best_variants": best,
        "lm_covariance_helped": _lane_assessment(summary_rows, "lm_curvature"),
        "residual_scaled_covariance_helped": _lane_assessment(summary_rows, "residual_scaled_lm"),
        "position_freeze_damping_helped": _lane_assessment(summary_rows, "position_freeze_damping"),
        "clock_drift_helped": _lane_assessment(summary_rows, "block_scaled_drift_tuning"),
        "gauge_projection_helped": _lane_assessment(summary_rows, "gauge_common_clock"),
        "schur_reduced_helped": _lane_assessment(summary_rows, "schur_reduced"),
        "next_recommended_action": "review covariance exploration and promote at most one robust Step 3 formulation for real migration-ladder implementation",
    }
    metadata_json = _write_json(OUTPUT_ROOT / "metadata.json", payload)
    payload["metadata_json"] = metadata_json
    _write_json(OUTPUT_ROOT / "metadata.json", payload)
    _write_report(payload)
    return payload


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="List planned work without executing.")
    parser.add_argument("--include-hard-case", action="store_true", help="Include optional cheap hard case (Nu=3,Ns=4).")
    parser.add_argument("--run-promoted-medium", action="store_true", help="Run medium validation only for promoted variants.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> dict[str, Any]:
    """CLI entrypoint."""

    args = _parse_args(argv)
    plan = _planned_work(include_hard_case=args.include_hard_case, run_promoted_medium=args.run_promoted_medium)
    print(json.dumps(plan, indent=2))
    if args.dry_run:
        return plan
    payload = run_exploration(include_hard_case=args.include_hard_case, run_promoted_medium=args.run_promoted_medium)
    print(
        json.dumps(
            {
                "status": "wrote",
                "output_root": _repo_rel(OUTPUT_ROOT),
                "row_count": payload["row_count"],
                "promoted_variants": payload["promoted_variants"],
                "medium_validation_run": payload["medium_validation_run"],
            },
            indent=2,
        )
    )
    return payload


if __name__ == "__main__":
    main()
