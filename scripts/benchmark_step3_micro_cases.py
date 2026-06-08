"""Deterministic Step 3 micro-benchmarks for matrix/filter formulation checks.

The cases here are intentionally tiny. They isolate Step 3 update behavior in
linearized range/clock systems without running legacy notebooks, migration
ladders, network-size graphs, or Monte Carlo sweeps.
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


OUTPUT_ROOT = SAT_SIM_ROOT / "outputs" / "step3_micro_benchmarks"
PLOT_ROOT = OUTPUT_ROOT / "plots"
REPORT_ROOT = SAT_SIM_ROOT / "outputs" / "reports"
DT_SECONDS = 0.5
POSITION_RATIO_EPS_M = 1.0e-6
CLOCK_RATIO_EPS_KM = 1.0e-9


@dataclass(frozen=True)
class MicroCase:
    """One deterministic micro-benchmark case."""

    name: str
    description: str
    expected_behavior: str
    true_positions_km: np.ndarray
    estimate_positions_km: np.ndarray
    true_clocks_km: np.ndarray
    estimate_clocks_km: np.ndarray
    true_drifts_km_per_s: np.ndarray
    estimate_drifts_km_per_s: np.ndarray
    num_satellites: int = 4
    epochs: int = 1
    include_reference_downlink: bool = True


@dataclass(frozen=True)
class Variant:
    """One Step 3 structural variant."""

    name: str
    description: str
    position_variance_km2: float
    ue_clock_variance_km2: float
    satellite_clock_variance_km2: float
    drift_variance_km2_per_s2: float = 0.0
    measurement_sigma_km: float = 1.0e-4
    include_drift_state: bool = False
    project_common_clock: bool = False
    schur_eliminate_clocks: bool = False
    clock_only: bool = False


VARIANTS = [
    Variant(
        name="baseline_c5_current_cov",
        description="Current simple no-drift covariance proxy.",
        position_variance_km2=10.0**2,
        ue_clock_variance_km2=0.1**2,
        satellite_clock_variance_km2=0.1**2,
    ),
    Variant(
        name="block_scaled_no_drift",
        description="Typed position/clock covariance without drift state.",
        position_variance_km2=0.4**2,
        ue_clock_variance_km2=0.003**2,
        satellite_clock_variance_km2=0.003**2,
    ),
    Variant(
        name="block_scaled_with_clock_drift",
        description="Typed covariance with clock drift state.",
        position_variance_km2=0.4**2,
        ue_clock_variance_km2=0.003**2,
        satellite_clock_variance_km2=0.003**2,
        drift_variance_km2_per_s2=0.002**2,
        include_drift_state=True,
    ),
    Variant(
        name="gauge_common_clock_projected",
        description="Typed covariance with common-clock update projection.",
        position_variance_km2=0.4**2,
        ue_clock_variance_km2=0.003**2,
        satellite_clock_variance_km2=0.003**2,
        project_common_clock=True,
    ),
    Variant(
        name="schur_nuisance_clock_reduced",
        description="Schur-style solve with clock nuisance block elimination.",
        position_variance_km2=0.4**2,
        ue_clock_variance_km2=0.003**2,
        satellite_clock_variance_km2=0.003**2,
        schur_eliminate_clocks=True,
    ),
    Variant(
        name="clock_only_filter",
        description="Conservative clock-only update with frozen positions.",
        position_variance_km2=0.4**2,
        ue_clock_variance_km2=0.003**2,
        satellite_clock_variance_km2=0.003**2,
        clock_only=True,
    ),
]


SAT_POSITIONS_KM = np.asarray(
    [
        [0.0, 20.0],
        [18.0, 8.0],
        [-15.0, 12.0],
        [7.0, -18.0],
        [-20.0, -6.0],
        [22.0, -12.0],
    ],
    dtype=float,
)


def _base_positions(num_users: int) -> np.ndarray:
    """Return deterministic UE positions in km."""

    return np.asarray([[0.0, 0.0], [1.2, 0.4], [-0.7, 1.1]], dtype=float)[:num_users]


def _base_clocks(num_users: int, num_satellites: int) -> np.ndarray:
    """Return deterministic non-reference clock offsets in km."""

    return np.asarray([0.0008, -0.0005, 0.0003, -0.0002, 0.00045, -0.00035, 0.00025, -0.00015], dtype=float)[: num_users + num_satellites - 1]


def _micro_cases() -> list[MicroCase]:
    """Return all deterministic micro-benchmark cases."""

    num_users = 2
    num_satellites = 4
    positions = _base_positions(num_users)
    clocks = _base_clocks(num_users, num_satellites)
    zeros = np.zeros_like(clocks)
    pos_perturb = np.asarray([[0.004, -0.002], [-0.003, 0.003]], dtype=float)
    clock_perturb = np.asarray([0.00045, -0.00035, 0.00025, -0.0002, 0.00015], dtype=float)
    drift = np.asarray([0.00020, -0.00015, 0.00010, -0.00008, 0.00006], dtype=float)
    return [
        MicroCase(
            name="clock_only_correction",
            description="Positions are correct; clock estimates are biased.",
            expected_behavior="clock improves and position update remains small",
            true_positions_km=positions,
            estimate_positions_km=positions.copy(),
            true_clocks_km=clocks,
            estimate_clocks_km=clocks + clock_perturb,
            true_drifts_km_per_s=zeros,
            estimate_drifts_km_per_s=zeros,
            num_satellites=num_satellites,
        ),
        MicroCase(
            name="position_only_correction",
            description="Clocks are correct; UE positions are perturbed.",
            expected_behavior="position improves and clock update remains small",
            true_positions_km=positions,
            estimate_positions_km=positions + pos_perturb,
            true_clocks_km=clocks,
            estimate_clocks_km=clocks.copy(),
            true_drifts_km_per_s=zeros,
            estimate_drifts_km_per_s=zeros,
            num_satellites=num_satellites,
        ),
        MicroCase(
            name="clock_drift_correction",
            description="Clock biases evolve over three epochs with known drift.",
            expected_behavior="drift-state model beats no-drift clock prediction",
            true_positions_km=positions,
            estimate_positions_km=positions.copy(),
            true_clocks_km=clocks,
            estimate_clocks_km=clocks + 0.5 * clock_perturb,
            true_drifts_km_per_s=drift,
            estimate_drifts_km_per_s=zeros,
            num_satellites=num_satellites,
            epochs=3,
        ),
        MicroCase(
            name="gauge_common_clock_perturbation",
            description="All estimated non-reference clocks include a common offset in a reference-free link set.",
            expected_behavior="common-clock update component is not chased",
            true_positions_km=positions,
            estimate_positions_km=positions.copy(),
            true_clocks_km=clocks,
            estimate_clocks_km=clocks + 0.0005,
            true_drifts_km_per_s=zeros,
            estimate_drifts_km_per_s=zeros,
            num_satellites=num_satellites,
            include_reference_downlink=False,
        ),
        MicroCase(
            name="mixed_position_clock_perturbation",
            description="Positions and clocks are both perturbed.",
            expected_behavior="variant improves both metrics or exposes tradeoff",
            true_positions_km=positions,
            estimate_positions_km=positions + 0.7 * pos_perturb,
            true_clocks_km=clocks,
            estimate_clocks_km=clocks + 0.7 * clock_perturb,
            true_drifts_km_per_s=zeros,
            estimate_drifts_km_per_s=zeros,
            num_satellites=num_satellites,
        ),
        MicroCase(
            name="schur_nuisance_clock_toy",
            description="Mixed perturbation used to compare reduced and full joint updates.",
            expected_behavior="Schur/nuisance-clock update remains finite and interpretable",
            true_positions_km=positions,
            estimate_positions_km=positions + 0.5 * pos_perturb,
            true_clocks_km=clocks,
            estimate_clocks_km=clocks + 0.5 * clock_perturb,
            true_drifts_km_per_s=zeros,
            estimate_drifts_km_per_s=zeros,
            num_satellites=num_satellites,
        ),
    ]


def _clock_count(case: MicroCase) -> int:
    """Return number of estimated clocks: UE clocks plus non-reference satellites."""

    return case.true_positions_km.shape[0] + case.num_satellites - 1


def _position_slice(case: MicroCase) -> slice:
    return slice(0, 2 * case.true_positions_km.shape[0])


def _clock_slice(case: MicroCase) -> slice:
    start = 2 * case.true_positions_km.shape[0]
    return slice(start, start + _clock_count(case))


def _drift_slice(case: MicroCase, variant: Variant) -> slice:
    start = 2 * case.true_positions_km.shape[0] + _clock_count(case)
    return slice(start, start + (_clock_count(case) if variant.include_drift_state else 0))


def _pack_state(positions: np.ndarray, clocks: np.ndarray, drifts: np.ndarray | None = None) -> np.ndarray:
    """Pack positions, clocks, and optional drifts."""

    parts = [np.asarray(positions, dtype=float).reshape(-1), np.asarray(clocks, dtype=float).reshape(-1)]
    if drifts is not None:
        parts.append(np.asarray(drifts, dtype=float).reshape(-1))
    return np.concatenate(parts)


def _unpack_state(theta: np.ndarray, case: MicroCase, variant: Variant) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Unpack a state vector."""

    num_users = case.true_positions_km.shape[0]
    positions = theta[_position_slice(case)].reshape(num_users, 2)
    clocks = theta[_clock_slice(case)]
    if variant.include_drift_state:
        drifts = theta[_drift_slice(case, variant)]
    else:
        drifts = np.zeros(_clock_count(case))
    return positions, clocks, drifts


