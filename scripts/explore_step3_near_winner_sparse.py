"""Near-winner Step 3 sparse network exploration.

This diagnostic tests variants close to the micro-benchmark winner:
block-scaled covariance with a clock-drift state. It uses deterministic sparse
toy networks and does not run migration ladders, full grids, notebook code, or
manuscript figure generation.
"""

from __future__ import annotations

import argparse
import csv
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


OUTPUT_ROOT = SAT_SIM_ROOT / "outputs" / "step3_near_winner_sparse"
PLOT_ROOT = OUTPUT_ROOT / "plots"
REPORT_ROOT = SAT_SIM_ROOT / "outputs" / "reports"
DT_SECONDS = 0.5
EPOCHS = 3
SPARSE_CASES = [(3, 8), (7, 8), (7, 12)]
MEDIUM_CASES = [(nu, ns) for nu in (1, 3, 5, 7) for ns in (4, 8, 12)]
POSITION_RATIO_EPS_M = 1.0e-6
CLOCK_RATIO_EPS_KM = 1.0e-9


@dataclass(frozen=True)
class SparseCase:
    """One deterministic sparse network case."""

    name: str
    num_users: int
    num_satellites: int
    true_positions_km: np.ndarray
    step_b_positions_km: np.ndarray
    true_clocks_km: np.ndarray
    step_b_clocks_km: np.ndarray
    true_drifts_km_per_s: np.ndarray
    step_b_drifts_km_per_s: np.ndarray


@dataclass(frozen=True)
class NearWinnerVariant:
    """One near-winner Step 3 structural variant."""

    name: str
    description: str
    position_variance_km2: float
    ue_clock_variance_km2: float
    satellite_clock_variance_km2: float
    drift_variance_km2_per_s2: float
    include_drift_state: bool
    project_common_clock: bool = False
    schur_eliminate_clocks: bool = False
    clock_only: bool = False
    max_position_update_km: float | None = None
    max_ue_clock_update_km: float | None = None
    max_satellite_clock_update_km: float | None = None
    max_clock_drift_update_km_per_s: float | None = None
    measurement_sigma_km: float = 2.5e-4


VARIANTS = [
    NearWinnerVariant(
        name="block_scaled_drift_base",
        description="Typed position/clock/drift covariance blocks with clock drift state.",
        position_variance_km2=0.20**2,
        ue_clock_variance_km2=0.0025**2,
        satellite_clock_variance_km2=0.0025**2,
        drift_variance_km2_per_s2=0.0012**2,
        include_drift_state=True,
    ),
    NearWinnerVariant(
        name="block_scaled_drift_common_clock_projected",
        description="V1 plus common-clock/gauge update projection.",
        position_variance_km2=0.20**2,
        ue_clock_variance_km2=0.0025**2,
        satellite_clock_variance_km2=0.0025**2,
        drift_variance_km2_per_s2=0.0012**2,
        include_drift_state=True,
        project_common_clock=True,
    ),
    NearWinnerVariant(
        name="block_scaled_drift_blockwise_update_clip",
        description="V1 plus blockwise update clipping.",
        position_variance_km2=0.20**2,
        ue_clock_variance_km2=0.0025**2,
        satellite_clock_variance_km2=0.0025**2,
        drift_variance_km2_per_s2=0.0012**2,
        include_drift_state=True,
        max_position_update_km=0.010,
        max_ue_clock_update_km=0.0015,
        max_satellite_clock_update_km=0.0015,
        max_clock_drift_update_km_per_s=0.0010,
    ),
    NearWinnerVariant(
        name="block_scaled_drift_strong_clock_prior",
        description="V1 with stronger clock-bias and drift priors.",
        position_variance_km2=0.20**2,
        ue_clock_variance_km2=0.0010**2,
        satellite_clock_variance_km2=0.0010**2,
        drift_variance_km2_per_s2=0.0005**2,
        include_drift_state=True,
    ),
    NearWinnerVariant(
        name="block_scaled_drift_loose_clock_prior",
        description="V1 with looser clock-bias and drift priors.",
        position_variance_km2=0.20**2,
        ue_clock_variance_km2=0.0060**2,
        satellite_clock_variance_km2=0.0060**2,
        drift_variance_km2_per_s2=0.0030**2,
        include_drift_state=True,
    ),
    NearWinnerVariant(
        name="block_scaled_no_drift_common_clock_projected",
        description="Typed covariance without drift state plus common-clock projection.",
        position_variance_km2=0.20**2,
        ue_clock_variance_km2=0.0025**2,
        satellite_clock_variance_km2=0.0025**2,
        drift_variance_km2_per_s2=0.0,
        include_drift_state=False,
        project_common_clock=True,
    ),
    NearWinnerVariant(
        name="schur_nuisance_clock_reduced_block_scaled",
        description="Block-scaled Schur/reduced solve treating clocks as nuisance variables.",
        position_variance_km2=0.20**2,
        ue_clock_variance_km2=0.0025**2,
        satellite_clock_variance_km2=0.0025**2,
        drift_variance_km2_per_s2=0.0,
        include_drift_state=False,
        schur_eliminate_clocks=True,
    ),
    NearWinnerVariant(
        name="clock_only_step3_after_step_b",
        description="Freeze Step-B positions and refine only clock bias/drift.",
        position_variance_km2=0.20**2,
        ue_clock_variance_km2=0.0025**2,
        satellite_clock_variance_km2=0.0025**2,
        drift_variance_km2_per_s2=0.0012**2,
        include_drift_state=True,
        clock_only=True,
    ),
]


def _repo_rel(path: Path) -> str:
    return path.relative_to(SAT_SIM_ROOT).as_posix()


