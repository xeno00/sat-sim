"""Canonical pipeline schema for non-final benchmark-card provenance."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

READINESS_STATUSES = frozenset(
    {
        "legacy_reference_only",
        "debug_only",
        "human_review_only",
        "candidate_nonfinal",
        "manuscript_ready",
        "blocked",
    }
)

IMPLEMENTATION_STATUSES = frozenset(
    {
        "schema_only",
        "adapter_planned",
        "adapter_available",
        "runner_available",
        "deprecated",
    }
)


@dataclass(frozen=True)
class PipelineStageVersions:
    """Version labels for one result-generation pipeline tuple."""

    system_model_version: str
    initialization_version: str
    stage_a_version: str
    stage_b_version: str
    stage_c_version: str
    metric_version: str
    units_version: str

    def __post_init__(self) -> None:
        """Validate that all tuple fields are explicit strings."""

        for field_name, value in asdict(self).items():
            if not isinstance(value, str) or not value:
                raise ValueError(f"{field_name} must be a nonempty string.")

    def to_dict(self) -> dict[str, str]:
        """Return a JSON-compatible dictionary."""

        return asdict(self)


@dataclass(frozen=True)
class TruthUseLedger:
    """Truth-use declaration for estimator decisions and offline metrics."""

    truth_used_for_prior_construction: bool
    truth_used_for_initialization: bool
    truth_used_for_lm_acceptance: bool
    truth_used_for_step_c_acceptance: bool
    truth_used_for_covariance: bool
    truth_used_for_fallback_or_reversion: bool
    truth_used_for_offline_metrics: bool
    summary: str

    def __post_init__(self) -> None:
        """Validate that the ledger summary is explicit."""

        if not isinstance(self.summary, str) or not self.summary:
            raise ValueError("summary must be a nonempty string.")

    def to_dict(self) -> dict[str, bool | str]:
        """Return a JSON-compatible dictionary."""

        return asdict(self)


@dataclass(frozen=True)
class PipelineSpec:
    """Static metadata for one benchmark-capable or provenance pipeline."""

    pipeline_id: str
    display_name: str
    stage_versions: PipelineStageVersions
    truth_use: TruthUseLedger
    readiness: str
    recommended_use: str
    units_status: str
    result_lineage_status: str
    implementation_status: str
    adapter_module: str
    runner_script: str
    notes: str

    def __post_init__(self) -> None:
        """Validate registry status fields."""

        if not self.pipeline_id:
            raise ValueError("pipeline_id must be nonempty.")
        if not self.display_name:
            raise ValueError("display_name must be nonempty.")
        if self.readiness not in READINESS_STATUSES:
            raise ValueError(f"Unsupported readiness: {self.readiness!r}.")
        if self.implementation_status not in IMPLEMENTATION_STATUSES:
            raise ValueError(f"Unsupported implementation_status: {self.implementation_status!r}.")
        for field_name in (
            "recommended_use",
            "units_status",
            "result_lineage_status",
            "adapter_module",
            "runner_script",
            "notes",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value:
                raise ValueError(f"{field_name} must be a nonempty string.")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible dictionary."""

        return {
            "pipeline_id": self.pipeline_id,
            "display_name": self.display_name,
            "stage_versions": self.stage_versions.to_dict(),
            "truth_use": self.truth_use.to_dict(),
            "readiness": self.readiness,
            "recommended_use": self.recommended_use,
            "units_status": self.units_status,
            "result_lineage_status": self.result_lineage_status,
            "implementation_status": self.implementation_status,
            "adapter_module": self.adapter_module,
            "runner_script": self.runner_script,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class StageMetrics:
    """Localization/synchronization metrics for one pipeline stage."""

    pos_error_m: float | None
    sync_error_ns: float | None
    available: bool
    missing_reason: str | None = None
    metric_notes: str = ""

    def __post_init__(self) -> None:
        """Validate missing-metric semantics."""

        if self.available:
            if self.pos_error_m is None and self.sync_error_ns is None:
                raise ValueError("available StageMetrics must include at least one metric value.")
            if self.missing_reason:
                raise ValueError("available StageMetrics must not include missing_reason.")
        else:
            if self.pos_error_m is not None or self.sync_error_ns is not None:
                raise ValueError("unavailable StageMetrics must have None error values.")
            if not self.missing_reason:
                raise ValueError("unavailable StageMetrics require a missing_reason.")

    def to_dict(self) -> dict[str, float | bool | str | None]:
        """Return a JSON-compatible dictionary."""

        return asdict(self)


@dataclass(frozen=True)
class PipelineRunResult:
    """Schema-only result record for a future pipeline execution adapter."""

    pipeline_id: str
    case_id: str
    initialization: StageMetrics
    step_a: StageMetrics
    step_b: StageMetrics
    step_c: StageMetrics
    truth_use: TruthUseLedger
    units_status: str
    readiness: str
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validate result status fields."""

        if not self.pipeline_id:
            raise ValueError("pipeline_id must be nonempty.")
        if not self.case_id:
            raise ValueError("case_id must be nonempty.")
        if self.readiness not in READINESS_STATUSES:
            raise ValueError(f"Unsupported readiness: {self.readiness!r}.")
        if not self.units_status:
            raise ValueError("units_status must be nonempty.")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible dictionary."""

        return {
            "pipeline_id": self.pipeline_id,
            "case_id": self.case_id,
            "initialization": self.initialization.to_dict(),
            "step_a": self.step_a.to_dict(),
            "step_b": self.step_b.to_dict(),
            "step_c": self.step_c.to_dict(),
            "truth_use": self.truth_use.to_dict(),
            "units_status": self.units_status,
            "readiness": self.readiness,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class BenchmarkCard:
    """Schema-only benchmark-card envelope for one pipeline and case."""

    pipeline: PipelineSpec
    case: Any
    result: PipelineRunResult
    safe_claims: tuple[str, ...]
    unsafe_claims: tuple[str, ...]
    recommended_next_action: str

    def __post_init__(self) -> None:
        """Validate benchmark-card claims and identity consistency."""

        if not self.safe_claims:
            raise ValueError("safe_claims must include at least one entry.")
        if not self.unsafe_claims:
            raise ValueError("unsafe_claims must include at least one entry.")
        if not self.recommended_next_action:
            raise ValueError("recommended_next_action must be nonempty.")
        if self.pipeline.pipeline_id != self.result.pipeline_id:
            raise ValueError("pipeline and result pipeline_id must match.")
        if getattr(self.case, "case_id", None) != self.result.case_id:
            raise ValueError("case and result case_id must match.")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible dictionary."""

        return {
            "pipeline": self.pipeline.to_dict(),
            "case": self.case.to_dict(),
            "result": self.result.to_dict(),
            "safe_claims": list(self.safe_claims),
            "unsafe_claims": list(self.unsafe_claims),
            "recommended_next_action": self.recommended_next_action,
        }