def _clock_index(num_users: int, node_type: str, node_index: int) -> int | None:
    """Return clock index for UE or satellite nodes."""

    if node_type == "ue":
        return node_index
    if node_index == 0:
        return None
    return num_users + node_index - 1


def _clock_value(clocks: np.ndarray, drifts: np.ndarray, clock_index: int | None, epoch: int) -> float:
    """Return clock value in km for one clock index and epoch."""

    if clock_index is None:
        return 0.0
    return float(clocks[clock_index] + drifts[clock_index] * DT_SECONDS * epoch)


def _links(case: MicroCase) -> list[tuple[str, int, str, int]]:
    """Return receiver/transmitter links."""

    num_users = case.true_positions_km.shape[0]
    links: list[tuple[str, int, str, int]] = []
    sat_start = 0 if case.include_reference_downlink else 1
    for user in range(num_users):
        for sat in range(sat_start, case.num_satellites):
            links.append(("ue", user, "sat", sat))
    for rx in range(num_users):
        for tx in range(num_users):
            if rx != tx:
                links.append(("ue", rx, "ue", tx))
    return links


def _node_position(case: MicroCase, positions: np.ndarray, node_type: str, node_index: int) -> np.ndarray:
    """Return node position in km."""

    if node_type == "ue":
        return positions[node_index]
    return SAT_POSITIONS_KM[node_index]


