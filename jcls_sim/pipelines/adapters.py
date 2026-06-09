"""Execution adapters for canonical benchmark pipeline specs.

Only package-native adapters belong here. Legacy/notebook-style execution
remains outside core ``jcls_sim`` and is represented with explicit missing
metrics until a safe adapter boundary is implemented.
"""

from __future__ import annotations

from typing import Any

from jcls_sim.figure_generation import _scenario_and_metadata_for_case, run_single_trial_step_c7_algorithm
from jcls_sim.pipelines.specs import PipelineRunResult, PipelineSpec, StageMetrics

from jcls_sim.benchmark.standard_cases import StandardCaseSpec


MISSING_REASONS_BY_PIPELINE = {
    "legacy_surgical_prior_region": "legacy_surgical_adapter_not_integrated_on_main",
    "controlled_migration_step_b_lm_only": "controlled_step_b_adapter_not_executable_without_legacy_runner",
    "legacy_truth_gated_l0_reference_only": "truth_gated_provenance_adapter_not_executed_for_benchmark_cards",
}


def _missing_stage(reason: str, notes: str = "") -> StageMetrics:
    """Return an unavailable stage metric with an explicit reason."""

    return StageMetrics(
        pos_error_m=None,
        sync_error_ns=None,
        available=False,
        missing_reason=reason,
        metric_notes=notes,
    )


def unavailable_pipeline_result(pipeline: PipelineSpec, case: StandardCaseSpec, reason: str) -> PipelineRunResult:
    """Return a schema-complete missing-result record for one unavailable adapter."""

    return PipelineRunResult(
        pipeline_id=pipeline.pipeline_id,
        case_id=case.case_id,
        initialization=_missing_stage(reason, "Adapter execution is not available on main."),
        step_a=_missing_stage(reason, "Adapter execution is not available on main."),
        step_b=_missing_stage(reason, "Adapter execution is not available on main."),
        step_c=_missing_stage(reason, "Adapter execution is not available on main."),
        truth_use=pipeline.truth_use,
        units_status=pipeline.units_status,
        readiness=pipeline.readiness,
        warnings=(reason,),
    )


def _standard_case_config(case: StandardCaseSpec) -> dict[str, Any]:
    """Return the manuscript-like package-native config for a standard case."""

    return {
        "scenario_model": "manuscript_candidate_mit_stata_synthetic_leo",
        "reference_location": {
            "latitude_deg": 42.361145,
            "longitude_deg": -71.09085,
            "altitude_m": 20.0,
        },
        "ue_disk_radius_m": 500.0,
        "minimum_elevation_deg": 30.0,
        "satellite_pool_size": max(24, int(case.num_satellites)),
        "satellite_altitude_km": 550.0,
        "link_budget": {
            "dl_frequency_hz": 2.2e9,
            "dl_bandwidth_hz": 20.0e6,
            "dl_transmit_power_dbm": 55.0,
            "dl_transmit_antenna_gain_db": 20.0,
            "dl_receive_antenna_gain_db": 3.0,
            "sl_frequency_hz": 5.9e9,
            "sl_bandwidth_hz": 40.0e6,
            "sl_transmit_power_dbm": 20.0,
            "sl_transmit_antenna_gain_db": 3.0,
            "sl_receive_antenna_gain_db": 3.0,
            "noise_density_dbm_per_hz": -174.0,
            "receiver_noise_figure_db": 5.0,
            "implementation_loss_db": 0.0,
        },
    }


def package_native_standard_scenario(case: StandardCaseSpec) -> tuple[Any, dict[str, Any]]:
    """Return the deterministic package-native scenario for a standard case."""

    if case.sidelink_graph != "full_mesh":
        raise ValueError("package_native_c7 currently supports only full_mesh standard cases.")
    clock_std_ns = float(case.clock_std_seconds) * 1.0e9
    return _scenario_and_metadata_for_case(
        config=_standard_case_config(case),
        case={
            "num_users": int(case.num_users),
            "num_satellites": int(case.num_satellites),
            "clock_std_ns": clock_std_ns,
        },
        seed=int(case.seed),
    )


