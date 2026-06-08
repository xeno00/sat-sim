import inspect
import json
import unittest
from pathlib import Path

from scripts import explore_step3_low_cost as low_cost


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs" / "step3_low_cost_exploration"
REPORTS = ROOT / "outputs" / "reports"
GALLERY = ROOT / "outputs" / "gallery" / "PLOT_GALLERY.json"


class TestStep3LowCostExploration(unittest.TestCase):
    def test_default_plan_is_sparse_and_not_full_grid(self) -> None:
        planned = low_cost.main(["--dry-run", "--max-cases", "1", "--max-methods", "2"])

        self.assertEqual(planned["artifact_status"], "non_final_step3_low_cost_planned_work")
        self.assertFalse(planned["will_execute"])
        self.assertTrue(planned["default_is_sparse_only"])
        self.assertFalse(planned["full_ladder_run"])
        self.assertFalse(planned["medium_validation_default"])
        self.assertEqual(planned["row_count"], 2)

    def test_planned_rows_include_lanes_and_cases(self) -> None:
        rows = low_cost._planned_rows()
        cases = {(row["num_users"], row["num_satellites"]) for row in rows}
        lanes = {row["lane"] for row in rows}

        self.assertEqual(cases, set(low_cost.CASES))
        self.assertIn("block_covariance", lanes)
        self.assertIn("clock_drift", lanes)
        self.assertIn("gauge_nullspace", lanes)
        self.assertIn("schur_nuisance_clock", lanes)
        self.assertIn("robust_measurement", lanes)
        self.assertIn("solver_mechanics", lanes)

    def test_method_source_does_not_use_truth_state_for_acceptance(self) -> None:
        source = inspect.getsource(low_cost._evaluate_method)

        self.assertNotIn("get_true_state", source)
        self.assertIn("truth_state_used_for_acceptance", source)
        self.assertIn("truth_state_used_for_covariance", source)

    def test_promotion_rule_is_bounded_to_two_ideas(self) -> None:
        summaries = [
            {
                "lane": "a",
                "method": "good",
                "both_improved_rows": 2,
                "mean_position_ratio": 0.9,
                "mean_sync_ratio": 0.9,
                "mean_runtime_seconds": 1.0,
            },
            {
                "lane": "b",
                "method": "also_good",
                "both_improved_rows": 2,
                "mean_position_ratio": 0.8,
                "mean_sync_ratio": 0.9,
                "mean_runtime_seconds": 1.0,
            },
            {
                "lane": "c",
                "method": "too_slow",
                "both_improved_rows": 3,
                "mean_position_ratio": 0.8,
                "mean_sync_ratio": 0.8,
                "mean_runtime_seconds": 99.0,
            },
        ]

        promoted = low_cost._promotion_candidates(summaries)

        self.assertEqual(len(promoted), 2)
        self.assertNotIn("too_slow", {item["method"] for item in promoted})

    def test_outputs_have_common_schema_when_generated(self) -> None:
        path = OUTPUT_ROOT / "metadata.json"
        if not path.exists():
            self.skipTest("Low-cost Step 3 outputs have not been generated")
        payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertFalse(payload["manuscript_ready"])
        self.assertFalse(payload["truth_state_used_for_acceptance"])
        self.assertFalse(payload["truth_state_used_for_covariance"])
        self.assertTrue(payload["truth_state_used_for_diagnostics"])
        self.assertFalse(payload["full_ladder_run"])
        self.assertFalse(payload["medium_validation_run"])
        self.assertTrue((OUTPUT_ROOT / "raw.csv").exists())
        self.assertTrue((OUTPUT_ROOT / "summary.csv").exists())

    def test_rows_record_ratios_and_cache_keys_when_generated(self) -> None:
        path = OUTPUT_ROOT / "step3_low_cost_results.json"
        if not path.exists():
            self.skipTest("Low-cost Step 3 results have not been generated")
        payload = json.loads(path.read_text(encoding="utf-8"))
        row = payload["rows"][0]

        self.assertIn("position_ratio", row)
        self.assertIn("sync_ratio", row)
        self.assertIn("cache_key", row)
        self.assertIn("lane", row)
        self.assertIn("method", row)
        self.assertFalse(row["truth_state_used_for_acceptance"])
        self.assertFalse(row["truth_state_used_for_covariance"])

    def test_each_lane_writes_common_files_when_generated(self) -> None:
        path = OUTPUT_ROOT / "metadata.json"
        if not path.exists():
            self.skipTest("Low-cost Step 3 outputs have not been generated")
        payload = json.loads(path.read_text(encoding="utf-8"))

        for lane in payload["lanes_run"]:
            lane_root = OUTPUT_ROOT / lane
            self.assertTrue((lane_root / "raw.csv").exists())
            self.assertTrue((lane_root / "summary.csv").exists())
            self.assertTrue((lane_root / "metadata.json").exists())

    def test_gallery_includes_low_cost_plots_when_outputs_exist(self) -> None:
        if not (OUTPUT_ROOT / "plots" / "pareto_position_sync_ratio.pdf").exists():
            self.skipTest("Low-cost Step 3 plots have not been generated")
        gallery = json.loads(GALLERY.read_text(encoding="utf-8"))
        paths = {entry["source_pdf_path"] for entry in gallery["entries"]}

        self.assertIn("outputs/step3_low_cost_exploration/plots/pareto_position_sync_ratio.pdf", paths)
        self.assertIn("outputs/step3_low_cost_exploration/plots/both_improved_by_lane.pdf", paths)


if __name__ == "__main__":
    unittest.main()
