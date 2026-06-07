"""Package-native V24 three-stage JCLS estimator helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

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
    return np.zeros((scenario.num_users, 3), dtype=float)


def coarse_individual_localization(
    scenario: V24ScenarioConfig,
    z: np.ndarray,
    *,
    max_iterations: int = 12,
    tolerance: float = 1e-8,
) -> EstimatorResult:
    """Run Step 1 weighted GN UE localization from DL measurements only."""

    positions = deterministic_position_initialization(scenario)
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

        position = positions[user_id - 1].copy()
        status = "max_iterations"
        rank = 0
        residual_norm = np.inf
        step_norm = np.inf
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
        positions[user_id - 1] = position
        user_diagnostics.append(
            {
                "user_id": user_id,
                "success": status == "converged",
                "status": status,
                "iteration_count": iteration if row_indices else 0,
                "rank": rank,
                "residual_norm": residual_norm,
                "step_norm": step_norm,
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
            "initialization_strategy": "deterministic_satellite_mean_earth_surface_or_origin",
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
            status = "rank_deficient"
            break
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
                status = "converged"
                converged = True
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
            status = "updated_not_converged"

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
                "posterior_covariance_trace": float(np.trace(p)),
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
