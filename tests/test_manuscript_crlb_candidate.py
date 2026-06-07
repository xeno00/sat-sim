import sys
import unittest

from jcls_sim.constants import C_KM_PER_S
from scripts.diagnose_v24_manuscript_crlb_candidate import (
    build_manuscript_crlb_candidate,
)


class TestV24ManuscriptCrlbCandidate(unittest.TestCase):
    def test_repeated_runs_are_deterministic(self) -> None:
        first = build_manuscript_crlb_candidate(base_seed=24680)
        second = build_manuscript_crlb_candidate(base_seed=24680)

        self.assertEqual(first, second)

    def test_schema_and_case_fields(self) -> None:
        payload = build_manuscript_crlb_candidate(base_seed=20260606)

        self.assertEqual(payload["diagnostic_type"], "non_final_v24_manuscript_crlb_candidate")
        self.assertEqual(payload["candidate_type"], "rank_feasibility_with_finite_bound_summaries")
        self.assertIn("not a manuscript figure", payload["output_note"])
        self.assertIn("Rank-deficient points", payload["unavailable_policy"])
        self.assertGreater(payload["finite_case_count"], 0)
        self.assertGreater(payload["unavailable_case_count"], 0)

        for case in payload["cases"]:
            for key in (
                "num_users",
                "num_satellites",
                "link_pattern",
                "measurement_count",
                "parameter_dim",
                "fim_rank",
                "fim_nullity",
                "crlb_status",
                "is_manuscript_ready",
                "plot_value_status",
            ):
                self.assertIn(key, case)
            self.assertEqual(case["fim_nullity"], case["parameter_dim"] - case["fim_rank"])

    def test_rank_deficient_points_are_unavailable(self) -> None:
        payload = build_manuscript_crlb_candidate(base_seed=20260606)
        unavailable_cases = [
            case for case in payload["cases"] if case["plot_value_status"] == "unavailable_rank_deficient"
        ]

        self.assertGreater(len(unavailable_cases), 0)
        for case in unavailable_cases:
            self.assertEqual(case["crlb_status"], "rank_deficient_diagnostic")
            self.assertFalse(case["is_manuscript_ready"])
            self.assertIsNone(case["average_ue_peb_km"])
            self.assertIsNone(case["average_clock_bound_km"])
            self.assertIsNone(case["average_clock_bound_s"])
            self.assertEqual(case["unavailable_reason"], "rank_deficient_diagnostic")

    def test_finite_points_are_manuscript_ready(self) -> None:
        payload = build_manuscript_crlb_candidate(base_seed=20260606)
        finite_cases = [
            case for case in payload["cases"] if case["plot_value_status"] == "finite"
        ]

        self.assertGreater(len(finite_cases), 0)
        for case in finite_cases:
            self.assertEqual(case["crlb_status"], "finite_crlb")
            self.assertTrue(case["is_full_rank"])
            self.assertTrue(case["is_manuscript_ready"])
            self.assertIsNotNone(case["average_ue_peb_km"])
            self.assertIsNotNone(case["average_clock_bound_km"])
            self.assertIsNotNone(case["average_clock_bound_s"])
            self.assertIsNone(case["unavailable_reason"])

    def test_clock_bound_seconds_conversion(self) -> None:
        payload = build_manuscript_crlb_candidate(base_seed=20260606)

        for case in payload["cases"]:
            if case["plot_value_status"] == "finite":
                self.assertAlmostEqual(
                    case["average_clock_bound_s"],
                    case["average_clock_bound_km"] / C_KM_PER_S,
                )

    def test_minimal_full_rank_table(self) -> None:
        payload = build_manuscript_crlb_candidate(base_seed=20260606)
        rows = payload["minimal_full_rank_table"]

        self.assertGreater(len(rows), 0)
        for row in rows:
            self.assertLessEqual(
                row["min_full_rank_num_satellites"],
                min(row["full_rank_num_satellites"]),
            )
            self.assertEqual(
                row["min_full_rank_num_satellites"],
                min(row["full_rank_num_satellites"]),
            )

    def test_no_notebook_import_is_used(self) -> None:
        build_manuscript_crlb_candidate(base_seed=20260606)

        self.assertNotIn("JCLS_Simulation", set(sys.modules))


if __name__ == "__main__":
    unittest.main()
