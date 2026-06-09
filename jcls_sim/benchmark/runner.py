"""No-execution benchmark runner interface for future pipeline adapters."""

from __future__ import annotations

from jcls_sim.pipelines.specs import PipelineRunResult, PipelineSpec

from .standard_cases import StandardCaseSpec


def run_pipeline(case: StandardCaseSpec, pipeline: PipelineSpec) -> PipelineRunResult:
    """Refuse to execute pipelines until adapters are implemented."""

    raise NotImplementedError(
        "Pipeline execution adapters are not implemented in the schema-only layer."
    )
