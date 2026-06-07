import csv
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

from jcls_sim.constants import C_KM_PER_S
from jcls_sim.figure_generation import (
    BASELINE_DEFINITIONS,
    ARTIFACT_WARNING,
    CANDIDATE_ARTIFACT_WARNING,
    HUMAN_REVIEW_ARTIFACT_WARNING,
    _scenario_for_case,
    load_figure_config,
    run_figure_config,
    run_single_trial,
    validate_figure_id,
    validate_output_root,
)
from jcls_sim.gauge import expected_v24_parameter_dim, relative_clock_dict
from jcls_sim.metrics import position_error_m


class TestPackageNativeFigureGeneration(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix=".tmp_v24_figure_generation_test_", dir=Path.cwd()))

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _tiny_config(self) -> Path:
        config = {
            "figure_id": "test_fig4_tiny",
            "manuscript_figure_label": "test",
            "title": "Tiny package-native test",
            "sweep_type": "satellite_count",
            "metric_field": "position_error_mean_m",
            "x_label": "Ns",
            "y_label": "error [m]",
            "log_y": True,
            "base_seed": 12345,
            "monte_carlo_trials": 1,
            "num_users_values": [2],
            "num_satellites_values": [6],
            "clock_std_devs_ns": [1000.0],
            "range_std_dev_km": 0.03,
            "refinement_epochs": 2,
            "assumptions": ["unit-test config"],
            "known_discrepancy_from_v24": "unit-test config",
        }
        path = self.temp_dir / "tiny_config.json"
        path.write_text(json.dumps(config), encoding="utf-8")
        return path

    def _tiny_candidate_config(self) -> Path:
        config = {
            "figure_id": "test_fig_candidate_tiny",
            "manuscript_figure_label": "test candidate",
            "artifact_profile": "manuscript_candidate",
            "scenario_model": "manuscript_candidate_mit_stata_synthetic_leo",
            "title": "Tiny manuscript-candidate test",
            "sweep_type": "satellite_count",
            "metric_field": "position_error_mean_m",
            "plot_metric_scale": 1.0,
            "plot_metric_unit": "m",
            "x_label": "Ns",
            "y_label": "error [m]",
            "log_y": True,
            "base_seed": 23456,
            "monte_carlo_trials": 1,
            "num_users_values": [1],
            "num_satellites_values": [4],
            "clock_std_devs_ns": [1000.0],
            "refinement_epochs": 1,
            "refinement_interval_s": 0.5,
            "refinement_epoch_dt_s": 0.5,
            "estimator_mode": "v24_three_stage_dynamic",
            "process_noise_std_km": 1e-5,
            "reference_location": {
                "latitude_deg": 42.361145,
                "longitude_deg": -71.09085,
                "altitude_m": 20.0,
            },
            "ue_disk_radius_m": 500.0,
            "minimum_elevation_deg": 30.0,
            "satellite_pool_size": 12,
            "satellite_altitude_km": 550.0,
            "link_budget": {
                "dl_frequency_hz": 2.2e9,
                "dl_bandwidth_hz": 20.0e6,
                "dl_transmit_power_dbm": 55.0,
                "dl_transmit_antenna_gain_db": 20.0,
                "dl_receive_antenna_gain_db": 3.0,
                "sl_frequency_hz": 5.9e9,
                "sl_bandwidth_hz": 40.0e6,
                "sl_transmit_power_dbm": 20.0,
                "sl_transmit_antenna_gain_db": 3.0,
                "sl_receive_antenna_gain_db": 3.0,
                "noise_density_dbm_per_hz": -174.0,
                "receiver_noise_figure_db": 5.0,
                "implementation_loss_db": 0.0,
            },
            "assumptions": ["unit-test candidate config"],
            "known_discrepancy_from_v24": "unit-test candidate config",
        }
        path = self.temp_dir / "tiny_candidate_config.json"
        path.write_text(json.dumps(config), encoding="utf-8")
        return path

    def _json_strings(self, value):
        if isinstance(value, str):
            yield value
        elif isinstance(value, dict):
            for nested in value.values():
                yield from self._json_strings(nested)
        elif isinstance(value, list):
            for nested in value:
                yield from self._json_strings(nested)

    def test_tiny_config_writes_complete_output_package(self) -> None:
        result = run_figure_config(self._tiny_config(), self.temp_dir / "outputs")

        for path in (
            result.raw_csv,
            result.summary_csv,
            result.raw_npz,
            result.pdf,
            result.metadata_json,
            result.provenance_json,
        ):
            self.assertTrue(path.exists(), path)
            self.assertGreater(path.stat().st_size, 0)

        metadata = json.loads(result.metadata_json.read_text(encoding="utf-8"))
        self.assertTrue(metadata["diagnostic_only"])
        self.assertTrue(metadata["non_final"])
        self.assertFalse(metadata["manuscript_ready"])
        self.assertTrue(metadata["not_for_manuscript_submission"])
        self.assertEqual(metadata["artifact_warning"], ARTIFACT_WARNING)
        self.assertFalse(metadata["notebook_used"])
        self.assertFalse(metadata["manuscript_directories_touched"])
        self.assertEqual(metadata["monte_carlo_trials"], 1)
        self.assertFalse(metadata["overwrite_used"])
        self.assertFalse(Path(metadata["config_path"]).is_absolute())
        self.assertFalse(Path(metadata["output_dir"]).is_absolute())
        self.assertIn("without_cooperation", metadata["baselines"])
        self.assertIn("coarse_jcls", metadata["baselines"])
        self.assertIn("refined_jcls", metadata["baselines"])
        self.assertEqual(metadata["units"]["synchronization_metric_raw"], "s")
        self.assertEqual(metadata["units"]["plot_metric_unit"], "raw")

        provenance = json.loads(result.provenance_json.read_text(encoding="utf-8"))
        self.assertTrue(provenance["diagnostic_only"])
        self.assertTrue(provenance["non_final"])
        self.assertFalse(provenance["manuscript_ready"])
        self.assertTrue(provenance["not_for_manuscript_submission"])
        self.assertEqual(provenance["artifact_warning"], ARTIFACT_WARNING)
        self.assertIn("run_v24_figures_4_7.py", provenance["command"])
        self.assertIn("test_figure_generation", provenance["test_coverage"][0])
        self.assertFalse(Path(provenance["config_file"]).is_absolute())
        self.assertFalse(Path(provenance["raw_output_file"]).is_absolute())

    def test_checked_in_configs_have_required_schema(self) -> None:
        config_paths = list(Path("configs/v24_figures_4_7").glob("*.json"))
        config_paths += list(Path("configs/v24_manuscript_candidate_figures_4_7").glob("*.json"))
        config_paths += list(Path("configs/v24_human_review_figures_4_7").glob("*.json"))

        for path in sorted(config_paths):
            with self.subTest(config=path.name):
                config = load_figure_config(path)
                self.assertIn(config["sweep_type"], {"satellite_count", "clock_std"})
                self.assertIsInstance(config["base_seed"], int)
                self.assertGreaterEqual(config["monte_carlo_trials"], 1)
                self.assertIn("plot_metric_scale", config)
                self.assertIn("plot_metric_unit", config)
                self.assertIn("assumptions", config)
                self.assertIn("known_discrepancy_from_v24", config)
                self.assertGreater(len(config["assumptions"]), 0)
                self.assertIn(config.get("artifact_profile", "diagnostic"), {"diagnostic", "manuscript_candidate", "human_review"})
                if config.get("artifact_profile") in {"manuscript_candidate", "human_review"}:
                    self.assertEqual(config["scenario_model"], "manuscript_candidate_mit_stata_synthetic_leo")
                    self.assertEqual(config.get("estimator_mode"), "v24_three_stage_dynamic")
                    self.assertIn("process_noise_std_km", config)
                    self.assertIn("reference_location", config)
                    self.assertIn("link_budget", config)
                else:
                    self.assertIn("not forced to match legacy notebook curves", config["known_discrepancy_from_v24"])
                if config["metric_field"] == "sync_error_mean_s":
                    self.assertEqual(config["plot_metric_scale"], 1_000_000_000.0)
                    self.assertEqual(config["plot_metric_unit"], "ns")
                else:
                    self.assertEqual(config["plot_metric_unit"], "m")

    def test_unsafe_figure_ids_are_rejected(self) -> None:
        unsafe_ids = [
            "",
            ".",
            "../Work-In-Progress/x",
            "fig4/../../PSFrag/x",
            "fig4\\PSFrag",
            "fig 4",
            "CON",
            "legacy_fig4",
        ]

        for figure_id in unsafe_ids:
            with self.subTest(figure_id=figure_id):
                with self.assertRaises(ValueError):
                    validate_figure_id(figure_id)

    def test_checked_in_outputs_have_hardened_schema(self) -> None:
        output_root = Path("v24_figure_outputs")
        forbidden_fragments = ["C:/", "C:\\", "Users/James", "Users\\James", "MIT Dropbox"]
        expected_figures = {
            "fig4_localization_vs_satellites",
            "fig5_synchronization_vs_satellites",
            "fig6_localization_vs_clock_std",
            "fig7_synchronization_vs_clock_std",
        }

        self.assertTrue(output_root.exists())
        self.assertEqual(
            {path.name for path in output_root.iterdir() if path.is_dir()},
            expected_figures,
        )
        self.assertTrue((output_root / "figure_provenance_table.json").exists())
        self.assertTrue((output_root / "figure_provenance_table.md").exists())

        for figure_id in expected_figures:
            with self.subTest(figure_id=figure_id):
                figure_dir = output_root / figure_id
                expected_files = {
                    f"{figure_id}.pdf",
                    f"{figure_id}_metadata.json",
                    f"{figure_id}_provenance.json",
                    f"{figure_id}_raw.csv",
                    f"{figure_id}_raw.npz",
                    f"{figure_id}_summary.csv",
                }
                self.assertEqual({path.name for path in figure_dir.iterdir()}, expected_files)

                metadata = json.loads((figure_dir / f"{figure_id}_metadata.json").read_text(encoding="utf-8"))
                provenance = json.loads((figure_dir / f"{figure_id}_provenance.json").read_text(encoding="utf-8"))
                for payload in (metadata, provenance):
                    self.assertTrue(payload["diagnostic_only"])
                    self.assertTrue(payload["non_final"])
                    self.assertFalse(payload["manuscript_ready"])
                    self.assertTrue(payload["not_for_manuscript_submission"])
                    self.assertEqual(payload["artifact_warning"], ARTIFACT_WARNING)
                    for text in self._json_strings(payload):
                        for forbidden in forbidden_fragments:
                            self.assertNotIn(forbidden, text)
                self.assertEqual(provenance["provenance_type"], "package_native_v24_diagnostic_figure_provenance")
                self.assertTrue(provenance["config_file"].startswith("configs/v24_figures_4_7/"))
                self.assertTrue(provenance["raw_output_file"].startswith("v24_figure_outputs/"))

        combined = json.loads((output_root / "figure_provenance_table.json").read_text(encoding="utf-8"))
        self.assertEqual(combined["provenance_table_type"], "package_native_v24_diagnostic_figure_provenance_table")
        self.assertTrue(combined["diagnostic_only"])
        self.assertFalse(combined["manuscript_ready"])
        self.assertEqual(len(combined["rows"]), 4)
        for text in self._json_strings(combined):
            for forbidden in forbidden_fragments:
                self.assertNotIn(forbidden, text)

    def test_checked_in_candidate_outputs_have_candidate_schema(self) -> None:
        output_root = Path("v24_manuscript_candidate_outputs")
        expected_figures = {
            "fig4_localization_vs_satellites_candidate",
            "fig5_synchronization_vs_satellites_candidate",
            "fig6_localization_vs_clock_std_candidate",
            "fig7_synchronization_vs_clock_std_candidate",
        }

        self.assertTrue(output_root.exists())
        self.assertEqual({path.name for path in output_root.iterdir() if path.is_dir()}, expected_figures)
        combined = json.loads((output_root / "figure_provenance_table.json").read_text(encoding="utf-8"))
        self.assertFalse(combined["diagnostic_only"])
        self.assertTrue(combined["candidate_only"])
        self.assertFalse(combined["manuscript_ready"])
        self.assertEqual(combined["artifact_warning"], CANDIDATE_ARTIFACT_WARNING)
        self.assertEqual(len(combined["rows"]), 4)

        for figure_id in expected_figures:
            with self.subTest(figure_id=figure_id):
                figure_dir = output_root / figure_id
                metadata = json.loads((figure_dir / f"{figure_id}_metadata.json").read_text(encoding="utf-8"))
                provenance = json.loads((figure_dir / f"{figure_id}_provenance.json").read_text(encoding="utf-8"))
                self.assertFalse(metadata["diagnostic_only"])
                self.assertTrue(metadata["candidate_only"])
                self.assertFalse(metadata["manuscript_ready"])
                self.assertEqual(metadata["artifact_warning"], CANDIDATE_ARTIFACT_WARNING)
                self.assertIn("case_metadata", metadata)
                self.assertIn("geometry", metadata["case_metadata"][0])
                self.assertIn("link_noise", metadata["case_metadata"][0])
                self.assertEqual(provenance["provenance_type"], "package_native_v24_manuscript_candidate_figure_provenance")
                self.assertTrue(provenance["candidate_only"])

    def test_output_root_guard_rejects_unsafe_locations(self) -> None:
        unsafe_roots = [
            Path("..") / "outside",
            Path("Work-In-Progress") / "Figures",
            Path("PSFrag") / "figures",
            Path("legacy") / "outputs",
            Path("notebook") / "outputs",
            Path(tempfile.gettempdir()) / "external_v24_figures",
        ]

        for unsafe_root in unsafe_roots:
            with self.subTest(root=str(unsafe_root)):
                with self.assertRaises(ValueError):
                    validate_output_root(unsafe_root)

    def test_output_root_guard_accepts_default_diagnostic_root(self) -> None:
        safe = validate_output_root(Path("v24_figure_outputs"))

        self.assertEqual(safe, Path("v24_figure_outputs"))

    def test_output_root_guard_accepts_candidate_root(self) -> None:
        safe = validate_output_root(Path("v24_manuscript_candidate_outputs"))

        self.assertEqual(safe, Path("v24_manuscript_candidate_outputs"))

    def test_developer_override_allows_external_root(self) -> None:
        external = Path(tempfile.gettempdir()) / "external_v24_figures"

        self.assertEqual(validate_output_root(external, allow_unsafe_output_root=True), external)

    def test_no_overwrite_and_explicit_overwrite_behavior(self) -> None:
        config_path = self._tiny_config()
        output_root = self.temp_dir / "overwrite_outputs"

        run_figure_config(config_path, output_root)
        with self.assertRaises(FileExistsError):
            run_figure_config(config_path, output_root)
        metadata = json.loads(
            run_figure_config(config_path, output_root, overwrite=True).metadata_json.read_text(encoding="utf-8")
        )
        self.assertTrue(metadata["overwrite_used"])

    def test_cli_writes_combined_provenance_table(self) -> None:
        config_path = self._tiny_config()
        output_root = self.temp_dir / "cli_outputs"

        completed = subprocess.run(
            [
                sys.executable,
                "scripts/run_v24_figures_4_7.py",
                "--config",
                str(config_path),
                "--output-root",
                str(output_root),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("combined provenance", completed.stdout)
        combined = json.loads((output_root / "figure_provenance_table.json").read_text(encoding="utf-8"))
        self.assertTrue(combined["diagnostic_only"])
        self.assertFalse(combined["manuscript_ready"])
        self.assertEqual(combined["artifact_warning"], ARTIFACT_WARNING)
        self.assertEqual(len(combined["rows"]), 1)
        self.assertFalse(Path(combined["rows"][0]["config_file"]).is_absolute())

    def test_candidate_config_writes_candidate_metadata(self) -> None:
        result = run_figure_config(self._tiny_candidate_config(), self.temp_dir / "candidate_outputs")

        metadata = json.loads(result.metadata_json.read_text(encoding="utf-8"))
        self.assertFalse(metadata["diagnostic_only"])
        self.assertTrue(metadata["candidate_only"])
        self.assertTrue(metadata["non_final"])
        self.assertFalse(metadata["manuscript_ready"])
        self.assertEqual(metadata["artifact_warning"], CANDIDATE_ARTIFACT_WARNING)
        self.assertEqual(metadata["artifact_kind"], "manuscript_candidate")
        self.assertEqual(metadata["scenario_model"], "manuscript_candidate_mit_stata_synthetic_leo")
        self.assertEqual(metadata["estimator_mode"], "v24_three_stage_dynamic")
        self.assertEqual(metadata["estimator_metadata"]["v24_three_stage_dynamic"]["state_model"], "x=theta, F=I, Pi=I, Q=process_noise_std_km^2 I")
        self.assertEqual(metadata["rank_metadata"]["scope"], "full_jcls_scenario_plus_baseline_specific_observability")
        self.assertFalse(metadata["rank_metadata"]["baseline_specific_rank_pending"])
        self.assertIn("case_metadata", metadata)
        self.assertIn("ue_coordinates", metadata["case_metadata"][0]["geometry"])
        self.assertIn("satellite_coordinates", metadata["case_metadata"][0]["geometry"])
        self.assertIn("link_noise", metadata["case_metadata"][0])
        self.assertIn("dl_range_sigma_m_min", metadata["case_metadata"][0]["link_noise"]["summary"])

        provenance = json.loads(result.provenance_json.read_text(encoding="utf-8"))
        self.assertEqual(provenance["provenance_type"], "package_native_v24_manuscript_candidate_figure_provenance")
        self.assertTrue(provenance["candidate_only"])
        self.assertIn("candidate_outputs", provenance["command"])
        self.assertEqual(provenance["rank_metadata"]["scope"], "full_jcls_scenario_plus_baseline_specific_observability")

    def test_human_review_config_writes_human_review_metadata(self) -> None:
        config = json.loads(self._tiny_candidate_config().read_text(encoding="utf-8"))
        config["figure_id"] = "test_fig_human_review_tiny"
        config["artifact_profile"] = "human_review"
        config_path = self.temp_dir / "tiny_human_review_config.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")

        result = run_figure_config(config_path, self.temp_dir / "human_review_outputs")
        metadata = json.loads(result.metadata_json.read_text(encoding="utf-8"))
        provenance = json.loads(result.provenance_json.read_text(encoding="utf-8"))

        self.assertFalse(metadata["diagnostic_only"])
        self.assertTrue(metadata["human_review_ready"])
        self.assertTrue(metadata["candidate_only"])
        self.assertTrue(metadata["non_final"])
        self.assertFalse(metadata["manuscript_ready"])
        self.assertTrue(metadata["not_for_manuscript_submission"])
        self.assertEqual(metadata["artifact_warning"], HUMAN_REVIEW_ARTIFACT_WARNING)
        self.assertEqual(metadata["artifact_kind"], "human_review")
        self.assertEqual(provenance["provenance_type"], "package_native_v24_human_review_figure_provenance")
        self.assertTrue(provenance["human_review_ready"])

    def test_baseline_definitions_are_explicit(self) -> None:
        self.assertFalse(BASELINE_DEFINITIONS["without_cooperation"]["uses_sl"])
        self.assertIn("ignored", BASELINE_DEFINITIONS["without_cooperation"]["satellite_clocks"])
        self.assertTrue(BASELINE_DEFINITIONS["coarse_jcls"]["uses_sl"])
        self.assertTrue(BASELINE_DEFINITIONS["refined_jcls"]["uses_sl"])
        self.assertIn("full V24 theta", BASELINE_DEFINITIONS["coarse_jcls"]["state_estimated"])

    def test_zero_noise_full_gauge_recovery(self) -> None:
        scenario = _scenario_for_case(
            num_users=2,
            num_satellites=6,
            seed=101,
            clock_std_ns=1000.0,
            range_std_dev_km=0.03,
        )
        rows = {
            row["baseline_id"]: row
            for row in run_single_trial(
                scenario,
                trial_seed=202,
                refinement_epochs=3,
                noise_scale=0.0,
            )
        }

        self.assertEqual(rows["coarse_jcls"]["parameter_dim"], expected_v24_parameter_dim(2, 6))
        self.assertTrue(rows["coarse_jcls"]["full_jcls_scenario_is_full_rank"])
        self.assertLess(rows["coarse_jcls"]["position_error_mean_m"], 1e-5)
        self.assertLess(rows["coarse_jcls"]["sync_error_mean_s"], 1e-14)
        self.assertLess(rows["refined_jcls"]["position_error_mean_m"], 1e-5)
        self.assertLess(rows["refined_jcls"]["sync_error_mean_s"], 1e-14)

    def test_candidate_rows_use_conservative_success_and_scoped_rank_metadata(self) -> None:
        result = run_figure_config(self._tiny_candidate_config(), self.temp_dir / "candidate_outputs")
        with result.raw_csv.open(newline="", encoding="utf-8") as handle:
            raw_rows = list(csv.DictReader(handle))
        with result.summary_csv.open(newline="", encoding="utf-8") as handle:
            summary_rows = list(csv.DictReader(handle))

        self.assertGreater(len(raw_rows), 0)
        for row in raw_rows:
            self.assertNotIn("fim_rank", row)
            self.assertNotIn("is_full_rank", row)
            self.assertIn("full_jcls_scenario_fim_rank", row)
            self.assertEqual(row["rank_metadata_scope"], "full_jcls_scenario_not_baseline_observability")
            self.assertIn("baseline_observability_rank", row)
            self.assertIn("baseline_observability_scope", row)
            if row["baseline_id"] in {"coarse_jcls", "refined_jcls"} and row["algorithm_converged"] == "False":
                self.assertEqual(row["success"], "False")

        for row in summary_rows:
            self.assertNotIn("min_fim_rank", row)
            self.assertNotIn("all_full_rank", row)
            self.assertIn("min_full_jcls_scenario_fim_rank", row)
            self.assertEqual(row["rank_metadata_scope"], "full_jcls_scenario_not_baseline_observability")
            self.assertIn("min_baseline_observability_rank", row)
            self.assertIn("all_baseline_observability_reportable", row)

    def test_single_ue_has_no_sidelinks(self) -> None:
        scenario = _scenario_for_case(
            num_users=1,
            num_satellites=6,
            seed=303,
            clock_std_ns=100.0,
            range_std_dev_km=0.03,
        )

        self.assertTrue(all(not (rx <= 1 and tx <= 1) for rx, tx in scenario.links))

    def test_gauge_shift_invariance_for_relative_clocks(self) -> None:
        full = {1: 1.0, 2: -2.0, 3: 10.0, 4: 12.0}
        shifted = {node_id: value + 123.0 for node_id, value in full.items()}

        self.assertEqual(relative_clock_dict(full, 2, 2), relative_clock_dict(shifted, 2, 2))

    def test_meter_vs_kilometer_position_metric_equivalence(self) -> None:
        true_m = np.array([[0.0, 0.0, 0.0], [1000.0, 2000.0, 0.0]])
        est_m = true_m + np.array([[3.0, 4.0, 0.0], [0.0, 6.0, 8.0]])
        errors_m = position_error_m(true_m / 1000.0, est_m / 1000.0)

        np.testing.assert_allclose(errors_m, np.array([5.0, 10.0]))

    def test_large_clock_offset_sweep_degrades_without_cooperation(self) -> None:
        low = _scenario_for_case(
            num_users=3,
            num_satellites=8,
            seed=404,
            clock_std_ns=1.0,
            range_std_dev_km=0.03,
        )
        high = _scenario_for_case(
            num_users=3,
            num_satellites=8,
            seed=404,
            clock_std_ns=10000.0,
            range_std_dev_km=0.03,
        )
        low_row = {
            row["baseline_id"]: row
            for row in run_single_trial(low, trial_seed=505, refinement_epochs=2)
        }["without_cooperation"]
        high_row = {
            row["baseline_id"]: row
            for row in run_single_trial(high, trial_seed=505, refinement_epochs=2)
        }["without_cooperation"]

        self.assertGreater(high_row["position_error_mean_m"], low_row["position_error_mean_m"])

    def test_clock_units_are_seconds_after_range_conversion(self) -> None:
        one_ns_km = 1e-9 * C_KM_PER_S
        self.assertAlmostEqual(one_ns_km / C_KM_PER_S, 1e-9)

    def test_no_notebook_import_is_used(self) -> None:
        run_figure_config(self._tiny_config(), self.temp_dir / "outputs")

        self.assertNotIn("JCLS_Simulation", set(sys.modules))

    def test_generation_source_does_not_target_manuscript_outputs(self) -> None:
        source = Path("jcls_sim/figure_generation.py").read_text(encoding="utf-8")

        self.assertNotIn("Work-In-Progress", source)
        self.assertNotIn("PSFrag", source)
        self.assertNotIn("GeneratePSFrag", source)
        self.assertNotIn("savefig('../../", source)


if __name__ == "__main__":
    unittest.main()
