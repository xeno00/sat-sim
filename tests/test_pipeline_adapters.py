"""Tests for normalized pipeline execution adapters."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from jcls_sim.benchmark.standard_cases import primary_standard_case
from jcls_sim.pipelines.adapters import run_pipeline_adapter
from jcls_sim.pipelines.registry import get_pipeline_spec


class PipelineAdapterTests(unittest.TestCase):
    """Verify adapter execution and missing-result boundaries."""

    def test_unavailable_adapters_return_missing_result(self) -> None:
        """Unimplemented adapters must not fabricate metrics."""

        case = primary_standard_case()
        pipeline = get_pipeline_spec("legacy_surgical_prior_region")
        result = run_pipeline_adapter(pipeline, case)

        self.assertEqual(result.pipeline_id, pipeline.pipeline_id)
        self.assertFalse(result.step_a.available)
        self.assertIsNone(result.step_a.pos_error_m)
        self.assertEqual(result.step_a.missing_reason, "legacy_surgical_adapter_not_integrated_on_main")
        self.assertEqual(result.truth_use, pipeline.truth_use)

    def test_package_native_c7_adapter_builds_result_from_rows(self) -> None:
        """Package-native C7 adapter maps row metrics to StageMetrics."""

        case = primary_standard_case()
        pipeline = get_pipeline_spec("package_native_c7")
        fake_rows = [
            {
                "baseline_id": "without_cooperation",
                "position_error_mean_m": 10.0,
                "sync_error_mean_s": 1.0e-6,
            },
            {
                "baseline_id": "coarse_jcls",
                "position_error_mean_m": 4.0,
                "sync_error_mean_s": 2.0e-7,
            },
            {
                "baseline_id": "refined_jcls",
                "position_error_mean_m": 3.0,
                "sync_error_mean_s": 1.0e-7,
            },
        ]

        with (
            patch(
                "jcls_sim.pipelines.adapters.package_native_standard_scenario",
                return_value=(SimpleNamespace(scenario_name="patched_test_scenario"), {"geometry": {"geometry_model": "test"}}),
            ),
            patch("jcls_sim.pipelines.adapters.run_single_trial_step_c7_algorithm", return_value=fake_rows),
        ):
            result = run_pipeline_adapter(pipeline, case)

        self.assertFalse(result.initialization.available)
        self.assertEqual(result.step_a.pos_error_m, 10.0)
        self.assertEqual(result.step_a.sync_error_ns, 1000.0)
        self.assertEqual(result.step_b.pos_error_m, 4.0)
        self.assertEqual(result.step_c.pos_error_m, 3.0)
        self.assertEqual(result.truth_use, pipeline.truth_use)


if __name__ == "__main__":
    unittest.main()
