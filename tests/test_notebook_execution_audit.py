import unittest
from pathlib import Path

import numpy as np

from jcls_sim.constants import C_KM_PER_S, C_M_PER_S
from scripts.audit_notebook_measurements import (
    deterministic_fixture,
    notebook_line_audit,
    unit_clock_fixture,
)
from scripts.run_legacy_notebook_smoke import run_smoke


class TestNotebookExecutionAudit(unittest.TestCase):
    def test_line_audit_resolves_receiver_transmitter_order(self) -> None:
        audit = notebook_line_audit()

        self.assertEqual(audit["status"], "verified_compatible")
        answers = audit["answers"]
        self.assertTrue(answers["notebook_model_is_range_plus_transmitter_minus_receiver"])
        self.assertTrue(answers["measurement_vector_order_matches_symbolic_model_vector_order"])
        self.assertTrue(answers["notebook_jacobian_row_order_matches_measurement_order"])
        self.assertTrue(answers["dl_and_sl_rows_have_consistent_ordering"])
        self.assertTrue(answers["package_row_order_matches_notebook_row_order_when_links_are_supplied_as_receiver_transmitter"])

    def test_deterministic_fixture_matches_hand_notebook_and_package(self) -> None:
        fixture = deterministic_fixture()

        self.assertEqual(fixture["status"], "verified_compatible")
        self.assertEqual(
            fixture["notebook_links_receiver_transmitter"],
            [(1, 2), (1, 3), (1, 4), (2, 1), (2, 3), (2, 4)],
        )
        hand = np.asarray(fixture["hand_measurements_km"], dtype=float)
        notebook = np.asarray(fixture["notebook_extracted_measurements_km"], dtype=float)
        package = np.asarray(fixture["package_measurements_km"], dtype=float)
        self.assertTrue(np.allclose(hand, notebook))
        self.assertTrue(np.allclose(hand, package))
        self.assertTrue(fixture["swapped_receiver_transmitter_detected"])
        self.assertTrue(fixture["inverted_clock_sign_detected"])

    def test_unit_clock_fixture_has_one_c_conversion_and_sigma_squared_covariance(self) -> None:
        fixture = unit_clock_fixture()

        self.assertEqual(fixture["status"], "verified_compatible")
        self.assertAlmostEqual(fixture["meters_seconds_model_m"], fixture["km_range_clock_model_m"])
        self.assertAlmostEqual(fixture["round_trip_seconds"], fixture["clock_sigma_seconds"])
        sigma_km = fixture["clock_sigma_seconds"] * C_KM_PER_S
        self.assertAlmostEqual(fixture["clock_sigma_km"], sigma_km)
        self.assertEqual(
            fixture["covariance_diag_km2"],
            [sigma_km**2, (2.0 * sigma_km) ** 2],
        )
        self.assertNotAlmostEqual(fixture["sampling_scale_km"], fixture["sqrt_sigma_would_be_wrong_km"])
        self.assertTrue(fixture["no_double_c_multiplication"])

    def test_active_package_code_has_no_clock_std_sqrt_sampling_pattern(self) -> None:
        root = Path(__file__).resolve().parents[1]
        active_paths = list((root / "jcls_sim").glob("*.py")) + [
            root / "scripts" / "run_v24_figures_4_7.py",
        ]
        joined = "\n".join(path.read_text(encoding="utf-8") for path in active_paths)

        self.assertNotIn("sqrt(clock_std_dev_km", joined)
        self.assertNotIn("sqrt(clock_std", joined)

    def test_meters_seconds_direct_formula_matches_fixture_sign(self) -> None:
        rx = np.array([1200.0, -3400.0, 800.0])
        tx = np.array([-500.0, 900.0, 2300.0])
        rx_clock_s = 2.5e-7
        tx_clock_s = -1.75e-7

        expected = np.linalg.norm(rx - tx) + C_M_PER_S * (tx_clock_s - rx_clock_s)
        fixture = unit_clock_fixture()

        self.assertAlmostEqual(expected, fixture["meters_seconds_model_m"])

    def test_safe_legacy_smoke_executes_selected_class_cells_only(self) -> None:
        smoke = run_smoke()

        self.assertEqual(smoke["status"], "executable_smoke_passed")
        self.assertFalse(smoke["notebook_source_modified"])
        self.assertFalse(smoke["full_notebook_executed"])
        self.assertFalse(smoke["figure_outputs_written"])
        self.assertEqual(smoke["links_receiver_transmitter"], [(1, 2), (1, 3), (1, 4), (2, 1), (2, 3), (2, 4)])
        self.assertLess(smoke["max_abs_z_minus_h_km"], 1.0e-9)
        self.assertEqual(smoke["jacobian_shape"][0], smoke["measurement_count"])
        self.assertIn("IL", smoke["optimizer_results"])
        self.assertIn("LM", smoke["optimizer_results"])
        self.assertIn("EKF", smoke["optimizer_results"])


if __name__ == "__main__":
    unittest.main()
