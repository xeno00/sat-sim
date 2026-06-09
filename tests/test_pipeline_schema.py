import json
import unittest

from jcls_sim.benchmark.runner import run_pipeline
from jcls_sim.benchmark.standard_cases import primary_standard_case
from jcls_sim.pipelines.registry import get_pipeline_spec, pipeline_ids, pipeline_specs
from jcls_sim.pipelines.specs import (
    BenchmarkCard,
    PipelineRunResult,
    PipelineStageVersions,
    StageMetrics,
    TruthUseLedger,
)


REQUIRED_PIPELINES = {
    "legacy_surgical_prior_region",
    "controlled_migration_step_b_lm_only",
    "package_native_c7",
    "legacy_truth_gated_l0_reference_only",
}


class PipelineSchemaTests(unittest.TestCase):
    def test_registry_contains_exact_required_pipeline_ids(self) -> None:
        self.assertEqual(set(pipeline_ids()), REQUIRED_PIPELINES)
        self.assertEqual(len(pipeline_specs()), 4)

    def test_every_pipeline_has_required_metadata(self) -> None:
        for spec in pipeline_specs():
            with self.subTest(spec.pipeline_id):
                payload = spec.to_dict()
                json.dumps(payload)
                self.assertIn("system_model_version", payload["stage_versions"])
                self.assertIn("stage_a_version", payload["stage_versions"])
                self.assertIn("stage_b_version", payload["stage_versions"])
                self.assertIn("stage_c_version", payload["stage_versions"])
                self.assertIn("truth_used_for_lm_acceptance", payload["truth_use"])
                self.assertTrue(payload["readiness"])
                self.assertTrue(payload["recommended_use"])
                self.assertTrue(payload["units_status"])
                self.assertTrue(payload["result_lineage_status"])
                self.assertTrue(payload["implementation_status"])

    def test_legacy_truth_gated_pipeline_records_truth_use(self) -> None:
        spec = get_pipeline_spec("legacy_truth_gated_l0_reference_only")

        self.assertEqual(spec.readiness, "legacy_reference_only")
        self.assertEqual(spec.implementation_status, "deprecated")
        self.assertTrue(spec.truth_use.truth_used_for_initialization)
        self.assertTrue(spec.truth_use.truth_used_for_lm_acceptance)
        self.assertTrue(spec.truth_use.truth_used_for_step_c_acceptance)
        self.assertTrue(spec.truth_use.truth_used_for_covariance)
        self.assertTrue(spec.truth_use.truth_used_for_fallback_or_reversion)

    def test_primary_candidate_records_adapter_planned(self) -> None:
        spec = get_pipeline_spec("legacy_surgical_prior_region")

        self.assertEqual(spec.readiness, "candidate_nonfinal")
        self.assertEqual(spec.implementation_status, "adapter_planned")
        self.assertEqual(spec.recommended_use, "pursue_as_primary_after_normalized_validation")
        self.assertTrue(spec.truth_use.truth_used_for_prior_construction)
        self.assertFalse(spec.truth_use.truth_used_for_lm_acceptance)
        self.assertFalse(spec.truth_use.truth_used_for_step_c_acceptance)
        self.assertFalse(spec.truth_use.truth_used_for_covariance)

    def test_stage_versions_reject_missing_fields(self) -> None:
        with self.assertRaisesRegex(ValueError, "system_model_version"):
            PipelineStageVersions(
                system_model_version="",
                initialization_version="init",
                stage_a_version="a",
                stage_b_version="b",
                stage_c_version="c",
                metric_version="metric",
                units_version="units",
            )

    def test_truth_use_ledger_requires_summary(self) -> None:
        with self.assertRaisesRegex(ValueError, "summary"):
            TruthUseLedger(
                truth_used_for_prior_construction=False,
                truth_used_for_initialization=False,
                truth_used_for_lm_acceptance=False,
                truth_used_for_step_c_acceptance=False,
                truth_used_for_covariance=False,
                truth_used_for_fallback_or_reversion=False,
                truth_used_for_offline_metrics=True,
                summary="",
            )

    def test_stage_metrics_missing_values_require_reason(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing_reason"):
            StageMetrics(pos_error_m=None, sync_error_ns=None, available=False)
        with self.assertRaisesRegex(ValueError, "None"):
            StageMetrics(pos_error_m=1.0, sync_error_ns=None, available=False, missing_reason="not run")
        with self.assertRaisesRegex(ValueError, "at least one"):
            StageMetrics(pos_error_m=None, sync_error_ns=None, available=True)

    def test_benchmark_card_serializes_claims_and_missing_metrics(self) -> None:
        pipeline = get_pipeline_spec("package_native_c7")
        case = primary_standard_case()
        missing = StageMetrics(
            pos_error_m=None,
            sync_error_ns=None,
            available=False,
            missing_reason="schema-only layer; execution adapter not implemented",
        )
        result = PipelineRunResult(
            pipeline_id=pipeline.pipeline_id,
            case_id=case.case_id,
            initialization=missing,
            step_a=missing,
            step_b=missing,
            step_c=missing,
            truth_use=pipeline.truth_use,
            units_status=pipeline.units_status,
            readiness=pipeline.readiness,
            warnings=("schema only",),
        )
        card = BenchmarkCard(
            pipeline=pipeline,
            case=case,
            result=result,
            safe_claims=("schema records pipeline metadata",),
            unsafe_claims=("no benchmark result has been generated",),
            recommended_next_action="implement execution adapter",
        )

        payload = card.to_dict()
        json.dumps(payload)
        self.assertEqual(payload["safe_claims"], ["schema records pipeline metadata"])
        self.assertEqual(payload["unsafe_claims"], ["no benchmark result has been generated"])
        self.assertFalse(payload["result"]["step_c"]["available"])

    def test_runner_does_not_fabricate_unavailable_adapter_results(self) -> None:
        result = run_pipeline(primary_standard_case(), get_pipeline_spec("legacy_surgical_prior_region"))

        self.assertFalse(result.step_a.available)
        self.assertIsNone(result.step_a.pos_error_m)
        self.assertEqual(result.step_a.missing_reason, "legacy_surgical_adapter_not_integrated_on_main")


if __name__ == "__main__":
    unittest.main()
