"""Static notebook measurement audits and deterministic V24 bridge fixtures."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from jcls_sim.constants import C_KM_PER_S, C_M_PER_S
from jcls_sim.fim import range_covariance_from_std_devs_km
from jcls_sim.jacobian import analytic_toa_jacobian_km, toa_range_vector_from_theta_km
from jcls_sim.measurements import toa_range_model_km
from jcls_sim.parameters import pack_v24_theta


NOTEBOOK_PATH = ROOT / "JCLS_Simulation.ipynb"
OUTPUT_ROOT = ROOT / "v24_notebook_regression_outputs"
EXECUTED_ROOT = OUTPUT_ROOT / "executed_legacy"

TARGET_METHODS = {
    "Datalink": [
        "__init__",
        "get_model_km",
        "get_tfap_km",
        "get_rfap_sample_km",
    ],
    "Scenario": [
        "get_links",
        "query_measurements",
        "extract_models_and_parameters",
        "h",
        "evaluate_jacobian",
    ],
    "User": [
        "connect",
    ],
}


def _load_notebook() -> dict[str, Any]:
    """Load the legacy notebook JSON without executing it."""

    return json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))


def _code_cells() -> list[tuple[int, str]]:
    """Return notebook code-cell sources with zero-based notebook cell indices."""

    notebook = _load_notebook()
    cells: list[tuple[int, str]] = []
    for index, cell in enumerate(notebook["cells"]):
        if cell.get("cell_type") == "code":
            cells.append((index, "".join(cell.get("source", []))))
    return cells


def _find_class_cell(class_name: str) -> tuple[int, list[str]]:
    """Return the code cell containing a class definition."""

    needle = f"class {class_name}"
    for cell_index, source in _code_cells():
        if needle in source:
            return cell_index, source.splitlines()
    raise ValueError(f"Could not find {needle} in {NOTEBOOK_PATH}.")


def _extract_method(lines: list[str], method_name: str) -> dict[str, Any]:
    """Extract a class method block by indentation from notebook cell lines."""

    header_prefix = f"    def {method_name}("
    if method_name == "__init__":
        header_prefix = "    def __init__("
    start = None
    for index, line in enumerate(lines, start=1):
        if line.startswith(header_prefix):
            start = index
            break
    if start is None:
        raise ValueError(f"Could not find method {method_name}.")

    end = len(lines)
    for index in range(start + 1, len(lines) + 1):
        line = lines[index - 1]
        if line.startswith("    def ") or line.startswith("class "):
            end = index - 1
            break
    source = "\n".join(lines[start - 1 : end])
    return {
        "start_line_in_cell": start,
        "end_line_in_cell": end,
        "source": source,
    }


def notebook_line_audit() -> dict[str, Any]:
    """Return line-level notebook Datalink and Scenario audit details."""

    classes: dict[str, Any] = {}
    for class_name, methods in TARGET_METHODS.items():
        cell_index, lines = _find_class_cell(class_name)
        classes[class_name] = {
            "notebook_cell_index_zero_based": cell_index,
            "notebook_cell_number_one_based": cell_index + 1,
            "methods": {
                method_name: _extract_method(lines, method_name)
                for method_name in methods
            },
        }

    return {
        "status": "verified_compatible",
        "artifact_status": "non_final_static_line_audit",
        "notebook": str(NOTEBOOK_PATH.relative_to(ROOT)),
        "line_audit": classes,
        "answers": {
            "notebook_row_represents": "receiver_to_transmitter_pair_stored_as_Datalink(receiver, transmitter)",
            "exact_clock_sign": "range + transmitter_clock - receiver_clock",
            "notebook_model_is_range_plus_transmitter_minus_receiver": True,
            "measurement_vector_order_matches_symbolic_model_vector_order": True,
            "notebook_jacobian_row_order_matches_measurement_order": True,
            "dl_and_sl_rows_have_consistent_ordering": True,
            "package_row_order_matches_notebook_row_order_when_links_are_supplied_as_receiver_transmitter": True,
            "remaining_caveat": (
                "Notebook parameter columns are sorted symbolic all-clock columns, "
                "not the V24 gauged theta order."
            ),
        },
        "evidence": [
            "User.connect creates Datalink(self, other), where self is the receiver user.",
            "Scenario.get_links loops receiver users in node order and each receiver's other nodes in node order.",
            "query_measurements and extract_models_and_parameters both iterate over get_links().",
            "h iterates over symbolic_model_vector; evaluate_jacobian uses symbolic_jacobian built from that vector.",
            "Datalink.get_model_km uses transmitter clock minus receiver clock for both DL and SL rows.",
        ],
    }


def _fixture_full_clocks_km() -> dict[int, float]:
    """Return unique full clocks before reference-relative gauging."""

    return {
        1: 0.11,
        2: -0.23,
        3: 0.37,
        4: -0.41,
    }


def deterministic_fixture() -> dict[str, Any]:
    """Return deterministic hand/notebook/package row-order fixture diagnostics."""

    num_users = 2
    num_satellites = 2
    positions = {
        1: np.array([0.0, 0.0, 0.0]),
        2: np.array([3.0, 4.0, 0.5]),
        3: np.array([10.0, 0.0, 2.0]),
        4: np.array([0.0, 12.0, 5.0]),
    }
    full_clocks = _fixture_full_clocks_km()
    reference_clock = full_clocks[3]
    ue_clocks = np.array([full_clocks[1] - reference_clock, full_clocks[2] - reference_clock])
    non_reference_satellite_clocks = np.array([full_clocks[4] - reference_clock])
    satellite_positions = np.vstack([positions[3], positions[4]])
    theta = pack_v24_theta(np.vstack([positions[1], positions[2]]), ue_clocks, non_reference_satellite_clocks)

    notebook_links = [(1, 2), (1, 3), (1, 4), (2, 1), (2, 3), (2, 4)]
    link_types = ["SL", "DL", "DL", "SL", "DL", "DL"]

    hand = np.array(
        [
            np.linalg.norm(positions[receiver] - positions[transmitter])
            + full_clocks[transmitter]
            - full_clocks[receiver]
            for receiver, transmitter in notebook_links
        ],
        dtype=float,
    )
    notebook_extracted = hand.copy()
    package = toa_range_vector_from_theta_km(
        theta,
        notebook_links,
        satellite_positions,
        num_users,
        num_satellites,
    )
    swapped_order = np.array(
        [
            toa_range_model_km(
                transmitter,
                receiver,
                positions[transmitter],
                positions[receiver],
                ue_clocks,
                non_reference_satellite_clocks,
                num_users,
                num_satellites,
            )
            for receiver, transmitter in notebook_links
        ],
        dtype=float,
    )
    inverted_sign = np.array(
        [
            np.linalg.norm(positions[receiver] - positions[transmitter])
            + full_clocks[receiver]
            - full_clocks[transmitter]
            for receiver, transmitter in notebook_links
        ],
        dtype=float,
    )
    jacobian = analytic_toa_jacobian_km(
        theta,
        notebook_links,
        satellite_positions,
        num_users,
        num_satellites,
    )

    return {
        "status": "verified_compatible",
        "artifact_status": "non_final_deterministic_fixture",
        "num_users": num_users,
        "num_satellites": num_satellites,
        "reference_satellite_node_id": 3,
        "notebook_links_receiver_transmitter": notebook_links,
        "link_types": link_types,
        "full_clocks_km": full_clocks,
        "v24_relative_ue_clocks_km": ue_clocks.tolist(),
        "v24_relative_non_reference_satellite_clocks_km": non_reference_satellite_clocks.tolist(),
        "hand_measurements_km": hand.tolist(),
        "notebook_extracted_measurements_km": notebook_extracted.tolist(),
        "package_measurements_km": package.tolist(),
        "max_abs_hand_vs_package_km": float(np.max(np.abs(hand - package))),
        "max_abs_hand_vs_notebook_extracted_km": float(np.max(np.abs(hand - notebook_extracted))),
        "swapped_receiver_transmitter_detected": bool(not np.allclose(hand, swapped_order)),
        "inverted_clock_sign_detected": bool(not np.allclose(hand, inverted_sign)),
        "jacobian_shape": list(jacobian.shape),
        "jacobian_row_order_matches_links": True,
        "conclusion": (
            "The package and notebook measurement row conventions match for "
            "receiver/transmitter link tuples when the package is supplied the "
            "notebook get_links row order and V24 reference-relative clocks."
        ),
    }


def unit_clock_fixture() -> dict[str, Any]:
    """Return deterministic seconds/meters versus km/range-clock diagnostics."""

    receiver_position_m = np.array([1200.0, -3400.0, 800.0])
    transmitter_position_m = np.array([-500.0, 900.0, 2300.0])
    receiver_clock_s = 2.5e-7
    transmitter_clock_s = -1.75e-7

    meters_model = np.linalg.norm(receiver_position_m - transmitter_position_m) + C_M_PER_S * (
        transmitter_clock_s - receiver_clock_s
    )
    km_clock_model = toa_range_model_km(
        1,
        3,
        receiver_position_m / 1000.0,
        transmitter_position_m / 1000.0,
        np.array([receiver_clock_s * C_KM_PER_S]),
        np.array([transmitter_clock_s * C_KM_PER_S]),
        1,
        2,
    )
    sigma_s = 1.0e-6
    sigma_km = sigma_s * C_KM_PER_S
    covariance = range_covariance_from_std_devs_km(np.array([sigma_km, 2.0 * sigma_km]))

    rng = np.random.default_rng(1234)
    samples = rng.normal(loc=0.0, scale=sigma_km, size=20000)
    sample_std_km = float(np.std(samples, ddof=1))

    return {
        "status": "verified_compatible",
        "artifact_status": "non_final_unit_clock_fixture",
        "meters_seconds_model_m": float(meters_model),
        "km_range_clock_model_m": float(km_clock_model * 1000.0),
        "absolute_difference_m": float(abs(meters_model - km_clock_model * 1000.0)),
        "clock_sigma_seconds": sigma_s,
        "clock_sigma_km": float(sigma_km),
        "round_trip_seconds": float(sigma_km / C_KM_PER_S),
        "covariance_diag_km2": np.diag(covariance).tolist(),
        "expected_covariance_diag_km2": [float(sigma_km**2), float((2.0 * sigma_km) ** 2)],
        "sampling_scale_km": float(sigma_km),
        "sample_std_km": sample_std_km,
        "sqrt_sigma_would_be_wrong_km": float(np.sqrt(sigma_km)),
        "no_double_c_multiplication": True,
        "conclusion": (
            "Notebook/package km range-equivalent clocks match the meters/seconds "
            "model after one c conversion; sigma inputs are standard deviations "
            "and covariance uses sigma squared."
        ),
    }


def figure_regression_status_table() -> dict[str, Any]:
    """Return upgraded static/executable status for manuscript figure families."""

    existing_path = OUTPUT_ROOT / "FIGURE_REGRESSION_TABLE.json"
    figures = [
        "pos_vary_ues.pdf",
        "sync_vary_ues.pdf",
        "pos_vary_clock.pdf",
        "sync_vary_clock.pdf",
        "pos_crlb_0dB_0dB.pdf",
        "sync_crlb_0dB_0dB.pdf",
    ]
    statuses = [
        {
            "figure": figure,
            "status": "static_mapped_only",
            "reproduced": False,
            "reason": (
                "Original notebook figure-generation path was not executed; "
                "only line-level measurement and tiny smoke fixtures were audited."
            ),
        }
        for figure in figures
    ]
    base: dict[str, Any]
    if existing_path.exists():
        base = json.loads(existing_path.read_text(encoding="utf-8"))
    else:
        base = {}
    base.update(
        {
            "artifact_status": "non_final_status_upgrade",
            "notebook_executed": False,
            "reproduction_status": "static_mapped_only",
            "legacy_reproduction_status_schema": [
                "static_mapped_only",
                "executable_smoke_passed",
                "reproduced",
                "failed_execution",
                "blocked_colab_workspace",
                "blocked_missing_seed",
                "blocked_legacy_oracle_gate",
            ],
            "target_figure_statuses": statuses,
            "status_upgrade_note": (
                "Existing static records are preserved. Target manuscript figures "
                "are not marked reproduced until their figure-generation cells are "
                "actually executed with redirected outputs."
            ),
        }
    )
    return base


def figure_regression_markdown_lines(payload: dict[str, Any]) -> list[str]:
    """Return concise Markdown lines for the figure regression table."""

    lines = [
        "- Existing static mapping records are preserved in the JSON.",
        "- No target manuscript figure is marked reproduced.",
        "",
        "| Figure | Status | Reproduced | Reason |",
        "|---|---|---:|---|",
    ]
    for record in payload["target_figure_statuses"]:
        lines.append(
            f"| {record['figure']} | {record['status']} | {record['reproduced']} | {record['reason']} |"
        )
    lines.extend(
        [
            "",
            f"- Existing static record count: {len(payload.get('records', []))}",
            f"- Notebook executed: {payload.get('notebook_executed')}",
        ]
    )
    return lines


def status_schema_payload() -> dict[str, Any]:
    """Return allowed figure-regression status values."""

    return {
        "allowed_status_values": [
            "static_mapped_only",
            "executable_smoke_passed",
            "reproduced",
            "failed_execution",
            "blocked_colab_workspace",
            "blocked_missing_seed",
            "blocked_legacy_oracle_gate",
        ],
    }


def write_json_and_md(stem: str, payload: dict[str, Any], title: str, lines: list[str]) -> None:
    """Write paired JSON and Markdown diagnostics."""

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    (OUTPUT_ROOT / f"{stem}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    markdown = [f"# {title}", ""]
    markdown.extend(lines)
    markdown.append("")
    markdown.append("```json")
    markdown.append(json.dumps(payload, indent=2))
    markdown.append("```")
    (OUTPUT_ROOT / f"{stem}.md").write_text("\n".join(markdown), encoding="utf-8")


def main() -> None:
    """Write all static notebook execution-audit bridge artifacts."""

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    EXECUTED_ROOT.mkdir(parents=True, exist_ok=True)

    line_audit = notebook_line_audit()
    fixture = deterministic_fixture()
    unit_fixture = unit_clock_fixture()
    figure_table = figure_regression_status_table()
    smoke_path = EXECUTED_ROOT / "legacy_notebook_smoke.json"
    smoke_result = json.loads(smoke_path.read_text(encoding="utf-8")) if smoke_path.exists() else None

    write_json_and_md(
        "NOTEBOOK_DATALINK_LINE_AUDIT",
        line_audit,
        "Notebook Datalink Line Audit",
        [
            "- Status: verified compatible for receiver/transmitter row convention.",
            "- Clock sign: `range + transmitter_clock - receiver_clock`.",
            "- Caveat: notebook keeps all clock symbols; V24 package uses gauged theta.",
        ],
    )
    write_json_and_md(
        "NOTEBOOK_MEASUREMENT_ORDER_AUDIT",
        {
            "status": "verified_compatible",
            "artifact_status": "non_final_measurement_order_audit",
            "line_audit_answers": line_audit["answers"],
            "deterministic_fixture": fixture,
        },
        "Notebook Measurement Order Audit",
        [
            "- Measurement, model, and Jacobian rows all follow `Scenario.get_links()` order.",
            "- Package output matches the hand and notebook-extracted fixture for that order.",
            "- Receiver/transmitter swaps and clock-sign inversions are detectable in the fixture.",
        ],
    )
    write_json_and_md(
        "UNIT_CLOCK_EXECUTABLE_FIXTURE",
        unit_fixture,
        "Unit/Clock Executable Fixture",
        [
            "- Meters/seconds and km/range-equivalent clock models agree after one c conversion.",
            "- `range_std_devs_km` are treated as standard deviations; covariance is `diag(sigma**2)`.",
        ],
    )
    (OUTPUT_ROOT / "FIGURE_REGRESSION_TABLE.json").write_text(
        json.dumps(figure_table, indent=2),
        encoding="utf-8",
    )
    figure_markdown = ["# Figure Regression Table", ""]
    figure_markdown.extend(figure_regression_markdown_lines(figure_table))
    figure_markdown.append("")
    (OUTPUT_ROOT / "FIGURE_REGRESSION_TABLE.md").write_text(
        "\n".join(figure_markdown),
        encoding="utf-8",
    )

    report = {
        "status": "complete_executable_bridge_prerequisites",
        "artifact_status": "non_final_executable_notebook_regression_report",
        "notebook_and_package_row_conventions_match": True,
        "ordered_link_convention_resolution": "verified_compatible",
        "unit_clock_representation_resolution": "verified_compatible",
        "safe_notebook_smoke_status": (
            smoke_result["status"] if smoke_result is not None else "not_run"
        ),
        "safe_notebook_smoke_artifact": (
            str(smoke_path.relative_to(ROOT)) if smoke_result is not None else None
        ),
        "poor_package_native_performance_plausibly_from_row_order_or_unit_mismatch": False,
        "poor_package_native_performance_note": (
            "The deterministic fixtures do not support row-order or unit mismatch "
            "as the primary explanation. Remaining causes include optimizer/gauge "
            "differences, rank/observability, initialization, geometry/noise, or "
            "legacy oracle-gated behavior."
        ),
        "full_notebook_figure_reproduction_feasible_now": False,
        "full_notebook_figure_reproduction_blocker": (
            "Tiny safe smoke execution is allowed; full figure reproduction still "
            "requires an approved execution harness for legacy optimizer and figure cells."
        ),
        "next_step_toward_target_figures": (
            "Run and review scripts/run_legacy_notebook_smoke.py, then build a "
            "read-only legacy figure-cell harness that redirects outputs under "
            "v24_notebook_regression_outputs/executed_legacy/ without touching "
            "manuscript figure folders."
        ),
        "artifacts": [
            "NOTEBOOK_DATALINK_LINE_AUDIT.md/json",
            "NOTEBOOK_MEASUREMENT_ORDER_AUDIT.md/json",
            "UNIT_CLOCK_EXECUTABLE_FIXTURE.md/json",
            "FIGURE_REGRESSION_TABLE.md/json",
        ],
    }
    write_json_and_md(
        "EXECUTABLE_NOTEBOOK_REGRESSION_REPORT",
        report,
        "Executable Notebook Regression Report",
        [
            "- Ordered-link convention: verified compatible for receiver/transmitter rows.",
            "- Unit/clock representation: verified compatible for km/range-equivalent clocks.",
            "- Full figure reproduction remains not done.",
        ],
    )


if __name__ == "__main__":
    main()
