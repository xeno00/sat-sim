import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_MD = ROOT / "outputs" / "reports" / "RESULT_VERSION_LINEAGE_AND_UNITS_REVIEW.md"
REPORT_JSON = ROOT / "outputs" / "reports" / "RESULT_VERSION_LINEAGE_AND_UNITS_REVIEW.json"
REGISTRY_MD = ROOT / "outputs" / "registry" / "RESULT_REGISTRY.md"


class ResultLineageUnitsReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(REPORT_MD.exists(), str(REPORT_MD))
        self.assertTrue(REPORT_JSON.exists(), str(REPORT_JSON))
        self.payload = json.loads(REPORT_JSON.read_text(encoding="utf-8"))

    def test_report_and_registry_exist_and_parse(self) -> None:
        self.assertEqual(self.payload["artifact_status"], "result_version_lineage_and_units_review")
        self.assertTrue(REGISTRY_MD.exists(), str(REGISTRY_MD))
        self.assertGreater(REPORT_MD.stat().st_size, 0)
        self.assertGreater(REGISTRY_MD.stat().st_size, 0)

    def test_every_registered_family_has_pipeline_versions(self) -> None:
        required = [
            "result_family",
            "system_model_version",
            "stage_a_version",
            "stage_b_version",
            "stage_c_version",
        ]
        for family in self.payload["result_families"]:
            for key in required:
                self.assertIn(key, family)
                self.assertNotIn(family[key], ("", None), f"{family['result_family']} missing {key}")

    def test_every_registered_family_has_units_and_use_status(self) -> None:
        allowed_units = {
            "units_consistent",
            "units_consistent_but_legacy",
            "units_uncertain",
            "suspect_m_to_km",
            "suspect_clock_seconds_to_range",
            "suspect_noise_double_conversion",
            "blocking_units_mismatch",
        }
        allowed_readiness = {
            "safe_to_cite",
            "use_for_human_review",
            "diagnostic_only",
            "legacy_reference_only",
            "quarantine_until_reconciled",
            "do_not_use",
        }
        allowed_recommended = {
            "use_for_human_review",
            "use_for_debugging_only",
            "legacy_reference_only",
            "quarantine_until_reconciled",
            "do_not_use",
        }
        for family in self.payload["result_families"]:
            self.assertIn(family["units_status"], allowed_units, family["result_family"])
            self.assertIn(family["readiness"], allowed_readiness, family["result_family"])
            self.assertIn(family["recommended_use"], allowed_recommended, family["result_family"])

    def test_required_result_families_are_covered(self) -> None:
        families = {family["result_family"] for family in self.payload["result_families"]}
        required = {
            "original_notebook_manuscript_results",
            "legacy_clock_sweep_replay",
            "legacy_network_size_replay",
            "legacy_crlb_los_replay",
            "step_b_lm_only_results",
            "c7_residual_cov_sync_safeguard",
            "c7_candidate_figure_validation",
            "c7_manuscript_figure_recreation",
            "wave_results_exploration",
            "package_native_suspect_fig4_7_outputs",
            "gnss_baseline_exploration",
        }
        self.assertTrue(required.issubset(families), sorted(required - families))

    def test_contradictory_c7_pipelines_are_explicitly_flagged(self) -> None:
        contradiction_ids = {item["contradiction_id"] for item in self.payload["contradictions"]}
        self.assertIn("c7_centimeter_vs_manuscript_recreation_meter_scale", contradiction_ids)
        self.assertIn("legacy_clock_sweep_good_behavior_vs_c7_clock_sweep_instability", contradiction_ids)

    def test_units_review_has_required_verdicts(self) -> None:
        verdicts = {item["unit_risk_verdict"] for item in self.payload["units_review"]}
        self.assertIn("units_consistent", verdicts)
        self.assertIn("units_consistent_but_legacy", verdicts)
        self.assertIn("units_uncertain", verdicts)


if __name__ == "__main__":
    unittest.main()
