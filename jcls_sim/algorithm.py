"""Package-native V24 three-stage JCLS estimator helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import numpy as np

from .configs import V24ScenarioConfig
from .estimators import information_form_ekf_update, weighted_normal_equations
from .gauge import expected_v24_parameter_dim
from .jacobian import analytic_toa_jacobian_km, toa_range_vector_from_theta_km
from .parameters import pack_v24_theta, unpack_v24_theta


@dataclass(frozen=True)
class V24StateModel:
    """V24 dynamic state model with explicit F, Q, and Pi."""

    f_matrix: np.ndarray
    q_covariance: np.ndarray
    pi_matrix: np.ndarray
    model_name: str = "theta_identity_state"

    def validate(self, theta_dim: int) -> None:
        """Validate model dimensions for a V24 theta dimension."""

        state_dim = self.f_matrix.shape[0]
        if self.f_matrix.shape != (state_dim, state_dim):
            raise ValueError("f_matrix must be square.")
        if self.q_covariance.shape != (state_dim, state_dim):
            raise ValueError("q_covariance must match f_matrix dimensions.")
        if self.pi_matrix.shape != (theta_dim, state_dim):
            raise ValueError(f"pi_matrix must have shape ({theta_dim}, {state_dim}).")


@dataclass(frozen=True)
class EstimatorResult:
    """Estimator output and audit diagnostics."""

    theta: np.ndarray
    success: bool
    diagnostics: dict[str, Any]
    covariance: np.ndarray | None = None


STEP_C7_ESTIMATOR_MODE = "step_c7_residual_cov_sync_safeguard"


@dataclass(frozen=True)
class StepC7BlockSlices:
    """State-vector slices used by the C7 block covariance and safeguard."""

    position: slice
    ue_clock: slice
    satellite_clock: slice
    clock_drift: slice


@dataclass(frozen=True)
class StepC7Config:
    """Configuration for residual-scaled C7 Step 3 refinement."""

    damping_lambda: float = 1.0e-5
    covariance_rcond: float = 1.0e-10
    update_rcond: float = 1.0e-10
    position_floor_km2: float = 0.002**2
    position_ceiling_km2: float = 1.0**2
    clock_floor_km2: float = 0.0002**2
    clock_ceiling_km2: float = 0.020**2
    drift_floor_km2_per_s2: float = 0.00005**2
    drift_ceiling_km2_per_s2: float = 0.010**2
    objective_tolerance: float = 1.0e-9
    clock_update_covariance_sigma_limit: float = 3.0
    common_clock_ratio_limit: float = 0.95
    single_user_clock_safeguard: bool = True
    sync_safeguard: bool = True
    residual_scale_enabled: bool = True


def _slice_length(slc: slice) -> int:
    """Return a nonnegative slice length for Step C7 contiguous slices."""

    return max(0, int(slc.stop or 0) - int(slc.start or 0))


def _validate_c7_inputs(
    state: np.ndarray,
    jacobian: np.ndarray,
    residual: np.ndarray,
    sigmas: np.ndarray,
    block_slices: StepC7BlockSlices,
    num_users: int,
    config: StepC7Config,
) -> None:
    """Validate C7 array dimensions and scalar controls."""

    if num_users < 1:
        raise ValueError("num_users must be at least 1.")
    if state.ndim != 1:
        raise ValueError("initial_state must be one-dimensional.")
    if jacobian.ndim != 2 or jacobian.shape[1] != state.size:
        raise ValueError("jacobian must have shape (N_z, state_dim).")
    if residual.shape != (jacobian.shape[0],):
        raise ValueError("residual must have one entry per measurement row.")
    if sigmas.shape != residual.shape:
        raise ValueError("sigmas must have one entry per measurement row.")
    if np.any(sigmas <= 0.0):
        raise ValueError("sigmas must be strictly positive.")
    for name, slc in (
        ("position", block_slices.position),
        ("ue_clock", block_slices.ue_clock),
        ("satellite_clock", block_slices.satellite_clock),
        ("clock_drift", block_slices.clock_drift),
    ):
        start = int(slc.start or 0)
        stop = int(slc.stop or 0)
        if start < 0 or stop < start or stop > state.size:
            raise ValueError(f"{name} slice is outside the state vector.")
    if config.damping_lambda < 0.0:
        raise ValueError("damping_lambda must be nonnegative.")


def _clip_diagonal_block(
    variances: np.ndarray,
    slc: slice,
    floor: float,
    ceiling: float,
) -> None:
    """Clip a diagonal covariance block in place."""

    if _slice_length(slc) == 0:
        return
    if floor < 0.0 or ceiling <= 0.0 or floor > ceiling:
        raise ValueError("covariance floors/ceilings must be nonnegative and ordered.")
    variances[slc] = np.clip(variances[slc], floor, ceiling)


def step_c7_residual_scaled_block_covariance(
    jacobian: np.ndarray,
    residual: np.ndarray,
    sigmas: np.ndarray,
    block_slices: StepC7BlockSlices,
    *,
    config: StepC7Config | None = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Return residual-scaled block-diagonal LM covariance for C7."""

    cfg = config or StepC7Config()
    jac = np.asarray(jacobian, dtype=float)
    res = np.asarray(residual, dtype=float)
    sigma = np.asarray(sigmas, dtype=float)
    dummy_state = np.zeros(jac.shape[1], dtype=float)
    _validate_c7_inputs(dummy_state, jac, res, sigma, block_slices, 1, cfg)

    r_inv_diag = 1.0 / np.square(sigma)
    information = jac.T @ (jac * r_inv_diag[:, None])
    damped_information = information + cfg.damping_lambda * np.eye(information.shape[0], dtype=float)
    covariance = np.linalg.pinv(damped_information, rcond=cfg.covariance_rcond)
    covariance = 0.5 * (covariance + covariance.T)
    residual_cost = float(np.sum(np.square(res / sigma)))
    dof = max(1, int(res.size - jac.shape[1]))
    residual_scale_factor = residual_cost / dof if cfg.residual_scale_enabled else 1.0
    covariance *= residual_scale_factor

    block_diagonal = np.zeros_like(covariance)
    for slc in (
        block_slices.position,
        block_slices.ue_clock,
        block_slices.satellite_clock,
        block_slices.clock_drift,
    ):
        if _slice_length(slc) > 0:
            block_diagonal[slc, slc] = covariance[slc, slc]
    variances = np.diag(block_diagonal).copy()
    _clip_diagonal_block(variances, block_slices.position, cfg.position_floor_km2, cfg.position_ceiling_km2)
    _clip_diagonal_block(variances, block_slices.ue_clock, cfg.clock_floor_km2, cfg.clock_ceiling_km2)
    _clip_diagonal_block(variances, block_slices.satellite_clock, cfg.clock_floor_km2, cfg.clock_ceiling_km2)
    _clip_diagonal_block(
        variances,
        block_slices.clock_drift,
        cfg.drift_floor_km2_per_s2,
        cfg.drift_ceiling_km2_per_s2,
    )
    clipped_covariance = np.diag(variances)
    return clipped_covariance, {
        "covariance_source": "residual_scaled_lm_curvature_block_diagonal_diagonal_clipped",
        "residual_cost": residual_cost,
        "degrees_of_freedom": dof,
        "residual_scale_factor": residual_scale_factor,
        "residual_scale_enabled": bool(cfg.residual_scale_enabled),
        "information_rank": int(np.linalg.matrix_rank(information)),
        "covariance_rank": int(np.linalg.matrix_rank(clipped_covariance)),
        "covariance_shape": list(clipped_covariance.shape),
        "state_dimension": int(jac.shape[1]),
        "damping_lambda": float(cfg.damping_lambda),
        "truth_state_used_for_covariance": False,
    }


