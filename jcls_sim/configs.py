"""Deterministic V24 smoke-run configurations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from .gauge import expected_v24_parameter_dim, reference_satellite_node_id
from .parameters import pack_v24_theta


@dataclass(frozen=True)
class V24ScenarioConfig:
    """Small V24 scenario configuration with kilometer-domain clocks."""

    scenario_name: str
    num_users: int
    num_satellites: int
    seed: int
    ue_positions_km: np.ndarray
    satellite_positions_km: np.ndarray
    ue_clock_offsets_km: np.ndarray
    non_reference_satellite_clock_offsets_km: np.ndarray
    links: tuple[tuple[int, int], ...]
    range_std_devs_km: np.ndarray

    def validate(self) -> None:
        """Validate V24 dimensions, links, and standard deviations."""

        if self.num_users < 1:
            raise ValueError(f"num_users must be at least 1, got {self.num_users}.")
        if self.num_satellites < 1:
            raise ValueError(f"num_satellites must be at least 1, got {self.num_satellites}.")

        ue_positions = np.asarray(self.ue_positions_km, dtype=float)
        satellite_positions = np.asarray(self.satellite_positions_km, dtype=float)
        ue_clocks = np.asarray(self.ue_clock_offsets_km, dtype=float)
        satellite_clocks = np.asarray(self.non_reference_satellite_clock_offsets_km, dtype=float)
        sigmas = np.asarray(self.range_std_devs_km, dtype=float)

        if ue_positions.shape != (self.num_users, 3):
            raise ValueError(
                "ue_positions_km must have shape "
                f"({self.num_users}, 3), got {ue_positions.shape}."
            )
        if satellite_positions.shape != (self.num_satellites, 3):
            raise ValueError(
                "satellite_positions_km must have shape "
                f"({self.num_satellites}, 3), got {satellite_positions.shape}."
            )
        if ue_clocks.shape != (self.num_users,):
            raise ValueError(
                "ue_clock_offsets_km must have shape "
                f"({self.num_users},), got {ue_clocks.shape}."
            )
        if satellite_clocks.shape != (self.num_satellites - 1,):
            raise ValueError(
                "non_reference_satellite_clock_offsets_km must have shape "
                f"({self.num_satellites - 1},), got {satellite_clocks.shape}."
            )
        if sigmas.shape != (len(self.links),):
            raise ValueError(
                "range_std_devs_km must have one entry per link, "
                f"got {sigmas.shape} and {len(self.links)} links."
            )
        if np.any(sigmas <= 0.0):
            raise ValueError("range_std_devs_km must contain strictly positive values.")

        max_node_id = self.num_users + self.num_satellites
        for receiver_node_id, transmitter_node_id in self.links:
            if receiver_node_id < 1 or receiver_node_id > max_node_id:
                raise ValueError(f"Invalid receiver node id {receiver_node_id}.")
            if transmitter_node_id < 1 or transmitter_node_id > max_node_id:
                raise ValueError(f"Invalid transmitter node id {transmitter_node_id}.")

    def theta(self) -> np.ndarray:
        """Return this scenario's V24 theta vector."""

        self.validate()
        theta = pack_v24_theta(
            self.ue_positions_km,
            self.ue_clock_offsets_km,
            self.non_reference_satellite_clock_offsets_km,
        )
        expected_dim = expected_v24_parameter_dim(self.num_users, self.num_satellites)
        if theta.shape != (expected_dim,):
            raise ValueError(f"Packed theta has shape {theta.shape}, expected ({expected_dim},).")
        return theta

    def full_clock_dict_km(self) -> dict[int, float]:
        """Return full node clock offsets with the reference satellite fixed to zero."""

        self.validate()
        clocks: dict[int, float] = {
            node_id: float(clock)
            for node_id, clock in enumerate(np.asarray(self.ue_clock_offsets_km), start=1)
        }
        reference_node_id = reference_satellite_node_id(self.num_users)
        clocks[reference_node_id] = 0.0
        non_reference_clocks = np.asarray(self.non_reference_satellite_clock_offsets_km, dtype=float)
        for offset, clock in enumerate(non_reference_clocks, start=1):
            clocks[reference_node_id + offset] = float(clock)
        return clocks


