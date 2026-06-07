"""V24 gauge-consistency diagnostic for the JCLS simulation notebook.

This script is intentionally diagnostic-only. It does not modify notebook state,
manuscript files, figures, or saved results. The goal is to make the V24 clock
gauge convention explicit and compare it against the notebook's older all-clock
metric conventions on a tiny deterministic scenario.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable

import numpy as np

from jcls_sim.constants import C_KM_PER_S
from jcls_sim.gauge import (
    all_clock_node_ids,
    expected_v24_parameter_dim,
    reference_satellite_node_id,
    v24_clock_node_ids,
    v24_clock_vector_from_full,
)
from jcls_sim.metrics import all_non_reference_clock_error

SEED = 20260606


def full_clock_vector_to_map(full_clock_vector: Iterable[float], num_users: int, num_satellites: int) -> dict[int, float]:
    """Map a full clock vector ordered by node id to ``{node_id: clock_value}``."""

    values = list(full_clock_vector)
    expected = num_users + num_satellites
    if len(values) != expected:
        raise ValueError(f"Expected {expected} clock values, got {len(values)}.")
    return dict(zip(all_clock_node_ids(num_users, num_satellites), values))


def v24_relative_clock_vector(full_clock_vector: Iterable[float], num_users: int, num_satellites: int) -> np.ndarray:
    """Subtract the first satellite clock and return V24 clock order."""

    clock_map = full_clock_vector_to_map(full_clock_vector, num_users, num_satellites)
    return v24_clock_vector_from_full(clock_map, num_users, num_satellites)


def old_average_clock_error_seconds(true_full_clocks_km: np.ndarray, est_full_clocks_km: np.ndarray) -> float:
    """Notebook-style average absolute error over all clock offsets."""

    return float(np.mean(np.abs(est_full_clocks_km - true_full_clocks_km)) / C_KM_PER_S)


def v24_average_clock_error_seconds(
    true_full_clocks_km: np.ndarray,
    est_full_clocks_km: np.ndarray,
    num_users: int,
    num_satellites: int,
) -> float:
    """Gauge-consistent average over UE and non-reference satellite offsets."""

    true_map = full_clock_vector_to_map(true_full_clocks_km, num_users, num_satellites)
    est_map = full_clock_vector_to_map(est_full_clocks_km, num_users, num_satellites)
    return all_non_reference_clock_error(true_map, est_map, num_users, num_satellites) / C_KM_PER_S


def old_parameter_names(num_users: int, num_satellites: int) -> list[str]:
    """Diagnostic parameter order for the old all-clock model."""

    position_names = [
        f"{axis}_{user_id}"
        for user_id in range(1, num_users + 1)
        for axis in ("x", "y", "z")
    ]
    clock_names = [f"delta_{node_id}" for node_id in all_clock_node_ids(num_users, num_satellites)]
    return position_names + clock_names


def v24_parameter_names(num_users: int, num_satellites: int) -> list[str]:
    """Diagnostic parameter order under the V24 clock gauge."""

    position_names = [
        f"{axis}_{user_id}"
        for user_id in range(1, num_users + 1)
        for axis in ("x", "y", "z")
    ]
    clock_names = [f"delta_{node_id}" for node_id in v24_clock_node_ids(num_users, num_satellites)]
    return position_names + clock_names


@dataclass(frozen=True)
class ToyGeometry:
    users_km: np.ndarray
    satellites_km: np.ndarray


def make_toy_geometry(num_users: int, num_satellites: int) -> ToyGeometry:
    """Create a deterministic small geometry in km for Jacobian diagnostics."""

    base_users = np.array(
        [
            [0.00, 0.00, 0.00],
            [0.75, 0.25, 0.04],
            [0.20, 0.90, -0.03],
            [0.95, -0.55, 0.08],
        ],
        dtype=float,
    )
    base_satellites = np.array(
        [
            [2.0, -5.0, 7.0],
            [-3.0, 4.5, 6.5],
            [5.5, 2.0, 8.0],
            [-4.0, -3.0, 7.5],
            [1.0, 6.0, 8.5],
        ],
        dtype=float,
    )
    if num_users > len(base_users) or num_satellites > len(base_satellites):
        raise ValueError("Toy geometry only supports up to 4 users and 5 satellites.")
    return ToyGeometry(base_users[:num_users], base_satellites[:num_satellites])


def build_toy_measurement_jacobian(
    num_users: int,
    num_satellites: int,
    dl_sigma_km: float = 0.030,
    sl_sigma_km: float = 0.010,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Build a tiny DL/SL TOA Jacobian with notebook clock-sign convention.

    Measurements follow range + delta_tx - delta_rx. Satellites have fixed
    positions; user positions and all node clocks are estimated in the old model.
    """

    geometry = make_toy_geometry(num_users, num_satellites)
    param_names = old_parameter_names(num_users, num_satellites)
    col = {name: idx for idx, name in enumerate(param_names)}
    rows: list[np.ndarray] = []
    variances: list[float] = []

    def position_slice(user_id: int) -> tuple[int, int, int]:
        return (col[f"x_{user_id}"], col[f"y_{user_id}"], col[f"z_{user_id}"])

    # Downlinks: each UE receives from each satellite.
    for rx_idx in range(num_users):
        rx_node_id = rx_idx + 1
        rx_pos = geometry.users_km[rx_idx]
        for sat_idx in range(num_satellites):
            sat_node_id = num_users + sat_idx + 1
            sat_pos = geometry.satellites_km[sat_idx]
            diff = rx_pos - sat_pos
            rng = np.linalg.norm(diff)
            row = np.zeros(len(param_names))
            row[list(position_slice(rx_node_id))] = diff / rng
            row[col[f"delta_{rx_node_id}"]] = -1.0
            row[col[f"delta_{sat_node_id}"]] = 1.0
            rows.append(row)
            variances.append(dl_sigma_km**2)

    # Directed sidelinks: each UE receives from every other UE, matching connect().
    for rx_idx in range(num_users):
        rx_node_id = rx_idx + 1
        rx_pos = geometry.users_km[rx_idx]
        for tx_idx in range(num_users):
            if tx_idx == rx_idx:
                continue
            tx_node_id = tx_idx + 1
            tx_pos = geometry.users_km[tx_idx]
            diff = rx_pos - tx_pos
            rng = np.linalg.norm(diff)
            row = np.zeros(len(param_names))
            row[list(position_slice(rx_node_id))] += diff / rng
            row[list(position_slice(tx_node_id))] -= diff / rng
            row[col[f"delta_{rx_node_id}"]] = -1.0
            row[col[f"delta_{tx_node_id}"]] = 1.0
            rows.append(row)
            variances.append(sl_sigma_km**2)

    return np.vstack(rows), np.diag(variances), param_names


