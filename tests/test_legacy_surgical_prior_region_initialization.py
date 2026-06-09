import csv
import json
import os
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "legacy_surgical_prior_region_initialization"
REPORTS = ROOT / "outputs" / "reports"


def _exists(path: Path) -> bool:
    if path.exists():
        return True
    resolved = str(path.resolve())
    if os.name == "nt" and not resolved.startswith("\\\\?\\"):
        return os.path.exists("\\\\?\\" + resolved)
    return False


class TestLegacySurgicalPriorRegionInitialization(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        required = [
            OUTPUT / "raw.csv",
            OUTPUT / "summary.csv",
            OUTPUT / "metadata.json",
            OUTPUT / "trace.jsonl",
            OUTPUT / "arrays.npz",
            REPORTS / "LEGACY_SURGICAL_PRIOR_REGION_INITIALIZATION_REPORT.json",
            REPORTS / "LEGACY_SURGICAL_PRIOR_REGION_INITIALIZATION_REPORT.md",
        ]
        missing = [path for path in required if not _exists(path)]
        if missing:
            raise AssertionError(
                "Run scripts/run_legacy_surgical_prior_region_initialization.py first; "
                f"missing {missing}"
            )

    def _raw_rows(self) -> list[dict[str, str]]:
        with (OUTPUT / "raw.csv").open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))

    def _summary_rows(self) -> list[dict[str, str]]:
        with (OUTPUT / "summary.csv").open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))

    def _report(self) -> dict:
        return json.loads((REPORTS / "LEGACY_SURGICAL_PRIOR_REGION_INITIALIZATION_REPORT.json").read_text(encoding="utf-8"))

    def _metadata(self) -> dict:
        return json.loads((OUTPUT / "metadata.json").read_text(encoding="utf-8"))

    def test_prior_region_outputs_exist_and_are_nonfinal(self) -> None:
        report = self._report()
        metadata = self._metadata()

        self.assertFalse(report["manuscript_ready"])
        self.assertTrue(report["non_final_diagnostic"])
        self.assertFalse(metadata["manuscript_ready"])
        self.assertTrue(metadata["non_final_diagnostic"])
        for paths in report["figures"].values():
            if isinstance(paths, list):
                for relative_path in paths:
                    self.assertTrue(_exists(ROOT / relative_path), relative_path)

    def test_prior_region_initialization_exists_and_records_radius(self) -> None:
        rows = [row for row in self._raw_rows() if row["pipeline"] != "legacy_exact_truth_gated"]
        radii = {float(row["prior_radius_m"]) for row in rows}

        self.assertEqual(radii, {10.0, 100.0, 1000.0, 10000.0, 100000.0})
        self.assertTrue(all(row["initializer"] == "coarse_prior_region_initialization" for row in rows))
        self.assertTrue(all(row["prior_mode"] == "prior_ball_R0" for row in rows))
        self.assertTrue(all(float(row["initial_average_position_error_m"]) > 0.0 for row in rows))

    def test_l1_l2_use_truth_only_for_prior_simulation_and_metrics(self) -> None:
        rows = [row for row in self._raw_rows() if row["pipeline"] in {"legacy_nontruth_lm", "legacy_surgical_nontruth"}]

        self.assertGreater(len(rows), 0)
        for row in rows:
            self.assertEqual(row["truth_used_algorithmically"], "False")
            self.assertEqual(row["truth_use_label"], "prior_simulation_and_metrics_only")
            self.assertEqual(row["truth_state_used_for_prior_simulation"], "True")
            self.assertEqual(row["truth_state_used_for_stage_a_acceptance"], "False")
            self.assertEqual(row["truth_state_used_for_lm_acceptance"], "False")
            self.assertEqual(row["truth_state_used_for_map_covariance"], "False")
            self.assertEqual(row["truth_state_used_for_map_acceptance"], "False")
            self.assertEqual(row["truth_state_used_for_metrics"], "True")

    def test_l2_uses_nontruth_residual_scaled_covariance(self) -> None:
        rows = [row for row in self._raw_rows() if row["pipeline"] == "legacy_surgical_nontruth"]

        self.assertGreater(len(rows), 0)
        for row in rows:
            self.assertEqual(row["map_covariance_mode"], "residual_scaled_information_pseudoinverse")
            self.assertEqual(row["map_update_mode"], "observable_residual_covariance_checks")

    def test_standard_cases_and_radii_are_complete(self) -> None:
        expected_cases = {
            "std_nu3_ns10_fullmesh_los_clock1us_seed0",
            "std_nu3_ns10_fullmesh_los_clock10ns_seed0",
            "std_nu3_ns4_fullmesh_los_clock1us_seed0",
        }
        expected_radii = {10.0, 100.0, 1000.0, 10000.0, 100000.0}
        observed = {
            (row["case_id"], row["pipeline"], float(row["prior_radius_m"]))
            for row in self._raw_rows()
            if row["pipeline"] != "legacy_exact_truth_gated"
        }

        for case_id in expected_cases:
            for pipeline in {"legacy_nontruth_lm", "legacy_surgical_nontruth"}:
                for radius in expected_radii:
                    self.assertIn((case_id, pipeline, radius), observed)

    def test_green_decision_and_largest_radius_values(self) -> None:
        report = self._report()

        self.assertEqual(report["decision"], "green")
        self.assertTrue(report["prior_region_initialization_defensible"])
        self.assertEqual(report["largest_stage_b_radius_m_primary"], 100000.0)
        self.assertEqual(report["largest_stage_c_radius_m_primary"], 100000.0)
        self.assertEqual(report["multi_seed_sensitivity"], "not_run; seed 0 only")

    def test_summary_marks_primary_100km_as_manuscript_like(self) -> None:
        rows = [
            row
            for row in self._summary_rows()
            if row["case_id"] == "std_nu3_ns10_fullmesh_los_clock1us_seed0"
            and row["prior_radius_m"] == "100000.0"
        ]

        self.assertEqual({row["pipeline"] for row in rows}, {"legacy_nontruth_lm", "legacy_surgical_nontruth"})
        for row in rows:
            self.assertEqual(row["stage_b_manuscript_like"], "True")
        l2 = [row for row in rows if row["pipeline"] == "legacy_surgical_nontruth"][0]
        self.assertEqual(l2["stage_c_useful"], "True")

    def test_stage_a_patch_source_does_not_call_true_state(self) -> None:
        import inspect
        from scripts.run_legacy_surgical_prior_region_initialization import _install_nontruth_stage_a_completion

        source = inspect.getsource(_install_nontruth_stage_a_completion)
        self.assertNotIn("get_true_state", source)
        self.assertNotIn("true_state", source)

    def test_report_contains_suggested_manuscript_wording_without_editing_manuscript(self) -> None:
        report = self._report()

        self.assertIn("coarse prior region", report["suggested_manuscript_wording"])
        self.assertIn("true state information is not used", report["suggested_manuscript_wording"])

    def test_protected_manuscript_and_notebook_files_are_not_modified(self) -> None:
        diff = subprocess.run(
            ["git", "diff", "--name-only"],
            cwd=ROOT,
            text=True,
            check=True,
            stdout=subprocess.PIPE,
        ).stdout.splitlines()
        protected_fragments = [
            "JCLS_Simulation.ipynb",
            "Work-In-Progress",
            "All-Version-Archive",
            ".tex",
            ".bib",
            ".pdf",
            "PSFrag",
        ]

        offenders = [
            path
            for path in diff
            if any(fragment in path for fragment in protected_fragments)
            and not path.startswith("outputs/legacy_surgical_prior_region_initialization/")
            and not path.startswith("outputs/reports/LEGACY_SURGICAL_PRIOR_REGION")
            and not path.startswith("tests/test_legacy_surgical_prior_region_initialization.py")
        ]
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
