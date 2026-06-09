import json
import subprocess
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
            Path("outputs/reports/ACTIVE_BRANCH_LEDGER.json"),
            Path("outputs/reports/BRANCH_INTEGRATION_INVENTORY.json"),
            Path("outputs/reports/INTEGRATION_COMPLIANCE_REPORT.json"),
            Path("outputs/reports/MERGE_DISCIPLINE_POLICY.json"),
            Path("outputs/reports/INTEGRATION_COMPLIANCE_TASK_MATRIX.json"),
            Path("outputs/reports/BRANCH_CLEANUP_AND_PR_REPORT.json"),
        ]
        for path in required:
            self.assertTrue(path.exists(), f"Missing report: {path}")
            json.loads(path.read_text(encoding="utf-8"))

    def test_inventory_has_required_branch_fields(self) -> None:
        path = Path("outputs/reports/ACTIVE_BRANCH_LEDGER.json")
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertIn("branches", data)
        self.assertGreater(len(data["branches"]), 0)
        required_fields = {
            "branch_name",
            "local_remote_state",
            "latest_commit",
            "ancestor_of_main",
            "unique_commits_not_on_main",
            "open_pr",
            "pr_status",
            "active_worktree",
            "disposition",
            "disposition_reason",
            "risk_class",
            "science_readiness",
            "protected_file_risk",
            "result_lineage_status",
            "units_status",
            "merge_condition",
            "delete_condition",
            "next_action",
        }
        for branch in data["branches"]:
            self.assertTrue(required_fields.issubset(branch.keys()))
            self.assertIn(
                branch["disposition"],
                {
                    "merged_delete_safe",
                    "parked_keep",
                    "quarantined_keep",
                    "superseded_delete_safe",
                    "open_pr_review",
                    "needs_human_review",
                    "unknown_blocked",
                },
            )
            self.assertTrue(branch["next_action"])

    def test_policy_requires_merge_disposition(self) -> None:
        text = Path("outputs/reports/MERGE_DISCIPLINE_POLICY.md").read_text(encoding="utf-8")
        self.assertIn("not complete merely because a branch was pushed", text)
        self.assertIn("quarantined_keep", text)
        self.assertIn("PR status", text)
        self.assertIn("ACTIVE_BRANCH_LEDGER", text)
        self.assertIn("protected-file", text.lower())

    def test_cleanup_report_exists_and_records_pr_status(self) -> None:
        path = Path("outputs/reports/BRANCH_CLEANUP_AND_PR_REPORT.json")
        self.assertTrue(path.exists(), "Missing branch cleanup report")
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertIn("pull_requests_closed", data)
        self.assertIn("branches_deleted_locally", data)
        self.assertIn("branches_deleted_remotely", data)

    def test_active_branch_ledger_matches_git_refs(self) -> None:
        ledger = json.loads(Path("outputs/reports/ACTIVE_BRANCH_LEDGER.json").read_text(encoding="utf-8"))
        ledger_branches = {entry["branch_name"] for entry in ledger["branches"]}
        output = subprocess.check_output(
            ["git", "for-each-ref", "--format=%(refname:short)", "refs/heads", "refs/remotes/origin"],
            text=True,
        )
        git_branches = set()
        for raw_name in output.splitlines():
            name = raw_name.strip()
            if not name or name in {"main", "origin", "origin/HEAD", "origin/main"}:
                continue
            if name.startswith("origin/"):
                name = name[len("origin/") :]
            git_branches.add(name)
        self.assertEqual(ledger_branches, git_branches)

    def test_active_branch_ledger_invariants(self) -> None:
        ledger = json.loads(Path("outputs/reports/ACTIVE_BRANCH_LEDGER.json").read_text(encoding="utf-8"))
        for entry in ledger["branches"]:
            self.assertTrue(entry["disposition"], entry["branch_name"])
            self.assertTrue(entry["next_action"], entry["branch_name"])
            if entry["disposition"] == "quarantined_keep":
                self.assertNotEqual(entry["risk_class"], "unknown", entry["branch_name"])
            if entry["disposition"] == "parked_keep":
                self.assertTrue(entry["merge_condition"], entry["branch_name"])
            if entry["disposition"] == "superseded_delete_safe":
                self.assertTrue(entry["delete_condition"], entry["branch_name"])

    def test_existing_reports_point_to_active_branch_ledger(self) -> None:
        reports = [
            Path("outputs/reports/BRANCH_INTEGRATION_INVENTORY.md"),
            Path("outputs/reports/BRANCH_CLEANUP_AND_PR_REPORT.md"),
            Path("outputs/reports/INTEGRATION_COMPLIANCE_REPORT.md"),
        ]
        for path in reports:
            text = path.read_text(encoding="utf-8")
            self.assertIn("ACTIVE_BRANCH_LEDGER.md", text, str(path))


if __name__ == "__main__":
    unittest.main()
