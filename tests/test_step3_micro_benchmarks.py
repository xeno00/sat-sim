import json
import time
import unittest
from pathlib import Path

import numpy as np

from scripts import benchmark_step3_micro_cases as micro


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs" / "step3_micro_benchmarks"
REPORTS = ROOT / "outputs" / "reports"
GALLERY = ROOT / "outputs" / "gallery" / "PLOT_GALLERY.json"


class TestStep3MicroBenchmarks(unittest.TestCase):
    def test_dry_run_lists_micro_work_without_ladders(self) -> None:
        planned = micro.main(["--dry-run"])

        self.assertEqual(planned["artifact_status"], "non_final_step3_micro_benchmark_planned_work")
        self.assertFalse(planned["will_execute"])
        self.assertFalse(planned["network_size_graphs_run"])
        self.assertFalse(planned["full_ladder_run"])
        self.assertFalse(planned["medium_grid_run"])
        self.assertEqual(len(planned["cases"]), 6)
        self.assertEqual(len(planned["variants"]), 6)

    def test_cases_have_explicit_expected_behavior(self) -> None:
        cases = micro._micro_cases()
        names = {case.name for case in cases}

        self.assertEqual(
            names,
            {
                "clock_only_correction",
                "position_only_correction",
                "clock_drift_correction",
                "gauge_common_clock_perturbation",
                "mixed_position_clock_perturbation",
                "schur_nuisance_clock_toy",
            },
        )
        for case in cases:
            self.assertTrue(case.expected_behavior)
            self.assertLessEqual(case.true_positions_km.shape[0], 3)
            self.assertLessEqual(case.num_satellites, 6)

    def test_variants_cover_structural_step3_ideas(self) -> None:
        variants = {variant.name: variant for variant in micro.VARIANTS}

        self.assertIn("baseline_c5_current_cov", variants)
        self.assertIn("block_scaled_no_drift", variants)
        self.assertTrue(variants["block_scaled_with_clock_drift"].include_drift_state)
        self.assertTrue(variants["gauge_common_clock_projected"].project_common_clock)
        self.assertTrue(variants["schur_nuisance_clock_reduced"].schur_eliminate_clocks)
        self.assertTrue(variants["clock_only_filter"].clock_only)

    def test_block_covariance_dimensions_and_units_are_consistent(self) -> None:
        case = micro._micro_cases()[0]
        for variant in micro.VARIANTS:
            theta = micro._pack_state(
                case.estimate_positions_km,
                case.estimate_clocks_km,
                case.estimate_drifts_km_per_s if variant.include_drift_state else None,
            )
            prior = micro._prior_variances(case, variant)

            self.assertEqual(prior.shape, theta.shape)
            self.assertTrue(np.all(prior > 0.0))

    def test_clock_drift_transition_changes_later_epoch_prediction(self) -> None:
        case = next(item for item in micro._micro_cases() if item.name == "clock_drift_correction")
        drift_variant = next(item for item in micro.VARIANTS if item.name == "block_scaled_with_clock_drift")
        no_drift_variant = next(item for item in micro.VARIANTS if item.name == "block_scaled_no_drift")
        drift_theta = micro._pack_state(case.estimate_positions_km, case.estimate_clocks_km, case.true_drifts_km_per_s)
        no_drift_theta = micro._pack_state(case.estimate_positions_km, case.estimate_clocks_km)

        _, drift_pred, drift_jac = micro._measurements_and_jacobian(case, drift_variant, drift_theta)
        _, no_drift_pred, no_drift_jac = micro._measurements_and_jacobian(case, no_drift_variant, no_drift_theta)

        self.assertNotEqual(drift_jac.shape[1], no_drift_jac.shape[1])
        self.assertFalse(np.allclose(drift_pred, no_drift_pred))

    def test_gauge_projection_removes_common_clock_component(self) -> None:
        case = next(item for item in micro._micro_cases() if item.name == "gauge_common_clock_perturbation")
        variant = next(item for item in micro.VARIANTS if item.name == "gauge_common_clock_projected")

        row = micro._evaluate_case_variant(case, variant, [])

        self.assertTrue(row["finite_output"])
        self.assertLess(row["common_clock_update_component"], 1.0e-10)
        self.assertTrue(row["expected_behavior_pass"])

    def test_schur_nuisance_clock_toy_solve_runs(self) -> None:
        case = next(item for item in micro._micro_cases() if item.name == "schur_nuisance_clock_toy")
        variant = next(item for item in micro.VARIANTS if item.name == "schur_nuisance_clock_reduced")

        row = micro._evaluate_case_variant(case, variant, [])

        self.assertTrue(row["finite_output"])
        self.assertTrue(row["expected_behavior_pass"])
        self.assertGreaterEqual(row["position_update_norm"], 0.0)
        self.assertGreaterEqual(row["ue_clock_update_norm"], 0.0)

    def test_micro_benchmark_runs_in_seconds_and_writes_reports(self) -> None:
        started = time.monotonic()
        payload = micro.run_benchmarks()
        elapsed = time.monotonic() - started

        self.assertLess(elapsed, 20.0)
        self.assertEqual(payload["row_count"], 36)
        self.assertFalse(payload["network_size_graphs_run"])
        self.assertFalse(payload["full_ladder_run"])
        self.assertFalse(payload["medium_grid_run"])
        self.assertTrue((OUTPUT_ROOT / "raw.csv").exists())
        self.assertTrue((OUTPUT_ROOT / "summary.csv").exists())
        self.assertTrue((OUTPUT_ROOT / "metadata.json").exists())
        self.assertTrue((REPORTS / "STEP3_MICRO_BENCHMARK_REPORT.md").exists())
        self.assertTrue((REPORTS / "STEP3_MICRO_BENCHMARK_REPORT.json").exists())
        self.assertTrue(all(row["finite_output"] for row in payload["rows"]))

    def test_promotion_rule_requires_required_micro_cases(self) -> None:
        payload_path = REPORTS / "STEP3_MICRO_BENCHMARK_REPORT.json"
        if not payload_path.exists():
            self.skipTest("Micro-benchmark report has not been generated")
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        rows = payload["rows"]

        required_cases = {
            "clock_only_correction",
            "position_only_correction",
            "gauge_common_clock_perturbation",
            "mixed_position_clock_perturbation",
        }
        for variant in payload["promoted_variants"]:
            passed = {
                row["case_name"]
                for row in rows
                if row["variant"] == variant and row["expected_behavior_pass"]
            }
            self.assertTrue(required_cases.issubset(passed), variant)

    def test_gallery_includes_micro_benchmark_plots_when_rendered(self) -> None:
        if not (OUTPUT_ROOT / "plots" / "pass_fail_heatmap.pdf").exists():
            self.skipTest("Micro-benchmark plots have not been generated")
        if not GALLERY.exists():
            self.skipTest("Plot gallery has not been rendered")
        gallery = json.loads(GALLERY.read_text(encoding="utf-8"))
        paths = {entry["source_pdf_path"] for entry in gallery["entries"]}

        self.assertIn("outputs/step3_micro_benchmarks/plots/pass_fail_heatmap.pdf", paths)
        self.assertIn("outputs/step3_micro_benchmarks/plots/position_clock_improvement_scatter.pdf", paths)


if __name__ == "__main__":
    unittest.main()
