# Merge Discipline Policy

A Codex task is not complete merely because a branch was pushed.

The canonical live branch-status source is [ACTIVE_BRANCH_LEDGER.md](ACTIVE_BRANCH_LEDGER.md) and [ACTIVE_BRANCH_LEDGER.json](ACTIVE_BRANCH_LEDGER.json). Update it whenever branch state changes.

Every active branch must have one explicit disposition:

- `merged_delete_safe`
- `parked_keep`
- `quarantined_keep`
- `superseded_delete_safe`
- `open_pr_review`
- `needs_human_review`
- `unknown_blocked`

A branch with unique work must either be merged, have an open PR, or be recorded as parked, quarantined, superseded, needing human review, or blocked with a reason. A pushed branch alone is not a complete task disposition.

Final responses for branch-related work must include current main before/after, working tree status, PR status, PRs opened/closed/merged, branches deleted local/remote, parked/quarantined/human-review branches, protected-file check, tests, reports updated, and whether `ACTIVE_BRANCH_LEDGER` was updated.

Protected-file changes must be checked with:

```powershell
python scripts/check_protected_files.py --base main --target HEAD --fail-on-protected
```
