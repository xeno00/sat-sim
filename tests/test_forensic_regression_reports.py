import json
import unittest
from pathlib import Path


class TestForensicRegressionReports(unittest.TestCase):
    required = [
        "TASK_MATRIX",
        "SPRINT_COMPLETION_CHECKLIST",
        "MANUSCRIPT_ALGORITHM_MAP",
        "NOTEBOOK_FORENSICS_REPORT",
        "MANUSCRIPT_NOTEBOOK_CROSSWALK",
        "ORDERED_LINK_CONVENTION_AUDIT",
        "UNIT_CLOCK_REPRESENTATION_AUDIT",
        "UNITS_NOISE_COVARIANCE_REPORT",
        "GAUGE_AB_TEST_REPORT",
        "BASELINE_SEMANTICS_REPORT",
        "FIGURE_REGRESSION_TABLE",
        "PLOT_GALLERY",
        "RED_TEAM_REPORT",
        "FORENSIC_REGRESSION_SPRINT_REPORT",
    ]

    def test_required_forensic_reports_exist_and_parse(self) -> None:
        root = Path("v24_notebook_regression_outputs")
        for stem in self.required:
            with self.subTest(stem=stem):
                self.assertTrue((root / f"{stem}.md").exists())
                self.assertTrue((root / f"{stem}.json").exists())
                json.loads((root / f"{stem}.json").read_text(encoding="utf-8"))

    def test_crosswalk_contains_core_steps_and_blocking_audits(self) -> None:
        root = Path("v24_notebook_regression_outputs")
        crosswalk = (root / "MANUSCRIPT_NOTEBOOK_CROSSWALK.md").read_text(encoding="utf-8")
        ordered = json.loads((root / "ORDERED_LINK_CONVENTION_AUDIT.json").read_text(encoding="utf-8"))
        units = json.loads((root / "UNIT_CLOCK_REPRESENTATION_AUDIT.json").read_text(encoding="utf-8"))

        self.assertIn("Step 1", crosswalk)
        self.assertIn("Step 2", crosswalk)
        self.assertIn("Step 3", crosswalk)
        self.assertTrue(ordered["blocking"])
        self.assertTrue(units["blocking"])

    def test_plot_gallery_includes_human_review_artifacts(self) -> None:
        gallery = json.loads(Path("v24_notebook_regression_outputs/PLOT_GALLERY.json").read_text(encoding="utf-8"))
        paths = {row["path"] for row in gallery["artifacts"]}

        self.assertTrue(any("v24_human_review_outputs" in path for path in paths))


if __name__ == "__main__":
    unittest.main()
