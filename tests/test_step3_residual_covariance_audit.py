import json
import unittest
from pathlib import Path

from scripts import audit_step3_residual_covariance as audit


ROOT = Path(__file__).resolve().parents[1]
FAILURE_ROOT = ROOT / "outputs" / "step3_residual_cov_failure_audit"
ROBUST_ROOT = ROOT / "outputs" / "step3_residual_cov_robust_candidates"
REPORTS = ROOT / "outputs" / "reports"
GALLERY = ROOT / "outputs" / "gallery" / "PLOT_GALLERY.json"


class TestStep3ResidualCovarianceAudit(unittest.TestCase):
    def test_dry_run_is_narrow_and_medium_only(self) -> None:
        planned = audit.main(["--dry-run"])

        self.assertEqual(planned["artifact_status"], "non_final_step3_residual_cov_audit_planned_work")
        self.assertFalse(planned["will_execute"])
        self.assertEqual(
            planned["target_variants"],
            ["block_diag_residual_scaled_covariance", "full_residual_scaled_covariance"],
        )
        self.assertEqual(
            planned["candidates"],
            [
                "residual_scaled_block_diag_base",
                "residual_scaled_block_diag_with_sync_safeguard",
                "residual_scaled_block_diag_clock_only_fallback",
                "residual_scaled_block_diag_position_damped",
            ],
        )
        self.assertEqual(len(planned["medium_cases"]), 12)
        self.assertFalse(planned["broad_exploration_rerun"])
        self.assertFalse(planned["full_ladder_run"])
        self.assertFalse(planned["notebook_run"])
        self.assertFalse(planned["manuscript_figures_generated"])

    def test_failure_rows_are_identified(self) -> None:
        rows = audit._target_medium_rows()
        payload = audit._failure_audit(rows)
        sync_worse = [
            row for row in payload["failure_rows"]
            if row["flags"]["sync_worse_gt_5_percent"]
        ]

        self.assertEqual(payload["row_count"], 24)
        self.assertGreaterEqual(payload["failure_count"], 6)
        self.assertEqual(len(sync_worse), 6)
        self.assertTrue(all(row["num_users"] == 1 for row in sync_worse))
        self.assertTrue(all(row["flags"]["objective_decreases_but_metric_worsens"] for row in sync_worse))

    def test_block_diagonal_and_full_comparison_exists(self) -> None:
        comparison = audit._compare_target_variants(audit._target_medium_rows())

        self.assertEqual(comparison["row_count"], 12)
        self.assertTrue(comparison["effectively_identical"])
        self.assertFalse(comparison["full_cross_covariance_used"])
        self.assertEqual(comparison["preferred_variant"], "block_diag_residual_scaled_covariance")

    def test_robust_candidate_validation_and_fallbacks(self) -> None:
        payload = audit.run_audit_and_candidates()
        best = payload["best_candidate"]
        rows = payload["rows"]

        self.assertEqual(payload["row_count"], 48)
        self.assertEqual(best["candidate"], "residual_scaled_block_diag_with_sync_safeguard")
        self.assertLessEqual(best["max_position_ratio"], 1.05)
        self.assertLessEqual(best["max_sync_ratio"], 1.05)
        self.assertEqual(best["fallback_count"], 3)
        self.assertTrue(best["passes_strict_promotion_criterion"])
        self.assertFalse(payload["truth_state_used_for_acceptance"])
        self.assertFalse(payload["truth_state_used_for_covariance"])
        self.assertTrue(payload["truth_state_used_for_diagnostics"])
        self.assertTrue(all(not row["truth_state_used_for_acceptance"] for row in rows))
        self.assertTrue(all(not row["truth_state_used_for_covariance"] for row in rows))

    def test_safeguard_uses_non_truth_diagnostics(self) -> None:
        payload = audit.run_audit_and_candidates()
        guarded = [
            row for row in payload["rows"]
            if row["candidate"] == "residual_scaled_block_diag_with_sync_safeguard"
        ]
        fallback_rows = [row for row in guarded if row["fallback_used"]]

        self.assertEqual(len(fallback_rows), 3)
        self.assertTrue(all(row["safeguard_enabled"] for row in guarded))
        self.assertTrue(all(not row["safeguard_used_truth_metrics"] for row in guarded))
        self.assertTrue(
            all("single_user_clock_update_not_observable" in row["safeguard_reasons"] for row in fallback_rows)
        )
        self.assertTrue(all(row["fallback_behavior"] == "clock_and_drift_reverted_to_step_b" for row in fallback_rows))

    def test_candidate_summary_has_mean_and_max_ratios(self) -> None:
        payload_path = ROBUST_ROOT / "metadata.json"
        if not payload_path.exists():
            self.skipTest("Residual covariance robust candidate outputs have not been generated")
        payload = json.loads(payload_path.read_text(encoding="utf-8"))

        for row in payload["summary"]:
            self.assertIn("mean_position_ratio", row)
            self.assertIn("max_position_ratio", row)
            self.assertIn("mean_sync_ratio", row)
            self.assertIn("max_sync_ratio", row)
            self.assertIn("failure_row_count", row)
            self.assertIn("fallback_count", row)
        self.assertTrue((REPORTS / "STEP3_RESIDUAL_COV_FAILURE_AUDIT.md").exists())
        self.assertTrue((REPORTS / "STEP3_RESIDUAL_COV_FAILURE_AUDIT.json").exists())
        self.assertTrue((REPORTS / "STEP3_RESIDUAL_COV_ROBUST_CANDIDATE_REPORT.md").exists())
        self.assertTrue((REPORTS / "STEP3_RESIDUAL_COV_ROBUST_CANDIDATE_REPORT.json").exists())
        self.assertTrue((FAILURE_ROOT / "failure_rows.csv").exists())

    def test_gallery_includes_audit_plots_when_rendered(self) -> None:
        if not (ROBUST_ROOT / "plots" / "robust_candidate_max_ratio_comparison.pdf").exists():
            self.skipTest("Residual covariance robust candidate plots have not been generated")
        if not GALLERY.exists():
            self.skipTest("Plot gallery has not been rendered")
        gallery = json.loads(GALLERY.read_text(encoding="utf-8"))
        paths = {entry["source_pdf_path"] for entry in gallery["entries"]}

        self.assertIn("outputs/step3_residual_cov_robust_candidates/plots/robust_candidate_max_ratio_comparison.pdf", paths)
        self.assertIn("outputs/step3_residual_cov_robust_candidates/plots/block_diag_vs_full_covariance_row_comparison.pdf", paths)


if __name__ == "__main__":
    unittest.main()
