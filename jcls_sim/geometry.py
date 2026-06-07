"""Manuscript-candidate geometry helpers for package-native V24 simulations."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np


WGS84_A_M = 6_378_137.0
WGS84_F = 1.0 / 298.257_223_563
WGS84_E2 = WGS84_F * (2.0 - WGS84_F)


@dataclass(frozen=True)
class GroundReference:
    """Reference geodetic point for local scenario generation."""

    latitude_deg: float
    longitude_deg: float
    altitude_m: float


@dataclass(frozen=True)
class CandidateGeometry:
    """Candidate UE/satellite geometry and audit metadata."""

    ue_positions_km: np.ndarray
    satellite_positions_km: np.ndarray
    metadata: dict[str, Any]


def lla_to_ecef_m(latitude_deg: float, longitude_deg: float, altitude_m: float) -> np.ndarray:
    """Convert WGS84 latitude/longitude/altitude to ECEF meters."""

    lat = math.radians(float(latitude_deg))
    lon = math.radians(float(longitude_deg))
    sin_lat = math.sin(lat)
    cos_lat = math.cos(lat)
    normal_radius = WGS84_A_M / math.sqrt(1.0 - WGS84_E2 * sin_lat**2)
    return np.array(
        [
            (normal_radius + altitude_m) * cos_lat * math.cos(lon),
            (normal_radius + altitude_m) * cos_lat * math.sin(lon),
            (normal_radius * (1.0 - WGS84_E2) + altitude_m) * sin_lat,
        ],
        dtype=float,
    )


def ecef_to_lla_deg(ecef_m: np.ndarray) -> tuple[float, float, float]:
    """Convert ECEF meters to WGS84 latitude, longitude, and altitude."""

    x, y, z = np.asarray(ecef_m, dtype=float)
    lon = math.atan2(y, x)
    p = math.hypot(x, y)
    lat = math.atan2(z, p * (1.0 - WGS84_E2))
    for _ in range(8):
        sin_lat = math.sin(lat)
        normal_radius = WGS84_A_M / math.sqrt(1.0 - WGS84_E2 * sin_lat**2)
        alt = p / math.cos(lat) - normal_radius
        lat = math.atan2(z, p * (1.0 - WGS84_E2 * normal_radius / (normal_radius + alt)))
    sin_lat = math.sin(lat)
    normal_radius = WGS84_A_M / math.sqrt(1.0 - WGS84_E2 * sin_lat**2)
    alt = p / math.cos(lat) - normal_radius
    return math.degrees(lat), math.degrees(lon), float(alt)


def enu_basis(latitude_deg: float, longitude_deg: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return east, north, and up unit vectors in ECEF coordinates."""

    lat = math.radians(float(latitude_deg))
    lon = math.radians(float(longitude_deg))
    east = np.array([-math.sin(lon), math.cos(lon), 0.0], dtype=float)
    north = np.array(
        [-math.sin(lat) * math.cos(lon), -math.sin(lat) * math.sin(lon), math.cos(lat)],
        dtype=float,
    )
    up = np.array([math.cos(lat) * math.cos(lon), math.cos(lat) * math.sin(lon), math.sin(lat)], dtype=float)
    return east, north, up


def ecef_from_enu_offset_m(reference: GroundReference, east_m: float, north_m: float, up_m: float = 0.0) -> np.ndarray:
    """Return ECEF meters after applying a local ENU offset."""

    origin = lla_to_ecef_m(reference.latitude_deg, reference.longitude_deg, reference.altitude_m)
    east, north, up = enu_basis(reference.latitude_deg, reference.longitude_deg)
    return origin + east_m * east + north_m * north + up_m * up


def elevation_deg(receiver_ecef_m: np.ndarray, transmitter_ecef_m: np.ndarray) -> float:
    """Return transmitter elevation angle at receiver in degrees."""

    receiver = np.asarray(receiver_ecef_m, dtype=float)
    transmitter = np.asarray(transmitter_ecef_m, dtype=float)
    up = receiver / np.linalg.norm(receiver)
    line = transmitter - receiver
    line_unit = line / np.linalg.norm(line)
    return math.degrees(math.asin(float(np.clip(np.dot(line_unit, up), -1.0, 1.0))))


def generate_ue_disk_geometry(
    *,
    reference: GroundReference,
    num_users: int,
    radius_m: float,
    seed: int,
) -> tuple[np.ndarray, list[dict[str, Any]]]:
    """Generate deterministic UE positions inside a local disk around a reference."""

    if num_users < 1:
        raise ValueError("num_users must be at least 1.")
    if radius_m <= 0.0:
        raise ValueError("radius_m must be positive.")
    rng = np.random.default_rng(int(seed))
    radial = radius_m * np.sqrt(rng.random(num_users))
    azimuth = 2.0 * math.pi * rng.random(num_users)
    east_offsets = radial * np.cos(azimuth)
    north_offsets = radial * np.sin(azimuth)

    positions_m = []
    metadata = []
    for index, (east_m, north_m) in enumerate(zip(east_offsets, north_offsets, strict=True), start=1):
        ecef_m = ecef_from_enu_offset_m(reference, float(east_m), float(north_m), 0.0)
        lat_deg, lon_deg, alt_m = ecef_to_lla_deg(ecef_m)
        positions_m.append(ecef_m)
        metadata.append(
            {
                "node_id": index,
                "east_offset_m": float(east_m),
                "north_offset_m": float(north_m),
                "radius_from_reference_m": float(math.hypot(east_m, north_m)),
                "latitude_deg": float(lat_deg),
                "longitude_deg": float(lon_deg),
                "altitude_m": float(alt_m),
                "ecef_km": (ecef_m / 1000.0).tolist(),
            }
        )
    return np.asarray(positions_m, dtype=float) / 1000.0, metadata


