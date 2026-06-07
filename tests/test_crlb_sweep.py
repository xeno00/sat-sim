import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

from jcls_sim.gauge import expected_v24_parameter_dim
from scripts.sweep_v24_crlb import (
    DEFAULT_SATELLITE_COUNTS,
    build_v24_crlb_sweep_diagnostics,
    case_seed,
    write_v24_crlb_sweep_diagnostics,
)


class TestV24CrlbMiniSweep(unittest.TestCase):
    def test_repeated_runs_with_same_base_seed_are_identical(self) -> None:
        first = build_v24_crlb_sweep_diagnostics(base_seed=12345)
        second = build_v24_crlb_sweep_diagnostics(base_seed=12345)

        self.assertEqual(first, second)

    def test_one_case_per_requested_satellite_count(self) -> None:
        satellite_counts = (2, 4, 6)

        payload = build_v24_crlb_sweep_diagnostics(
            base_seed=100,
            satellite_counts=satellite_counts,
        )

        self.assertEqual(payload["sweep_axis"], "num_satellites")
        self.assertEqual(payload["satellite_counts"], list(satellite_counts))
        self.assertEqual([case["num_satellites"] for case in payload["cases"]], list(satellite_counts))
        self.assertEqual(len(payload["cases"]), len(satellite_counts))

    def test_case_dimensions_and_required_fields(self) -> None:
        payload = build_v24_crlb_sweep_diagnostics(base_seed=2026)

        self.assertEqual(payload["diagnostic_type"], "non_final_v24_full_gauged_crlb_ns_sweep")
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["num_users"], 2)
        self.assertEqual(len(payload["cases"]), len(DEFAULT_SATELLITE_COUNTS))
        self.assertTrue(payload["legacy_static_risk_notes"])

        for case in payload["cases"]:
            num_users = payload["num_users"]
            num_satellites = case["num_satellites"]
            expected_dim = expected_v24_parameter_dim(num_users, num_satellites)

            self.assertEqual(case["seed"], case_seed(payload["base_seed"], num_satellites))
            self.assertEqual(case["parameter_dim"], expected_dim)
            self.assertEqual(case["expected_parameter_dim"], expected_dim)
            self.assertEqual(case["fim_shape"], [expected_dim, expected_dim])
            self.assertEqual(case["measurement_count"], 2 * num_satellites + 1)
            self.assertEqual(case["unknown_count"], expected_dim)
            self.assertIsInstance(case["fim_rank"], int)
            self.assertEqual(case["fim_nullity"], expected_dim - case["fim_rank"])
            self.assertIn(case["covariance_method"], {"inverse", "pinv"})
            self.assertIsInstance(case["covariance_rank"], int)
            self.assertIn("covariance_condition_number", case)
            self.assertIn("fim_min_eigenvalue", case)
            self.assertIn(
                case["manuscript_crlb_status"],
                {
                    "finite_full_rank",
                    "finite_estimable_subspace_rank_deficient",
                    "undefined_rank_deficient",
                },
            )
            self.assertIsInstance(case["manuscript_bounds_defined"], bool)
            self.assertIn("runtime_seconds", case)

    def test_bounds_are_finite_and_nonnegative(self) -> None:
        payload = build_v24_crlb_sweep_diagnostics(base_seed=54321)

        for case in payload["cases"]:
            bound_keys = (
                "average_ue_peb_km",
                "average_clock_bound_km",
                "average_ue_clock_bound_km",
                "average_non_reference_satellite_clock_bound_km",
            )
            for key in bound_keys:
                self.assertTrue(np.isfinite(case[key]), msg=f"{key} was not finite")
                self.assertGreaterEqual(case[key], 0.0, msg=f"{key} was negative")

    def test_rank_deficient_cases_are_not_manuscript_reportable(self) -> None:
        payload = build_v24_crlb_sweep_diagnostics(base_seed=20260606)

        for case in payload["cases"]:
            if case["fim_nullity"] == 0:
                self.assertTrue(case["manuscript_bounds_defined"])
                self.assertEqual(case["manuscript_crlb_status"], "finite_full_rank")
                self.assertEqual(case["manuscript_average_ue_peb_km"], case["average_ue_peb_km"])
                self.assertEqual(case["manuscript_average_clock_bound_km"], case["average_clock_bound_km"])
            else:
                self.assertFalse(case["manuscript_bounds_defined"])
                self.assertEqual(case["manuscript_crlb_status"], "undefined_rank_deficient")
                self.assertIsNone(case["manuscript_average_ue_peb_km"])
                self.assertIsNone(case["manuscript_average_clock_bound_km"])

    def test_json_writer_refuses_overwrite_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "sweep.json"

            written = write_v24_crlb_sweep_diagnostics(output, base_seed=777)
            first_text = output.read_text(encoding="utf-8")
            loaded = json.loads(first_text)

            self.assertEqual(written, output)
            self.assertEqual(loaded["base_seed"], 777)
            with self.assertRaises(FileExistsError):
                write_v24_crlb_sweep_diagnostics(output, base_seed=777)

            write_v24_crlb_sweep_diagnostics(output, base_seed=777, overwrite=True)
            self.assertEqual(output.read_text(encoding="utf-8"), first_text)

    def test_no_notebook_import_is_used(self) -> None:
        build_v24_crlb_sweep_diagnostics(base_seed=2468)

        imported_modules = set(sys.modules)
        self.assertNotIn("JCLS_Simulation", imported_modules)


if __name__ == "__main__":
    unittest.main()
