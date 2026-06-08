import json
import unittest
from pathlib import Path

import numpy as np

from scripts import explore_step3_near_winner_sparse as sparse


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs" / "step3_near_winner_sparse"
REPORTS = ROOT / "outputs" / "reports"
GALLERY = ROOT / "outputs" / "gallery" / "PLOT_GALLERY.json"


class TestStep3NearWinnerSparse(unittest.TestCase):
    def test_dry_run_is_sparse_only_by_default(self) -> None:
        planned = sparse.main(["--dry-run"])

        self.assertEqual(planned["artifact_status"], "non_final_step3_near_winner_sparse_planned_work")
        self.assertEqual(planned["sparse_cases"], [{"num_users": 3, "num_satellites": 8}, {"num_users": 7, "num_satellites": 8}, {"num_users": 7, "num_satellites": 12}])
        self.assertEqual(planned["sparse_row_count"], 24)
        self.assertFalse(planned["run_promoted_medium"])
        self.assertFalse(planned["network_size_graphs_run"])
        self.assertFalse(planned["full_ladder_run"])
        self.assertFalse(planned["medium_grid_default"])

    def test_variant_list_is_near_winner_family(self) -> None:
        names = [variant.name for variant in sparse.VARIANTS]

        self.assertEqual(
            names,
            [
                "block_scaled_drift_base",
                "block_scaled_drift_common_clock_projected",
                "block_scaled_drift_blockwise_update_clip",
                "block_scaled_drift_strong_clock_prior",
                "block_scaled_drift_loose_clock_prior",
                "block_scaled_no_drift_common_clock_projected",
                "schur_nuisance_clock_reduced_block_scaled",
                "clock_only_step3_after_step_b",
            ],
        )
        self.assertTrue(all("nis" not in name and "huber" not in name for name in names))

    def test_clock_only_step3_freezes_positions(self) -> None:
        case = sparse.sparse_cases()[0]
        variant = next(item for item in sparse.VARIANTS if item.name == "clock_only_step3_after_step_b")

        row = sparse._evaluate_case_variant(case, variant, grid="sparse")

        self.assertEqual(row["position_update_norm"], 0.0)
        self.assertEqual(row["position_ratio"], 1.0)
        self.assertTrue(row["sync_improved"])

    def test_common_clock_projection_reduces_common_component(self) -> None:
        case = sparse.sparse_cases()[0]
        variant = next(item for item in sparse.VARIANTS if item.name == "block_scaled_drift_common_clock_projected")

        row = sparse._evaluate_case_variant(case, variant, grid="sparse")

        self.assertTrue(row["project_common_clock"])
        self.assertLessEqual(row["common_clock_update_component"], row["raw_common_clock_update_component"] + 1.0e-15)

    def test_blockwise_clipping_is_recorded(self) -> None:
        case = sparse.sparse_cases()[0]
        variant = next(item for item in sparse.VARIANTS if item.name == "block_scaled_drift_blockwise_update_clip")

        row = sparse._evaluate_case_variant(case, variant, grid="sparse")

        self.assertTrue(row["blockwise_clipping_enabled"])
        self.assertIn("position_clip_scale", row)
        self.assertIn("ue_clock_clip_scale", row)
        self.assertIn("satellite_clock_clip_scale", row)
        self.assertIn("clock_drift_clip_scale", row)

    def test_no_truth_state_acceptance_or_covariance(self) -> None:
        row = sparse._evaluate_case_variant(sparse.sparse_cases()[0], sparse.VARIANTS[0], grid="sparse")

        self.assertFalse(row["truth_state_used_for_acceptance"])
        self.assertFalse(row["truth_state_used_for_covariance"])
        self.assertTrue(row["truth_state_used_for_diagnostics"])

    def test_promotion_rule_limits_to_two_variants(self) -> None:
        rows = [sparse._evaluate_case_variant(case, variant, grid="sparse") for case in sparse.sparse_cases() for variant in sparse.VARIANTS]
        summary = sparse._variant_summary(rows)
        promoted = sparse._promotion_candidates(summary)

        self.assertLessEqual(len(promoted), 2)
        for item in promoted:
            self.assertTrue(
                item["both_improved_count"] >= 2
                or (item["sync_improved_count"] >= 2 and item["max_position_ratio"] <= 1.10)
                or (item["position_improved_count"] >= 2 and item["max_sync_ratio"] <= 1.10)
            )

    def test_medium_validation_runs_only_for_promoted_variants_when_requested(self) -> None:
        payload = sparse.run_exploration(run_promoted_medium=True)
        promoted = set(payload["promoted_variants"])
        medium_variants = {row["variant"] for row in payload["rows"] if row["grid"] == "medium"}

        self.assertTrue(payload["medium_validation_run"])
        self.assertEqual(medium_variants, promoted)
        self.assertLessEqual(len(medium_variants), 2)
        self.assertEqual(payload["medium_row_count"], 12 * len(promoted))

    def test_generated_outputs_have_required_schema(self) -> None:
        metadata_path = OUTPUT_ROOT / "metadata.json"
        if not metadata_path.exists():
            self.skipTest("Near-winner sparse outputs have not been generated")
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        row = payload["rows"][0]

        self.assertFalse(payload["manuscript_ready"])
        self.assertFalse(payload["truth_state_used_for_acceptance"])
        self.assertFalse(payload["truth_state_used_for_covariance"])
        self.assertIn("step_b_position_error_m", row)
        self.assertIn("step3_position_error_m", row)
        self.assertIn("position_ratio", row)
        self.assertIn("sync_ratio", row)
        self.assertIn("common_clock_update_component", row)
        self.assertIn("cache_status", row)
        self.assertTrue((REPORTS / "STEP3_NEAR_WINNER_SPARSE_REPORT.md").exists())
        self.assertTrue((REPORTS / "STEP3_NEAR_WINNER_SPARSE_REPORT.json").exists())

    def test_schur_reduced_solve_records_diagnostics(self) -> None:
        case = sparse.sparse_cases()[0]
        variant = next(item for item in sparse.VARIANTS if item.name == "schur_nuisance_clock_reduced_block_scaled")

        row = sparse._evaluate_case_variant(case, variant, grid="sparse")

        self.assertTrue(np.isfinite(row["position_ratio"]))
        self.assertGreater(row["schur_reduced_dimension"], 0)
        self.assertGreater(row["schur_nuisance_dimension"], 0)

    def test_gallery_includes_sparse_plots_when_rendered(self) -> None:
        if not (OUTPUT_ROOT / "plots" / "position_sync_ratio_scatter.pdf").exists():
            self.skipTest("Near-winner sparse plots have not been generated")
        if not GALLERY.exists():
            self.skipTest("Plot gallery has not been rendered")
        gallery = json.loads(GALLERY.read_text(encoding="utf-8"))
        paths = {entry["source_pdf_path"] for entry in gallery["entries"]}

        self.assertIn("outputs/step3_near_winner_sparse/plots/position_sync_ratio_scatter.pdf", paths)
        self.assertIn("outputs/step3_near_winner_sparse/plots/sync_ratio_heatmap.pdf", paths)


if __name__ == "__main__":
    unittest.main()