def _make_positions(num_users: int) -> np.ndarray:
    """Return deterministic 2D UE positions in km."""

    idx = np.arange(num_users, dtype=float)
    angles = 2.0 * np.pi * idx / max(num_users, 1)
    radius = 0.35 + 0.06 * (idx % 3)
    x = radius * np.cos(angles) + 0.04 * (idx % 2)
    y = radius * np.sin(angles) - 0.03 * ((idx + 1) % 2)
    return np.column_stack([x, y])


def _make_satellites(num_satellites: int) -> np.ndarray:
    """Return deterministic 2D satellite positions in km."""

    idx = np.arange(num_satellites, dtype=float)
    angles = 2.0 * np.pi * idx / max(num_satellites, 1) + 0.18
    radius = 18.0 + 1.5 * (idx % 4)
    return np.column_stack([radius * np.cos(angles), radius * np.sin(angles)])


def _clock_count(num_users: int, num_satellites: int) -> int:
    """Return number of estimated clocks with first satellite as reference."""

    return num_users + num_satellites - 1


def _make_clocks(num_users: int, num_satellites: int) -> np.ndarray:
    """Return deterministic UE and non-reference satellite clocks in km."""

    count = _clock_count(num_users, num_satellites)
    idx = np.arange(count, dtype=float)
    return 0.00075 * np.sin(0.71 * (idx + 1.0)) + 0.00035 * np.cos(0.37 * (idx + 2.0))


def _make_drifts(count: int) -> np.ndarray:
    """Return deterministic clock drift in km/s."""

    idx = np.arange(count, dtype=float)
    return 0.00018 * np.sin(0.43 * (idx + 1.0)) - 0.00011 * np.cos(0.29 * (idx + 3.0))


def _make_case(num_users: int, num_satellites: int) -> SparseCase:
    """Return a deterministic sparse network case with Step-B-like initial errors."""

    positions = _make_positions(num_users)
    clocks = _make_clocks(num_users, num_satellites)
    drifts = _make_drifts(clocks.size)
    user_idx = np.arange(num_users, dtype=float)
    pos_error = np.column_stack(
        [
            0.0025 * np.sin(1.3 * (user_idx + 1.0)),
            0.0020 * np.cos(0.9 * (user_idx + 2.0)),
        ]
    )
    clock_idx = np.arange(clocks.size, dtype=float)
    clock_error = 0.00028 * np.cos(0.51 * (clock_idx + 1.0))
    drift_error = -0.40 * drifts
    return SparseCase(
        name=f"Nu{num_users}_Ns{num_satellites}",
        num_users=num_users,
        num_satellites=num_satellites,
        true_positions_km=positions,
        step_b_positions_km=positions + pos_error,
        true_clocks_km=clocks,
        step_b_clocks_km=clocks + clock_error,
        true_drifts_km_per_s=drifts,
        step_b_drifts_km_per_s=drift_error,
    )


def sparse_cases() -> list[SparseCase]:
    """Return default sparse cases."""

    return [_make_case(num_users, num_satellites) for num_users, num_satellites in SPARSE_CASES]


def medium_cases() -> list[SparseCase]:
    """Return medium-validation cases."""

    return [_make_case(num_users, num_satellites) for num_users, num_satellites in MEDIUM_CASES]


def _position_slice(case: SparseCase) -> slice:
    return slice(0, 2 * case.num_users)


def _clock_slice(case: SparseCase) -> slice:
    start = 2 * case.num_users
    return slice(start, start + _clock_count(case.num_users, case.num_satellites))


def _drift_slice(case: SparseCase, variant: NearWinnerVariant) -> slice:
    start = 2 * case.num_users + _clock_count(case.num_users, case.num_satellites)
    count = _clock_count(case.num_users, case.num_satellites) if variant.include_drift_state else 0
    return slice(start, start + count)


def _pack_state(case: SparseCase, variant: NearWinnerVariant) -> np.ndarray:
    """Pack Step-B-like state for one case and variant."""

    pieces = [case.step_b_positions_km.reshape(-1), case.step_b_clocks_km]
    if variant.include_drift_state:
        pieces.append(case.step_b_drifts_km_per_s)
    return np.concatenate(pieces).astype(float)