def tiny_v24_reproducibility_config(seed: int = 20260606) -> V24ScenarioConfig:
    """Return a deterministic Nu=2, Ns=2 V24 smoke-run scenario."""

    links: Sequence[tuple[int, int]] = (
        (1, 3),  # DL: reference satellite to UE 1
        (2, 3),  # DL: reference satellite to UE 2
        (1, 4),  # DL: non-reference satellite to UE 1
        (2, 4),  # DL: non-reference satellite to UE 2
        (1, 2),  # SL: UE 2 to UE 1
    )
    return V24ScenarioConfig(
        scenario_name="tiny_v24_package_smoke",
        num_users=2,
        num_satellites=2,
        seed=int(seed),
        ue_positions_km=np.array(
            [
                [0.0, 0.0, 0.0],
                [3.0, 4.0, 0.0],
            ],
            dtype=float,
        ),
        satellite_positions_km=np.array(
            [
                [0.0, 0.0, 10.0],
                [0.0, 0.0, 20.0],
            ],
            dtype=float,
        ),
        ue_clock_offsets_km=np.array([0.1, -0.2], dtype=float),
        non_reference_satellite_clock_offsets_km=np.array([0.5], dtype=float),
        links=tuple(links),
        range_std_devs_km=np.array([0.02, 0.025, 0.03, 0.035, 0.04], dtype=float),
    )


def downlink_links(num_users: int, num_satellites: int) -> tuple[tuple[int, int], ...]:
    """Return all satellite-to-UE downlink links for V24 node indexing."""

    if num_users < 1:
        raise ValueError(f"num_users must be at least 1, got {num_users}.")
    if num_satellites < 1:
        raise ValueError(f"num_satellites must be at least 1, got {num_satellites}.")
    satellite_node_ids = range(num_users + 1, num_users + num_satellites + 1)
    return tuple(
        (user_node_id, satellite_node_id)
        for satellite_node_id in satellite_node_ids
        for user_node_id in range(1, num_users + 1)
    )


def directed_sidelink_links(num_users: int) -> tuple[tuple[int, int], ...]:
    """Return all directed UE-to-UE sidelink links."""

    if num_users < 1:
        raise ValueError(f"num_users must be at least 1, got {num_users}.")
    return tuple(
        (receiver_node_id, transmitter_node_id)
        for receiver_node_id in range(1, num_users + 1)
        for transmitter_node_id in range(1, num_users + 1)
        if receiver_node_id != transmitter_node_id
    )


def minimal_sidelink_links(num_users: int) -> tuple[tuple[int, int], ...]:
    """Return a simple directed UE chain for minimal sidelink diagnostics."""

    if num_users < 1:
        raise ValueError(f"num_users must be at least 1, got {num_users}.")
    return tuple(
        (receiver_node_id, receiver_node_id + 1)
        for receiver_node_id in range(1, num_users)
    )


def v24_geometry_links(
    num_users: int,
    num_satellites: int,
    link_pattern: str,
) -> tuple[tuple[int, int], ...]:
    """Return deterministic links for a named V24 CRLB diagnostic pattern."""

    dl_links = downlink_links(num_users, num_satellites)
    if link_pattern == "dl_only":
        return dl_links
    if link_pattern == "all_dl_minimal_sl":
        return dl_links + minimal_sidelink_links(num_users)
    if link_pattern == "all_dl_all_directed_sl":
        return dl_links + directed_sidelink_links(num_users)
    raise ValueError(
        "link_pattern must be one of 'dl_only', 'all_dl_minimal_sl', "
        f"or 'all_dl_all_directed_sl', got {link_pattern!r}."
    )