def _block_stats(matrix: np.ndarray, slc: slice) -> dict[str, float]:
    """Return trace and eigenvalue diagnostics for one matrix block."""

    if _slice_length(slc) == 0:
        return {"trace": 0.0, "eig_min": 0.0, "eig_max": 0.0}
    block = matrix[slc, slc]
    eigvals = np.linalg.eigvalsh(0.5 * (block + block.T))
    return {
        "trace": float(np.trace(block)),
        "eig_min": float(np.min(eigvals)),
        "eig_max": float(np.max(eigvals)),
    }


def _combined_clock_slice(block_slices: StepC7BlockSlices) -> slice:
    """Return the contiguous clock-bias slice for C7 state layouts."""

    if int(block_slices.ue_clock.stop or 0) != int(block_slices.satellite_clock.start or 0):
        raise ValueError("C7 expects adjacent UE and satellite clock blocks.")
    return slice(block_slices.ue_clock.start, block_slices.satellite_clock.stop)


def _c7_safeguard_diagnostics(
    update: np.ndarray,
    covariance: np.ndarray,
    block_slices: StepC7BlockSlices,
    num_users: int,
    objective_before: float,
    objective_after_full_update: float,
    finite_output: bool,
    config: StepC7Config,
) -> dict[str, Any]:
    """Return C7 non-truth safeguard diagnostics."""

    clock_slice = _combined_clock_slice(block_slices)
    clock_update = update[clock_slice]
    drift_update = update[block_slices.clock_drift] if _slice_length(block_slices.clock_drift) else np.asarray([], dtype=float)
    p_clock_trace = float(np.trace(covariance[clock_slice, clock_slice]))
    clock_update_norm = float(np.linalg.norm(clock_update))
    drift_update_norm = float(np.linalg.norm(drift_update))
    common_clock_component = abs(float(np.mean(clock_update))) if clock_update.size else 0.0
    clock_update_to_cov_scale = clock_update_norm / max(np.sqrt(max(p_clock_trace, 1.0e-18)), 1.0e-18)
    common_ratio = common_clock_component / max(clock_update_norm / max(np.sqrt(clock_update.size), 1.0), 1.0e-18)
    reasons: list[str] = []
    if not finite_output:
        reasons.append("nonfinite_update")
    if objective_after_full_update > objective_before + config.objective_tolerance:
        reasons.append("observable_objective_not_decreased")
    if config.single_user_clock_safeguard and num_users < 2 and clock_update_norm > 0.0:
        reasons.append("single_user_clock_update_not_observable")
    if clock_update_to_cov_scale > config.clock_update_covariance_sigma_limit:
        reasons.append("clock_update_exceeds_covariance_scale")
    if common_ratio > config.common_clock_ratio_limit and common_clock_component > 0.0:
        reasons.append("large_common_clock_component")
    return {
        "nis": objective_before,
        "clock_update_to_cov_scale": clock_update_to_cov_scale,
        "common_clock_component": common_clock_component,
        "common_clock_ratio": common_ratio,
        "drift_update_norm_before_fallback": drift_update_norm,
        "safeguard_failed": bool(reasons),
        "safeguard_reasons": reasons,
        "truth_state_used_for_safeguard": False,
    }


