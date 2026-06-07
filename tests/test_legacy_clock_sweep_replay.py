import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "v24_notebook_regression_outputs"
CLOCK_ROOT = OUTPUT_ROOT / "executed_legacy" / "clock_sweep_replay"
FULL_CLOCK_ROOT = OUTPUT_ROOT / "executed_legacy" / "clock_sweep_replay_full"


class TestLegacyClockSweepReplay(unittest.TestCase):
    def test_smoke_replay_outputs_exist_and_are_nonfinal(self) -> None:
        report = json.loads((OUTPUT_ROOT / "LEGACY_CLOCK_SWEEP_REPLAY_REPORT.json").read_text(encoding="utf-8"))

        self.assertEqual(report["artifact_status"], "non_final_legacy_clock_sweep_replay")
        self.assertEqual(report["mode"], "smoke")
        self.assertTrue(report["legacy_replay"])
        self.assertFalse(report["manuscript_ready"])
        self.assertTrue(report["not_for_manuscript_submission"])
        self.assertFalse(report["notebook_source_modified"])
        self.assertFalse(report["full_notebook_executed"])
        self.assertFalse(report["colab_setup_executed"])
        self.assertFalse(report["workspace_pickle_executed"])
        self.assertFalse(report["manuscript_output_paths_written"])

        for relative_path in report["raw_outputs"].values():
            self.assertTrue((ROOT / relative_path).exists(), relative_path)
        for relative_path in report["plot_outputs"]:
            path = ROOT / relative_path
            self.assertTrue(path.exists(), relative_path)
            self.assertGreater(path.stat().st_size, 0)

    def test_metadata_records_legacy_caveats_and_fallbacks(self) -> None:
        metadata = json.loads((CLOCK_ROOT / "legacy_clock_sweep_metadata.json").read_text(encoding="utf-8"))
        caveats = metadata["legacy_caveats"]
        counts = metadata["counts"]

        self.assertFalse(caveats["truth_centered_initialization"])
        self.assertTrue(caveats["true_state_acceptance_gates_used"])
        self.assertTrue(caveats["lm_reverts_or_accepts_based_on_true_state_error"])
        self.assertTrue(caveats["map_reverts_based_on_true_state_error"])
        self.assertTrue(caveats["exceptions_fall_back_to_il_or_previous_state"])
        self.assertTrue(caveats["all_clock_symbolic_state"])
        self.assertTrue(caveats["v24_gauging_absent"])
        self.assertTrue(caveats["smoothing_fitting_manual_transforms_applied"])
        self.assertTrue(caveats["legacy_sync_metric_averages_all_clock_symbols"])
        self.assertIn("legacy_only", caveats["classification"])
        self.assertGreaterEqual(counts["total_fallback_events"], counts["map_global_fallback_count"])
        self.assertGreater(counts["map_global_fallback_count"], 0)

    def test_full_replay_outputs_are_distinct_and_nonfinal(self) -> None:
        report = json.loads((OUTPUT_ROOT / "LEGACY_CLOCK_SWEEP_FULL_REPLAY_REPORT.json").read_text(encoding="utf-8"))

        self.assertEqual(report["artifact_status"], "non_final_legacy_clock_sweep_full_replay")
        self.assertEqual(report["status"], "legacy_full_replayed_unverified_match")
        self.assertEqual(report["mode"], "full")
        self.assertTrue(report["full_mode_completed"])
        self.assertGreater(report["runtime_seconds"], 0.0)
        self.assertTrue(report["legacy_replay"])
        self.assertFalse(report["manuscript_ready"])
        self.assertTrue(report["not_for_manuscript_submission"])
        self.assertEqual(report["output_root"], "v24_notebook_regression_outputs\\executed_legacy\\clock_sweep_replay_full")
        self.assertNotEqual(report["output_root"], "v24_notebook_regression_outputs\\executed_legacy\\clock_sweep_replay")
        self.assertEqual(report["counts"]["row_count"], 7)
        self.assertEqual(report["num_iterations"], 25)

        metadata = json.loads((FULL_CLOCK_ROOT / "legacy_clock_sweep_metadata.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["mode"], "full")
        self.assertEqual(len(metadata["per_clock_std_results"]), 7)
        self.assertIn("replayed_artifacts", metadata["existing_artifact_comparison"])
        self.assertIn("data_ranges", metadata)
        self.assertIn("plot_axis_labels", metadata)

        for relative_path in report["raw_outputs"].values():
            self.assertTrue((ROOT / relative_path).exists(), relative_path)
        for relative_path in report["plot_outputs"]:
            path = ROOT / relative_path
            self.assertTrue(path.exists(), relative_path)
            self.assertGreater(path.stat().st_size, 0)

    def test_figure_regression_table_updates_only_clock_and_crlb_pairs(self) -> None:
        table = json.loads((OUTPUT_ROOT / "FIGURE_REGRESSION_TABLE.json").read_text(encoding="utf-8"))
        status_by_figure = {
            entry["figure"]: entry
            for entry in table["target_figure_statuses"]
        }

        for figure in ["pos_vary_clock.pdf", "sync_vary_clock.pdf"]:
            self.assertEqual(status_by_figure[figure]["status"], "legacy_full_replayed_unverified_match")
            self.assertTrue(status_by_figure[figure]["legacy_replay"])
            self.assertTrue(status_by_figure[figure]["full_legacy_replay"])
            self.assertFalse(status_by_figure[figure]["manuscript_ready"])

        for figure in ["pos_crlb_0dB_0dB.pdf", "sync_crlb_0dB_0dB.pdf"]:
            self.assertEqual(status_by_figure[figure]["status"], "legacy_replayed_unverified_match")
            self.assertTrue(status_by_figure[figure]["legacy_replay"])
            self.assertFalse(status_by_figure[figure]["manuscript_ready"])

        for figure in ["pos_vary_ues.pdf", "sync_vary_ues.pdf"]:
            self.assertEqual(status_by_figure[figure]["status"], "legacy_network_size_smoke_replayed_unverified_match")
            self.assertFalse(status_by_figure[figure]["manuscript_ready"])

    def test_replay_script_is_redirected_and_does_not_use_forbidden_paths(self) -> None:
        source = (ROOT / "scripts" / "replay_legacy_clock_sweep_figures.py").read_text(encoding="utf-8")

        self.assertIn("v24_notebook_regression_outputs", source)
        self.assertIn("clock_sweep_replay", source)
        self.assertIn("clock_sweep_replay_full", source)
        self.assertIn("legacy_clock_sweep_execution_failure", source)
        self.assertNotIn("Work-In-Progress", source)
        self.assertNotIn("save_workspace(", source)
        self.assertNotIn("load_workspace(", source)


if __name__ == "__main__":
    unittest.main()
