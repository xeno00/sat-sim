import csv
import json
import re
import unittest
from pathlib import Path

from scripts import run_c7_manuscript_figure_recreation as runner


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs" / "c7_manuscript_figure_recreation"
REPORT_ROOT = ROOT / "outputs" / "reports"
GALLERY_JSON = ROOT / "outputs" / "gallery" / "PLOT_GALLERY.json"


class C7ManuscriptFigureRecreationTests(unittest.TestCase):
    def test_default_plan_is_bounded_and_matches_requested_families(self) -> None:
        plans = runner.build_plan()
        self.assertEqual(len(plans), 56)
        self.assertEqual(len([plan for plan in plans if plan.family == "network_size"]), 52)
        self.assertEqual(len([plan for plan in plans if plan.family == "clock_sweep"]), 4)
        self.assertEqual({plan.num_users for plan in plans if plan.family == "network_size"}, {1, 3, 5, 7})
        self.assertEqual({plan.num_satellites for plan in plans if plan.family == "network_size"}, set(range(3, 16)))
        self.assertEqual(
            {plan.clock_std_ns for plan in plans if plan.family == "clock_sweep"},
            {1.0e5, 1.0e3, 1.0e1, 1.0e-1},
        )

    def test_provenance_records_source_figure_conventions(self) -> None:
        provenance = json.loads((REPORT_ROOT / "C7_MANUSCRIPT_FIGURE_PROVENANCE_AUDIT.json").read_text(encoding="utf-8"))
        self.assertFalse(provenance["notebook_used_for_execution"])
        self.assertEqual(provenance["notebook_source_inspected"], "JCLS_Simulation.ipynb")
        self.assertEqual(provenance["figure_findings"]["fig4_pos_vary_ues"]["x_values"], "range(3, 15+1)")
        self.assertEqual(provenance["figure_findings"]["fig6_pos_vary_clock"]["num_users"], 3)
        self.assertEqual(provenance["figure_findings"]["fig6_pos_vary_clock"]["num_satellites"], 10)
        self.assertIn("np.logspace(-4, -10, 7)", provenance["figure_findings"]["fig7_sync_vary_clock"]["x_values"])

    def test_metadata_and_status_are_non_final_and_resumable(self) -> None:
        metadata = json.loads((OUTPUT_ROOT / "metadata.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["artifact_status"], "non_final_c7_manuscript_figure_recreation")
        self.assertTrue(metadata["candidate_only"])
        self.assertTrue(metadata["non_final"])
        self.assertFalse(metadata["manuscript_ready"])
        self.assertTrue(metadata["not_for_manuscript_submission"])
        self.assertTrue(metadata["resume_default"])
        self.assertEqual(metadata["planned_row_count"], 56)
        self.assertEqual(metadata["completed_cache_count"], 56)
        self.assertEqual(metadata["failed_row_count"], 0)
        self.assertEqual(metadata["clock_sweep_status"], "candidate_failed_or_diagnostic_only")
        self.assertEqual(
            metadata["covariance_terminology"],
            "typed block-extracted, diagonal-clipped residual-scaled covariance",
        )
        self.assertFalse(metadata["truth_state_used_for_acceptance"])
        self.assertFalse(metadata["truth_state_used_for_covariance"])
        self.assertTrue(metadata["truth_used_only_for_offline_metrics"])

        run_status = json.loads((OUTPUT_ROOT / "RUN_STATUS.json").read_text(encoding="utf-8"))
        self.assertEqual(run_status["status"], "complete")
        self.assertEqual(run_status["planned_row_count"], 56)

    def test_cache_manifest_and_row_status_exist(self) -> None:
        manifest = json.loads((OUTPUT_ROOT / "CACHE_MANIFEST.json").read_text(encoding="utf-8"))
        self.assertEqual(len(manifest["entries"]), 56)
        self.assertEqual({entry["status"] for entry in manifest["entries"]}, {"complete"})
        self.assertTrue((OUTPUT_ROOT / "CACHE_MANIFEST.md").exists())
        self.assertTrue((OUTPUT_ROOT / "ROW_STATUS.jsonl").exists())
        status_lines = [
            json.loads(line)
            for line in (OUTPUT_ROOT / "ROW_STATUS.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertTrue(any(line["status"] in {"complete", "cache_hit"} for line in status_lines))

    def test_single_ue_rows_are_not_cooperative_jcls(self) -> None:
        raw_rows = list(csv.DictReader((OUTPUT_ROOT / "raw.csv").read_text(encoding="utf-8").splitlines()))
        network_single_ue = [
            row
            for row in raw_rows
            if row["family"] == "network_size" and row["num_users"] == "1"
        ]
        self.assertGreater(len(network_single_ue), 0)
        self.assertEqual({row["baseline_id"] for row in network_single_ue}, {"without_cooperation"})

        network_coop = [
            row
            for row in raw_rows
            if row["family"] == "network_size" and row["num_users"] in {"3", "5", "7"}
        ]
        self.assertEqual({row["baseline_id"] for row in network_coop}, {"coarse_jcls", "refined_jcls"})

    def test_stage_columns_and_clock_sweep_failure_are_recorded(self) -> None:
        summary_rows = list(csv.DictReader((OUTPUT_ROOT / "summary.csv").read_text(encoding="utf-8").splitlines()))
        families = {row["family"] for row in summary_rows}
        self.assertEqual(families, {"network_size", "clock_sweep"})
        self.assertEqual({row["metric"] for row in summary_rows}, {"position_error_m", "sync_error_ns"})

        clock_position = [
            row
            for row in summary_rows
            if row["family"] == "clock_sweep" and row["metric"] == "position_error_m"
        ]
        self.assertTrue(any(row["baseline_id"] == "refined_jcls" for row in clock_position))
        high_clock_refined = [
            row
            for row in clock_position
            if row["baseline_id"] == "refined_jcls" and float(row["x_value"]) == 1.0e5
        ][0]
        high_clock_coarse = [
            row
            for row in clock_position
            if row["baseline_id"] == "coarse_jcls" and float(row["x_value"]) == 1.0e5
        ][0]
        self.assertGreater(float(high_clock_refined["mean"]), 1.05 * float(high_clock_coarse["mean"]))

    def test_plots_reports_and_gallery_entries_exist(self) -> None:
        for stem in (
            "fig4_c7_localization_vs_satellites",
            "fig5_c7_synchronization_vs_satellites",
            "fig6_c7_localization_vs_clock_std",
            "fig7_c7_synchronization_vs_clock_std",
        ):
            for suffix in (".pdf", ".png"):
                path = OUTPUT_ROOT / "plots" / f"{stem}{suffix}"
                self.assertTrue(path.exists(), f"missing {path}")
                self.assertGreater(path.stat().st_size, 0)

        report = (REPORT_ROOT / "C7_MANUSCRIPT_FIGURE_RECREATION_REPORT.md").read_text(encoding="utf-8")
        self.assertIn("PASS WITH CAVEAT", report)
        self.assertIn("candidate_failed_or_diagnostic_only", report)
        targets = re.findall(r"\]\((\.\./c7_manuscript_figure_recreation/[^)]+)\)", report)
        self.assertGreaterEqual(len(targets), 8)
        for target in targets:
            self.assertTrue((REPORT_ROOT / target).resolve().exists(), f"broken report link {target}")

        gallery = json.loads(GALLERY_JSON.read_text(encoding="utf-8"))
        entries = [
            entry
            for entry in gallery["entries"]
            if entry["group"] == "C7 manuscript figure recreation"
        ]
        self.assertEqual(len(entries), 4)
        for entry in entries:
            self.assertFalse(entry["manuscript_ready"])
            self.assertEqual(entry["render_status"], "rendered")


if __name__ == "__main__":
    unittest.main()