def trace_inverse(matrix: np.ndarray) -> tuple[float, str]:
    """Trace inverse if nonsingular; otherwise trace pseudoinverse."""

    rank = np.linalg.matrix_rank(matrix)
    if rank == matrix.shape[0]:
        return float(np.trace(np.linalg.inv(matrix))), "inv"
    return float(np.trace(np.linalg.pinv(matrix))), "pinv"


def fim_metrics(num_users: int, num_satellites: int) -> dict[str, object]:
    """Compare old notebook-style and V24-gauged FIM dimensions/metrics."""

    J, Sigma, old_params = build_toy_measurement_jacobian(num_users, num_satellites)
    W = np.linalg.inv(Sigma)
    position_cols = [idx for idx, name in enumerate(old_params) if name[0] in {"x", "y", "z"}]
    clock_cols = [idx for idx, name in enumerate(old_params) if name.startswith("delta_")]
    ref_name = f"delta_{reference_satellite_node_id(num_users)}"
    ref_col = old_params.index(ref_name)

    FIM_old_full = J.T @ W @ J
    FIM_loc_old = J[:, position_cols].T @ W @ J[:, position_cols]
    FIM_clock_old = J[:, clock_cols].T @ W @ J[:, clock_cols]
    loc_trace_old, loc_inverse_kind_old = trace_inverse(FIM_loc_old)
    sync_trace_old, sync_inverse_kind_old = trace_inverse(FIM_clock_old)

    keep_cols = [idx for idx in range(len(old_params)) if idx != ref_col]
    J_v24 = J[:, keep_cols]
    v24_params_from_old = [old_params[idx] for idx in keep_cols]
    FIM_v24_full = J_v24.T @ W @ J_v24
    cov_v24 = np.linalg.pinv(FIM_v24_full)
    v24_position_cols = [idx for idx, name in enumerate(v24_params_from_old) if name[0] in {"x", "y", "z"}]
    v24_clock_cols = [idx for idx, name in enumerate(v24_params_from_old) if name.startswith("delta_")]
    loc_v24 = float(np.trace(cov_v24[np.ix_(v24_position_cols, v24_position_cols)]) / num_users)
    sync_v24 = float(np.trace(cov_v24[np.ix_(v24_clock_cols, v24_clock_cols)]) / len(v24_clock_cols))

    return {
        "old_params": old_params,
        "v24_params": v24_parameter_names(num_users, num_satellites),
        "old_param_dim": len(old_params),
        "v24_param_dim": len(v24_parameter_names(num_users, num_satellites)),
        "expected_v24_dim": expected_v24_parameter_dim(num_users, num_satellites),
        "reference_clock": ref_name,
        "reference_in_old_params": ref_name in old_params,
        "reference_in_v24_params": ref_name in v24_parameter_names(num_users, num_satellites),
        "measurement_count": int(J.shape[0]),
        "old_full_fim_shape": FIM_old_full.shape,
        "old_full_fim_rank": int(np.linalg.matrix_rank(FIM_old_full)),
        "v24_full_fim_shape": FIM_v24_full.shape,
        "v24_full_fim_rank": int(np.linalg.matrix_rank(FIM_v24_full)),
        "old_position_crlb_metric": float(loc_trace_old / num_users),
        "old_position_inverse_kind": loc_inverse_kind_old,
        "v24_position_crlb_metric": loc_v24,
        "old_sync_crlb_metric": float(sync_trace_old / (num_users + num_satellites)),
        "old_sync_inverse_kind": sync_inverse_kind_old,
        "v24_sync_crlb_metric": sync_v24,
        "current_notebook_pinv_for_sync": True,
        "current_notebook_excludes_reference_clock": False,
    }


