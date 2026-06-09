# Merge Discipline Policy

A Codex task is not complete merely because a branch was pushed.

Every task branch must end with one explicit disposition:

- `already_merged_close_delete`
- `open_pr_needed`
- `merge_directly_if_safe`
- `park_keep_branch`
- `quarantine_keep_branch`
- `superseded_close_delete`
- `needs_human_review`
- `unknown`

A branch with unique work must either be merged, have an open PR, or be recorded as parked, quarantined, superseded, or awaiting human review with a reason. A pushed branch alone is not a complete task disposition.

Final responses must include:

```text
Branch:
Commit:
Pushed:
PR:
PR status:
Merged to main:
Merge commit:
If not merged, disposition:
Reason not merged:
If branch remains open, why:
If branch deleted, deletion confirmation:
Tests:
Protected-file check:
Reports/outputs:
Next action:
```

Output-producing branches must include pipeline/units/readiness metadata before they are discussed as evidence or considered for merge.

Protected-file changes must be checked with:

```powershell
python scripts/check_protected_files.py --base main --target HEAD --fail-on-protected
```
