"""V24-consistent metrics for JCLS simulation outputs."""

from __future__ import annotations

import numpy as np

from .gauge import relative_clock_dict, reference_satellite_node_id, v24_clock_node_ids


def _selected_clock_ids(num_users: int, num_satellites: int, clock_ids: str) -> list[int]:
    """Return node ids selected by a supported clock-error group."""

    if clock_ids == "all_non_reference":
        selected = v24_clock_node_ids(num_users, num_satellites)
    elif clock_ids == "ue":
        selected = list(range(1, num_users + 1))
    elif clock_ids == "satellite_non_reference":
        reference_id = reference_satellite_node_id(num_users)
        selected = [
            node_id
            for node_id in range(num_users + 1, num_users + num_satellites + 1)
            if node_id != reference_id
        ]
    else:
        raise ValueError(
            "clock_ids must be one of 'all_non_reference', 'ue', "
            f"or 'satellite_non_reference', got {clock_ids!r}."
        )
    if not selected:
        raise ValueError(f"clock_ids={clock_ids!r} selected no clocks for this network.")
    return selected


def clock_error_relative_to_reference(
    true_full_clock_by_node: dict[int, float],
    est_full_clock_by_node: dict[int, float],
    num_users: int,
    num_satellites: int,
    clock_ids: str = "all_non_reference",
) -> float:
    """Return mean absolute clock error after reference-satellite alignment.

    Clock inputs and the returned error use the same units, normally seconds.
    The reference satellite clock is excluded from the average.
    """

    true_relative = relative_clock_dict(true_full_clock_by_node, num_users, num_satellites)
    est_relative = relative_clock_dict(est_full_clock_by_node, num_users, num_satellites)
    selected = _selected_clock_ids(num_users, num_satellites, clock_ids)
    errors = [abs(est_relative[node_id] - true_relative[node_id]) for node_id in selected]
    return float(np.mean(errors))


def ue_clock_error(
    true_full_clock_by_node: dict[int, float],
    est_full_clock_by_node: dict[int, float],
    num_users: int,
    num_satellites: int,
) -> float:
    """Return mean UE clock error relative to the reference satellite."""

    return clock_error_relative_to_reference(
        true_full_clock_by_node,
        est_full_clock_by_node,
        num_users,
        num_satellites,
        clock_ids="ue",
    )


def non_reference_satellite_clock_error(
    true_full_clock_by_node: dict[int, float],
    est_full_clock_by_node: dict[int, float],
    num_users: int,
    num_satellites: int,
) -> float:
    """Return mean non-reference satellite clock error relative to the reference."""

    return clock_error_relative_to_reference(
        true_full_clock_by_node,
        est_full_clock_by_node,
        num_users,
        num_satellites,
        clock_ids="satellite_non_reference",
    )


def all_non_reference_clock_error(
    true_full_clock_by_node: dict[int, float],
    est_full_clock_by_node: dict[int, float],
    num_users: int,
    num_satellites: int,
) -> float:
    """Return mean clock error over UE and non-reference satellite clocks."""

    return clock_error_relative_to_reference(
        true_full_clock_by_node,
        est_full_clock_by_node,
        num_users,
        num_satellites,
        clock_ids="all_non_reference",
    )


def position_error_m(true_positions_km: np.ndarray, est_positions_km: np.ndarray) -> np.ndarray:
    """Return Euclidean position errors in meters for kilometer-valued positions.

    Inputs may have shape (N, 3) or (3,). The return value is always a 1-D array
    containing one error per position.
    """

    true_positions = np.asarray(true_positions_km, dtype=float)
    est_positions = np.asarray(est_positions_km, dtype=float)
    if true_positions.shape != est_positions.shape:
        raise ValueError(
            "true_positions_km and est_positions_km must have matching shapes, "
            f"got {true_positions.shape} and {est_positions.shape}."
        )
    if true_positions.ndim == 1:
        if true_positions.shape != (3,):
            raise ValueError(f"1-D position inputs must have shape (3,), got {true_positions.shape}.")
        true_positions = true_positions.reshape(1, 3)
        est_positions = est_positions.reshape(1, 3)
    elif true_positions.ndim == 2:
        if true_positions.shape[1] != 3:
            raise ValueError(f"2-D position inputs must have shape (N, 3), got {true_positions.shape}.")
    else:
        raise ValueError(f"Position inputs must have shape (3,) or (N, 3), got {true_positions.shape}.")
    return np.linalg.norm(est_positions - true_positions, axis=1) * 1000.0