def step_c7_residual_cov_sync_safeguard_refinement(
    initial_state: np.ndarray,
    jacobian: np.ndarray,
    residual: np.ndarray,
    sigmas: np.ndarray,
    block_slices: StepC7BlockSlices,
    *,
    num_users: int,
    residual_at_state: Callable[[np.ndarray], np.ndarray] | None = None,
    config: StepC7Config | None = None,
) -> EstimatorResult:
    """Run C7 residual-scaled block-covariance Step 3 with sync safeguard."""

    cfg = config or StepC7Config()
    state = np.asarray(initial_state, dtype=float).copy()
    jac = np.asarray(jacobian, dtype=float)
    res = np.asarray(residual, dtype=float)
    sigma = np.asarray(sigmas, dtype=float)
    _validate_c7_inputs(state, jac, res, sigma, block_slices, num_users, cfg)

    covariance, covariance_info = step_c7_residual_scaled_block_covariance(
        jac,
        res,
        sigma,
        block_slices,
        config=cfg,
    )
    p_inv = np.linalg.pinv(covariance, rcond=cfg.covariance_rcond)
    r_inv_diag = 1.0 / np.square(sigma)
    information = jac.T @ (jac * r_inv_diag[:, None])
    normal = information + p_inv
    rhs = jac.T @ (r_inv_diag * res)
    raw_update = np.linalg.pinv(normal, rcond=cfg.update_rcond) @ rhs

    def residual_for(candidate_state: np.ndarray) -> np.ndarray:
        if residual_at_state is not None:
            return np.asarray(residual_at_state(candidate_state), dtype=float)
        return res - jac @ (candidate_state - state)

    full_candidate = state + raw_update
    full_residual_after = residual_for(full_candidate)
    objective_before = float(np.sum(np.square(res / sigma)))
    residual_cost_after_full = float(np.sum(np.square(full_residual_after / sigma)))
    prior_cost_after_full = float(raw_update.T @ p_inv @ raw_update)
    objective_after_full = residual_cost_after_full + prior_cost_after_full
    finite_full = bool(np.all(np.isfinite(full_candidate)) and np.isfinite(objective_after_full))
    safeguard = _c7_safeguard_diagnostics(
        raw_update,
        covariance,
        block_slices,
        num_users,
        objective_before,
        objective_after_full,
        finite_full,
        cfg,
    )

    update = raw_update.copy()
    fallback_behavior = "none"
    fallback_event = False
    affected_state_blocks: list[str] = []
    if cfg.sync_safeguard and safeguard["safeguard_failed"]:
        update[block_slices.ue_clock] = 0.0
        update[block_slices.satellite_clock] = 0.0
        affected_state_blocks.extend(["ue_clock", "satellite_clock"])
        if _slice_length(block_slices.clock_drift) > 0:
            update[block_slices.clock_drift] = 0.0
            affected_state_blocks.append("clock_drift")
        fallback_behavior = "clock_and_drift_reverted_to_step_b"
        fallback_event = True

    final_state = state + update
    residual_after = residual_for(final_state)
    residual_cost_after = float(np.sum(np.square(residual_after / sigma)))
    prior_cost = float(update.T @ p_inv @ update)
    objective_after = residual_cost_after + prior_cost
    position_stats = _block_stats(covariance, block_slices.position)
    ue_clock_stats = _block_stats(covariance, block_slices.ue_clock)
    satellite_clock_stats = _block_stats(covariance, block_slices.satellite_clock)
    clock_stats = _block_stats(covariance, _combined_clock_slice(block_slices))
    drift_stats = _block_stats(covariance, block_slices.clock_drift)
    clock_update = update[_combined_clock_slice(block_slices)]
    diagnostics = {
        "stage": "step3_residual_cov_sync_safeguard",
        "estimator_mode": STEP_C7_ESTIMATOR_MODE,
        "map_acceptance_mode": "nontruth_sync_safeguard",
        "map_covariance_mode": "residual_scaled_lm_block_diagonal",
        "truth_state_used_for_acceptance": False,
        "truth_state_used_for_covariance": False,
        "truth_state_used_for_safeguard": False,
        "truth_state_used_for_diagnostics": False,
        "residual_scaled_covariance_formula": "sigma_hat_squared * pinv(J.T R^-1 J + lambda I)",
        "sigma_hat_squared_formula": "r.T R^-1 r / max(1, N_z - N_theta)",
        "status": "updated_with_clock_fallback" if fallback_event else "updated",
        "converged": True,
        "numerical_failure": not bool(np.all(np.isfinite(final_state)) and np.isfinite(objective_after)),
        "update_completed": True,
        "accepted_steps": int(objective_after <= objective_before + cfg.objective_tolerance),
        "rejected_steps": int(objective_after > objective_before + cfg.objective_tolerance),
        "objective_before": objective_before,
        "objective_after": objective_after,
        "objective_after_full_update": objective_after_full,
        "objective_decreased": objective_after <= objective_before + cfg.objective_tolerance,
        "residual_cost_before": objective_before,
        "residual_cost_after": residual_cost_after,
        "residual_cost_after_full_update": residual_cost_after_full,
        "prior_cost": prior_cost,
        "prior_cost_after_full_update": prior_cost_after_full,
        "fallback_event": fallback_event,
        "fallback_behavior": fallback_behavior,
        "fallback_trigger": ";".join(safeguard["safeguard_reasons"]) if fallback_event else "none",
        "fallback_reason": safeguard["safeguard_reasons"][0] if fallback_event and safeguard["safeguard_reasons"] else "none",
        "affected_state_blocks": affected_state_blocks,
        "safeguard": safeguard,
        "raw_position_update_norm": float(np.linalg.norm(raw_update[block_slices.position])),
        "raw_ue_clock_update_norm": float(np.linalg.norm(raw_update[block_slices.ue_clock])),
        "raw_satellite_clock_update_norm": float(np.linalg.norm(raw_update[block_slices.satellite_clock])),
        "raw_clock_drift_update_norm": float(np.linalg.norm(raw_update[block_slices.clock_drift])),
        "position_update_norm": float(np.linalg.norm(update[block_slices.position])),
        "ue_clock_update_norm": float(np.linalg.norm(update[block_slices.ue_clock])),
        "satellite_clock_update_norm": float(np.linalg.norm(update[block_slices.satellite_clock])),
        "clock_drift_update_norm": float(np.linalg.norm(update[block_slices.clock_drift])),
        "common_clock_update_component": abs(float(np.mean(clock_update))) if clock_update.size else 0.0,
        "normal_rank": int(np.linalg.matrix_rank(normal)),
        "information_rank": int(np.linalg.matrix_rank(information)),
        "normal_condition_number": float(np.linalg.cond(normal)),
        "p_position_trace": position_stats["trace"],
        "p_position_eig_min": position_stats["eig_min"],
        "p_position_eig_max": position_stats["eig_max"],
        "p_ue_clock_trace": ue_clock_stats["trace"],
        "p_satellite_clock_trace": satellite_clock_stats["trace"],
        "p_clock_trace": clock_stats["trace"],
        "p_clock_eig_min": clock_stats["eig_min"],
        "p_clock_eig_max": clock_stats["eig_max"],
        "p_clock_drift_trace": drift_stats["trace"],
        "p_clock_drift_eig_min": drift_stats["eig_min"],
        "p_clock_drift_eig_max": drift_stats["eig_max"],
        "clock_drift_prior_scale": cfg.drift_floor_km2_per_s2,
        **covariance_info,
    }
    return EstimatorResult(
        theta=final_state,
        success=not diagnostics["numerical_failure"],
        covariance=covariance,
        diagnostics=diagnostics,
    )


