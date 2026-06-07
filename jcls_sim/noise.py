"""Link-budget and range-domain noise helpers for V24 candidate simulations."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np

from .constants import C_KM_PER_S, C_M_PER_S


@dataclass(frozen=True)
class LinkBudgetConfig:
    """DL/SL link-budget assumptions for manuscript-candidate diagnostics."""

    dl_frequency_hz: float = 2.2e9
    dl_bandwidth_hz: float = 20.0e6
    dl_transmit_power_dbm: float = 55.0
    dl_transmit_antenna_gain_db: float = 20.0
    dl_receive_antenna_gain_db: float = 3.0
    sl_frequency_hz: float = 5.9e9
    sl_bandwidth_hz: float = 40.0e6
    sl_transmit_power_dbm: float = 20.0
    sl_transmit_antenna_gain_db: float = 3.0
    sl_receive_antenna_gain_db: float = 3.0
    noise_density_dbm_per_hz: float = -174.0
    receiver_noise_figure_db: float = 5.0
    implementation_loss_db: float = 0.0
    beta_model: str = "bandwidth_as_rms_bandwidth"


def fspl_db(range_km: float, frequency_hz: float) -> float:
    """Return free-space path loss in dB for range in km and frequency in Hz."""

    if range_km <= 0.0:
        raise ValueError("range_km must be positive.")
    if frequency_hz <= 0.0:
        raise ValueError("frequency_hz must be positive.")
    frequency_mhz = frequency_hz / 1.0e6
    return 32.44 + 20.0 * math.log10(range_km) + 20.0 * math.log10(frequency_mhz)


def noise_power_dbm(bandwidth_hz: float, noise_density_dbm_per_hz: float, noise_figure_db: float) -> float:
    """Return receiver noise power in dBm."""

    if bandwidth_hz <= 0.0:
        raise ValueError("bandwidth_hz must be positive.")
    return noise_density_dbm_per_hz + 10.0 * math.log10(bandwidth_hz) + noise_figure_db


def snr_db(
    *,
    range_km: float,
    frequency_hz: float,
    bandwidth_hz: float,
    transmit_power_dbm: float,
    transmit_gain_db: float,
    receive_gain_db: float,
    noise_density_dbm_per_hz: float,
    noise_figure_db: float,
    implementation_loss_db: float,
) -> float:
    """Return SNR in dB for a free-space link budget."""

    received_dbm = transmit_power_dbm + transmit_gain_db + receive_gain_db - fspl_db(range_km, frequency_hz) - implementation_loss_db
    return received_dbm - noise_power_dbm(bandwidth_hz, noise_density_dbm_per_hz, noise_figure_db)


def range_sigma_km_from_snr(snr_linear: float, beta_hz: float) -> float:
    """Return range-domain TOA standard deviation in km using manuscript-style beta/SNR formula."""

    if snr_linear <= 0.0:
        raise ValueError("snr_linear must be positive.")
    if beta_hz <= 0.0:
        raise ValueError("beta_hz must be positive.")
    sigma_m = C_M_PER_S / math.sqrt(8.0 * (math.pi * beta_hz) ** 2 * snr_linear)
    return sigma_m / 1000.0


def link_budget_for_range(
    *,
    range_km: float,
    link_type: str,
    config: LinkBudgetConfig,
) -> dict[str, float | str]:
    """Return link-budget diagnostics and range-domain sigma for one link."""

    if link_type == "DL":
        frequency_hz = config.dl_frequency_hz
        bandwidth_hz = config.dl_bandwidth_hz
        transmit_power_dbm = config.dl_transmit_power_dbm
        transmit_gain_db = config.dl_transmit_antenna_gain_db
        receive_gain_db = config.dl_receive_antenna_gain_db
    elif link_type == "SL":
        frequency_hz = config.sl_frequency_hz
        bandwidth_hz = config.sl_bandwidth_hz
        transmit_power_dbm = config.sl_transmit_power_dbm
        transmit_gain_db = config.sl_transmit_antenna_gain_db
        receive_gain_db = config.sl_receive_antenna_gain_db
    else:
        raise ValueError(f"link_type must be 'DL' or 'SL', got {link_type!r}.")

    snr_value_db = snr_db(
        range_km=range_km,
        frequency_hz=frequency_hz,
        bandwidth_hz=bandwidth_hz,
        transmit_power_dbm=transmit_power_dbm,
        transmit_gain_db=transmit_gain_db,
        receive_gain_db=receive_gain_db,
        noise_density_dbm_per_hz=config.noise_density_dbm_per_hz,
        noise_figure_db=config.receiver_noise_figure_db,
        implementation_loss_db=config.implementation_loss_db,
    )
    snr_linear = 10.0 ** (snr_value_db / 10.0)
    sigma_km = range_sigma_km_from_snr(snr_linear, bandwidth_hz)
    return {
        "link_type": link_type,
        "range_km": float(range_km),
        "frequency_hz": float(frequency_hz),
        "bandwidth_hz": float(bandwidth_hz),
        "transmit_power_dbm": float(transmit_power_dbm),
        "transmit_antenna_gain_db": float(transmit_gain_db),
        "receive_antenna_gain_db": float(receive_gain_db),
        "fspl_db": float(fspl_db(range_km, frequency_hz)),
        "noise_power_dbm": float(noise_power_dbm(bandwidth_hz, config.noise_density_dbm_per_hz, config.receiver_noise_figure_db)),
        "snr_db": float(snr_value_db),
        "snr_linear": float(snr_linear),
        "range_sigma_km": float(sigma_km),
        "range_sigma_m": float(sigma_km * 1000.0),
        "toa_sigma_s": float(sigma_km / C_KM_PER_S),
    }


def range_sigmas_for_links(
    *,
    ue_positions_km: np.ndarray,
    satellite_positions_km: np.ndarray,
    links: tuple[tuple[int, int], ...],
    num_users: int,
    config: LinkBudgetConfig,
) -> tuple[np.ndarray, list[dict[str, Any]], dict[str, Any]]:
    """Return range-domain sigmas and per-link metadata for V24 links."""

    sigmas: list[float] = []
    records: list[dict[str, Any]] = []
    for index, (receiver_node_id, transmitter_node_id) in enumerate(links):
        if transmitter_node_id > num_users:
            link_type = "DL"
            receiver_position = ue_positions_km[receiver_node_id - 1]
            transmitter_position = satellite_positions_km[transmitter_node_id - num_users - 1]
        else:
            link_type = "SL"
            receiver_position = ue_positions_km[receiver_node_id - 1]
            transmitter_position = ue_positions_km[transmitter_node_id - 1]
        range_km = float(np.linalg.norm(receiver_position - transmitter_position))
        budget = link_budget_for_range(range_km=range_km, link_type=link_type, config=config)
        budget.update(
            {
                "link_index": index,
                "receiver_node_id": int(receiver_node_id),
                "transmitter_node_id": int(transmitter_node_id),
            }
        )
        sigmas.append(float(budget["range_sigma_km"]))
        records.append(budget)

    snrs_db = np.asarray([record["snr_db"] for record in records], dtype=float)
    sigmas_km = np.asarray(sigmas, dtype=float)
    dl_sigmas = np.asarray([record["range_sigma_km"] for record in records if record["link_type"] == "DL"], dtype=float)
    sl_sigmas = np.asarray([record["range_sigma_km"] for record in records if record["link_type"] == "SL"], dtype=float)
    summary = {
        "link_budget_model": "free_space_path_loss_beta_snr_toa",
        "beta_interpretation": config.beta_model,
        "noise_density_dbm_per_hz": float(config.noise_density_dbm_per_hz),
        "receiver_noise_figure_db": float(config.receiver_noise_figure_db),
        "implementation_loss_db": float(config.implementation_loss_db),
        "dl_frequency_hz": float(config.dl_frequency_hz),
        "dl_bandwidth_hz": float(config.dl_bandwidth_hz),
        "dl_transmit_power_dbm": float(config.dl_transmit_power_dbm),
        "dl_transmit_antenna_gain_db": float(config.dl_transmit_antenna_gain_db),
        "dl_receive_antenna_gain_db": float(config.dl_receive_antenna_gain_db),
        "sl_frequency_hz": float(config.sl_frequency_hz),
        "sl_bandwidth_hz": float(config.sl_bandwidth_hz),
        "sl_transmit_power_dbm": float(config.sl_transmit_power_dbm),
        "sl_transmit_antenna_gain_db": float(config.sl_transmit_antenna_gain_db),
        "sl_receive_antenna_gain_db": float(config.sl_receive_antenna_gain_db),
        "snr_db_min": float(np.min(snrs_db)),
        "snr_db_max": float(np.max(snrs_db)),
        "range_sigma_km_min": float(np.min(sigmas_km)),
        "range_sigma_km_max": float(np.max(sigmas_km)),
        "dl_range_sigma_km_min": float(np.min(dl_sigmas)) if dl_sigmas.size else None,
        "dl_range_sigma_km_max": float(np.max(dl_sigmas)) if dl_sigmas.size else None,
        "sl_range_sigma_km_min": float(np.min(sl_sigmas)) if sl_sigmas.size else None,
        "sl_range_sigma_km_max": float(np.max(sl_sigmas)) if sl_sigmas.size else None,
        "dl_range_sigma_m_min": float(np.min(dl_sigmas) * 1000.0) if dl_sigmas.size else None,
        "dl_range_sigma_m_max": float(np.max(dl_sigmas) * 1000.0) if dl_sigmas.size else None,
        "sl_range_sigma_m_min": float(np.min(sl_sigmas) * 1000.0) if sl_sigmas.size else None,
        "sl_range_sigma_m_max": float(np.max(sl_sigmas) * 1000.0) if sl_sigmas.size else None,
    }
    return sigmas_km, records, summary
