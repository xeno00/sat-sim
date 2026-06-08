import json
import unittest
from pathlib import Path

from jcls_sim.migration import (
    legacy_staged_compatible_step,
    step_a_no_display_smoothing,
    step_b_lm_residual_acceptance,
    step_c1_legacy_cov_observable_acceptance,
    step_c2_observable_cov_legacy_acceptance,
    step_c3_cov_damped_pinv,
    step_diff,
)
from scripts.run_controlled_migration_ladder import _install_map_diagnosis, _install_residual_lm_acceptance


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

    def test_step_b_changes_only_lm_acceptance_mode(self) -> None:
        diff = step_diff(step_a_no_display_smoothing(), step_b_lm_residual_acceptance())

        self.assertEqual(diff, {"acceptance_mode": ("truth_gated_legacy", "residual_trust_region")})

    def test_step_c_diagnosis_substeps_change_expected_map_axes(self) -> None:
        c1 = step_diff(step_b_lm_residual_acceptance(), step_c1_legacy_cov_observable_acceptance())
        c2 = step_diff(step_b_lm_residual_acceptance(), step_c2_observable_cov_legacy_acceptance())
        c3 = step_diff(step_b_lm_residual_acceptance(), step_c3_cov_damped_pinv())

        self.assertEqual(c1, {"map_update_mode": ("truth_gated_legacy", "observable_residual_covariance_checks")})
        self.assertEqual(c2, {"map_covariance_mode": ("truth_error_diagonal", "damped_information_pseudoinverse")})
        self.assertEqual(
            c3,
            {
                "map_covariance_mode": ("truth_error_diagonal", "damped_pseudoinverse_information_matrix"),
                "map_update_mode": ("truth_gated_legacy", "observable_residual_covariance_checks"),
            },
        )

    def test_ladder_report_has_wrapper_and_step_a_tiny_medium(self) -> None:
        report = json.loads((REPORTS / "CONTROLLED_MIGRATION_LADDER.json").read_text(encoding="utf-8"))

        self.assertFalse(report["manuscript_ready"])
        self.assertIn(report["first_degraded_step"], [None, "step_b_lm_residual_acceptance"])
        self.assertEqual(report["stop_rule_triggered"], report["first_degraded_step"] is not None)
        names = {(entry["step"]["name"], entry["grid"]) for entry in report["steps"]}
        self.assertIn(("legacy_staged_compatible", "tiny"), names)
        self.assertIn(("legacy_staged_compatible", "medium"), names)
        self.assertIn(("step_a_no_display_smoothing", "tiny"), names)
        self.assertIn(("step_a_no_display_smoothing", "medium"), names)
        self.assertIn(("step_b_lm_residual_acceptance", "tiny"), names)
        if not any(entry["step"]["name"] == "step_b_lm_residual_acceptance" and entry["health"]["catastrophic_failure"] for entry in report["steps"]):
            self.assertIn(("step_b_lm_residual_acceptance", "medium"), names)
        self.assertIn(("step_c0_legacy_map_instrumented", "tiny"), names)
        self.assertIn(("step_c1_legacy_cov_observable_acceptance", "tiny"), names)
        self.assertIn(("step_c2_observable_cov_legacy_acceptance", "tiny"), names)
        self.assertTrue(all(entry["health"]["status"] in {"healthy", "partially_degraded", "failed"} for entry in report["steps"]))

    def test_each_step_grid_has_required_outputs(self) -> None:
        for step in [
            "legacy_staged_compatible",
            "step_a_no_display_smoothing",
            "step_b_lm_residual_acceptance",
            "step_c0_legacy_map_instrumented",
            "step_c1_legacy_cov_observable_acceptance",
            "step_c2_observable_cov_legacy_acceptance",
            "step_c3_cov_damped_pinv",
        ]:
            for grid in ["tiny", "medium"]:
                root = LADDER / step / grid
                if step.startswith("step_") and not root.exists():
                    continue
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
        self.assertIn("outputs/migration_ladder/step_b_lm_residual_acceptance/medium/pos_vary_ues.pdf", paths)
        self.assertIn("outputs/migration_ladder/step_c1_legacy_cov_observable_acceptance/tiny/pos_vary_ues.pdf", paths)

    def test_cache_key_changes_with_migration_step(self) -> None:
        wrapper = json.loads(
            (LADDER / "legacy_staged_compatible" / "medium" / "migration_step_metadata.json").read_text(encoding="utf-8")
        )
        step_a = json.loads(
            (LADDER / "step_a_no_display_smoothing" / "medium" / "migration_step_metadata.json").read_text(encoding="utf-8")
        )

        self.assertNotEqual(wrapper["cache"]["cache_key"], step_a["cache"]["cache_key"])

        step_b = json.loads(
            (LADDER / "step_b_lm_residual_acceptance" / "medium" / "migration_step_metadata.json").read_text(encoding="utf-8")
        )
        self.assertNotEqual(step_a["cache"]["cache_key"], step_b["cache"]["cache_key"])
        self.assertEqual(step_b["step"]["acceptance_mode"], "residual_trust_region")

    def test_single_ue_never_attempts_cooperative_jcls_in_ladder(self) -> None:
        raw = (LADDER / "step_b_lm_residual_acceptance" / "medium" / "migration_raw.csv").read_text(encoding="utf-8")

        single_user_lines = [line for line in raw.splitlines() if line.startswith("1,")]
        self.assertGreater(len(single_user_lines), 0)
        for line in single_user_lines:
            self.assertIn("False", line)
            self.assertIn("noncooperative_clockless_baseline_only", line)

    def test_step_b_metadata_records_no_truth_state_lm_acceptance(self) -> None:
        metadata = json.loads(
            (LADDER / "step_b_lm_residual_acceptance" / "medium" / "migration_step_metadata.json").read_text(encoding="utf-8")
        )

        self.assertEqual(metadata["lm_acceptance_mode"], "residual_trust_region")
        self.assertFalse(metadata["truth_state_used_for_lm_acceptance"])
        self.assertFalse(metadata["lm_acceptance_diagnostics"]["truth_state_used_for_lm_acceptance"])
        self.assertGreaterEqual(metadata["lm_acceptance_diagnostics"]["accepted_step_count"], 0)

    def test_step_b_accepted_steps_do_not_increase_residual_cost(self) -> None:
        metadata = json.loads(
            (LADDER / "step_b_lm_residual_acceptance" / "medium" / "migration_step_metadata.json").read_text(encoding="utf-8")
        )

        self.assertEqual(metadata["lm_acceptance_diagnostics"]["rows_with_residual_cost_increase"], 0)

    def test_step_b_lm_acceptance_patch_does_not_call_true_state(self) -> None:
        import inspect

        source = inspect.getsource(_install_residual_lm_acceptance)
        self.assertNotIn("get_true_state", source)

    def test_map_diagnosis_patch_records_truth_state_usage_modes(self) -> None:
        import inspect

        source = inspect.getsource(_install_map_diagnosis)
        self.assertIn("truth_state_used_for_map_covariance", source)
        self.assertIn("truth_acceptance", source)

    def test_step_b_comparison_report_exists(self) -> None:
        report = json.loads((REPORTS / "STEP_B_LM_ACCEPTANCE_COMPARISON.json").read_text(encoding="utf-8"))

        self.assertFalse(report["manuscript_ready"])
        self.assertEqual(report["step_b"], "step_b_lm_residual_acceptance")
        self.assertGreater(len(report["comparisons"]), 0)

    def test_step_c_diagnosis_report_exists(self) -> None:
        report = json.loads((REPORTS / "STEP_C_DIAGNOSIS_REPORT.json").read_text(encoding="utf-8"))

        self.assertFalse(report["manuscript_ready"])
        self.assertIn(report["breaking_factor"], {
            "covariance_replacement",
            "acceptance_replacement",
            "both_acceptance_and_covariance_or_map_instability",
            "neither_c1_nor_c2_breaks",
            "incomplete_c1_c2_evidence",
        })
        self.assertGreater(len(report["summaries"]), 0)


if __name__ == "__main__":
    unittest.main()
