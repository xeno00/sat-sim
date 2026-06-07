import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"
REPORTS = OUTPUTS / "reports"
GALLERY = OUTPUTS / "gallery"


class TestCanonicalGraphPackage(unittest.TestCase):
    def test_required_reports_and_index_exist(self) -> None:
        required = [
            OUTPUTS / "OUTPUT_INDEX.md",
            OUTPUTS / "OUTPUT_INDEX.json",
            GALLERY / "PLOT_GALLERY.md",
            GALLERY / "PLOT_GALLERY.html",
            GALLERY / "PLOT_GALLERY.json",
            REPORTS / "CURRENT_GRAPH_STATUS.md",
            REPORTS / "CURRENT_GRAPH_STATUS.json",
            REPORTS / "CRLB_LOS_REPLAY_REPORT.md",
            REPORTS / "CRLB_LOS_REPLAY_REPORT.json",
            REPORTS / "CRLB_NLOS_REPORT.md",
            REPORTS / "CRLB_NLOS_REPORT.json",
            REPORTS / "LEGACY_NETWORK_SIZE_REPLAY_REPORT.md",
            REPORTS / "LEGACY_NETWORK_SIZE_REPLAY_REPORT.json",
            OUTPUTS / "cache" / "CACHE_MANIFEST.md",
            OUTPUTS / "cache" / "CACHE_MANIFEST.json",
        ]
        for path in required:
            self.assertTrue(path.exists(), str(path))
            self.assertGreater(path.stat().st_size, 0, str(path))

    def test_los_crlb_and_network_outputs_are_nonfinal(self) -> None:
        los = json.loads((REPORTS / "CRLB_LOS_REPLAY_REPORT.json").read_text(encoding="utf-8"))
        nlos = json.loads((REPORTS / "CRLB_NLOS_REPORT.json").read_text(encoding="utf-8"))
        network = json.loads((REPORTS / "LEGACY_NETWORK_SIZE_REPLAY_REPORT.json").read_text(encoding="utf-8"))

        self.assertFalse(los["manuscript_ready"])
        self.assertEqual(nlos["status"], "nlos_crlb_not_generated")
        self.assertFalse(nlos["manuscript_ready"])
        self.assertTrue(network["legacy_replay"])
        self.assertFalse(network["manuscript_ready"])
        self.assertTrue(network["not_for_manuscript_submission"])

        for rel_path in los["plot_outputs"] + network["plot_outputs"]:
            self.assertTrue((ROOT / rel_path).exists(), rel_path)

    def test_current_status_marks_suspect_package_native_graphs(self) -> None:
        status = json.loads((REPORTS / "CURRENT_GRAPH_STATUS.json").read_text(encoding="utf-8"))
        self.assertIn("none are manuscript-ready", status["overall"])
        suspect_paths = {entry["path"] for entry in status["suspect_graphs"]}
        self.assertIn("v24_human_review_outputs", suspect_paths)
        self.assertIn("v24_figure_outputs", suspect_paths)
        self.assertGreaterEqual(len(status["current_best_graphs"]), 4)

    def test_output_index_links_current_graph_families(self) -> None:
        index = json.loads((OUTPUTS / "OUTPUT_INDEX.json").read_text(encoding="utf-8"))
        folder_paths = {entry["path"] for entry in index["folders"]}
        for expected in [
            "outputs/gallery",
            "outputs/legacy_replay",
            "outputs/package_diagnostic",
            "outputs/manuscript_candidate",
            "outputs/human_review",
            "outputs/cache",
            "outputs/reports",
        ]:
            self.assertIn(expected, folder_paths)
        self.assertTrue(any("crlb_los" in graph["path"] for graph in index["current_best_graphs"]))
        self.assertTrue(any("clock_sweep_full" in graph["path"] for graph in index["current_best_graphs"]))

    def test_markdown_links_are_url_style_and_resolve_when_local(self) -> None:
        markdown_files = [
            OUTPUTS / "OUTPUT_INDEX.md",
            GALLERY / "PLOT_GALLERY.md",
            REPORTS / "CURRENT_GRAPH_STATUS.md",
            REPORTS / "CRLB_LOS_REPLAY_REPORT.md",
            REPORTS / "CRLB_NLOS_REPORT.md",
            REPORTS / "LEGACY_NETWORK_SIZE_REPLAY_REPORT.md",
            OUTPUTS / "cache" / "CACHE_MANIFEST.md",
        ]
        for path in markdown_files:
            text = path.read_text(encoding="utf-8")
            self.assertNotRegex(text, r"\]\([^)]*\\", str(path))
            for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
                if target.startswith(("http://", "https://", "mailto:")):
                    continue
                local = (path.parent / target).resolve()
                self.assertTrue(local.exists(), f"{path}: {target}")

    def test_gallery_previews_cover_rendered_pdf_entries(self) -> None:
        gallery = json.loads((GALLERY / "PLOT_GALLERY.json").read_text(encoding="utf-8"))
        rendered_entries = [entry for entry in gallery["entries"] if entry["render_status"] == "rendered"]
        self.assertGreater(len(rendered_entries), 0)
        for entry in rendered_entries:
            self.assertGreater(len(entry["preview_paths"]), 0, entry["figure_name"])
            for preview in entry["preview_paths"]:
                self.assertTrue((GALLERY / preview).exists(), preview)


if __name__ == "__main__":
    unittest.main()
