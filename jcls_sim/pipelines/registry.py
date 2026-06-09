"""Schema-only registry for initial JCLS benchmark pipeline candidates."""

from __future__ import annotations

from .specs import PipelineSpec, PipelineStageVersions, TruthUseLedger


def _legacy_surgical_prior_region() -> PipelineSpec:
    return PipelineSpec(
        pipeline_id="legacy_surgical_prior_region",
        display_name="Legacy-surgical prior-region candidate",
        stage_versions=PipelineStageVersions(
            system_model_version="legacy_compatible_all_clock",
            initialization_version="A0_prior_region_il",
            stage_a_version="A0_prior_region_il",
            stage_b_version="B1_residual_trust_region_lm_no_truth_gate",
            stage_c_version="C_surgical_residual_scaled_info_map",
            metric_version="legacy_all_clock_metric_pending_v24_reference_relative_recompute",
            units_version="legacy_km_range_equivalent_clock_units_with_m_ns_reporting",
        ),
        truth_use=TruthUseLedger(
            truth_used_for_prior_construction=True,
            truth_used_for_initialization=False,
            truth_used_for_lm_acceptance=False,
            truth_used_for_step_c_acceptance=False,
            truth_used_for_covariance=False,
            truth_used_for_fallback_or_reversion=False,
            truth_used_for_offline_metrics=True,
            summary=(
                "Truth is used for simulation prior construction and offline metrics; "
                "estimator acceptance, covariance, and fallback decisions are non-truth."
            ),
        ),
        readiness="candidate_nonfinal",
        recommended_use="pursue_as_primary_after_normalized_validation",
        units_status="units_consistent_but_legacy",
        result_lineage_status="registered",
        implementation_status="adapter_planned",
        adapter_module="jcls_sim.pipelines.legacy_surgical",
        runner_script="scripts/run_legacy_surgical_prior_region_initialization.py",
        notes="Recommended primary candidate family, but adapter execution is not implemented in this schema-only layer.",
    )


def _controlled_migration_step_b_lm_only() -> PipelineSpec:
    return PipelineSpec(
        pipeline_id="controlled_migration_step_b_lm_only",
        display_name="Controlled migration Step B LM-only",
        stage_versions=PipelineStageVersions(
            system_model_version="legacy_compatible_all_clock",
            initialization_version="A0_legacy_il_clockless_preconditioning",
            stage_a_version="A0_legacy_il_clockless_preconditioning",
            stage_b_version="B1_residual_lm",
            stage_c_version="C_none",
            metric_version="legacy_all_clock_metric_pending_v24_reference_relative_recompute",
            units_version="legacy_km_range_equivalent_clock_units_with_m_ns_reporting",
        ),
        truth_use=TruthUseLedger(
            truth_used_for_prior_construction=False,
            truth_used_for_initialization=True,
            truth_used_for_lm_acceptance=False,
            truth_used_for_step_c_acceptance=False,
            truth_used_for_covariance=False,
            truth_used_for_fallback_or_reversion=False,
            truth_used_for_offline_metrics=True,
            summary="Legacy initialization is retained, but LM acceptance is residual/trust-region based; truth is used for offline metrics.",
        ),
        readiness="human_review_only",
        recommended_use="defensible_step_b_backbone",
        units_status="units_consistent_but_legacy",
        result_lineage_status="registered",
        implementation_status="adapter_planned",
        adapter_module="jcls_sim.pipelines.migration",
        runner_script="scripts/run_controlled_migration_ladder.py",
        notes="Current defensible Step B backbone; package execution adapter is planned, not available.",
    )


def _package_native_c7() -> PipelineSpec:
    return PipelineSpec(
        pipeline_id="package_native_c7",
        display_name="Package-native C7 reference",
        stage_versions=PipelineStageVersions(
            system_model_version="package_native_current",
            initialization_version="A1_package_dl_only",
            stage_a_version="A1_package_dl_only",
            stage_b_version="B1_residual_lm",
            stage_c_version="C7_residual_cov_sync_safeguard",
            metric_version="V24_reference_relative_excluding_reference_satellite",
            units_version="package_km_positions_range_equivalent_clocks_with_seconds_ns_reporting",
        ),
        truth_use=TruthUseLedger(
            truth_used_for_prior_construction=False,
            truth_used_for_initialization=False,
            truth_used_for_lm_acceptance=False,
            truth_used_for_step_c_acceptance=False,
            truth_used_for_covariance=False,
            truth_used_for_fallback_or_reversion=False,
            truth_used_for_offline_metrics=True,
            summary="No truth is used for estimator decisions; truth is used only for offline metrics.",
        ),
        readiness="human_review_only",
        recommended_use="v24_clean_backup_reference",
        units_status="units_consistent",
        result_lineage_status="registered",
        implementation_status="adapter_available",
        adapter_module="jcls_sim.pipelines.adapters",
        runner_script="scripts/run_standard_benchmark_cards.py",
        notes="V24-clean backup/reference path; bounded primary-standard benchmark-card adapter is available.",
    )


def _legacy_truth_gated_l0_reference_only() -> PipelineSpec:
    return PipelineSpec(
        pipeline_id="legacy_truth_gated_l0_reference_only",
        display_name="Legacy truth-gated L0 reference",
        stage_versions=PipelineStageVersions(
            system_model_version="legacy_all_clock",
            initialization_version="A0_legacy_il_clockless_preconditioning",
            stage_a_version="A0_legacy_il_clockless_preconditioning",
            stage_b_version="B0_legacy_lm_truth_gate",
            stage_c_version="C0_legacy_truth_cov_ekf",
            metric_version="legacy_all_clock_metric",
            units_version="legacy_km_range_equivalent_clock_units_with_m_ns_reporting",
        ),
        truth_use=TruthUseLedger(
            truth_used_for_prior_construction=False,
            truth_used_for_initialization=True,
            truth_used_for_lm_acceptance=True,
            truth_used_for_step_c_acceptance=True,
            truth_used_for_covariance=True,
            truth_used_for_fallback_or_reversion=True,
            truth_used_for_offline_metrics=True,
            summary=(
                "Legacy provenance reference uses truth-centered initialization, "
                "truth-gated acceptance/fallback, truth-derived covariance, and offline metrics."
            ),
        ),
        readiness="legacy_reference_only",
        recommended_use="provenance_reference_only_not_manuscript_evidence",
        units_status="units_consistent_but_legacy",
        result_lineage_status="registered",
        implementation_status="deprecated",
        adapter_module="legacy_provenance_only",
        runner_script="scripts/replay_legacy_clock_sweep_figures.py",
        notes="Reference-only legacy path; not a manuscript-evidence pipeline.",
    )


_PIPELINE_SPECS = {
    spec.pipeline_id: spec
    for spec in (
        _legacy_surgical_prior_region(),
        _controlled_migration_step_b_lm_only(),
        _package_native_c7(),
        _legacy_truth_gated_l0_reference_only(),
    )
}


def pipeline_specs() -> tuple[PipelineSpec, ...]:
    """Return all registered schema-only pipeline specs."""

    return tuple(_PIPELINE_SPECS[pipeline_id] for pipeline_id in sorted(_PIPELINE_SPECS))


def pipeline_ids() -> tuple[str, ...]:
    """Return sorted registered pipeline IDs."""

    return tuple(sorted(_PIPELINE_SPECS))


def get_pipeline_spec(pipeline_id: str) -> PipelineSpec:
    """Return one registered pipeline spec by ID."""

    try:
        return _PIPELINE_SPECS[pipeline_id]
    except KeyError as exc:
        raise KeyError(f"Unknown pipeline_id: {pipeline_id}") from exc
