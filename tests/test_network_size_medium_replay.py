import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts import replay_legacy_network_size_figures as replay


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "outputs" / "reports"
MEDIUM_ROOT = ROOT / "outputs" / "legacy_replay" / "network_size_medium"
GALLERY = ROOT / "outputs" / "gallery" / "PLOT_GALLERY.json"


class TestNetworkSizeMediumReplay(unittest.TestCase):
    def test_medium_outputs_are_not_smoke_or_manuscript_ready(self) -> None:
        report = json.loads((REPORTS / "LEGACY_NETWORK_SIZE_REPLAY_REPORT.json").read_text(encoding="utf-8"))

        self.assertEqual(report["mode"], "medium")
        self.assertEqual(report["status"], "legacy_network_size_medium_replayed_unverified_match")
        self.assertNotIn("smoke", report["status"])
        self.assertFalse(report["manuscript_ready"])
        self.assertTrue(report["not_for_manuscript_submission"])
        self.assertEqual(report["counts"]["row_count"], 12)
        self.assertEqual(report["config"]["num_users_range"], [1, 3, 5, 7])

    def test_single_ue_rows_do_not_attempt_cooperative_jcls(self) -> None:
        with (MEDIUM_ROOT / "legacy_network_size_raw.csv").open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))

        single_user_rows = [row for row in rows if row["num_users"] == "1"]
        self.assertGreater(len(single_user_rows), 0)
        for row in single_user_rows:
            self.assertEqual(row["cooperative_jcls_attempted"], "False")
            self.assertEqual(row["single_ue_policy"], "noncooperative_clockless_baseline_only")
            self.assertIn("single_ue_noncooperative_baseline_only", row["fallbacks"])

    def test_raw_csv_has_metrics_and_fallback_counts(self) -> None:
        with (MEDIUM_ROOT / "legacy_network_size_raw.csv").open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            self.assertIn("il_position_error_m", reader.fieldnames)
            self.assertIn("lm_position_error_m", reader.fieldnames)
            self.assertIn("map_position_error_m", reader.fieldnames)
            self.assertIn("il_sync_error_s", reader.fieldnames)
            self.assertIn("lm_sync_error_s", reader.fieldnames)
            self.assertIn("map_sync_error_s", reader.fieldnames)
            self.assertIn("fallback_count", reader.fieldnames)
            rows = list(reader)
        self.assertEqual(len(rows), 12)

    def test_gallery_includes_medium_network_size_figures(self) -> None:
        gallery = json.loads(GALLERY.read_text(encoding="utf-8"))
        source_paths = {entry["source_pdf_path"] for entry in gallery["entries"]}
        self.assertIn("outputs/legacy_replay/network_size_medium/pos_vary_ues.pdf", source_paths)
        self.assertIn("outputs/legacy_replay/network_size_medium/sync_vary_ues.pdf", source_paths)

    def test_v24_figure_replacement_plan_classifies_all_targets(self) -> None:
        plan = json.loads((REPORTS / "V24_FIGURE_REPLACEMENT_PLAN.json").read_text(encoding="utf-8"))

        self.assertTrue(plan["no_figure_marked_manuscript_ready"])
        self.assertEqual(plan["manuscript_ready_count"], 0)
        self.assertEqual(len(plan["figures"]), 7)
        classes = {item["figure"]: set(item["classification"]) for item in plan["figures"]}
        self.assertIn("needs_nlos_model_design", classes["NLOS CRLB variants"])
        self.assertIn("needs_v24_clean_replacement", classes["Fig. 4 localization vs satellites"])

    def test_cache_key_changes_with_user_count_and_stale_cache_rejected(self) -> None:
        config = replay._mode_config("medium")
        identity = replay._identity(config, 3, 8)
        changed = replay._identity(config, 5, 8)
        self.assertNotEqual(replay._cache_key(identity), replay._cache_key(changed))

        with tempfile.TemporaryDirectory(dir=ROOT / "outputs" / "cache") as tmp:
            cache_root = Path(tmp)
            key = replay._cache_key(identity)
            paths = replay._cache_paths(cache_root, key)
            paths["dir"].mkdir(parents=True)
            paths["metadata"].write_text(json.dumps({"status": "partial"}), encoding="utf-8")
            paths["row"].write_text("{}", encoding="utf-8")
            events: list[dict] = []
            self.assertIsNone(replay._load_cache(cache_root, identity, events))
            self.assertEqual(events[-1]["invalidation_reason"], "cache_status_partial")


if __name__ == "__main__":
    unittest.main()
