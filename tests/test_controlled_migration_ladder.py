import json
import unittest
from pathlib import Path

from jcls_sim.migration import legacy_staged_compatible_step, step_a_no_display_smoothing, step_diff


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "outputs" / "reports"
LADDER = ROOT / "outputs" / "migration_ladder"
BASELINE = ROOT / "outputs" / "migration_baseline" / "legacy_behavior_freeze"
GALLERY = ROOT / "outputs" / "gallery" / "PLOT_GALLERY.json"


class TestControlledMigrationLadder(unittest.TestCase):
    def test_baseline_freeze_exists_and_is_healthy(self) -> None:
        report = json.loads((BASELINE / "baseline_health_summary.json").read_text(encoding="utf-8"))

        self.assertFalse(report["manuscript_ready"])
        self.assertEqual(report["baseline_health"]["status"], "healthy")
        self.assertGreater(report["baseline_health"]["position_improvement_count"], 0)
        self.assertGreater(report["baseline_health"]["sync_improvement_count"], 0)
        self.assertEqual(report["baseline_health"]["failed_rows"], 0)

    def test_step_a_changes_only_display_transform(self) -> None:
        diff = step_diff(legacy_staged_compatible_step(), step_a_no_display_smoothing())

        self.assertEqual(diff, {"display_transform_mode": ("legacy_replay_display", "raw_metrics_no_smoothing")})

    def test_ladder_report_has_wrapper_and_step_a_tiny_medium(self) -> None:
        report = json.loads((REPORTS / "CONTROLLED_MIGRATION_LADDER.json").read_text(encoding="utf-8"))

        self.assertFalse(report["manuscript_ready"])
        self.assertIsNone(report["first_degraded_step"])
        self.assertFalse(report["stop_rule_triggered"])
        names = {(entry["step"]["name"], entry["grid"]) for entry in report["steps"]}
        self.assertIn(("legacy_staged_compatible", "tiny"), names)
        self.assertIn(("legacy_staged_compatible", "medium"), names)
        self.assertIn(("step_a_no_display_smoothing", "tiny"), names)
        self.assertIn(("step_a_no_display_smoothing", "medium"), names)
        self.assertTrue(all(entry["health"]["status"] == "healthy" for entry in report["steps"]))

    def test_each_step_grid_has_required_outputs(self) -> None:
        for step in ["legacy_staged_compatible", "step_a_no_display_smoothing"]:
            for grid in ["tiny", "medium"]:
                root = LADDER / step / grid
                for name in [
                    "pos_vary_ues.pdf",
                    "sync_vary_ues.pdf",
                    "migration_raw.csv",
                    "migration_summary.csv",
                    "migration_arrays.npz",
                    "migration_step_metadata.json",
                    "migration_step_metadata.md",
                ]:
                    self.assertTrue((root / name).exists(), f"{root / name}")

    def test_gallery_includes_migration_ladder_graphs(self) -> None:
        gallery = json.loads(GALLERY.read_text(encoding="utf-8"))
        paths = {entry["source_pdf_path"] for entry in gallery["entries"]}

        self.assertIn("outputs/migration_ladder/legacy_staged_compatible/medium/pos_vary_ues.pdf", paths)
        self.assertIn("outputs/migration_ladder/step_a_no_display_smoothing/medium/sync_vary_ues.pdf", paths)

    def test_cache_key_changes_with_migration_step(self) -> None:
        wrapper = json.loads(
            (LADDER / "legacy_staged_compatible" / "medium" / "migration_step_metadata.json").read_text(encoding="utf-8")
        )
        step_a = json.loads(
            (LADDER / "step_a_no_display_smoothing" / "medium" / "migration_step_metadata.json").read_text(encoding="utf-8")
        )

        self.assertNotEqual(wrapper["cache"]["cache_key"], step_a["cache"]["cache_key"])

    def test_single_ue_never_attempts_cooperative_jcls_in_ladder(self) -> None:
        raw = (LADDER / "step_a_no_display_smoothing" / "medium" / "migration_raw.csv").read_text(encoding="utf-8")

        single_user_lines = [line for line in raw.splitlines() if line.startswith("1,")]
        self.assertGreater(len(single_user_lines), 0)
        for line in single_user_lines:
            self.assertIn("False", line)
            self.assertIn("noncooperative_clockless_baseline_only", line)


if __name__ == "__main__":
    unittest.main()