def _measurements_and_jacobian(case: MicroCase, variant: Variant, theta: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return true measurements, predicted measurements, and Jacobian."""

    est_positions, est_clocks, est_drifts = _unpack_state(theta, case, variant)
    true_positions = case.true_positions_km
    true_clocks = case.true_clocks_km
    true_drifts = case.true_drifts_km_per_s
    rows = []
    z_true = []
    z_pred = []
    num_users = true_positions.shape[0]
    state_dim = theta.size
    for epoch in range(case.epochs):
        for rx_type, rx_idx, tx_type, tx_idx in _links(case):
            true_rx_pos = _node_position(case, true_positions, rx_type, rx_idx)
            true_tx_pos = _node_position(case, true_positions, tx_type, tx_idx)
            est_rx_pos = _node_position(case, est_positions, rx_type, rx_idx)
            est_tx_pos = _node_position(case, est_positions, tx_type, tx_idx)
            true_range = float(np.linalg.norm(true_rx_pos - true_tx_pos))
            est_range = float(np.linalg.norm(est_rx_pos - est_tx_pos))
            rx_clock_idx = _clock_index(num_users, rx_type, rx_idx)
            tx_clock_idx = _clock_index(num_users, tx_type, tx_idx)
            true_clock_term = _clock_value(true_clocks, true_drifts, tx_clock_idx, epoch) - _clock_value(true_clocks, true_drifts, rx_clock_idx, epoch)
            est_clock_term = _clock_value(est_clocks, est_drifts, tx_clock_idx, epoch) - _clock_value(est_clocks, est_drifts, rx_clock_idx, epoch)
            z_true.append(true_range + true_clock_term)
            z_pred.append(est_range + est_clock_term)
            row = np.zeros(state_dim)
            if est_range > 1.0e-12:
                direction = (est_rx_pos - est_tx_pos) / est_range
                if rx_type == "ue":
                    row[2 * rx_idx : 2 * rx_idx + 2] += direction
                if tx_type == "ue":
                    row[2 * tx_idx : 2 * tx_idx + 2] -= direction
            clock_start = _clock_slice(case).start
            drift_start = _drift_slice(case, variant).start
            for clock_idx, sign in ((tx_clock_idx, 1.0), (rx_clock_idx, -1.0)):
                if clock_idx is None:
                    continue
                row[clock_start + clock_idx] += sign
                if variant.include_drift_state:
                    row[drift_start + clock_idx] += sign * DT_SECONDS * epoch
            rows.append(row)
    return np.asarray(z_true), np.asarray(z_pred), np.vstack(rows)


def _prior_variances(case: MicroCase, variant: Variant) -> np.ndarray:
    """Return diagonal prior variances for the packed state."""

    num_users = case.true_positions_km.shape[0]
    clock_count = _clock_count(case)
    position_vars = np.full(2 * num_users, variant.position_variance_km2)
    clock_vars = np.empty(clock_count)
    clock_vars[:num_users] = variant.ue_clock_variance_km2
    clock_vars[num_users:] = variant.satellite_clock_variance_km2
    parts = [position_vars, clock_vars]
    if variant.include_drift_state:
        parts.append(np.full(clock_count, variant.drift_variance_km2_per_s2))
    return np.maximum(np.concatenate(parts), 1.0e-18)


def _solve_update(normal: np.ndarray, rhs: np.ndarray, case: MicroCase, variant: Variant) -> np.ndarray:
    """Solve full or Schur-reduced normal equations."""

    if not variant.schur_eliminate_clocks:
        return np.linalg.pinv(normal) @ rhs
    position_idx = np.arange(_position_slice(case).start, _position_slice(case).stop)
    clock_idx = np.arange(_clock_slice(case).start, _clock_slice(case).stop)
    other_idx = np.arange(_drift_slice(case, variant).start, _drift_slice(case, variant).stop)
    nuisance_idx = np.concatenate([clock_idx, other_idx])
    if nuisance_idx.size == 0:
        return np.linalg.pinv(normal) @ rhs
    app = normal[np.ix_(position_idx, position_idx)]
    apc = normal[np.ix_(position_idx, nuisance_idx)]
    acp = normal[np.ix_(nuisance_idx, position_idx)]
    acc = normal[np.ix_(nuisance_idx, nuisance_idx)]
    bp = rhs[position_idx]
    bc = rhs[nuisance_idx]
    acc_inv = np.linalg.pinv(acc)
    reduced = app - apc @ acc_inv @ acp
    reduced_rhs = bp - apc @ acc_inv @ bc
    delta_pos = np.linalg.pinv(reduced) @ reduced_rhs
    delta_clock = acc_inv @ (bc - acp @ delta_pos)
    delta = np.zeros_like(rhs)
    delta[position_idx] = delta_pos
    delta[nuisance_idx] = delta_clock
    return delta


def _apply_variant(case: MicroCase, variant: Variant) -> dict[str, Any]:
    """Run one case/variant pair."""

    theta0 = _pack_state(
        case.estimate_positions_km,
        case.estimate_clocks_km,
        case.estimate_drifts_km_per_s if variant.include_drift_state else None,
    )
    z_true, z_pred, jacobian = _measurements_and_jacobian(case, variant, theta0)
    residual = z_true - z_pred
    sigma = np.full(residual.size, variant.measurement_sigma_km)
    r_inv = np.diag(1.0 / np.maximum(sigma**2, 1.0e-18))
    p_vars = _prior_variances(case, variant)
    p_inv = np.diag(1.0 / p_vars)
    normal = jacobian.T @ r_inv @ jacobian + p_inv
    rhs = jacobian.T @ r_inv @ residual
    delta = _solve_update(normal, rhs, case, variant)
    if variant.clock_only:
        delta[_position_slice(case)] = 0.0
    if variant.project_common_clock:
        clock_slice = _clock_slice(case)
        delta[clock_slice] -= float(np.mean(delta[clock_slice]))
    theta1 = theta0 + delta
    _, z_after, _ = _measurements_and_jacobian(case, variant, theta1)
    residual_after = z_true - z_after
    prior_cost = float(delta.T @ p_inv @ delta)
    residual_cost_before = float(residual.T @ r_inv @ residual)
    residual_cost_after = float(residual_after.T @ r_inv @ residual_after)
    total_cost_after = residual_cost_after + prior_cost
    return {
        "theta0": theta0,
        "theta1": theta1,
        "delta": delta,
        "jacobian": jacobian,
        "residual_cost_before": residual_cost_before,
        "residual_cost_after": residual_cost_after,
        "prior_cost": prior_cost,
        "dynamics_cost": 0.0,
        "total_cost_before": residual_cost_before,
        "total_cost_after": total_cost_after,
        "normal_rank": int(np.linalg.matrix_rank(normal)),
        "normal_condition": float(np.linalg.cond(normal)),
    }


def _position_error_m(case: MicroCase, positions: np.ndarray) -> float:
    """Return mean UE position error in meters."""

    return float(np.mean(np.linalg.norm(positions - case.true_positions_km, axis=1)) * 1000.0)


def _clock_error_km(case: MicroCase, clocks: np.ndarray, drifts: np.ndarray, *, final_epoch: bool = True) -> float:
    """Return mean clock error in km at final or first epoch."""

    epoch = case.epochs - 1 if final_epoch else 0
    estimated = clocks + drifts * DT_SECONDS * epoch
    truth = case.true_clocks_km + case.true_drifts_km_per_s * DT_SECONDS * epoch
    return float(np.mean(np.abs(estimated - truth)))


def _block_norms(case: MicroCase, variant: Variant, delta: np.ndarray, jacobian: np.ndarray) -> dict[str, float]:
    """Return update norms by block and gauge/nullspace components."""

    position_update = delta[_position_slice(case)]
    clock_update = delta[_clock_slice(case)]
    num_users = case.true_positions_km.shape[0]
    drift = delta[_drift_slice(case, variant)] if variant.include_drift_state else np.asarray([])
    _, _, vh = np.linalg.svd(jacobian, full_matrices=True)
    rank = int(np.linalg.matrix_rank(jacobian))
    basis = vh.T
    null_basis = basis[:, rank:]
    null_component = null_basis @ (null_basis.T @ delta) if null_basis.size else np.zeros_like(delta)
    return {
        "position_update_norm": float(np.linalg.norm(position_update)),
        "ue_clock_update_norm": float(np.linalg.norm(clock_update[:num_users])),
        "satellite_clock_update_norm": float(np.linalg.norm(clock_update[num_users:])),
        "clock_drift_update_norm": float(np.linalg.norm(drift)),
        "common_clock_update_component": float(abs(np.mean(clock_update))) if clock_update.size else 0.0,
        "nullspace_update_norm": float(np.linalg.norm(null_component)),
        "nullspace_update_ratio": float(np.linalg.norm(null_component) / max(np.linalg.norm(delta), 1.0e-18)),
    }


def _case_pass(case: MicroCase, variant: Variant, row: dict[str, Any], rows_so_far: list[dict[str, Any]]) -> tuple[bool, str]:
    """Evaluate expected behavior for a case/variant row."""

    if case.name == "clock_only_correction":
        return row["clock_error_ratio"] < 0.75 and row["position_update_norm"] < 1.0e-3, "clock improves and position update is small"
    if case.name == "position_only_correction":
        return row["position_error_ratio"] < 0.75 and row["clock_error_after_km"] < 2.0e-4, "position improves and clock error remains small"
    if case.name == "clock_drift_correction":
        if not variant.include_drift_state:
            return False, "no-drift variant cannot satisfy drift-specific expectation"
        no_drift = [item for item in rows_so_far if item["case_name"] == case.name and item["variant"] == "block_scaled_no_drift"]
        if not no_drift:
            return row["clock_error_ratio"] < 0.75, "drift model improves clock error"
        return row["clock_error_after_km"] < no_drift[0]["clock_error_after_km"], "drift model beats no-drift block-scaled variant"
    if case.name == "gauge_common_clock_perturbation":
        if variant.project_common_clock:
            return row["common_clock_update_component"] < 1.0e-10, "common-clock projection removes gauge component"
        return row["common_clock_update_component"] < 1.0e-3, "common-clock component remains bounded"
    if case.name == "mixed_position_clock_perturbation":
        return row["position_error_ratio"] < 1.0 and row["clock_error_ratio"] < 1.0, "both position and clock improve"
    if case.name == "schur_nuisance_clock_toy":
        if variant.schur_eliminate_clocks:
            return np.isfinite(row["position_error_after_m"]) and row["position_error_ratio"] < 2.0 and row["clock_error_ratio"] < 2.0, "Schur update is finite and stable"
        return np.isfinite(row["position_error_after_m"]) and row["position_error_ratio"] < 3.0, "full update remains finite"
    return False, "unknown expectation"


def _evaluate_case_variant(case: MicroCase, variant: Variant, rows_so_far: list[dict[str, Any]]) -> dict[str, Any]:
    """Evaluate and summarize one case/variant pair."""

    started = time.monotonic()
    result = _apply_variant(case, variant)
    theta0 = result["theta0"]
    theta1 = result["theta1"]
    pos0, clock0, drift0 = _unpack_state(theta0, case, variant)
    pos1, clock1, drift1 = _unpack_state(theta1, case, variant)
    pos_before = _position_error_m(case, pos0)
    pos_after = _position_error_m(case, pos1)
    clock_before = _clock_error_km(case, clock0, drift0)
    clock_after = _clock_error_km(case, clock1, drift1)
    position_ratio_meaningful = pos_before > POSITION_RATIO_EPS_M
    clock_ratio_meaningful = clock_before > CLOCK_RATIO_EPS_KM
    norms = _block_norms(case, variant, result["delta"], result["jacobian"])
    row = {
        "case_name": case.name,
        "case_description": case.description,
        "expected_behavior": case.expected_behavior,
        "variant": variant.name,
        "variant_description": variant.description,
        "num_users": case.true_positions_km.shape[0],
        "num_satellites": case.num_satellites,
        "epochs": case.epochs,
        "runtime_seconds": time.monotonic() - started,
        "position_error_before_m": pos_before,
        "position_error_after_m": pos_after,
        "position_error_ratio": pos_after / max(pos_before, POSITION_RATIO_EPS_M),
        "position_error_ratio_meaningful": position_ratio_meaningful,
        "clock_error_before_km": clock_before,
        "clock_error_after_km": clock_after,
        "clock_error_ratio": clock_after / max(clock_before, CLOCK_RATIO_EPS_KM),
        "clock_error_ratio_meaningful": clock_ratio_meaningful,
        "sync_error_before_s": clock_before / C_KM_PER_S,
        "sync_error_after_s": clock_after / C_KM_PER_S,
        "residual_cost_before": result["residual_cost_before"],
        "residual_cost_after": result["residual_cost_after"],
        "prior_cost": result["prior_cost"],
        "dynamics_cost": result["dynamics_cost"],
        "total_cost_before": result["total_cost_before"],
        "total_cost_after": result["total_cost_after"],
        "normal_rank": result["normal_rank"],
        "normal_condition": result["normal_condition"],
        "position_variance_km2": variant.position_variance_km2,
        "ue_clock_variance_km2": variant.ue_clock_variance_km2,
        "satellite_clock_variance_km2": variant.satellite_clock_variance_km2,
        "drift_variance_km2_per_s2": variant.drift_variance_km2_per_s2,
        "include_drift_state": variant.include_drift_state,
        "project_common_clock": variant.project_common_clock,
        "schur_eliminate_clocks": variant.schur_eliminate_clocks,
        "clock_only": variant.clock_only,
        **norms,
    }
    passed, reason = _case_pass(case, variant, row, rows_so_far)
    row["expected_behavior_pass"] = bool(passed)
    row["expected_behavior_reason"] = reason
    row["finite_output"] = bool(np.all(np.isfinite([row["position_error_after_m"], row["clock_error_after_km"], row["total_cost_after"]])))
    return row


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> str:
    """Write CSV rows."""

    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row.keys()})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return _repo_rel(path)


def _write_json(path: Path, payload: dict[str, Any]) -> str:
    """Write JSON and return repo-relative path."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return _repo_rel(path)


def _repo_rel(path: Path) -> str:
    """Return repo-relative path."""

    return path.relative_to(SAT_SIM_ROOT).as_posix()


def _summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Summarize variant-level benchmark results."""

    output = []
    for variant in [item.name for item in VARIANTS]:
        subset = [row for row in rows if row["variant"] == variant]
        position_ratios = [
            row["position_error_ratio"]
            for row in subset
            if row["position_error_ratio_meaningful"]
        ]
        clock_ratios = [
            row["clock_error_ratio"]
            for row in subset
            if row["clock_error_ratio_meaningful"]
        ]
        output.append(
            {
                "variant": variant,
                "tested_cases": len(subset),
                "passed_cases": sum(1 for row in subset if row["expected_behavior_pass"]),
                "finite_cases": sum(1 for row in subset if row["finite_output"]),
                "mean_position_ratio_meaningful_only": float(np.mean(position_ratios)) if position_ratios else None,
                "mean_clock_ratio_meaningful_only": float(np.mean(clock_ratios)) if clock_ratios else None,
                "position_ratio_meaningful_cases": len(position_ratios),
                "clock_ratio_meaningful_cases": len(clock_ratios),
                "mean_runtime_seconds": float(np.mean([row["runtime_seconds"] for row in subset])),
            }
        )
    return output


def _promotion_candidates(summary_rows: list[dict[str, Any]], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return variants passing minimum micro-benchmark promotion rule."""

    required_cases = {
        "clock_only_correction",
        "position_only_correction",
        "gauge_common_clock_perturbation",
        "mixed_position_clock_perturbation",
    }
    promoted = []
    for item in summary_rows:
        subset = [row for row in rows if row["variant"] == item["variant"]]
        passed = {row["case_name"] for row in subset if row["expected_behavior_pass"]}
        if required_cases <= passed:
            promoted.append(item)
    return promoted


def _plot_grouped_bars(rows: list[dict[str, Any]], key_before: str, key_after: str, ylabel: str, stem: str) -> list[str]:
    """Write before/after bar plot for each case/variant."""

    PLOT_ROOT.mkdir(parents=True, exist_ok=True)
    labels = [f"{row['case_name']}\n{row['variant']}" for row in rows]
    x = np.arange(len(rows))
    width = 0.42
    fig, ax = plt.subplots(figsize=(12.0, 4.8), dpi=180)
    ax.bar(x - width / 2, [row[key_before] for row in rows], width, label="before")
    ax.bar(x + width / 2, [row[key_after] for row in rows], width, label="after")
    ax.set_ylabel(ylabel)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=75, ha="right", fontsize=5)
    ax.legend(fontsize=7)
    fig.tight_layout()
    outputs = []
    for suffix in ("pdf", "png"):
        path = PLOT_ROOT / f"{stem}.{suffix}"
        fig.savefig(path)
        outputs.append(_repo_rel(path))
    plt.close(fig)
    return outputs


