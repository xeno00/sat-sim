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
                    "already_merged_close_delete",
                    "open_pr_needed",
                    "merge_directly_if_safe",
                    "park_keep_branch",
                    "quarantine_keep_branch",
                    "superseded_close_delete",
                    "needs_human_review",
                    "unknown",
                },
            )

    def test_policy_requires_merge_disposition(self) -> None:
        text = Path("outputs/reports/MERGE_DISCIPLINE_POLICY.md").read_text(encoding="utf-8")
        self.assertIn("not complete merely because a branch was pushed", text)
        self.assertIn("quarantine_keep_branch", text)
        self.assertIn("PR status", text)
        self.assertIn("protected-file", text.lower())

    def test_cleanup_report_exists_and_records_pr_status(self) -> None:
        path = Path("outputs/reports/BRANCH_CLEANUP_AND_PR_REPORT.json")
        self.assertTrue(path.exists(), "Missing branch cleanup report")
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertIn("pull_requests_closed", data)
        self.assertIn("branches_deleted_locally", data)
        self.assertIn("branches_deleted_remotely", data)


if __name__ == "__main__":
    unittest.main()
