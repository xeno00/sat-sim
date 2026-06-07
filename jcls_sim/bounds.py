"""Bound extraction helpers for full-gauged V24 FIMs and covariances."""

from __future__ import annotations

import math

import numpy as np

from .gauge import expected_v24_parameter_dim


def _validate_counts(num_users: int, num_satellites: int) -> None:
    """Validate positive user and satellite counts."""

    if num_users < 1:
        raise ValueError(f"num_users must be at least 1, got {num_users}.")
    if num_satellites < 1:
        raise ValueError(f"num_satellites must be at least 1, got {num_satellites}.")


def _validate_square_matrix(matrix: np.ndarray, name: str) -> np.ndarray:
    """Return a validated square matrix."""

    array = np.asarray(matrix, dtype=float)
    if array.ndim != 2 or array.shape[0] != array.shape[1]:
        raise ValueError(f"{name} must be a square matrix, got {array.shape}.")
    return array


def _validate_full_v24_covariance(
    covariance: np.ndarray,
    num_users: int,
    num_satellites: int,
) -> np.ndarray:
    """Return a covariance matrix with full V24 gauged dimension."""

    _validate_counts(num_users, num_satellites)
    cov = _validate_square_matrix(covariance, "covariance")
    expected_dim = expected_v24_parameter_dim(num_users, num_satellites)
    if cov.shape != (expected_dim, expected_dim):
        raise ValueError(f"covariance must have shape ({expected_dim}, {expected_dim}), got {cov.shape}.")
    return cov


def _sqrt_nonnegative(values: np.ndarray, *, tol: float = 1e-12) -> np.ndarray:
    """Return square roots, allowing only tiny numerical negative values."""

    array = np.asarray(values, dtype=float)
    if np.any(array < -tol):
        raise ValueError("covariance diagonal contains clearly negative entries.")
    return np.sqrt(np.maximum(array, 0.0))


def covariance_from_fim(
    fim: np.ndarray,
    rcond: float = 1e-12,
) -> tuple[np.ndarray, dict[str, float | int | str | bool]]:
    """Return covariance from a full gauged FIM and rank/method metadata."""

    fim_array = _validate_square_matrix(fim, "fim")
    if rcond <= 0.0:
        raise ValueError(f"rcond must be positive, got {rcond}.")
    dimension = fim_array.shape[0]
    rank = int(np.linalg.matrix_rank(fim_array, tol=rcond))
    try:
        condition_number = float(np.linalg.cond(fim_array))
    except np.linalg.LinAlgError:
        condition_number = math.inf
    full_rank = rank == dimension
    well_conditioned = full_rank and math.isfinite(condition_number) and condition_number <= 1.0 / rcond
    if well_conditioned:
        covariance = np.linalg.inv(fim_array)
        method = "inverse"
    else:
        covariance = np.linalg.pinv(fim_array, rcond=rcond)
        method = "pinv"
    metadata: dict[str, float | int | str | bool] = {
        "rank": rank,
        "dimension": dimension,
        "method": method,
        "condition_number": condition_number,
        "rcond": float(rcond),
        "full_rank": full_rank,
        "well_conditioned": well_conditioned,
    }
    return covariance, metadata


def ue_position_block_indices(num_users: int) -> list[slice]:
    """Return per-UE 3D position block slices in V24 theta order."""

    if num_users < 1:
        raise ValueError(f"num_users must be at least 1, got {num_users}.")
    return [slice(3 * user_index, 3 * (user_index + 1)) for user_index in range(num_users)]


def clock_block_slice(num_users: int, num_satellites: int) -> slice:
    """Return slice for all estimated non-reference clock parameters."""

    _validate_counts(num_users, num_satellites)
    return slice(3 * num_users, expected_v24_parameter_dim(num_users, num_satellites))


def ue_clock_block_slice(num_users: int, num_satellites: int) -> slice:
    """Return slice for UE clock parameters in V24 theta order."""

    _validate_counts(num_users, num_satellites)
    return slice(3 * num_users, 4 * num_users)


def non_reference_satellite_clock_block_slice(num_users: int, num_satellites: int) -> slice:
    """Return slice for non-reference satellite clock parameters."""

    _validate_counts(num_users, num_satellites)
    return slice(4 * num_users, expected_v24_parameter_dim(num_users, num_satellites))


def per_user_peb_from_covariance(
    covariance: np.ndarray,
    num_users: int,
    num_satellites: int,
) -> np.ndarray:
    """Return per-UE PEBs from a full V24 gauged covariance."""

    cov = _validate_full_v24_covariance(covariance, num_users, num_satellites)
    pebs = []
    for block_slice in ue_position_block_indices(num_users):
        block = cov[block_slice, block_slice]
        trace_value = float(np.trace(block))
        if trace_value < -1e-12:
            raise ValueError("position covariance block has negative trace.")
        pebs.append(math.sqrt(max(trace_value, 0.0)))
    return np.array(pebs, dtype=float)


def average_ue_peb_from_covariance(
    covariance: np.ndarray,
    num_users: int,
    num_satellites: int,
) -> float:
    """Return average UE PEB from a full V24 gauged covariance."""

    return float(np.mean(per_user_peb_from_covariance(covariance, num_users, num_satellites)))


def clock_std_bounds_from_covariance(
    covariance: np.ndarray,
    num_users: int,
    num_satellites: int,
    group: str = "all_non_reference",
) -> np.ndarray:
    """Return per-clock standard-deviation bounds for a selected V24 clock group."""

    cov = _validate_full_v24_covariance(covariance, num_users, num_satellites)
    if group == "all_non_reference":
        selected_slice = clock_block_slice(num_users, num_satellites)
    elif group == "ue":
        selected_slice = ue_clock_block_slice(num_users, num_satellites)
    elif group == "satellite_non_reference":
        selected_slice = non_reference_satellite_clock_block_slice(num_users, num_satellites)
    else:
        raise ValueError(
            "group must be one of 'all_non_reference', 'ue', "
            f"or 'satellite_non_reference', got {group!r}."
        )
    diagonal = np.diag(cov[selected_slice, selected_slice])
    if diagonal.size == 0:
        raise ValueError(f"group={group!r} selected no clock parameters.")
    return _sqrt_nonnegative(diagonal)


def average_clock_bound_from_covariance(
    covariance: np.ndarray,
    num_users: int,
    num_satellites: int,
    group: str = "all_non_reference",
) -> float:
    """Return average clock standard-deviation bound for a selected group."""

    return float(np.mean(clock_std_bounds_from_covariance(covariance, num_users, num_satellites, group=group)))