def notebook_source_audit(notebook_path: Path) -> dict[str, object]:
    """Inspect the notebook text for current metric/FIM conventions."""

    raw = notebook_path.read_text(encoding="utf-8")
    nb = json.loads(raw)
    source = "\n".join("".join(cell.get("source", [])) for cell in nb.get("cells", []))
    return {
        "has_calculate_average_clock_error": "def calculate_average_clock_error" in source,
        "clock_error_averages_delta_symbols": "param.name.startswith('delta_')" in source,
        "clock_error_subtracts_reference": "delta_rel" in source or "reference_satellite" in source,
        "master_clock_id_assignment": "self.master_clock_id = 1" in source,
        "reference_substitution_commented_out": "#if self.receiver.node_id == self.master_clock_id" in source,
        "fim_function_present": "def generate_FIM_data" in source,
        "fim_sync_uses_pinv": "np.trace(np.linalg.pinv(FIM_clock))" in source,
        "fim_uses_all_delta_symbols": "if param.name.startswith('delta_')" in source,
    }


def relative_difference(new_value: float, old_value: float) -> float:
    """Return relative difference against the old value, guarding zero."""

    if old_value == 0:
        return float("inf") if new_value != 0 else 0.0
    return float(abs(new_value - old_value) / abs(old_value))


def classify_materiality(abs_diff: float, rel_diff: float) -> str:
    """Simple diagnostic materiality classifier for tiny smoke tests."""

    if rel_diff > 0.10:
        return "material in this tiny gauge smoke test"
    if rel_diff > 0.01:
        return "minor but nonzero in this tiny gauge smoke test"
    if abs_diff > 1e-12:
        return "numerically small in this tiny gauge smoke test"
    return "no observed difference in this tiny gauge smoke test"


def figure_risk(sync_rel_diff: float, fim: dict[str, object]) -> list[tuple[str, str, str]]:
    """Classify current manuscript figure risk from the smoke-test findings."""

    crlb_loc_rel = relative_difference(
        float(fim["v24_position_crlb_metric"]),
        float(fim["old_position_crlb_metric"]),
    )
    crlb_sync_rel = relative_difference(
        float(fim["v24_sync_crlb_metric"]),
        float(fim["old_sync_crlb_metric"]),
    )
    sync_metric_material = sync_rel_diff > 0.10
    return [
        (
            "CRLB localization",
            "NEEDS RERUN",
            f"current CRLB construction uses old/all-clock dimensions; tiny V24 joint-gauge position metric relative difference = {crlb_loc_rel:.3g}",
        ),
        (
            "CRLB synchronization",
            "NEEDS RERUN",
            f"current CRLB synchronization includes all clocks; tiny V24 gauge metric relative difference = {crlb_sync_rel:.3g}",
        ),
        (
            "localization vs number of satellites",
            "UNKNOWN / needs human decision",
            "position error metric does not directly average clocks, but the solver state is overparameterized relative to V24 gauge",
        ),
        (
            "synchronization vs number of satellites",
            "NEEDS RERUN" if sync_metric_material else "LIKELY SAFE / minor metric difference",
            f"synchronization metric changes after V24 reference-clock normalization; tiny relative difference = {sync_rel_diff:.3g}",
        ),
        (
            "localization vs sigma_delta",
            "UNKNOWN / needs human decision",
            "sweep depends on clock uncertainty and old overparameterized solver state, even though plotted metric is position error",
        ),
        (
            "synchronization vs sigma_delta",
            "NEEDS RERUN" if sync_metric_material else "LIKELY SAFE / minor metric difference",
            f"plotted metric is directly gauge-dependent; tiny relative difference = {sync_rel_diff:.3g}",
        ),
    ]


