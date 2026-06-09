"""Bounded normalized benchmark-card runner."""

from __future__ import annotations

from typing import Iterable

from jcls_sim.pipelines.adapters import adapter_status, run_pipeline_adapter
from jcls_sim.pipelines.registry import get_pipeline_spec, pipeline_ids, pipeline_specs
from jcls_sim.pipelines.specs import BenchmarkCard, PipelineRunResult, PipelineSpec, StageMetrics

from .standard_cases import PRIMARY_STANDARD_CASE_ID, StandardCaseSpec, get_standard_case


STAGE_NAMES = ("initialization", "step_a", "step_b", "step_c")


def run_pipeline(case: StandardCaseSpec, pipeline: PipelineSpec) -> PipelineRunResult:
    """Run one pipeline adapter or return explicit missing stage metrics."""

    return run_pipeline_adapter(pipeline, case)


def benchmark_card_for_pipeline(case: StandardCaseSpec, pipeline: PipelineSpec) -> BenchmarkCard:
    """Return one normalized benchmark card for a pipeline/case pair."""

    result = run_pipeline(case, pipeline)
    any_available = any(getattr(result, stage).available for stage in STAGE_NAMES)
    if any_available:
        safe_claims = (
            f"{pipeline.pipeline_id} produced a bounded single-trial card for {case.case_id}.",
            "Truth-use, units, readiness, and missing-stage semantics are recorded in the card.",
        )
        unsafe_claims = (
            "This is not a manuscript figure, sweep, Monte Carlo result, or final evidence.",
            "One primary-standard fingerprint does not establish robustness.",
        )
        next_action = "Review benchmark card and implement remaining planned adapters before downselect."
    else:
        reason = _first_missing_reason(result)
        safe_claims = (
            f"{pipeline.pipeline_id} is represented without fabricated metrics.",
            f"Unavailable adapter reason is explicit: {reason}.",
        )
        unsafe_claims = (
            "No performance claim is available for this pipeline from this benchmark-card run.",
            "Missing metrics must not be substituted from legacy or secondary stress cases.",
        )
        next_action = "Implement a safe adapter boundary before using this pipeline as benchmark evidence."
    return BenchmarkCard(
        pipeline=pipeline,
        case=case,
        result=result,
        safe_claims=safe_claims,
        unsafe_claims=unsafe_claims,
        recommended_next_action=next_action,
    )


def run_benchmark_cards(
    *,
    case_id: str = PRIMARY_STANDARD_CASE_ID,
    selected_pipeline_ids: Iterable[str] | None = None,
) -> tuple[BenchmarkCard, ...]:
    """Return benchmark cards for selected pipelines on one standard case."""

    case = get_standard_case(case_id)
    ids = tuple(selected_pipeline_ids) if selected_pipeline_ids is not None else pipeline_ids()
    return tuple(benchmark_card_for_pipeline(case, get_pipeline_spec(pipeline_id)) for pipeline_id in ids)


def plan_rows(
    *,
    case_id: str = PRIMARY_STANDARD_CASE_ID,
    selected_pipeline_ids: Iterable[str] | None = None,
) -> list[dict[str, str]]:
    """Return a no-execution plan for the requested benchmark cards."""

    ids = tuple(selected_pipeline_ids) if selected_pipeline_ids is not None else pipeline_ids()
    # Validate case and pipeline ids while still avoiding adapter execution.
    case = get_standard_case(case_id)
    rows = []
    for pipeline_id in ids:
        pipeline = get_pipeline_spec(pipeline_id)
        rows.append(
            {
                "pipeline_id": pipeline.pipeline_id,
                "case_id": case.case_id,
                "adapter_status": adapter_status(pipeline),
                "readiness": pipeline.readiness,
                "recommended_use": pipeline.recommended_use,
                "units_status": pipeline.units_status,
            }
        )
    return rows


def stage_metric_columns(stage_name: str, metrics: StageMetrics) -> dict[str, float | str | bool | None]:
    """Return flattened CSV columns for one stage."""

    return {
        f"{stage_name}_pos_error_m": metrics.pos_error_m,
        f"{stage_name}_sync_error_ns": metrics.sync_error_ns,
        f"{stage_name}_available": metrics.available,
        f"{stage_name}_missing_reason": metrics.missing_reason or "",
        f"{stage_name}_metric_notes": metrics.metric_notes,
    }


def benchmark_card_row(card: BenchmarkCard) -> dict[str, object]:
    """Return a flattened output row for one benchmark card."""

    result = card.result
    row: dict[str, object] = {
        "pipeline_id": result.pipeline_id,
        "case_id": result.case_id,
        "system_model_version": card.pipeline.stage_versions.system_model_version,
        "initialization_version": card.pipeline.stage_versions.initialization_version,
        "stage_a_version": card.pipeline.stage_versions.stage_a_version,
        "stage_b_version": card.pipeline.stage_versions.stage_b_version,
        "stage_c_version": card.pipeline.stage_versions.stage_c_version,
        "metric_version": card.pipeline.stage_versions.metric_version,
        "units_version": card.pipeline.stage_versions.units_version,
        "readiness": result.readiness,
        "recommended_use": card.pipeline.recommended_use,
        "units_status": result.units_status,
        "implementation_status": card.pipeline.implementation_status,
        "truth_usage_summary": result.truth_use.summary,
        "warnings": "; ".join(result.warnings),
    }
    for stage_name in STAGE_NAMES:
        row.update(stage_metric_columns(stage_name, getattr(result, stage_name)))
    row["step_c_improves_position_over_step_b"] = _improves(result.step_b.pos_error_m, result.step_c.pos_error_m)
    row["step_c_improves_sync_over_step_b"] = _improves(result.step_b.sync_error_ns, result.step_c.sync_error_ns)
    return row


def summary_row(card: BenchmarkCard) -> dict[str, object]:
    """Return a compact summary row for one benchmark card."""

    result = card.result
    available_stages = [stage for stage in STAGE_NAMES if getattr(result, stage).available]
    return {
        "pipeline_id": result.pipeline_id,
        "case_id": result.case_id,
        "adapter_status": adapter_status(card.pipeline),
        "available_stage_count": len(available_stages),
        "available_stages": "; ".join(available_stages),
        "missing_reasons": "; ".join(_missing_reasons(result)),
        "readiness": result.readiness,
        "recommended_use": card.pipeline.recommended_use,
        "units_status": result.units_status,
        "step_c_improves_position_over_step_b": _improves(result.step_b.pos_error_m, result.step_c.pos_error_m),
        "step_c_improves_sync_over_step_b": _improves(result.step_b.sync_error_ns, result.step_c.sync_error_ns),
    }


def _improves(before: float | None, after: float | None) -> bool | None:
    """Return whether after is lower than before, preserving missing values."""

    if before is None or after is None:
        return None
    return bool(after < before)


def _missing_reasons(result: PipelineRunResult) -> tuple[str, ...]:
    """Return unique missing reasons across unavailable stages."""

    reasons = []
    for stage_name in STAGE_NAMES:
        reason = getattr(result, stage_name).missing_reason
        if reason and reason not in reasons:
            reasons.append(reason)
    return tuple(reasons)


def _first_missing_reason(result: PipelineRunResult) -> str:
    """Return the first missing reason in a result."""

    reasons = _missing_reasons(result)
    return reasons[0] if reasons else "none"


def default_pipeline_specs() -> tuple[PipelineSpec, ...]:
    """Return registered specs in runner order."""

    return pipeline_specs()
