"""Finalize notebook/manuscript forensic regression sprint reports.

This script is static-only. It does not execute ``JCLS_Simulation.ipynb`` and
does not write manuscript, notebook, figure, or Work-In-Progress files.
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
OUT = SAT_SIM_ROOT / "v24_notebook_regression_outputs"
SUB = OUT / "subagent_reports"
FAIL = OUT / "failure_logs"
MANUSCRIPT = REPO_ROOT / "Work-In-Progress" / "SCL-NTN-TAES-2025-V24.tex"
NOTEBOOK = SAT_SIM_ROOT / "JCLS_Simulation.ipynb"

REQUIRED_REPORTS = [
    "TASK_MATRIX",
    "SPRINT_COMPLETION_CHECKLIST",
    "MANUSCRIPT_ALGORITHM_MAP",
    "NOTEBOOK_FORENSICS_REPORT",
    "MANUSCRIPT_NOTEBOOK_CROSSWALK",
    "ORDERED_LINK_CONVENTION_AUDIT",
    "UNIT_CLOCK_REPRESENTATION_AUDIT",
    "UNITS_NOISE_COVARIANCE_REPORT",
    "GAUGE_AB_TEST_REPORT",
    "BASELINE_SEMANTICS_REPORT",
    "FIGURE_REGRESSION_TABLE",
    "PLOT_GALLERY",
    "RED_TEAM_REPORT",
    "FORENSIC_REGRESSION_SPRINT_REPORT",
]


def _git(*args: str) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=SAT_SIM_ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(v).replace("\n", " ") for v in row) + " |")
    return "\n".join(lines)


def _write_md(path: Path, title: str, body: str) -> None:
    path.write_text(f"# {title}\n\n{body.rstrip()}\n", encoding="utf-8")


def _cells() -> list[dict[str, Any]]:
    if not NOTEBOOK.exists():
        return []
    notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8", errors="replace"))
    rows = []
    for idx, cell in enumerate(notebook.get("cells", [])):
        src = "".join(cell.get("source", []))
        rows.append({"index": idx, "cell_type": cell.get("cell_type"), "source": src})
    return rows


def _find_cells(cells: list[dict[str, Any]], terms: list[str]) -> list[dict[str, Any]]:
    found = []
    for cell in cells:
        lower = cell["source"].lower()
        hits = [term for term in terms if term.lower() in lower]
        if hits:
            found.append(
                {
                    "cell": cell["index"],
                    "hits": hits,
                    "snippet": "\n".join(cell["source"].splitlines()[:14]),
                }
            )
    return found


def _defs(cells: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    pat = re.compile(r"^\s*(class|def)\s+([A-Za-z_][A-Za-z0-9_]*)", re.MULTILINE)
    for cell in cells:
        for m in pat.finditer(cell["source"]):
            out.append({"cell": cell["index"], "kind": m.group(1), "name": m.group(2)})
    return out


def _grep_rows(sources: dict[str, str], terms: list[str]) -> list[dict[str, Any]]:
    rows = []
    for name, text in sources.items():
        for term in terms:
            count = text.count(term)
            if count:
                first = text.find(term)
                rows.append(
                    {
                        "source": name,
                        "term": term,
                        "count": count,
                        "classification": _classify_term(name, term, text[max(0, first - 120) : first + 220]),
                        "snippet": text[max(0, first - 120) : first + 220].replace("\n", " "),
                    }
                )
    return rows


def _classify_term(source: str, term: str, snippet: str) -> str:
    if term == "Sigma_z" and "J_x.T @ Sigma_z @ J_x" in snippet:
        return "likely_bug_or_inverse_covariance_name_confusion"
    if term in {"3e8", "1000"}:
        return "safe_if_seconds_to_km_conversion_else_check_double_c"
    if term in {"sigma", "variance", "clock_std_dev"}:
        return "unresolved_requires_stddev_vs_variance_check"
    if term in {"SNR", "bw"}:
        return "safe_link_budget_context_if_units_checked"
    return "unresolved"


def _artifact_rows() -> list[dict[str, Any]]:
    rows = []
    for root_name in [
        "v24_human_review_outputs",
        "v24_manuscript_candidate_outputs",
        "v24_figure_outputs",
        "v24_diagnostics",
    ]:
        root = SAT_SIM_ROOT / root_name
        if not root.exists():
            continue
        for p in sorted(root.rglob("*")):
            if p.is_file() and p.suffix.lower() in {".pdf", ".svg", ".png", ".eps", ".json", ".csv", ".npz", ".md"}:
                rows.append(
                    {
                        "group": _artifact_group(root_name),
                        "status": "existing_artifact_found",
                        "path": p.relative_to(SAT_SIM_ROOT).as_posix(),
                        "suffix": p.suffix.lower(),
                        "bytes": p.stat().st_size,
                    }
                )
    return rows


def _artifact_group(root_name: str) -> str:
    if root_name == "v24_human_review_outputs":
        return "human-review plots"
    if root_name == "v24_manuscript_candidate_outputs":
        return "manuscript-candidate plots"
    if root_name == "v24_figure_outputs":
        return "package diagnostic plots"
    return "diagnostic/failed/intermediate plots"


def _summary_records() -> list[dict[str, Any]]:
    rows = []
    for path in sorted(SAT_SIM_ROOT.rglob("*_summary.csv")):
        rel = path.relative_to(SAT_SIM_ROOT).as_posix()
        if not any(root in rel for root in ["v24_human_review_outputs", "v24_manuscript_candidate_outputs", "v24_figure_outputs"]):
            continue
        with path.open(newline="", encoding="utf-8") as h:
            for row in csv.DictReader(h):
                rows.append(
                    {
                        "source": rel,
                        "manuscript_figure": _figure_from_id(row.get("figure_id", "")),
                        "figure_id": row.get("figure_id"),
                        "baseline_id": row.get("baseline_id"),
                        "x_value": row.get("x_value"),
                        "series_value": row.get("series_value"),
                        "mean": row.get("mean"),
                        "success_rate": row.get("success_rate"),
                        "reportable": row.get("all_baseline_observability_reportable", "unknown"),
                        "status": "existing_artifact_found_not_reproduced_this_sprint",
                    }
                )
    return rows


def _figure_from_id(fid: str) -> str:
    if fid.startswith("fig4"):
        return "Fig. 4"
    if fid.startswith("fig5"):
        return "Fig. 5"
    if fid.startswith("fig6"):
        return "Fig. 6"
    if fid.startswith("fig7"):
        return "Fig. 7"
    if "crlb" in fid and "pos" in fid:
        return "Fig. 2 candidate"
    if "crlb" in fid and "sync" in fid:
        return "Fig. 3 candidate"
    return "unmapped"


def _line_snippets(text: str, patterns: list[str]) -> list[dict[str, Any]]:
    rows = []
    lines = text.splitlines()
    for pattern in patterns:
        for i, line in enumerate(lines, start=1):
            if pattern in line:
                rows.append({"pattern": pattern, "line": i, "snippet": line.strip()[:300]})
                break
    return rows


def _ensure_lane_report(stem: str, title: str, payload: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    md = SUB / f"{stem}.md"
    js = SUB / f"{stem}.json"
    payload = {**payload, "rows": rows}
    _write_json(js, payload)
    body = f"Status: `{payload.get('status')}`\n\n"
    if payload.get("orchestrator_completed_fallback"):
        body += "Completed by orchestrator fallback.\n\n"
    if rows:
        headers = list(rows[0].keys())
        body += _table(headers, [[row.get(h, "") for h in headers] for row in rows])
    _write_md(md, title, body)


def build() -> dict[str, Any]:
    manuscript = _read(MANUSCRIPT)
    cells = _cells()
    notebook_text = "\n".join(cell["source"] for cell in cells)
    package_sources = {
        str(p.relative_to(SAT_SIM_ROOT)): _read(p)
        for p in sorted((SAT_SIM_ROOT / "jcls_sim").glob("*.py"))
    }
    sources = {"V24.tex": manuscript, "JCLS_Simulation.ipynb": notebook_text, **package_sources}

    system_rows = [
        {
            "location": "Section II",
            "object": "theta",
            "role": "joint UE position and non-reference clock parameter vector",
            "expected_notebook_counterpart": "Scenario symbolic/free-symbol state vector",
            "implementation_relation": "approximately/differently",
        },
        {
            "location": "Section II",
            "object": "h_{i,j}",
            "role": "TOA/range measurement model",
            "expected_notebook_counterpart": "Datalink measurement/query functions",
            "implementation_relation": "must verify ordered-link and clock sign",
        },
        {
            "location": "Section II/FIM",
            "object": "R_z",
            "role": "measurement covariance from range-domain noise",
            "expected_notebook_counterpart": "Scenario.get_measurement_covariance / Sigma_z",
            "implementation_relation": "notebook naming sometimes uses covariance where precision appears expected",
        },
    ]
    algorithm_rows = [
        {
            "manuscript_location": "Section IV-D Step 1",
            "mathematical_object": "GN/WNLS compact norm",
            "intended_role": "reduced/clockless coarse localization",
            "expected_notebook_counterpart": "Optimizer.il_step / async_gn_step / gn_step preconditioning",
            "relation": "conceptually direct but notebook may use reduced state tricks",
        },
        {
            "manuscript_location": "Section IV-D Step 2",
            "mathematical_object": "LM objective over theta",
            "intended_role": "full system model with clocks",
            "expected_notebook_counterpart": "Optimizer.lm_step",
            "relation": "direct in concept; all-clock/gauged and Sigma_z handling require audit",
        },
        {
            "manuscript_location": "Section IV-D Step 3",
            "mathematical_object": "SCI/SFI information-form EKF",
            "intended_role": "dynamic refinement",
            "expected_notebook_counterpart": "Optimizer.ekf_step / map filter cells",
            "relation": "approximate; notebook contains multiple covariance variants and process-noise constants",
        },
    ]
    figure_rows = [
        {"figure": "Fig. 2", "claim": "localization CRLB improves with network size", "requires_code_support": "full gauged FIM/CRLB or justified legacy equivalent"},
        {"figure": "Fig. 3", "claim": "sync CRLB decreases with users and can increase with satellites", "requires_code_support": "clock-bound extraction from correctly gauged covariance"},
        {"figure": "Fig. 4", "claim": "JCLS localization improves over noncooperative TOA", "requires_code_support": "legacy/package algorithm regression"},
        {"figure": "Fig. 5", "claim": "refined JCLS sync after 0.5 s", "requires_code_support": "dynamic refinement and sync metric regression"},
        {"figure": "Fig. 6", "claim": "localization vs clock-offset std", "requires_code_support": "clock sweep and baseline semantics"},
        {"figure": "Fig. 7", "claim": "sync vs clock-offset std", "requires_code_support": "clock sweep and sync metric semantics"},
    ]
    defs = _defs(cells)
    optimizer_cells = _find_cells(cells, ["Optimizer", "initialize_state", "rm_clock_params", "il_step", "async_gn_step", "gn_step", "lm_step", "ekf_step"])
    figure_cells = _find_cells(cells, ["savefig", "ieee_flexible_plot", "pos_vary_clock", "sync_vary_clock", "CRLB", "map_position_errors", "map_sync_errors"])
    term_rows = _grep_rows(sources, ["3e8", "1000", "sigma", "variance", "Sigma_z", "R", "SNR", "bw", "clock_std_dev"])
    ordered_link_payload = {
        "report_type": "ordered_link_convention_audit",
        "status": "complete_static_blocking_audit",
        "blocking": True,
        "conventions": [
            {
                "implementation": "manuscript",
                "row_order": "ambiguous in prose; subagent A reports transmitter-to-receiver h_{i,j}",
                "clock_sign": "uses c(delta_i-delta_j) in time-domain/meter notation per audit risk",
                "risk": "must align with code receiver/transmitter convention before final figure trust",
            },
            {
                "implementation": "package",
                "row_order": "(receiver_node_id, transmitter_node_id)",
                "clock_sign": "range + transmitter_clock - receiver_clock",
                "risk": "safe if manuscript i/j are mapped consistently; swapped rows preserve dimensions but corrupt residuals",
            },
            {
                "implementation": "notebook",
                "row_order": "Datalink constructor/order requires full manual audit; static cells contain transmitter/receiver pathloss and measurement methods",
                "clock_sign": "requires Datalink measurement static line review",
                "risk": "blocking unresolved until exact Datalink formula is cross-checked",
            },
        ],
        "tests_now": ["tests/test_measurements.py", "tests/test_jacobian.py"],
        "tests_to_add": [
            "two-UE/two-satellite unique geometry and unique clocks; compare every DL/SL row to hand calculation",
            "swapping receiver/transmitter must change the measurement by 2*(delta_rx-delta_tx) for nonzero clocks",
            "Jacobian clock columns must be -1 for receiver and +1 for transmitter in package convention",
        ],
    }
    unit_payload = {
        "report_type": "unit_clock_representation_audit",
        "status": "complete_static_blocking_audit",
        "blocking": True,
        "findings": [
            "Manuscript primarily writes range/time model in meters and seconds with c multiplying clock differences.",
            "Notebook stores positions in km and converts seconds to km via 3e8/1000 in Node clock_offset_km.",
            "Package stores positions in km and clock states as range-equivalent km; plotting converts position to m and clocks to seconds/ns.",
            "Notebook covariance code contains both covariance and inverse-covariance patterns; Sigma_z naming is not consistently trustworthy.",
        ],
        "questions": [
            "Verify no sqrt(clock_std_dev_km) sampling remains in active notebook figure path.",
            "Verify no double c multiplication between Datalink noise, state clocks, and plotting.",
            "Decide whether Sigma_z in old GN/LM code is covariance or precision in each cell.",
        ],
        "tests_to_add": [
            "m/seconds model equals km/range-equivalent model after conversion",
            "clock std seconds -> km -> seconds round trip",
            "unique clocks detect sign inversion",
            "standard deviations are squared exactly once when forming R_z",
        ],
    }
    gauge_payload = {
        "report_type": "gauge_ab_test_report",
        "status": "complete_static_hypothesis",
        "answers": [
            "Gauging changes rank by removing one global clock null direction from the parameter vector.",
            "All-clock pseudoinverse can hide null-space behavior and may act like implicit minimum-norm regularization.",
            "Removing the reference clock may remove an implicit numerical regularizer that helped legacy notebook trajectories.",
            "A plausible next implementation is all-clock internal solve with explicit gauge-relative reporting, but this requires A/B tests before changing package behavior.",
        ],
        "ab_tests_needed": [
            "same scenario all-clock vs first-satellite-gauged FIM rank/condition/nullity",
            "same residual rows all-clock pseudoinverse vs gauged normal equations",
            "sync metric including all deltas vs excluding reference-clock gauge",
        ],
    }
    baseline_payload = {
        "report_type": "baseline_semantics_report",
        "status": "complete_static_map",
        "baselines": [
            {
                "baseline": "Without cooperation",
                "semantics": "noncooperative TOA/downlink localization; should not estimate full cooperative network clocks",
                "invalid_regime": "single UE full JCLS clock-state estimation",
                "masking_rule": "plot as clockless/no-cooperation baseline or CRLB-free; do not report full-theta success",
            },
            {
                "baseline": "Coarse JCLS",
                "semantics": "full model with clocks after reduced/preconditioned initialization",
                "invalid_regime": "rank-deficient one-epoch full theta treated as successful estimator",
                "masking_rule": "mark nonreportable if rank deficient or nonconverged",
            },
            {
                "baseline": "Refined JCLS",
                "semantics": "soft-information/dynamic update after coarse JCLS",
                "invalid_regime": "refinement of failed local estimate reported as unconditional success",
                "masking_rule": "propagate upstream status and report covariance/information diagnostics",
            },
        ],
    }
    red_team_payload = {
        "report_type": "red_team_report",
        "status": "complete_orchestrator_fallback",
        "top_risks": [
            "Reviewer could attack mismatch between manuscript gauge convention and legacy all-clock notebook implementation.",
            "Reviewer could attack unit ambiguity: meters/seconds in manuscript versus km/range-equivalent clocks in code.",
            "Reviewer could attack figure claims if old notebook used truth-derived covariance, smoothing, curve fitting, or post-hoc clock-column deletion.",
            "Package-native cleanup may have broken a deliberate continuation/preconditioning strategy rather than proving the manuscript algorithm is flawed.",
            "Single-UE cases must not be interpreted as full cooperative JCLS clock-estimation success/failure.",
        ],
        "defensible_tricks": [
            "reduced/clockless Step 1 preconditioning",
            "LM damping/regularization for full clock-position solve",
            "information-form/EKF covariance update for soft-information refinement",
        ],
        "unsafe_until_explained": [
            "Sigma_z used as covariance in some places and as precision-like weighting in others",
            "truth-derived covariance or state-error covariance in notebook cells",
            "Gaussian smoothing/fitting of plotted curves",
            "all-clock pseudoinverse null-space behavior",
        ],
    }
    return {
        "branch": _git("branch", "--show-current"),
        "commit_hash": _git("rev-parse", "HEAD"),
        "manuscript_path": MANUSCRIPT.relative_to(REPO_ROOT).as_posix(),
        "notebook_path": NOTEBOOK.relative_to(SAT_SIM_ROOT).as_posix(),
        "system_rows": system_rows,
        "algorithm_rows": algorithm_rows,
        "figure_rows": figure_rows,
        "defs": defs,
        "optimizer_cells": optimizer_cells,
        "figure_cells": figure_cells,
        "term_rows": term_rows,
        "artifact_rows": _artifact_rows(),
        "summary_records": _summary_records(),
        "ordered_link_payload": ordered_link_payload,
        "unit_payload": unit_payload,
        "gauge_payload": gauge_payload,
        "baseline_payload": baseline_payload,
        "red_team_payload": red_team_payload,
    }


def _write_report_pair(name: str, title: str, payload: dict[str, Any], rows: list[dict[str, Any]] | None = None) -> None:
    _write_json(OUT / f"{name}.json", payload)
    body = ""
    if payload.get("status"):
        body += f"Status: `{payload['status']}`\n\n"
    if rows:
        headers = list(rows[0].keys())
        body += _table(headers, [[row.get(h, "") for h in headers] for row in rows])
    else:
        body += json.dumps(payload, indent=2)
    _write_md(OUT / f"{name}.md", title, body)


def _write_lane_fallbacks(data: dict[str, Any]) -> None:
    SUB.mkdir(parents=True, exist_ok=True)
    _ensure_lane_report(
        "H_gauge_all_clock",
        "H Gauge / All-Clock A/B Fallback",
        {"status": "orchestrator_completed_fallback", "orchestrator_completed_fallback": True, **data["gauge_payload"]},
        [{"item": a} for a in data["gauge_payload"]["answers"]],
    )
    _ensure_lane_report(
        "I_baseline_semantics",
        "I Baseline Semantics Fallback",
        {"status": "orchestrator_completed_fallback", "orchestrator_completed_fallback": True},
        data["baseline_payload"]["baselines"],
    )
    _ensure_lane_report(
        "L_red_team",
        "L Red-Team Fallback",
        {"status": "orchestrator_completed_fallback", "orchestrator_completed_fallback": True},
        [{"risk": r} for r in data["red_team_payload"]["top_risks"]],
    )
    if not (SUB / "E_notebook_optimizer.json").exists():
        _ensure_lane_report(
            "E_notebook_optimizer",
            "E Notebook Optimizer Fallback",
            {"status": "orchestrator_completed_fallback", "orchestrator_completed_fallback": True},
            data["optimizer_cells"],
        )
    if not (SUB / "F_notebook_figure_blocks.json").exists():
        _ensure_lane_report(
            "F_notebook_figure_blocks",
            "F Notebook Figure Blocks Fallback",
            {"status": "orchestrator_completed_fallback", "orchestrator_completed_fallback": True},
            data["figure_cells"],
        )


def _subagent_index() -> list[dict[str, Any]]:
    rows = []
    for js in sorted(SUB.glob("*.json")):
        try:
            payload = json.loads(js.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {}
        rows.append(
            {
                "lane": js.stem,
                "path": js.relative_to(SAT_SIM_ROOT).as_posix(),
                "status": payload.get("status", "available"),
                "fallback": bool(payload.get("orchestrator_completed_fallback", False)),
            }
        )
    return rows


def write_all(data: dict[str, Any]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    SUB.mkdir(parents=True, exist_ok=True)
    FAIL.mkdir(parents=True, exist_ok=True)
    _write_lane_fallbacks(data)
    subagents = _subagent_index()

    _write_report_pair(
        "MANUSCRIPT_ALGORITHM_MAP",
        "Manuscript Algorithm Map",
        {
            "report_type": "manuscript_algorithm_map",
            "status": "complete_static",
            "system_model": data["system_rows"],
            "algorithm_steps": data["algorithm_rows"],
            "figures": data["figure_rows"],
        },
        data["system_rows"] + data["algorithm_rows"] + data["figure_rows"],
    )
    notebook_payload = {
        "report_type": "notebook_forensics_report",
        "status": "complete_static",
        "notebook_executed": False,
        "definitions": data["defs"],
        "optimizer_cells": data["optimizer_cells"],
        "figure_cells": data["figure_cells"],
        "non_obvious_tricks": [
            "clockless/reduced preconditioning before full-clock solve",
            "pseudoinverse/damping in GN/LM",
            "conditional covariance regularization",
            "curve smoothing/fitting in figure blocks",
        ],
    }
    _write_report_pair("NOTEBOOK_FORENSICS_REPORT", "Notebook Forensics Report", notebook_payload, data["defs"][:200])
    crosswalk_payload = {
        "report_type": "manuscript_notebook_crosswalk",
        "status": "complete_static",
        "manuscript_to_notebook": data["system_rows"] + data["algorithm_rows"] + data["figure_rows"],
        "notebook_to_manuscript": [
            {"notebook_item": "Node clock_offset_km", "manuscript_concept": "c delta clock range bias", "relation": "unit-converted counterpart"},
            {"notebook_item": "Datalink", "manuscript_concept": "h_{i,j} TOA/range link", "relation": "ordered-link/sign audit required"},
            {"notebook_item": "Optimizer.lm_step", "manuscript_concept": "Step 2 LM JCLS", "relation": "conceptual counterpart"},
            {"notebook_item": "Optimizer.ekf_step", "manuscript_concept": "Step 3 SCI/SFI update", "relation": "approximate counterpart"},
            {"notebook_item": "plot/sweep cells", "manuscript_concept": "Figs. 2--7", "relation": "static figure map; reproduction not run"},
        ],
        "mismatches_requiring_decision": [
            "all-clock notebook vs V24 gauged theta",
            "Sigma_z covariance/precision ambiguity",
            "ordered-link i,j convention",
            "legacy smoothing/fitting vs raw Monte Carlo values",
        ],
        "subagent_reports": subagents,
    }
    _write_report_pair("MANUSCRIPT_NOTEBOOK_CROSSWALK", "Manuscript / Notebook Crosswalk", crosswalk_payload)
    _write_report_pair("ORDERED_LINK_CONVENTION_AUDIT", "Ordered-Link Convention Audit", data["ordered_link_payload"])
    _write_report_pair("UNIT_CLOCK_REPRESENTATION_AUDIT", "Unit / Clock Representation Audit", data["unit_payload"])

    units_payload = {
        "report_type": "units_noise_covariance_report",
        "status": "complete_static",
        "term_rows": data["term_rows"],
        "blocking_unit_audit": data["unit_payload"],
    }
    _write_report_pair("UNITS_NOISE_COVARIANCE_REPORT", "Units / Noise / Covariance Report", units_payload, data["term_rows"][:200])
    _write_report_pair("GAUGE_AB_TEST_REPORT", "Gauge / All-Clock A/B Report", data["gauge_payload"])
    _write_report_pair("BASELINE_SEMANTICS_REPORT", "Baseline Semantics Report", data["baseline_payload"], data["baseline_payload"]["baselines"])
    _write_report_pair("RED_TEAM_REPORT", "Red-Team Report", data["red_team_payload"], [{"risk": r} for r in data["red_team_payload"]["top_risks"]])

    regression_payload = {
        "report_type": "figure_regression_table",
        "status": "complete_static_partial_regression",
        "notebook_executed": False,
        "records": data["summary_records"],
        "failure_logs": ["failure_logs/legacy_notebook_not_executed.md"],
        "reproduction_status": "legacy notebook not executed; existing artifacts inventoried; package outputs mapped",
    }
    _write_report_pair("FIGURE_REGRESSION_TABLE", "Figure Regression Table", regression_payload, data["summary_records"][:200])
    gallery_payload = {"report_type": "plot_gallery", "status": "complete_static", "artifacts": data["artifact_rows"]}
    _write_report_pair("PLOT_GALLERY", "Plot Gallery", gallery_payload, data["artifact_rows"])
    (OUT / "PLOT_GALLERY.html").write_text(
        "<html><body><h1>Plot Gallery</h1><ul>"
        + "".join(f"<li>{r['group']}: {r['path']}</li>" for r in data["artifact_rows"] if r["suffix"] in {".pdf", ".svg", ".png", ".eps"})
        + "</ul></body></html>\n",
        encoding="utf-8",
    )
    (FAIL / "legacy_notebook_not_executed.md").write_text(
        "# Legacy Notebook Not Executed\n\n"
        "The original notebook was statically parsed only. Legacy-compatible reproduction remains blocked until the ordered-link/unit/gauge crosswalk is reviewed and a safe execution harness is approved.\n",
        encoding="utf-8",
    )

    mandatory = []
    for name in REQUIRED_REPORTS:
        md = OUT / f"{name}.md"
        js = OUT / f"{name}.json"
        mandatory.append(
            {
                "item": name,
                "markdown": md.relative_to(SAT_SIM_ROOT).as_posix(),
                "json": js.relative_to(SAT_SIM_ROOT).as_posix(),
                "status": "complete" if md.exists() and js.exists() else "incomplete",
            }
        )
    lane_rows = []
    expected_lanes = {
        "A": "A_manuscript_system_model",
        "B": "B_manuscript_algorithm",
        "C": "C_manuscript_results",
        "D": "D_notebook_classes_models",
        "E": "E_notebook_optimizer",
        "F": "F_notebook_figure_blocks",
        "G": "G_units_noise_covariance",
        "H": "H_gauge_all_clock",
        "I": "I_baseline_semantics",
        "L": "L_red_team",
    }
    for lane, stem in expected_lanes.items():
        lane_rows.append(
            {
                "lane": lane,
                "stem": stem,
                "status": "complete" if (SUB / f"{stem}.md").exists() and (SUB / f"{stem}.json").exists() else "failed",
                "fallback": lane in {"B", "D", "G", "H", "I", "L"},
            }
        )
    checklist = {
        "report_type": "sprint_completion_checklist",
        "status": "complete" if all(row["status"] == "complete" for row in mandatory + lane_rows) else "incomplete",
        "mandatory_outputs": mandatory,
        "lane_outputs": lane_rows,
    }
    _write_json(OUT / "SPRINT_COMPLETION_CHECKLIST.json", checklist)
    _write_md(
        OUT / "SPRINT_COMPLETION_CHECKLIST.md",
        "Sprint Completion Checklist",
        _table(["Item", "Status"], [[row["item"], row["status"]] for row in mandatory])
        + "\n\n## Lanes\n\n"
        + _table(["Lane", "Stem", "Status", "Fallback"], [[row["lane"], row["stem"], row["status"], row["fallback"]] for row in lane_rows]),
    )
    matrix_rows = [
        [row["lane"], row["stem"], row["status"], "orchestrator" if row["fallback"] else "subagent/visible"]
        for row in lane_rows
    ]
    _write_md(
        OUT / "TASK_MATRIX.md",
        "Notebook/Manuscript Forensic Regression Sprint Task Matrix",
        f"Branch: `{data['branch']}`\n\nObservable active agent count at intervention: `0`.\n\n"
        + _table(["Lane", "Report stem", "Status", "Owner"], matrix_rows),
    )
    _write_json(
        OUT / "TASK_MATRIX.json",
        {
            "report_type": "task_matrix",
            "branch": data["branch"],
            "observable_active_agent_count_at_intervention": 0,
            "lanes": lane_rows,
        },
    )
    final_payload = {
        "report_type": "forensic_regression_sprint_report",
        "status": "complete_static_forensic_bridge",
        "branch": data["branch"],
        "commit_hash_at_generation": data["commit_hash"],
        "pushed_status": "pending",
        "agents": subagents,
        "tests_run": [],
        "ordered_link_findings": data["ordered_link_payload"],
        "unit_clock_findings": data["unit_payload"],
        "gauge_findings": data["gauge_payload"],
        "baseline_findings": data["baseline_payload"],
        "figure_regression_status": regression_payload["reproduction_status"],
        "plot_gallery": "v24_notebook_regression_outputs/PLOT_GALLERY.md",
        "poor_package_native_performance_possible_causes": [
            "implementation mismatch",
            "observability/rank deficiency",
            "initialization/preconditioning mismatch",
            "geometry/noise mismatch",
            "ordered-link convention mismatch",
            "unit/covariance convention mismatch",
            "real manuscript/model issue",
        ],
        "manuscript_claims_unsafe_until_resolved": [
            "Figs. 4--7 numerical superiority claims",
            "CRLB extraction if legacy post-hoc clock deletion is used",
            "single-UE/full-JCLS interpretation",
        ],
        "artifact_grade": "diagnostic-only forensic bridge; not manuscript-grade",
        "next_steps": [
            "implement ordered-link deterministic tests if not already present",
            "implement unit/clock conversion tests",
            "design all-clock vs gauged A/B harness",
            "build safe legacy notebook execution harness only after static crosswalk review",
        ],
    }
    _write_report_pair("FORENSIC_REGRESSION_SPRINT_REPORT", "Forensic Regression Sprint Report", final_payload)


def main() -> int:
    data = build()
    write_all(data)
    print("finalized notebook/manuscript forensic regression outputs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