def _unpack_state(theta: np.ndarray, case: SparseCase, variant: NearWinnerVariant) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Unpack positions, clocks, and optional drifts."""

    positions = theta[_position_slice(case)].reshape(case.num_users, 2)
    clocks = theta[_clock_slice(case)]
    if variant.include_drift_state:
        drifts = theta[_drift_slice(case, variant)]
    else:
        drifts = np.zeros_like(clocks)
    return positions, clocks, drifts


def _clock_index_for_node(node_id: int, num_users: int) -> int | None:
    """Return estimated-clock index for a node id, or None for the reference satellite."""

    reference_satellite = num_users
    if node_id < num_users:
        return node_id
    if node_id == reference_satellite:
        return None
    return num_users + (node_id - reference_satellite - 1)


def _links(case: SparseCase) -> list[tuple[int, int]]:
    """Return deterministic DL and SL receiver/transmitter node-id pairs."""

    links: list[tuple[int, int]] = []
    for ue in range(case.num_users):
        for sat in range(case.num_satellites):
            links.append((ue, case.num_users + sat))
    for ue in range(case.num_users):
        neighbor = (ue + 1) % case.num_users
        if ue != neighbor:
            links.append((ue, neighbor))
            links.append((neighbor, ue))
    return links


def _node_position(node_id: int, user_positions: np.ndarray, satellite_positions: np.ndarray, num_users: int) -> np.ndarray:
    """Return node position in km."""

    if node_id < num_users:
        return user_positions[node_id]
    return satellite_positions[node_id - num_users]


def _clock_value(clocks: np.ndarray, node_id: int, num_users: int) -> float:
    """Return clock value for a node, with the first satellite fixed to zero."""

    idx = _clock_index_for_node(node_id, num_users)
    if idx is None:
        return 0.0
    return float(clocks[idx])


def _measurements_and_jacobian(case: SparseCase, variant: NearWinnerVariant, theta: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return true measurements, predicted measurements, and local Jacobian."""

    est_positions, est_clocks, est_drifts = _unpack_state(theta, case, variant)
    sat_positions = _make_satellites(case.num_satellites)
    links = _links(case)
    state_dim = theta.size
    true_rows: list[float] = []
    pred_rows: list[float] = []
    jac_rows: list[np.ndarray] = []
    clock_offset = _clock_slice(case).start
    drift_offset = _drift_slice(case, variant).start
    for epoch in range(EPOCHS):
        t = epoch * DT_SECONDS
        true_clocks = case.true_clocks_km + t * case.true_drifts_km_per_s
        pred_clocks = est_clocks + t * est_drifts
        for receiver, transmitter in links:
            true_rx = _node_position(receiver, case.true_positions_km, sat_positions, case.num_users)
            true_tx = _node_position(transmitter, case.true_positions_km, sat_positions, case.num_users)
            pred_rx = _node_position(receiver, est_positions, sat_positions, case.num_users)
            pred_tx = _node_position(transmitter, est_positions, sat_positions, case.num_users)
            true_range = float(np.linalg.norm(true_rx - true_tx))
            pred_range = float(np.linalg.norm(pred_rx - pred_tx))
            true_value = true_range + _clock_value(true_clocks, transmitter, case.num_users) - _clock_value(true_clocks, receiver, case.num_users)
            pred_value = pred_range + _clock_value(pred_clocks, transmitter, case.num_users) - _clock_value(pred_clocks, receiver, case.num_users)
            row = np.zeros(state_dim, dtype=float)
            diff = pred_rx - pred_tx
            distance = max(float(np.linalg.norm(diff)), 1.0e-12)
            unit = diff / distance
            if receiver < case.num_users:
                row[2 * receiver : 2 * receiver + 2] += unit
            if transmitter < case.num_users:
                row[2 * transmitter : 2 * transmitter + 2] -= unit
            rx_clock = _clock_index_for_node(receiver, case.num_users)
            tx_clock = _clock_index_for_node(transmitter, case.num_users)
            if tx_clock is not None:
                row[clock_offset + tx_clock] += 1.0
                if variant.include_drift_state:
                    row[drift_offset + tx_clock] += t
            if rx_clock is not None:
                row[clock_offset + rx_clock] -= 1.0
                if variant.include_drift_state:
                    row[drift_offset + rx_clock] -= t
            true_rows.append(true_value)
            pred_rows.append(pred_value)
            jac_rows.append(row)
    return np.asarray(true_rows), np.asarray(pred_rows), np.vstack(jac_rows)


def _prior_variances(case: SparseCase, variant: NearWinnerVariant) -> np.ndarray:
    """Return diagonal prior variances in km/range-clock units."""

    position = np.full(2 * case.num_users, variant.position_variance_km2)
    clocks = np.empty(_clock_count(case.num_users, case.num_satellites), dtype=float)
    clocks[: case.num_users] = variant.ue_clock_variance_km2
    clocks[case.num_users :] = variant.satellite_clock_variance_km2
    pieces = [position, clocks]
    if variant.include_drift_state:
        pieces.append(np.full_like(clocks, variant.drift_variance_km2_per_s2))
    return np.concatenate(pieces)


def _block_norms(case: SparseCase, variant: NearWinnerVariant, update: np.ndarray, jacobian: np.ndarray) -> dict[str, float]:
    """Return blockwise update and gauge/nullspace diagnostics."""

    clock_update = update[_clock_slice(case)]
    ue_clock_update = clock_update[: case.num_users]
    satellite_clock_update = clock_update[case.num_users :]
    drift_update = update[_drift_slice(case, variant)] if variant.include_drift_state else np.asarray([], dtype=float)
    _, singular_values, vh = np.linalg.svd(jacobian, full_matrices=True)
    tol = max(jacobian.shape) * np.finfo(float).eps * (singular_values[0] if singular_values.size else 1.0)
    rank = int(np.sum(singular_values > tol))
    null_basis = vh.T[:, rank:]
    null_component = null_basis @ (null_basis.T @ update) if null_basis.size else np.zeros_like(update)
    return {
        "position_update_norm": float(np.linalg.norm(update[_position_slice(case)])),
        "ue_clock_bias_update_norm": float(np.linalg.norm(ue_clock_update)),
        "satellite_clock_bias_update_norm": float(np.linalg.norm(satellite_clock_update)),
        "clock_drift_update_norm": float(np.linalg.norm(drift_update)),
        "common_clock_update_component": abs(float(np.mean(clock_update))) if clock_update.size else 0.0,
        "nullspace_update_norm": float(np.linalg.norm(null_component)),
        "nullspace_update_ratio": float(np.linalg.norm(null_component) / max(np.linalg.norm(update), 1.0e-18)),
        "jacobian_rank": rank,
        "jacobian_nullity": int(jacobian.shape[1] - rank),
    }


def _project_common_clock(case: SparseCase, variant: NearWinnerVariant, update: np.ndarray) -> np.ndarray:
    """Remove common clock-bias component from the update."""

    adjusted = update.copy()
    clock_slice = _clock_slice(case)
    adjusted[clock_slice] -= float(np.mean(adjusted[clock_slice]))
    if variant.include_drift_state:
        drift_slice = _drift_slice(case, variant)
        adjusted[drift_slice] -= float(np.mean(adjusted[drift_slice]))
    return adjusted


