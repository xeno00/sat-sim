import csv
import json
import unittest
from pathlib import Path

import numpy as np

from jcls_sim import STEP_C7_ESTIMATOR_MODE, StepC7BlockSlices, StepC7Config
from jcls_sim.algorithm import (
    step_c7_residual_cov_sync_safeguard_refinement,
    step_c7_residual_scaled_block_covariance,
)
from jcls_sim.migration import migration_ladder_steps, step_c7_residual_cov_sync_safeguard
from scripts import run_controlled_migration_ladder as ladder


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs" / "step_c7_residual_cov_sync_safeguard"
REPORT_JSON = ROOT / "outputs" / "reports" / "STEP_C7_RESIDUAL_COV_SYNC_SAFEGUARD_REPORT.json"
REPORT_MD = ROOT / "outputs" / "reports" / "STEP_C7_RESIDUAL_COV_SYNC_SAFEGUARD_REPORT.md"
GALLERY_JSON = ROOT / "outputs" / "gallery" / "PLOT_GALLERY.json"


class StepC7EstimatorTests(unittest.TestCase):
    def test_c7_migration_step_uses_real_estimator_mode(self) -> None:
        step = step_c7_residual_cov_sync_safeguard()
        self.assertEqual(step.name, STEP_C7_ESTIMATOR_MODE)
        self.assertEqual(step.estimator_mode, STEP_C7_ESTIMATOR_MODE)
        self.assertIn(step, migration_ladder_steps())

    def test_residual_scaled_covariance_formula_and_block_clipping(self) -> None:
        jacobian = np.array(
            [
                [1.0, 0.0, 1.0, 0.0],
                [0.0, 1.0, 0.0, 1.0],
                [1.0, 1.0, 0.0, 0.0],
            ],
            dtype=float,
        )
        residual = np.array([0.2, -0.1, 0.3], dtype=float)
        sigmas = np.array([0.1, 0.1, 0.1], dtype=float)
        slices = StepC7BlockSlices(
            position=slice(0, 1),
            ue_clock=slice(1, 2),
            satellite_clock=slice(2, 3),
            clock_drift=slice(3, 4),
        )
        covariance, info = step_c7_residual_scaled_block_covariance(jacobian, residual, sigmas, slices)
        expected_scale = float(np.sum(np.square(residual / sigmas)) / max(1, residual.size - jacobian.shape[1]))
        self.assertEqual(covariance.shape, (4, 4))
        self.assertTrue(np.allclose(covariance, covariance.T))
        self.assertTrue(np.all(np.linalg.eigvalsh(covariance) >= -1e-12))
        self.assertAlmostEqual(info["residual_scale_factor"], expected_scale)
        self.assertEqual(info["covariance_shape"], [4, 4])
        self.assertFalse(info["truth_state_used_for_covariance"])
        off_diag = covariance.copy()
        np.fill_diagonal(off_diag, 0.0)
        self.assertTrue(np.allclose(off_diag, 0.0))

    def test_single_user_sync_safeguard_reverts_clock_and_drift_without_truth(self) -> None:
        state = np.zeros(5, dtype=float)
        jacobian = np.eye(5, dtype=float)
        residual = np.ones(5, dtype=float)
        sigmas = np.ones(5, dtype=float)
        slices = StepC7BlockSlices(
            position=slice(0, 2),
            ue_clock=slice(2, 3),
            satellite_clock=slice(3, 4),
            clock_drift=slice(4, 5),
        )
        result = step_c7_residual_cov_sync_safeguard_refinement(
            state,
            jacobian,
            residual,
            sigmas,
            slices,
            num_users=1,
            config=StepC7Config(),
        )
        self.assertTrue(result.diagnostics["fallback_event"])
        self.assertEqual(result.diagnostics["fallback_reason"], "single_user_clock_update_not_observable")
        self.assertEqual(result.theta[2], 0.0)
        self.assertEqual(result.theta[3], 0.0)
        self.assertEqual(result.theta[4], 0.0)
        self.assertFalse(result.diagnostics["truth_state_used_for_acceptance"])
        self.assertFalse(result.diagnostics["truth_state_used_for_covariance"])
        self.assertFalse(result.diagnostics["truth_state_used_for_safeguard"])

    def test_ladder_dispatch_has_c7_path(self) -> None:
        self.assertEqual(ladder.STEP_C7_NAME, STEP_C7_ESTIMATOR_MODE)
        options = ladder.LadderRunOptions(steps=(STEP_C7_ESTIMATOR_MODE,), tiny_only=True, max_rows=1)
        planned = ladder._planned_work(options)
        self.assertEqual(planned[0]["step"], STEP_C7_ESTIMATOR_MODE)


