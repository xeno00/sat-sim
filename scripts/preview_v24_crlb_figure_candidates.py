"""Write non-final SVG previews from V24 CRLB figure-candidate JSON.

The previews are diagnostic-only. They do not touch manuscript figure
directories and must not be used as final manuscript figures.
"""

from __future__ import annotations

import argparse
import html
import json
import math
from pathlib import Path
from typing import Any

SAT_SIM_ROOT = Path(__file__).resolve().parents[1]


DEFAULT_INPUT_PATH = SAT_SIM_ROOT / "v24_diagnostics" / "crlb_figure_candidate_data.json"
DEFAULT_OUTPUT_DIR = SAT_SIM_ROOT / "v24_diagnostics" / "crlb_preview"

PREVIEW_POLICY = (
    "Non-final CRLB preview only. These SVGs are diagnostic aids for human "
    "figure-concept review and are not manuscript figures."
)


def _write_text(path: Path, text: str, *, overwrite: bool) -> Path:
    """Write text while refusing accidental overwrites unless requested."""

    if path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing preview output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _svg(width: int, height: int, body: str) -> str:
    """Return a complete SVG document."""

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">\n'
        "<style>\n"
        "text { font-family: Arial, Helvetica, sans-serif; fill: #1f2933; }\n"
        ".title { font-size: 18px; font-weight: 700; }\n"
        ".subtitle { font-size: 12px; fill: #52606d; }\n"
        ".axis { font-size: 11px; fill: #323f4b; }\n"
        ".small { font-size: 10px; fill: #52606d; }\n"
        ".note { font-size: 11px; fill: #7b341e; }\n"
        "</style>\n"
        f"{body}\n"
        "</svg>\n"
    )


def _text(x: float, y: float, text: str, class_name: str = "axis", anchor: str = "start") -> str:
    """Return escaped SVG text."""

    return (
        f'<text x="{x:.1f}" y="{y:.1f}" class="{class_name}" '
        f'text-anchor="{anchor}">{html.escape(text)}</text>'
    )


def _line(x1: float, y1: float, x2: float, y2: float, color: str = "#9aa5b1") -> str:
    """Return an SVG line."""

    return (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="{color}" stroke-width="1" />'
    )


def _circle(x: float, y: float, color: str, radius: float = 4.0) -> str:
    """Return an SVG circle marker."""

    return (
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" '
        f'fill="{color}" stroke="#1f2933" stroke-width="0.6" />'
    )


def _cross(x: float, y: float, color: str = "#b91c1c") -> str:
    """Return an SVG cross marker for unavailable points."""

    return (
        f'<path d="M{x - 4:.1f},{y - 4:.1f} L{x + 4:.1f},{y + 4:.1f} '
        f'M{x + 4:.1f},{y - 4:.1f} L{x - 4:.1f},{y + 4:.1f}" '
        f'stroke="{color}" stroke-width="1.8" />'
    )


def _linear_scale(value: float, source_min: float, source_max: float, target_min: float, target_max: float) -> float:
    """Map a value linearly between source and target intervals."""

    if source_max == source_min:
        return (target_min + target_max) / 2.0
    fraction = (value - source_min) / (source_max - source_min)
    return target_min + fraction * (target_max - target_min)


def _finite_log_values(series: list[dict[str, Any]], field: str) -> list[float]:
    """Return finite positive log10 values for a field."""

    values: list[float] = []
    for item in series:
        for value in item[field]:
            if value is not None and value > 0:
                values.append(math.log10(float(value)))
    return values


def build_rank_feasibility_heatmap_svg(payload: dict[str, Any]) -> str:
    """Return an SVG preview of rank-feasibility heatmap panels."""

    panels = payload["rank_feasibility_heatmap"]["panels"]
    width = 900
    panel_height = 190
    height = 95 + panel_height * len(panels)
    body = [
        _text(24, 30, "V24 CRLB Rank-Feasibility Preview", "title"),
        _text(24, 50, "Non-final diagnostic: green cells are full-rank; red cells are unavailable CRLB cases.", "subtitle"),
        _text(24, 70, "Cell text is FIM rank / parameter dimension.", "note"),
    ]
    for panel_index, panel in enumerate(panels):
        top = 95 + panel_index * panel_height
        users = panel["num_users_axis"]
        satellites = panel["num_satellites_axis"]
        full_rank = panel["full_rank_matrix"]
        ranks = panel["fim_rank_matrix"]
        dims = panel["parameter_dim_matrix"]
        left = 95
        cell_w = 82
        cell_h = 32
        body.append(_text(24, top, f"Link pattern: {panel['link_pattern']}", "title"))
        for col, ns_value in enumerate(satellites):
            body.append(_text(left + col * cell_w + cell_w / 2, top + 24, f"Ns={ns_value}", "axis", "middle"))
        for row, nu_value in enumerate(users):
            y = top + 35 + row * cell_h
            body.append(_text(24, y + 21, f"Nu={nu_value}", "axis"))
            for col, _ns_value in enumerate(satellites):
                x = left + col * cell_w
                fill = "#d8f3dc" if full_rank[row][col] else "#fee2e2"
                stroke = "#2f855a" if full_rank[row][col] else "#b91c1c"
                body.append(
                    f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell_w - 6:.1f}" '
                    f'height="{cell_h - 6:.1f}" fill="{fill}" stroke="{stroke}" />'
                )
                body.append(
                    _text(
                        x + (cell_w - 6) / 2,
                        y + 18,
                        f"{ranks[row][col]}/{dims[row][col]}",
                        "axis",
                        "middle",
                    )
                )
    return _svg(width, height, "\n".join(body))


