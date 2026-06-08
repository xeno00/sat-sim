"""Write non-final figure replacement and legacy-to-package port plans."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SAT_SIM_ROOT = Path(__file__).resolve().parents[1]
REPORTS = SAT_SIM_ROOT / "outputs" / "reports"


def _figure_plan() -> dict[str, Any]:
    """Return figure-family replacement classifications."""

    figures = [
        {
            "figure": "Fig. 2 LOS CRLB localization",
            "target_artifact": "pos_crlb_0dB_0dB.pdf",
            "classification": ["legacy_provenance_only", "needs_v24_clean_replacement"],
            "current_best_visual": "outputs/legacy_replay/crlb_los/pos_crlb_0dB_0dB.pdf",
            "reason": "LOS CRLB replay has corrected legends but preserves legacy all-clock/post-hoc bound extraction.",
        },
        {
            "figure": "Fig. 3 LOS CRLB synchronization",
            "target_artifact": "sync_crlb_0dB_0dB.pdf",
            "classification": ["legacy_provenance_only", "needs_v24_clean_replacement"],
            "current_best_visual": "outputs/legacy_replay/crlb_los/sync_crlb_0dB_0dB.pdf",
            "reason": "Legacy sync CRLB uses all-clock/post-hoc slicing and is not V24-gauge clean.",
        },
        {
            "figure": "Fig. 4 localization vs satellites",
            "target_artifact": "pos_vary_ues.pdf",
            "classification": ["current_best_visual_evidence", "candidate_for_human_review", "needs_v24_clean_replacement"],
            "current_best_visual": "outputs/legacy_replay/network_size_medium/pos_vary_ues.pdf",
            "reason": "Medium legacy-compatible replay visibly tests JCLS benefit, but remains all-clock/truth-gated legacy behavior.",
        },
        {
            "figure": "Fig. 5 synchronization vs satellites",
            "target_artifact": "sync_vary_ues.pdf",
            "classification": ["current_best_visual_evidence", "candidate_for_human_review", "needs_v24_clean_replacement"],
            "current_best_visual": "outputs/legacy_replay/network_size_medium/sync_vary_ues.pdf",
            "reason": "Medium legacy-compatible replay is the best visual evidence, but the metric remains legacy all-clock synchronization.",
        },
        {
            "figure": "Fig. 6 localization vs clock standard deviation",
            "target_artifact": "pos_vary_clock.pdf",
            "classification": ["current_best_visual_evidence", "legacy_provenance_only", "needs_v24_clean_replacement"],
            "current_best_visual": "outputs/legacy_replay/clock_sweep_full/pos_vary_clock.pdf",
            "reason": "Full legacy clock-sweep replay shows the intended qualitative behavior but uses truth-gated legacy estimation.",
        },
        {
            "figure": "Fig. 7 synchronization vs clock standard deviation",
            "target_artifact": "sync_vary_clock.pdf",
            "classification": ["current_best_visual_evidence", "legacy_provenance_only", "needs_v24_clean_replacement"],
            "current_best_visual": "outputs/legacy_replay/clock_sweep_full/sync_vary_clock.pdf",
            "reason": "Full legacy clock-sweep replay is visually useful but uses legacy all-clock synchronization metrics.",
        },
        {
            "figure": "NLOS CRLB variants",
            "target_artifact": "pos_crlb_nlos.pdf / sync_crlb_nlos.pdf",
            "classification": ["needs_nlos_model_design"],
            "current_best_visual": None,
            "reason": "No executable legacy Rayleigh/NLOS or package score-covariance NLOS FIM path currently exists.",
        },
    ]
    return {
        "artifact_status": "non_final_v24_figure_replacement_plan",
        "manuscript_ready_count": 0,
        "no_figure_marked_manuscript_ready": True,
        "figures": figures,
        "recommendation": (
            "Use legacy-compatible outputs as visual/provenance evidence only. "
            "Port the successful staged-estimation behavior into package-native V24 before manuscript replacement."
        ),
    }


def _port_plan() -> dict[str, Any]:
    """Return legacy-to-package port plan."""

    techniques = [
        {
            "technique": "clockless IL/GN preconditioning",
            "legacy_behavior": "Initialize UE positions with reduced/clockless equations before the full-clock solve.",
            "why_it_helped": "Keeps the nonlinear full-clock solve from starting too far from the geometry.",
            "scientifically_defensible": True,
            "v24_port": "Implement as a package-native Step 1 initializer using measurement residual cost only, then lift into the gauged V24 theta vector.",
            "tests_required": ["hand-computed DL-only initialization fixture", "no truth-state access", "improves or does not worsen residual in deterministic toy cases"],
        },
        {
            "technique": "full-clock internal solve with gauge-relative reporting",
            "legacy_behavior": "Solve an all-clock symbolic state, then report position/synchronization errors after post-processing.",
            "why_it_helped": "The optimizer had enough internal degrees of freedom to absorb clock biases.",
            "scientifically_defensible": True,
            "v24_port": "Use the explicit V24 gauged parameter vector internally, not all-clock state; report clocks relative to the reference satellite.",
            "tests_required": ["parameter order test", "reference satellite column absent", "sync metric excludes reference satellite"],
        },
        {
            "technique": "pseudoinverse / rank-tolerant updates",
            "legacy_behavior": "Use rank-tolerant linear algebra and dependent-row handling in difficult geometries.",
            "why_it_helped": "Prevents brittle failures in underconstrained or nearly singular intermediate stages.",
            "scientifically_defensible": True,
            "v24_port": "Allow rank-tolerant damped updates as diagnostic/non-successful initializers; do not report finite CRLB unless subspace estimability is proven.",
            "tests_required": ["rank-deficient status test", "finite CRLB only for full rank", "damped update never mislabeled as convergence"],
        },
        {
            "technique": "LM damping behavior",
            "legacy_behavior": "Use LM-style damping in the full nonlinear solve.",
            "why_it_helped": "Stabilizes nonlinear TOA residual minimization compared with raw Gauss-Newton.",
            "scientifically_defensible": True,
            "v24_port": "Package-native LM with accepted-step criteria based on weighted residual decrease and bounded step norms.",
            "tests_required": ["weighted residual decreases on accepted steps", "damping adapts deterministically", "no manuscript figure generated by unit tests"],
        },
        {
            "technique": "truth-gated acceptance replacement",
            "legacy_behavior": "Some LM/MAP acceptance or fallback decisions compare against true state error.",
            "why_it_helped": "Can suppress bad-looking estimates in replay plots, but leaks oracle information.",
            "scientifically_defensible": False,
            "v24_port": "Replace with observable criteria: weighted measurement residual, prior innovation, covariance trace, and consistency gates.",
            "tests_required": ["grep/no true-state access in estimator", "acceptance depends only on z/h/R/P/Q", "synthetic failure fallback is logged"],
        },
        {
            "technique": "MAP/global fallback behavior",
            "legacy_behavior": "Fallback paths keep a usable trajectory when a solver stage fails.",
            "why_it_helped": "Avoids catastrophic rows dominating small Monte Carlo grids.",
            "scientifically_defensible": True,
            "v24_port": "Implement explicit fallback hierarchy with status flags; include failed/fallback rows in diagnostics instead of hiding them.",
            "tests_required": ["fallback count test", "failure log test", "summary preserves non-success statuses"],
        },
        {
            "technique": "display smoothing/fitting separation",
            "legacy_behavior": "Plotting cells smooth or manually transform displayed curves.",
            "why_it_helped": "Improves visual readability but can obscure raw algorithm behavior.",
            "scientifically_defensible": True,
            "v24_port": "Keep raw CSV/NPZ as the authority; any smoothing must be a separate display transform recorded in metadata.",
            "tests_required": ["raw/display arrays both saved", "metadata records transform", "no smoothing in algorithm metrics"],
        },
    ]
    return {
        "artifact_status": "non_final_legacy_to_package_port_plan",
        "techniques": techniques,
        "recommendation": "Port estimator behavior before rerunning final manuscript figures; do not port truth-gated decisions.",
    }


def write_reports() -> dict[str, Any]:
    """Write Markdown and JSON reports."""

    REPORTS.mkdir(parents=True, exist_ok=True)
    figure = _figure_plan()
    port = _port_plan()
    (REPORTS / "V24_FIGURE_REPLACEMENT_PLAN.json").write_text(json.dumps(figure, indent=2), encoding="utf-8")
    (REPORTS / "LEGACY_TO_PACKAGE_PORT_PLAN.json").write_text(json.dumps(port, indent=2), encoding="utf-8")

    figure_md = [
        "# V24 Figure Replacement Plan",
        "",
        "## Executive Summary",
        figure["recommendation"],
        "",
        "No figure is marked manuscript-ready.",
        "",
        "| Figure | Classification | Current best visual | Reason |",
        "|---|---|---|---|",
    ]
    for item in figure["figures"]:
        visual = item["current_best_visual"] or "none"
        if item["current_best_visual"]:
            visual = f"[{visual}](../{item['current_best_visual'].replace('outputs/', '')})"
        figure_md.append(f"| {item['figure']} | {', '.join(item['classification'])} | {visual} | {item['reason']} |")
    (REPORTS / "V24_FIGURE_REPLACEMENT_PLAN.md").write_text("\n".join(figure_md) + "\n", encoding="utf-8")

    port_md = [
        "# Legacy-To-Package Port Plan",
        "",
        "## Executive Summary",
        port["recommendation"],
        "",
        "| Technique | Legacy behavior | Why it helped | Defensible? | V24 port | Tests required |",
        "|---|---|---|---:|---|---|",
    ]
    for item in port["techniques"]:
        port_md.append(
            "| {technique} | {legacy_behavior} | {why_it_helped} | {scientifically_defensible} | {v24_port} | {tests_required} |".format(
                **{**item, "tests_required": "; ".join(item["tests_required"])}
            )
        )
    (REPORTS / "LEGACY_TO_PACKAGE_PORT_PLAN.md").write_text("\n".join(port_md) + "\n", encoding="utf-8")
    return {"figure": figure, "port": port}


def main() -> int:
    payload = write_reports()
    print(json.dumps({"status": "wrote", "reports": ["V24_FIGURE_REPLACEMENT_PLAN", "LEGACY_TO_PACKAGE_PORT_PLAN"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
