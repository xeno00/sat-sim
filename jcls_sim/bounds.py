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


def _indices_from_slice(parameter_slice: slice, dimension: int) -> list[int]:
    """Return explicit indices selected by a slice."""

    return list(range(*parameter_slice.indices(dimension)))


def ue_position_parameter_indices(num_users: int) -> list[int]:
    """Return all UE position parameter indices in V24 theta order."""

    if num_users < 1:
        raise ValueError(f"num_users must be at least 1, got {num_users}.")
    return list(range(3 * num_users))


def clock_parameter_indices(
    num_users: int,
    num_satellites: int,
    group: str = "all_non_reference",
) -> list[int]:
    """Return clock parameter indices for a selected V24 clock group."""

    expected_dim = expected_v24_parameter_dim(num_users, num_satellites)
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
    indices = _indices_from_slice(selected_slice, expected_dim)
    if not indices:
        raise ValueError(f"group={group!r} selected no clock parameters.")
    return indices


def subspace_is_estimable_from_fim(
    fim: np.ndarray,
    parameter_indices: list[int] | tuple[int, ...] | np.ndarray,
    rcond: float = 1e-12,
    component_tol: float | None = None,
) -> bool:
    """Return whether selected coordinates avoid the FIM nullspace."""

    fim_array = _validate_square_matrix(fim, "fim")
    if rcond <= 0.0:
        raise ValueError(f"rcond must be positive, got {rcond}.")
    indices = np.asarray(parameter_indices, dtype=int)
    if indices.ndim != 1 or indices.size == 0:
        raise ValueError("parameter_indices must be a nonempty one-dimensional sequence.")
    dimension = fim_array.shape[0]
    if np.any(indices < 0) or np.any(indices >= dimension):
        raise ValueError(f"parameter_indices must be in [0, {dimension - 1}].")

    singular_values = np.linalg.svd(fim_array, compute_uv=False)
    rank = int(np.sum(singular_values > rcond))
    nullity = dimension - rank
    if nullity == 0:
        return True

    _, _, vh = np.linalg.svd(fim_array, full_matrices=True)
    nullspace = vh[rank:].T
    selected_nullspace = nullspace[indices, :]
    tolerance = component_tol if component_tol is not None else max(rcond, np.finfo(float).eps * dimension)
    return bool(np.linalg.norm(selected_nullspace, ord="fro") <= tolerance)


def manuscript_crlb_reportability_from_fim(
    fim: np.ndarray,
    num_users: int,
    num_satellites: int,
    rcond: float = 1e-12,
) -> dict[str, bool | int | str]:
    """Return whether V24 manuscript-style CRLB bounds are finite/reportable."""

    _validate_counts(num_users, num_satellites)
    fim_array = _validate_square_matrix(fim, "fim")
    expected_dim = expected_v24_parameter_dim(num_users, num_satellites)
    if fim_array.shape != (expected_dim, expected_dim):
        raise ValueError(f"fim must have shape ({expected_dim}, {expected_dim}), got {fim_array.shape}.")
    rank = int(np.linalg.matrix_rank(fim_array, tol=rcond))
    nullity = expected_dim - rank
    full_rank = nullity == 0
    position_estimable = subspace_is_estimable_from_fim(
        fim_array,
        ue_position_parameter_indices(num_users),
        rcond=rcond,
    )
    clock_estimable = subspace_is_estimable_from_fim(
        fim_array,
        clock_parameter_indices(num_users, num_satellites),
        rcond=rcond,
    )
    manuscript_bounds_defined = full_rank or (position_estimable and clock_estimable)
    if full_rank:
        status = "finite_full_rank"
    elif manuscript_bounds_defined:
        status = "finite_estimable_subspace_rank_deficient"
    else:
        status = "undefined_rank_deficient"
    return {
        "dimension": expected_dim,
        "rank": rank,
        "nullity": nullity,
        "full_rank": full_rank,
        "ue_position_subspace_estimable": position_estimable,
        "clock_subspace_estimable": clock_estimable,
        "manuscript_bounds_defined": manuscript_bounds_defined,
        "manuscript_crlb_status": status,
    }


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
