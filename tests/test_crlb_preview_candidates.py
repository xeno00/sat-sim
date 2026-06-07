import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.prepare_v24_crlb_figure_candidate import build_crlb_figure_candidate_data
from scripts.preview_v24_crlb_figure_candidates import (
    build_finite_crlb_clock_svg,
    build_finite_crlb_peb_svg,
    build_fixed_measurement_addition_svg,
    build_preview_manifest,
    build_rank_feasibility_heatmap_svg,
    write_crlb_preview_outputs,
)


class TestV24CrlbPreviewCandidates(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = build_crlb_figure_candidate_data(base_seed=20260606)
        self.temp_dir = Path(tempfile.mkdtemp(prefix="v24_crlb_preview_test_"))

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_svg_builders_include_non_final_language(self) -> None:
        svgs = [
            build_rank_feasibility_heatmap_svg(self.payload),
            build_finite_crlb_peb_svg(self.payload),
            build_finite_crlb_clock_svg(self.payload),
            build_fixed_measurement_addition_svg(self.payload),
        ]

        for svg in svgs:
            self.assertIn("<svg", svg)
            self.assertIn("Non-final", svg)

    def test_rank_heatmap_marks_full_rank_and_unavailable_cases(self) -> None:
        svg = build_rank_feasibility_heatmap_svg(self.payload)

        self.assertIn("#d8f3dc", svg)
        self.assertIn("#fee2e2", svg)
        self.assertIn("rank / parameter", svg)

    def test_finite_crlb_preview_marks_unavailable_points(self) -> None:
        peb_svg = build_finite_crlb_peb_svg(self.payload)
        clock_svg = build_finite_crlb_clock_svg(self.payload)

        for svg in (peb_svg, clock_svg):
            self.assertIn("Crosses mark rank-deficient unavailable points", svg)
            self.assertIn("stroke=\"#b91c1c\"", svg)

    def test_manifest_is_non_final_and_references_outputs(self) -> None:
        paths = [
            self.temp_dir / "rank.svg",
            self.temp_dir / "peb.svg",
        ]
        manifest = build_preview_manifest(self.payload, paths)

        self.assertEqual(manifest["diagnostic_type"], "non_final_v24_crlb_preview_manifest")
        self.assertFalse(manifest["manuscript_figure"])
        self.assertTrue(manifest["human_review_required"])
        self.assertEqual(len(manifest["outputs"]), len(paths))
        for output in manifest["outputs"]:
            self.assertTrue(output["non_final"])
            self.assertEqual(output["kind"], "svg_preview")

    def test_write_outputs_creates_expected_preview_files(self) -> None:
        input_path = self.temp_dir / "candidate.json"
        output_dir = self.temp_dir / "preview"
        input_path.write_text(
            json.dumps(self.payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )

        manifest = write_crlb_preview_outputs(
            input_path=input_path,
            output_dir=output_dir,
            overwrite=True,
        )

        expected_names = {
            "rank_feasibility_heatmap_preview.svg",
            "finite_crlb_vs_ns_ue_peb_preview.svg",
            "finite_crlb_vs_ns_clock_preview.svg",
            "fixed_measurement_addition_preview.svg",
            "preview_manifest.json",
        }
        self.assertEqual(
            expected_names,
            {path.name for path in output_dir.iterdir()},
        )
        self.assertEqual(len(manifest["outputs"]), 4)
        self.assertIn("preview_manifest.json", manifest["manifest_path"])


if __name__ == "__main__":
    unittest.main()
