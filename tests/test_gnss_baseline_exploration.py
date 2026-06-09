import csv
import json
import math
import unittest
from pathlib import Path

from scripts import run_gnss_baseline_exploration as gnss


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs" / "gnss_baseline_exploration"
REPORT_ROOT = ROOT / "outputs" / "reports"


class GNSSBaselineExplorationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = gnss.run_exploration(
            subagent_status={
                "agent_a": "completed_read_only_literature_scan",
                "agent_b": "completed_read_only_taxonomy",
                "agent_c": "completed_read_only_position_prior_plan",
                "agent_d": "completed_read_only_clock_prior_plan",
                "agent_e": "orchestrator_red_team_fallback",
            }
        )

    def test_taxonomy_exists_and_labels_all_baselines(self) -> None:
        taxonomy_json = OUTPUT_ROOT / "gnss_baseline_taxonomy.json"
        taxonomy_csv = OUTPUT_ROOT / "gnss_baseline_taxonomy.csv"
        taxonomy_md = OUTPUT_ROOT / "gnss_baseline_taxonomy.md"
        for path in (taxonomy_json, taxonomy_csv, taxonomy_md):
            self.assertTrue(path.exists(), f"missing {path}")
            self.assertGreater(path.stat().st_size, 0, f"empty {path}")

        payload = json.loads(taxonomy_json.read_text(encoding="utf-8"))
        labels = {row["label"] for row in payload["baselines"]}
        self.assertEqual(
            labels,
            {
                "standalone_gnss_reference",
                "degraded_gnss_reference",
                "gnss_aided_initialization",
                "gnss_clock_aided_ntn",
                "intermittent_gnss_update",
                "gnss_correction_service_reference",
                "leo_pnt_literature_reference",
            },
        )
        for row in payload["baselines"]:
            self.assertIn("oracle_diagnostic_reference", row)
            self.assertIn("comparison_class", row)
            self.assertIn("gnss_required", row)
            self.assertIn("assumption_summary", row)

    def test_no_oracle_or_reference_baseline_is_marked_fair(self) -> None:
        payload = json.loads((OUTPUT_ROOT / "gnss_baseline_taxonomy.json").read_text(encoding="utf-8"))
        for row in payload["baselines"]:
            label = str(row["oracle_diagnostic_reference"])
            if "oracle" in label or "reference" in label:
                self.assertFalse(row["fair_comparison_to_jcls"], row["label"])

    def test_prior_and_clock_sweeps_are_bounded_and_non_final(self) -> None:
        metadata = json.loads((OUTPUT_ROOT / "metadata.json").read_text(encoding="utf-8"))
        self.assertTrue(metadata["bounded_mode"])
        self.assertFalse(metadata["full_sweep_run"])
        self.assertTrue(metadata["non_final"])
        self.assertFalse(metadata["manuscript_ready"])
        self.assertTrue(metadata["not_for_manuscript_submission"])
        self.assertFalse(metadata["notebook_used"])
        self.assertFalse(metadata["manuscript_directories_touched"])

        position_rows = list(csv.DictReader((OUTPUT_ROOT / "gnss_prior_sensitivity_raw.csv").read_text(encoding="utf-8").splitlines()))
        clock_rows = list(csv.DictReader((OUTPUT_ROOT / "clock_prior_sensitivity_raw.csv").read_text(encoding="utf-8").splitlines()))
        self.assertEqual(len(position_rows), 3 * 5 * 3)
        self.assertEqual(len(clock_rows), 3 * 6 * 3)
        self.assertEqual({row["stage"] for row in position_rows}, {"stage_a_dl_only", "step_b_jcls", "c7_jcls"})
        self.assertEqual({row["stage"] for row in clock_rows}, {"dl_only", "step_b_jcls", "c7_jcls"})

        required = {
            "localization_rmse_m",
            "synchronization_rmse_ns",
            "convergence_probability",
            "runtime_seconds",
            "finite_output",
            "truth_state_used_for_acceptance",
            "truth_state_used_for_covariance",
            "truth_used_only_for_offline_metrics",
        }
        for row in position_rows + clock_rows:
            self.assertTrue(required.issubset(row.keys()))
            self.assertEqual(row["manuscript_ready"], "False")
            self.assertEqual(row["not_for_manuscript_submission"], "True")
            self.assertEqual(row["truth_state_used_for_acceptance"], "False")
            self.assertEqual(row["truth_state_used_for_covariance"], "False")

    def test_literature_table_has_citations_and_links(self) -> None:
        payload = json.loads((REPORT_ROOT / "GNSS_BASELINE_LITERATURE_TABLE.json").read_text(encoding="utf-8"))
        self.assertTrue(payload["non_final"])
        self.assertGreaterEqual(len(payload["sources"]), 8)
        labels = {row["label"] for row in payload["sources"]}
        self.assertIn("standalone_gnss_reference", labels)
        self.assertIn("gnss_correction_service_reference", labels)
        self.assertIn("leo_pnt_literature_reference", labels)
        for row in payload["sources"]:
            self.assertTrue(row["url"].startswith("https://"), row)
            self.assertTrue(row["source_title"], row)
            self.assertTrue(row["comparison_caveat"], row)

    def test_intermitent_gnss_rows_include_manuscript_drift_example(self) -> None:
        rows = json.loads((OUTPUT_ROOT / "intermittent_gnss_clock_drift.json").read_text(encoding="utf-8"))["rows"]
        self.assertEqual(len(rows), 4 * 4)
        example = [
            row
            for row in rows
            if row["oscillator_label"] == "tcxo_0_5_ppm" and float(row["update_interval_s"]) == 15.0
        ]
        self.assertEqual(len(example), 1)
        row = example[0]
        self.assertTrue(row["matches_manuscript_example"])
        self.assertAlmostEqual(float(row["time_error_us"]), 7.5, places=9)
        self.assertAlmostEqual(float(row["range_bias_equivalent_m"]), 2248.443435, places=6)

    def test_required_plots_and_reports_exist(self) -> None:
        required = [
            OUTPUT_ROOT / "plots" / "gnss_prior_sensitivity_localization.pdf",
            OUTPUT_ROOT / "plots" / "gnss_prior_sensitivity_synchronization.pdf",
            OUTPUT_ROOT / "plots" / "clock_prior_sensitivity_localization.pdf",
            OUTPUT_ROOT / "plots" / "clock_prior_sensitivity_synchronization.pdf",
            OUTPUT_ROOT / "plots" / "intermittent_gnss_clock_drift_bias.pdf",
            OUTPUT_ROOT / "plots" / "baseline_taxonomy_matrix.pdf",
            REPORT_ROOT / "GNSS_BASELINE_EXPLORATION_REPORT.md",
            REPORT_ROOT / "GNSS_BASELINE_EXPLORATION_REPORT.json",
            REPORT_ROOT / "GNSS_BASELINE_TASK_MATRIX.md",
            REPORT_ROOT / "GNSS_BASELINE_TASK_MATRIX.json",
        ]
        for path in required:
            self.assertTrue(path.exists(), f"missing {path}")
            self.assertGreater(path.stat().st_size, 0, f"empty {path}")

    def test_source_does_not_target_forbidden_manuscript_or_notebook_paths(self) -> None:
        source = (ROOT / "scripts" / "run_gnss_baseline_exploration.py").read_text(encoding="utf-8")
        forbidden = [
            "JCLS_Simulation.ipynb",
            "Work-In-Progress",
            "PSFrag",
            "All-Version-Archive",
            ".bib",
        ]
        for token in forbidden:
            self.assertNotIn(token, source)

    def test_clock_prior_perfect_oracle_is_not_marked_fair(self) -> None:
        rows = list(csv.DictReader((OUTPUT_ROOT / "clock_prior_sensitivity_raw.csv").read_text(encoding="utf-8").splitlines()))
        oracle_rows = [row for row in rows if row["clock_prior_level"] == "perfect_clock_oracle"]
        self.assertEqual(len(oracle_rows), 3 * 3)
        for row in oracle_rows:
            self.assertEqual(row["perfect_clock_oracle"], "True")
            self.assertEqual(row["clock_prior_sigma_ns"], "perfect_oracle")
            self.assertEqual(row["baseline_label"], "gnss_clock_aided_ntn")


if __name__ == "__main__":
    unittest.main()
