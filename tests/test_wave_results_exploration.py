import csv
import json
import tempfile
import unittest
from pathlib import Path


from scripts import run_wave_results_exploration as wave


class WaveResultsExplorationTests(unittest.TestCase):
    def test_dry_run_plan_exposes_required_cli_and_grid(self) -> None:
        options = wave.WaveOptions(cache_root=Path("unused"), dry_run=True, only_product="observability", max_trials=1)
        plan = wave.build_plan(options)

        for flag in (
            "--dry-run",
            "--list-plan",
            "--resume",
            "--force-rerun",
            "--max-runtime-minutes",
            "--row-timeout-seconds",
            "--trial-timeout-seconds",
            "--max-trials",
            "--only-product",
            "--only-row",
            "--pilot",
            "--full",
            "--cache-root",
        ):
            self.assertIn(flag, plan["required_cli_options_supported"])
        self.assertEqual(plan["observability_grid"]["num_users"], [1, 2, 3, 4, 5])
        self.assertEqual(plan["observability_grid"]["num_satellites"], [1, 2, 3, 4, 5, 6, 7, 8])
        self.assertEqual(plan["observability_grid"]["monte_carlo_trials"], 1)

    def test_single_ue_row_is_baseline_only_and_rank_deficient_crlb_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache_root = Path(tmp) / "wave_results"
            options = wave.WaveOptions(
                cache_root=cache_root,
                only_product="observability",
                only_row="observability_nu1_ns4_p1p0_c7e-06_t0",
                max_trials=1,
                force_rerun=True,
                render_plots=True,
            )
            payload = wave.run_wave_results(options)

            self.assertEqual(payload["products"][0]["name"], "observability")
            raw_rows = list(csv.DictReader((cache_root / "observability" / "raw.csv").read_text(encoding="utf-8").splitlines()))
            self.assertEqual(len(raw_rows), 1)
            row = raw_rows[0]
            self.assertEqual(row["single_ue_baseline_only"], "True")
            self.assertEqual(row["jcls_applicable"], "False")
            self.assertEqual(row["failure_reason"], "single_ue_baseline_only")
            self.assertEqual(row["crlb_status"], "rank_deficient_diagnostic")
            self.assertEqual(row["crlb_position_m"], "")
            self.assertTrue((cache_root / "WAVE_PLOT_GALLERY.json").exists())
            gallery = json.loads((cache_root / "WAVE_PLOT_GALLERY.json").read_text(encoding="utf-8"))
            self.assertGreaterEqual(gallery["entry_count"], 4)
            self.assertTrue((cache_root.parent / "reports" / "WAVE_RESULTS_PHASE_TRANSITION_REPORT.md").exists())

    def test_row_checkpoint_resume_skips_completed_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = wave.WavePaths.from_cache_root(Path(tmp) / "wave_results")
            row_spec = {
                "product": "observability",
                "num_users": 1,
                "num_satellites": 4,
                "trial_id": 0,
                "seed": 101124,
                "clock_sigma_seconds": wave.DEFAULT_CLOCK_SIGMA_SECONDS,
                "sl_edge_probability": 1.0,
                "full_mesh": True,
                "run_stage_c": True,
            }
            first = wave._execute_trial_row(
                paths=paths,
                row_id="observability_nu1_ns4_p1p0_c7e-06_t0",
                row_spec=row_spec,
                options=wave.WaveOptions(cache_root=paths.output_root, force_rerun=True),
            )
            second = wave._execute_trial_row(
                paths=paths,
                row_id="observability_nu1_ns4_p1p0_c7e-06_t0",
                row_spec=row_spec,
                options=wave.WaveOptions(cache_root=paths.output_root),
            )

            self.assertEqual(first["cache_status"], "miss")
            self.assertEqual(second["cache_status"], "hit")
            status_lines = (paths.output_root / "ROW_STATUS.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertTrue(any("cache_hit" in line for line in status_lines))

    def test_failed_row_is_preserved_without_killing_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = wave.WavePaths.from_cache_root(Path(tmp) / "wave_results")
            row = wave._execute_trial_row(
                paths=paths,
                row_id="bad_row",
                row_spec={
                    "product": "observability",
                    "num_users": 0,
                    "num_satellites": 1,
                    "trial_id": 0,
                    "seed": 1,
                },
                options=wave.WaveOptions(cache_root=paths.output_root, force_rerun=True),
            )

            self.assertTrue(row["failure_recorded"])
            self.assertIn("num_users", row["failure_reason"])
            self.assertTrue((paths.output_root / "observability" / "cache" / "bad_row.json").exists())

    def test_sparse_graph_generation_and_threshold_helpers(self) -> None:
        links0, edges0, graph0 = wave._sidelink_graph(num_users=4, edge_probability=0.0, seed=1)
        links1, edges1, graph1 = wave._sidelink_graph(num_users=4, edge_probability=1.0, seed=1)

        self.assertEqual(len(links0), 0)
        self.assertEqual(len(edges0), 0)
        self.assertEqual(graph0["connected_component_count"], 4)
        self.assertEqual(len(links1), 12)
        self.assertEqual(len(edges1), 6)
        self.assertTrue(graph1["graph_connected"])

        rows = [
            {"num_satellites": 3, "stage_b_position_rmse_m_mean": 2.0},
            {"num_satellites": 4, "stage_b_position_rmse_m_mean": 0.5},
            {"num_satellites": 5, "stage_b_position_rmse_m_mean": 0.1},
        ]
        self.assertEqual(wave._min_satellites_for_threshold(rows, "stage_b_position_rmse_m_mean", 1.0), 4)
        self.assertEqual(wave._saved_satellites(8, 4), 4)

        clock_summary = [
            {"clock_sigma_seconds": 1e-9, "stage_b_position_rmse_m_mean": 0.5, "stage_a_position_rmse_m_mean": 2.0, "stage_c_position_rmse_m_mean": 0.4},
            {"clock_sigma_seconds": 1e-6, "stage_b_position_rmse_m_mean": 2.0, "stage_a_position_rmse_m_mean": 3.0, "stage_c_position_rmse_m_mean": 1.5},
        ]
        threshold_rows = wave._threshold_table(clock_summary, x_key="clock_sigma_seconds", direction="max")
        stage_b_1m = [row for row in threshold_rows if row["method"] == "Stage B" and row["threshold_m"] == 1.0][0]
        self.assertEqual(stage_b_1m["clock_sigma_seconds"], 1e-9)

    def test_wave_outputs_do_not_target_forbidden_manuscript_paths(self) -> None:
        plan = wave.build_plan(wave.WaveOptions(cache_root=Path("outputs/wave_results"), only_product="observability", max_trials=1))
        plan_text = json.dumps(plan)
        for forbidden in ("Work-In-Progress", "PSFrag", "Response-Letter", "SCL-NTN-TAES-2025-V24.tex", "JCLS_Simulation.ipynb"):
            self.assertNotIn(forbidden, plan_text)


if __name__ == "__main__":
    unittest.main()
