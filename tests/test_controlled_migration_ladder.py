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
from scripts.run_controlled_migration_ladder import (
    LadderRunOptions,
    _cache_payload_status,
    _execution_metadata,
    _heartbeat_payload,
    _install_map_diagnosis,
    _install_residual_lm_acceptance,
    _parse_args,
    _planned_work,
    _should_stop_after_degradation,
)


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

    def test_dry_run_plan_lists_rows_without_medium_by_default(self) -> None:
        options = _parse_args([
            "--dry-run",
            "--step",
            "step_c0_legacy_map_instrumented",
        ])
        planned = _planned_work(options)

        self.assertTrue(options.dry_run)
        self.assertTrue(options.tiny_only)
        self.assertFalse(options.include_medium)
        self.assertGreater(len(planned), 0)
        self.assertEqual({row["grid"] for row in planned}, {"tiny"})

    def test_default_run_is_tiny_only(self) -> None:
        options = _parse_args([])

        self.assertTrue(options.tiny_only)
        self.assertFalse(options.include_medium)

    def test_medium_requires_explicit_medium_flag(self) -> None:
        without_medium = _parse_args(["--step", "step_c0_legacy_map_instrumented"])
        with_medium = _parse_args(["--step", "step_c0_legacy_map_instrumented", "--medium"])

        self.assertEqual({row["grid"] for row in _planned_work(without_medium)}, {"tiny"})
        self.assertIn("medium", {row["grid"] for row in _planned_work(with_medium)})

    def test_max_rows_limits_planned_execution(self) -> None:
        options = _parse_args([
            "--step",
            "step_c0_legacy_map_instrumented",
            "--tiny-only",
            "--max-rows",
            "2",
        ])

        self.assertEqual(len(_planned_work(options)), 2)

    def test_tiny_only_does_not_run_medium_even_with_no_medium_flag(self) -> None:
        options = _parse_args([
            "--step",
            "step_c0_legacy_map_instrumented",
            "--medium",
            "--no-medium",
        ])
        planned = _planned_work(options)

        self.assertEqual({row["grid"] for row in planned}, {"tiny"})

    def test_partial_execution_is_not_valid_cache(self) -> None:
        options = LadderRunOptions(max_rows=2)
        metadata = {"execution": _execution_metadata(
            planned_rows=4,
            executed_rows=2,
            status="partial",
            options=options,
            output_grid="tiny_bounded",
        )}

        self.assertEqual(_cache_payload_status(metadata), "partial")
        self.assertFalse(metadata["execution"]["complete"])

    def test_bounded_complete_execution_is_not_canonical_cache(self) -> None:
        options = LadderRunOptions(max_rows=2)
        metadata = {"execution": _execution_metadata(
            planned_rows=2,
            executed_rows=2,
            status="complete",
            options=options,
            output_grid="tiny_bounded",
        )}

        self.assertEqual(_cache_payload_status(metadata), "bounded_noncanonical")
        self.assertFalse(metadata["execution"]["canonical_cache_valid"])

    def test_heartbeat_payload_has_required_schema(self) -> None:
        payload = _heartbeat_payload(
            status="running",
            current_substep="step_c0_legacy_map_instrumented",
            current_grid_point={"grid": "tiny", "num_users": 1, "num_satellites": 4},
            row_number=1,
            total_rows=2,
            started_monotonic=0.0,
            process_start_time_utc="2026-06-08T00:00:00Z",
            last_completed_output=None,
        )

        for key in [
            "current_substep",
            "current_grid_point",
            "row_number",
            "elapsed_time_seconds",
            "estimated_remaining_rows",
            "last_completed_output",
            "process_start_time_utc",
            "status",
        ]:
            self.assertIn(key, payload)

    def test_timeout_status_is_represented_in_metadata(self) -> None:
        metadata = _execution_metadata(
            planned_rows=4,
            executed_rows=1,
            status="timeout_seconds_total",
            options=LadderRunOptions(timeout_seconds_total=1.0),
            output_grid="tiny_bounded",
        )

        self.assertEqual(metadata["status"], "timeout_seconds_total")
        self.assertTrue(metadata["partial"])
        self.assertFalse(metadata["complete"])

    def test_stop_after_first_degradation_guard(self) -> None:
        report = {"health": {"performance_degraded_vs_previous": True}}

        self.assertTrue(_should_stop_after_degradation(report, LadderRunOptions(stop_after_first_degradation=True)))
        self.assertFalse(_should_stop_after_degradation(report, LadderRunOptions(stop_after_first_degradation=False)))

    def test_dry_run_does_not_execute_rows(self) -> None:
        from scripts.run_controlled_migration_ladder import run_ladder

        payload = run_ladder(LadderRunOptions(
            steps=("step_c0_legacy_map_instrumented",),
            max_rows=1,
            dry_run=True,
        ))

        self.assertEqual(payload["artifact_status"], "non_final_controlled_migration_ladder_dry_run")
        self.assertEqual(payload["row_count"], 1)
        self.assertNotIn("execution", payload)

    def test_bounded_recovery_uses_separate_output_stem(self) -> None:
        options = LadderRunOptions(steps=("step_c0_legacy_map_instrumented",), max_rows=2)
        self.assertTrue(options.bounded)
        self.assertNotEqual("tiny_bounded", "tiny")


if __name__ == "__main__":
    unittest.main()