def _clip_block(update: np.ndarray, slc: slice, limit: float | None) -> tuple[float, bool]:
    """Clip one update block in place and return scale plus clipped flag."""

    if limit is None:
        return 1.0, False
    norm = float(np.linalg.norm(update[slc]))
    if norm <= limit or norm == 0.0:
        return 1.0, False
    scale = float(limit / norm)
    update[slc] *= scale
    return scale, True


def _apply_clipping(case: SparseCase, variant: NearWinnerVariant, update: np.ndarray) -> dict[str, Any]:
    """Apply blockwise clipping and return metadata."""

    clock_slice = _clock_slice(case)
    ue_slice = slice(clock_slice.start, clock_slice.start + case.num_users)
    sat_slice = slice(clock_slice.start + case.num_users, clock_slice.stop)
    pos_scale, pos_clipped = _clip_block(update, _position_slice(case), variant.max_position_update_km)
    ue_scale, ue_clipped = _clip_block(update, ue_slice, variant.max_ue_clock_update_km)
    sat_scale, sat_clipped = _clip_block(update, sat_slice, variant.max_satellite_clock_update_km)
    drift_scale, drift_clipped = _clip_block(update, _drift_slice(case, variant), variant.max_clock_drift_update_km_per_s)
    return {
        "blockwise_clipping_enabled": any(
            limit is not None
            for limit in (
                variant.max_position_update_km,
                variant.max_ue_clock_update_km,
                variant.max_satellite_clock_update_km,
                variant.max_clock_drift_update_km_per_s,
            )
        ),
        "position_clip_scale": pos_scale,
        "ue_clock_clip_scale": ue_scale,
        "satellite_clock_clip_scale": sat_scale,
        "clock_drift_clip_scale": drift_scale,
        "position_clipped": pos_clipped,
        "ue_clock_clipped": ue_clipped,
        "satellite_clock_clipped": sat_clipped,
        "clock_drift_clipped": drift_clipped,
    }


def _schur_update(normal: np.ndarray, rhs: np.ndarray, case: SparseCase) -> tuple[np.ndarray, dict[str, Any]]:
    """Return Schur-style update with clock/drift variables as nuisance block."""

    pos = np.arange(_position_slice(case).start, _position_slice(case).stop)
    other = np.asarray([idx for idx in range(normal.shape[0]) if idx not in set(pos)], dtype=int)
    a_pp = normal[np.ix_(pos, pos)]
    a_po = normal[np.ix_(pos, other)]
    a_op = normal[np.ix_(other, pos)]
    a_oo = normal[np.ix_(other, other)]
    b_p = rhs[pos]
    b_o = rhs[other]
    inv_oo = np.linalg.pinv(a_oo, rcond=1.0e-10)
    reduced = a_pp - a_po @ inv_oo @ a_op
    reduced_rhs = b_p - a_po @ inv_oo @ b_o
    delta_p = np.linalg.pinv(reduced, rcond=1.0e-10) @ reduced_rhs
    delta_o = inv_oo @ (b_o - a_op @ delta_p)
    update = np.zeros(normal.shape[0], dtype=float)
    update[pos] = delta_p
    update[other] = delta_o
    return update, {
        "schur_reduced_dimension": int(reduced.shape[0]),
        "schur_nuisance_dimension": int(a_oo.shape[0]),
        "schur_reduced_rank": int(np.linalg.matrix_rank(reduced)),
    }


def _position_error_m(case: SparseCase, positions: np.ndarray) -> float:
    """Return average UE position error in meters."""

    return float(np.mean(np.linalg.norm(positions - case.true_positions_km, axis=1)) * 1000.0)


def _sync_error_km(case: SparseCase, clocks: np.ndarray, drifts: np.ndarray) -> float:
    """Return average epoch-expanded clock/sync error in km."""

    errors = []
    for epoch in range(EPOCHS):
        t = epoch * DT_SECONDS
        true = case.true_clocks_km + t * case.true_drifts_km_per_s
        est = clocks + t * drifts
        errors.extend(np.abs(est - true).tolist())
    return float(np.mean(errors))