def _refinement_epochs_for_case(case: StandardCaseSpec) -> int:
    """Return the minimum bounded C7 epoch count for the standard operation time."""

    if case.operation_time_seconds <= 0.0:
        raise ValueError("operation_time_seconds must be positive.")
    return max(2, int(round(case.operation_time_seconds / 0.5)) + 1)


def _row_for_baseline(rows: list[dict[str, Any]], baseline_id: str) -> dict[str, Any]:
    """Return one metric row by baseline id."""

    for row in rows:
        if row.get("baseline_id") == baseline_id:
            return row
    raise ValueError(f"Missing baseline_id={baseline_id!r} in package-native C7 output.")


def _stage_from_row(row: dict[str, Any], notes: str) -> StageMetrics:
    """Convert one package-native metric row into canonical stage metrics."""

    return StageMetrics(
        pos_error_m=float(row["position_error_mean_m"]),
        sync_error_ns=float(row["sync_error_mean_s"]) * 1.0e9,
        available=True,
        metric_notes=notes,
    )


def run_package_native_c7(pipeline: PipelineSpec, case: StandardCaseSpec) -> PipelineRunResult:
    """Execute the package-native C7 adapter for one bounded standard case."""

    scenario, scenario_metadata = package_native_standard_scenario(case)
    rows = run_single_trial_step_c7_algorithm(
        scenario,
        trial_seed=int(case.seed),
        refinement_epochs=_refinement_epochs_for_case(case),
        noise_scale=1.0,
        process_noise_std_km=1.0e-5,
    )
    step_a_row = _row_for_baseline(rows, "without_cooperation")
    step_b_row = _row_for_baseline(rows, "coarse_jcls")
    step_c_row = _row_for_baseline(rows, "refined_jcls")
    geometry_metadata = scenario_metadata.get("geometry", {})
    geometry_model = geometry_metadata.get("scenario_geometry_model", "unknown")
    return PipelineRunResult(
        pipeline_id=pipeline.pipeline_id,
        case_id=case.case_id,
        initialization=_missing_stage(
            "package_native_c7_pre_step_initialization_metrics_not_reported",
            "The current package-native C7 path reports Step A/B/C metrics, not a separate pre-Step-A initialization metric.",
        ),
        step_a=_stage_from_row(step_a_row, "Stage A: package DL-only/coarse individual localization."),
        step_b=_stage_from_row(step_b_row, "Stage B: package residual LM JCLS."),
        step_c=_stage_from_row(step_c_row, "Stage C: package C7 residual-covariance sync safeguard."),
        truth_use=pipeline.truth_use,
        units_status=pipeline.units_status,
        readiness=pipeline.readiness,
        warnings=(
            "single_trial_non_final_benchmark_card",
            "truth_used_only_for_offline_metric_calculation",
            f"scenario={scenario.scenario_name}",
            f"geometry_model={geometry_model}",
        ),
    )


def run_pipeline_adapter(pipeline: PipelineSpec, case: StandardCaseSpec) -> PipelineRunResult:
    """Run an executable adapter or return a schema-complete missing result."""

    if pipeline.pipeline_id == "package_native_c7":
        return run_package_native_c7(pipeline, case)
    reason = MISSING_REASONS_BY_PIPELINE.get(pipeline.pipeline_id, "pipeline_adapter_not_available")
    return unavailable_pipeline_result(pipeline, case, reason)


def adapter_status(pipeline: PipelineSpec) -> str:
    """Return the current execution status for one pipeline adapter."""

    if pipeline.pipeline_id == "package_native_c7":
        return "adapter_available"
    if pipeline.pipeline_id in MISSING_REASONS_BY_PIPELINE:
        return "planned_unavailable"
    return "unknown"