class StepC7OutputTests(unittest.TestCase):
    def test_validation_reproduces_audit_level_behavior(self) -> None:
        with (OUTPUT_ROOT / "summary.csv").open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        main = next(row for row in rows if row["candidate"] == STEP_C7_ESTIMATOR_MODE)
        self.assertEqual(int(main["both_improved_count"]), 9)
        self.assertEqual(int(main["position_improved_count"]), 12)
        self.assertEqual(int(main["sync_improved_count"]), 9)
        self.assertEqual(int(main["fallback_count"]), 3)
        self.assertAlmostEqual(float(main["mean_position_ratio"]), 0.054160465424072914)
        self.assertAlmostEqual(float(main["max_position_ratio"]), 0.14448710044194635)
        self.assertAlmostEqual(float(main["mean_sync_ratio"]), 0.38561149595048044)
        self.assertAlmostEqual(float(main["max_sync_ratio"]), 1.0)

    def test_report_is_human_readable_and_nonfinal(self) -> None:
        payload = json.loads(REPORT_JSON.read_text(encoding="utf-8"))
        text = REPORT_MD.read_text(encoding="utf-8")
        self.assertEqual(payload["estimator_mode"], STEP_C7_ESTIMATOR_MODE)
        self.assertTrue(payload["not_for_manuscript_submission"])
        self.assertTrue(payload["ready_for_human_graph_review"])
        self.assertIn("Executive Summary", text)
        self.assertIn("No-Truth-Leak Statement", text)
        self.assertIn("Output Links", text)
        self.assertIn("outputs/step_c7_residual_cov_sync_safeguard/raw.csv", text)

    def test_raw_rows_have_no_truth_leak_and_single_user_fallbacks(self) -> None:
        with (OUTPUT_ROOT / "raw.csv").open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        main_rows = [row for row in rows if row["candidate"] == STEP_C7_ESTIMATOR_MODE]
        self.assertEqual(len(main_rows), 12)
        self.assertTrue(all(row["truth_state_used_for_acceptance"] == "False" for row in main_rows))
        self.assertTrue(all(row["truth_state_used_for_covariance"] == "False" for row in main_rows))
        self.assertTrue(all(row["truth_state_used_for_safeguard"] == "False" for row in main_rows))
        fallback_rows = [row for row in main_rows if row["fallback_triggered"] == "True"]
        self.assertEqual(len(fallback_rows), 3)
        self.assertTrue(all(row["fallback_reason"] == "single_user_clock_update_not_observable" for row in fallback_rows))

    def test_gallery_includes_c7_plots(self) -> None:
        gallery = json.loads(GALLERY_JSON.read_text(encoding="utf-8"))
        paths = {entry["source_pdf_path"] for entry in gallery["entries"]}
        self.assertIn("outputs/step_c7_residual_cov_sync_safeguard/plots/localization_error_vs_satellites.pdf", paths)
        self.assertIn("outputs/step_c7_residual_cov_sync_safeguard/plots/sync_ratio_heatmap.pdf", paths)


if __name__ == "__main__":
    unittest.main()
