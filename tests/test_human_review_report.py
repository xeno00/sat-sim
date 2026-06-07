import json
import shutil
import tempfile
import unittest
from pathlib import Path

from jcls_sim.figure_generation import HUMAN_REVIEW_ARTIFACT_WARNING, run_figure_config
from scripts.run_v24_figures_4_7 import _write_combined_provenance
from scripts.write_v24_human_review_report import write_report


class TestHumanReviewReport(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix=".tmp_v24_human_review_report_", dir=Path.cwd()))

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_report_writes_non_final_human_review_flags(self) -> None:
        config = {
            "figure_id": "test_human_review_report_fig",
            "manuscript_figure_label": "Fig. test",
            "artifact_profile": "human_review",
            "scenario_model": "manuscript_candidate_mit_stata_synthetic_leo",
            "title": "Tiny human review report figure",
            "sweep_type": "satellite_count",
            "metric_field": "position_error_mean_m",
            "plot_metric_scale": 1.0,
            "plot_metric_unit": "m",
            "x_label": "Ns",
            "y_label": "error [m]",
            "log_y": True,
            "base_seed": 45678,
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
            "assumptions": ["unit-test human-review config"],
            "known_discrepancy_from_v24": "unit-test human-review config",
        }
        config_path = self.temp_dir / "human_review_config.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")
        output_root = self.temp_dir / "human_outputs"
        result = run_figure_config(config_path, output_root)
        _write_combined_provenance(output_root, [result])

        json_path, md_path = write_report(output_root, previous_root=None, test_summary="unit tests")
        report = json.loads(json_path.read_text(encoding="utf-8"))

        self.assertTrue(json_path.exists())
        self.assertTrue(md_path.exists())
        self.assertTrue(report["human_review_ready"])
        self.assertTrue(report["candidate_only"])
        self.assertTrue(report["non_final"])
        self.assertFalse(report["manuscript_ready"])
        self.assertTrue(report["not_for_manuscript_submission"])
        self.assertEqual(report["artifact_warning"], HUMAN_REVIEW_ARTIFACT_WARNING)
        self.assertEqual(report["figure_count"], 1)
        self.assertIn("unit tests", report["test_summary"])


if __name__ == "__main__":
    unittest.main()
