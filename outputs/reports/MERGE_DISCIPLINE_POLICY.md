# Merge Discipline Policy

A Codex task is not complete merely because a branch was pushed.

Every task branch must end with exactly one disposition:

- `merged_to_main`
- `parked_do_not_merge_yet`
- `superseded_do_not_merge`
- `quarantined_do_not_merge`
- `awaiting_human_review`

Final responses must include branch, commit, pushed status, merge status, merge commit if applicable, reason when not merged, tests, protected-file check, reports/outputs, and next action.

Output-producing branches must include pipeline/units/readiness metadata before they are discussed as evidence or considered for merge.

Protected-file changes must be checked with:

```powershell
python scripts/check_protected_files.py --base main --target HEAD --fail-on-protected
```