def main() -> None:
    num_users = 3
    num_satellites = 4
    rng = np.random.default_rng(SEED)

    true_clocks_km = rng.normal(loc=0.0, scale=0.20, size=num_users + num_satellites)
    common_gauge_bias_km = 0.075
    estimator_noise_km = rng.normal(loc=0.0, scale=0.015, size=num_users + num_satellites)
    est_clocks_km = true_clocks_km + common_gauge_bias_km + estimator_noise_km

    old_sync = old_average_clock_error_seconds(true_clocks_km, est_clocks_km)
    v24_sync = v24_average_clock_error_seconds(true_clocks_km, est_clocks_km, num_users, num_satellites)
    sync_abs_diff = abs(v24_sync - old_sync)
    sync_rel_diff = relative_difference(v24_sync, old_sync)

    fim = fim_metrics(num_users, num_satellites)
    source_audit = notebook_source_audit(Path("JCLS_Simulation.ipynb"))

    print("V24 Gauge Integrity Diagnostic")
    print("==============================")
    print(f"Deterministic seed: {SEED}")
    print(f"Tiny scenario: Nu={num_users}, Ns={num_satellites}")
    print()
    print("Notebook source audit")
    print("---------------------")
    for key, value in source_audit.items():
        print(f"{key}: {value}")
    print()
    print("Gauge helper check")
    print("------------------")
    print(f"Reference satellite clock id: delta_{reference_satellite_node_id(num_users)}")
    print(f"All clock ids: {all_clock_node_ids(num_users, num_satellites)}")
    print(f"V24 clock ids/order: {v24_clock_node_ids(num_users, num_satellites)}")
    print(f"V24 relative true clock vector (km): {v24_relative_clock_vector(true_clocks_km, num_users, num_satellites)}")
    print()
    print("Parameter dimension check")
    print("-------------------------")
    print(f"Old all-clock parameter dimension: {fim['old_param_dim']}")
    print(f"V24 gauged parameter dimension: {fim['v24_param_dim']}")
    print(f"Expected V24 dimension 4*Nu+Ns-1: {fim['expected_v24_dim']}")
    print(f"Reference clock in old params: {fim['reference_in_old_params']}")
    print(f"Reference clock in V24 params: {fim['reference_in_v24_params']}")
    print(f"Old params: {fim['old_params']}")
    print(f"V24 params: {fim['v24_params']}")
    print()
    print("Synchronization metric check")
    print("----------------------------")
    print(f"Old notebook-style average clock error: {old_sync:.12e} s")
    print(f"V24 gauge-consistent average clock error: {v24_sync:.12e} s")
    print(f"Absolute difference: {sync_abs_diff:.12e} s")
    print(f"Relative difference: {sync_rel_diff:.6f}")
    print(f"Materiality: {classify_materiality(sync_abs_diff, sync_rel_diff)}")
    print()
    print("CRLB/FIM gauge check")
    print("--------------------")
    print(f"Measurement count: {fim['measurement_count']}")
    print(f"Old full FIM shape/rank: {fim['old_full_fim_shape']} / {fim['old_full_fim_rank']}")
    print(f"V24 full FIM shape/rank: {fim['v24_full_fim_shape']} / {fim['v24_full_fim_rank']}")
    print(f"Current notebook sync CRLB uses pseudoinverse: {fim['current_notebook_pinv_for_sync']}")
    print(f"Current notebook excludes reference clock: {fim['current_notebook_excludes_reference_clock']}")
    print(f"Old position CRLB metric: {fim['old_position_crlb_metric']:.12e} ({fim['old_position_inverse_kind']})")
    print(f"V24 position CRLB metric: {fim['v24_position_crlb_metric']:.12e} (joint pinv)")
    print(f"Old synchronization CRLB metric: {fim['old_sync_crlb_metric']:.12e} ({fim['old_sync_inverse_kind']})")
    print(f"V24 synchronization CRLB metric: {fim['v24_sync_crlb_metric']:.12e} (joint pinv)")
    print()
    print("Current figure risk classification")
    print("----------------------------------")
    for figure, status, rationale in figure_risk(sync_rel_diff, fim):
        print(f"{figure}: {status} -- {rationale}")
    print()
    print("Reproducibility notes")
    print("---------------------")
    print("- Seed insertion point for the notebook: before each Scenario construction loop and before optimizer initialization/noise sampling.")
    print("- Future per-trial outputs should be saved from generate_data_for_heatmap, generate_data_for_clock_std_dev, and generate_FIM_data.")
    print("- Recommended format: NPZ for arrays plus a CSV summary table with columns scenario_id, trial, method, Nu, Ns, sigma_delta_s, ue_id, position_error_m, clock_node_id, clock_error_s, seed.")
    print()
    print("Recommended next step")
    print("---------------------")
    print("D. larger code refactor needed before using this codebase for V24-consistent reruns; at minimum align the parameter vector, synchronization metric, and FIM/CRLB construction to the V24 gauge.")


if __name__ == "__main__":
    main()
