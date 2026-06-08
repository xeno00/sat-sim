"""Render non-final diagnostic/replay PDFs into a browsable plot gallery.

Only PDFs under sat-sim diagnostic output roots are considered. Manuscript,
PSFrag, Work-In-Progress, and original notebook artifacts outside those roots
are deliberately excluded.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SAT_SIM_ROOT = Path(__file__).resolve().parents[1]
GALLERY_ROOT = SAT_SIM_ROOT / "outputs" / "gallery"
PREVIEW_ROOT = GALLERY_ROOT / "previews"
SOURCE_ROOTS = [
    SAT_SIM_ROOT / "outputs" / "legacy_replay",
    SAT_SIM_ROOT / "outputs" / "package_diagnostic",
    SAT_SIM_ROOT / "outputs" / "manuscript_candidate",
    SAT_SIM_ROOT / "outputs" / "human_review",
    SAT_SIM_ROOT / "outputs" / "migration_baseline",
    SAT_SIM_ROOT / "outputs" / "migration_ladder",
    SAT_SIM_ROOT / "v24_notebook_regression_outputs",
    SAT_SIM_ROOT / "v24_human_review_outputs",
    SAT_SIM_ROOT / "v24_manuscript_candidate_outputs",
    SAT_SIM_ROOT / "v24_figure_outputs",
]
FORBIDDEN_PATH_PARTS = {
    "Work-In-Progress",
    "GeneratePSFrag",
    "PSFrag",
}


def _sha256(path: Path) -> str:
    """Return SHA256 for a file."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _repo_rel(path: Path) -> str:
    """Return a repo-relative path with URL-friendly separators."""

    return path.relative_to(SAT_SIM_ROOT).as_posix()


def _gallery_rel(path: Path) -> str:
    """Return a gallery-relative path with URL-friendly separators."""

    return path.relative_to(GALLERY_ROOT).as_posix()


def _link_from_gallery(repo_relative_path: str) -> str:
    """Return a link target from gallery files to a repo-relative path."""

    if repo_relative_path.startswith("outputs/"):
        return f"../{repo_relative_path.removeprefix('outputs/')}"
    return f"../../{repo_relative_path}"


