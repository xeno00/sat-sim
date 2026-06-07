import csv
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

from scripts.regress_v24_crlb_figures import (
    DEFAULT_CSV_NAME,
    DEFAULT_JSON_NAME,
    DEFAULT_NPZ_NAME,
    build_crlb_figure_family_regression,
    write_crlb_figure_family_regression,
)


class TestV24CrlbFigureFamilyRegression(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="v24_crlb_regression_test_"))

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_repeated_runs_are_deterministic(self) -> None:
        first = build_crlb_figure_family_regression(base_seed=20260606)
        second = build_crlb_figure_family_regression(base_seed=20260606)

        self.assertEqual(first, second)

    def test_schema_is_non_final_and_contains_two_families(self) -> None:
        payload = build_crlb_figure_family_regression(base_seed=20260606)

        self.assertEqual(payload["diagnostic_type"], "non_final_v24_crlb_figure_family_regression")
        self.assertTrue(payload["non_final"])
        self.assertFalse(payload["manuscript_figure"])
        self.assertFalse(payload["notebook_executed"])
        self.assertIn("package-native V24 full-gauged FIM/bounds", payload["regression_policy"])
        self.assertEqual(
            {"localization_crlb", "synchronization_crlb"},
            {family["family_id"] for family in payload["figure_families"]},
        )

    def test_rank_deficient_rows_have_no_finite_values(self) -> None:
        payload = build_crlb_figure_family_regression(base_seed=20260606)
        rows = [row for family in payload["figure_families"] for row in family["rows"]]
        finite_rows = [row for row in rows if row["finite_mask"]]
        unavailable_rows = [row for row in rows if row["unavailable_mask"]]

        self.assertGreater(len(finite_rows), 0)
        self.assertGreater(len(unavailable_rows), 0)
        for row in finite_rows:
            self.assertEqual(row["plot_value_status"], "finite")
            self.assertIsNotNone(row["finite_bound_value"])
            self.assertFalse(row["unavailable_mask"])
        for row in unavailable_rows:
            self.assertIsNone(row["finite_bound_value"])
            self.assertIsNone(row["finite_bound_unit"])
            self.assertFalse(row["finite_mask"])
            if row["rank_deficient_mask"]:
                self.assertEqual(row["crlb_status"], "rank_deficient_diagnostic")

    def test_rank_and_nullity_fields_are_consistent(self) -> None:
        payload = build_crlb_figure_family_regression(base_seed=20260606)

        for family in payload["figure_families"]:
            for row in family["rows"]:
                self.assertEqual(row["fim_nullity"], row["parameter_dim"] - row["fim_rank"])
                self.assertEqual(row["unknown_count"], row["parameter_dim"])

    def test_write_outputs_creates_json_csv_and_npz(self) -> None:
        payload = write_crlb_figure_family_regression(
            self.temp_dir,
            base_seed=20260606,
            overwrite=True,
        )

        json_path = self.temp_dir / DEFAULT_JSON_NAME
        csv_path = self.temp_dir / DEFAULT_CSV_NAME
        npz_path = self.temp_dir / DEFAULT_NPZ_NAME
        self.assertTrue(json_path.exists())
        self.assertTrue(csv_path.exists())
        self.assertTrue(npz_path.exists())
        self.assertEqual(str(json_path.as_posix()), payload["written_outputs"]["json"])

        written_json = json.loads(json_path.read_text(encoding="utf-8"))
        self.assertEqual(written_json["row_count"], payload["row_count"])
        with csv_path.open("r", newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), payload["row_count"])

        arrays = np.load(npz_path)
        self.assertEqual(arrays["finite_bound_value"].shape, (payload["row_count"],))
        self.assertEqual(arrays["finite_mask"].shape, (payload["row_count"],))
        self.assertTrue(np.any(arrays["finite_mask"]))
        self.assertTrue(np.any(arrays["unavailable_mask"]))
        self.assertTrue(np.all(np.isnan(arrays["finite_bound_value"][arrays["unavailable_mask"]])))

    def test_no_overwrite_refuses_existing_outputs(self) -> None:
        write_crlb_figure_family_regression(
            self.temp_dir,
            base_seed=20260606,
            overwrite=True,
        )

        with self.assertRaises(FileExistsError):
            write_crlb_figure_family_regression(
                self.temp_dir,
                base_seed=20260606,
                overwrite=False,
            )

    def test_no_notebook_import_is_used(self) -> None:
        build_crlb_figure_family_regression(base_seed=20260606)

        self.assertNotIn("JCLS_Simulation", set(sys.modules))


if __name__ == "__main__":
    unittest.main()
