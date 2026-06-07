import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.plan_v24_crlb_figure_decision import build_decision_plan, write_decision_plan


class TestV24CrlbFigureDecisionPlan(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="v24_crlb_decision_plan_test_"))

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_decision_plan_is_deterministic(self) -> None:
        first = build_decision_plan()
        second = build_decision_plan()

        self.assertEqual(first, second)

    def test_schema_marks_non_final_and_not_manuscript_figure(self) -> None:
        payload = build_decision_plan()

        self.assertEqual(payload["diagnostic_type"], "non_final_v24_crlb_figure_decision_plan")
        self.assertEqual(payload["decision_input_status"], "PASS_WITH_CAVEAT")
        self.assertTrue(payload["non_final"])
        self.assertFalse(payload["manuscript_figure"])

    def test_rank_feasibility_is_primary_recommendation(self) -> None:
        payload = build_decision_plan()
        first = payload["recommended_decision_path"][0]
        rank_summary = payload["candidate_summaries"]["rank_feasibility_heatmap"]

        self.assertEqual(first["candidate"], "rank_feasibility_heatmap")
        self.assertEqual(first["recommendation"], "propose_first")
        self.assertEqual(rank_summary["recommended_role"], "primary_decision_candidate")
        self.assertGreater(rank_summary["rank_deficient_cells"], 0)
        self.assertGreater(rank_summary["full_rank_cells"], 0)

    def test_growing_ns_caveat_is_explicit(self) -> None:
        payload = build_decision_plan()
        finite = payload["candidate_summaries"]["finite_crlb_vs_ns"]

        self.assertFalse(finite["monotonicity_claim_valid"])
        self.assertIn("parameter dimension", finite["required_caveat"])
        self.assertGreater(finite["unavailable_rank_deficient_points"], 0)
        for series in finite["series"]:
            self.assertTrue(series["parameter_dim_changes"])

    def test_fixed_measurement_addition_is_sanity_check_only(self) -> None:
        payload = build_decision_plan()
        fixed = payload["candidate_summaries"]["fixed_parameter_measurement_addition"]

        self.assertEqual(fixed["recommended_role"], "sanity_check_or_supplemental_candidate")
        self.assertIn("fixed", fixed["required_caveat"])
        self.assertIn("pass", fixed["monotonicity_status"])
        self.assertIsNotNone(fixed["first_full_rank_measurement_count"])

    def test_manuscript_implications_flag_legacy_crlb_risk(self) -> None:
        payload = build_decision_plan()
        statuses = {
            item["target"]: item["status"]
            for item in payload["likely_manuscript_figure_implications"]
        }

        self.assertEqual(
            statuses["legacy_CRLB_vs_satellite_count_figures"],
            "likely_needs_package_native_rerun_or_replacement",
        )
        self.assertEqual(
            statuses["legacy_CRLB_localization_and_synchronization_panels"],
            "unsafe_until_package_native_workflow_is_approved",
        )

    def test_write_decision_plan_creates_json_output(self) -> None:
        output_path = self.temp_dir / "decision.json"

        written = write_decision_plan(output_path, overwrite=True)
        payload = json.loads(written.read_text(encoding="utf-8"))

        self.assertEqual(written, output_path)
        self.assertEqual(payload["diagnostic_type"], "non_final_v24_crlb_figure_decision_plan")
        self.assertIn("preview_outputs", payload)


if __name__ == "__main__":
    unittest.main()