def _git_value(args: list[str]) -> str | None:
    """Return a git value when available."""

    try:
        result = subprocess.run(
            ["git", *args],
            cwd=SAT_SIM_ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return result.stdout.strip() or None


def _git_metadata() -> dict[str, str | None]:
    """Return branch/commit metadata for gallery provenance."""

    return {
        "branch": _git_value(["rev-parse", "--abbrev-ref", "HEAD"]),
        "commit": _git_value(["rev-parse", "--short", "HEAD"]),
    }


def _safe_stem(path: Path) -> str:
    """Return a filesystem-safe stem derived from a repo-relative path."""

    relative = path.relative_to(SAT_SIM_ROOT)
    text = "__".join(relative.with_suffix("").parts)
    safe = "".join(char if char.isalnum() or char in "._-" else "_" for char in text)
    digest = hashlib.sha256(str(relative).encode("utf-8")).hexdigest()[:12]
    if len(safe) > 90:
        safe = safe[-90:]
    return f"{digest}__{safe}"


def _find_pdfs() -> list[Path]:
    """Find eligible diagnostic PDFs."""

    pdfs: list[Path] = []
    for root in SOURCE_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*.pdf"):
            relative_parts = set(path.relative_to(SAT_SIM_ROOT).parts)
            if relative_parts & FORBIDDEN_PATH_PARTS:
                continue
            pdfs.append(path)
    return sorted(set(pdfs))


def _group_for(path: Path) -> str:
    """Classify a PDF into a gallery group."""

    text = _repo_rel(path).lower()
    if "outputs/legacy_replay/crlb_los" in text:
        return "legacy CRLB replay"
    if "outputs/legacy_replay/crlb_nlos" in text:
        return "NLOS CRLB status"
    if "outputs/legacy_replay/network_size_full" in text:
        return "legacy network-size full"
    if "outputs/legacy_replay/network_size_medium" in text:
        return "legacy network-size medium"
    if "outputs/legacy_replay/network_size" in text:
        return "legacy network-size smoke"
    if "outputs/migration_baseline" in text:
        return "migration baseline"
    if "outputs/migration_ladder" in text:
        return "controlled migration ladder"
    if "outputs/legacy_replay/clock_sweep_full" in text:
        return "legacy clock-sweep full"
    if "crlb_replay" in text:
        return "legacy CRLB replay"
    if "clock_sweep_replay_full" in text:
        return "legacy clock-sweep full"
    if "clock_sweep_replay" in text:
        return "legacy clock-sweep smoke"
    if "v24_human_review_outputs" in text:
        return "human-review"
    if "v24_manuscript_candidate_outputs" in text:
        return "manuscript-candidate"
    if "v24_figure_outputs" in text:
        return "package diagnostic"
    return "failed/not-reproduced figures"


def _load_status_by_figure() -> dict[str, dict[str, Any]]:
    """Load known figure statuses from the regression table."""

    table_path = SAT_SIM_ROOT / "v24_notebook_regression_outputs" / "FIGURE_REGRESSION_TABLE.json"
    if not table_path.exists():
        return {}
    table = json.loads(table_path.read_text(encoding="utf-8"))
    return {
        entry["figure"]: entry
        for entry in table.get("target_figure_statuses", [])
        if "figure" in entry
    }


def _nearby_metadata(path: Path) -> list[str]:
    """Return nearby JSON metadata files as repo-relative paths."""

    candidates = [
        item
        for item in path.parent.glob("*.json")
        if item.name.lower().endswith(("metadata.json", "report.json", "manifest.json"))
        or "metadata" in item.name.lower()
        or "report" in item.name.lower()
    ]
    return [_repo_rel(item) for item in sorted(candidates)]


def _nearby_raw_data(path: Path) -> list[str]:
    """Return nearby raw data artifacts as repo-relative paths."""

    candidates: list[Path] = []
    for pattern in ("*.csv", "*.npz"):
        candidates.extend(path.parent.glob(pattern))
    return [_repo_rel(item) for item in sorted(candidates)]


def _pdftoppm() -> str:
    """Return the available pdftoppm executable."""

    exe = shutil.which("pdftoppm")
    if exe is None:
        raise RuntimeError("pdftoppm was not found; TeX Live/Poppler PDF rendering is required.")
    return exe


def _render_pdf(path: Path, *, force: bool) -> tuple[list[Path], dict[str, Any]]:
    """Render a PDF into PNG previews and write per-PDF metadata."""

    PREVIEW_ROOT.mkdir(parents=True, exist_ok=True)
    stem = _safe_stem(path)
    prefix = PREVIEW_ROOT / stem
    metadata_path = PREVIEW_ROOT / f"{stem}.json"
    before = set(PREVIEW_ROOT.glob(f"{stem}-*.png"))
    current_hash = _sha256(path)
    if not force and metadata_path.exists():
        existing = json.loads(metadata_path.read_text(encoding="utf-8"))
        previews = [GALLERY_ROOT / item for item in existing.get("preview_paths", [])]
        if existing.get("source_pdf_sha256") == current_hash and all(item.exists() for item in previews):
            return previews, existing

    for old in before:
        old.unlink()
    try:
        subprocess.run(
            [_pdftoppm(), "-png", "-r", "160", str(path), str(prefix)],
            cwd=SAT_SIM_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as error:
        metadata = {
            "source_pdf_path": _repo_rel(path),
            "source_pdf_sha256": current_hash,
            "source_pdf_size_bytes": path.stat().st_size,
            "preview_paths": [],
            "preview_count": 0,
            "metadata_path": _gallery_rel(metadata_path),
            "render_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "render_status": "failed",
            "render_error": error.stderr or error.stdout or str(error),
            **_git_metadata(),
        }
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        return [], metadata
    previews = sorted(PREVIEW_ROOT.glob(f"{stem}-*.png"))
    metadata = {
        "source_pdf_path": _repo_rel(path),
        "source_pdf_sha256": current_hash,
        "source_pdf_size_bytes": path.stat().st_size,
        "preview_paths": [_gallery_rel(item) for item in previews],
        "preview_count": len(previews),
        "metadata_path": _gallery_rel(metadata_path),
        "render_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "render_status": "rendered",
        **_git_metadata(),
    }
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return previews, metadata


def _entry_for(path: Path, metadata: dict[str, Any], status_by_figure: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Build a gallery entry for one PDF."""

    status = status_by_figure.get(path.name, {})
    group = _group_for(path)
    manuscript_ready = bool(status.get("manuscript_ready", False))
    warning = status.get("reason") or (
        "Diagnostic-only output; not marked manuscript-ready."
        if not manuscript_ready
        else "Human-review artifact."
    )
    return {
        "figure_name": path.name,
        "group": group,
        "source_pdf_path": _repo_rel(path),
        "preview_paths": metadata["preview_paths"],
        "metadata_path": metadata["metadata_path"],
        "raw_data_paths": _nearby_raw_data(path),
        "nearby_metadata_paths": _nearby_metadata(path),
        "status": status.get("status", "diagnostic_output"),
        "manuscript_ready": manuscript_ready,
        "warning": warning,
        "render_status": metadata.get("render_status", "unknown"),
        "render_error": metadata.get("render_error"),
        "source_pdf_sha256": metadata["source_pdf_sha256"],
        "source_pdf_size_bytes": metadata["source_pdf_size_bytes"],
    }


def _missing_target_entries(status_by_figure: dict[str, dict[str, Any]], rendered_figures: set[str]) -> list[dict[str, Any]]:
    """Return status-only entries for target figures without rendered PDFs."""

    entries: list[dict[str, Any]] = []
    for figure_name, status in sorted(status_by_figure.items()):
        if figure_name in rendered_figures:
            continue
        entries.append(
            {
                "figure_name": figure_name,
                "group": "failed/not-reproduced figures",
                "source_pdf_path": None,
                "preview_paths": [],
                "metadata_path": None,
                "raw_data_paths": [],
                "nearby_metadata_paths": [],
                "status": status.get("status", "not_rendered"),
                "manuscript_ready": bool(status.get("manuscript_ready", False)),
                "warning": status.get("reason", "No eligible diagnostic PDF exists for this target figure."),
                "render_status": "not_rendered",
                "render_error": "No eligible diagnostic PDF exists for this target figure.",
                "source_pdf_sha256": None,
                "source_pdf_size_bytes": None,
            }
        )
    return entries


def _write_gallery(entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Write JSON, Markdown, and HTML gallery files."""

    GALLERY_ROOT.mkdir(parents=True, exist_ok=True)
    groups = sorted({entry["group"] for entry in entries})
    payload = {
        "artifact_status": "non_final_plot_gallery",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_roots": [_repo_rel(root) for root in SOURCE_ROOTS],
        "entry_count": len(entries),
        "groups": groups,
        "entries": entries,
        **_git_metadata(),
    }
    (GALLERY_ROOT / "PLOT_GALLERY.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    md_lines = [
        "# V24 Plot Gallery",
        "",
        "## Executive Summary",
        "This gallery renders non-final diagnostic and legacy-replay PDFs as PNG previews. No entry here is automatically manuscript-ready.",
        "",
        f"- Generated entries: {len(entries)}",
        f"- Generated at: {payload['generated_at_utc']}",
        "",
    ]
    for group in groups:
        md_lines.extend([f"## {group}", ""])
        for entry in [item for item in entries if item["group"] == group]:
            source_line = (
                f"- Source PDF: [{entry['source_pdf_path']}]({_link_from_gallery(entry['source_pdf_path'])})"
                if entry["source_pdf_path"]
                else "- Source PDF: `not rendered`"
            )
            md_lines.extend(
                [
                    f"### {entry['figure_name']}",
                    "",
                    f"- Status: `{entry['status']}`",
                    f"- Manuscript ready: `{entry['manuscript_ready']}`",
                    source_line,
                    f"- Warning: {entry['warning']}",
                    "",
                ]
            )
            for preview in entry["preview_paths"]:
                md_lines.append(f"![{entry['figure_name']}]({preview})")
            if entry["metadata_path"]:
                md_lines.append(f"- Preview metadata: [{entry['metadata_path']}]({entry['metadata_path']})")
            if entry["raw_data_paths"]:
                md_lines.append("- Raw data:")
                for raw_path in entry["raw_data_paths"]:
                    md_lines.append(f"  - [{raw_path}]({_link_from_gallery(raw_path)})")
            if entry["nearby_metadata_paths"]:
                md_lines.append("- Nearby metadata:")
                for metadata_path in entry["nearby_metadata_paths"]:
                    md_lines.append(f"  - [{metadata_path}]({_link_from_gallery(metadata_path)})")
            md_lines.append("")
    (GALLERY_ROOT / "PLOT_GALLERY.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    html_parts = [
        "<!doctype html>",
        "<html><head><meta charset='utf-8'><title>V24 Plot Gallery</title>",
        "<style>body{font-family:Arial,sans-serif;margin:24px;} .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:18px;} .card{border:1px solid #ccc;padding:12px;} img{max-width:100%;height:auto;border:1px solid #ddd;} code{word-break:break-all;} .warn{color:#7a4b00;}</style>",
        "</head><body>",
        "<h1>V24 Plot Gallery</h1>",
        "<p>Non-final previews of generated/replayed diagnostic PDFs.</p>",
    ]
    for group in groups:
        html_parts.append(f"<h2>{html.escape(group)}</h2><div class='grid'>")
        for entry in [item for item in entries if item["group"] == group]:
            html_parts.append("<div class='card'>")
            html_parts.append(f"<h3>{html.escape(entry['figure_name'])}</h3>")
            html_parts.append(f"<p>Status: <code>{html.escape(str(entry['status']))}</code><br>Manuscript ready: <code>{entry['manuscript_ready']}</code></p>")
            html_parts.append(f"<p class='warn'>{html.escape(str(entry['warning']))}</p>")
            for preview in entry["preview_paths"]:
                html_parts.append(f"<img src='{html.escape(preview)}' alt='{html.escape(entry['figure_name'])}'>")
            if entry["source_pdf_path"]:
                href = _link_from_gallery(entry["source_pdf_path"])
                html_parts.append(f"<p>Source: <a href='{html.escape(href)}'>{html.escape(entry['source_pdf_path'])}</a></p>")
            else:
                html_parts.append("<p>Source: <code>not rendered</code></p>")
            if entry["raw_data_paths"]:
                html_parts.append("<p>Raw data:<br>" + "<br>".join(f"<a href='{html.escape(_link_from_gallery(path))}'>{html.escape(path)}</a>" for path in entry["raw_data_paths"]) + "</p>")
            html_parts.append("</div>")
        html_parts.append("</div>")
    html_parts.append("</body></html>")
    (GALLERY_ROOT / "PLOT_GALLERY.html").write_text("\n".join(html_parts), encoding="utf-8")
    return payload


def render_gallery(*, force: bool = False) -> dict[str, Any]:
    """Render all eligible PDFs and update the plot gallery."""

    status_by_figure = _load_status_by_figure()
    entries = []
    newly_rendered: list[str] = []
    for pdf in _find_pdfs():
        previews, metadata = _render_pdf(pdf, force=force)
        entry = _entry_for(pdf, metadata, status_by_figure)
        entries.append(entry)
        newly_rendered.extend(_gallery_rel(path) for path in previews)
    entries.extend(_missing_target_entries(status_by_figure, {entry["figure_name"] for entry in entries}))
    payload = _write_gallery(entries)
    payload["preview_pngs"] = newly_rendered
    return payload


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Re-render even when cached previews match PDF hashes.")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    payload = render_gallery(force=args.force)
    print(json.dumps({
        "gallery": str((GALLERY_ROOT / "PLOT_GALLERY.html").relative_to(SAT_SIM_ROOT)).replace("\\", "/"),
        "entry_count": payload["entry_count"],
        "preview_count": sum(len(entry["preview_paths"]) for entry in payload["entries"]),
        "preview_pngs": payload["preview_pngs"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