def v24_crlb_geometry_config(
    num_users: int,
    num_satellites: int,
    seed: int,
    *,
    link_pattern: str = "all_dl_all_directed_sl",
    range_std_dev_km: float = 0.03,
) -> V24ScenarioConfig:
    """Return a deterministic V24 CRLB geometry-diagnostic scenario."""

    if num_users < 1:
        raise ValueError(f"num_users must be at least 1, got {num_users}.")
    if num_satellites < 2:
        raise ValueError(f"num_satellites must be at least 2, got {num_satellites}.")
    if range_std_dev_km <= 0.0:
        raise ValueError(f"range_std_dev_km must be positive, got {range_std_dev_km}.")

    rng = np.random.default_rng(int(seed))
    user_angles = np.linspace(0.15, 2.0 * np.pi + 0.15, num_users, endpoint=False)
    user_radii = 2.5 + 1.25 * np.arange(num_users, dtype=float)
    ue_positions_km = np.column_stack(
        [
            user_radii * np.cos(user_angles),
            0.8 * user_radii * np.sin(user_angles),
            0.15 * np.arange(num_users, dtype=float),
        ]
    )
    ue_positions_km += rng.normal(loc=0.0, scale=0.01, size=ue_positions_km.shape)

    satellite_angles = np.linspace(0.0, 2.0 * np.pi, num_satellites, endpoint=False)
    satellite_positions_km = np.column_stack(
        [
            10.0 * np.cos(satellite_angles),
            8.0 * np.sin(satellite_angles),
            20.0 + 2.0 * np.arange(num_satellites, dtype=float),
        ]
    )
    satellite_positions_km += rng.normal(loc=0.0, scale=0.02, size=satellite_positions_km.shape)

    ue_clock_offsets_km = np.linspace(0.08, -0.10, num_users, dtype=float)
    ue_clock_offsets_km += rng.normal(loc=0.0, scale=0.003, size=num_users)
    non_reference_satellite_clock_offsets_km = np.linspace(
        0.18,
        0.18 + 0.04 * (num_satellites - 2),
        num_satellites - 1,
        dtype=float,
    )
    non_reference_satellite_clock_offsets_km += rng.normal(
        loc=0.0,
        scale=0.003,
        size=num_satellites - 1,
    )
    links = v24_geometry_links(num_users, num_satellites, link_pattern)

    return V24ScenarioConfig(
        scenario_name=f"v24_crlb_geometry_{link_pattern}_nu{num_users}_ns{num_satellites}",
        num_users=int(num_users),
        num_satellites=int(num_satellites),
        seed=int(seed),
        ue_positions_km=ue_positions_km,
        satellite_positions_km=satellite_positions_km,
        ue_clock_offsets_km=ue_clock_offsets_km,
        non_reference_satellite_clock_offsets_km=non_reference_satellite_clock_offsets_km,
        links=links,
        range_std_devs_km=np.full(len(links), float(range_std_dev_km), dtype=float),
    )


def v24_crlb_mini_sweep_config(
    num_satellites: int,
    seed: int,
    *,
    num_users: int = 2,
    range_std_dev_km: float = 0.03,
) -> V24ScenarioConfig:
    """Return a deterministic V24 CRLB mini-sweep scenario for one satellite count."""

    if num_users != 2:
        raise ValueError("The CRLB mini-sweep diagnostic currently supports num_users=2 only.")
    if num_satellites < 2:
        raise ValueError(f"num_satellites must be at least 2, got {num_satellites}.")
    if range_std_dev_km <= 0.0:
        raise ValueError(f"range_std_dev_km must be positive, got {range_std_dev_km}.")

    rng = np.random.default_rng(int(seed))
    ue_positions_km = np.array(
        [
            [0.0, 0.0, 0.0],
            [3.5, 4.0, 0.2],
        ],
        dtype=float,
    )
    ue_positions_km += rng.normal(loc=0.0, scale=0.02, size=ue_positions_km.shape)

    angles = np.linspace(0.0, 2.0 * np.pi, num_satellites, endpoint=False)
    satellite_positions_km = np.column_stack(
        [
            7.0 * np.cos(angles),
            5.0 * np.sin(angles),
            18.0 + 1.5 * np.arange(num_satellites, dtype=float),
        ]
    )
    satellite_positions_km += rng.normal(loc=0.0, scale=0.03, size=satellite_positions_km.shape)

    ue_clock_offsets_km = np.array([0.08, -0.12], dtype=float)
    ue_clock_offsets_km += rng.normal(loc=0.0, scale=0.005, size=num_users)
    non_reference_satellite_clock_offsets_km = np.linspace(
        0.18,
        0.18 + 0.04 * (num_satellites - 2),
        num_satellites - 1,
        dtype=float,
    )
    non_reference_satellite_clock_offsets_km += rng.normal(
        loc=0.0,
        scale=0.004,
        size=num_satellites - 1,
    )

    satellite_node_ids = range(num_users + 1, num_users + num_satellites + 1)
    links: list[tuple[int, int]] = [
        (user_node_id, satellite_node_id)
        for satellite_node_id in satellite_node_ids
        for user_node_id in range(1, num_users + 1)
    ]
    links.append((1, 2))

    return V24ScenarioConfig(
        scenario_name=f"v24_crlb_mini_sweep_ns{num_satellites}",
        num_users=num_users,
        num_satellites=int(num_satellites),
        seed=int(seed),
        ue_positions_km=ue_positions_km,
        satellite_positions_km=satellite_positions_km,
        ue_clock_offsets_km=ue_clock_offsets_km,
        non_reference_satellite_clock_offsets_km=non_reference_satellite_clock_offsets_km,
        links=tuple(links),
        range_std_devs_km=np.full(len(links), float(range_std_dev_km), dtype=float),
    )
