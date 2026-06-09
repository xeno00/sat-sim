"""Focused tests for the minimal corrected legacy-compatible JCLS runner."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "minimal_legacy_corrected_jcls.py"
OUTPUT_ROOT = ROOT / "outputs" / "minimal_legacy_corrected"
NOTEBOOK = ROOT / "JCLS_Simulation.ipynb"


class MinimalLegacyCorrectedTests(unittest.TestCase):
    """Validate the minimal corrected legacy runner contract."""

    def test_script_exists(self) -> None:
        self.assertTrue(SCRIPT.exists())

    def test_primary_standard_case_can_be_listed_without_execution(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--list-plan", "--mode", "primary"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
        self.assertIn("rows=1", result.stdout)
        self.assertIn("std_nu3_ns10_fullmesh_los_clock1us_seed0", result.stdout)

    def test_sparse_manuscript_can_be_listed_without_execution(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--list-plan", "--mode", "sparse-manuscript"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
        self.assertIn("sparse_network_nu3_ns4_clock1us_seed0", result.stdout)
        self.assertIn("sparse_clock_nu3_ns10_clock1e-09s_seed0", result.stdout)

    def test_metadata_truth_flags_are_corrected(self) -> None:
        metadata = json.loads((OUTPUT_ROOT / "metadata.json").read_text(encoding="utf-8"))
        self.assertTrue(metadata["truth_used_for_prior_construction"])
        self.assertTrue(metadata["truth_used_for_offline_metrics"])
        self.assertFalse(metadata["truth_used_for_initialization"])
        self.assertFalse(metadata["truth_used_for_lm_acceptance"])
        self.assertFalse(metadata["truth_used_for_step_c_acceptance"])
        self.assertFalse(metadata["truth_used_for_covariance"])
        self.assertFalse(metadata["truth_used_for_fallback_or_reversion"])
        self.assertFalse(metadata["truth_use_blocker"])

    def test_output_schema_has_all_required_stages_and_missing_reasons(self) -> None:
        with (OUTPUT_ROOT / "raw.csv").open(encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 1)
        row = rows[0]
        for stage in ["initialization", "step_a", "step_b", "step_c"]:
            self.assertIn(f"{stage}_localization_error_m", row)
            self.assertIn(f"{stage}_synchronization_error_ns", row)
            self.assertIn(f"{stage}_stage_success", row)
            self.assertIn(f"{stage}_failure_reason", row)
        self.assertEqual(row["initialization_synchronization_error_ns"], "")
        self.assertNotEqual(row["initialization_failure_reason"], "")

    def test_sparse_output_schema_is_planned(self) -> None:
        output = subprocess.check_output(
            [sys.executable, str(SCRIPT), "--list-plan", "--mode", "sparse-manuscript"],
            cwd=ROOT,
            text=True,
        )
        self.assertIn("sparse_network", output)
        self.assertIn("sparse_clock", output)

    def test_json_metadata_and_manifest_parse(self) -> None:
        for relative in ["metadata.json", "PIPELINE_MANIFEST.json"]:
            payload = json.loads((OUTPUT_ROOT / relative).read_text(encoding="utf-8"))
            self.assertFalse(payload["manuscript_ready"])

    def test_outputs_stay_under_minimal_legacy_corrected_root(self) -> None:
        metadata = json.loads((OUTPUT_ROOT / "metadata.json").read_text(encoding="utf-8"))
        for key in ["raw_csv", "summary_csv", "trace_jsonl"]:
            self.assertTrue(metadata[key].startswith("outputs/minimal_legacy_corrected/"))

    def test_original_notebook_is_not_modified(self) -> None:
        self.assertTrue(NOTEBOOK.exists())
        changed = subprocess.check_output(["git", "diff", "--name-only", "HEAD"], cwd=ROOT, text=True)
        self.assertNotIn("JCLS_Simulation.ipynb", changed)


if __name__ == "__main__":
    unittest.main()