def identity_theta_state_model(theta_dim: int, process_noise_std_km: float = 1e-5) -> V24StateModel:
    """Return x=theta, F=I, Pi=I with diagonal process covariance."""

    if theta_dim < 1:
        raise ValueError("theta_dim must be at least 1.")
    if process_noise_std_km < 0.0:
        raise ValueError("process_noise_std_km must be nonnegative.")
    return V24StateModel(
        f_matrix=np.eye(theta_dim, dtype=float),
        q_covariance=(float(process_noise_std_km) ** 2) * np.eye(theta_dim, dtype=float),
        pi_matrix=np.eye(theta_dim, dtype=float),
    )


def deterministic_position_initialization(scenario: V24ScenarioConfig) -> np.ndarray:
    """Return non-truth-centered deterministic UE position initialization."""

    satellite_positions = np.asarray(scenario.satellite_positions_km, dtype=float)
    mean_satellite = np.mean(satellite_positions, axis=0)
    norm = float(np.linalg.norm(mean_satellite))
    if norm > 1000.0:
        base = mean_satellite / norm * 6371.0
        offsets = np.linspace(-0.15, 0.15, scenario.num_users)
        return np.vstack([base + np.array([offset, -offset, 0.0]) for offset in offsets])
    angles = np.linspace(0.0, 2.0 * np.pi, scenario.num_users, endpoint=False)
    radius = 0.1
    return np.column_stack(
        [
            radius * np.cos(angles),
            radius * np.sin(angles),
            np.zeros(scenario.num_users, dtype=float),
        ]
    )