def _build_metric_series_svg(
    payload: dict[str, Any],
    *,
    field: str,
    title: str,
    y_label: str,
    output_note: str,
) -> str:
    """Return an SVG preview for finite CRLB-vs-Ns metric series."""

    series = payload["finite_crlb_vs_ns"]["series"]
    log_values = _finite_log_values(series, field)
    min_log = min(log_values)
    max_log = max(log_values)
    if min_log == max_log:
        min_log -= 0.5
        max_log += 0.5
    width = 980
    panel_height = 195
    link_patterns = sorted({item["link_pattern"] for item in series})
    height = 95 + panel_height * len(link_patterns)
    colors = {2: "#1d4ed8", 3: "#047857", 4: "#9333ea"}
    body = [
        _text(24, 30, title, "title"),
        _text(24, 50, "Non-final diagnostic preview. Crosses mark rank-deficient unavailable points.", "subtitle"),
        _text(24, 70, output_note, "note"),
    ]
    for panel_index, link_pattern in enumerate(link_patterns):
        top = 95 + panel_index * panel_height
        left = 80
        right = width - 160
        bottom = top + 135
        plot_top = top + 25
        items = sorted(
            [item for item in series if item["link_pattern"] == link_pattern],
            key=lambda item: item["num_users"],
        )
        ns_values = items[0]["num_satellites"]
        body.append(_text(24, top, f"Link pattern: {link_pattern}", "title"))
        body.append(_line(left, bottom, right, bottom))
        body.append(_line(left, plot_top, left, bottom))
        body.append(_text(24, plot_top + 10, y_label, "small"))
        for ns_value in ns_values:
            x = _linear_scale(float(ns_value), min(ns_values), max(ns_values), left, right)
            body.append(_line(x, bottom, x, bottom + 4))
            body.append(_text(x, bottom + 18, str(ns_value), "axis", "middle"))
        body.append(_text((left + right) / 2, bottom + 38, "number of satellites, Ns", "axis", "middle"))
        for item in items:
            color = colors.get(int(item["num_users"]), "#374151")
            previous: tuple[float, float] | None = None
            unavailable_y = bottom - 7
            for index, ns_value in enumerate(item["num_satellites"]):
                x = _linear_scale(float(ns_value), min(ns_values), max(ns_values), left, right)
                value = item[field][index]
                if value is None:
                    body.append(_cross(x, unavailable_y))
                    previous = None
                    continue
                y = _linear_scale(math.log10(float(value)), min_log, max_log, bottom, plot_top)
                if previous is not None:
                    body.append(_line(previous[0], previous[1], x, y, color))
                body.append(_circle(x, y, color))
                previous = (x, y)
            legend_x = right + 24
            legend_y = plot_top + 18 + 20 * (int(item["num_users"]) - 2)
            body.append(_circle(legend_x, legend_y - 4, color, 4))
            body.append(_text(legend_x + 12, legend_y, f"Nu={item['num_users']}", "axis"))
    return _svg(width, height, "\n".join(body))


def build_finite_crlb_peb_svg(payload: dict[str, Any]) -> str:
    """Return a finite CRLB-vs-Ns UE PEB SVG preview."""

    return _build_metric_series_svg(
        payload,
        field="average_ue_peb_km",
        title="Finite V24 CRLB-vs-Ns Preview: UE PEB",
        y_label="log10 average UE PEB [km]",
        output_note="Growing Ns changes parameter dimension; no monotonic trend is claimed.",
    )


def build_finite_crlb_clock_svg(payload: dict[str, Any]) -> str:
    """Return a finite CRLB-vs-Ns clock-bound SVG preview."""

    return _build_metric_series_svg(
        payload,
        field="average_clock_bound_s",
        title="Finite V24 CRLB-vs-Ns Preview: Clock Bound",
        y_label="log10 average clock bound [s]",
        output_note="Growing Ns adds nuisance clock states; unavailable points remain marked.",
    )


