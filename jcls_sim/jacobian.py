"""Jacobian helpers for V24 range-domain TOA measurements."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from .gauge import expected_v24_parameter_dim, reference_satellite_node_id
from .measurements import toa_range_model_km
from .parameters import unpack_v24_theta, v24_parameter_index


def _validate_counts(num_users: int, num_satellites: int) -> None:
    """Validate positive user and satellite counts."""

    if num_users < 1:
        raise ValueError(f"num_users must be at least 1, got {num_users}.")
    if num_satellites < 1:
        raise ValueError(f"num_satellites must be at least 1, got {num_satellites}.")


def _validate_satellite_positions(
    satellite_positions_km: np.ndarray,
    num_satellites: int,
) -> np.ndarray:
    """Return validated known satellite positions."""

    satellite_positions = np.asarray(satellite_positions_km, dtype=float)
    expected_shape = (num_satellites, 3)
    if satellite_positions.shape != expected_shape:
        raise ValueError(f"satellite_positions_km must have shape {expected_shape}, got {satellite_positions.shape}.")
    return satellite_positions


def _validate_node_id(node_id: int, num_users: int, num_satellites: int) -> None:
    """Validate a UE or satellite node id."""

    if node_id < 1 or node_id > num_users + num_satellites:
        raise ValueError(f"node_id must be in [1, {num_users + num_satellites}], got {node_id}.")


def node_position_km(
    node_id: int,
    ue_positions_km: np.ndarray,
    satellite_positions_km: np.ndarray,
    num_users: int,
    num_satellites: int,
) -> np.ndarray:
    """Return a UE or known satellite position in kilometers."""

    _validate_node_id(node_id, num_users, num_satellites)
    if node_id <= num_users:
        return np.asarray(ue_positions_km, dtype=float)[node_id - 1]
    return np.asarray(satellite_positions_km, dtype=float)[node_id - num_users - 1]


def toa_range_vector_from_theta_km(
    theta: np.ndarray,
    links: Sequence[tuple[int, int]],
    satellite_positions_km: np.ndarray,
    num_users: int,
    num_satellites: int,
) -> np.ndarray:
    """Evaluate V24 range-domain TOA measurements from theta."""

    _validate_counts(num_users, num_satellites)
    theta_array = np.asarray(theta, dtype=float)
    expected_dim = expected_v24_parameter_dim(num_users, num_satellites)
    if theta_array.ndim != 1 or theta_array.shape[0] != expected_dim:
        raise ValueError(f"theta must have shape ({expected_dim},), got {theta_array.shape}.")
    satellite_positions = _validate_satellite_positions(satellite_positions_km, num_satellites)
    ue_positions, ue_clocks, non_reference_satellite_clocks = unpack_v24_theta(
        theta_array,
        num_users,
        num_satellites,
    )
    values = []
    for receiver_node_id, transmitter_node_id in links:
        receiver_position = node_position_km(
            receiver_node_id,
            ue_positions,
            satellite_positions,
            num_users,
            num_satellites,
        )
        transmitter_position = node_position_km(
            transmitter_node_id,
            ue_positions,
            satellite_positions,
            num_users,
            num_satellites,
        )
        values.append(
            toa_range_model_km(
                receiver_node_id,
                transmitter_node_id,
                receiver_position,
                transmitter_position,
                ue_clocks,
                non_reference_satellite_clocks,
                num_users,
                num_satellites,
            )
        )
    return np.array(values, dtype=float)


def analytic_toa_jacobian_km(
    theta: np.ndarray,
    links: Sequence[tuple[int, int]],
    satellite_positions_km: np.ndarray,
    num_users: int,
    num_satellites: int,
) -> np.ndarray:
    """Return the analytic Jacobian for V24 range-domain TOA measurements."""

    _validate_counts(num_users, num_satellites)
    theta_array = np.asarray(theta, dtype=float)
    expected_dim = expected_v24_parameter_dim(num_users, num_satellites)
    if theta_array.ndim != 1 or theta_array.shape[0] != expected_dim:
        raise ValueError(f"theta must have shape ({expected_dim},), got {theta_array.shape}.")
    satellite_positions = _validate_satellite_positions(satellite_positions_km, num_satellites)
    ue_positions, _, _ = unpack_v24_theta(theta_array, num_users, num_satellites)
    parameter_index = v24_parameter_index(num_users, num_satellites)
    reference_node_id = reference_satellite_node_id(num_users)
    jacobian = np.zeros((len(links), expected_dim), dtype=float)

    for row_index, (receiver_node_id, transmitter_node_id) in enumerate(links):
        _validate_node_id(receiver_node_id, num_users, num_satellites)
        _validate_node_id(transmitter_node_id, num_users, num_satellites)
        receiver_position = node_position_km(
            receiver_node_id,
            ue_positions,
            satellite_positions,
            num_users,
            num_satellites,
        )
        transmitter_position = node_position_km(
            transmitter_node_id,
            ue_positions,
            satellite_positions,
            num_users,
            num_satellites,
        )
        difference = receiver_position - transmitter_position
        range_km = np.linalg.norm(difference)
        if range_km == 0.0:
            raise ValueError("TOA Jacobian is undefined for zero receiver-transmitter range.")
        direction = difference / range_km

        if receiver_node_id <= num_users:
            for axis_index, axis in enumerate(("x", "y", "z")):
                jacobian[row_index, parameter_index[f"{axis}_{receiver_node_id}"]] += direction[axis_index]
        if transmitter_node_id <= num_users:
            for axis_index, axis in enumerate(("x", "y", "z")):
                jacobian[row_index, parameter_index[f"{axis}_{transmitter_node_id}"]] -= direction[axis_index]

        if receiver_node_id != reference_node_id:
            receiver_clock_name = f"delta_{receiver_node_id}"
            if receiver_clock_name in parameter_index:
                jacobian[row_index, parameter_index[receiver_clock_name]] -= 1.0
        if transmitter_node_id != reference_node_id:
            transmitter_clock_name = f"delta_{transmitter_node_id}"
            if transmitter_clock_name in parameter_index:
                jacobian[row_index, parameter_index[transmitter_clock_name]] += 1.0

    return jacobian
