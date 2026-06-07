"""V24 parameter-vector helpers for JCLS simulation code."""

from __future__ import annotations

import numpy as np

from .gauge import expected_v24_parameter_dim, v24_clock_node_ids


def _validate_counts(num_users: int, num_satellites: int) -> None:
    """Validate positive user and satellite counts."""

    if num_users < 1:
        raise ValueError(f"num_users must be at least 1, got {num_users}.")
    if num_satellites < 1:
        raise ValueError(f"num_satellites must be at least 1, got {num_satellites}.")


def ue_position_param_names(num_users: int) -> list[str]:
    """Return UE position parameter names in V24 order."""

    if num_users < 1:
        raise ValueError(f"num_users must be at least 1, got {num_users}.")
    return [
        f"{axis}_{user_id}"
        for user_id in range(1, num_users + 1)
        for axis in ("x", "y", "z")
    ]


def ue_clock_param_names(num_users: int) -> list[str]:
    """Return UE clock parameter names: delta_1, ..., delta_Nu."""

    if num_users < 1:
        raise ValueError(f"num_users must be at least 1, got {num_users}.")
    return [f"delta_{user_id}" for user_id in range(1, num_users + 1)]


def non_reference_satellite_clock_param_names(num_users: int, num_satellites: int) -> list[str]:
    """Return non-reference satellite clock names in V24 order."""

    _validate_counts(num_users, num_satellites)
    non_reference_ids = [
        node_id
        for node_id in v24_clock_node_ids(num_users, num_satellites)
        if node_id > num_users
    ]
    return [f"delta_{node_id}" for node_id in non_reference_ids]


def v24_parameter_names(num_users: int, num_satellites: int) -> list[str]:
    """Return V24 parameter names: UE positions, UE clocks, non-reference satellite clocks."""

    _validate_counts(num_users, num_satellites)
    return (
        ue_position_param_names(num_users)
        + ue_clock_param_names(num_users)
        + non_reference_satellite_clock_param_names(num_users, num_satellites)
    )


def v24_parameter_index(num_users: int, num_satellites: int) -> dict[str, int]:
    """Return a mapping from V24 parameter name to vector index."""

    return {
        name: index
        for index, name in enumerate(v24_parameter_names(num_users, num_satellites))
    }


def pack_v24_theta(
    ue_positions_km: np.ndarray,
    ue_clocks_km: np.ndarray,
    non_reference_satellite_clocks_km: np.ndarray,
) -> np.ndarray:
    """Pack a V24 theta vector in manuscript order."""

    positions = np.asarray(ue_positions_km, dtype=float)
    ue_clocks = np.asarray(ue_clocks_km, dtype=float)
    satellite_clocks = np.asarray(non_reference_satellite_clocks_km, dtype=float)
    if positions.ndim != 2 or positions.shape[1] != 3:
        raise ValueError(f"ue_positions_km must have shape (Nu, 3), got {positions.shape}.")
    num_users = positions.shape[0]
    if num_users < 1:
        raise ValueError("ue_positions_km must contain at least one UE position.")
    if ue_clocks.shape != (num_users,):
        raise ValueError(f"ue_clocks_km must have shape ({num_users},), got {ue_clocks.shape}.")
    if satellite_clocks.ndim != 1:
        raise ValueError(
            "non_reference_satellite_clocks_km must be a 1-D array, "
            f"got {satellite_clocks.shape}."
        )
    num_satellites = satellite_clocks.shape[0] + 1
    return np.concatenate([positions.reshape(-1), ue_clocks, satellite_clocks])


def unpack_v24_theta(
    theta: np.ndarray,
    num_users: int,
    num_satellites: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Unpack theta into UE positions, UE clocks, and non-reference satellite clocks."""

    _validate_counts(num_users, num_satellites)
    theta_array = np.asarray(theta, dtype=float)
    expected_length = expected_v24_parameter_dim(num_users, num_satellites)
    if theta_array.ndim != 1 or theta_array.shape[0] != expected_length:
        raise ValueError(f"theta must have shape ({expected_length},), got {theta_array.shape}.")
    position_end = 3 * num_users
    ue_clock_end = position_end + num_users
    ue_positions = theta_array[:position_end].reshape(num_users, 3)
    ue_clocks = theta_array[position_end:ue_clock_end]
    non_reference_satellite_clocks = theta_array[ue_clock_end:]
    return ue_positions, ue_clocks, non_reference_satellite_clocks
