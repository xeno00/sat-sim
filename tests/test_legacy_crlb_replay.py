import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "v24_notebook_regression_outputs"
REPLAY_ROOT = OUTPUT_ROOT / "executed_legacy" / "crlb_replay"


class TestLegacyCrlbReplay(unittest.TestCase):
    def test_replay_outputs_exist_and_are_nonfinal(self) -> None:
        report = json.loads((OUTPUT_ROOT / "LEGACY_CRLB_REPLAY_REPORT.json").read_text(encoding="utf-8"))

        self.assertEqual(report["status"], "legacy_crlb_replayed_unverified_match")
        self.assertTrue(report["legacy_replay"])
        self.assertFalse(report["manuscript_ready"])
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

    def test_metadata_records_legacy_crlb_caveats(self) -> None:
        metadata = json.loads((REPLAY_ROOT / "legacy_crlb_replay_metadata.json").read_text(encoding="utf-8"))
        caveats = metadata["legacy_caveats"]

        self.assertTrue(caveats["uses_all_clock_symbolic_state"])
        self.assertFalse(caveats["v24_gauged_state"])
        self.assertTrue(caveats["removes_dependent_rows_by_qr"])
        self.assertTrue(caveats["posthoc_position_clock_slicing"])
        self.assertTrue(caveats["localization_bound_uses_inv"])
        self.assertTrue(caveats["synchronization_bound_uses_pinv"])
        self.assertTrue(caveats["sync_bound_averages_all_clock_symbols_including_reference"])
        self.assertIn("legacy_only", caveats["classification"])
        self.assertFalse(metadata["manuscript_ready"])

    def test_figure_regression_table_marks_only_crlb_replayed(self) -> None:
        table = json.loads((OUTPUT_ROOT / "FIGURE_REGRESSION_TABLE.json").read_text(encoding="utf-8"))
        status_by_figure = {
            entry["figure"]: entry
            for entry in table["target_figure_statuses"]
        }

        self.assertEqual(status_by_figure["pos_crlb_0dB_0dB.pdf"]["status"], "legacy_replayed_unverified_match")
        self.assertEqual(status_by_figure["sync_crlb_0dB_0dB.pdf"]["status"], "legacy_replayed_unverified_match")
        self.assertTrue(status_by_figure["pos_crlb_0dB_0dB.pdf"]["legacy_replay"])
        self.assertTrue(status_by_figure["sync_crlb_0dB_0dB.pdf"]["legacy_replay"])
        self.assertFalse(status_by_figure["pos_crlb_0dB_0dB.pdf"]["manuscript_ready"])
        self.assertFalse(status_by_figure["sync_crlb_0dB_0dB.pdf"]["manuscript_ready"])

        for figure in [
            "pos_vary_ues.pdf",
            "sync_vary_ues.pdf",
        ]:
            self.assertEqual(status_by_figure[figure]["status"], "static_mapped_only")

    def test_replay_script_uses_safe_output_root_and_no_work_in_progress_paths(self) -> None:
        source = (ROOT / "scripts" / "replay_legacy_crlb_figures.py").read_text(encoding="utf-8")

        self.assertIn("v24_notebook_regression_outputs", source)
        self.assertIn("executed_legacy", source)
        self.assertNotIn("Work-In-Progress", source)
        self.assertNotIn("save_workspace(", source)
        self.assertNotIn("load_workspace(", source)


if __name__ == "__main__":
    unittest.main()
