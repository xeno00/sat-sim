"""V24 clock-gauge helpers for JCLS simulation code."""

from __future__ import annotations

import numpy as np


def _validate_counts(num_users: int, num_satellites: int) -> None:
    """Validate positive network dimensions."""

    if num_users < 1:
        raise ValueError(f"num_users must be at least 1, got {num_users}.")
    if num_satellites < 1:
        raise ValueError(f"num_satellites must be at least 1, got {num_satellites}.")


def _validate_clock_dict(
    full_clock_by_node: dict[int, float],
    num_users: int,
    num_satellites: int,
) -> None:
    """Validate that a full clock dictionary contains all required node ids."""

    _validate_counts(num_users, num_satellites)
    required = set(all_clock_node_ids(num_users, num_satellites))
    present = set(full_clock_by_node)
    missing = sorted(required - present)
    if missing:
        raise ValueError(f"full_clock_by_node is missing required node id(s): {missing}.")


def reference_satellite_node_id(num_users: int) -> int:
    """Return the V24 reference satellite node id, Nu + 1."""

    if num_users < 1:
        raise ValueError(f"num_users must be at least 1, got {num_users}.")
    return num_users + 1


def all_clock_node_ids(num_users: int, num_satellites: int) -> list[int]:
    """Return all UE and satellite clock node ids: [1, ..., Nu+Ns]."""

    _validate_counts(num_users, num_satellites)
    return list(range(1, num_users + num_satellites + 1))


def v24_clock_node_ids(num_users: int, num_satellites: int) -> list[int]:
    """Return V24 estimated clock ids: UE clocks plus non-reference satellite clocks."""

    _validate_counts(num_users, num_satellites)
    reference_id = reference_satellite_node_id(num_users)
    return [
        node_id
        for node_id in all_clock_node_ids(num_users, num_satellites)
        if node_id != reference_id
    ]


def expected_v24_parameter_dim(num_users: int, num_satellites: int) -> int:
    """Return the V24 JCLS parameter dimension 4*Nu + Ns - 1."""

    _validate_counts(num_users, num_satellites)
    return 4 * num_users + num_satellites - 1


def relative_clock_dict(
    full_clock_by_node: dict[int, float],
    num_users: int,
    num_satellites: int,
) -> dict[int, float]:
    """Return all clocks shifted relative to the reference satellite.

    The returned dictionary includes every node id in [1, ..., Nu+Ns], including
    the reference satellite with value 0.0.
    """

    _validate_clock_dict(full_clock_by_node, num_users, num_satellites)
    reference_id = reference_satellite_node_id(num_users)
    reference_clock = float(full_clock_by_node[reference_id])
    return {
        node_id: float(full_clock_by_node[node_id]) - reference_clock
        for node_id in all_clock_node_ids(num_users, num_satellites)
    }


def v24_clock_vector_from_full(
    full_clock_by_node: dict[int, float],
    num_users: int,
    num_satellites: int,
) -> np.ndarray:
    """Return the V24 ordered non-reference clock vector.

    The output subtracts the reference satellite clock and excludes that
    reference. The order is [1, ..., Nu, Nu+2, ..., Nu+Ns].
    """

    relative_clocks = relative_clock_dict(full_clock_by_node, num_users, num_satellites)
    return np.array(
        [relative_clocks[node_id] for node_id in v24_clock_node_ids(num_users, num_satellites)],
        dtype=float,
    )
