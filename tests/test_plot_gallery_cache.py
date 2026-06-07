import json
import re
import tempfile
import unittest
from pathlib import Path

from scripts import replay_legacy_clock_sweep_figures as replay


ROOT = Path(__file__).resolve().parents[1]
GALLERY_ROOT = ROOT / "outputs" / "gallery"
CACHE_ROOT = ROOT / "v24_notebook_regression_outputs" / "cache"


class TestPlotGalleryAndClockCache(unittest.TestCase):
    def test_gallery_outputs_reference_preview_pngs(self) -> None:
        gallery = json.loads((GALLERY_ROOT / "PLOT_GALLERY.json").read_text(encoding="utf-8"))

        self.assertEqual(gallery["artifact_status"], "non_final_plot_gallery")
        self.assertGreaterEqual(gallery["entry_count"], 6)
        self.assertIn("legacy clock-sweep full", gallery["groups"])
        self.assertIn("legacy CRLB replay", gallery["groups"])
        self.assertIn("package diagnostic", gallery["groups"])
        self.assertTrue((GALLERY_ROOT / "PLOT_GALLERY.html").exists())
        self.assertTrue((GALLERY_ROOT / "PLOT_GALLERY.md").exists())

        preview_count = 0
        for entry in gallery["entries"]:
            source_pdf_path = entry["source_pdf_path"]
            if source_pdf_path is not None:
                self.assertNotIn("\\", source_pdf_path)
                self.assertNotIn("Work-In-Progress", source_pdf_path)
                self.assertNotIn("GeneratePSFrag", source_pdf_path)
            for preview in entry["preview_paths"]:
                preview_count += 1
                self.assertNotIn("\\", preview)
                path = GALLERY_ROOT / preview
                self.assertTrue(path.exists(), preview)
                self.assertGreater(path.stat().st_size, 0)
        self.assertGreater(preview_count, 0)

        html = (GALLERY_ROOT / "PLOT_GALLERY.html").read_text(encoding="utf-8")
        markdown = (GALLERY_ROOT / "PLOT_GALLERY.md").read_text(encoding="utf-8")
        self.assertNotRegex(markdown, r"!\[[^\]]+\]\([^)]*\\")
        self.assertNotRegex(html, r"<img[^>]+src=['\"][^'\"]*\\")
        self.assertIn(".png", html)
        self.assertIn(".png", markdown)
        for image_path in re.findall(r"!\[[^\]]+\]\(([^)]+)\)", markdown):
            self.assertTrue((GALLERY_ROOT / image_path).exists(), image_path)
        for image_path in re.findall(r"<img[^>]+src=['\"]([^'\"]+)['\"]", html):
            self.assertTrue((GALLERY_ROOT / image_path).exists(), image_path)

    def test_full_clock_replay_metadata_records_cache_hits(self) -> None:
        report = json.loads(
            (ROOT / "v24_notebook_regression_outputs" / "LEGACY_CLOCK_SWEEP_FULL_REPLAY_REPORT.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(report["mode"], "full")
        self.assertEqual(report["status"], "legacy_full_replayed_unverified_match")
        self.assertFalse(report["manuscript_ready"])
        self.assertEqual(report["cache"]["cache_hit_count"], 7)
        self.assertEqual(report["cache"]["cache_miss_count"], 0)
        self.assertEqual(report["cache"]["manifest_fresh_hit_count"], 7)

        summary = (ROOT / report["raw_outputs"]["summary_csv"]).read_text(encoding="utf-8")
        self.assertIn("cache_hit_count", summary)

    def test_cache_key_changes_with_config_and_notebook_hash(self) -> None:
        config = replay._mode_config("full")
        identity = replay._cache_identity(config, 1.0e-4)
        same_key = replay._cache_key(identity)

        changed_config = dict(config)
        changed_config["num_satellites"] = int(config["num_satellites"]) + 1
        changed_identity = replay._cache_identity(changed_config, 1.0e-4)
        self.assertNotEqual(same_key, replay._cache_key(changed_identity))

        changed_notebook = json.loads(json.dumps(identity))
        changed_notebook["notebook_sha256"] = "different-notebook-hash"
        self.assertNotEqual(same_key, replay._cache_key(changed_notebook))

    def test_failed_or_stale_cache_is_not_loaded(self) -> None:
        config = replay._mode_config("smoke")
        identity = replay._cache_identity(config, 1.0e-4)
        with tempfile.TemporaryDirectory(dir=ROOT / "v24_notebook_regression_outputs") as tmp:
            cache_root = Path(tmp)
            replay._write_failed_cache_entry(cache_root, identity, RuntimeError("synthetic cache failure"))
            paths = replay._cache_paths(cache_root, replay._cache_key(identity))
            paths["row"].write_text("{}", encoding="utf-8")
            events: list[dict] = []
            self.assertIsNone(replay._load_cached_row(cache_root=cache_root, identity=identity, manifest_events=events))
            self.assertEqual(events[-1]["invalidation_reason"], "cache_status_failed")

    def test_execution_failure_log_is_nonfinal(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "v24_notebook_regression_outputs") as tmp:
            output_root = Path(tmp)
            replay._write_execution_failure("full", output_root, RuntimeError("synthetic failure"))
            payload = json.loads((output_root / "legacy_clock_sweep_execution_failure.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "legacy_full_replay_failed")
            self.assertFalse(payload["manuscript_ready"])
            self.assertTrue(payload["not_for_manuscript_submission"])

    def test_cache_manifest_records_fresh_full_hits(self) -> None:
        manifest = json.loads((CACHE_ROOT / "CACHE_MANIFEST.json").read_text(encoding="utf-8"))

        self.assertEqual(manifest["cache_schema_version"], "legacy-clock-sweep-row-v1")
        self.assertEqual(manifest["fresh_hit_count"], 7)
        self.assertEqual(manifest["miss_or_stale_count"], 0)
        self.assertTrue(all(event["fresh"] for event in manifest["events"]))


if __name__ == "__main__":
    unittest.main()