def _evaluate_case_variant(case: SparseCase, variant: NearWinnerVariant, *, grid: str) -> dict[str, Any]:
    """Evaluate one sparse case and variant."""

    started = time.monotonic()
    theta0 = _pack_state(case, variant)
    z_true, z_pred, jacobian = _measurements_and_jacobian(case, variant, theta0)
    residual = z_true - z_pred
    sigma = np.full(z_true.size, variant.measurement_sigma_km)
    r_inv_diag = 1.0 / np.square(sigma)
    prior_var = _prior_variances(case, variant)
    p_inv_diag = 1.0 / np.maximum(prior_var, 1.0e-18)
    weighted_j = jacobian * r_inv_diag[:, None]
    normal = jacobian.T @ weighted_j + np.diag(p_inv_diag)
    rhs = jacobian.T @ (r_inv_diag * residual)
    schur_diag: dict[str, Any] = {
        "schur_reduced_dimension": 0,
        "schur_nuisance_dimension": 0,
        "schur_reduced_rank": 0,
    }
    if variant.schur_eliminate_clocks:
        update, schur_diag = _schur_update(normal, rhs, case)
    else:
        update = np.linalg.pinv(normal, rcond=1.0e-10) @ rhs
    raw_common_component = abs(float(np.mean(update[_clock_slice(case)])))
    if variant.project_common_clock:
        update = _project_common_clock(case, variant, update)
    clipping = _apply_clipping(case, variant, update)
    if variant.clock_only:
        update[_position_slice(case)] = 0.0
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
    prior_cost = float(np.sum(np.square(update) * p_inv_diag))
    objective_before = residual_cost_before
    objective_after = residual_cost_after + prior_cost
    norms = _block_norms(case, variant, update, jacobian)
    position_ratio = pos_after / max(pos_before, POSITION_RATIO_EPS_M)
    sync_ratio = sync_after / max(sync_before, CLOCK_RATIO_EPS_KM)
    position_improved = position_ratio < 1.0
    sync_improved = sync_ratio < 1.0
    row = {
        "grid": grid,
        "case_name": case.name,
        "num_users": case.num_users,
        "num_satellites": case.num_satellites,
        "variant": variant.name,
        "variant_description": variant.description,
        "runtime_seconds": time.monotonic() - started,
        "step_b_position_error_m": pos_before,
        "step3_position_error_m": pos_after,
        "step_b_sync_error_km": sync_before,
        "step3_sync_error_km": sync_after,
        "step_b_sync_error_s": sync_before / C_KM_PER_S,
        "step3_sync_error_s": sync_after / C_KM_PER_S,
        "position_ratio": position_ratio,
        "sync_ratio": sync_ratio,
        "position_improved": position_improved,
        "sync_improved": sync_improved,
        "both_improved": position_improved and sync_improved,
        "position_hurt_but_sync_helped": position_ratio > 1.0 and sync_improved,
        "sync_hurt_but_position_helped": sync_ratio > 1.0 and position_improved,
        "accepted_update_count": int(objective_after <= objective_before + 1.0e-9),
        "rejected_update_count": int(objective_after > objective_before + 1.0e-9),
        "objective_decreased": bool(objective_after <= objective_before + 1.0e-9),
        "objective_before": objective_before,
        "objective_after": objective_after,
        "residual_cost_before": residual_cost_before,
        "residual_cost_after": residual_cost_after,
        "prior_cost": prior_cost,
        "dynamics_cost": 0.0,
        "raw_common_clock_update_component": raw_common_component,
        "cache_status": "not_used_deterministic_sparse",
        "truth_state_used_for_acceptance": False,
        "truth_state_used_for_covariance": False,
        "truth_state_used_for_diagnostics": True,
        "medium_validation": grid == "medium",
        "network_size_graph": False,
        "full_ladder_run": False,
        "manuscript_ready": False,
        "not_for_manuscript_submission": True,
        **asdict(variant),
        **norms,
        **clipping,
        **schur_diag,
    }
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


def _variant_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return variant-level sparse summary."""

    output = []
    for variant in [item.name for item in VARIANTS]:
        subset = [row for row in rows if row["variant"] == variant and row["grid"] == "sparse"]
        if not subset:
            continue
        output.append(
            {
                "variant": variant,
                "tested_cases": len(subset),
                "both_improved_count": sum(1 for row in subset if row["both_improved"]),
                "position_improved_count": sum(1 for row in subset if row["position_improved"]),
                "sync_improved_count": sum(1 for row in subset if row["sync_improved"]),
                "position_hurt_but_sync_helped_count": sum(1 for row in subset if row["position_hurt_but_sync_helped"]),
                "sync_hurt_but_position_helped_count": sum(1 for row in subset if row["sync_hurt_but_position_helped"]),
                "mean_position_ratio": float(np.mean([row["position_ratio"] for row in subset])),
                "mean_sync_ratio": float(np.mean([row["sync_ratio"] for row in subset])),
                "max_position_ratio": float(np.max([row["position_ratio"] for row in subset])),
                "max_sync_ratio": float(np.max([row["sync_ratio"] for row in subset])),
                "mean_runtime_seconds": float(np.mean([row["runtime_seconds"] for row in subset])),
            }
        )
    return output


def _grid_summary(rows: list[dict[str, Any]], grid: str) -> list[dict[str, Any]]:
    """Return variant-level summary for a named grid."""

    output = []
    variants = sorted({row["variant"] for row in rows if row["grid"] == grid})
    for variant in variants:
        subset = [row for row in rows if row["grid"] == grid and row["variant"] == variant]
        output.append(
            {
                "grid": grid,
                "variant": variant,
                "tested_cases": len(subset),
                "both_improved_count": sum(1 for row in subset if row["both_improved"]),
                "position_improved_count": sum(1 for row in subset if row["position_improved"]),
                "sync_improved_count": sum(1 for row in subset if row["sync_improved"]),
                "mean_position_ratio": float(np.mean([row["position_ratio"] for row in subset])),
                "mean_sync_ratio": float(np.mean([row["sync_ratio"] for row in subset])),
                "max_position_ratio": float(np.max([row["position_ratio"] for row in subset])),
                "max_sync_ratio": float(np.max([row["sync_ratio"] for row in subset])),
            }
        )
    return output


def _promotion_candidates(summary_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Promote at most two variants by the sparse near-winner rule."""

    candidates = []
    for row in summary_rows:
        qualifies = (
            row["both_improved_count"] >= 2
            or (row["sync_improved_count"] >= 2 and row["max_position_ratio"] <= 1.10)
            or (row["position_improved_count"] >= 2 and row["max_sync_ratio"] <= 1.10)
        )
        if row["variant"] == "clock_only_step3_after_step_b":
            qualifies = row["sync_improved_count"] >= 2 and row["max_position_ratio"] <= 1.001
        if qualifies:
            score = row["mean_position_ratio"] + row["mean_sync_ratio"] - 0.20 * row["both_improved_count"]
            candidates.append({**row, "promotion_score": float(score)})
    return sorted(candidates, key=lambda item: (item["promotion_score"], item["variant"]))[:2]


