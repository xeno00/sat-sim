import csv
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs" / "c7_candidate_figures"
REPORT_ROOT = ROOT / "outputs" / "reports"
GALLERY_JSON = ROOT / "outputs" / "gallery" / "PLOT_GALLERY.json"
METADATA_JSON = OUTPUT_ROOT / "metadata.json"
REPORT_MD = REPORT_ROOT / "C7_CANDIDATE_FIGURE_VALIDATION_REPORT.md"


class C7CandidateFigureArtifactTests(unittest.TestCase):
    def test_metadata_marks_candidate_outputs_non_final(self) -> None:
        metadata = json.loads(METADATA_JSON.read_text(encoding="utf-8"))

        self.assertEqual(metadata["artifact_status"], "non_final_c7_candidate_figures")
        self.assertTrue(metadata["candidate_only"])
        self.assertTrue(metadata["non_final"])
        self.assertFalse(metadata["manuscript_ready"])
        self.assertTrue(metadata["not_for_manuscript_submission"])
        self.assertFalse(metadata["notebook_used"])
        self.assertFalse(metadata["manuscript_directories_touched"])
        self.assertTrue(metadata["human_signoff_required"])
        self.assertEqual(
            metadata["covariance_terminology"],
            "typed block-extracted, diagonal-clipped residual-scaled covariance",
        )
        self.assertEqual(metadata["baseline"], "Step B / LM-only")
        self.assertEqual(metadata["estimator_mode"], "step_c7_residual_cov_sync_safeguard")
        self.assertEqual(metadata["sync_units"], "ns in plots; km retained in raw CSV")
        self.assertEqual(metadata["clock_sweep_status"], "sparse_bounded_blocked_by_localization_instability")
        self.assertFalse(metadata["truth_state_used_for_acceptance"])
        self.assertFalse(metadata["truth_state_used_for_covariance"])
        self.assertFalse(metadata["truth_state_used_for_safeguard"])
        self.assertTrue(metadata["truth_used_only_for_offline_metrics"])

    def test_required_raw_summary_and_plot_artifacts_exist(self) -> None:
        required = [
            OUTPUT_ROOT / "raw.csv",
            OUTPUT_ROOT / "network_size_raw.csv",
            OUTPUT_ROOT / "clock_sweep_raw.csv",
            OUTPUT_ROOT / "summary.csv",
            OUTPUT_ROOT / "arrays.npz",
            OUTPUT_ROOT / "metadata.json",
            OUTPUT_ROOT / "network_size_notes.md",
            OUTPUT_ROOT / "clock_sweep_notes.md",
            REPORT_ROOT / "C7_CANDIDATE_FIGURE_TASK_MATRIX.md",
            REPORT_ROOT / "C7_CANDIDATE_FIGURE_TASK_MATRIX.json",
            REPORT_ROOT / "C7_CANDIDATE_FIGURE_VALIDATION_REPORT.md",
            REPORT_ROOT / "C7_CANDIDATE_FIGURE_VALIDATION_REPORT.json",
        ]
        plot_names = [
            "c7_network_localization_vs_satellites",
            "c7_network_synchronization_vs_satellites",
            "c7_clock_sweep_localization",
            "c7_clock_sweep_synchronization",
            "c7_fallback_annotations",
            "c7_ratio_summary",
        ]
        for name in plot_names:
            required.append(OUTPUT_ROOT / "plots" / f"{name}.pdf")
            required.append(OUTPUT_ROOT / "plots" / f"{name}.png")

        for path in required:
            self.assertTrue(path.exists(), f"missing {path}")
            self.assertGreater(path.stat().st_size, 0, f"empty {path}")

    def test_summary_records_network_success_and_clock_sweep_blocker(self) -> None:
        rows = {
            row["family"]: row
            for row in csv.DictReader((OUTPUT_ROOT / "summary.csv").read_text(encoding="utf-8").splitlines())
        }

        network = rows["network_size"]
        self.assertEqual(int(network["row_count"]), 12)
        self.assertEqual(int(network["position_improved_count"]), 12)
        self.assertEqual(int(network["sync_improved_count"]), 9)
        self.assertEqual(int(network["both_improved_count"]), 9)
        self.assertEqual(int(network["fallback_count"]), 3)
        self.assertLess(float(network["max_position_ratio"]), 1.0)
        self.assertEqual(float(network["max_sync_ratio"]), 1.0)

        clock = rows["clock_sweep"]
        self.assertEqual(int(clock["row_count"]), 4)
        self.assertEqual(int(clock["position_improved_count"]), 2)
        self.assertEqual(int(clock["sync_improved_count"]), 2)
        self.assertEqual(int(clock["both_improved_count"]), 2)
        self.assertEqual(int(clock["fallback_count"]), 2)
        self.assertGreater(float(clock["max_position_ratio"]), 1.05)
        self.assertEqual(float(clock["max_sync_ratio"]), 1.0)

    def test_raw_rows_include_baseline_c7_fallbacks_and_no_truth_flags(self) -> None:
        raw_rows = list(csv.DictReader((OUTPUT_ROOT / "raw.csv").read_text(encoding="utf-8").splitlines()))
        self.assertEqual(len(raw_rows), 16)
        for row in raw_rows:
            self.assertEqual(row["candidate"], "step_c7_residual_cov_sync_safeguard")
            self.assertEqual(row["estimator_mode"], "step_c7_residual_cov_sync_safeguard")
            self.assertIn("step_b_position_error_m", row)
            self.assertIn("c7_position_error_m", row)
            self.assertIn("step_b_sync_error_ns", row)
            self.assertIn("c7_sync_error_ns", row)
            self.assertEqual(row["truth_state_used_for_acceptance"], "False")
            self.assertEqual(row["truth_state_used_for_covariance"], "False")
            self.assertEqual(row["truth_state_used_for_safeguard"], "False")

        network_fallbacks = [
            row
            for row in raw_rows
            if row["family"] == "network_size" and row["fallback_triggered"] == "True"
        ]
        self.assertEqual(len(network_fallbacks), 3)
        self.assertEqual({row["num_users"] for row in network_fallbacks}, {"1"})
        self.assertEqual(
            {row["fallback_reason"] for row in network_fallbacks},
            {"single_user_clock_update_not_observable"},
        )

        clock_fallbacks = [
            row
            for row in raw_rows
            if row["family"] == "clock_sweep" and row["fallback_triggered"] == "True"
        ]
        self.assertEqual(len(clock_fallbacks), 2)
        self.assertEqual({row["fallback_reason"] for row in clock_fallbacks}, {"clock_update_exceeds_covariance_scale"})

    def test_gallery_contains_c7_candidate_previews(self) -> None:
        gallery = json.loads(GALLERY_JSON.read_text(encoding="utf-8"))
        entries = [
            entry
            for entry in gallery["entries"]
            if entry["group"] == "C7 candidate figure validation"
        ]
        self.assertEqual(len(entries), 6)
        for entry in entries:
            self.assertTrue(entry["source_pdf_path"].startswith("outputs/c7_candidate_figures/plots/"))
            self.assertEqual(entry["render_status"], "rendered")
            self.assertFalse(entry["manuscript_ready"])
            self.assertEqual(entry["status"], "diagnostic_output")
            self.assertGreater(len(entry["preview_paths"]), 0)
            for preview in entry["preview_paths"]:
                self.assertTrue((ROOT / "outputs" / "gallery" / preview).exists())

    def test_report_links_are_relative_and_valid(self) -> None:
        report = REPORT_MD.read_text(encoding="utf-8")
        self.assertIn("typed block-extracted, diagonal-clipped residual-scaled covariance", report)
        self.assertIn("PASS WITH CAVEAT", report)
        self.assertIn("sparse_bounded_blocked_by_localization_instability", report)

        targets = re.findall(r"\]\((\.\./c7_candidate_figures/[^)]+)\)", report)
        self.assertGreaterEqual(len(targets), 10)
        for target in targets:
            self.assertTrue((REPORT_ROOT / target).resolve().exists(), f"broken report link {target}")


if __name__ == "__main__":
    unittest.main()
