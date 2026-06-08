import json
import unittest
from pathlib import Path

import numpy as np

from scripts import explore_step3_covariance as cov


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs" / "step3_covariance_exploration"
REPORTS = ROOT / "outputs" / "reports"
GALLERY = ROOT / "outputs" / "gallery" / "PLOT_GALLERY.json"


class TestStep3CovarianceExploration(unittest.TestCase):
    def test_dry_run_is_sparse_only_by_default(self) -> None:
        planned = cov.main(["--dry-run"])

        self.assertEqual(planned["artifact_status"], "non_final_step3_covariance_exploration_planned_work")
        self.assertFalse(planned["will_execute"])
        self.assertEqual(
            planned["sparse_cases"],
            [
                {"num_users": 3, "num_satellites": 8},
                {"num_users": 7, "num_satellites": 8},
                {"num_users": 7, "num_satellites": 12},
            ],
        )
        self.assertEqual(planned["sparse_row_count"], 66)
        self.assertFalse(planned["run_promoted_medium"])
        self.assertFalse(planned["medium_grid_default"])
        self.assertFalse(planned["network_size_graphs_run"])
        self.assertFalse(planned["full_ladder_run"])

    def test_lane_variant_counts_are_bounded(self) -> None:
        counts = {
            lane: sum(1 for variant in cov.LANE_VARIANTS if variant.lane == lane)
            for lane in sorted({variant.lane for variant in cov.LANE_VARIANTS})
        }

        self.assertEqual(
            set(counts),
            {
                "lm_curvature",
                "residual_scaled_lm",
                "position_freeze_damping",
                "block_scaled_drift_tuning",
                "gauge_common_clock",
                "schur_reduced",
            },
        )
        self.assertTrue(all(count <= 6 for count in counts.values()))

    def test_position_freeze_variant_keeps_positions_fixed(self) -> None:
        case = cov.sparse_cases()[0]
        variant = next(item for item in cov.LANE_VARIANTS if item.name == "freeze_positions_clock_drift")

        row = cov._evaluate_case_variant(case, variant, grid="sparse")

        self.assertEqual(row["position_update_norm"], 0.0)
        self.assertEqual(row["position_ratio"], 1.0)
        self.assertTrue(row["sync_improved"])

    def test_covariance_block_dimensions_units_and_floors_are_valid(self) -> None:
        case = cov.sparse_cases()[0]
        variant = next(item for item in cov.LANE_VARIANTS if item.name == "lm_covariance_floors_ceilings")
        theta0 = cov._pack_state(case, variant)
        z_true, z_pred, jacobian = cov._measurements_and_jacobian(case, variant, theta0)
        sigma = np.full(z_true.size, variant.measurement_sigma_km)

        covariance, info = cov._covariance_from_mode(case, variant, jacobian, z_true - z_pred, sigma)

        self.assertEqual(covariance.shape, (theta0.size, theta0.size))
        self.assertTrue(np.all(np.isfinite(covariance)))
        self.assertTrue(np.allclose(covariance, covariance.T))
        self.assertGreaterEqual(info["covariance_rank"], 1)
        diag = np.diag(covariance)
        self.assertGreaterEqual(float(np.min(diag[cov._position_slice(case)])), variant.position_floor_km2)
        self.assertGreaterEqual(float(np.min(diag[cov._clock_slice(case)])), variant.clock_floor_km2)
        self.assertLessEqual(float(np.max(diag[cov._position_slice(case)])), variant.position_ceiling_km2)
        self.assertLessEqual(float(np.max(diag[cov._clock_slice(case)])), variant.clock_ceiling_km2)

    def test_common_clock_projection_reduces_common_component(self) -> None:
        case = cov.sparse_cases()[0]
        variant = next(item for item in cov.LANE_VARIANTS if item.name == "project_common_clock")

        row = cov._evaluate_case_variant(case, variant, grid="sparse")

        self.assertTrue(row["project_common_clock"])
        self.assertLessEqual(row["common_clock_update_component"], row["raw_common_clock_update_component"] + 1.0e-15)
        self.assertLess(row["common_clock_update_component"], 1.0e-12)

    def test_schur_reduced_variant_records_diagnostics(self) -> None:
        case = cov.sparse_cases()[0]
        variant = next(item for item in cov.LANE_VARIANTS if item.name == "schur_position_clock_backsolve")

        row = cov._evaluate_case_variant(case, variant, grid="sparse")

        self.assertTrue(np.isfinite(row["position_ratio"]))
        self.assertGreater(row["schur_reduced_dimension"], 0)
        self.assertGreater(row["schur_nuisance_dimension"], 0)

    def test_no_truth_state_acceptance_or_covariance(self) -> None:
        row = cov._evaluate_case_variant(cov.sparse_cases()[0], cov.LANE_VARIANTS[0], grid="sparse")

        self.assertFalse(row["truth_state_used_for_acceptance"])
        self.assertFalse(row["truth_state_used_for_covariance"])
        self.assertTrue(row["truth_state_used_for_diagnostics"])

    def test_cache_key_depends_on_case_variant_and_grid(self) -> None:
        case = cov.sparse_cases()[0]
        other_case = cov.sparse_cases()[1]
        first = cov.LANE_VARIANTS[0]
        second = cov.LANE_VARIANTS[1]

        self.assertNotEqual(cov._cache_key(case, first, "sparse"), cov._cache_key(case, second, "sparse"))
        self.assertNotEqual(cov._cache_key(case, first, "sparse"), cov._cache_key(other_case, first, "sparse"))
        self.assertNotEqual(cov._cache_key(case, first, "sparse"), cov._cache_key(case, first, "medium"))

    def test_promotion_rule_limits_to_two_variants(self) -> None:
        rows = [
            cov._evaluate_case_variant(case, variant, grid="sparse")
            for case in cov.sparse_cases()
            for variant in cov.LANE_VARIANTS
        ]
        summary = cov._summarize(rows, group_fields=("lane", "variant"))
        promoted = cov._promotion_candidates(summary)

        self.assertLessEqual(len(promoted), 2)
        for item in promoted:
            self.assertTrue(
                item["both_improved_count"] >= 2
                or (item["sync_improved_count"] >= 2 and item["max_position_ratio"] <= 1.10)
                or (item["position_improved_count"] >= 2 and item["max_sync_ratio"] <= 1.10)
            )

    def test_medium_validation_runs_only_for_promoted_variants_when_requested(self) -> None:
        payload = cov.run_exploration(run_promoted_medium=True)
        promoted = set(payload["promoted_variants"])
        medium_variants = {row["variant"] for row in payload["rows"] if row["grid"] == "medium"}

        self.assertTrue(payload["medium_validation_run"])
        self.assertEqual(medium_variants, promoted)
        self.assertLessEqual(len(medium_variants), 2)
        self.assertEqual(payload["medium_row_count"], 12 * len(promoted))

    def test_outputs_have_common_schema_and_reports(self) -> None:
        metadata_path = OUTPUT_ROOT / "metadata.json"
        if not metadata_path.exists():
            self.skipTest("Covariance exploration outputs have not been generated")
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        row = payload["rows"][0]

        for field in cov.REQUIRED_ROW_FIELDS:
            self.assertIn(field, row)
        self.assertFalse(payload["manuscript_ready"])
        self.assertFalse(payload["truth_state_used_for_acceptance"])
        self.assertFalse(payload["truth_state_used_for_covariance"])
        self.assertTrue((REPORTS / "STEP3_COVARIANCE_EXPLORATION_REPORT.md").exists())
        self.assertTrue((REPORTS / "STEP3_COVARIANCE_EXPLORATION_REPORT.json").exists())
        self.assertTrue((REPORTS / "STEP3_COVARIANCE_EXPLORATION_TASK_MATRIX.md").exists())
        self.assertTrue((REPORTS / "STEP3_COVARIANCE_EXPLORATION_TASK_MATRIX.json").exists())

    def test_gallery_includes_covariance_plots_when_rendered(self) -> None:
        if not (OUTPUT_ROOT / "plots" / "position_sync_ratio_scatter.pdf").exists():
            self.skipTest("Covariance exploration plots have not been generated")
        if not GALLERY.exists():
            self.skipTest("Plot gallery has not been rendered")
        gallery = json.loads(GALLERY.read_text(encoding="utf-8"))
        paths = {entry["source_pdf_path"] for entry in gallery["entries"]}

        self.assertIn("outputs/step3_covariance_exploration/plots/position_sync_ratio_scatter.pdf", paths)
        self.assertIn("outputs/step3_covariance_exploration/plots/runtime_by_lane.pdf", paths)


if __name__ == "__main__":
    unittest.main()