def _best_variants(summary_rows: list[dict[str, Any]]) -> dict[str, str | None]:
    """Return best position, sync, and balanced variants."""

    if not summary_rows:
        return {"position": None, "sync": None, "balanced": None}
    position = min(summary_rows, key=lambda row: (row["mean_position_ratio"], row["mean_sync_ratio"]))
    sync = min(summary_rows, key=lambda row: (row["mean_sync_ratio"], row["mean_position_ratio"]))
    balanced = min(summary_rows, key=lambda row: (row["mean_position_ratio"] + row["mean_sync_ratio"], row["variant"]))
    return {"position": position["variant"], "sync": sync["variant"], "balanced": balanced["variant"]}


def _write_variant_diagnostics(rows: list[dict[str, Any]]) -> list[str]:
    """Write per-variant diagnostics JSON files."""

    paths = []
    root = OUTPUT_ROOT / "diagnostics"
    for variant in [item.name for item in VARIANTS]:
        subset = [row for row in rows if row["variant"] == variant]
        paths.append(_write_json(root / f"{variant}.json", {"variant": variant, "rows": subset}))
    return paths


def _plot_scatter(rows: list[dict[str, Any]]) -> list[str]:
    """Write position-ratio versus sync-ratio scatter."""

    PLOT_ROOT.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7.0, 4.8))
    sparse = [row for row in rows if row["grid"] == "sparse"]
    for variant in [item.name for item in VARIANTS]:
        subset = [row for row in sparse if row["variant"] == variant]
        ax.scatter([row["position_ratio"] for row in subset], [row["sync_ratio"] for row in subset], label=variant, s=28, alpha=0.75)
    ax.axvline(1.0, color="0.5", linewidth=0.8)
    ax.axhline(1.0, color="0.5", linewidth=0.8)
    ax.set_xlabel("Position ratio Step3 / StepB")
    ax.set_ylabel("Sync ratio Step3 / StepB")
    ax.set_title("Sparse near-winner Step 3 variants")
    ax.legend(fontsize=5, ncol=2)
    fig.tight_layout()
    outputs = []
    for suffix in ("pdf", "png"):
        path = PLOT_ROOT / f"position_sync_ratio_scatter.{suffix}"
        fig.savefig(path)
        outputs.append(_repo_rel(path))
    plt.close(fig)
    return outputs


def _plot_both_improved(summary_rows: list[dict[str, Any]]) -> list[str]:
    """Write both-improved count bar chart."""

    fig, ax = plt.subplots(figsize=(8.0, 4.2))
    labels = [row["variant"].replace("block_scaled_", "").replace("_", "\n") for row in summary_rows]
    values = [row["both_improved_count"] for row in summary_rows]
    ax.bar(range(len(labels)), values, color="#4C78A8")
    ax.set_xticks(range(len(labels)), labels, rotation=0, fontsize=6)
    ax.set_ylabel("Both-improved cases")
    ax.set_ylim(0, 3)
    ax.set_title("Both-improved count by variant")
    fig.tight_layout()
    outputs = []
    for suffix in ("pdf", "png"):
        path = PLOT_ROOT / f"both_improved_count_by_variant.{suffix}"
        fig.savefig(path)
        outputs.append(_repo_rel(path))
    plt.close(fig)
    return outputs


def _plot_heatmap(rows: list[dict[str, Any]], metric: str, stem: str, title: str) -> list[str]:
    """Write per-case ratio heatmap."""

    sparse = [row for row in rows if row["grid"] == "sparse"]
    cases = [f"Nu{nu}_Ns{ns}" for nu, ns in SPARSE_CASES]
    variants = [item.name for item in VARIANTS]
    matrix = np.full((len(variants), len(cases)), np.nan)
    for row in sparse:
        matrix[variants.index(row["variant"]), cases.index(row["case_name"])] = row[metric]
    fig, ax = plt.subplots(figsize=(6.4, 5.0))
    image = ax.imshow(matrix, cmap="viridis_r", vmin=0.0, vmax=max(1.5, float(np.nanmax(matrix))))
    ax.set_xticks(range(len(cases)), cases, rotation=30, ha="right")
    ax.set_yticks(range(len(variants)), [variant.replace("block_scaled_", "").replace("_", " ") for variant in variants], fontsize=6)
    ax.set_title(title)
    fig.colorbar(image, ax=ax, label=metric)
    for y in range(matrix.shape[0]):
        for x in range(matrix.shape[1]):
            ax.text(x, y, f"{matrix[y, x]:.2f}", ha="center", va="center", color="white", fontsize=6)
    fig.tight_layout()
    outputs = []
    for suffix in ("pdf", "png"):
        path = PLOT_ROOT / f"{stem}.{suffix}"
        fig.savefig(path)
        outputs.append(_repo_rel(path))
    plt.close(fig)
    return outputs


def _plot_update_norms(rows: list[dict[str, Any]]) -> list[str]:
    """Write update norm by block chart."""

    sparse = [row for row in rows if row["grid"] == "sparse"]
    summary = []
    for variant in [item.name for item in VARIANTS]:
        subset = [row for row in sparse if row["variant"] == variant]
        summary.append(
            [
                np.mean([row["position_update_norm"] for row in subset]),
                np.mean([row["ue_clock_bias_update_norm"] for row in subset]),
                np.mean([row["satellite_clock_bias_update_norm"] for row in subset]),
                np.mean([row["clock_drift_update_norm"] for row in subset]),
            ]
        )
    matrix = np.asarray(summary)
    labels = ["position", "UE clock", "sat clock", "drift"]
    fig, ax = plt.subplots(figsize=(8.0, 4.3))
    x = np.arange(len(VARIANTS))
    width = 0.18
    for idx, label in enumerate(labels):
        ax.bar(x + (idx - 1.5) * width, matrix[:, idx], width=width, label=label)
    ax.set_xticks(x, [variant.name.replace("block_scaled_", "").replace("_", "\n") for variant in VARIANTS], fontsize=6)
    ax.set_ylabel("Mean update norm")
    ax.set_title("Update norm by block")
    ax.legend(fontsize=7)
    fig.tight_layout()
    outputs = []
    for suffix in ("pdf", "png"):
        path = PLOT_ROOT / f"update_norm_by_block.{suffix}"
        fig.savefig(path)
        outputs.append(_repo_rel(path))
    plt.close(fig)
    return outputs


