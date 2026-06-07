"""Fisher-information helpers for V24 JCLS simulations."""

from __future__ import annotations

import numpy as np


def range_covariance_from_std_devs_km(range_std_devs_km: np.ndarray) -> np.ndarray:
    """Return R_z = diag(sigma**2) from range-domain standard deviations."""

    sigmas = np.asarray(range_std_devs_km, dtype=float)
    if sigmas.ndim != 1:
        raise ValueError(f"range_std_devs_km must be a 1-D array, got {sigmas.shape}.")
    if sigmas.shape[0] == 0:
        raise ValueError("range_std_devs_km must contain at least one standard deviation.")
    if np.any(sigmas <= 0):
        raise ValueError("range_std_devs_km must contain strictly positive standard deviations.")
    return np.diag(sigmas**2)


def gaussian_fim_from_jacobian(jacobian: np.ndarray, range_std_devs_km: np.ndarray) -> np.ndarray:
    """Return J_h.T @ R_z^{-1} @ J_h for Gaussian/Rician range noise."""

    jac = np.asarray(jacobian, dtype=float)
    if jac.ndim != 2:
        raise ValueError(f"jacobian must be a 2-D array, got {jac.shape}.")
    covariance = range_covariance_from_std_devs_km(range_std_devs_km)
    if covariance.shape[0] != jac.shape[0]:
        raise ValueError(
            "range_std_devs_km length must equal the number of Jacobian rows, "
            f"got {covariance.shape[0]} and {jac.shape[0]}."
        )
    weights = 1.0 / np.diag(covariance)
    return jac.T @ (weights[:, np.newaxis] * jac)


def fim_rank(information_matrix: np.ndarray, tol: float | None = None) -> int:
    """Return the numerical rank of a Fisher-information matrix."""

    fim = np.asarray(information_matrix, dtype=float)
    if fim.ndim != 2 or fim.shape[0] != fim.shape[1]:
        raise ValueError(f"information_matrix must be square, got {fim.shape}.")
    return int(np.linalg.matrix_rank(fim, tol=tol))
