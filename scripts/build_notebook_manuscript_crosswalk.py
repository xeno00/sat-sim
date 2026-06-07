"""Build static notebook/manuscript forensic crosswalk reports.

This script does not execute ``JCLS_Simulation.ipynb``. It reads manuscript
source, notebook cell text, package diagnostics, and existing non-final output
artifacts to produce forensic sprint reports under
``v24_notebook_regression_outputs/``.
"""

from __future__ import annotations

import csv
import json
import re
import subprocess
from pathlib import Path
from typing import Any


SAT_SIM_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SAT_SIM_ROOT.parent
OUTPUT_ROOT = SAT_SIM_ROOT / "v24_notebook_regression_outputs"
REPORT_ROOT = OUTPUT_ROOT / "subagent_reports"
FAILURE_ROOT = OUTPUT_ROOT / "failure_logs"
MANUSCRIPT = REPO_ROOT / "Work-In-Progress" / "SCL-NTN-TAES-2025-V24.tex"
NOTEBOOK = SAT_SIM_ROOT / "JCLS_Simulation.ipynb"


def _git_value(*args: str) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=SAT_SIM_ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def _json_write(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _md_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(value).replace("\n", " ") for value in row) + " |")
    return "\n".join(lines)


def _extract_section(text: str, label: str, next_label: str | None = None) -> str:
    start = text.find(label)
    if start < 0:
        return ""
    if next_label:
        end = text.find(next_label, start + len(label))
        if end > start:
            return text[start:end]
    next_section = text.find("\\section", start + len(label))
    if next_section > start:
        return text[start:next_section]
    return text[start:]


def _notebook_cells() -> list[dict[str, Any]]:
    if not NOTEBOOK.exists():
        return []
    notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8", errors="replace"))
    cells = []
    for index, cell in enumerate(notebook.get("cells", [])):
        source = "".join(cell.get("source", []))
        cells.append(
            {
                "index": index,
                "cell_type": cell.get("cell_type"),
                "line_count": source.count("\n") + 1 if source else 0,
                "source": source,
            }
        )
    return cells