def _plot_runtime(summary_rows: list[dict[str, Any]]) -> list[str]:
    """Write runtime by variant."""

    fig, ax = plt.subplots(figsize=(8.0, 4.1))
    labels = [row["variant"].replace("block_scaled_", "").replace("_", "\n") for row in summary_rows]
    values = [row["mean_runtime_seconds"] for row in summary_rows]
    ax.bar(range(len(labels)), values, color="#59A14F")
    ax.set_xticks(range(len(labels)), labels, fontsize=6)
    ax.set_ylabel("Mean runtime [s]")
    ax.set_title("Runtime by variant")
    fig.tight_layout()
    outputs = []
    for suffix in ("pdf", "png"):
        path = PLOT_ROOT / f"runtime_by_variant.{suffix}"
        fig.savefig(path)
        outputs.append(_repo_rel(path))
    plt.close(fig)
    return outputs


def _write_plots(rows: list[dict[str, Any]], summary_rows: list[dict[str, Any]]) -> list[str]:
    """Write compact diagnostic plots."""

    outputs = []
    outputs.extend(_plot_scatter(rows))
    outputs.extend(_plot_both_improved(summary_rows))
    outputs.extend(_plot_heatmap(rows, "position_ratio", "position_ratio_heatmap", "Position ratio by sparse case"))
    outputs.extend(_plot_heatmap(rows, "sync_ratio", "sync_ratio_heatmap", "Sync ratio by sparse case"))
    outputs.extend(_plot_update_norms(rows))
    outputs.extend(_plot_runtime(summary_rows))
    return outputs


