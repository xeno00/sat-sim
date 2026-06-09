"""Build the result lineage and units review reports.

The report is intentionally conservative: it records known system/stage
versions and unit paths, and marks missing benchmark data explicitly instead of
inferring across incompatible figure families.
"""

from __future__ import annotations

import csv
import json
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "outputs" / "reports"
REGISTRY = ROOT / "outputs" / "registry"
STANDARD_CASE_ID = "std_nu3_ns4_fullmesh_los_clock1us_seed0"
C_KM_PER_S = 299_792.458


def repo_rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read_json(path: str) -> dict[str, Any]:
    full = ROOT / path
    if not full.exists():
        return {}
    return json.loads(full.read_text(encoding="utf-8"))


def read_csv(path: str) -> list[dict[str, str]]:
    full = ROOT / path
    if not full.exists():
        return []
    with full.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def first_row(rows: list[dict[str, str]], **criteria: str) -> dict[str, str] | None:
    for row in rows:
        if all(row.get(key) == value for key, value in criteria.items()):
            return row
    return None


def to_float(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def km_clock_to_ns(value: str | None) -> float | None:
    raw = to_float(value)
    if raw is None:
        return None
    return raw / C_KM_PER_S * 1e9


def fmt(value: Any) -> str:
    if value is None:
        return "unknown"
    if isinstance(value, float):
        if abs(value) >= 1e4 or (abs(value) < 1e-3 and value != 0):
            return f"{value:.3e}"
        return f"{value:.6g}"
    if isinstance(value, list):
        return "; ".join(str(item) for item in value)
    return str(value)


def git_value(*args: str) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


@dataclass
class ResultFamily:
    result_family: str
    output_root: str
    branch: str
    commit: str
    generating_script: str
    system_model_version: str
    stage_a_version: str
    stage_b_version: str
    stage_c_version: str
    pipeline_class: str
    truth_usage: str
    units_status: str
    standard_case_id: str
    standard_case_stage_a_pos_m: float | None
    standard_case_stage_b_pos_m: float | None
    standard_case_stage_c_pos_m: float | None
    standard_case_stage_a_sync_ns: float | None
    standard_case_stage_b_sync_ns: float | None
    standard_case_stage_c_sync_ns: float | None
    rough_performance_tag: str
    readiness: str
    recommended_use: str
    quarantine_reason: str


def build_result_families() -> list[ResultFamily]:
    current_branch = git_value("branch", "--show-current")
    current_commit = git_value("rev-parse", "--short", "HEAD")

    step_b_row = first_row(
        read_csv("outputs/migration_ladder/step_b_lm_residual_acceptance/medium/migration_raw.csv"),
        num_users="3",
        num_satellites="4",
    )
    c7_row = first_row(
        read_csv("outputs/step_c7_residual_cov_sync_safeguard/raw.csv"),
        candidate="step_c7_residual_cov_sync_safeguard",
        num_users="3",
        num_satellites="4",
    )
    recreation_rows = read_csv("outputs/c7_manuscript_figure_recreation/raw.csv")
    recreation_b = first_row(
        recreation_rows,
        family="network_size",
        num_users="3",
        num_satellites="4",
        baseline_id="coarse_jcls",
    )
    recreation_c = first_row(
        recreation_rows,
        family="network_size",
        num_users="3",
        num_satellites="4",
        baseline_id="refined_jcls",
    )
    candidate_report = read_json("outputs/reports/C7_CANDIDATE_FIGURE_VALIDATION_REPORT.json")
    c7_report = read_json("outputs/reports/STEP_C7_RESIDUAL_COV_SYNC_SAFEGUARD_REPORT.json")
    network_report = read_json("outputs/reports/LEGACY_NETWORK_SIZE_REPLAY_REPORT.json")
    clock_report = read_json("outputs/legacy_replay/clock_sweep_full/legacy_clock_sweep_metadata.json")
    crlb_report = read_json("outputs/reports/CRLB_LOS_REPLAY_REPORT.json")

    families = [
        ResultFamily(
            "original_notebook_manuscript_results",
            "Work-In-Progress/Figures/GeneratePSFrag",
            "manual_manuscript_storage",
            "not_git_tracked",
            "JCLS_Simulation.ipynb original figure cells",
            "legacy_all_clock_notebook",
            "A0_legacy_il_clockless_preconditioning",
            "B0_legacy_lm_truth_gate",
            "C0_legacy_truth_cov_ekf",
            "legacy_final_artifact",
            "truth gates/covariance suspected from legacy notebook path; exact manuscript artifact lineage not fully executable",
            "units_uncertain",
            STANDARD_CASE_ID,
            None,
            None,
            None,
            None,
            None,
            None,
            "unknown",
            "quarantine_until_reconciled",
            "legacy_reference_only",
            "Manuscript artifacts predate the current tested provenance stack and mix legacy all-clock/truth-gated behavior.",
        ),
        ResultFamily(
            "legacy_clock_sweep_replay",
            "outputs/legacy_replay/clock_sweep_full",
            "codex/legacy-clock-sweep-replay",
            "unknown_not_recorded",
            "scripts/replay_legacy_clock_sweep_figures.py --full",
            "legacy_all_clock_notebook",
            "A0_legacy_il_clockless_preconditioning",
            "B0_legacy_lm_truth_gate",
            "C0_legacy_truth_cov_ekf",
            "legacy",
            "truth-error LM/MAP acceptance and legacy fallbacks used; full notebook not executed",
            "units_consistent_but_legacy",
            "clock_sweep_nu3_ns10_legacy_full",
            clock_report.get("per_clock_std_results", [{}])[2].get("il_position_error_m") if clock_report.get("per_clock_std_results") else None,
            clock_report.get("per_clock_std_results", [{}])[2].get("lm_position_error_m") if clock_report.get("per_clock_std_results") else None,
            clock_report.get("per_clock_std_results", [{}])[2].get("map_position_error_m") if clock_report.get("per_clock_std_results") else None,
            (clock_report.get("per_clock_std_results", [{}])[2].get("il_sync_error_s") or 0) * 1e9 if clock_report.get("per_clock_std_results") else None,
            (clock_report.get("per_clock_std_results", [{}])[2].get("lm_sync_error_s") or 0) * 1e9 if clock_report.get("per_clock_std_results") else None,
            (clock_report.get("per_clock_std_results", [{}])[2].get("map_sync_error_s") or 0) * 1e9 if clock_report.get("per_clock_std_results") else None,
            "legacy clock sweep reproduces executable behavior but uses oracle gates/fallbacks",
            "legacy_reference_only",
            "legacy_reference_only",
            "Truth-gated acceptance, all-clock state, and legacy synchronization metric are unsafe for V24 evidence.",
        ),
        ResultFamily(
            "legacy_network_size_replay",
            "outputs/legacy_replay/network_size_medium",
            network_report.get("branch", "codex/legacy-network-size-and-v24-port-plan"),
            network_report.get("commit", "unknown_not_recorded"),
            "scripts/replay_legacy_network_size_figures.py --medium",
            "legacy_all_clock_notebook",
            "A0_legacy_il_clockless_preconditioning",
            "B0_legacy_lm_truth_gate",
            "C0_legacy_truth_cov_ekf",
            "legacy",
            "truth gates/fallbacks used in legacy estimator path",
            "units_consistent_but_legacy",
            "legacy_medium_nu3_ns4_clock0p5ns_seed2042",
            None,
            None,
            None,
            None,
            None,
            None,
            "legacy medium replay improves JCLS in 9/9 baseline comparisons",
            "legacy_reference_only",
            "legacy_reference_only",
            "Legacy all-clock/truth-gated path is provenance, not V24-clean evidence.",
        ),
        ResultFamily(
            "legacy_crlb_los_replay",
            "outputs/legacy_replay/crlb_los",
            "codex/legacy-crlb-figure-replay",
            "unknown_not_recorded",
            "scripts/replay_legacy_crlb_figures.py",
            "legacy_all_clock_crlb",
            "not_applicable",
            "not_applicable",
            "not_applicable",
            "legacy_diagnostic",
            "no estimator truth gate, but all-clock/post-hoc CRLB slicing preserved",
            "units_consistent_but_legacy",
            "not_applicable_crlb_curve",
            None,
            None,
            None,
            None,
            None,
            None,
            "legacy CRLB replay; not V24-clean",
            "legacy_reference_only",
            "legacy_reference_only",
            "All-clock/post-hoc CRLB path is incompatible with current V24 gauged FIM requirements.",
        ),
        ResultFamily(
            "step_b_lm_only_results",
            "outputs/migration_ladder/step_b_lm_residual_acceptance/medium",
            "codex/migration-step-b-lm-no-truth-gate",
            "unknown_not_recorded",
            "scripts/run_controlled_migration_ladder.py --step step_b_lm_residual_acceptance --medium",
            "legacy_compatible_all_clock",
            "A0_legacy_il_clockless_preconditioning",
            "B1_residual_lm",
            "C_none_or_legacy_fallback_disabled_for_lm_only_readout",
            "diagnostic",
            "LM truth acceptance removed; later legacy MAP fields in CSV are not used as Step B evidence",
            "units_consistent_but_legacy",
            STANDARD_CASE_ID,
            to_float(step_b_row.get("il_position_error_m") if step_b_row else None),
            to_float(step_b_row.get("lm_position_error_m") if step_b_row else None),
            None,
            (to_float(step_b_row.get("il_sync_error_s") if step_b_row else None) or 0) * 1e9 if step_b_row else None,
            (to_float(step_b_row.get("lm_sync_error_s") if step_b_row else None) or 0) * 1e9 if step_b_row else None,
            None,
            "healthy clean baseline on controlled migration grid",
            "use_for_human_review",
            "use_for_human_review",
            "",
        ),
        ResultFamily(
            "c7_residual_cov_sync_safeguard",
            "outputs/step_c7_residual_cov_sync_safeguard",
            "codex/step-c7-residual-cov-sync-safeguard",
            "89a9b2a",
            "scripts/run_step_c7_residual_cov_sync_safeguard.py",
            "package_native_current",
            "A1_package_dl_only",
            "B1_residual_lm",
            "C7_residual_cov_sync_safeguard",
            "diagnostic",
            "truth used only for offline metrics; no truth acceptance/covariance/safeguard",
            "units_consistent",
            STANDARD_CASE_ID,
            None,
            to_float(c7_row.get("step_b_position_error_m") if c7_row else None),
            to_float(c7_row.get("c7_position_error_m") if c7_row else None),
            None,
            km_clock_to_ns(c7_row.get("step_b_sync_error_km") if c7_row else None),
            km_clock_to_ns(c7_row.get("c7_sync_error_km") if c7_row else None),
            "centimeter-level toy/medium diagnostic on selected standard row",
            "use_for_human_review",
            "use_for_human_review",
            "",
        ),
        ResultFamily(
            "c7_candidate_figure_validation",
            "outputs/c7_candidate_figures",
            "codex/c7-candidate-figure-validation",
            "04ba189",
            "scripts/run_c7_candidate_figures.py",
            "package_native_current",
            "A1_package_dl_only",
            "B1_residual_lm",
            "C7_residual_cov_sync_safeguard",
            "candidate",
            "truth used only for offline metrics; no truth acceptance/covariance/safeguard",
            "units_consistent",
            "bounded_network_grid_and_sparse_clock_sweep",
            None,
            None,
            None,
            None,
            None,
            None,
            f"network mean ratios pos={candidate_report.get('network_summary', {}).get('mean_position_ratio')}, sync={candidate_report.get('network_summary', {}).get('mean_sync_ratio')}; clock sweep blocked",
            "use_for_human_review",
            "use_for_human_review",
            "Sparse clock-sweep localization instability blocks manuscript use.",
        ),
        ResultFamily(
            "c7_manuscript_figure_recreation",
            "outputs/c7_manuscript_figure_recreation",
            current_branch,
            current_commit,
            "scripts/run_c7_manuscript_figure_recreation.py",
            "package_native_current_manuscript_style_geometry",
            "A1_package_dl_only",
            "B1_residual_lm",
            "C7_residual_cov_sync_safeguard",
            "candidate",
            "truth used only for offline metrics; no truth acceptance/covariance/safeguard; notebook not executed",
            "units_consistent",
            "network_nu3_ns4_clock1us_trial0",
            None,
            to_float(recreation_b.get("position_error_mean_m") if recreation_b else None),
            to_float(recreation_c.get("position_error_mean_m") if recreation_c else None),
            None,
            to_float(recreation_b.get("sync_error_ns") if recreation_b else None),
            to_float(recreation_c.get("sync_error_ns") if recreation_c else None),
            "network-size figures human-review only; clock sweep candidate failed",
            "use_for_human_review",
            "use_for_human_review",
            "Clock-sweep family remains diagnostic/candidate-failed because high-clock rows worsen localization.",
        ),
        ResultFamily(
            "wave_results_exploration",
            "not_found",
            "not_found",
            "not_found",
            "not_found",
            "unknown",
            "unknown",
            "unknown",
            "unknown",
            "not_found",
            "unknown",
            "units_uncertain",
            STANDARD_CASE_ID,
            None,
            None,
            None,
            None,
            None,
            None,
            "no wave-results output root found in repository inventory",
            "quarantine_until_reconciled",
            "do_not_use",
            "Required family name was requested, but no matching output artifacts were found.",
        ),
        ResultFamily(
            "package_native_suspect_fig4_7_outputs",
            "v24_figure_outputs",
            "codex/package-native-figures-4-7",
            "unknown_not_recorded",
            "scripts/run_package_native_figures_4_7.py",
            "package_native_current_synthetic_static",
            "A1_package_dl_only",
            "B1_residual_lm",
            "generic_dynamic_sci_sfi",
            "diagnostic",
            "truth used only for offline metrics, but algorithm fidelity unresolved",
            "units_consistent",
            "unknown_needs_review",
            None,
            None,
            None,
            None,
            None,
            None,
            "package-native suspect Fig. 4-7 diagnostics conflict with manuscript narrative",
            "quarantine_until_reconciled",
            "use_for_debugging_only",
            "Synthetic geometry/noise and algorithm fidelity were unresolved; outputs are suspect diagnostics only.",
        ),
        ResultFamily(
            "manuscript_candidate_geometry_noise_outputs",
            "v24_manuscript_candidate_outputs",
            "codex/manuscript-geometry-noise",
            "unknown_not_recorded",
            "scripts/run_v24_manuscript_candidate_figures.py",
            "package_native_mit_stata_leo_synthetic",
            "A1_package_dl_only",
            "B1_residual_lm",
            "generic_dynamic_sci_sfi",
            "candidate",
            "truth used only for offline metrics, but estimator robustness unresolved",
            "units_consistent",
            "unknown_needs_review",
            None,
            None,
            None,
            None,
            None,
            None,
            "closer geometry/noise, still not final",
            "quarantine_until_reconciled",
            "use_for_debugging_only",
            "Synthetic satellite geometry, estimator robustness, and numerical behavior remain unresolved.",
        ),
        ResultFamily(
            "human_review_fig4_7_outputs",
            "v24_human_review_outputs",
            "codex/human-ready-figures-sprint",
            "unknown_not_recorded",
            "scripts/run_human_review_figures.py",
            "package_native_human_review",
            "A1_package_dl_only",
            "B1_residual_lm",
            "generic_dynamic_sci_sfi",
            "diagnostic",
            "truth used only for offline metrics; not final",
            "units_consistent",
            "unknown_needs_review",
            None,
            None,
            None,
            None,
            None,
            None,
            "human-review package conflicts with manuscript narrative in several regimes",
            "quarantine_until_reconciled",
            "use_for_debugging_only",
            "JCLS success rates were low and refined JCLS could underperform baseline.",
        ),
        ResultFamily(
            "gnss_baseline_exploration",
            "not_found",
            "not_found",
            "not_found",
            "not_found",
            "unknown",
            "unknown",
            "unknown",
            "unknown",
            "not_found",
            "unknown",
            "units_uncertain",
            STANDARD_CASE_ID,
            None,
            None,
            None,
            None,
            None,
            None,
            "no GNSS/baseline exploration output root found in repository inventory",
            "quarantine_until_reconciled",
            "do_not_use",
            "Required family was requested if present; no matching output artifacts were found.",
        ),
    ]
    return families


def build_units_review() -> list[dict[str, Any]]:
    return [
        {
            "pipeline_family": "legacy_notebook_and_legacy_replays",
            "position_units": {
                "internal_ue_position_units": "km",
                "internal_satellite_position_units": "km",
                "output_localization_metric_units": "m",
                "plotted_localization_conversion": "legacy position error km multiplied by 1000 where plotting/reporting expects meters",
            },
            "clock_units": {
                "internal_clock_state_units": "range-equivalent km",
                "clock_sigma_input_units": "seconds in notebook clock-sweep inputs",
                "clock_sigma_internal_units": "range-equivalent km after speed-of-light conversion in legacy logic",
                "synchronization_error_output_units": "seconds/raw or ns/plotted depending on replay",
                "clock_error_conversion": "range-equivalent km divided by c_km_per_s, then multiplied by 1e9 for ns plots",
            },
            "measurement_units": {
                "measurement_vector_units": "km",
                "measurement_model_units": "km",
                "measurement_covariance_units": "km^2",
                "jacobian_units": "position columns dimensionless; clock columns dimensionless for range-equivalent clocks",
            },
            "unit_risk_verdict": "units_consistent_but_legacy",
            "notes": "Executable fixtures verified row order and km/range-clock representation for tiny cases, but legacy all-clock/truth-gated behavior remains unsafe.",
        },
        {
            "pipeline_family": "package_native_current_and_c7",
            "position_units": {
                "internal_ue_position_units": "km",
                "internal_satellite_position_units": "km",
                "output_localization_metric_units": "m",
                "plotted_localization_conversion": "position_error_m reports Euclidean km error multiplied by 1000",
            },
            "clock_units": {
                "internal_clock_state_units": "range-equivalent km",
                "clock_sigma_input_units": "seconds or ns in figure configs, converted before range-domain simulation",
                "clock_sigma_internal_units": "range-equivalent km",
                "synchronization_error_output_units": "seconds internally, ns for plotted/reported figure metrics",
                "clock_error_conversion": "gauge-relative range-km error divided by c_km_per_s; ns uses *1e9",
            },
            "measurement_units": {
                "measurement_vector_units": "km",
                "measurement_model_units": "km",
                "measurement_covariance_units": "km^2 from sigma_km^2",
                "jacobian_units": "position columns dimensionless direction cosines; clock columns dimensionless range-km derivatives",
            },
            "unit_risk_verdict": "units_consistent",
            "notes": "Package tests cover km-to-meter position output and gauge-relative clock metrics; C7 reports raw km and plotted ns explicitly.",
        },
        {
            "pipeline_family": "package_native_suspect_v24_figures",
            "position_units": {
                "internal_ue_position_units": "km",
                "internal_satellite_position_units": "km",
                "output_localization_metric_units": "m",
                "plotted_localization_conversion": "reported as meters in metadata/summary",
            },
            "clock_units": {
                "internal_clock_state_units": "range-equivalent km",
                "clock_sigma_input_units": "figure-config dependent",
                "clock_sigma_internal_units": "range-equivalent km",
                "synchronization_error_output_units": "seconds/ns depending on figure family",
                "clock_error_conversion": "package metric conversion as above",
            },
            "measurement_units": {
                "measurement_vector_units": "km",
                "measurement_model_units": "km",
                "measurement_covariance_units": "km^2",
                "jacobian_units": "package range-domain Jacobian",
            },
            "unit_risk_verdict": "units_consistent",
            "notes": "Units appear consistent, but system model and algorithm fidelity are suspect; do not cite as evidence.",
        },
        {
            "pipeline_family": "original_manuscript_artifacts",
            "position_units": {
                "internal_ue_position_units": "unknown from artifact alone",
                "internal_satellite_position_units": "unknown from artifact alone",
                "output_localization_metric_units": "m in manuscript-style labels",
                "plotted_localization_conversion": "unknown_needs_review",
            },
            "clock_units": {
                "internal_clock_state_units": "unknown from artifact alone",
                "clock_sigma_input_units": "seconds/ns depending on figure",
                "clock_sigma_internal_units": "unknown_needs_review",
                "synchronization_error_output_units": "ns in labels",
                "clock_error_conversion": "unknown_needs_review",
            },
            "measurement_units": {
                "measurement_vector_units": "unknown_needs_review",
                "measurement_model_units": "unknown_needs_review",
                "measurement_covariance_units": "unknown_needs_review",
                "jacobian_units": "unknown_needs_review",
            },
            "unit_risk_verdict": "units_uncertain",
            "notes": "The PDF artifacts alone do not prove the execution path or units; keep as manuscript artifacts, not code evidence.",
        },
        {
            "pipeline_family": "wave_or_gnss_missing",
            "position_units": {
                "internal_ue_position_units": "unknown",
                "internal_satellite_position_units": "unknown",
                "output_localization_metric_units": "unknown",
                "plotted_localization_conversion": "unknown",
            },
            "clock_units": {
                "internal_clock_state_units": "unknown",
                "clock_sigma_input_units": "unknown",
                "clock_sigma_internal_units": "unknown",
                "synchronization_error_output_units": "unknown",
                "clock_error_conversion": "unknown",
            },
            "measurement_units": {
                "measurement_vector_units": "unknown",
                "measurement_model_units": "unknown",
                "measurement_covariance_units": "unknown",
                "jacobian_units": "unknown",
            },
            "unit_risk_verdict": "units_uncertain",
            "notes": "No matching wave-results or GNSS/baseline exploration output roots were found.",
        },
    ]


def build_pipeline_tuples() -> list[dict[str, Any]]:
    return [
        {
            "pipeline_tuple": "legacy_all_clock + A0_legacy_il + B0_legacy_lm_truth_gate + C0_legacy_truth_cov_ekf",
            "implemented": True,
            "has_benchmark_card": True,
            "reproduces_legacy": True,
            "candidate_final": False,
            "quarantined": True,
            "notes": "Use as legacy reference only; truth gates and all-clock metrics are unsafe for V24 evidence.",
        },
        {
            "pipeline_tuple": "legacy_compatible_all_clock + A0_legacy_il + B1_residual_lm + C_none",
            "implemented": True,
            "has_benchmark_card": True,
            "reproduces_legacy": False,
            "candidate_final": False,
            "quarantined": False,
            "notes": "Current clean Step B/LM-only baseline for human review.",
        },
        {
            "pipeline_tuple": "package_native_current + A1_package_dl_only + B1_residual_lm + C_none",
            "implemented": True,
            "has_benchmark_card": True,
            "reproduces_legacy": False,
            "candidate_final": False,
            "quarantined": False,
            "notes": "Used as baseline in C7 candidate validation.",
        },
        {
            "pipeline_tuple": "package_native_current + A1_package_dl_only + B1_residual_lm + C7_residual_cov_sync_safeguard",
            "implemented": True,
            "has_benchmark_card": True,
            "reproduces_legacy": False,
            "candidate_final": False,
            "quarantined": False,
            "notes": "Ready for human graph review only; not manuscript-ready.",
        },
        {
            "pipeline_tuple": "gauge_fixed + A2_gauge_fixed_dl_only + B2_gauge_fixed_residual_lm + C7_residual_cov_sync_safeguard",
            "implemented": False,
            "has_benchmark_card": False,
            "reproduces_legacy": False,
            "candidate_final": False,
            "quarantined": True,
            "notes": "Recognized future tuple; not implemented as a distinct result family.",
        },
    ]


def build_contradictions() -> list[dict[str, Any]]:
    c7_row = first_row(
        read_csv("outputs/step_c7_residual_cov_sync_safeguard/raw.csv"),
        candidate="step_c7_residual_cov_sync_safeguard",
        num_users="3",
        num_satellites="4",
    )
    recreation_rows = read_csv("outputs/c7_manuscript_figure_recreation/raw.csv")
    recreation_c = first_row(
        recreation_rows,
        family="network_size",
        num_users="3",
        num_satellites="4",
        baseline_id="refined_jcls",
    )
    c7_pos = to_float(c7_row.get("c7_position_error_m") if c7_row else None)
    recreation_pos = to_float(recreation_c.get("position_error_mean_m") if recreation_c else None)
    ratio = (recreation_pos / c7_pos) if c7_pos and recreation_pos else None
    return [
        {
            "contradiction_id": "c7_centimeter_vs_manuscript_recreation_meter_scale",
            "source_a": "outputs/step_c7_residual_cov_sync_safeguard/raw.csv Nu=3,Ns=4",
            "source_b": "outputs/c7_manuscript_figure_recreation/raw.csv network Nu=3,Ns=4 refined_jcls",
            "numerical_mismatch": f"C7 diagnostic Stage C position {fmt(c7_pos)} m versus C7 manuscript recreation Stage C position {fmt(recreation_pos)} m; ratio about {fmt(ratio)}",
            "likely_cause": "The rows are not a controlled same-system benchmark: diagnostic medium uses a small deterministic validation setup, while manuscript recreation uses notebook-inspired figure-family settings, different geometry/noise/clock assumptions, and manuscript-style output semantics.",
            "quarantine_decision": "Do not compare these as evidence of algorithm performance until a normalized benchmark card is run across both paths.",
            "next_diagnostic_action": "Create a single benchmark runner that drives Step B and C7 through the exact same geometry, noise, links, seeds, and clock sigma.",
        },
        {
            "contradiction_id": "legacy_clock_sweep_good_behavior_vs_c7_clock_sweep_instability",
            "source_a": "outputs/legacy_replay/clock_sweep_full/legacy_clock_sweep_metadata.json",
            "source_b": "outputs/c7_candidate_figures/metadata.json and outputs/c7_manuscript_figure_recreation/metadata.json",
            "numerical_mismatch": "Legacy replay reports refined position below 0.06 m at all seven clock points after truth-gated fallback behavior; C7 bounded/sparse clock-sweep reports candidate-failed localization at high clock standard deviation.",
            "likely_cause": "Legacy uses all-clock state, truth-error acceptance/fallback behavior, all-clock synchronization metric, and smoothing/fitting transforms; C7 uses non-truth safeguards and package-native metrics.",
            "quarantine_decision": "Use legacy clock sweep as reference only and C7 clock sweep as debugging evidence only.",
            "next_diagnostic_action": "Run a normalized clock-sweep benchmark with raw Stage A/B/C metrics, no smoothing, and explicit clock-unit conversion audit.",
        },
        {
            "contradiction_id": "jcls_label_mixes_stage_tuples",
            "source_a": "legacy replay labels coarse/refined JCLS",
            "source_b": "package-native and C7 labels coarse/refined JCLS",
            "numerical_mismatch": "Same label can refer to legacy truth-gated all-clock MAP, Step B LM-only, generic dynamic SCI/SFI, or C7 residual-covariance safeguard.",
            "likely_cause": "Historical figure labels are algorithm-stage labels, not full pipeline tuple identifiers.",
            "quarantine_decision": "Every new result must include the explicit system/A/B/C tuple before being discussed as evidence.",
            "next_diagnostic_action": "Add pipeline tuple labels to future summary CSV/metadata and figure notes.",
        },
        {
            "contradiction_id": "manuscript_ready_claim_absent_but_outputs_exist",
            "source_a": "all inspected report JSON files",
            "source_b": "generated PDF outputs",
            "numerical_mismatch": "No inspected current output claims manuscript_ready=true, but many PDFs resemble manuscript figures.",
            "likely_cause": "Diagnostic and candidate plots intentionally mimic figure families for review.",
            "quarantine_decision": "Do not cite any generated PDF unless its lineage row is promoted by human signoff.",
            "next_diagnostic_action": "Keep RESULT_VERSION_LINEAGE_AND_UNITS_REVIEW as the first lookup before discussing figures.",
        },
    ]


def build_current_use_decisions(families: list[ResultFamily]) -> list[dict[str, str]]:
    return [
        {
            "result_family": family.result_family,
            "current_use_status": family.recommended_use,
            "decision": (
                "Use only with explicit caveats."
                if family.recommended_use == "use_for_human_review"
                else "Do not use as manuscript evidence."
            ),
            "reason": family.quarantine_reason or family.rough_performance_tag,
        }
        for family in families
    ]


def build_payload() -> dict[str, Any]:
    families = build_result_families()
    units_review = build_units_review()
    contradictions = build_contradictions()
    unit_counts: dict[str, int] = {}
    quarantine_count = 0
    for family in families:
        unit_counts[family.units_status] = unit_counts.get(family.units_status, 0) + 1
        if family.readiness in {"quarantine_until_reconciled"} or family.recommended_use in {"do_not_use", "use_for_debugging_only"}:
            quarantine_count += 1
    return {
        "artifact_status": "result_version_lineage_and_units_review",
        "branch": git_value("branch", "--show-current"),
        "commit": git_value("rev-parse", "--short", "HEAD"),
        "standard_case_id": STANDARD_CASE_ID,
        "result_family_count": len(families),
        "unit_status_counts": unit_counts,
        "quarantine_count": quarantine_count,
        "result_families": [asdict(family) for family in families],
        "units_review": units_review,
        "pipeline_tuples": build_pipeline_tuples(),
        "contradictions": contradictions,
        "current_use_decisions": build_current_use_decisions(families),
        "currently_recommended_result_family": "step_b_lm_only_results and c7_residual_cov_sync_safeguard for human review only; no family is manuscript-ready",
        "next_diagnostic_action": "Create one normalized benchmark-card runner that compares Step B and C7 under identical geometry/noise/clock settings before any manuscript evidence claim.",
    }


def md_table(headers: list[str], rows: list[dict[str, Any]]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        values = [fmt(row.get(header, "")) for header in headers]
        values = [value.replace("|", "/") for value in values]
        lines.append("| " + " | ".join(values) + " |")
    return lines


def write_reports(payload: dict[str, Any]) -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    REGISTRY.mkdir(parents=True, exist_ok=True)
    json_path = REPORTS / "RESULT_VERSION_LINEAGE_AND_UNITS_REVIEW.json"
    md_path = REPORTS / "RESULT_VERSION_LINEAGE_AND_UNITS_REVIEW.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    headers = [
        "result_family",
        "output_root",
        "branch",
        "commit",
        "generating_script",
        "system_model_version",
        "stage_a_version",
        "stage_b_version",
        "stage_c_version",
        "pipeline_class",
        "truth_usage",
        "units_status",
        "standard_case_id",
        "standard_case_stage_a_pos_m",
        "standard_case_stage_b_pos_m",
        "standard_case_stage_c_pos_m",
        "standard_case_stage_a_sync_ns",
        "standard_case_stage_b_sync_ns",
        "standard_case_stage_c_sync_ns",
        "rough_performance_tag",
        "readiness",
        "recommended_use",
        "quarantine_reason",
    ]
    lines = [
        "# Result Version Lineage and Units Review",
        "",
        "## Executive Summary",
        "This is the first-stop bookkeeping artifact for generated results. It records the system-model/stage tuple, truth usage, unit status, and current-use decision for each major result family. No listed family is manuscript-ready.",
        "",
        f"- Result families covered: `{payload['result_family_count']}`",
        f"- Standard benchmark label: `{payload['standard_case_id']}`",
        f"- Units-consistent families: `{payload['unit_status_counts'].get('units_consistent', 0)}`",
        f"- Units-uncertain families: `{payload['unit_status_counts'].get('units_uncertain', 0)}`",
        f"- Quarantined/debug-only/not-use families: `{payload['quarantine_count']}`",
        "",
        "## Result Lineage Table",
        *md_table(headers, payload["result_families"]),
        "",
        "## Units Review",
    ]
    for item in payload["units_review"]:
        lines += [
            "",
            f"### {item['pipeline_family']}",
            f"- Unit-risk verdict: `{item['unit_risk_verdict']}`",
            f"- Position units: UE `{item['position_units']['internal_ue_position_units']}`, satellite `{item['position_units']['internal_satellite_position_units']}`, output `{item['position_units']['output_localization_metric_units']}`, conversion `{item['position_units']['plotted_localization_conversion']}`.",
            f"- Clock units: state `{item['clock_units']['internal_clock_state_units']}`, sigma input `{item['clock_units']['clock_sigma_input_units']}`, sigma internal `{item['clock_units']['clock_sigma_internal_units']}`, output `{item['clock_units']['synchronization_error_output_units']}`, conversion `{item['clock_units']['clock_error_conversion']}`.",
            f"- Measurement units: vector `{item['measurement_units']['measurement_vector_units']}`, model `{item['measurement_units']['measurement_model_units']}`, covariance `{item['measurement_units']['measurement_covariance_units']}`, Jacobian `{item['measurement_units']['jacobian_units']}`.",
            f"- Notes: {item['notes']}",
        ]

    lines += [
        "",
        "## Version Combination Tuples",
        *md_table(
            ["pipeline_tuple", "implemented", "has_benchmark_card", "reproduces_legacy", "candidate_final", "quarantined", "notes"],
            payload["pipeline_tuples"],
        ),
        "",
        "## Contradictions and Quarantine Decisions",
    ]
    for item in payload["contradictions"]:
        lines += [
            "",
            f"### {item['contradiction_id']}",
            f"- Source A: `{item['source_a']}`",
            f"- Source B: `{item['source_b']}`",
            f"- Numerical mismatch: {item['numerical_mismatch']}",
            f"- Likely cause: {item['likely_cause']}",
            f"- Quarantine decision: {item['quarantine_decision']}",
            f"- Next diagnostic action: {item['next_diagnostic_action']}",
        ]

    lines += [
        "",
        "## Standard Benchmark Section",
        f"The requested benchmark label is `{payload['standard_case_id']}`. Several historical families do not expose that exact case; those rows are explicitly marked `unknown`, `not_applicable`, or with a family-specific benchmark label.",
        "",
        "## Current-Use Decision",
        *md_table(["result_family", "current_use_status", "decision", "reason"], payload["current_use_decisions"]),
        "",
        "## Blunt Recommendation",
        f"- Currently recommended result family: {payload['currently_recommended_result_family']}",
        f"- Next diagnostic action: {payload['next_diagnostic_action']}",
        "",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")

    registry_lines = [
        "# Result Registry",
        "",
        "The mandatory lineage and units review is the authoritative bookkeeping artifact for result provenance:",
        "",
        "- [RESULT_VERSION_LINEAGE_AND_UNITS_REVIEW.md](../reports/RESULT_VERSION_LINEAGE_AND_UNITS_REVIEW.md)",
        "- [RESULT_VERSION_LINEAGE_AND_UNITS_REVIEW.json](../reports/RESULT_VERSION_LINEAGE_AND_UNITS_REVIEW.json)",
        "",
        "Every new result family must include a pipeline tuple, unit verdict, readiness status, and recommended-use status before it is discussed as evidence.",
        "",
        "## Registered Families",
        *md_table(["result_family", "output_root", "system_model_version", "stage_a_version", "stage_b_version", "stage_c_version", "units_status", "readiness", "recommended_use"], payload["result_families"]),
        "",
    ]
    (REGISTRY / "RESULT_REGISTRY.md").write_text("\n".join(registry_lines), encoding="utf-8")


def main() -> None:
    write_reports(build_payload())


if __name__ == "__main__":
    main()
