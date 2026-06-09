"""Check branch diffs for protected sat-sim/manuscript-adjacent files."""

from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


PROTECTED_PATTERNS = (
    "JCLS_Simulation.ipynb",
    "*.tex",
    "*.bib",
    "*Response-Letter*",
    "Response-Letter*",
    "Work-In-Progress/*",
    "All-Version-Archive/*",
    "PSFrag/*",
    "Generated-Figures/*",
    "generated-manuscript/*",
)

PROTECTED_EXTENSIONS_OUTSIDE_OUTPUTS = (".eps",)


@dataclass(frozen=True)
class ProtectedFileChange:
    status: str
    path: str
    reason: str


def _run_git(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


def changed_files(base: str, target: str) -> list[tuple[str, str]]:
    """Return ``(status, path)`` entries changed between base and target."""
    output = _run_git(["diff", "--name-status", f"{base}...{target}"])
    entries: list[tuple[str, str]] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0]
        path = parts[-1].replace("\\", "/")
        entries.append((status, path))
    return entries


def protected_reason(path: str) -> str | None:
    """Return the protection reason for a path, or ``None`` when allowed."""
    normalized = path.replace("\\", "/")
    if normalized.startswith("outputs/"):
        return None
    for pattern in PROTECTED_PATTERNS:
        if fnmatch.fnmatch(normalized, pattern):
            return f"matches protected pattern {pattern}"
    suffix = Path(normalized).suffix.lower()
    if suffix in PROTECTED_EXTENSIONS_OUTSIDE_OUTPUTS:
        return f"protected generated-figure extension {suffix}"
    return None


def find_protected_changes(base: str, target: str) -> list[ProtectedFileChange]:
    """Return protected changes between base and target."""
    protected: list[ProtectedFileChange] = []
    for status, path in changed_files(base, target):
        reason = protected_reason(path)
        if reason:
            protected.append(ProtectedFileChange(status=status, path=path, reason=reason))
    return protected


def build_report(base: str, target: str) -> dict[str, object]:
    """Build a machine-readable protected-file report."""
    protected = find_protected_changes(base, target)
    return {
        "base": base,
        "target": target,
        "protected_change_count": len(protected),
        "protected_changes": [asdict(change) for change in protected],
        "passed": not protected,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="main", help="Base ref for comparison.")
    parser.add_argument("--target", default="HEAD", help="Target ref for comparison.")
    parser.add_argument("--json", action="store_true", help="Emit JSON only.")
    parser.add_argument(
        "--fail-on-protected",
        action="store_true",
        help="Exit nonzero when protected changes are detected.",
    )
    args = parser.parse_args(argv)

    report = build_report(args.base, args.target)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"Protected-file check: {args.base}...{args.target}")
        if report["passed"]:
            print("PASS: no protected-file changes detected.")
        else:
            print(f"FAIL: {report['protected_change_count']} protected change(s) detected.")
            for change in report["protected_changes"]:
                print(f"- {change['status']} {change['path']}: {change['reason']}")

    if args.fail_on_protected and not report["passed"]:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
