import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_MD = ROOT / "outputs" / "reports" / "RESULT_VERSION_LINEAGE_AND_UNITS_REVIEW.md"
REPORT_JSON = ROOT / "outputs" / "reports" / "RESULT_VERSION_LINEAGE_AND_UNITS_REVIEW.json"
REGISTRY_MD = ROOT / "outputs" / "registry" / "RESULT_REGISTRY.md"
REGISTRY_JSON = ROOT / "outputs" / "registry" / "RESULT_REGISTRY.json"
PRIMARY_STANDARD_CASE_ID = "std_nu3_ns10_fullmesh_los_clock1us_seed0"
SECONDARY_LOW_SAT_CASE_ID = "std_nu3_ns4_fullmesh_los_clock1us_seed0"


class ResultLineageUnitsReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(REPORT_MD.exists(), str(REPORT_MD))
        self.assertTrue(REPORT_JSON.exists(), str(REPORT_JSON))
        self.payload = json.loads(REPORT_JSON.read_text(encoding="utf-8"))

    def test_report_and_registry_exist_and_parse(self) -> None:
        self.assertEqual(self.payload["artifact_status"], "result_version_lineage_and_units_review")
        self.assertTrue(REGISTRY_MD.exists(), str(REGISTRY_MD))
        self.assertTrue(REGISTRY_JSON.exists(), str(REGISTRY_JSON))
        json.loads(REGISTRY_JSON.read_text(encoding="utf-8"))
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

    def test_primary_standard_case_is_nu3_ns10(self) -> None:
        self.assertEqual(self.payload["standard_case_id"], PRIMARY_STANDARD_CASE_ID)
        self.assertEqual(self.payload["primary_standard_case_id"], PRIMARY_STANDARD_CASE_ID)
        text = REPORT_MD.read_text(encoding="utf-8")
        self.assertIn(f"Standard benchmark label: `{PRIMARY_STANDARD_CASE_ID}`", text)
        self.assertNotIn(f"Standard benchmark label: `{SECONDARY_LOW_SAT_CASE_ID}`", text)

    def test_registry_uses_primary_standard_case_fields(self) -> None:
        registry = json.loads(REGISTRY_JSON.read_text(encoding="utf-8"))
        self.assertEqual(registry["primary_standard_case_id"], PRIMARY_STANDARD_CASE_ID)
        self.assertIn("result_families", registry)
        for family in registry["result_families"]:
            self.assertIn("primary_standard_case_id", family)
            self.assertIn("primary_standard_status", family)
            self.assertEqual(family["primary_standard_case_id"], PRIMARY_STANDARD_CASE_ID)

    def test_old_nu3_ns4_case_is_secondary_only(self) -> None:
        self.assertEqual(
            self.payload["secondary_low_satellite_stress_case"]["case_id"],
            SECONDARY_LOW_SAT_CASE_ID,
        )
        self.assertEqual(
            self.payload["secondary_low_satellite_stress_case"]["role"],
            "secondary_low_satellite_stress_case",
        )
        for family in self.payload["result_families"]:
            self.assertEqual(family["secondary_low_sat_case_id"], SECONDARY_LOW_SAT_CASE_ID)
            self.assertEqual(family["secondary_low_sat_case_role"], "secondary_low_satellite_stress_case")
            self.assertNotEqual(family["standard_case_id"], SECONDARY_LOW_SAT_CASE_ID)

    def test_primary_values_are_not_silent_nu3_ns4_substitutions(self) -> None:
        by_family = {family["result_family"]: family for family in self.payload["result_families"]}
        step_b = by_family["step_b_lm_only_results"]
        self.assertEqual(step_b["primary_standard_status"], "missing_needs_benchmark_run")
        self.assertIsNone(step_b["primary_standard_stage_b_pos_m"])
        self.assertEqual(step_b["secondary_low_sat_status"], "available")
        self.assertIsNotNone(step_b["secondary_low_sat_stage_b_pos_m"])

    def test_contradiction_notes_secondary_low_satellite_anchor(self) -> None:
        c7 = next(
            item
            for item in self.payload["contradictions"]
            if item["contradiction_id"] == "c7_centimeter_vs_manuscript_recreation_meter_scale"
        )
        joined = " ".join(str(value) for value in c7.values())
        self.assertIn("secondary low-satellite stress case", joined)
        self.assertIn(PRIMARY_STANDARD_CASE_ID, joined)


if __name__ == "__main__":
    unittest.main()