def _class_function_inventory(cells: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records = []
    pattern = re.compile(r"^\s*(class|def)\s+([A-Za-z_][A-Za-z0-9_]*)", re.MULTILINE)
    for cell in cells:
        for match in pattern.finditer(cell["source"]):
            records.append(
                {
                    "cell_index": cell["index"],
                    "kind": match.group(1),
                    "name": match.group(2),
                }
            )
    return records


def _keyword_cells(cells: list[dict[str, Any]], keywords: list[str]) -> list[dict[str, Any]]:
    records = []
    for cell in cells:
        source_lower = cell["source"].lower()
        hits = [keyword for keyword in keywords if keyword.lower() in source_lower]
        if hits:
            records.append(
                {
                    "cell_index": cell["index"],
                    "cell_type": cell["cell_type"],
                    "hits": hits,
                    "line_count": cell["line_count"],
                    "snippet": "\n".join(cell["source"].splitlines()[:12]),
                }
            )
    return records


def _artifact_records() -> list[dict[str, Any]]:
    roots = [
        "v24_human_review_outputs",
        "v24_manuscript_candidate_outputs",
        "v24_figure_outputs",
        "v24_diagnostics",
    ]
    records = []
    for root_name in roots:
        root = SAT_SIM_ROOT / root_name
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.suffix.lower() in {".pdf", ".svg", ".png", ".eps", ".json", ".csv", ".npz", ".md"}:
                records.append(
                    {
                        "root": root_name,
                        "path": path.relative_to(SAT_SIM_ROOT).as_posix(),
                        "suffix": path.suffix.lower(),
                        "size_bytes": path.stat().st_size,
                    }
                )
    return records


def _summary_csv_records() -> list[dict[str, Any]]:
    records = []
    for path in sorted(SAT_SIM_ROOT.rglob("*_summary.csv")):
        if "v24_human_review_outputs" not in path.as_posix() and "v24_manuscript_candidate_outputs" not in path.as_posix():
            continue
        try:
            with path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
        except OSError:
            continue
        for row in rows:
            records.append(
                {
                    "source": path.relative_to(SAT_SIM_ROOT).as_posix(),
                    "figure_id": row.get("figure_id"),
                    "baseline_id": row.get("baseline_id"),
                    "x_value": row.get("x_value"),
                    "series_value": row.get("series_value"),
                    "mean": row.get("mean"),
                    "success_rate": row.get("success_rate"),
                    "baseline_observability_reportable": row.get("all_baseline_observability_reportable"),
                    "baseline_observability_nullity": row.get("max_baseline_observability_nullity"),
                }
            )
    return records


def _subagent_report_index() -> list[dict[str, Any]]:
    records = []
    if not REPORT_ROOT.exists():
        return records
    for path in sorted(REPORT_ROOT.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {"parse_error": True}
        records.append(
            {
                "path": path.relative_to(SAT_SIM_ROOT).as_posix(),
                "keys": sorted(payload.keys()),
                "status": payload.get("status", payload.get("verdict", "available")),
            }
        )
    return records


def build_payload() -> dict[str, Any]:
    manuscript = _read_text(MANUSCRIPT)
    section_ii = _extract_section(manuscript, "\\section{Non-Terrestrial Network System Model}", "\\section{Fisher Information Analysis}")
    section_iv = _extract_section(manuscript, "\\section{Algorithm for Joint Cooperative Localization and Synchronization}", "\\section{Numerical Results}")
    section_v = _extract_section(manuscript, "\\section{Numerical Results}")
    cells = _notebook_cells()
    inventory = _class_function_inventory(cells)
    notebook_keywords = _keyword_cells(
        cells,
        [
            "Node",
            "User",
            "Satellite",
            "Datalink",
            "Scenario",
            "Optimizer",
            "initialize_state",
            "rm_clock_params",
            "lm_step",
            "ekf_step",
            "savefig",
            "clock_std",
            "Sigma_z",
            "3e8",
            "1000",
            "CRLB",
        ],
    )
    figure_claims = [
        {"figure": "Fig. 2", "manuscript_label": "fig:pos_crlb", "expected_support": "CRLB localization/network-size code path"},
        {"figure": "Fig. 3", "manuscript_label": "fig:sync_crlb", "expected_support": "CRLB synchronization/network-size code path"},
        {"figure": "Fig. 4", "manuscript_label": "fig:pos_sats", "expected_support": "localization vs satellite count with baselines"},
        {"figure": "Fig. 5", "manuscript_label": "fig:sync_sats", "expected_support": "synchronization vs satellite count with baselines"},
        {"figure": "Fig. 6", "manuscript_label": "fig:pos_clock", "expected_support": "localization vs clock-offset standard deviation"},
        {"figure": "Fig. 7", "manuscript_label": "fig:sync_clock", "expected_support": "synchronization vs clock-offset standard deviation"},
    ]
    return {
        "report_type": "notebook_manuscript_forensic_sprint_payload",
        "branch": _git_value("branch", "--show-current"),
        "commit_hash": _git_value("rev-parse", "HEAD"),
        "manuscript_path": MANUSCRIPT.relative_to(REPO_ROOT).as_posix() if MANUSCRIPT.exists() else None,
        "notebook_path": NOTEBOOK.relative_to(SAT_SIM_ROOT).as_posix() if NOTEBOOK.exists() else None,
        "section_lengths": {
            "section_ii_chars": len(section_ii),
            "section_iv_chars": len(section_iv),
            "section_v_chars": len(section_v),
        },
        "manuscript_system_objects": [
            {"object": "theta", "expected_code_counterpart": "jcls_sim.parameters.pack_v24_theta / V24ScenarioConfig.theta"},
            {"object": "h(theta)", "expected_code_counterpart": "jcls_sim.jacobian.toa_range_vector_from_theta_km"},
            {"object": "R_z", "expected_code_counterpart": "range_std_devs_km -> diag(sigma^2) in FIM/estimators"},
            {"object": "first satellite reference clock", "expected_code_counterpart": "jcls_sim.gauge.reference_satellite_node_id"},
            {"object": "DL/SL graph", "expected_code_counterpart": "jcls_sim.configs.downlink_links / directed_sidelink_links"},
        ],
        "manuscript_algorithm_steps": [
            {"step": "Step 1", "concept": "GN/WNLS downlink-only coarse UE localization"},
            {"step": "Step 2", "concept": "LM/WNLS full gauged V24 theta JCLS"},
            {"step": "Step 3", "concept": "SCI/SFI dynamic information-form update with F,Q,Pi"},
        ],
        "figure_claims": figure_claims,
        "notebook_class_function_inventory": inventory,
        "notebook_keyword_cells": notebook_keywords,
        "artifact_records": _artifact_records(),
        "summary_csv_records": _summary_csv_records(),
        "subagent_reports": _subagent_report_index(),
        "top_risks": [
            "Legacy notebook must not be executed as final provenance until all-clock/gauge behavior is resolved.",
            "Existing human-review package outputs are explicitly not manuscript-ready.",
            "CRLB and Fig. 4--7 pipelines need figure-by-figure support checks before manuscript use.",
        ],
    }


def write_outputs(payload: dict[str, Any]) -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    FAILURE_ROOT.mkdir(parents=True, exist_ok=True)
    _json_write(OUTPUT_ROOT / "MANUSCRIPT_ALGORITHM_MAP.json", payload)
    (OUTPUT_ROOT / "MANUSCRIPT_ALGORITHM_MAP.md").write_text(
        "# Manuscript Algorithm Map\n\n"
        + _md_table(["Step", "Concept"], [[row["step"], row["concept"]] for row in payload["manuscript_algorithm_steps"]])
        + "\n",
        encoding="utf-8",
    )
    notebook_payload = {
        "report_type": "notebook_forensics_report",
        "inventory": payload["notebook_class_function_inventory"],
        "keyword_cells": payload["notebook_keyword_cells"],
        "static_only": True,
        "notebook_executed": False,
    }
    _json_write(OUTPUT_ROOT / "NOTEBOOK_FORENSICS_REPORT.json", notebook_payload)
    (OUTPUT_ROOT / "NOTEBOOK_FORENSICS_REPORT.md").write_text(
        "# Notebook Forensics Report\n\n"
        "Static parse only; `JCLS_Simulation.ipynb` was not executed.\n\n"
        + _md_table(
            ["Cell", "Kind", "Name"],
            [[row["cell_index"], row["kind"], row["name"]] for row in payload["notebook_class_function_inventory"]],
        )
        + "\n",
        encoding="utf-8",
    )
    crosswalk = {
        "report_type": "manuscript_notebook_crosswalk",
        "system_objects": payload["manuscript_system_objects"],
        "algorithm_steps": payload["manuscript_algorithm_steps"],
        "figure_claims": payload["figure_claims"],
        "subagent_reports": payload["subagent_reports"],
        "status": "initial_static_crosswalk_pending_full_human_review",
    }
    _json_write(OUTPUT_ROOT / "MANUSCRIPT_NOTEBOOK_CROSSWALK.json", crosswalk)
    (OUTPUT_ROOT / "MANUSCRIPT_NOTEBOOK_CROSSWALK.md").write_text(
        "# Manuscript/Notebook Crosswalk\n\n"
        "This crosswalk is assembled from static scans and subagent reports. It does not execute the legacy notebook.\n\n"
        + _md_table(
            ["Manuscript object", "Expected code counterpart"],
            [[row["object"], row["expected_code_counterpart"]] for row in payload["manuscript_system_objects"]],
        )
        + "\n\n## Figure Claims\n\n"
        + _md_table(
            ["Figure", "Label", "Required support"],
            [[row["figure"], row["manuscript_label"], row["expected_support"]] for row in payload["figure_claims"]],
        )
        + "\n",
        encoding="utf-8",
    )
    regression = {
        "report_type": "figure_regression_table",
        "static_only": True,
        "notebook_executed": False,
        "summary_records": payload["summary_csv_records"],
        "failure_logs": ["failure_logs/legacy_notebook_not_executed.md"],
    }
    _json_write(OUTPUT_ROOT / "FIGURE_REGRESSION_TABLE.json", regression)
    (OUTPUT_ROOT / "FIGURE_REGRESSION_TABLE.md").write_text(
        "# Figure Regression Table\n\n"
        "Package output summaries are listed below. Legacy notebook reproduction was not attempted because notebook execution is out of scope for this sprint stage.\n\n"
        + _md_table(
            ["Source", "Figure", "Baseline", "x", "Series", "Mean", "Success", "Reportable"],
            [
                [
                    row["source"],
                    row["figure_id"],
                    row["baseline_id"],
                    row["x_value"],
                    row["series_value"],
                    row["mean"],
                    row["success_rate"],
                    row["baseline_observability_reportable"],
                ]
                for row in payload["summary_csv_records"][:200]
            ],
        )
        + "\n",
        encoding="utf-8",
    )
    artifacts = payload["artifact_records"]
    _json_write(OUTPUT_ROOT / "PLOT_GALLERY.json", {"report_type": "plot_gallery", "artifacts": artifacts})
    pdf_svg = [row for row in artifacts if row["suffix"] in {".pdf", ".svg", ".png", ".eps"}]
    (OUTPUT_ROOT / "PLOT_GALLERY.md").write_text(
        "# Plot Gallery\n\n"
        "Existing package-native/non-final plot artifacts. Paths are repo-relative.\n\n"
        + _md_table(
            ["Root", "Path", "Type", "Bytes"],
            [[row["root"], row["path"], row["suffix"], row["size_bytes"]] for row in pdf_svg],
        )
        + "\n",
        encoding="utf-8",
    )
    unit_payload = {
        "report_type": "units_noise_covariance_report",
        "status": "static_scan_plus_subagent_pending",
        "high_risk_terms": ["3e8", "1000", "sigma", "variance", "Sigma_z", "clock_std_dev"],
        "classification": "needs human/code audit before manuscript result use",
    }
    _json_write(OUTPUT_ROOT / "UNITS_NOISE_COVARIANCE_REPORT.json", unit_payload)
    (OUTPUT_ROOT / "UNITS_NOISE_COVARIANCE_REPORT.md").write_text(
        "# Units/Noise/Covariance Report\n\n"
        "Initial status: static scan plus subagent synthesis pending. High-risk terms: `3e8`, `1000`, `sigma`, `variance`, `Sigma_z`, `clock_std_dev`.\n",
        encoding="utf-8",
    )
    gauge_payload = {
        "report_type": "gauge_ab_test_report",
        "status": "static_hypothesis_only",
        "hypothesis": "Legacy notebook all-clock behavior may differ from V24 first-satellite gauged package behavior.",
        "ab_tests_needed": ["all-clock vs gauged theta FIM rank/nullity", "sync metric with/without reference clock"],
    }
    _json_write(OUTPUT_ROOT / "GAUGE_AB_TEST_REPORT.json", gauge_payload)
    (OUTPUT_ROOT / "GAUGE_AB_TEST_REPORT.md").write_text(
        "# Gauge A/B Test Report\n\n"
        "Initial hypothesis: legacy all-clock notebook behavior may differ from V24 first-satellite gauged package behavior. A/B tests remain needed.\n",
        encoding="utf-8",
    )
    baseline_payload = {
        "report_type": "baseline_semantics_report",
        "status": "initial_static_map",
        "baselines": [
            {"baseline": "Without cooperation", "risk": "may ignore clocks or absorb clock bias into position"},
            {"baseline": "Coarse JCLS", "risk": "one-epoch full theta may be weak/ill-conditioned"},
            {"baseline": "Refined JCLS", "risk": "dynamic refinement cannot rescue bad local estimate"},
        ],
    }
    _json_write(OUTPUT_ROOT / "BASELINE_SEMANTICS_REPORT.json", baseline_payload)
    (OUTPUT_ROOT / "BASELINE_SEMANTICS_REPORT.md").write_text(
        "# Baseline Semantics Report\n\n"
        + _md_table(["Baseline", "Risk"], [[row["baseline"], row["risk"]] for row in baseline_payload["baselines"]])
        + "\n",
        encoding="utf-8",
    )
    (FAILURE_ROOT / "legacy_notebook_not_executed.md").write_text(
        "# Legacy Notebook Reproduction Failure Log\n\n"
        "`JCLS_Simulation.ipynb` was intentionally not executed. Static forensic mapping was performed instead. Legacy-compatible reproduction commands remain to be designed after the notebook/code crosswalk is reviewed.\n",
        encoding="utf-8",
    )
    final = {
        "report_type": "notebook_manuscript_regression_sprint_summary",
        "branch": payload["branch"],
        "commit_hash": payload["commit_hash"],
        "subagent_reports": payload["subagent_reports"],
        "outputs": [
            "MANUSCRIPT_ALGORITHM_MAP.md/json",
            "NOTEBOOK_FORENSICS_REPORT.md/json",
            "MANUSCRIPT_NOTEBOOK_CROSSWALK.md/json",
            "FIGURE_REGRESSION_TABLE.md/json",
            "BASELINE_SEMANTICS_REPORT.md/json",
            "UNITS_NOISE_COVARIANCE_REPORT.md/json",
            "GAUGE_AB_TEST_REPORT.md/json",
            "PLOT_GALLERY.md/json",
        ],
        "notebook_executed": False,
        "manuscript_files_edited": False,
    }
    _json_write(OUTPUT_ROOT / "FINAL_SPRINT_SUMMARY.json", final)
    (OUTPUT_ROOT / "FINAL_SPRINT_SUMMARY.md").write_text(
        "# Notebook/Manuscript Regression Sprint Summary\n\n"
        f"- Branch: `{payload['branch']}`\n"
        f"- Commit at report generation: `{payload['commit_hash']}`\n"
        "- Notebook executed: false\n"
        "- Manuscript files edited: false\n"
        "- Status: initial fan-out/fan-in forensic reports generated; human review still required.\n",
        encoding="utf-8",
    )


def main() -> int:
    payload = build_payload()
    write_outputs(payload)
    print(f"wrote forensic sprint outputs under {OUTPUT_ROOT.relative_to(SAT_SIM_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
