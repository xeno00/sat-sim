"""Safely execute a tiny extracted legacy-notebook smoke scenario."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = ROOT / "JCLS_Simulation.ipynb"
OUTPUT_ROOT = ROOT / "v24_notebook_regression_outputs" / "executed_legacy"


def _load_notebook() -> dict[str, Any]:
    """Load the legacy notebook JSON without mutating it."""

    return json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))


def _class_cell_sources() -> list[str]:
    """Return only the safe class cells needed for a tiny smoke run."""

    notebook = _load_notebook()
    wanted = [
        "class Node",
        "class User",
        "class Satellite",
        "class Datalink",
        "class Scenario",
        "class Optimizer",
    ]
    sources: list[str] = []
    for needle in wanted:
        for cell in notebook["cells"]:
            source = "".join(cell.get("source", []))
            if cell.get("cell_type") == "code" and needle in source:
                sources.append(source)
                break
        else:
            raise ValueError(f"Could not find {needle} in {NOTEBOOK_PATH}.")
    return sources


def _execute_classes() -> dict[str, Any]:
    """Execute safe notebook class cells in an isolated namespace."""

    import itertools
    import warnings
    from copy import copy

    import sympy as sp
    from scipy.stats import rv_continuous

    namespace: dict[str, Any] = {
        "np": np,
        "sp": sp,
        "rv_continuous": rv_continuous,
        "copy": copy,
        "itertools": itertools,
        "warnings": warnings,
    }
    for source in _class_cell_sources():
        exec(compile(source, str(NOTEBOOK_PATH), "exec"), namespace)
    return namespace


def _set_node_clock(node: Any, seconds: float) -> None:
    """Set both seconds and km clock fields on a legacy node."""

    node.clock_offset_seconds = float(seconds)
    node.clock_offset_km = float(seconds) * 3.0e8 / 1000.0


def run_smoke() -> dict[str, Any]:
    """Run a deterministic tiny legacy scenario and return raw diagnostics."""

    np.random.seed(2025)
    namespace = _execute_classes()
    Scenario = namespace["Scenario"]
    Optimizer = namespace["Optimizer"]

    users = [
        np.array([0.0, 0.0, 0.0]),
        np.array([3.0, 4.0, 0.5]),
    ]
    satellites = [
        np.array([10.0, 0.0, 2.0]),
        np.array([0.0, 12.0, 5.0]),
    ]
    scenario = Scenario(users=users, satellites=satellites, clock_std_dev_seconds=1e-9)
    deterministic_clocks_s = {
        1: 0.11 / (3.0e8 / 1000.0),
        2: -0.23 / (3.0e8 / 1000.0),
        3: 0.37 / (3.0e8 / 1000.0),
        4: -0.41 / (3.0e8 / 1000.0),
    }
    for node in scenario.nodes:
        _set_node_clock(node, deterministic_clocks_s[node.node_id])
    scenario.extract_models_and_parameters()

    links = scenario.get_links()
    link_pairs = [(int(link.receiver.node_id), int(link.transmitter.node_id)) for link in links]
    link_types = [str(link.link_type) for link in links]
    z_tfap = scenario.query_measurements(tfap=True)
    true_state = scenario.get_true_state()
    h_true = scenario.h(true_state)
    jacobian = scenario.evaluate_jacobian(true_state)
    covariance_tfap = scenario.get_measurement_covariance(tfap=True)

    optimizer = Optimizer()
    optimizer_results: dict[str, Any] = {}
    for algorithm in ["IL", "LM"]:
        try:
            result = optimizer.run(
                algorithm,
                scenario,
                true_state.copy(),
                z_tfap.copy(),
                num_steps=1,
                tol=1e-12,
            )
            optimizer_results[algorithm] = {
                "status": "passed",
                "state_norm_error_km": float(np.linalg.norm(result - true_state)),
            }
        except Exception as exc:  # noqa: BLE001 - diagnostics should capture legacy failures.
            optimizer_results[algorithm] = {
                "status": "failed_execution",
                "error_type": type(exc).__name__,
                "error": str(exc),
            }

    try:
        ekf_state, ekf_cov = optimizer.ekf_step(
            scenario,
            true_state.copy(),
            np.eye(true_state.shape[0]),
            z_tfap.copy(),
            easy=True,
        )
        optimizer_results["EKF"] = {
            "status": "passed",
            "state_norm_error_km": float(np.linalg.norm(ekf_state - true_state)),
            "covariance_shape": list(ekf_cov.shape),
        }
    except Exception as exc:  # noqa: BLE001 - diagnostics should capture legacy failures.
        optimizer_results["EKF"] = {
            "status": "failed_execution",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }

    return {
        "status": "executable_smoke_passed",
        "artifact_status": "non_final_legacy_notebook_smoke",
        "notebook_source_modified": False,
        "full_notebook_executed": False,
        "selected_cells_executed": [
            "Node",
            "User",
            "Satellite",
            "Datalink",
            "Scenario",
            "Optimizer",
        ],
        "skipped_side_effects": [
            "google.colab drive.mount",
            "pip/apt/wget notebook lines",
            "workspace pickle load/save",
            "plt.show",
            "figure cells",
        ],
        "seed": 2025,
        "num_users": 2,
        "num_satellites": 2,
        "links_receiver_transmitter": link_pairs,
        "link_types": link_types,
        "symbolic_parameter_order": [str(param) for param in scenario.symbolic_parameter_vector],
        "measurement_count": int(z_tfap.shape[0]),
        "state_dimension": int(true_state.shape[0]),
        "z_tfap_km": z_tfap.tolist(),
        "h_true_km": h_true.tolist(),
        "max_abs_z_minus_h_km": float(np.max(np.abs(z_tfap - h_true))),
        "jacobian_shape": list(jacobian.shape),
        "covariance_tfap_diag": np.diag(covariance_tfap).tolist(),
        "optimizer_results": optimizer_results,
        "figure_outputs_written": False,
        "output_root": str(OUTPUT_ROOT.relative_to(ROOT)),
    }


def main() -> None:
    """Run and write the tiny legacy notebook smoke diagnostics."""

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    result = run_smoke()
    (OUTPUT_ROOT / "legacy_notebook_smoke.json").write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )
    (OUTPUT_ROOT / "legacy_notebook_smoke.md").write_text(
        "\n".join(
            [
                "# Legacy Notebook Smoke",
                "",
                f"- Status: {result['status']}",
                "- Scope: selected class cells only; no figure cells; no notebook source edits.",
                f"- Links: {result['links_receiver_transmitter']}",
                f"- Optimizer results: {result['optimizer_results']}",
                "",
                "```json",
                json.dumps(result, indent=2),
                "```",
            ]
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