def _plot_update_norms(rows: list[dict[str, Any]]) -> list[str]:
    """Write block update norm plot."""

    labels = [f"{row['case_name']}\n{row['variant']}" for row in rows]
    x = np.arange(len(rows))
    fig, ax = plt.subplots(figsize=(12.0, 4.8), dpi=180)
    bottom = np.zeros(len(rows))
    for key, label in [
        ("position_update_norm", "position"),
        ("ue_clock_update_norm", "UE clock"),
        ("satellite_clock_update_norm", "sat clock"),
        ("clock_drift_update_norm", "drift"),
    ]:
        values = np.asarray([row[key] for row in rows])
        ax.bar(x, values, bottom=bottom, label=label)
        bottom += values
    ax.set_ylabel("Update norm [km or km/s]")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=75, ha="right", fontsize=5)
    ax.legend(fontsize=7)
    fig.tight_layout()
    outputs = []
    for suffix in ("pdf", "png"):
        path = PLOT_ROOT / f"block_update_norms.{suffix}"
        fig.savefig(path)
        outputs.append(_repo_rel(path))
    plt.close(fig)
    return outputs


def _plot_pass_heatmap(rows: list[dict[str, Any]]) -> list[str]:
    """Write pass/fail heatmap by case and variant."""

    cases = [case.name for case in _micro_cases()]
    variants = [variant.name for variant in VARIANTS]
    data = np.zeros((len(cases), len(variants)))
    for i, case in enumerate(cases):
        for j, variant in enumerate(variants):
            match = [row for row in rows if row["case_name"] == case and row["variant"] == variant]
            data[i, j] = 1.0 if match and match[0]["expected_behavior_pass"] else 0.0
    fig, ax = plt.subplots(figsize=(7.0, 4.2), dpi=180)
    ax.imshow(data, cmap="Greens", vmin=0.0, vmax=1.0)
    ax.set_xticks(np.arange(len(variants)))
    ax.set_xticklabels(variants, rotation=45, ha="right", fontsize=7)
    ax.set_yticks(np.arange(len(cases)))
    ax.set_yticklabels(cases, fontsize=7)
    ax.set_title("Expected behavior pass/fail")
    fig.tight_layout()
    outputs = []
    for suffix in ("pdf", "png"):
        path = PLOT_ROOT / f"pass_fail_heatmap.{suffix}"
        fig.savefig(path)
        outputs.append(_repo_rel(path))
    plt.close(fig)
    return outputs