def generate_starlink_like_visible_satellites(
    *,
    reference: GroundReference,
    requested_satellites: int,
    seed: int,
    minimum_elevation_deg: float,
    pool_size: int = 24,
    altitude_km: float = 550.0,
) -> tuple[np.ndarray, list[dict[str, Any]], dict[str, Any]]:
    """Generate deterministic visible synthetic LEO satellites with an elevation mask."""

    if requested_satellites < 1:
        raise ValueError("requested_satellites must be at least 1.")
    if pool_size < requested_satellites:
        raise ValueError("pool_size must be at least requested_satellites.")
    if minimum_elevation_deg < 0.0:
        raise ValueError("minimum_elevation_deg must be nonnegative.")

    rng = np.random.default_rng(int(seed))
    origin = lla_to_ecef_m(reference.latitude_deg, reference.longitude_deg, reference.altitude_m)
    east, north, up = enu_basis(reference.latitude_deg, reference.longitude_deg)
    satellite_records: list[dict[str, Any]] = []
    satellite_positions: list[np.ndarray] = []
    base_elevations = np.linspace(
        minimum_elevation_deg + 5.0,
        82.0,
        pool_size,
        dtype=float,
    )
    azimuths = np.linspace(0.0, 360.0, pool_size, endpoint=False, dtype=float)
    rng.shuffle(azimuths)
    elevation_jitter = rng.normal(0.0, 1.25, size=pool_size)
    slant_range_m = (altitude_km * 1000.0) / np.sin(np.radians(base_elevations))

    for index in range(pool_size):
        elevation = float(max(minimum_elevation_deg + 0.5, base_elevations[index] + elevation_jitter[index]))
        azimuth = float(azimuths[index])
        az = math.radians(azimuth)
        el = math.radians(elevation)
        line_unit = math.cos(el) * math.sin(az) * east + math.cos(el) * math.cos(az) * north + math.sin(el) * up
        position_m = origin + slant_range_m[index] * line_unit
        actual_elevation = elevation_deg(origin, position_m)
        record = {
            "satellite_id": f"synthetic-starlink-like-{index + 1:03d}",
            "selection_index": index,
            "azimuth_deg": azimuth,
            "elevation_deg": float(actual_elevation),
            "slant_range_km": float(np.linalg.norm(position_m - origin) / 1000.0),
            "ecef_km": (position_m / 1000.0).tolist(),
            "altitude_model_km": float(altitude_km),
        }
        satellite_records.append(record)
        satellite_positions.append(position_m / 1000.0)

    visible = [
        (position, record)
        for position, record in zip(satellite_positions, satellite_records, strict=True)
        if record["elevation_deg"] >= minimum_elevation_deg
    ]
    visible.sort(key=lambda item: (-item[1]["elevation_deg"], item[1]["satellite_id"]))
    selected = visible[:requested_satellites]
    if len(selected) < requested_satellites:
        raise ValueError(
            f"Only {len(selected)} synthetic satellites meet the elevation mask; "
            f"requested {requested_satellites}."
        )
    selection_metadata = {
        "satellite_geometry_model": "starlink_like_synthetic_leo",
        "tle_sgp4_used": False,
        "satellite_altitude_model_km": float(altitude_km),
        "minimum_elevation_deg": float(minimum_elevation_deg),
        "geometrically_visible_satellites": int(len(visible)),
        "requested_satellites": int(requested_satellites),
        "selected_satellites": int(len(selected)),
        "selection_method": "deterministic_highest_elevation",
        "insufficient_visible_satellites_policy": "raise_error",
    }
    return (
        np.asarray([position for position, _record in selected], dtype=float),
        [record for _position, record in selected],
        selection_metadata,
    )


def manuscript_candidate_geometry(
    *,
    num_users: int,
    num_satellites: int,
    seed: int,
    reference: GroundReference,
    ue_radius_m: float,
    minimum_elevation_deg: float,
    satellite_pool_size: int,
    satellite_altitude_km: float,
) -> CandidateGeometry:
    """Build deterministic manuscript-candidate UE and synthetic LEO geometry."""

    ue_positions_km, ue_metadata = generate_ue_disk_geometry(
        reference=reference,
        num_users=num_users,
        radius_m=ue_radius_m,
        seed=int(seed),
    )
    satellite_positions_km, satellite_metadata, visibility_metadata = generate_starlink_like_visible_satellites(
        reference=reference,
        requested_satellites=num_satellites,
        seed=int(seed) + 4099,
        minimum_elevation_deg=minimum_elevation_deg,
        pool_size=satellite_pool_size,
        altitude_km=satellite_altitude_km,
    )
    return CandidateGeometry(
        ue_positions_km=ue_positions_km,
        satellite_positions_km=satellite_positions_km,
        metadata={
            "scenario_geometry_model": "manuscript_candidate_mit_stata_synthetic_leo",
            "reference_location": {
                "latitude_deg": float(reference.latitude_deg),
                "longitude_deg": float(reference.longitude_deg),
                "altitude_m": float(reference.altitude_m),
                "ecef_km": (lla_to_ecef_m(reference.latitude_deg, reference.longitude_deg, reference.altitude_m) / 1000.0).tolist(),
            },
            "ue_disk_radius_m": float(ue_radius_m),
            "ue_coordinates": ue_metadata,
            "satellite_coordinates": satellite_metadata,
            "visibility": visibility_metadata,
        },
    )
