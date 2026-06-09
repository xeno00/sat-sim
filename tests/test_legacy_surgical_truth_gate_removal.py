import csv
import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "legacy_surgical_truth_gate_removal"
REPORTS = ROOT / "outputs" / "reports"


class TestLegacySurgicalTruthGateRemoval(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        required = [
            OUTPUT / "raw.csv",
            OUTPUT / "summary.csv",
            OUTPUT / "trace.jsonl",
            OUTPUT / "metadata.json",
            OUTPUT / "arrays.npz",
            REPORTS / "LEGACY_SURGICAL_TRUTH_GATE_REMOVAL_REPORT.json",
            REPORTS / "LEGACY_SURGICAL_TRUTH_GATE_REMOVAL_REPORT.md",
            REPORTS / "LEGACY_SURGICAL_TASK_MATRIX.json",
            REPORTS / "LEGACY_SURGICAL_TASK_MATRIX.md",
        ]
        missing = [path for path in required if not path.exists()]
        if missing:
            raise AssertionError(f"Run scripts/run_legacy_surgical_truth_gate_removal.py first; missing {missing}")

    def _raw_rows(self) -> list[dict[str, str]]:
        with (OUTPUT / "raw.csv").open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))

    def _report(self) -> dict:
        return json.loads((REPORTS / "LEGACY_SURGICAL_TRUTH_GATE_REMOVAL_REPORT.json").read_text(encoding="utf-8"))

    def _metadata(self) -> dict:
        return json.loads((OUTPUT / "metadata.json").read_text(encoding="utf-8"))

    def test_required_outputs_exist_and_are_nonfinal(self) -> None:
        metadata = self._metadata()
        report = self._report()

        self.assertFalse(metadata["manuscript_ready"])
        self.assertTrue(metadata["non_final_diagnostic"])
        self.assertFalse(report["manuscript_ready"])
        self.assertTrue(report["non_final_diagnostic"])
        for figure_paths in report["figures"].values():
            for relative_path in figure_paths:
                self.assertTrue((ROOT / relative_path).exists(), relative_path)

    def test_l0_pipeline_is_explicitly_truth_gated(self) -> None:
        rows = [row for row in self._raw_rows() if row["pipeline"] == "legacy_exact_truth_gated"]

        self.assertGreater(len(rows), 0)
        for row in rows:
            self.assertEqual(row["algorithmic_truth_use"], "legacy_reproduction_truth_use_only")
            self.assertEqual(row["truth_state_used_for_initialization"], "True")
            self.assertEqual(row["truth_state_used_for_lm_acceptance"], "True")
            self.assertEqual(row["truth_state_used_for_map_covariance"], "True")
            self.assertEqual(row["truth_state_used_for_map_acceptance"], "True")

    def test_l1_l2_remove_decision_and_covariance_truth_but_document_initialization(self) -> None:
        rows = [
            row
            for row in self._raw_rows()
            if row["pipeline"] in {"legacy_nontruth_lm", "legacy_surgical_nontruth"}
        ]

        self.assertGreater(len(rows), 0)
        for row in rows:
            self.assertEqual(row["truth_state_used_for_initialization"], "True")
            self.assertEqual(row["truth_state_used_for_lm_acceptance"], "False")
            self.assertEqual(row["truth_state_used_for_map_covariance"], "False")
            self.assertEqual(row["truth_state_used_for_map_acceptance"], "False")
            self.assertEqual(row["truth_state_used_for_metrics"], "True")

    def test_l2_uses_nontruth_residual_scaled_map_covariance(self) -> None:
        rows = [row for row in self._raw_rows() if row["pipeline"] == "legacy_surgical_nontruth"]

        self.assertGreater(len(rows), 0)
        for row in rows:
            self.assertEqual(row["map_covariance_mode"], "residual_scaled_information_pseudoinverse")
            self.assertEqual(row["map_update_mode"], "observable_residual_covariance_checks")
            self.assertGreaterEqual(int(row["map_accepted_updates"]), 0)

    def test_standard_cases_run_for_all_pipelines(self) -> None:
        expected_cases = {
            "std_nu3_ns10_fullmesh_los_clock1us_seed0",
            "std_nu3_ns4_fullmesh_los_clock1us_seed0",
            "std_nu3_ns10_fullmesh_los_clock10ns_seed0",
        }
        expected_pipelines = {
            "legacy_exact_truth_gated",
            "legacy_nontruth_lm",
            "legacy_surgical_nontruth",
        }
        observed = {(row["case_id"], row["pipeline"]) for row in self._raw_rows()}

        for case_id in expected_cases:
            for pipeline in expected_pipelines:
                self.assertIn((case_id, pipeline), observed)

    def test_units_ledger_exists_and_records_legacy_km_all_clock_metrics(self) -> None:
        ledger = self._report()["units_ledger"]
        text = json.dumps(ledger).lower()

        self.assertIn("kilometer internally", text)
        self.assertIn("range-equivalent kilometer", text)
        self.assertIn("all-clock", text)
        self.assertIn("not v24 reference-relative rmse", text)

    def test_truth_inventory_has_required_classifications(self) -> None:
        inventory = self._report()["truth_use_inventory"]
        classes = {item["classification"] for item in inventory}
        components = {item["component"] for item in inventory}

        self.assertIn("algorithmic_truth_use_remove", classes)
        self.assertIn("offline_metric_truth_use_ok", classes)
        self.assertIn("legacy_reproduction_truth_use_only", classes)
        self.assertIn("Legacy initialization", components)
        self.assertIn("LM acceptance", components)
        self.assertIn("MAP covariance", components)

    def test_summary_verdicts_are_green_on_bounded_cases(self) -> None:
        report = self._report()

        self.assertEqual(report["decision"], "green_light")
        self.assertTrue(report["l0_reproduces_legacy"])
        self.assertTrue(report["l1_preserves_stage_b_without_truth_lm"])
        self.assertTrue(report["l2_preserves_stage_c_without_truth_covariance"])
        self.assertTrue(all(row["verdict"] == "green_light" for row in report["summary"]))

    def test_trace_records_lm_and_map_steps(self) -> None:
        traces = [
            json.loads(line)
            for line in (OUTPUT / "trace.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

        self.assertGreater(len(traces), 0)
        l1 = [trace for trace in traces if trace["pipeline"] == "legacy_nontruth_lm"]
        l2 = [trace for trace in traces if trace["pipeline"] == "legacy_surgical_nontruth"]
        self.assertTrue(any(trace["lm_trace"] for trace in l1))
        self.assertTrue(any(trace["map_trace"] for trace in l2))

    def test_protected_manuscript_and_notebook_files_are_not_modified(self) -> None:
        diff = subprocess.run(
            ["git", "diff", "--name-only"],
            cwd=ROOT,
            text=True,
            check=True,
            stdout=subprocess.PIPE,
        ).stdout.splitlines()
        protected_fragments = [
            "JCLS_Simulation.ipynb",
            "Work-In-Progress",
            "All-Version-Archive",
            ".tex",
            ".bib",
            ".pdf",
            "PSFrag",
        ]

        offenders = [
            path
            for path in diff
            if any(fragment in path for fragment in protected_fragments)
            and not path.startswith("outputs/legacy_surgical_truth_gate_removal/")
            and not path.startswith("outputs/reports/LEGACY_SURGICAL")
            and not path.startswith("tests/test_legacy_surgical_truth_gate_removal.py")
        ]
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