def deterministic_position_initialization_candidates(scenario: V24ScenarioConfig) -> list[np.ndarray]:
    """Return deterministic non-truth-centered UE position initialization candidates."""

    base = deterministic_position_initialization(scenario)
    if scenario.num_users < 1:
        raise ValueError("num_users must be at least 1.")
    reference = base[0]
    radial_norm = float(np.linalg.norm(reference))
    if radial_norm > 1000.0:
        up = reference / radial_norm
        trial_axis = np.array([0.0, 0.0, 1.0], dtype=float)
        if abs(float(np.dot(up, trial_axis))) > 0.9:
            trial_axis = np.array([0.0, 1.0, 0.0], dtype=float)
        east = np.cross(trial_axis, up)
        east = east / np.linalg.norm(east)
        north = np.cross(up, east)
    else:
        east = np.array([1.0, 0.0, 0.0], dtype=float)
        north = np.array([0.0, 1.0, 0.0], dtype=float)
    shifts = [
        np.zeros(3, dtype=float),
        0.25 * east,
        -0.25 * east,
        0.25 * north,
        -0.25 * north,
        0.5 * (east + north),
        -0.5 * (east + north),
    ]
    return [base + shift for shift in shifts]


def coarse_individual_localization(
    scenario: V24ScenarioConfig,
    z: np.ndarray,
    *,
    max_iterations: int = 12,
    tolerance: float = 1e-8,
) -> EstimatorResult:
    """Run Step 1 weighted GN UE localization from DL measurements only."""

    initialization_candidates = deterministic_position_initialization_candidates(scenario)
    positions = initialization_candidates[0].copy()
    z_array = np.asarray(z, dtype=float)
    links = list(scenario.links)
    user_diagnostics = []
    for user_id in range(1, scenario.num_users + 1):
        row_indices = [
            index
            for index, (receiver, transmitter) in enumerate(links)
            if receiver == user_id and transmitter > scenario.num_users
        ]
        if len(row_indices) < 3:
            user_diagnostics.append(
                {
                    "user_id": user_id,
                    "success": False,
                    "status": "rank_deficient_dl_geometry",
                    "iteration_count": 0,
                    "rank": len(row_indices),
                    "residual_norm": None,
                    "step_norm": None,
                }
            )
            continue

        best_position = positions[user_id - 1].copy()
        best_status = "max_iterations"
        best_rank = 0
        best_residual_norm = np.inf
        best_step_norm = np.inf
        best_iteration = 0
        best_candidate_index = 0
        candidate_records = []
        for candidate_index, candidate_positions in enumerate(initialization_candidates):
            position = candidate_positions[user_id - 1].copy()
            status = "max_iterations"
            rank = 0
            residual_norm = np.inf
            step_norm = np.inf
            iteration = 0
            for iteration in range(1, max_iterations + 1):
                predictions = []
                jacobian_rows = []
                sigmas = []
                for row_index in row_indices:
                    _receiver, transmitter = links[row_index]
                    satellite_position = scenario.satellite_positions_km[transmitter - scenario.num_users - 1]
                    diff = position - satellite_position
                    range_km = float(np.linalg.norm(diff))
                    if range_km <= 0.0:
                        raise ValueError("Degenerate zero range in coarse localization.")
                    predictions.append(range_km)
                    jacobian_rows.append(diff / range_km)
                    sigmas.append(float(scenario.range_std_devs_km[row_index]))
                residual = z_array[row_indices] - np.asarray(predictions, dtype=float)
                jac = np.asarray(jacobian_rows, dtype=float)
                rank = int(np.linalg.matrix_rank(jac))
                residual_norm = float(np.linalg.norm(residual / np.asarray(sigmas, dtype=float)))
                if rank < 3:
                    status = "rank_deficient_dl_geometry"
                    break
                normal, rhs = weighted_normal_equations(jac, residual, np.asarray(sigmas, dtype=float))
                try:
                    step = np.linalg.solve(normal, rhs)
                except np.linalg.LinAlgError:
                    step = np.linalg.pinv(normal) @ rhs
                step_norm = float(np.linalg.norm(step))
                position = position + step
                if step_norm < tolerance:
                    status = "converged"
                    break
            predictions = []
            for row_index in row_indices:
                _receiver, transmitter = links[row_index]
                satellite_position = scenario.satellite_positions_km[transmitter - scenario.num_users - 1]
                diff = position - satellite_position
                range_km = float(np.linalg.norm(diff))
                if range_km <= 0.0:
                    raise ValueError("Degenerate zero range in coarse localization.")
                predictions.append(range_km)
            sigmas = np.asarray([float(scenario.range_std_devs_km[row_index]) for row_index in row_indices], dtype=float)
            residual = z_array[row_indices] - np.asarray(predictions, dtype=float)
            residual_norm = float(np.linalg.norm(residual / np.asarray(sigmas, dtype=float)))
            candidate_records.append(
                {
                    "candidate_index": candidate_index,
                    "status": status,
                    "iteration_count": iteration,
                    "rank": rank,
                    "residual_norm": residual_norm,
                    "step_norm": step_norm,
                }
            )
            if residual_norm < best_residual_norm:
                best_position = position
                best_status = status
                best_rank = rank
                best_residual_norm = residual_norm
                best_step_norm = step_norm
                best_iteration = iteration
                best_candidate_index = candidate_index
        positions[user_id - 1] = best_position
        user_diagnostics.append(
            {
                "user_id": user_id,
                "success": best_status == "converged",
                "status": best_status,
                "iteration_count": best_iteration if row_indices else 0,
                "rank": best_rank,
                "residual_norm": best_residual_norm,
                "step_norm": best_step_norm,
                "best_initialization_candidate": best_candidate_index,
                "initialization_candidate_count": len(initialization_candidates),
                "candidate_records": candidate_records,
            }
        )

    theta = pack_v24_theta(
        positions,
        np.zeros(scenario.num_users, dtype=float),
        np.zeros(scenario.num_satellites - 1, dtype=float),
    )
    return EstimatorResult(
        theta=theta,
        success=all(record["success"] for record in user_diagnostics),
        diagnostics={
            "stage": "step1_coarse_individual_dl_gn",
            "initialization_strategy": "deterministic_multistart_satellite_mean_earth_surface_or_origin",
            "initialization_candidate_count": len(initialization_candidates),
            "truth_centered_initialization": False,
            "users": user_diagnostics,
        },
    )


