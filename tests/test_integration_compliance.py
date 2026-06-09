import json
import unittest
from pathlib import Path

from scripts.check_protected_files import protected_reason


class IntegrationComplianceTests(unittest.TestCase):
    def test_protected_file_patterns(self) -> None:
        self.assertIsNotNone(protected_reason("JCLS_Simulation.ipynb"))
        self.assertIsNotNone(protected_reason("Work-In-Progress/foo.pdf"))
        self.assertIsNotNone(protected_reason("Response-Letter-V24.tex"))
        self.assertIsNone(protected_reason("outputs/reports/example.json"))
        self.assertIsNone(protected_reason("outputs/c7_candidate_figures/plots/example.pdf"))

    def test_integration_reports_parse(self) -> None:
        required = [
            Path("outputs/reports/BRANCH_INTEGRATION_INVENTORY.json"),
            Path("outputs/reports/INTEGRATION_COMPLIANCE_REPORT.json"),
            Path("outputs/reports/MERGE_DISCIPLINE_POLICY.json"),
            Path("outputs/reports/INTEGRATION_COMPLIANCE_TASK_MATRIX.json"),
        ]
        for path in required:
            self.assertTrue(path.exists(), f"Missing report: {path}")
            json.loads(path.read_text(encoding="utf-8"))

    def test_inventory_has_required_branch_fields(self) -> None:
        path = Path("outputs/reports/BRANCH_INTEGRATION_INVENTORY.json")
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertIn("branches", data)
        self.assertGreater(len(data["branches"]), 0)
        required_fields = {
            "branch_name",
            "latest_commit",
            "pushed_status",
            "primary_purpose",
            "merge_status",
            "disposition",
            "disposition_reason",
            "modifies_manuscript_or_protected",
        }
        for branch in data["branches"]:
            self.assertTrue(required_fields.issubset(branch.keys()))
            self.assertIn(
                branch["disposition"],
                {
                    "merge_now",
                    "merge_after_minor_fix",
                    "park_do_not_merge_yet",
                    "superseded_do_not_merge",
                    "quarantine_do_not_merge",
                    "already_merged",
                    "unknown_needs_human_review",
                },
            )

    def test_policy_requires_merge_disposition(self) -> None:
        text = Path("outputs/reports/MERGE_DISCIPLINE_POLICY.md").read_text(encoding="utf-8")
        self.assertIn("not complete merely because a branch was pushed", text)
        self.assertIn("quarantined_do_not_merge", text)
        self.assertIn("protected-file", text.lower())


if __name__ == "__main__":
    unittest.main()
