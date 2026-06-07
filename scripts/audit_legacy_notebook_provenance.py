"""Audit legacy notebook provenance without executing notebook code.

The audit is diagnostic-only. It parses ``JCLS_Simulation.ipynb`` as JSON,
classifies cells by keyword categories, and writes a compact non-final report
under ``v24_diagnostics/``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


SAT_SIM_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NOTEBOOK_PATH = SAT_SIM_ROOT / "JCLS_Simulation.ipynb"
DEFAULT_OUTPUT_PATH = SAT_SIM_ROOT / "v24_diagnostics" / "legacy_notebook_provenance_audit.json"

KEYWORD_CATEGORIES: dict[str, list[str]] = {
    "crlb_fim_bound": [
        "CRLB",
        "FIM",
        "Fisher",
        "FIM_loc",
        "FIM_clock",
        "np.linalg.inv(FIM",
        "np.linalg.pinv(FIM",
        "J.T @ np.linalg.inv",
    ],
    "figure_output": [
        "savefig",
        "display_heatmap",
        "ieee_flexible_plot",
        "plot_heatmap",
        "plt.figure",
        ".pdf",
        ".eps",
        "title=",
    ],
    "gauge_or_all_clock_risk": [
        "master_clock_id = 1",
        "rm_clock_params",
        "delta_indices",
        "np.delete",
        "delete",
        "clock_indices",
        "symbolic_parameter_vector",
        "FIM_loc",
        "FIM_clock",
        "scenario.num_users+scenario.num_satellites",
    ],
    "synchronization_metric": [
        "calculate_average_clock_error",
        "sync_errors",
        "sync_mat",
        "Average clock",
        "Average synchronization",
        "clock error",
        "clock offset",
    ],
    "workspace_persistence": [
        "save_workspace",
        "load_workspace",
        "pickle",
        "MyDrive",
        "workspace.pkl",
    ],
}


def _load_notebook(path: str | Path) -> dict[str, Any]:
    """Load a notebook JSON object without executing it."""

    resolved = Path(path)
    return json.loads(resolved.read_text(encoding="utf-8"))


def _cell_source(cell: dict[str, Any]) -> str:
    """Return a notebook cell source string."""

    source = cell.get("source", "")
    if isinstance(source, list):
        return "".join(str(part) for part in source)
    return str(source)


def _matched_categories(source: str) -> dict[str, list[str]]:
    """Return matched keyword categories for a source string."""

    matches: dict[str, list[str]] = {}
    lower_source = source.lower()
    for category, keywords in KEYWORD_CATEGORIES.items():
        matched = [
            keyword
            for keyword in keywords
            if keyword.lower() in lower_source
        ]
        if matched:
            matches[category] = matched
    return matches


def _risk_level(categories: dict[str, list[str]]) -> str:
    """Return a deterministic provenance risk level from matched categories."""

    category_names = set(categories)
    if "crlb_fim_bound" in category_names and "gauge_or_all_clock_risk" in category_names:
        return "high"
    if "crlb_fim_bound" in category_names and "figure_output" in category_names:
        return "high"
    if "figure_output" in category_names and "synchronization_metric" in category_names:
        return "medium"
    if "workspace_persistence" in category_names:
        return "medium"
    if category_names:
        return "low"
    return "none"


def _excerpt(source: str, max_length: int = 280) -> str:
    """Return a compact one-line excerpt from a cell source."""

    squashed = re.sub(r"\s+", " ", source).strip()
    if len(squashed) <= max_length:
        return squashed
    return squashed[: max_length - 3] + "..."


def audit_notebook_cells(notebook: dict[str, Any]) -> list[dict[str, Any]]:
    """Return provenance audit entries for notebook cells with matched categories."""

    audited_cells = []
    for index, cell in enumerate(notebook.get("cells", [])):
        source = _cell_source(cell)
        categories = _matched_categories(source)
        if not categories:
            continue
        audited_cells.append(
            {
                "cell_index": index,
                "cell_type": cell.get("cell_type", "unknown"),
                "execution_count_present": cell.get("execution_count") is not None,
                "matched_categories": categories,
                "risk_level": _risk_level(categories),
                "excerpt": _excerpt(source),
            }
        )
    return audited_cells


def _count_by_key(items: list[dict[str, Any]], key: str) -> dict[str, int]:
    """Count audit entries by a string key."""

    counts: dict[str, int] = {}
    for item in items:
        value = str(item[key])
        counts[value] = counts.get(value, 0) + 1
    return counts


def _category_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    """Count cells matched by category."""

    counts = {category: 0 for category in KEYWORD_CATEGORIES}
    for item in items:
        for category in item["matched_categories"]:
            counts[category] += 1
    return counts


def build_legacy_notebook_provenance_audit(
    notebook_path: str | Path = DEFAULT_NOTEBOOK_PATH,
) -> dict[str, Any]:
    """Return a non-final provenance audit for the legacy notebook."""

    path = Path(notebook_path)
    raw_bytes = path.read_bytes()
    notebook = json.loads(raw_bytes.decode("utf-8"))
    cells = notebook.get("cells", [])
    audited_cells = audit_notebook_cells(notebook)
    high_risk_cells = [cell for cell in audited_cells if cell["risk_level"] == "high"]
    return {
        "diagnostic_type": "non_final_legacy_notebook_provenance_audit",
        "schema_version": 1,
        "generated_marker": "deterministic_no_timestamp",
        "non_final": True,
        "notebook_executed": False,
        "manuscript_figure": False,
        "notebook_path": str(path.as_posix()),
        "notebook_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "total_cell_count": len(cells),
        "matched_cell_count": len(audited_cells),
        "risk_counts": _count_by_key(audited_cells, "risk_level"),
        "category_counts": _category_counts(audited_cells),
        "legacy_notebook_crlb_paths_status": (
            "unsafe_until_package_native_replacement"
            if high_risk_cells
            else "needs_human_review"
        ),
        "high_risk_cell_indices": [cell["cell_index"] for cell in high_risk_cells],
        "figure_or_crlb_cell_indices": [
            cell["cell_index"]
            for cell in audited_cells
            if (
                "figure_output" in cell["matched_categories"]
                or "crlb_fim_bound" in cell["matched_categories"]
            )
        ],
        "audit_policy": (
            "Static notebook JSON audit only; no notebook execution, no figure "
            "generation, and no manuscript output writes."
        ),
        "cells": audited_cells,
    }


def write_legacy_notebook_provenance_audit(
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    *,
    notebook_path: str | Path = DEFAULT_NOTEBOOK_PATH,
    overwrite: bool = True,
) -> Path:
    """Build and write the non-final legacy notebook provenance audit."""

    payload = build_legacy_notebook_provenance_audit(notebook_path)
    resolved = Path(output_path)
    if resolved.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite diagnostic output: {resolved}")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return resolved


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--notebook", type=Path, default=DEFAULT_NOTEBOOK_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--no-overwrite", action="store_true")
    return parser.parse_args()


def main() -> int:
    """Run the legacy notebook provenance audit."""

    args = _parse_args()
    output_path = write_legacy_notebook_provenance_audit(
        args.output,
        notebook_path=args.notebook,
        overwrite=not args.no_overwrite,
    )
    print(f"Wrote non-final legacy notebook provenance audit: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