def weighted_cost(residual: np.ndarray, sigmas: np.ndarray) -> float:
    """Return 0.5 * r.T R^-1 r."""

    return 0.5 * float(np.sum((np.asarray(residual, dtype=float) / np.asarray(sigmas, dtype=float)) ** 2))


def joint_lm_jcls(
    scenario: V24ScenarioConfig,
    z: np.ndarray,
    initial_theta: np.ndarray,
    *,
    initial_damping: float = 1e-3,
    max_iterations: int = 25,
    tolerance: float = 1e-8,
) -> EstimatorResult:
    """Run Step 2 weighted LM over the full gauged V24 theta vector."""

    theta = np.asarray(initial_theta, dtype=float).copy()
    sigmas = np.asarray(scenario.range_std_devs_km, dtype=float)
    z_array = np.asarray(z, dtype=float)
    damping = float(initial_damping)
    damping_history = []
    status = "max_iterations"
    accepted_steps = 0
    step_norm = np.inf
    residual_norm = np.inf
    rank = 0
    condition_number = np.inf
    converged = False
    numerical_failure = False
    rank_deficient_seen = False
    iteration = 0
    for iteration in range(1, max_iterations + 1):
        prediction = toa_range_vector_from_theta_km(
            theta,
            scenario.links,
            scenario.satellite_positions_km,
            scenario.num_users,
            scenario.num_satellites,
        )
        residual = z_array - prediction
        jac = analytic_toa_jacobian_km(
            theta,
            scenario.links,
            scenario.satellite_positions_km,
            scenario.num_users,
            scenario.num_satellites,
        )
        rank = int(np.linalg.matrix_rank(jac))
        theta_dim = expected_v24_parameter_dim(scenario.num_users, scenario.num_satellites)
        if rank < theta_dim:
            rank_deficient_seen = True
        normal, rhs = weighted_normal_equations(jac, residual, sigmas, damping=damping)
        condition_number = float(np.linalg.cond(normal))
        if not np.all(np.isfinite(normal)) or not np.all(np.isfinite(rhs)):
            status = "failed"
            numerical_failure = True
            break
        current_cost = weighted_cost(residual, sigmas)
        try:
            step = np.linalg.solve(normal, rhs)
        except np.linalg.LinAlgError:
            step = np.linalg.pinv(normal) @ rhs
        if not np.all(np.isfinite(step)):
            status = "failed"
            numerical_failure = True
            break
        candidate = theta + step
        if not np.all(np.isfinite(candidate)):
            status = "failed"
            numerical_failure = True
            break
        candidate_residual = z_array - toa_range_vector_from_theta_km(
            candidate,
            scenario.links,
            scenario.satellite_positions_km,
            scenario.num_users,
            scenario.num_satellites,
        )
        candidate_cost = weighted_cost(candidate_residual, sigmas)
        if not np.isfinite(candidate_cost):
            status = "failed"
            numerical_failure = True
            break
        accepted = bool(candidate_cost <= current_cost)
        damping_history.append(float(damping))
        if accepted:
            theta = candidate
            accepted_steps += 1
            damping = max(damping / 3.0, 1e-12)
            step_norm = float(np.linalg.norm(step))
            residual_norm = float(np.linalg.norm(candidate_residual / sigmas))
            if step_norm < tolerance:
                status = "rank_deficient_updated" if rank_deficient_seen else "converged"
                converged = not rank_deficient_seen
                break
        else:
            damping = min(damping * 10.0, 1e12)
    else:
        residual_norm = float(
            np.linalg.norm(
                (
                    z_array
                    - toa_range_vector_from_theta_km(
                        theta,
                        scenario.links,
                        scenario.satellite_positions_km,
                        scenario.num_users,
                        scenario.num_satellites,
                    )
                )
                / sigmas
            )
        )
        if accepted_steps > 0:
            status = "rank_deficient_updated" if rank_deficient_seen else "updated_not_converged"

    return EstimatorResult(
        theta=theta,
        success=converged,
        diagnostics={
            "stage": "step2_joint_lm_jcls",
            "status": status,
            "converged": converged,
            "numerical_failure": numerical_failure,
            "iteration_limit_reached": status in {"max_iterations", "updated_not_converged"},
            "iteration_count": iteration,
            "accepted_steps": accepted_steps,
            "damping_history": damping_history,
            "final_damping": float(damping),
            "residual_norm": residual_norm,
            "step_norm": step_norm,
            "rank": rank,
            "rank_deficient_seen": bool(rank_deficient_seen),
            "condition_number": condition_number,
            "reference_satellite_clock_in_state": False,
            "uses_precision_weighting": True,
        },
    )


