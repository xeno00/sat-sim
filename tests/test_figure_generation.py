import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

from jcls_sim.constants import C_KM_PER_S
from jcls_sim.figure_generation import (
    BASELINE_DEFINITIONS,
    _scenario_for_case,
    run_figure_config,
    run_single_trial,
)
from jcls_sim.gauge import expected_v24_parameter_dim, relative_clock_dict
from jcls_sim.metrics import position_error_m


class TestPackageNativeFigureGeneration(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="v24_figure_generation_test_"))

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
        self.assertFalse(metadata["notebook_used"])
        self.assertFalse(metadata["manuscript_directories_touched"])
        self.assertEqual(metadata["monte_carlo_trials"], 1)
        self.assertIn("without_cooperation", metadata["baselines"])
        self.assertIn("coarse_jcls", metadata["baselines"])
        self.assertIn("refined_jcls", metadata["baselines"])
        self.assertEqual(metadata["units"]["synchronization_metric_raw"], "s")
        self.assertEqual(metadata["units"]["plot_metric_unit"], "raw")

        provenance = json.loads(result.provenance_json.read_text(encoding="utf-8"))
        self.assertIn("run_v24_figures_4_7.py", provenance["command"])
        self.assertIn("test_figure_generation", provenance["test_coverage"][0])

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
        self.assertTrue(rows["coarse_jcls"]["is_full_rank"])
        self.assertLess(rows["coarse_jcls"]["position_error_mean_m"], 1e-5)
        self.assertLess(rows["coarse_jcls"]["sync_error_mean_s"], 1e-14)
        self.assertLess(rows["refined_jcls"]["position_error_mean_m"], 1e-5)
        self.assertLess(rows["refined_jcls"]["sync_error_mean_s"], 1e-14)

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
