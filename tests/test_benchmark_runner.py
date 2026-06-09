"""Tests for normalized standard benchmark-card runner."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jcls_sim.benchmark.runner import benchmark_card_row, run_benchmark_cards
from jcls_sim.benchmark.standard_cases import PRIMARY_STANDARD_CASE_ID, primary_standard_case


class BenchmarkRunnerTests(unittest.TestCase):
    """Verify benchmark-card runner semantics."""

    def test_runner_includes_all_pipeline_ids_with_missing_reasons(self) -> None:
        """Runner emits all registered pipelines and explicit unavailable reasons."""

        cards = run_benchmark_cards(
            case_id=PRIMARY_STANDARD_CASE_ID,
            selected_pipeline_ids=("legacy_surgical_prior_region", "controlled_migration_step_b_lm_only"),
        )

        self.assertEqual([card.pipeline.pipeline_id for card in cards], ["legacy_surgical_prior_region", "controlled_migration_step_b_lm_only"])
        for card in cards:
            row = benchmark_card_row(card)
            self.assertEqual(row["case_id"], PRIMARY_STANDARD_CASE_ID)
            self.assertFalse(row["step_a_available"])
            self.assertTrue(row["step_a_missing_reason"])

    def test_package_native_card_preserves_truth_and_stage_schema(self) -> None:
        """Package-native C7 card has every checkpoint field when adapter is patched."""

        fake_result = run_benchmark_cards(
            case_id=PRIMARY_STANDARD_CASE_ID,
            selected_pipeline_ids=("legacy_surgical_prior_region",),
        )[0].result
        with patch("jcls_sim.benchmark.runner.run_pipeline", return_value=fake_result):
            card = run_benchmark_cards(
                case_id=PRIMARY_STANDARD_CASE_ID,
                selected_pipeline_ids=("legacy_surgical_prior_region",),
            )[0]
        row = benchmark_card_row(card)

        self.assertIn("initialization_pos_error_m", row)
        self.assertIn("step_a_pos_error_m", row)
        self.assertIn("step_b_pos_error_m", row)
        self.assertIn("step_c_pos_error_m", row)
        self.assertIn("truth_usage_summary", row)

    def test_list_plan_does_not_create_outputs(self) -> None:
        """The CLI defaults to no-execution list-plan behavior."""

        with tempfile.TemporaryDirectory() as temp_dir:
            output_root = Path(temp_dir) / "cards"
            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/run_standard_benchmark_cards.py",
                    "--list-plan",
                    "--output-root",
                    str(output_root),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertIn(primary_standard_case().case_id, completed.stdout)
            self.assertFalse(output_root.exists())


if __name__ == "__main__":
    unittest.main()