def initial_covariance_from_linearization(
    scenario: V24ScenarioConfig,
    theta: np.ndarray,
    *,
    diagonal_floor: float = 1e-8,
) -> np.ndarray:
    """Return a full-theta covariance from the local measurement linearization."""

    jac = analytic_toa_jacobian_km(
        theta,
        scenario.links,
        scenario.satellite_positions_km,
        scenario.num_users,
        scenario.num_satellites,
    )
    weights = 1.0 / np.asarray(scenario.range_std_devs_km, dtype=float) ** 2
    information = jac.T @ (weights[:, np.newaxis] * jac)
    regularized = information + diagonal_floor * np.eye(information.shape[0], dtype=float)
    try:
        return np.linalg.inv(regularized)
    except np.linalg.LinAlgError:
        return np.linalg.pinv(regularized)


def dynamic_soft_information_refinement(
    scenario: V24ScenarioConfig,
    measurements: list[np.ndarray],
    initial_theta: np.ndarray,
    *,
    initial_covariance: np.ndarray | None = None,
    state_model: V24StateModel | None = None,
    process_noise_std_km: float = 1e-5,
    upstream_success: bool = True,
    upstream_status: str | None = None,
) -> EstimatorResult:
    """Run Step 3 dynamic SCI/SFI refinement with F, Q, Pi, and information updates."""

    theta_dim = expected_v24_parameter_dim(scenario.num_users, scenario.num_satellites)
    model = state_model or identity_theta_state_model(theta_dim, process_noise_std_km=process_noise_std_km)
    model.validate(theta_dim)
    x = np.asarray(initial_theta, dtype=float).copy()
    if x.shape != (model.f_matrix.shape[0],):
        raise ValueError("initial_theta/state has incompatible shape.")
    upstream_status_value = upstream_status or ("converged" if upstream_success else "unknown")
    if not upstream_success and upstream_status_value in {"rank_deficient", "failed"}:
        return EstimatorResult(
            theta=model.pi_matrix @ x,
            success=False,
            covariance=initial_covariance,
            diagnostics={
                "stage": "step3_dynamic_sci_sfi_information_update",
                "status": "not_updated_upstream_failed",
                "converged": False,
                "numerical_failure": False,
                "update_completed": False,
                "upstream_success": bool(upstream_success),
                "upstream_status": upstream_status_value,
                "state_model": model.model_name,
                "state_dim": int(model.f_matrix.shape[0]),
                "theta_dim": int(theta_dim),
                "f_matrix": model.f_matrix.tolist(),
                "q_covariance_diag": np.diag(model.q_covariance).tolist(),
                "pi_shape": list(model.pi_matrix.shape),
                "process_noise_std_km": float(process_noise_std_km),
                "epoch_count": 0,
                "epochs": [],
                "uses_innovation_z_minus_h_pred": True,
                "truth_derived_covariance": False,
            },
        )
    p = (
        np.asarray(initial_covariance, dtype=float).copy()
        if initial_covariance is not None
        else initial_covariance_from_linearization(scenario, x)
    )
    if p.shape != (x.shape[0], x.shape[0]):
        raise ValueError("initial_covariance has incompatible shape.")

    epoch_diagnostics = []
    update_completed = True
    numerical_failure = False
    for epoch_index, z in enumerate(measurements, start=1):
        x_pred = model.f_matrix @ x
        p_pred = model.f_matrix @ p @ model.f_matrix.T + model.q_covariance
        predicted_trace = float(np.trace(p_pred))
        theta_pred = model.pi_matrix @ x_pred
        h_pred = toa_range_vector_from_theta_km(
            theta_pred,
            scenario.links,
            scenario.satellite_positions_km,
            scenario.num_users,
            scenario.num_satellites,
        )
        jac_theta = analytic_toa_jacobian_km(
            theta_pred,
            scenario.links,
            scenario.satellite_positions_km,
            scenario.num_users,
            scenario.num_satellites,
        )
        jac_x = jac_theta @ model.pi_matrix
        innovation = np.asarray(z, dtype=float) - h_pred
        try:
            x, p = information_form_ekf_update(
                x_pred,
                p_pred,
                h_pred,
                jac_x,
                np.asarray(z, dtype=float),
                scenario.range_std_devs_km,
            )
        except (ValueError, np.linalg.LinAlgError):
            update_completed = False
            numerical_failure = True
            break
        if not np.all(np.isfinite(x)) or not np.all(np.isfinite(p)):
            update_completed = False
            numerical_failure = True
            break
        epoch_diagnostics.append(
            {
                "epoch": epoch_index,
                "innovation_norm": float(np.linalg.norm(innovation / scenario.range_std_devs_km)),
                "predicted_covariance_trace": predicted_trace,
                "posterior_covariance_trace": float(np.trace(p)),
                "covariance_trace_reduction": predicted_trace - float(np.trace(p)),
                "posterior_covariance_condition_number": float(np.linalg.cond(p)),
                "jacobian_rank": int(np.linalg.matrix_rank(jac_x)),
                "status": "updated",
            }
        )
    theta = model.pi_matrix @ x
    if numerical_failure:
        status = "failed_numerical"
    elif not upstream_success:
        status = "updated_upstream_not_converged"
    elif epoch_diagnostics and all(record["jacobian_rank"] == 0 for record in epoch_diagnostics):
        status = "rank_deficient_or_uninformative"
    else:
        status = "updated"
    success = status == "updated"
    return EstimatorResult(
        theta=theta,
        success=success,
        covariance=p,
        diagnostics={
            "stage": "step3_dynamic_sci_sfi_information_update",
            "status": status,
            "converged": success,
            "numerical_failure": numerical_failure,
            "update_completed": update_completed,
            "upstream_success": bool(upstream_success),
            "upstream_status": upstream_status_value,
            "state_model": model.model_name,
            "state_dim": int(model.f_matrix.shape[0]),
            "theta_dim": int(theta_dim),
            "f_matrix": model.f_matrix.tolist(),
            "q_covariance_diag": np.diag(model.q_covariance).tolist(),
            "pi_shape": list(model.pi_matrix.shape),
            "process_noise_std_km": float(process_noise_std_km),
            "epoch_count": len(measurements),
            "epochs": epoch_diagnostics,
            "uses_innovation_z_minus_h_pred": True,
            "truth_derived_covariance": False,
        },
    )