def build_fixed_measurement_addition_svg(payload: dict[str, Any]) -> str:
    """Return an SVG preview of fixed-parameter measurement addition."""

    fixed = payload["fixed_parameter_measurement_addition"]
    width = 900
    height = 300
    left = 80
    right = width - 170
    top = 85
    bottom = 230
    counts = [int(value) for value in fixed["measurement_count"]]
    fields = [
        ("average_ue_peb_km", "#1d4ed8", "UE PEB [km]"),
        ("average_clock_bound_s", "#047857", "clock bound [s]"),
    ]
    log_values: list[float] = []
    for field, _color, _label in fields:
        for value in fixed[field]:
            if value is not None and value > 0:
                log_values.append(math.log10(float(value)))
    min_log = min(log_values)
    max_log = max(log_values)
    body = [
        _text(24, 30, "Fixed-Parameter Measurement-Addition Preview", "title"),
        _text(24, 50, "Non-final diagnostic: monotonicity is checked only after full rank is reached.", "subtitle"),
        _text(24, 70, f"Nu={fixed['num_users']}, Ns={fixed['num_satellites']}, parameter dim={fixed['parameter_dim']}", "note"),
        _line(left, bottom, right, bottom),
        _line(left, top, left, bottom),
        _text(24, top + 10, "log10 bound value", "small"),
    ]
    for count in counts:
        x = _linear_scale(float(count), min(counts), max(counts), left, right)
        body.append(_line(x, bottom, x, bottom + 4))
        body.append(_text(x, bottom + 18, str(count), "axis", "middle"))
    body.append(_text((left + right) / 2, bottom + 38, "measurement count", "axis", "middle"))
    for field, color, label in fields:
        previous: tuple[float, float] | None = None
        for index, count in enumerate(counts):
            x = _linear_scale(float(count), min(counts), max(counts), left, right)
            value = fixed[field][index]
            if value is None:
                body.append(_cross(x, bottom - 7))
                previous = None
                continue
            y = _linear_scale(math.log10(float(value)), min_log, max_log, bottom, top)
            if previous is not None:
                body.append(_line(previous[0], previous[1], x, y, color))
            body.append(_circle(x, y, color))
            previous = (x, y)
        legend_x = right + 24
        legend_y = top + 25 + 24 * fields.index((field, color, label))
        body.append(_circle(legend_x, legend_y - 4, color, 4))
        body.append(_text(legend_x + 12, legend_y, label, "axis"))
    return _svg(width, height, "\n".join(body))


def load_candidate_data(input_path: str | Path = DEFAULT_INPUT_PATH) -> dict[str, Any]:
    """Load non-final CRLB figure-candidate JSON."""

    path = Path(input_path)
    return json.loads(path.read_text(encoding="utf-8"))


def build_preview_manifest(payload: dict[str, Any], output_paths: list[Path]) -> dict[str, Any]:
    """Return a manifest describing non-final CRLB preview outputs."""

    return {
        "diagnostic_type": "non_final_v24_crlb_preview_manifest",
        "schema_version": 1,
        "generated_marker": "deterministic_no_timestamp",
        "preview_policy": PREVIEW_POLICY,
        "source_diagnostic_type": payload["diagnostic_type"],
        "source_schema_version": payload["schema_version"],
        "source_generated_marker": payload["generated_marker"],
        "outputs": [
            {
                "path": str(path.as_posix()),
                "kind": "svg_preview",
                "non_final": True,
            }
            for path in output_paths
        ],
        "human_review_required": True,
        "manuscript_figure": False,
    }


def write_crlb_preview_outputs(
    *,
    input_path: str | Path = DEFAULT_INPUT_PATH,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    overwrite: bool = True,
) -> dict[str, Any]:
    """Write non-final CRLB preview SVGs and a JSON manifest."""

    payload = load_candidate_data(input_path)
    output_root = Path(output_dir)
    outputs = [
        (
            output_root / "rank_feasibility_heatmap_preview.svg",
            build_rank_feasibility_heatmap_svg(payload),
        ),
        (
            output_root / "finite_crlb_vs_ns_ue_peb_preview.svg",
            build_finite_crlb_peb_svg(payload),
        ),
        (
            output_root / "finite_crlb_vs_ns_clock_preview.svg",
            build_finite_crlb_clock_svg(payload),
        ),
        (
            output_root / "fixed_measurement_addition_preview.svg",
            build_fixed_measurement_addition_svg(payload),
        ),
    ]
    written_paths = [_write_text(path, text, overwrite=overwrite) for path, text in outputs]
    manifest = build_preview_manifest(payload, written_paths)
    manifest_path = output_root / "preview_manifest.json"
    manifest["manifest_path"] = str(manifest_path.as_posix())
    _write_text(
        manifest_path,
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        overwrite=overwrite,
    )
    return manifest


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--no-overwrite", action="store_true")
    return parser.parse_args()


def main() -> int:
    """Run the non-final V24 CRLB preview writer."""

    args = _parse_args()
    manifest = write_crlb_preview_outputs(
        input_path=args.input,
        output_dir=args.output_dir,
        overwrite=not args.no_overwrite,
    )
    print(f"Wrote non-final V24 CRLB preview manifest: {manifest['manifest_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