def _plot_scatter(rows: list[dict[str, Any]]) -> list[str]:
    """Write position-vs-clock improvement scatter."""

    fig, ax = plt.subplots(figsize=(5.2, 4.0), dpi=180)
    for variant in [item.name for item in VARIANTS]:
        subset = [row for row in rows if row["variant"] == variant]
        plottable = [
            row
            for row in subset
            if row["position_error_ratio_meaningful"] and row["clock_error_ratio_meaningful"]
        ]
        if not plottable:
            continue
        ax.scatter([row["position_error_ratio"] for row in plottable], [row["clock_error_ratio"] for row in plottable], label=variant, s=22, alpha=0.75)
    ax.axvline(1.0, color="0.5", linewidth=0.8)
    ax.axhline(1.0, color="0.5", linewidth=0.8)
    ax.set_xlabel("Position error ratio after/before (nonzero baseline cases)")
    ax.set_ylabel("Clock error ratio after/before (nonzero baseline cases)")
    ax.legend(fontsize=5)
    fig.tight_layout()
    outputs = []
    for suffix in ("pdf", "png"):
        path = PLOT_ROOT / f"position_clock_improvement_scatter.{suffix}"
        fig.savefig(path)
        outputs.append(_repo_rel(path))
    plt.close(fig)
    return outputs


