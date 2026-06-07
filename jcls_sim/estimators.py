"""Small estimator helpers for V24 toy-problem tests."""

from __future__ import annotations

import numpy as np

__all__ = [
    "gauss_newton_step",
    "information_form_ekf_update",
    "levenberg_marquardt_step",
    "weighted_normal_equations",
]


def _range_weights_from_std_devs_km(range_std_devs_km: np.ndarray, expected_length: int) -> np.ndarray:
    """Return range-domain precisions 1 / sigma**2."""

    sigmas = np.asarray(range_std_devs_km, dtype=float)
    if sigmas.ndim != 1:
        raise ValueError(f"range_std_devs_km must be a 1-D array, got {sigmas.shape}.")
    if sigmas.shape[0] != expected_length:
        raise ValueError(
            "range_std_devs_km length must equal the number of measurement rows, "
            f"got {sigmas.shape[0]} and {expected_length}."
        )
    if sigmas.shape[0] == 0:
        raise ValueError("range_std_devs_km must contain at least one standard deviation.")
    if np.any(sigmas <= 0):
        raise ValueError("range_std_devs_km must contain strictly positive standard deviations.")
    return 1.0 / sigmas**2


def _validate_damping(damping: float) -> float:
    """Return a validated nonnegative damping scalar."""

    damping_array = np.asarray(damping, dtype=float)
    if damping_array.ndim != 0:
        raise ValueError(f"damping must be a scalar, got {damping_array.shape}.")
    damping_value = float(damping_array)
    if not np.isfinite(damping_value) or damping_value < 0.0:
        raise ValueError(f"damping must be nonnegative, got {damping}.")
    return damping_value


def weighted_normal_equations(
    jacobian: np.ndarray,
    residual: np.ndarray,
    range_std_devs_km: np.ndarray,
    damping: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Return precision-weighted normal matrix and right-hand side."""

    jac = np.asarray(jacobian, dtype=float)
    if jac.ndim != 2:
        raise ValueError(f"jacobian must be a 2-D array, got {jac.shape}.")
    res = np.asarray(residual, dtype=float)
    if res.ndim != 1:
        raise ValueError(f"residual must be a 1-D array, got {res.shape}.")
    if res.shape[0] != jac.shape[0]:
        raise ValueError(
            "residual length must equal the number of Jacobian rows, "
            f"got {res.shape[0]} and {jac.shape[0]}."
        )
    damping_value = _validate_damping(damping)
    weights = _range_weights_from_std_devs_km(range_std_devs_km, jac.shape[0])

    normal = jac.T @ (weights[:, np.newaxis] * jac)
    rhs = jac.T @ (weights * res)
    if damping_value > 0.0:
        normal = normal + damping_value * np.eye(jac.shape[1], dtype=float)
    return normal, rhs


def _solve_weighted_step(
    x: np.ndarray,
    residual: np.ndarray,
    jacobian: np.ndarray,
    range_std_devs_km: np.ndarray,
    damping: float,
) -> np.ndarray:
    """Return x plus the weighted least-squares increment."""

    normal, rhs = weighted_normal_equations(jacobian, residual, range_std_devs_km, damping=damping)
    x_array = np.asarray(x, dtype=float)
    if x_array.ndim != 1:
        raise ValueError(f"x must be a 1-D array, got {x_array.shape}.")
    if x_array.shape[0] != normal.shape[0]:
        raise ValueError(
            "x length must equal the number of Jacobian columns, "
            f"got {x_array.shape[0]} and {normal.shape[0]}."
        )
    try:
        step = np.linalg.solve(normal, rhs)
    except np.linalg.LinAlgError:
        step = np.linalg.pinv(normal) @ rhs
    return x_array + step


def gauss_newton_step(
    x: np.ndarray,
    residual: np.ndarray,
    jacobian: np.ndarray,
    range_std_devs_km: np.ndarray,
) -> np.ndarray:
    """Return one precision-weighted Gauss-Newton update."""

    return _solve_weighted_step(x, residual, jacobian, range_std_devs_km, damping=0.0)


def levenberg_marquardt_step(
    x: np.ndarray,
    residual: np.ndarray,
    jacobian: np.ndarray,
    range_std_devs_km: np.ndarray,
    damping: float,
) -> np.ndarray:
    """Return one damped precision-weighted Levenberg-Marquardt update."""

    return _solve_weighted_step(x, residual, jacobian, range_std_devs_km, damping=damping)


def information_form_ekf_update(
    x_pred: np.ndarray,
    p_pred: np.ndarray,
    h_pred: np.ndarray,
    jacobian: np.ndarray,
    z: np.ndarray,
    range_std_devs_km: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Return the information-form EKF posterior mean and covariance."""

    x_pred_array = np.asarray(x_pred, dtype=float)
    if x_pred_array.ndim != 1:
        raise ValueError(f"x_pred must be a 1-D array, got {x_pred_array.shape}.")
    state_dim = x_pred_array.shape[0]

    p_pred_array = np.asarray(p_pred, dtype=float)
    if p_pred_array.ndim != 2 or p_pred_array.shape != (state_dim, state_dim):
        raise ValueError(f"p_pred must have shape ({state_dim}, {state_dim}), got {p_pred_array.shape}.")

    jac = np.asarray(jacobian, dtype=float)
    if jac.ndim != 2:
        raise ValueError(f"jacobian must be a 2-D array, got {jac.shape}.")
    if jac.shape[1] != state_dim:
        raise ValueError(
            "jacobian columns must equal x_pred length, "
            f"got {jac.shape[1]} and {state_dim}."
        )

    h_pred_array = np.asarray(h_pred, dtype=float)
    if h_pred_array.ndim != 1:
        raise ValueError(f"h_pred must be a 1-D array, got {h_pred_array.shape}.")
    z_array = np.asarray(z, dtype=float)
    if z_array.ndim != 1:
        raise ValueError(f"z must be a 1-D array, got {z_array.shape}.")
    if h_pred_array.shape[0] != jac.shape[0]:
        raise ValueError(
            "h_pred length must equal the number of Jacobian rows, "
            f"got {h_pred_array.shape[0]} and {jac.shape[0]}."
        )
    if z_array.shape[0] != jac.shape[0]:
        raise ValueError(
            "z length must equal the number of Jacobian rows, "
            f"got {z_array.shape[0]} and {jac.shape[0]}."
        )

    weights = _range_weights_from_std_devs_km(range_std_devs_km, jac.shape[0])
    innovation = z_array - h_pred_array

    try:
        p_pred_precision = np.linalg.inv(p_pred_array)
    except np.linalg.LinAlgError:
        p_pred_precision = np.linalg.pinv(p_pred_array)

    posterior_precision = p_pred_precision + jac.T @ (weights[:, np.newaxis] * jac)
    try:
        posterior_cov = np.linalg.inv(posterior_precision)
    except np.linalg.LinAlgError:
        posterior_cov = np.linalg.pinv(posterior_precision)

    posterior_mean = x_pred_array + posterior_cov @ (jac.T @ (weights * innovation))
    return posterior_mean, posterior_cov
