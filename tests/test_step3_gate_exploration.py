import inspect
import json
import unittest
from pathlib import Path

from scripts import explore_step3_gates as gates


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs" / "step3_gate_exploration"
REPORTS = ROOT / "outputs" / "reports"
GALLERY = ROOT / "outputs" / "gallery" / "PLOT_GALLERY.json"


class TestStep3GateExploration(unittest.TestCase):
    def test_default_plan_is_sparse_and_not_full_ladder(self) -> None:
        planned = gates.main(["--dry-run", "--max-cases", "1", "--max-gates", "2"])

        self.assertEqual(planned["artifact_status"], "non_final_step3_gate_exploration_planned_work")
        self.assertFalse(planned["will_execute"])
        self.assertTrue(planned["default_is_sparse_only"])
        self.assertFalse(planned["full_ladder_run"])
        self.assertEqual(planned["row_count"], 2)

    def test_planned_rows_use_representative_cases(self) -> None:
        rows = gates._planned_rows()
        cases = {(row["num_users"], row["num_satellites"]) for row in rows}

        self.assertEqual(cases, set(gates.CASES))
        self.assertEqual(len(rows), len(gates.CASES) * len(gates.GATES))

    def test_gate_update_source_does_not_use_truth_state(self) -> None:
        source = inspect.getsource(gates._evaluate_gate_update)

        self.assertNotIn("get_true_state", source)
        self.assertIn("truth_state_used_for_acceptance", source)

    def test_gate_configs_cover_required_diagnostics(self) -> None:
        gate_names = {gate.name for gate in gates.GATES}

        self.assertIn("nis_line_search", gate_names)
        self.assertIn("nullspace_line_search", gate_names)
        self.assertIn("clock_position_line_search", gate_names)
        self.assertIn("huber_line_search", gate_names)
        self.assertIn("covariance_k10", gate_names)
        self.assertIn("measurement_lambda10", gate_names)

    def test_outputs_exist_when_exploration_has_run(self) -> None:
        metadata = OUTPUT_ROOT / "metadata.json"
        if not metadata.exists():
            self.skipTest("Step 3 gate exploration outputs have not been generated")
        payload = json.loads(metadata.read_text(encoding="utf-8"))

        self.assertFalse(payload["manuscript_ready"])
        self.assertFalse(payload["truth_state_used_for_acceptance"])
        self.assertTrue(payload["truth_state_used_for_diagnostics"])
        self.assertEqual(payload["row_count"], len(gates.CASES) * len(gates.GATES))
        self.assertTrue((OUTPUT_ROOT / "step3_gate_exploration_raw.csv").exists())
        self.assertTrue((OUTPUT_ROOT / "objective_history.json").exists())
        self.assertTrue((OUTPUT_ROOT / "update_diagnostics.json").exists())

    def test_diagnostics_record_nis_nullspace_and_alpha(self) -> None:
        path = OUTPUT_ROOT / "update_diagnostics.json"
        if not path.exists():
            self.skipTest("Step 3 gate diagnostics have not been generated")
        payload = json.loads(path.read_text(encoding="utf-8"))
        row = payload["rows"][0]

        self.assertIn("nis", row)
        self.assertIn("nullspace_ratio", row)
        self.assertIn("chosen_alpha", row)
        self.assertIn("clock_position_update_ratio", row)
        self.assertIn("both_improved", row)
        self.assertFalse(row["truth_state_used_for_acceptance"])
        self.assertTrue(row["truth_state_used_for_diagnostics"])

    def test_report_records_no_medium_validation_by_default(self) -> None:
        path = REPORTS / "STEP3_GATE_EXPLORATION_REPORT.json"
        if not path.exists():
            self.skipTest("Step 3 gate report has not been generated")
        payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertFalse(payload["medium_validation_run"])
        self.assertFalse(payload["manuscript_ready"])
        self.assertEqual(payload["branch_policy"], "sparse_cases_only_no_full_ladder")

    def test_gallery_includes_exploration_plots_when_outputs_exist(self) -> None:
        if not (OUTPUT_ROOT / "position_sync_ratio_scatter.pdf").exists():
            self.skipTest("Step 3 gate exploration plots have not been generated")
        gallery = json.loads(GALLERY.read_text(encoding="utf-8"))
        paths = {entry["source_pdf_path"] for entry in gallery["entries"]}

        self.assertIn("outputs/step3_gate_exploration/position_sync_ratio_scatter.pdf", paths)
        self.assertIn("outputs/step3_gate_exploration/gate_both_improved_bar.pdf", paths)


if __name__ == "__main__":
    unittest.main()