def _write_plots(rows: list[dict[str, Any]]) -> list[str]:
    """Write all compact micro-benchmark plots."""

    outputs = []
    outputs.extend(_plot_grouped_bars(rows, "position_error_before_m", "position_error_after_m", "Position error [m]", "position_error_before_after"))
    outputs.extend(_plot_grouped_bars(rows, "clock_error_before_km", "clock_error_after_km", "Clock error [km]", "clock_error_before_after"))
    outputs.extend(_plot_update_norms(rows))
    outputs.extend(_plot_pass_heatmap(rows))
    outputs.extend(_plot_scatter(rows))
    return outputs


def _write_report(payload: dict[str, Any]) -> None:
    """Write report pair."""

    def _ratio_text(value: float | None, count: int) -> str:
        if value is None:
            return "n/a (0)"
        return f"{value:.6g} ({count})"

    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    _write_json(REPORT_ROOT / "STEP3_MICRO_BENCHMARK_REPORT.json", payload)
    md = [
        "# Step 3 Micro-Benchmark Report",
        "",
        "## Executive Summary",
        "",
        f"- Artifact status: `{payload['artifact_status']}`",
        f"- Runtime seconds: `{payload['runtime_seconds']:.3f}`",
        f"- Cases: `{payload['cases_implemented']}`",
        f"- Variants: `{payload['variants_tested']}`",
        f"- Promoted variants: `{payload['promoted_variants']}`",
        "",
        "## Variant Summary",
        "",
        "| Variant | Passed | Finite | Mean position ratio | Mean clock ratio |",
        "|---|---:|---:|---:|---:|",
    ]
    for item in payload["summary"]:
        md.append(
            f"| `{item['variant']}` | {item['passed_cases']}/{item['tested_cases']} | "
            f"{item['finite_cases']}/{item['tested_cases']} | "
            f"{_ratio_text(item['mean_position_ratio_meaningful_only'], item['position_ratio_meaningful_cases'])} | "
            f"{_ratio_text(item['mean_clock_ratio_meaningful_only'], item['clock_ratio_meaningful_cases'])} |"
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
    (REPORT_ROOT / "STEP3_MICRO_BENCHMARK_REPORT.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def run_benchmarks() -> dict[str, Any]:
    """Run all deterministic micro-benchmarks."""

    started = time.monotonic()
    rows: list[dict[str, Any]] = []
    for case in _micro_cases():
        for variant in VARIANTS:
            rows.append(_evaluate_case_variant(case, variant, rows))
    summary_rows = _summary(rows)
    promoted = _promotion_candidates(summary_rows, rows)
    raw_csv = _write_csv(OUTPUT_ROOT / "raw.csv", rows)
    summary_csv = _write_csv(OUTPUT_ROOT / "summary.csv", summary_rows)
    plots = _write_plots(rows)
    metadata = {
        "artifact_status": "non_final_step3_micro_benchmarks",
        "manuscript_ready": False,
        "not_for_manuscript_submission": True,
        "network_size_graphs_run": False,
        "full_ladder_run": False,
        "medium_grid_run": False,
        "deterministic": True,
        "monte_carlo": False,
        "cases_implemented": [case.name for case in _micro_cases()],
        "variants_tested": [variant.name for variant in VARIANTS],
        "row_count": len(rows),
        "promotion_rule": "clock-only, position-only, gauge/common-clock, and mixed case must pass before network-size promotion",
        "promoted_variants": [item["variant"] for item in promoted],
        "runtime_seconds": time.monotonic() - started,
        "raw_csv": raw_csv,
        "summary_csv": summary_csv,
        "plots": plots,
        "summary": summary_rows,
        "rows": rows,
        "interpretation": "Micro-benchmarks isolate Step 3 matrix behavior in deterministic toy systems. Passing these cases is necessary but not sufficient for network-size figure work.",
    }
    metadata_json = _write_json(OUTPUT_ROOT / "metadata.json", metadata)
    payload = {**metadata, "metadata_json": metadata_json}
    _write_report(payload)
    return payload


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Print planned cases/variants without running.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> dict[str, Any]:
    """CLI entrypoint."""

    args = _parse_args(argv)
    planned = {
        "artifact_status": "non_final_step3_micro_benchmark_planned_work",
        "will_execute": not args.dry_run,
        "cases": [case.name for case in _micro_cases()],
        "variants": [variant.name for variant in VARIANTS],
        "network_size_graphs_run": False,
        "full_ladder_run": False,
        "medium_grid_run": False,
    }
    print(json.dumps(planned, indent=2))
    if args.dry_run:
        return planned
    payload = run_benchmarks()
    print(json.dumps({"status": "wrote", "output_root": _repo_rel(OUTPUT_ROOT), "row_count": len(payload["rows"])}, indent=2))
    return payload


if __name__ == "__main__":
    main()
