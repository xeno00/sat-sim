"""Run package-native V24 figure generation for Figs. 4--7.

Outputs are written under ``v24_figure_outputs/`` by default. This script does
not import or execute ``JCLS_Simulation.ipynb`` and does not write to manuscript
figure directories.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SAT_SIM_ROOT = Path(__file__).resolve().parents[1]
if str(SAT_SIM_ROOT) not in sys.path:
    sys.path.insert(0, str(SAT_SIM_ROOT))

from jcls_sim.figure_generation import run_figure_config  # noqa: E402
from jcls_sim.figure_generation import (  # noqa: E402
    ARTIFACT_WARNING,
    DIAGNOSTIC_ARTIFACT_FLAGS,
    validate_output_root,
)


DEFAULT_CONFIG_DIR = SAT_SIM_ROOT / "configs" / "v24_figures_4_7"
DEFAULT_OUTPUT_ROOT = SAT_SIM_ROOT / "v24_figure_outputs"


def _default_configs() -> list[Path]:
    """Return checked-in V24 Fig. 4--7 config paths."""

    return [
        DEFAULT_CONFIG_DIR / "fig4_localization_vs_satellites.json",
        DEFAULT_CONFIG_DIR / "fig5_synchronization_vs_satellites.json",
        DEFAULT_CONFIG_DIR / "fig6_localization_vs_clock_std.json",
        DEFAULT_CONFIG_DIR / "fig7_synchronization_vs_clock_std.json",
    ]


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        action="append",
        help="Figure config to run. May be supplied multiple times.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all checked-in Fig. 4--7 configs.",
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Permit replacement of existing diagnostic output files.",
    )
    parser.add_argument(
        "--allow-unsafe-output-root",
        action="store_true",
        help="Developer-only override for writing outside repo-local diagnostic output roots.",
    )
    return parser.parse_args()


def _write_combined_provenance(output_root: Path, results: list) -> tuple[Path, Path]:
    """Write a top-level provenance table for the completed figure runs."""

    output_root.mkdir(parents=True, exist_ok=True)
    rows = []
    for result in results:
        provenance = json.loads(result.provenance_json.read_text(encoding="utf-8"))
        metadata = json.loads(result.metadata_json.read_text(encoding="utf-8"))
        rows.append(
            {
                "figure_id": result.figure_id,
                "manuscript_figure": provenance["manuscript_figure"],
                "command": provenance["command"],
                "config_file": provenance["config_file"],
                "raw_output_file": provenance["raw_output_file"],
                "summary_output_file": provenance["summary_output_file"],
                "npz_output_file": provenance["npz_output_file"],
                "plot_output_file": provenance["plot_output_file"],
                "metadata_file": provenance["metadata_file"],
                "base_seed": metadata["base_seed"],
                "monte_carlo_trials": metadata["monte_carlo_trials"],
                "runtime_seconds": metadata["runtime_seconds"],
                "notebook_used": metadata["notebook_used"],
                "manuscript_directories_touched": metadata["manuscript_directories_touched"],
                "known_discrepancy_from_v24": provenance["known_discrepancy_from_v24"],
            }
        )

    json_path = output_root / "figure_provenance_table.json"
    md_path = output_root / "figure_provenance_table.md"
    payload = {
        "provenance_table_type": "package_native_v24_diagnostic_figure_provenance_table",
        **DIAGNOSTIC_ARTIFACT_FLAGS,
        "artifact_warning": ARTIFACT_WARNING,
        "rows": rows,
    }
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    header = [
        "# Package-Native V24 Fig. 4--7 Diagnostic Provenance",
        "",
        f"Warning: {ARTIFACT_WARNING}",
        "",
        "| Figure | Config | Raw CSV | Summary CSV | PDF | Metadata | Trials | Seed | Notebook used | Manuscript dirs touched |",
        "|---|---|---|---|---|---|---:|---:|---|---|",
    ]
    body = [
        "| {figure} | `{config}` | `{raw}` | `{summary}` | `{pdf}` | `{metadata}` | {trials} | {seed} | {notebook} | {manuscript_dirs} |".format(
            figure=row["manuscript_figure"],
            config=row["config_file"],
            raw=row["raw_output_file"],
            summary=row["summary_output_file"],
            pdf=row["plot_output_file"],
            metadata=row["metadata_file"],
            trials=row["monte_carlo_trials"],
            seed=row["base_seed"],
            notebook=row["notebook_used"],
            manuscript_dirs=row["manuscript_directories_touched"],
        )
        for row in rows
    ]
    md_path.write_text("\n".join(header + body) + "\n", encoding="utf-8")
    return json_path, md_path


def main() -> int:
    """Run selected package-native figure configs."""

    args = _parse_args()
    configs = args.config or []
    if args.all:
        configs = _default_configs()
    if not configs:
        raise SystemExit("Provide --config <path> or --all.")

    output_root = validate_output_root(
        args.output_root,
        allow_unsafe_output_root=args.allow_unsafe_output_root,
    )
    if output_root.exists() and any(output_root.iterdir()) and not args.overwrite:
        raise SystemExit(
            f"Refusing to overwrite existing non-empty diagnostic output root: {output_root}. "
            "Use --overwrite to replace diagnostic outputs."
        )

    results = []
    for config in configs:
        result = run_figure_config(
            config,
            output_root,
            overwrite=args.overwrite,
            allow_unsafe_output_root=args.allow_unsafe_output_root,
        )
        results.append(result)
        print(f"{result.figure_id}:")
        print(f"  raw: {result.raw_csv}")
        print(f"  summary: {result.summary_csv}")
        print(f"  npz: {result.raw_npz}")
        print(f"  pdf: {result.pdf}")
        print(f"  metadata: {result.metadata_json}")
        print(f"  provenance: {result.provenance_json}")
    json_path, md_path = _write_combined_provenance(output_root, results)
    print("combined provenance:")
    print(f"  json: {json_path}")
    print(f"  markdown: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
