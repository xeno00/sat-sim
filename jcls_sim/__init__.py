"""Core helpers for V24-consistent JCLS simulation code."""

from .constants import C_KM_PER_S, C_M_PER_S
from .configs import V24ScenarioConfig, tiny_v24_reproducibility_config, v24_crlb_mini_sweep_config
from .bounds import (
    average_clock_bound_from_covariance,
    average_ue_peb_from_covariance,
    clock_block_slice,
    clock_std_bounds_from_covariance,
    covariance_from_fim,
    non_reference_satellite_clock_block_slice,
    per_user_peb_from_covariance,
    ue_clock_block_slice,
    ue_position_block_indices,
)
from .estimators import (
    gauss_newton_step,
    information_form_ekf_update,
    levenberg_marquardt_step,
    weighted_normal_equations,
)
from .gauge import (
    all_clock_node_ids,
    expected_v24_parameter_dim,
    reference_satellite_node_id,
    relative_clock_dict,
    v24_clock_node_ids,
    v24_clock_vector_from_full,
)
from .fim import (
    fim_rank,
    gaussian_fim_from_jacobian,
    range_covariance_from_std_devs_km,
)
from .jacobian import (
    analytic_toa_jacobian_km,
    node_position_km,
    toa_range_vector_from_theta_km,
)
from .io import json_ready, write_json_diagnostic
from .metrics import (
    all_non_reference_clock_error,
    clock_error_relative_to_reference,
    non_reference_satellite_clock_error,
    position_error_m,
    ue_clock_error,
)
from .measurements import (
    clock_offset_for_node_km,
    euclidean_range_km,
    toa_range_model_km,
    toa_range_vector_km,
)
from .parameters import (
    non_reference_satellite_clock_param_names,
    pack_v24_theta,
    ue_clock_param_names,
    ue_position_param_names,
    unpack_v24_theta,
    v24_parameter_index,
    v24_parameter_names,
)

__all__ = [
    "C_KM_PER_S",
    "C_M_PER_S",
    "V24ScenarioConfig",
    "all_clock_node_ids",
    "all_non_reference_clock_error",
    "analytic_toa_jacobian_km",
    "average_clock_bound_from_covariance",
    "average_ue_peb_from_covariance",
    "clock_block_slice",
    "clock_error_relative_to_reference",
    "clock_offset_for_node_km",
    "clock_std_bounds_from_covariance",
    "covariance_from_fim",
    "euclidean_range_km",
    "expected_v24_parameter_dim",
    "fim_rank",
    "gauss_newton_step",
    "gaussian_fim_from_jacobian",
    "information_form_ekf_update",
    "json_ready",
    "levenberg_marquardt_step",
    "node_position_km",
    "non_reference_satellite_clock_param_names",
    "non_reference_satellite_clock_error",
    "non_reference_satellite_clock_block_slice",
    "pack_v24_theta",
    "per_user_peb_from_covariance",
    "position_error_m",
    "range_covariance_from_std_devs_km",
    "reference_satellite_node_id",
    "relative_clock_dict",
    "toa_range_model_km",
    "toa_range_vector_from_theta_km",
    "toa_range_vector_km",
    "tiny_v24_reproducibility_config",
    "ue_clock_error",
    "ue_clock_block_slice",
    "ue_clock_param_names",
    "ue_position_param_names",
    "ue_position_block_indices",
    "unpack_v24_theta",
    "v24_clock_node_ids",
    "v24_clock_vector_from_full",
    "v24_crlb_mini_sweep_config",
    "v24_parameter_index",
    "v24_parameter_names",
    "weighted_normal_equations",
    "write_json_diagnostic",
]
