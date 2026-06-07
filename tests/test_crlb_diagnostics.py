import sys
import unittest

from jcls_sim.constants import C_KM_PER_S
from scripts.diagnose_v24_crlb_geometry import (
    build_crlb_geometry_diagnostics,
    build_fixed_parameter_information_addition,
    build_growing_ns_diagnostic,
    build_rank_feasibility_grid,
)


class TestV24CrlbGeometryDiagnostics(unittest.TestCase):
    def test_repeated_runs_are_deterministic(self) -> None:
        first = build_crlb_geometry_diagnostics(base_seed=123456)
        second = build_crlb_geometry_diagnostics(base_seed=123456)

        self.assertEqual(first, second)

    def test_fixed_parameter_nested_measurements(self) -> None:
        payload = build_fixed_parameter_information_addition(seed=20260606)
        cases = payload["cases"]
        parameter_dims = {case["parameter_dim"] for case in cases}
        measurement_counts = [case["measurement_count"] for case in cases]
        checked_cases = [case for case in cases if case["monotonicity_checked"]]

        self.assertEqual(len(parameter_dims), 1)
        self.assertTrue(payload["fixed_parameter_dim"])
        self.assertEqual(measurement_counts, sorted(measurement_counts))
        self.assertGreater(len(checked_cases), 0)
        for case in cases:
            self.assertIn(
                case["monotonicity_status"],
                {"pass", "fail", "not_applicable"},
            )
            if case["monotonicity_checked"]:
                self.assertEqual(case["crlb_status"], "finite_crlb")
                self.assertTrue(case["is_full_rank"])
                self.assertEqual(case["monotonicity_status"], "pass")
            else:
                self.assertEqual(case["monotonicity_status"], "not_applicable")

    def test_rank_deficient_cases_are_diagnostic_only(self) -> None:
        payload = build_fixed_parameter_information_addition(seed=20260606)
        rank_deficient_cases = [
            case for case in payload["cases"] if case["fim_nullity"] > 0
        ]

        self.assertGreater(len(rank_deficient_cases), 0)
        for case in rank_deficient_cases:
            self.assertEqual(case["crlb_status"], "rank_deficient_diagnostic")
            self.assertFalse(case["is_manuscript_ready"])
            self.assertFalse(case["manuscript_bounds_defined"])
            self.assertIsNone(case["manuscript_average_ue_peb_km"])
            self.assertIsNone(case["manuscript_average_clock_bound_km"])
            self.assertIsNone(case["manuscript_average_clock_bound_s"])

    def test_growing_ns_metadata_marks_nonmonotonic_interpretation(self) -> None:
        payload = build_growing_ns_diagnostic(seed=20260606)
        dims = [case["parameter_dim"] for case in payload["cases"]]

        self.assertTrue(payload["this_sweep_changes_parameter_dimension"])
        self.assertFalse(payload["monotonic_crlb_interpretation_valid"])
        self.assertIn("not a fixed-parameter", payload["interpretation_warning"])
        self.assertEqual(dims, sorted(dims))
        self.assertGreater(len(set(dims)), 1)
        for case in payload["cases"]:
            self.assertTrue(case["this_case_changes_parameter_dimension"])
            self.assertIn("is_manuscript_ready", case)
            self.assertIn("average_clock_bound_s", case)

    def test_rank_feasibility_grid_required_fields(self) -> None:
        payload = build_rank_feasibility_grid(
            seed=20260606,
            num_users_values=(2,),
            num_satellite_values=(2, 3),
            link_patterns=("dl_only", "all_dl_all_directed_sl"),
        )

        self.assertEqual(len(payload["cases"]), 4)
        for case in payload["cases"]:
            for key in (
                "num_users",
                "num_satellites",
                "link_pattern",
                "measurement_count",
                "parameter_dim",
                "fim_rank",
                "fim_nullity",
                "is_full_rank",
                "crlb_status",
                "notes",
            ):
                self.assertIn(key, case)
            self.assertEqual(case["fim_nullity"], case["parameter_dim"] - case["fim_rank"])

    def test_clock_bound_unit_conversion(self) -> None:
        payload = build_crlb_geometry_diagnostics(base_seed=20260606)
        all_cases = []
        all_cases.extend(payload["fixed_parameter_information_addition"]["cases"])
        all_cases.extend(payload["growing_ns_diagnostic"]["cases"])
        all_cases.extend(payload["rank_feasibility_grid"]["cases"])

        for case in all_cases:
            self.assertAlmostEqual(
                case["average_clock_bound_s"],
                case["average_clock_bound_km"] / C_KM_PER_S,
            )

    def test_no_notebook_import_is_used(self) -> None:
        build_crlb_geometry_diagnostics(base_seed=20260606)

        self.assertNotIn("JCLS_Simulation", set(sys.modules))


if __name__ == "__main__":
    unittest.main()
