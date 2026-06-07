import sys
import unittest

from scripts.prepare_v24_crlb_figure_candidate import (
    build_crlb_figure_candidate_data,
)


class TestV24CrlbFigureCandidateData(unittest.TestCase):
    def test_repeated_runs_are_deterministic(self) -> None:
        first = build_crlb_figure_candidate_data(base_seed=1234)
        second = build_crlb_figure_candidate_data(base_seed=1234)

        self.assertEqual(first, second)

    def test_schema_is_non_final_and_figure_free(self) -> None:
        payload = build_crlb_figure_candidate_data(base_seed=20260606)

        self.assertEqual(payload["diagnostic_type"], "non_final_v24_crlb_figure_candidate_data")
        self.assertIn("no figures generated", payload["output_note"])
        self.assertIn("must not be used as a manuscript figure", payload["figure_candidate_policy"])
        self.assertIn("rank_feasibility_heatmap", payload)
        self.assertIn("finite_crlb_vs_ns", payload)
        self.assertIn("fixed_parameter_measurement_addition", payload)

    def test_rank_heatmap_matrices_match_axes(self) -> None:
        payload = build_crlb_figure_candidate_data(base_seed=20260606)
        panels = payload["rank_feasibility_heatmap"]["panels"]

        self.assertGreater(len(panels), 0)
        for panel in panels:
            user_axis = panel["num_users_axis"]
            satellite_axis = panel["num_satellites_axis"]
            for matrix_key in (
                "full_rank_matrix",
                "fim_rank_matrix",
                "fim_nullity_matrix",
                "parameter_dim_matrix",
            ):
                matrix = panel[matrix_key]
                self.assertEqual(len(matrix), len(user_axis))
                for row in matrix:
                    self.assertEqual(len(row), len(satellite_axis))

    def test_finite_crlb_series_masks_unavailable_points(self) -> None:
        payload = build_crlb_figure_candidate_data(base_seed=20260606)
        series = payload["finite_crlb_vs_ns"]["series"]

        self.assertFalse(payload["finite_crlb_vs_ns"]["monotonicity_claim_valid"])
        self.assertGreater(len(series), 0)
        saw_unavailable = False
        saw_finite = False
        for item in series:
            statuses = item["plot_value_status"]
            unavailable_mask = item["unavailable_mask"]
            self.assertEqual(len(statuses), len(unavailable_mask))
            for index, status in enumerate(statuses):
                is_unavailable = unavailable_mask[index]
                self.assertEqual(is_unavailable, status != "finite")
                if is_unavailable:
                    saw_unavailable = True
                    self.assertIsNone(item["average_ue_peb_km"][index])
                    self.assertIsNone(item["average_clock_bound_s"][index])
                else:
                    saw_finite = True
                    self.assertIsNotNone(item["average_ue_peb_km"][index])
                    self.assertIsNotNone(item["average_clock_bound_s"][index])
        self.assertTrue(saw_unavailable)
        self.assertTrue(saw_finite)

    def test_fixed_measurement_addition_masks_rank_deficient_values(self) -> None:
        payload = build_crlb_figure_candidate_data(base_seed=20260606)
        fixed = payload["fixed_parameter_measurement_addition"]

        self.assertTrue(fixed["recommended_as_sanity_check"])
        self.assertEqual(len(fixed["measurement_count"]), len(fixed["unavailable_mask"]))
        for index, unavailable in enumerate(fixed["unavailable_mask"]):
            if unavailable:
                self.assertIsNone(fixed["average_ue_peb_km"][index])
                self.assertIsNone(fixed["average_clock_bound_s"][index])
            else:
                self.assertIsNotNone(fixed["average_ue_peb_km"][index])
                self.assertIsNotNone(fixed["average_clock_bound_s"][index])

    def test_no_notebook_import_is_used(self) -> None:
        build_crlb_figure_candidate_data(base_seed=20260606)

        self.assertNotIn("JCLS_Simulation", set(sys.modules))


if __name__ == "__main__":
    unittest.main()
