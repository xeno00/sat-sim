"""Range-domain TOA measurement helpers for V24 JCLS simulations."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from .gauge import reference_satellite_node_id


def _validate_counts(num_users: int, num_satellites: int) -> None:
    """Validate positive user and satellite counts."""

    if num_users < 1:
        raise ValueError(f"num_users must be at least 1, got {num_users}.")
    if num_satellites < 1:
        raise ValueError(f"num_satellites must be at least 1, got {num_satellites}.")


def _validate_position(position_km: np.ndarray | Sequence[float], name: str) -> np.ndarray:
    """Return a validated 3-D position vector in kilometers."""

    position = np.asarray(position_km, dtype=float)
    if position.shape != (3,):
        raise ValueError(f"{name} must have shape (3,), got {position.shape}.")
    return position


def _validate_clock_vectors(
    ue_clocks_km: np.ndarray,
    non_reference_satellite_clocks_km: np.ndarray,
    num_users: int,
    num_satellites: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Return validated V24 clock vectors."""

    _validate_counts(num_users, num_satellites)
    ue_clocks = np.asarray(ue_clocks_km, dtype=float)
    satellite_clocks = np.asarray(non_reference_satellite_clocks_km, dtype=float)
    if ue_clocks.shape != (num_users,):
        raise ValueError(f"ue_clocks_km must have shape ({num_users},), got {ue_clocks.shape}.")
    expected_satellite_shape = (num_satellites - 1,)
    if satellite_clocks.shape != expected_satellite_shape:
        raise ValueError(
            "non_reference_satellite_clocks_km must have shape "
            f"{expected_satellite_shape}, got {satellite_clocks.shape}."
        )
    return ue_clocks, satellite_clocks


def euclidean_range_km(
    receiver_position_km: np.ndarray | Sequence[float],
    transmitter_position_km: np.ndarray | Sequence[float],
) -> float:
    """Return Euclidean range in kilometers."""

    receiver_position = _validate_position(receiver_position_km, "receiver_position_km")
    transmitter_position = _validate_position(transmitter_position_km, "transmitter_position_km")
    return float(np.linalg.norm(receiver_position - transmitter_position))


def clock_offset_for_node_km(
    node_id: int,
    ue_clocks_km: np.ndarray,
    non_reference_satellite_clocks_km: np.ndarray,
    num_users: int,
    num_satellites: int,
) -> float:
    """Return a V24 clock-range offset for a UE or satellite node."""

    ue_clocks, satellite_clocks = _validate_clock_vectors(
        ue_clocks_km,
        non_reference_satellite_clocks_km,
        num_users,
        num_satellites,
    )
    if node_id < 1 or node_id > num_users + num_satellites:
        raise ValueError(
            f"node_id must be in [1, {num_users + num_satellites}], got {node_id}."
        )
    if node_id <= num_users:
        return float(ue_clocks[node_id - 1])
    reference_id = reference_satellite_node_id(num_users)
    if node_id == reference_id:
        return 0.0
    satellite_index = node_id - (num_users + 2)
    return float(satellite_clocks[satellite_index])


def toa_range_model_km(
    receiver_node_id: int,
    transmitter_node_id: int,
    receiver_position_km: np.ndarray | Sequence[float],
    transmitter_position_km: np.ndarray | Sequence[float],
    ue_clocks_km: np.ndarray,
    non_reference_satellite_clocks_km: np.ndarray,
    num_users: int,
    num_satellites: int,
) -> float:
    """Return range + transmitter clock - receiver clock in kilometers."""

    range_km = euclidean_range_km(receiver_position_km, transmitter_position_km)
    receiver_clock = clock_offset_for_node_km(
        receiver_node_id,
        ue_clocks_km,
        non_reference_satellite_clocks_km,
        num_users,
        num_satellites,
    )
    transmitter_clock = clock_offset_for_node_km(
        transmitter_node_id,
        ue_clocks_km,
        non_reference_satellite_clocks_km,
        num_users,
        num_satellites,
    )
    return range_km + transmitter_clock - receiver_clock


def toa_range_vector_km(
    links: Sequence[tuple[int, int, np.ndarray | Sequence[float], np.ndarray | Sequence[float]]],
    ue_clocks_km: np.ndarray,
    non_reference_satellite_clocks_km: np.ndarray,
    num_users: int,
    num_satellites: int,
) -> np.ndarray:
    """Evaluate multiple range-domain TOA measurements in kilometers."""

    return np.array(
        [
            toa_range_model_km(
                receiver_node_id,
                transmitter_node_id,
                receiver_position_km,
                transmitter_position_km,
                ue_clocks_km,
                non_reference_satellite_clocks_km,
                num_users,
                num_satellites,
            )
            for receiver_node_id, transmitter_node_id, receiver_position_km, transmitter_position_km in links
        ],
        dtype=float,
    )