def _write_report(payload: dict[str, Any]) -> None:
    """Write Markdown and JSON report pair."""

    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    _write_json(REPORT_ROOT / "STEP3_NEAR_WINNER_SPARSE_REPORT.json", payload)
    md = [
        "# Step 3 Near-Winner Sparse Report",
        "",
        "## Executive Summary",
        "",
        f"- Artifact status: `{payload['artifact_status']}`",
        f"- Runtime seconds: `{payload['runtime_seconds']:.3f}`",
        f"- Sparse cases: `{payload['sparse_cases_tested']}`",
        f"- Variants tested: `{payload['variants_tested']}`",
        f"- Promoted variants: `{payload['promoted_variants']}`",
        f"- Medium validation run: `{payload['medium_validation_run']}`",
        "",
        "## Best Variants",
        "",
        f"- Best position variant: `{payload['best_variants']['position']}`",
        f"- Best synchronization variant: `{payload['best_variants']['sync']}`",
        f"- Best balanced variant: `{payload['best_variants']['balanced']}`",
        f"- Clock-only Step 3 promising: `{payload['clock_only_step3_promising']}`",
        f"- Drift helps: `{payload['drift_helps']}`",
        f"- Common-clock projection helps: `{payload['common_clock_projection_helps']}`",
        f"- Schur/nuisance-clock reduction helps: `{payload['schur_reduction_helps']}`",
        "",
        "## Variant Summary",
        "",
        "| Variant | Both improved | Position improved | Sync improved | Mean pos ratio | Mean sync ratio |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for item in payload["summary"]:
        md.append(
            f"| `{item['variant']}` | {item['both_improved_count']}/{item['tested_cases']} | "
            f"{item['position_improved_count']}/{item['tested_cases']} | "
            f"{item['sync_improved_count']}/{item['tested_cases']} | "
            f"{item['mean_position_ratio']:.4g} | {item['mean_sync_ratio']:.4g} |"
        )
    if payload["medium_validation_summary"]:
        md += [
            "",
            "## Medium Validation Summary",
            "",
            "| Variant | Both improved | Position improved | Sync improved | Mean pos ratio | Mean sync ratio |",
            "|---|---:|---:|---:|---:|---:|",
        ]
        for item in payload["medium_validation_summary"]:
            md.append(
                f"| `{item['variant']}` | {item['both_improved_count']}/{item['tested_cases']} | "
                f"{item['position_improved_count']}/{item['tested_cases']} | "
                f"{item['sync_improved_count']}/{item['tested_cases']} | "
                f"{item['mean_position_ratio']:.4g} | {item['mean_sync_ratio']:.4g} |"
            )
    md += [
        "",
        "## Interpretation",
        "",
        payload["interpretation"],
        "",
        "## Output Paths",
        "",
        f"- Raw CSV: `{payload['raw_csv']}`",
        f"- Summary CSV: `{payload['summary_csv']}`",
        f"- Metadata JSON: `{payload['metadata_json']}`",
        "- Plots:",
        *[f"  - `{path}`" for path in payload["plots"]],
    ]
    (REPORT_ROOT / "STEP3_NEAR_WINNER_SPARSE_REPORT.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def _run_rows(cases: list[SparseCase], variants: list[NearWinnerVariant], *, grid: str) -> list[dict[str, Any]]:
    """Run rows for a case/variant grid."""

    return [_evaluate_case_variant(case, variant, grid=grid) for case in cases for variant in variants]


def _planned_work(*, run_medium: bool) -> dict[str, Any]:
    """Return planned work metadata."""

    return {
        "artifact_status": "non_final_step3_near_winner_sparse_planned_work",
        "sparse_cases": [{"num_users": nu, "num_satellites": ns} for nu, ns in SPARSE_CASES],
        "variants": [variant.name for variant in VARIANTS],
        "sparse_row_count": len(SPARSE_CASES) * len(VARIANTS),
        "run_promoted_medium": run_medium,
        "network_size_graphs_run": False,
        "full_ladder_run": False,
        "medium_grid_default": False,
    }


def _interpret_results(summary_rows: list[dict[str, Any]], promoted: list[dict[str, Any]]) -> dict[str, Any]:
    """Return qualitative result flags."""

    by_name = {row["variant"]: row for row in summary_rows}
    drift = by_name.get("block_scaled_drift_base")
    no_drift = by_name.get("block_scaled_no_drift_common_clock_projected")
    projection = by_name.get("block_scaled_drift_common_clock_projected")
    schur = by_name.get("schur_nuisance_clock_reduced_block_scaled")
    clock_only = by_name.get("clock_only_step3_after_step_b")
    drift_helps = bool(drift and no_drift and drift["mean_sync_ratio"] < no_drift["mean_sync_ratio"])
    common_clock_helps = bool(projection and drift and projection["mean_sync_ratio"] <= drift["mean_sync_ratio"] and projection["mean_position_ratio"] <= 1.10 * drift["mean_position_ratio"])
    schur_helps = bool(schur and drift and schur["mean_position_ratio"] <= drift["mean_position_ratio"] and schur["mean_sync_ratio"] <= 1.10 * drift["mean_sync_ratio"])
    clock_only_promising = bool(clock_only and clock_only["sync_improved_count"] >= 2 and clock_only["max_position_ratio"] <= 1.001)
    return {
        "drift_helps": drift_helps,
        "common_clock_projection_helps": common_clock_helps,
        "schur_reduction_helps": schur_helps,
        "clock_only_step3_promising": clock_only_promising,
        "next_recommended_action": (
            "review promoted near-winner variants for sparse-network validation"
            if promoted
            else "keep Step B/LM-only baseline and redesign Step 3 before larger validation"
        ),
    }


def run_exploration(*, run_promoted_medium: bool) -> dict[str, Any]:
    """Run sparse near-winner exploration and optional promoted medium validation."""

    started = time.monotonic()
    sparse_rows = _run_rows(sparse_cases(), VARIANTS, grid="sparse")
    summary_rows = _variant_summary(sparse_rows)
    sparse_grid_summary = _grid_summary(sparse_rows, "sparse")
    promoted = _promotion_candidates(summary_rows)
    medium_rows: list[dict[str, Any]] = []
    if run_promoted_medium and promoted:
        promoted_names = {item["variant"] for item in promoted}
        medium_variants = [variant for variant in VARIANTS if variant.name in promoted_names]
        medium_rows = _run_rows(medium_cases(), medium_variants, grid="medium")
        for variant in medium_variants:
            variant_rows = [row for row in medium_rows if row["variant"] == variant.name]
            root = OUTPUT_ROOT / "medium_validation" / variant.name
            _write_csv(root / "raw.csv", variant_rows)
            _write_json(root / "metadata.json", {"variant": variant.name, "rows": variant_rows, "manuscript_ready": False})
    all_rows = sparse_rows + medium_rows
    medium_summary = _grid_summary(all_rows, "medium") if medium_rows else []
    raw_csv = _write_csv(OUTPUT_ROOT / "raw.csv", all_rows)
    summary_csv = _write_csv(OUTPUT_ROOT / "summary.csv", summary_rows)
    diagnostic_paths = _write_variant_diagnostics(all_rows)
    plots = _write_plots(all_rows, summary_rows)
    best = _best_variants(summary_rows)
    interpretation_flags = _interpret_results(summary_rows, promoted)
    metadata = {
        "artifact_status": "non_final_step3_near_winner_sparse",
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
        "sparse_cases_tested": [case.name for case in sparse_cases()],
        "medium_cases_tested": [case.name for case in medium_cases()] if medium_rows else [],
        "variants_tested": [variant.name for variant in VARIANTS],
        "promoted_variants": [item["variant"] for item in promoted],
        "row_count": len(all_rows),
        "sparse_row_count": len(sparse_rows),
        "medium_row_count": len(medium_rows),
        "runtime_seconds": time.monotonic() - started,
        "raw_csv": raw_csv,
        "summary_csv": summary_csv,
        "diagnostic_json_paths": diagnostic_paths,
        "plots": plots,
        "summary": summary_rows,
        "sparse_grid_summary": sparse_grid_summary,
        "medium_validation_summary": medium_summary,
        "rows": all_rows,
        "best_variants": best,
        "interpretation": "Sparse diagnostics test whether the micro-benchmark near-winner family transfers to representative network cases. These outputs are non-final and are not manuscript figures.",
        **interpretation_flags,
    }
    metadata_json = _write_json(OUTPUT_ROOT / "metadata.json", metadata)
    payload = {**metadata, "metadata_json": metadata_json}
    _write_report(payload)
    return payload


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Print planned work without executing.")
    parser.add_argument("--run-promoted-medium", action="store_true", help="Run medium validation for at most two promoted variants.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> dict[str, Any]:
    """CLI entrypoint."""

    args = _parse_args(argv)
    plan = _planned_work(run_medium=args.run_promoted_medium)
    print(json.dumps(plan, indent=2))
    if args.dry_run:
        return {**plan, "will_execute": False}
    payload = run_exploration(run_promoted_medium=args.run_promoted_medium)
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
