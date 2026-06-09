"""Generate non-final GPS/GNSS-style baseline diagnostics for JCLS.

This runner creates bounded diagnostic artifacts only. It does not execute the
notebook, touch manuscript directories, overwrite manuscript figures, or mark
any output as manuscript-ready.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


SAT_SIM_ROOT = Path(__file__).resolve().parents[1]
if str(SAT_SIM_ROOT) not in sys.path:
    sys.path.insert(0, str(SAT_SIM_ROOT))

from jcls_sim.constants import C_KM_PER_S, C_M_PER_S  # noqa: E402
from scripts import explore_step3_covariance as cov  # noqa: E402
from scripts import explore_step3_near_winner_sparse as nw  # noqa: E402
from scripts import run_step_c7_residual_cov_sync_safeguard as c7  # noqa: E402


OUTPUT_ROOT = SAT_SIM_ROOT / "outputs" / "gnss_baseline_exploration"
PLOT_ROOT = OUTPUT_ROOT / "plots"
REPORT_ROOT = SAT_SIM_ROOT / "outputs" / "reports"

REPRESENTATIVE_CASES = [(3, 4), (5, 8), (7, 8)]
GNSS_POSITION_PRIOR_SIGMA_M = [0.1, 1.0, 10.0, 100.0, None]
CLOCK_PRIOR_SIGMA_NS = [0.0, 1.0, 10.0, 100.0, 1000.0, None]
INTERMITTENT_UPDATE_SECONDS = [1.0, 5.0, 15.0, 30.0]
OSCILLATOR_DRIFT_PPM = [
    {
        "oscillator_label": "tcxo_0_5_ppm",
        "drift_ppm": 0.5,
        "basis": "Scenario assumption; matches the manuscript example 0.5 ppm over 15 s.",
    },
    {
        "oscillator_label": "tcxo_0_1_ppm",
        "drift_ppm": 0.1,
        "basis": "Scenario assumption for a better TCXO-class holdover case.",
    },
    {
        "oscillator_label": "ocxo_0_01_ppm",
        "drift_ppm": 0.01,
        "basis": "Scenario assumption for an OCXO-style 10 ppb holdover case.",
    },
    {
        "oscillator_label": "disciplined_ocxo_0_001_ppm",
        "drift_ppm": 0.001,
        "basis": "Scenario assumption for a disciplined oscillator-class 1 ppb case.",
    },
]

ARTIFACT_FLAGS = {
    "artifact_status": "non_final_gnss_baseline_exploration",
    "candidate_only": True,
    "non_final": True,
    "manuscript_ready": False,
    "not_for_manuscript_submission": True,
    "human_signoff_required": True,
    "notebook_used": False,
    "manuscript_directories_touched": False,
    "response_letter_touched": False,
    "bibliography_touched": False,
    "work_in_progress_figures_touched": False,
    "psfrag_touched": False,
    "generated_manuscript_pdfs_touched": False,
    "existing_manuscript_result_files_touched": False,
}


def _repo_rel(path: Path) -> str:
    """Return a sat-sim-relative path."""

    return path.relative_to(SAT_SIM_ROOT).as_posix()


def _json_dump(path: Path, payload: Any) -> str:
    """Write stable JSON and return a repo-relative path."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return _repo_rel(path)


def _csv_dump(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> str:
    """Write CSV rows and return a repo-relative path."""

    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = sorted({field for row in rows for field in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return _repo_rel(path)


def _md_table(rows: list[dict[str, Any]], fields: list[str]) -> str:
    """Render a simple Markdown table."""

    lines = [
        "| " + " | ".join(fields) + " |",
        "| " + " | ".join("---" for _ in fields) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(field, "")) for field in fields) + " |")
    return "\n".join(lines)


def _write_text(path: Path, text: str) -> str:
    """Write text and return a repo-relative path."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return _repo_rel(path)


def baseline_taxonomy_rows() -> list[dict[str, Any]]:
    """Return the GNSS baseline taxonomy requested by the task."""

    return [
        {
            "label": "standalone_gnss_reference",
            "gnss_required": True,
            "continuous_gnss_required": True,
            "external_corrections_required": False,
            "cooperation_required": False,
            "satellite_clock_correction_assumed": "GNSS broadcast orbit/clock correction and synchronized GNSS time.",
            "ue_clock_correction_assumed": "Receiver clock bias solved as part of the GNSS fix.",
            "fair_comparison_to_jcls": False,
            "comparison_class": "external_service_reference",
            "oracle_diagnostic_reference": "reference",
            "assumption_summary": "Open-sky or otherwise usable GNSS access; no NTN cooperation needed.",
            "safe_claim": "Useful as a familiar external PNT reference when GNSS is available.",
            "unsafe_claim": "Do not claim it is an infrastructure-matched GNSS-denied baseline for JCLS.",
        },
        {
            "label": "degraded_gnss_reference",
            "gnss_required": True,
            "continuous_gnss_required": True,
            "external_corrections_required": False,
            "cooperation_required": False,
            "satellite_clock_correction_assumed": "Standard GNSS timing and broadcast corrections remain assumed.",
            "ue_clock_correction_assumed": "Receiver clock solved from degraded pseudorange geometry.",
            "fair_comparison_to_jcls": False,
            "comparison_class": "scenario_stress_reference",
            "oracle_diagnostic_reference": "diagnostic_reference",
            "assumption_summary": "Nominal, degraded 10 m, poor 100 m, and unavailable scenario levels.",
            "safe_claim": "Shows sensitivity to GNSS blockage or weak geometry as scenario assumptions.",
            "unsafe_claim": "Do not present the 10 m or 100 m levels as literature values without a citation.",
        },
        {
            "label": "gnss_aided_initialization",
            "gnss_required": True,
            "continuous_gnss_required": False,
            "external_corrections_required": False,
            "cooperation_required": True,
            "satellite_clock_correction_assumed": "Only the initial GNSS fix inherits GNSS satellite timing assumptions.",
            "ue_clock_correction_assumed": "Initial UE position prior is aided; clock aiding is not continuous.",
            "fair_comparison_to_jcls": False,
            "comparison_class": "initialization_diagnostic",
            "oracle_diagnostic_reference": "diagnostic",
            "assumption_summary": "One-shot GNSS position prior with NTN/JCLS refinement after GNSS loss.",
            "safe_claim": "Tests whether good external initialization removes the need for cooperative refinement.",
            "unsafe_claim": "Do not call this standalone JCLS because it injects external GNSS information.",
        },
        {
            "label": "gnss_clock_aided_ntn",
            "gnss_required": True,
            "continuous_gnss_required": "variant-dependent",
            "external_corrections_required": False,
            "cooperation_required": "variant-dependent",
            "satellite_clock_correction_assumed": "Known or tightly constrained satellite/network clocks.",
            "ue_clock_correction_assumed": "Known, tightly constrained, or periodically updated UE clocks.",
            "fair_comparison_to_jcls": False,
            "comparison_class": "clock_aided_diagnostic",
            "oracle_diagnostic_reference": "oracle_for_perfect_clock_variant",
            "assumption_summary": "Perfect clock, 1 ns, 10 ns, 100 ns, 1 us, and unconstrained cases.",
            "safe_claim": "Shows how much external clock synchronization changes NTN localization.",
            "unsafe_claim": "Do not use the perfect-clock row as a fair synchronization baseline.",
        },
        {
            "label": "intermittent_gnss_update",
            "gnss_required": True,
            "continuous_gnss_required": False,
            "external_corrections_required": False,
            "cooperation_required": "optional_hybrid",
            "satellite_clock_correction_assumed": "Clock is corrected only at GNSS update epochs.",
            "ue_clock_correction_assumed": "Clock uncertainty grows between updates according to oscillator drift.",
            "fair_comparison_to_jcls": False,
            "comparison_class": "hybrid_outage_diagnostic",
            "oracle_diagnostic_reference": "diagnostic",
            "assumption_summary": "GNSS update intervals 1, 5, 15, and 30 s with ppm/ppb drift scenarios.",
            "safe_claim": "Quantifies holdover range bias between GNSS reacquisitions.",
            "unsafe_claim": "Do not call the outage interval GNSS-free without accounting for prior GNSS information.",
        },
        {
            "label": "gnss_correction_service_reference",
            "gnss_required": True,
            "continuous_gnss_required": True,
            "external_corrections_required": True,
            "cooperation_required": False,
            "satellite_clock_correction_assumed": "Precise orbit/clock corrections from an augmentation service.",
            "ue_clock_correction_assumed": "Receiver clock solved with augmented GNSS measurements.",
            "fair_comparison_to_jcls": False,
            "comparison_class": "high_infrastructure_reference",
            "oracle_diagnostic_reference": "reference",
            "assumption_summary": "RTK, PPP, DGNSS, SBAS, or commercial correction-service infrastructure.",
            "safe_claim": "Provides high-performance GNSS context when corrections are available.",
            "unsafe_claim": "Do not compare it as a fair GNSS-denied or infrastructure-matched JCLS baseline.",
        },
        {
            "label": "leo_pnt_literature_reference",
            "gnss_required": "literature-dependent",
            "continuous_gnss_required": "literature-dependent",
            "external_corrections_required": "literature-dependent",
            "cooperation_required": False,
            "satellite_clock_correction_assumed": "Often assumes known or estimated LEO orbit/clock information.",
            "ue_clock_correction_assumed": "Estimated or externally aided depending on the paper.",
            "fair_comparison_to_jcls": False,
            "comparison_class": "literature_context_reference",
            "oracle_diagnostic_reference": "reference_only",
            "assumption_summary": "Signals, batching time, reference receiver, and orbit knowledge vary by paper.",
            "safe_claim": "Useful as context for LEO-PNT and Starlink signal-of-opportunity work.",
            "unsafe_claim": "Do not claim direct superiority or inferiority without reproducing the paper assumptions.",
        },
    ]


def literature_rows() -> list[dict[str, Any]]:
    """Return conservative literature/source rows used by the reports."""

    return [
        {
            "label": "standalone_gnss_reference",
            "category": "GPS/GNSS standalone positioning performance",
            "source_title": "GPS.gov: GPS Accuracy",
            "url": "https://archive.gps.gov/systems/gps/performance/accuracy/",
            "reported_or_relevant_value": "Smartphone open-sky example 4.9 m radius; high-quality single-frequency FAA data <=1.82 m horizontal, 95%; GPS URE <=2.0 m, 95%.",
            "infrastructure_assumptions": "Open-sky GNSS, broadcast GNSS signals, GNSS control segment, receiver solution for position and time.",
            "comparison_caveat": "User accuracy depends on geometry, blockage, atmosphere, multipath, and receiver quality; URE is not user position accuracy.",
            "used_as_final_value": False,
        },
        {
            "label": "standalone_gnss_reference",
            "category": "GPS SPS performance commitment",
            "source_title": "GPS.gov: GPS Performance",
            "url": "https://prod-01-alb-www-gps.woc.noaa.gov/gps-performance",
            "reported_or_relevant_value": "2024 SPS metrics include <=8 m horizontal 95% global average, <=13 m vertical 95% global average, and <=30 ns time transfer 95%.",
            "infrastructure_assumptions": "Civil GPS SPS, healthy constellation, global service definitions, GPS control segment.",
            "comparison_caveat": "Service commitment/global metric, not a particular UE, urban, or NTN receiver result.",
            "used_as_final_value": False,
        },
        {
            "label": "standalone_gnss_reference",
            "category": "GPS timing reference",
            "source_title": "GPS.gov: GPS Accuracy - timing",
            "url": "https://archive.gps.gov/systems/gps/performance/accuracy/",
            "reported_or_relevant_value": "GPS time-transfer accuracy relative to UTC(USNO) <=30 ns, 95%, for specialized fixed time-transfer receivers.",
            "infrastructure_assumptions": "Specialized time-transfer receiver, fixed site, GNSS time infrastructure.",
            "comparison_caveat": "Not a generic mobile UE clock guarantee.",
            "used_as_final_value": False,
        },
        {
            "label": "gnss_aided_initialization",
            "category": "A-GNSS / 3GPP NG-RAN positioning",
            "source_title": "3GPP TS 38.305 UE positioning in NG-RAN",
            "url": "https://www.3gpp.org/ftp/specs/archive/38_series/38.305/",
            "reported_or_relevant_value": "NG-RAN positioning supports A-GNSS along with NR positioning methods such as DL-TDOA, DL-AoD, Multi-RTT, UL-TDOA, and UL-AoA.",
            "infrastructure_assumptions": "NG-RAN and LMF positioning architecture.",
            "comparison_caveat": "Standards support and architecture, not an accuracy guarantee.",
            "used_as_final_value": False,
        },
        {
            "label": "gnss_aided_initialization",
            "category": "Assisted GNSS / 3GPP LPP",
            "source_title": "3GPP TS 37.355 LTE Positioning Protocol (LPP)",
            "url": "https://portal.3gpp.org/desktopmodules/Specifications/SpecificationDetails.aspx?specificationId=3710",
            "reported_or_relevant_value": "LPP covers E-UTRA and NR positioning and includes A-GNSS assistance/provide-location procedures.",
            "infrastructure_assumptions": "Location server such as E-SMLC, LMF, or SLP; cellular control/user-plane assistance.",
            "comparison_caveat": "Protocol support is not a standalone accuracy claim.",
            "used_as_final_value": False,
        },
        {
            "label": "gnss_aided_initialization",
            "category": "OMA SUPL / assisted GNSS",
            "source_title": "OMA SUPL v2.0 enabler test specification",
            "url": "https://www.openmobilealliance.org/release/supl/ETS/OMA-ETS-SUPL-V2_0-20100914-C.pdf",
            "reported_or_relevant_value": "SUPL test cases include A-GPS/A-GNSS SET-assisted and SET-based modes.",
            "infrastructure_assumptions": "SUPL-enabled terminal, SUPL location platform/server, IP/user-plane connectivity.",
            "comparison_caveat": "Defines assistance architecture/test cases, not a universal accuracy number.",
            "used_as_final_value": False,
        },
        {
            "label": "gnss_correction_service_reference",
            "category": "SBAS / WAAS",
            "source_title": "FAA WAAS Performance Analysis Report",
            "url": "https://www.nstb.tc.faa.gov/reports/waaspanreports.htm",
            "reported_or_relevant_value": "FAA monitored WAAS reports provide site-level horizontal/vertical 95% performance statistics under aviation integrity modes.",
            "infrastructure_assumptions": "WAAS reference stations, master stations, GEO broadcast, and aviation receiver modes.",
            "comparison_caveat": "Aviation augmentation infrastructure; not unaided GNSS or GNSS-denied JCLS.",
            "used_as_final_value": False,
        },
        {
            "label": "gnss_correction_service_reference",
            "category": "Single-base RTK",
            "source_title": "NOAA NGS User Guidelines for Single Base Real Time GNSS Positioning",
            "url": "https://www.ngs.noaa.gov/PUBS_LIB/NGSRealTimeUserGuidelines.v2.0.4.pdf",
            "reported_or_relevant_value": "Survey-grade real-time precision often cited around 1 cm + 1 ppm horizontal and 2 cm + 1 ppm vertical at 1 sigma, when procedures and ambiguity fixing are successful.",
            "infrastructure_assumptions": "Known base station, rover, correction data link, calibration, and field quality control.",
            "comparison_caveat": "Precision and absolute accuracy differ; requires correction infrastructure and favorable GNSS conditions.",
            "used_as_final_value": False,
        },
        {
            "label": "gnss_correction_service_reference",
            "category": "Network RTK / RTN",
            "source_title": "NOAA NGS Guidelines for Real Time GNSS Networks",
            "url": "https://www.ngs.noaa.gov/PUBS_LIB/NGSGuidelinesForRealTimeGNSSNetworksV2.2.pdf",
            "reported_or_relevant_value": "RTN guidelines discuss centimeter-class horizontal/vertical precision under controlled network and field procedures.",
            "infrastructure_assumptions": "CORS/RTN network, datum alignment, cellular/internet data link, and user QC.",
            "comparison_caveat": "Network correction infrastructure is not comparable to GNSS-denied cooperative JCLS.",
            "used_as_final_value": False,
        },
        {
            "label": "gnss_correction_service_reference",
            "category": "CORS / postprocessed differential GNSS",
            "source_title": "NOAA CORS Network",
            "url": "https://geodesy.noaa.gov/CORS/",
            "reported_or_relevant_value": "CORS supports postprocessed high-accuracy positioning workflows through fiducial reference stations.",
            "infrastructure_assumptions": "Reference-station network, code/carrier data, postprocessing, and NSRS alignment.",
            "comparison_caveat": "Postprocessed survey infrastructure, not real-time standalone GNSS or JCLS.",
            "used_as_final_value": False,
        },
        {
            "label": "gnss_correction_service_reference",
            "category": "RTK/PPP/differential GNSS",
            "source_title": "NovAtel: RTK vs PPP correction services",
            "url": "https://novatel.com/tech-talk/an-introduction-to-gnss/resources/rtk-vs-ppp",
            "reported_or_relevant_value": "RTK, DGNSS, SBAS, and PPP are correction methods; RTK uses correction links, PPP can provide centimetre-level accuracy with global corrections.",
            "infrastructure_assumptions": "Reference stations, correction streams, satellite/internet delivery, or commercial correction service.",
            "comparison_caveat": "High-infrastructure reference, not a fair GNSS-denied baseline.",
            "used_as_final_value": False,
        },
        {
            "label": "gnss_correction_service_reference",
            "category": "PPP/correction products",
            "source_title": "International GNSS Service products / PPP-AR",
            "url": "https://www.igs.org/products/",
            "reported_or_relevant_value": "IGS provides precise orbit and clock products; PPP-AR uses precise products and bias information.",
            "infrastructure_assumptions": "Global GNSS monitoring and analysis-center infrastructure.",
            "comparison_caveat": "Correction products are external infrastructure and may have latency or service constraints.",
            "used_as_final_value": False,
        },
        {
            "label": "gnss_correction_service_reference",
            "category": "Real-time PPP corrections",
            "source_title": "Performance of real-time IGS satellite clocks for PPP",
            "url": "https://doi.org/10.1007/s10291-014-0369-5",
            "reported_or_relevant_value": "IGS real-time correction literature reports centimeter-class orbit and sub-nanosecond clock correction targets/behavior for PPP inputs.",
            "infrastructure_assumptions": "Real-time global tracking, analysis centers, correction streams, and PPP receiver processing.",
            "comparison_caveat": "Correction-stream performance is not direct user position accuracy and assumes external infrastructure.",
            "used_as_final_value": False,
        },
        {
            "label": "leo_pnt_literature_reference",
            "category": "LEO-PNT / signal of opportunity survey",
            "source_title": "Receiver architectures for positioning with low earth orbit satellite signals: a survey",
            "url": "https://link.springer.com/article/10.1186/s13634-023-01022-1",
            "reported_or_relevant_value": "Survey reports examples including 7.7 m 2D Starlink with altitude aiding, 25.9 m 2D and 33.5 m 3D without external altitude over 800 s using six satellites.",
            "infrastructure_assumptions": "Signal-specific receiver, TLE/orbit information, batching/EKF, sometimes altitude or other aiding.",
            "comparison_caveat": "Literature context only; assumptions differ from JCLS cooperative NTN.",
            "used_as_final_value": False,
        },
        {
            "label": "leo_pnt_literature_reference",
            "category": "Opportunistic Starlink PNT",
            "source_title": "The First Carrier Phase Tracking and Positioning Results With Starlink LEO Satellite Signals",
            "url": "https://doi.org/10.1109/TAES.2021.3113880",
            "reported_or_relevant_value": "Reported experimental examples include 7.7 m 2D error with known altitude and tens-of-meters 2D/3D errors without external altitude over an extended batch.",
            "infrastructure_assumptions": "Passive/non-cooperative Starlink signal exploitation, carrier-phase tracking, static receiver, and aiding for best case.",
            "comparison_caveat": "Proof-of-concept experiment, not an operational PNT service or infrastructure-matched JCLS baseline.",
            "used_as_final_value": False,
        },
        {
            "label": "leo_pnt_literature_reference",
            "category": "LEO observability",
            "source_title": "Observability Analysis of Opportunistic Receiver Localization with LEO Satellite Pseudorange Measurements",
            "url": "https://doi.org/10.33012/2022.18540",
            "reported_or_relevant_value": "Analyzes observability from LEO pseudorange measurements over time and includes experimental demonstrations.",
            "infrastructure_assumptions": "Known LEO satellite state over time and pseudorange extraction from LEO signals.",
            "comparison_caveat": "Observability context, not a general accuracy benchmark.",
            "used_as_final_value": False,
        },
        {
            "label": "leo_pnt_literature_reference",
            "category": "NR-NTN positioning with GNSS comparison",
            "source_title": "LEO-based Positioning: Foundations, Signal Design, and Receiver Enhancements for 6G NTN",
            "url": "https://arxiv.org/abs/2410.18301",
            "reported_or_relevant_value": "Discusses LEO-based NR-NTN positioning as complementary infrastructure to GNSS and potentially an alternative with enhancements.",
            "infrastructure_assumptions": "NR-NTN physical-layer enhancements, PRS resource design, LEO orbit/signal simulation framework.",
            "comparison_caveat": "Design-study context, not a reproduced baseline for this manuscript.",
            "used_as_final_value": False,
        },
        {
            "label": "leo_pnt_literature_reference",
            "category": "NTN positioning and GNSS augmentation",
            "source_title": "NTN-based 6G Localization: Vision, Role of LEOs, and Open Problems",
            "url": "https://arxiv.org/abs/2305.12259",
            "reported_or_relevant_value": "Identifies multi-LEO positioning and GNSS-augmented LEO positioning when insufficient GNSS satellites are visible.",
            "infrastructure_assumptions": "3GPP-related NTN positioning assumptions and CRLB simulation study.",
            "comparison_caveat": "Useful for framing weak/unavailable GNSS, not for direct numerical comparison.",
            "used_as_final_value": False,
        },
        {
            "label": "leo_pnt_literature_reference",
            "category": "LEO-enhanced GNSS PPP",
            "source_title": "LEO enhanced GNSS precise point positioning with emphasis on model comparison",
            "url": "https://doi.org/10.1016/j.asr.2024.06.006",
            "reported_or_relevant_value": "Reports LEO-augmented GNSS PPP geometry/accuracy improvements under the paper's simulation and data assumptions.",
            "infrastructure_assumptions": "GNSS PPP infrastructure plus simulated/augmented LEO observations.",
            "comparison_caveat": "LEO-augmented GNSS, not standalone cooperative NTN JCLS.",
            "used_as_final_value": False,
        },
        {
            "label": "intermittent_gnss_update",
            "category": "TCXO drift scenario support",
            "source_title": "Rakon TCXO product family",
            "url": "https://www.rakon.com/products/tcxo",
            "reported_or_relevant_value": "TCXO frequency stability options span roughly +/-0.05 to +/-1.5 ppm.",
            "infrastructure_assumptions": "Local oscillator holdover after GNSS loss.",
            "comparison_caveat": "The sweep values are scenario assumptions, not final literature-calibrated device models.",
            "used_as_final_value": False,
        },
        {
            "label": "intermittent_gnss_update",
            "category": "GNSS holdover",
            "source_title": "PMU holdover performance enhancement using double-oven controlled oscillator",
            "url": "https://www.ornl.gov/publication/pmu-holdover-performance-enhancement-using-double-oven-controlled-oscillator",
            "reported_or_relevant_value": "Reports maintaining timing within 1 us drift for more than 1.5 hours in a GPS holdover context.",
            "infrastructure_assumptions": "High-quality oscillator holdover and GPS timing application.",
            "comparison_caveat": "Application-specific timing holdover, not UE-grade clock-drift model.",
            "used_as_final_value": False,
        },
    ]


def context_comparison_rows() -> list[dict[str, Any]]:
    """Return a compact context comparison table."""

    return [
        {
            "row": "standalone GNSS",
            "infrastructure_required": "GNSS constellation/control segment and receiver.",
            "gnss_access_required": "continuous during fix",
            "time_to_solution": "receiver-dependent",
            "reported_or_modeled_accuracy": "meter-level context from GPS.gov under usable GNSS; not modeled here as a final value",
            "cooperation": "none",
            "clock_assumptions": "GNSS time and receiver clock solved by GNSS",
            "fair_comparison_caveat": "external PNT service reference",
        },
        {
            "row": "assisted GNSS",
            "infrastructure_required": "GNSS plus cellular/location server assistance.",
            "gnss_access_required": "yes",
            "time_to_solution": "assistance-dependent",
            "reported_or_modeled_accuracy": "not assigned; protocol/infrastructure reference",
            "cooperation": "none",
            "clock_assumptions": "GNSS time plus assistance data",
            "fair_comparison_caveat": "aided baseline with external data path",
        },
        {
            "row": "RTK/PPP/differential GNSS",
            "infrastructure_required": "GNSS plus correction service, base station, CORS, or precise products.",
            "gnss_access_required": "yes",
            "time_to_solution": "convergence/setup dependent",
            "reported_or_modeled_accuracy": "centimeter-class context under good correction-service conditions",
            "cooperation": "none",
            "clock_assumptions": "precise GNSS orbit/clock correction products",
            "fair_comparison_caveat": "high-infrastructure reference",
        },
        {
            "row": "opportunistic LEO-PNT / Starlink",
            "infrastructure_required": "LEO signals, orbit/clock knowledge or estimation, signal-specific receiver.",
            "gnss_access_required": "not necessarily",
            "time_to_solution": "batch/EKF and signal-dependent",
            "reported_or_modeled_accuracy": "literature examples from meters to tens of meters depending on aiding",
            "cooperation": "usually none",
            "clock_assumptions": "paper-dependent satellite and receiver clock/orbit treatment",
            "fair_comparison_caveat": "literature context only unless assumptions are reproduced",
        },
        {
            "row": "GNSS-aided NTN",
            "infrastructure_required": "brief or periodic GNSS plus NTN measurements.",
            "gnss_access_required": "initial or intermittent",
            "time_to_solution": "modeled as bounded one-step diagnostic",
            "reported_or_modeled_accuracy": "scenario sweep in this branch, non-final",
            "cooperation": "JCLS variants require UE cooperation",
            "clock_assumptions": "GNSS prior may aid position or clocks",
            "fair_comparison_caveat": "diagnostic with external prior information",
        },
        {
            "row": "JCLS",
            "infrastructure_required": "cooperative terrestrial/non-terrestrial measurements in the manuscript model.",
            "gnss_access_required": "no, unless using an aided variant",
            "time_to_solution": "estimator/runtime dependent",
            "reported_or_modeled_accuracy": "existing Stage B/C7 diagnostics reused; not final manuscript-ready",
            "cooperation": "yes",
            "clock_assumptions": "joint position/clock estimation relative to reference satellite",
            "fair_comparison_caveat": "main manuscript concept, but this branch is diagnostic only",
        },
    ]


def _unit_pattern(length: int, *, phase: float = 0.0) -> np.ndarray:
    """Return a deterministic zero-mean unit-RMS pattern."""

    idx = np.arange(length, dtype=float)
    pattern = np.sin(0.73 * (idx + 1.0) + phase) + 0.41 * np.cos(0.31 * (idx + 2.0) - phase)
    pattern -= float(np.mean(pattern))
    rms = math.sqrt(float(np.mean(np.square(pattern))))
    if rms == 0.0:
        pattern = np.ones(length, dtype=float)
        pattern -= float(np.mean(pattern))
        rms = 1.0
    return pattern / rms


def _position_prior_mean(case: nw.SparseCase, sigma_m: float) -> np.ndarray:
    """Return a deterministic GNSS-like position prior mean."""

    pattern = _unit_pattern(2 * case.num_users, phase=0.17).reshape(case.num_users, 2)
    norm_rms = math.sqrt(float(np.mean(np.sum(np.square(pattern), axis=1))))
    return case.true_positions_km + pattern / max(norm_rms, 1.0e-12) * (sigma_m / 1000.0)


def _clock_prior_mean(case: nw.SparseCase, sigma_ns: float | None, *, perfect: bool = False) -> np.ndarray:
    """Return a deterministic clock prior mean in range-domain km."""

    if perfect:
        return case.true_clocks_km.copy()
    if sigma_ns is None:
        return case.step_b_clocks_km.copy()
    pattern = _unit_pattern(case.true_clocks_km.size, phase=0.43)
    sigma_km = float(sigma_ns) * 1.0e-9 * C_KM_PER_S
    return case.true_clocks_km + pattern * sigma_km


def _stage_a_case(base: nw.SparseCase, *, position_prior_sigma_m: float | None = None) -> nw.SparseCase:
    """Return a deterministic Stage-A/DL-style initialization case."""

    if position_prior_sigma_m is None:
        position_estimate = _position_prior_mean(base, 100.0)
        position_source = "coarse_dl_only_scenario"
    else:
        position_estimate = _position_prior_mean(base, position_prior_sigma_m)
        position_source = "gnss_position_prior_scenario"
    clock_pattern = _unit_pattern(base.true_clocks_km.size, phase=0.61)
    drift_pattern = _unit_pattern(base.true_drifts_km_per_s.size, phase=0.89)
    clock_error_km = 1000.0e-9 * C_KM_PER_S
    drift_error_km_per_s = 0.5e-6 * C_KM_PER_S
    output = replace(
        base,
        name=f"{base.name}_{position_source}",
        step_b_positions_km=position_estimate,
        step_b_clocks_km=base.true_clocks_km + clock_pattern * clock_error_km,
        step_b_drifts_km_per_s=base.true_drifts_km_per_s + drift_pattern * drift_error_km_per_s,
    )
    return output


def _links(case: nw.SparseCase, mode: str) -> list[tuple[int, int]]:
    """Return DL-only or cooperative receiver/transmitter links."""

    links: list[tuple[int, int]] = []
    for ue in range(case.num_users):
        for sat in range(case.num_satellites):
            links.append((ue, case.num_users + sat))
    if mode == "cooperative":
        for ue in range(case.num_users):
            neighbor = (ue + 1) % case.num_users
            if ue != neighbor:
                links.append((ue, neighbor))
                links.append((neighbor, ue))
    if mode not in {"dl_only", "cooperative"}:
        raise ValueError(f"unknown measurement mode {mode}")
    return links


def _measurements_and_jacobian(
    case: nw.SparseCase,
    variant: cov.CovarianceVariant,
    theta: np.ndarray,
    *,
    measurement_mode: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return true/predicted measurements and Jacobian for selected links."""

    est_positions, est_clocks, est_drifts = cov._unpack_state(theta, case, variant)
    sat_positions = nw._make_satellites(case.num_satellites)
    rows_true: list[float] = []
    rows_pred: list[float] = []
    rows_jac: list[np.ndarray] = []
    clock_offset = cov._clock_slice(case).start
    drift_offset = cov._drift_slice(case, variant).start
    for epoch in range(nw.EPOCHS):
        t_seconds = epoch * nw.DT_SECONDS
        true_clocks = case.true_clocks_km + t_seconds * case.true_drifts_km_per_s
        pred_clocks = est_clocks + t_seconds * est_drifts
        for receiver, transmitter in _links(case, measurement_mode):
            true_rx = nw._node_position(receiver, case.true_positions_km, sat_positions, case.num_users)
            true_tx = nw._node_position(transmitter, case.true_positions_km, sat_positions, case.num_users)
            pred_rx = nw._node_position(receiver, est_positions, sat_positions, case.num_users)
            pred_tx = nw._node_position(transmitter, est_positions, sat_positions, case.num_users)
            true_range = float(np.linalg.norm(true_rx - true_tx))
            pred_range = float(np.linalg.norm(pred_rx - pred_tx))
            true_value = true_range + nw._clock_value(true_clocks, transmitter, case.num_users) - nw._clock_value(true_clocks, receiver, case.num_users)
            pred_value = pred_range + nw._clock_value(pred_clocks, transmitter, case.num_users) - nw._clock_value(pred_clocks, receiver, case.num_users)
            row = np.zeros(theta.size, dtype=float)
            diff = pred_rx - pred_tx
            distance = max(float(np.linalg.norm(diff)), 1.0e-12)
            unit = diff / distance
            if receiver < case.num_users:
                row[2 * receiver : 2 * receiver + 2] += unit
            if transmitter < case.num_users:
                row[2 * transmitter : 2 * transmitter + 2] -= unit
            rx_clock = nw._clock_index_for_node(receiver, case.num_users)
            tx_clock = nw._clock_index_for_node(transmitter, case.num_users)
            if tx_clock is not None:
                row[clock_offset + tx_clock] += 1.0
                if variant.include_drift_state:
                    row[drift_offset + tx_clock] += t_seconds
            if rx_clock is not None:
                row[clock_offset + rx_clock] -= 1.0
                if variant.include_drift_state:
                    row[drift_offset + rx_clock] -= t_seconds
            rows_true.append(true_value)
            rows_pred.append(pred_value)
            rows_jac.append(row)
    return np.asarray(rows_true), np.asarray(rows_pred), np.vstack(rows_jac)


def _position_rmse_m(case: nw.SparseCase, positions_km: np.ndarray) -> float:
    """Return UE position RMSE in meters."""

    return math.sqrt(float(np.mean(np.sum(np.square(positions_km - case.true_positions_km), axis=1)))) * 1000.0


def _sync_rmse_ns(case: nw.SparseCase, clocks_km: np.ndarray, drifts_km_per_s: np.ndarray) -> float:
    """Return epoch-expanded synchronization RMSE in ns."""

    errors_km = []
    for epoch in range(nw.EPOCHS):
        t_seconds = epoch * nw.DT_SECONDS
        true = case.true_clocks_km + t_seconds * case.true_drifts_km_per_s
        est = clocks_km + t_seconds * drifts_km_per_s
        errors_km.extend((est - true).tolist())
    rmse_km = math.sqrt(float(np.mean(np.square(errors_km))))
    return rmse_km / C_KM_PER_S * 1.0e9


def _condition_number(matrix: np.ndarray) -> float:
    """Return a condition number diagnostic."""

    try:
        return float(np.linalg.cond(matrix))
    except np.linalg.LinAlgError:
        return float("inf")


def _prior_diagnostics(
    theta0: np.ndarray,
    rhs: np.ndarray,
    normal: np.ndarray,
    case: nw.SparseCase,
    variant: cov.CovarianceVariant,
    *,
    position_prior_sigma_m: float | None = None,
    clock_prior_sigma_ns: float | None = None,
    perfect_clock_oracle: bool = False,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Add GNSS position/clock prior information to normal equations."""

    normal_out = normal.copy()
    rhs_out = rhs.copy()
    prior_sources: list[str] = []
    if position_prior_sigma_m is not None:
        sigma_km = max(float(position_prior_sigma_m) / 1000.0, 1.0e-9)
        prior_mean = _position_prior_mean(case, float(position_prior_sigma_m)).reshape(-1)
        slc = cov._position_slice(case)
        weight = 1.0 / (sigma_km * sigma_km)
        normal_out[slc, slc] += np.eye(slc.stop - slc.start) * weight
        rhs_out[slc] += weight * (prior_mean - theta0[slc])
        prior_sources.append("gnss_position_prior")
    if perfect_clock_oracle or clock_prior_sigma_ns is not None:
        sigma_ns = 1.0e-6 if perfect_clock_oracle else float(clock_prior_sigma_ns)
        sigma_km = max(sigma_ns * 1.0e-9 * C_KM_PER_S, 1.0e-12)
        prior_mean = _clock_prior_mean(case, clock_prior_sigma_ns, perfect=perfect_clock_oracle)
        slc = cov._clock_slice(case)
        weight = 1.0 / (sigma_km * sigma_km)
        normal_out[slc, slc] += np.eye(slc.stop - slc.start) * weight
        rhs_out[slc] += weight * (prior_mean - theta0[slc])
        prior_sources.append("perfect_clock_oracle" if perfect_clock_oracle else "gnss_clock_prior")
        if perfect_clock_oracle and variant.include_drift_state:
            drift_slc = cov._drift_slice(case, variant)
            normal_out[drift_slc, drift_slc] += np.eye(drift_slc.stop - drift_slc.start) * weight
            rhs_out[drift_slc] += weight * (case.true_drifts_km_per_s - theta0[drift_slc])
            prior_sources.append("perfect_drift_oracle")
    diagnostics = {
        "prior_sources": ";".join(prior_sources) if prior_sources else "none",
        "position_prior_sigma_m": "" if position_prior_sigma_m is None else float(position_prior_sigma_m),
        "clock_prior_sigma_ns": "perfect_oracle" if perfect_clock_oracle else ("" if clock_prior_sigma_ns is None else float(clock_prior_sigma_ns)),
        "perfect_clock_oracle": perfect_clock_oracle,
        "truth_used_to_simulate_prior_measurement": bool(prior_sources),
    }
    return normal_out, rhs_out, diagnostics


def _map_update_row(
    case: nw.SparseCase,
    variant: cov.CovarianceVariant,
    *,
    stage: str,
    measurement_mode: str,
    baseline_label: str,
    position_prior_sigma_m: float | None = None,
    clock_prior_sigma_ns: float | None = None,
    perfect_clock_oracle: bool = False,
) -> tuple[dict[str, Any], np.ndarray]:
    """Run one bounded one-step MAP diagnostic row."""

    started = time.monotonic()
    theta0 = cov._pack_state(case, variant)
    z_true, z_pred, jacobian = _measurements_and_jacobian(case, variant, theta0, measurement_mode=measurement_mode)
    residual = z_true - z_pred
    sigma = np.full(z_true.size, variant.measurement_sigma_km)
    r_inv_diag = 1.0 / np.square(sigma)
    normal = jacobian.T @ (jacobian * r_inv_diag[:, None])
    rhs = jacobian.T @ (r_inv_diag * residual)
    normal, rhs, prior_diag = _prior_diagnostics(
        theta0,
        rhs,
        normal,
        case,
        variant,
        position_prior_sigma_m=position_prior_sigma_m,
        clock_prior_sigma_ns=clock_prior_sigma_ns,
        perfect_clock_oracle=perfect_clock_oracle,
    )
    damped = normal + np.eye(normal.shape[0]) * max(variant.damping_lambda, 1.0e-10)
    update = np.linalg.pinv(damped, rcond=1.0e-10) @ rhs
    theta1 = theta0 + update
    pos0, clock0, drift0 = cov._unpack_state(theta0, case, variant)
    pos1, clock1, drift1 = cov._unpack_state(theta1, case, variant)
    residual_after = z_true - _measurements_and_jacobian(case, variant, theta1, measurement_mode=measurement_mode)[1]
    residual_cost_before = float(np.sum(np.square(residual / sigma)))
    residual_cost_after = float(np.sum(np.square(residual_after / sigma)))
    finite_output = bool(np.all(np.isfinite(theta1)) and np.isfinite(residual_cost_after))
    objective_decreased = bool(residual_cost_after <= residual_cost_before + 1.0e-9)
    row = {
        **ARTIFACT_FLAGS,
        "family": baseline_label,
        "baseline_label": baseline_label,
        "stage": stage,
        "measurement_mode": measurement_mode,
        "num_users": case.num_users,
        "num_satellites": case.num_satellites,
        "case_name": case.name,
        "runtime_seconds": time.monotonic() - started,
        "localization_rmse_m": _position_rmse_m(case, pos1),
        "synchronization_rmse_ns": _sync_rmse_ns(case, clock1, drift1),
        "initial_localization_rmse_m": _position_rmse_m(case, pos0),
        "initial_synchronization_rmse_ns": _sync_rmse_ns(case, clock0, drift0),
        "convergence_probability": 1.0 if finite_output and objective_decreased else 0.0,
        "finite_output": finite_output,
        "objective_decreased": objective_decreased,
        "residual_cost_before": residual_cost_before,
        "residual_cost_after": residual_cost_after,
        "normal_rank": int(np.linalg.matrix_rank(normal)),
        "normal_condition": _condition_number(normal),
        "normal_dimension": int(normal.shape[0]),
        "jacobian_rank": int(np.linalg.matrix_rank(jacobian)),
        "jacobian_rows": int(jacobian.shape[0]),
        "jacobian_columns": int(jacobian.shape[1]),
        "update_norm": float(np.linalg.norm(update)),
        "truth_state_used_for_acceptance": False,
        "truth_state_used_for_covariance": False,
        "truth_used_only_for_offline_metrics": True,
        **prior_diag,
    }
    return row, theta1


def _c7_row_from_theta(
    source_case: nw.SparseCase,
    variant: cov.CovarianceVariant,
    theta_step_b: np.ndarray,
    *,
    baseline_label: str,
    position_prior_sigma_m: float | None = None,
    clock_prior_sigma_ns: float | None = None,
    perfect_clock_oracle: bool = False,
) -> dict[str, Any]:
    """Run C7 from an externally supplied Step-B state."""

    pos_b, clock_b, drift_b = cov._unpack_state(theta_step_b, source_case, variant)
    c7_case = replace(
        source_case,
        name=f"{source_case.name}_c7_from_prior",
        step_b_positions_km=pos_b,
        step_b_clocks_km=clock_b,
        step_b_drifts_km_per_s=drift_b,
    )
    started = time.monotonic()
    c7_candidate = c7.CANDIDATES[0]
    c7_variant = c7._candidate_variant(c7_candidate)
    theta0 = cov._pack_state(c7_case, c7_variant)
    z_true, z_pred, jacobian = cov._measurements_and_jacobian(c7_case, c7_variant, theta0)
    residual = z_true - z_pred
    sigma = np.full(z_true.size, c7_variant.measurement_sigma_km)
    block_slices = c7._c7_block_slices(c7_case, c7_variant)
    config = c7.StepC7Config(
        damping_lambda=c7_variant.damping_lambda,
        position_floor_km2=c7_variant.position_floor_km2,
        position_ceiling_km2=c7_variant.position_ceiling_km2,
        clock_floor_km2=c7_variant.clock_floor_km2,
        clock_ceiling_km2=c7_variant.clock_ceiling_km2,
        drift_floor_km2_per_s2=c7_variant.drift_floor_km2_per_s2,
        drift_ceiling_km2_per_s2=c7_variant.drift_ceiling_km2_per_s2,
        sync_safeguard=c7_candidate.sync_safeguard,
        residual_scale_enabled=c7_candidate.residual_scale_enabled,
    )

    def residual_at_state(theta: np.ndarray) -> np.ndarray:
        return z_true - cov._measurements_and_jacobian(c7_case, c7_variant, theta)[1]

    result = c7.step_c7_residual_cov_sync_safeguard_refinement(
        theta0,
        jacobian,
        residual,
        sigma,
        block_slices,
        num_users=c7_case.num_users,
        residual_at_state=residual_at_state,
        config=config,
    )
    theta_eval = result.theta.copy()
    if perfect_clock_oracle:
        theta_eval[cov._clock_slice(c7_case)] = c7_case.true_clocks_km
        if c7_variant.include_drift_state:
            theta_eval[cov._drift_slice(c7_case, c7_variant)] = c7_case.true_drifts_km_per_s
    pos0, clock0, drift0 = cov._unpack_state(theta0, c7_case, c7_variant)
    pos1, clock1, drift1 = cov._unpack_state(theta_eval, c7_case, c7_variant)
    diagnostics = result.diagnostics
    safeguard = diagnostics["safeguard"]
    row = {
        **ARTIFACT_FLAGS,
        "family": baseline_label,
        "baseline_label": baseline_label,
        "stage": "c7_jcls",
        "measurement_mode": "cooperative",
        "num_users": c7_case.num_users,
        "num_satellites": c7_case.num_satellites,
        "case_name": c7_case.name,
        "runtime_seconds": time.monotonic() - started,
        "localization_rmse_m": _position_rmse_m(c7_case, pos1),
        "synchronization_rmse_ns": _sync_rmse_ns(c7_case, clock1, drift1),
        "initial_localization_rmse_m": _position_rmse_m(c7_case, pos0),
        "initial_synchronization_rmse_ns": _sync_rmse_ns(c7_case, clock0, drift0),
        "convergence_probability": 1.0 if bool(diagnostics["objective_decreased"]) and not bool(diagnostics["fallback_event"]) else 0.0,
        "finite_output": bool(np.all(np.isfinite(result.theta))),
        "objective_decreased": bool(diagnostics["objective_decreased"]),
        "residual_cost_before": float(diagnostics["objective_before"]),
        "residual_cost_after": float(diagnostics["objective_after"]),
        "normal_rank": "",
        "normal_condition": "",
        "normal_dimension": "",
        "jacobian_rank": "",
        "jacobian_rows": "",
        "jacobian_columns": "",
        "update_norm": float(
            diagnostics["position_update_norm"]
            + diagnostics["ue_clock_update_norm"]
            + diagnostics["satellite_clock_update_norm"]
            + diagnostics["clock_drift_update_norm"]
        ),
        "position_prior_sigma_m": "" if position_prior_sigma_m is None else float(position_prior_sigma_m),
        "clock_prior_sigma_ns": "perfect_oracle" if perfect_clock_oracle else ("" if clock_prior_sigma_ns is None else float(clock_prior_sigma_ns)),
        "perfect_clock_oracle": perfect_clock_oracle,
        "prior_sources": "carried_from_step_b",
        "truth_used_to_simulate_prior_measurement": position_prior_sigma_m is not None or clock_prior_sigma_ns is not None or perfect_clock_oracle,
        "truth_state_used_for_acceptance": False,
        "truth_state_used_for_covariance": False,
        "truth_used_only_for_offline_metrics": True,
        "fallback_triggered": bool(diagnostics["fallback_event"]),
        "fallback_reason": diagnostics["fallback_reason"],
        "fallback_behavior": diagnostics["fallback_behavior"],
        "affected_state_blocks": ";".join(diagnostics["affected_state_blocks"]),
        "safeguard_reasons": ";".join(safeguard["safeguard_reasons"]),
        "estimator_mode": c7.STEP_C7_ESTIMATOR_MODE,
    }
    return row


def _candidate_variant() -> cov.CovarianceVariant:
    """Return the main C7-compatible covariance variant."""

    return c7._candidate_variant(c7.CANDIDATES[0])


def run_position_prior_sweep() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Run GNSS-aided initialization prior sensitivity diagnostics."""

    rows: list[dict[str, Any]] = []
    variant = _candidate_variant()
    for num_users, num_satellites in REPRESENTATIVE_CASES:
        base = cov._make_case(num_users, num_satellites)
        for prior_sigma_m in GNSS_POSITION_PRIOR_SIGMA_M:
            case = _stage_a_case(base, position_prior_sigma_m=prior_sigma_m)
            prior_label = "no_gnss_prior" if prior_sigma_m is None else f"{prior_sigma_m:g}_m"
            baseline_label = "gnss_aided_initialization"
            dl_row, _ = _map_update_row(
                case,
                variant,
                stage="stage_a_dl_only",
                measurement_mode="dl_only",
                baseline_label=baseline_label,
                position_prior_sigma_m=prior_sigma_m,
            )
            dl_row["position_prior_level"] = prior_label
            rows.append(dl_row)
            step_b_row, theta_step_b = _map_update_row(
                case,
                variant,
                stage="step_b_jcls",
                measurement_mode="cooperative",
                baseline_label=baseline_label,
                position_prior_sigma_m=prior_sigma_m,
            )
            step_b_row["position_prior_level"] = prior_label
            rows.append(step_b_row)
            c7_row = _c7_row_from_theta(
                case,
                variant,
                theta_step_b,
                baseline_label=baseline_label,
                position_prior_sigma_m=prior_sigma_m,
            )
            c7_row["position_prior_level"] = prior_label
            rows.append(c7_row)
    return rows, _summarize_sweep(rows, group_fields=("baseline_label", "stage", "position_prior_level"))


def run_clock_prior_sweep() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Run GNSS clock-aided NTN clock-prior diagnostics."""

    rows: list[dict[str, Any]] = []
    variant = _candidate_variant()
    for num_users, num_satellites in REPRESENTATIVE_CASES:
        stage_a_base = _stage_a_case(cov._make_case(num_users, num_satellites), position_prior_sigma_m=None)
        for clock_sigma_ns in CLOCK_PRIOR_SIGMA_NS:
            perfect = clock_sigma_ns == 0.0
            base = (
                replace(
                    stage_a_base,
                    step_b_clocks_km=stage_a_base.true_clocks_km.copy(),
                    step_b_drifts_km_per_s=stage_a_base.true_drifts_km_per_s.copy(),
                )
                if perfect
                else stage_a_base
            )
            prior_level = "perfect_clock_oracle" if perfect else ("unconstrained" if clock_sigma_ns is None else f"{clock_sigma_ns:g}_ns")
            baseline_label = "gnss_clock_aided_ntn"
            dl_row, _ = _map_update_row(
                base,
                variant,
                stage="dl_only",
                measurement_mode="dl_only",
                baseline_label=baseline_label,
                clock_prior_sigma_ns=clock_sigma_ns if not perfect else None,
                perfect_clock_oracle=perfect,
            )
            dl_row["clock_prior_level"] = prior_level
            dl_row["oracle_baseline"] = perfect
            rows.append(dl_row)
            step_b_row, theta_step_b = _map_update_row(
                base,
                variant,
                stage="step_b_jcls",
                measurement_mode="cooperative",
                baseline_label=baseline_label,
                clock_prior_sigma_ns=clock_sigma_ns if not perfect else None,
                perfect_clock_oracle=perfect,
            )
            step_b_row["clock_prior_level"] = prior_level
            step_b_row["oracle_baseline"] = perfect
            rows.append(step_b_row)
            c7_row = _c7_row_from_theta(
                base,
                variant,
                theta_step_b,
                baseline_label=baseline_label,
                clock_prior_sigma_ns=clock_sigma_ns if not perfect else None,
                perfect_clock_oracle=perfect,
            )
            c7_row["clock_prior_level"] = prior_level
            c7_row["oracle_baseline"] = perfect
            rows.append(c7_row)
    return rows, _summarize_sweep(rows, group_fields=("baseline_label", "stage", "clock_prior_level"))


def _summarize_sweep(rows: list[dict[str, Any]], *, group_fields: tuple[str, ...]) -> list[dict[str, Any]]:
    """Summarize deterministic rows across representative cases."""

    keys = sorted({tuple(str(row.get(field, "")) for field in group_fields) for row in rows})
    summaries: list[dict[str, Any]] = []
    for key in keys:
        subset = [row for row in rows if tuple(str(row.get(field, "")) for field in group_fields) == key]
        item = {field: value for field, value in zip(group_fields, key)}
        item.update(
            {
                "row_count": len(subset),
                "mean_localization_rmse_m": float(np.mean([float(row["localization_rmse_m"]) for row in subset])),
                "mean_synchronization_rmse_ns": float(np.mean([float(row["synchronization_rmse_ns"]) for row in subset])),
                "max_localization_rmse_m": float(np.max([float(row["localization_rmse_m"]) for row in subset])),
                "max_synchronization_rmse_ns": float(np.max([float(row["synchronization_rmse_ns"]) for row in subset])),
                "convergence_probability": float(np.mean([float(row["convergence_probability"]) for row in subset])),
                "mean_runtime_seconds": float(np.mean([float(row["runtime_seconds"]) for row in subset])),
                "finite_rows": sum(1 for row in subset if bool(row["finite_output"])),
                "non_final": True,
                "manuscript_ready": False,
            }
        )
        numeric_condition = [
            float(row["normal_condition"])
            for row in subset
            if row.get("normal_condition") not in ("", None) and math.isfinite(float(row["normal_condition"]))
        ]
        item["mean_normal_condition"] = "" if not numeric_condition else float(np.mean(numeric_condition))
        summaries.append(item)
    return summaries


def intermittent_gnss_rows() -> list[dict[str, Any]]:
    """Return clock-drift accumulation rows between intermittent GNSS fixes."""

    rows: list[dict[str, Any]] = []
    for oscillator in OSCILLATOR_DRIFT_PPM:
        drift_ppm = float(oscillator["drift_ppm"])
        for update_interval_s in INTERMITTENT_UPDATE_SECONDS:
            time_error_s = drift_ppm * 1.0e-6 * update_interval_s
            time_error_us = time_error_s * 1.0e6
            range_bias_m = C_M_PER_S * time_error_s
            expected_localization_degradation_m = math.sqrt(10.0**2 + range_bias_m**2)
            viability = (
                "low_holdover_bias_context"
                if range_bias_m <= 10.0
                else "moderate_bias_requires_clock_estimation"
                if range_bias_m <= 100.0
                else "large_bias_jcls_clock_estimation_or_external_update_needed"
            )
            rows.append(
                {
                    **ARTIFACT_FLAGS,
                    "baseline_label": "intermittent_gnss_update",
                    "oscillator_label": oscillator["oscillator_label"],
                    "drift_ppm": drift_ppm,
                    "update_interval_s": update_interval_s,
                    "time_error_s": time_error_s,
                    "time_error_us": time_error_us,
                    "range_bias_equivalent_m": range_bias_m,
                    "range_bias_equivalent_km": range_bias_m / 1000.0,
                    "expected_localization_degradation_m": expected_localization_degradation_m,
                    "viability_label": viability,
                    "basis": oscillator["basis"],
                    "scenario_assumption": True,
                    "matches_manuscript_example": oscillator["oscillator_label"] == "tcxo_0_5_ppm" and update_interval_s == 15.0,
                }
            )
    return rows


def degraded_gnss_rows() -> list[dict[str, Any]]:
    """Return scenario rows for degraded standalone GNSS reference levels."""

    levels = [
        ("nominal_gnss", 4.9, "GPS.gov smartphone open-sky context, not a final manuscript value"),
        ("degraded_gnss_10_m", 10.0, "scenario assumption"),
        ("poor_gnss_100_m", 100.0, "scenario assumption"),
        ("gnss_unavailable", None, "scenario assumption"),
    ]
    rows = []
    for label, accuracy_m, basis in levels:
        rows.append(
            {
                **ARTIFACT_FLAGS,
                "baseline_label": "degraded_gnss_reference",
                "degradation_level": label,
                "modeled_position_error_m": "" if accuracy_m is None else accuracy_m,
                "gnss_required": label != "gnss_unavailable",
                "clock_synchronization_available_from_gnss": label != "gnss_unavailable",
                "scenario_assumption": "scenario assumption" in basis,
                "basis": basis,
                "fair_comparison_to_jcls": False,
            }
        )
    return rows


def _plot_prior_sensitivity(summary: list[dict[str, Any]], *, metric: str, ylabel: str, filename: str, level_field: str) -> str:
    """Plot a prior-sensitivity summary."""

    stages = ["stage_a_dl_only", "dl_only", "step_b_jcls", "c7_jcls"]
    x_labels = []
    for row in summary:
        level = str(row[level_field])
        if level not in x_labels:
            x_labels.append(level)
    def sort_key(label: str) -> float:
        if label in {"no_gnss_prior", "unconstrained"}:
            return float("inf")
        if label == "perfect_clock_oracle":
            return -1.0
        return float(label.replace("_m", "").replace("_ns", ""))
    x_labels = sorted(x_labels, key=sort_key)
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    x = np.arange(len(x_labels))
    for stage in stages:
        selected = [row for row in summary if row["stage"] == stage]
        if not selected:
            continue
        values = []
        for label in x_labels:
            match = [row for row in selected if str(row[level_field]) == label]
            values.append(float(match[0][metric]) if match else np.nan)
        ax.plot(x, values, marker="o", label=stage)
    ax.set_xticks(x)
    ax.set_xticklabels(x_labels, rotation=30, ha="right")
    ax.set_ylabel(ylabel)
    ax.set_title("Non-final GNSS baseline diagnostic")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    PLOT_ROOT.mkdir(parents=True, exist_ok=True)
    output = PLOT_ROOT / filename
    fig.savefig(output)
    fig.savefig(output.with_suffix(".png"))
    plt.close(fig)
    return _repo_rel(output)


def _plot_intermittent(rows: list[dict[str, Any]]) -> str:
    """Plot intermittent GNSS update interval versus range bias."""

    fig, ax = plt.subplots(figsize=(7.0, 4.1))
    for oscillator in sorted({row["oscillator_label"] for row in rows}):
        selected = sorted([row for row in rows if row["oscillator_label"] == oscillator], key=lambda item: float(item["update_interval_s"]))
        ax.plot(
            [float(row["update_interval_s"]) for row in selected],
            [float(row["range_bias_equivalent_m"]) for row in selected],
            marker="o",
            label=oscillator,
        )
    ax.set_xlabel("GNSS update interval (s)")
    ax.set_ylabel("Equivalent range bias (m)")
    ax.set_title("Non-final intermittent GNSS holdover diagnostic")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    PLOT_ROOT.mkdir(parents=True, exist_ok=True)
    output = PLOT_ROOT / "intermittent_gnss_clock_drift_bias.pdf"
    fig.savefig(output)
    fig.savefig(output.with_suffix(".png"))
    plt.close(fig)
    return _repo_rel(output)


def _plot_taxonomy_matrix(rows: list[dict[str, Any]]) -> str:
    """Plot a boolean taxonomy matrix."""

    fields = [
        "gnss_required",
        "continuous_gnss_required",
        "external_corrections_required",
        "cooperation_required",
        "fair_comparison_to_jcls",
    ]
    labels = [row["label"] for row in rows]
    matrix = np.zeros((len(labels), len(fields)), dtype=float)
    for i, row in enumerate(rows):
        for j, field in enumerate(fields):
            matrix[i, j] = 1.0 if row[field] is True else 0.5 if isinstance(row[field], str) and row[field] != "False" else 0.0
    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    image = ax.imshow(matrix, vmin=0.0, vmax=1.0, cmap="viridis")
    ax.set_xticks(np.arange(len(fields)))
    ax.set_xticklabels(fields, rotation=30, ha="right")
    ax.set_yticks(np.arange(len(labels)))
    ax.set_yticklabels(labels)
    ax.set_title("Non-final baseline taxonomy matrix")
    cbar = fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("0=false, 0.5=variant-dependent, 1=true")
    fig.tight_layout()
    PLOT_ROOT.mkdir(parents=True, exist_ok=True)
    output = PLOT_ROOT / "baseline_taxonomy_matrix.pdf"
    fig.savefig(output)
    fig.savefig(output.with_suffix(".png"))
    plt.close(fig)
    return _repo_rel(output)


def write_taxonomy(taxonomy: list[dict[str, Any]]) -> dict[str, str]:
    """Write taxonomy CSV/JSON/Markdown artifacts."""

    fields = [
        "label",
        "gnss_required",
        "continuous_gnss_required",
        "external_corrections_required",
        "cooperation_required",
        "satellite_clock_correction_assumed",
        "ue_clock_correction_assumed",
        "fair_comparison_to_jcls",
        "comparison_class",
        "oracle_diagnostic_reference",
        "safe_claim",
        "unsafe_claim",
    ]
    md = "# GNSS Baseline Taxonomy\n\n"
    md += "All entries are non-final diagnostic/reference classifications, not manuscript-ready claims.\n\n"
    md += _md_table(taxonomy, fields) + "\n"
    return {
        "taxonomy_csv": _csv_dump(OUTPUT_ROOT / "gnss_baseline_taxonomy.csv", taxonomy, fields),
        "taxonomy_json": _json_dump(OUTPUT_ROOT / "gnss_baseline_taxonomy.json", {"baselines": taxonomy, **ARTIFACT_FLAGS}),
        "taxonomy_md": _write_text(OUTPUT_ROOT / "gnss_baseline_taxonomy.md", md),
    }


def write_literature_table(rows: list[dict[str, Any]]) -> dict[str, str]:
    """Write requested literature tables."""

    fields = [
        "label",
        "category",
        "source_title",
        "url",
        "reported_or_relevant_value",
        "infrastructure_assumptions",
        "comparison_caveat",
        "used_as_final_value",
    ]
    md = "# GNSS Baseline Literature Table\n\n"
    md += "These rows collect context sources only. Scenario assumptions are marked as such and should not be cited as final literature values.\n\n"
    md += _md_table(rows, fields) + "\n"
    return {
        "literature_json": _json_dump(REPORT_ROOT / "GNSS_BASELINE_LITERATURE_TABLE.json", {"sources": rows, **ARTIFACT_FLAGS}),
        "literature_md": _write_text(REPORT_ROOT / "GNSS_BASELINE_LITERATURE_TABLE.md", md),
    }


def write_task_matrix(subagent_status: dict[str, Any]) -> dict[str, str]:
    """Write the requested task/subagent matrix."""

    rows = [
        {
            "agent": "Agent A",
            "role": "GNSS Literature Agent",
            "branch_or_worktree": "read-only sidecar",
            "files_allowed_to_edit": "none",
            "status": subagent_status.get("agent_a", "orchestrator fallback integrated literature table"),
            "scope_boundary": "No manuscript or notebook edits.",
        },
        {
            "agent": "Agent B",
            "role": "Baseline Taxonomy Agent",
            "branch_or_worktree": "read-only sidecar",
            "files_allowed_to_edit": "none",
            "status": subagent_status.get("agent_b", "completed"),
            "scope_boundary": "Conservative fair/oracle/reference labels only.",
        },
        {
            "agent": "Agent C",
            "role": "GNSS Prior Simulation Agent",
            "branch_or_worktree": "read-only sidecar",
            "files_allowed_to_edit": "none",
            "status": subagent_status.get("agent_c", "orchestrator fallback implemented bounded model"),
            "scope_boundary": "No notebook or broad sweeps.",
        },
        {
            "agent": "Agent D",
            "role": "Clock Prior Simulation Agent",
            "branch_or_worktree": "read-only sidecar",
            "files_allowed_to_edit": "none",
            "status": subagent_status.get("agent_d", "orchestrator fallback implemented bounded model"),
            "scope_boundary": "No final figure generation.",
        },
        {
            "agent": "Agent E",
            "role": "Red-Team Agent",
            "branch_or_worktree": "read-only sidecar",
            "files_allowed_to_edit": "none",
            "status": subagent_status.get("agent_e", "pending or orchestrator fallback"),
            "scope_boundary": "Check overclaims/comparability only.",
        },
    ]
    fields = ["agent", "role", "branch_or_worktree", "files_allowed_to_edit", "status", "scope_boundary"]
    md = "# GNSS Baseline Task Matrix\n\n"
    md += _md_table(rows, fields) + "\n"
    return {
        "task_matrix_json": _json_dump(REPORT_ROOT / "GNSS_BASELINE_TASK_MATRIX.json", {"tasks": rows, **ARTIFACT_FLAGS}),
        "task_matrix_md": _write_text(REPORT_ROOT / "GNSS_BASELINE_TASK_MATRIX.md", md),
    }


def write_context_comparison(rows: list[dict[str, Any]]) -> dict[str, str]:
    """Write context comparison table under the output root."""

    fields = [
        "row",
        "infrastructure_required",
        "gnss_access_required",
        "time_to_solution",
        "reported_or_modeled_accuracy",
        "cooperation",
        "clock_assumptions",
        "fair_comparison_caveat",
    ]
    md = "# GNSS/JCLS Context Comparison Table\n\n"
    md += _md_table(rows, fields) + "\n"
    return {
        "context_comparison_json": _json_dump(OUTPUT_ROOT / "context_comparison_table.json", {"rows": rows, **ARTIFACT_FLAGS}),
        "context_comparison_md": _write_text(OUTPUT_ROOT / "context_comparison_table.md", md),
    }


def write_report(
    *,
    taxonomy: list[dict[str, Any]],
    literature: list[dict[str, Any]],
    context_rows: list[dict[str, Any]],
    position_rows: list[dict[str, Any]],
    position_summary: list[dict[str, Any]],
    clock_rows: list[dict[str, Any]],
    clock_summary: list[dict[str, Any]],
    intermittent_rows: list[dict[str, Any]],
    degraded_rows: list[dict[str, Any]],
    artifacts: dict[str, Any],
) -> dict[str, str]:
    """Write the requested Markdown/JSON report."""

    recommended = [
        "Use degraded_gnss_reference as a scenario/reference panel only, with nominal/degraded/poor/unavailable levels marked as assumptions.",
        "Use gnss_aided_initialization as a prior-sensitivity diagnostic if reviewer framing needs to answer whether a brief GNSS fix removes the need for JCLS.",
        "Use gnss_clock_aided_ntn only as a clock-aiding/oracle diagnostic; keep perfect clock visibly labeled as oracle.",
        "Use intermittent_gnss_update to explain why update interval and oscillator drift can dominate range bias during GNSS outages.",
    ]
    safe_claims = [
        "JCLS targets operating assumptions where continuous external GNSS PNT may be unavailable, intermittent, or used only as aiding.",
        "Standalone GNSS and correction-service GNSS assume external timing/positioning infrastructure that is not infrastructure-matched to JCLS.",
        "Perfect-clock and correction-service references are useful diagnostics or context, not fair GNSS-denied baselines.",
        "The 0.5 ppm over 15 s example corresponds to 7.5 microseconds and about 2.25 km range-equivalent bias.",
    ]
    unsafe_claims = [
        "JCLS beats GPS/GNSS generally.",
        "The 10 m and 100 m degraded GNSS levels are literature values.",
        "RTK/PPP is a fair baseline for GNSS-denied JCLS without matching correction infrastructure.",
        "A GNSS-aided initialization row represents standalone JCLS performance.",
        "Perfect clock oracle rows represent achievable GNSS clock aid for all UEs and NTN satellites.",
    ]
    report_payload = {
        **ARTIFACT_FLAGS,
        "executive_summary": "This branch implements non-final GPS/GNSS-style baseline taxonomy, literature context, position-prior sweeps, clock-prior sweeps, and intermittent GNSS holdover diagnostics.",
        "taxonomy": taxonomy,
        "literature": literature,
        "context_comparison": context_rows,
        "position_prior_summary": position_summary,
        "clock_prior_summary": clock_summary,
        "intermittent_gnss_rows": intermittent_rows,
        "degraded_gnss_rows": degraded_rows,
        "recommended_baselines_for_final_figures": recommended,
        "safe_claims": safe_claims,
        "unsafe_claims": unsafe_claims,
        "next_recommended_action": "Human review should choose at most one GNSS-aided diagnostic panel plus one taxonomy/context table before any manuscript edits.",
        "artifacts": artifacts,
    }
    lines = [
        "# GNSS Baseline Exploration Report",
        "",
        "## 1. Executive summary",
        "",
        report_payload["executive_summary"],
        "",
        "All artifacts are non-final diagnostics and are not manuscript-ready.",
        "",
        "## 2. Baseline taxonomy",
        "",
        _md_table(taxonomy, ["label", "comparison_class", "fair_comparison_to_jcls", "oracle_diagnostic_reference", "assumption_summary"]),
        "",
        "## 3. Literature summary",
        "",
        _md_table(literature, ["label", "category", "source_title", "reported_or_relevant_value", "comparison_caveat"]),
        "",
        "## 4. Implemented/modelled baselines",
        "",
        "- `standalone_gnss_reference`: taxonomy and literature context only.",
        "- `degraded_gnss_reference`: scenario table for nominal/degraded/poor/unavailable GNSS.",
        "- `gnss_aided_initialization`: bounded position-prior sensitivity sweep.",
        "- `gnss_clock_aided_ntn`: bounded clock-prior sensitivity sweep.",
        "- `intermittent_gnss_update`: clock-drift/range-bias table and plot.",
        "- `gnss_correction_service_reference`: taxonomy and literature context only.",
        "- `leo_pnt_literature_reference`: literature/context table only.",
        "",
        "## 5. What is fair to compare",
        "",
        "The only fair comparisons are those where external timing/positioning infrastructure is explicit. Most GNSS rows are references or diagnostics, not infrastructure-matched competitors.",
        "",
        "## 6. Oracle/reference rows",
        "",
        "Perfect-clock GNSS-aided NTN is an oracle. Correction-service GNSS and standalone GNSS are external-service references. LEO-PNT literature rows are context references unless their signal, clock, orbit, and batching assumptions are reproduced.",
        "",
        "## 7. Prior-sensitivity results",
        "",
        _md_table(position_summary, ["stage", "position_prior_level", "mean_localization_rmse_m", "mean_synchronization_rmse_ns", "convergence_probability"]),
        "",
        "## 8. Clock-prior results",
        "",
        _md_table(clock_summary, ["stage", "clock_prior_level", "mean_localization_rmse_m", "mean_synchronization_rmse_ns", "convergence_probability"]),
        "",
        "## 9. Intermittent GNSS results",
        "",
        _md_table(intermittent_rows, ["oscillator_label", "update_interval_s", "time_error_us", "range_bias_equivalent_m", "viability_label"]),
        "",
        "## 10. Recommended baselines for final manuscript figures",
        "",
        "\n".join(f"- {item}" for item in recommended),
        "",
        "## 11. Safe claims",
        "",
        "\n".join(f"- {item}" for item in safe_claims),
        "",
        "## 12. Unsafe claims",
        "",
        "\n".join(f"- {item}" for item in unsafe_claims),
        "",
        "## 13. Next recommended action",
        "",
        report_payload["next_recommended_action"],
        "",
        "## Artifact links",
        "",
        "\n".join(f"- {key}: `{value}`" for key, value in artifacts.items() if isinstance(value, str)),
        "",
    ]
    return {
        "json": _json_dump(REPORT_ROOT / "GNSS_BASELINE_EXPLORATION_REPORT.json", report_payload),
        "md": _write_text(REPORT_ROOT / "GNSS_BASELINE_EXPLORATION_REPORT.md", "\n".join(lines)),
    }


def write_raw_outputs(
    *,
    position_rows: list[dict[str, Any]],
    position_summary: list[dict[str, Any]],
    clock_rows: list[dict[str, Any]],
    clock_summary: list[dict[str, Any]],
    intermittent_rows: list[dict[str, Any]],
    degraded_rows: list[dict[str, Any]],
) -> dict[str, str]:
    """Write raw and summary diagnostic data."""

    artifacts = {
        "position_prior_raw_csv": _csv_dump(OUTPUT_ROOT / "gnss_prior_sensitivity_raw.csv", position_rows),
        "position_prior_summary_csv": _csv_dump(OUTPUT_ROOT / "gnss_prior_sensitivity_summary.csv", position_summary),
        "position_prior_json": _json_dump(
            OUTPUT_ROOT / "gnss_prior_sensitivity.json",
            {"rows": position_rows, "summary": position_summary, **ARTIFACT_FLAGS},
        ),
        "clock_prior_raw_csv": _csv_dump(OUTPUT_ROOT / "clock_prior_sensitivity_raw.csv", clock_rows),
        "clock_prior_summary_csv": _csv_dump(OUTPUT_ROOT / "clock_prior_sensitivity_summary.csv", clock_summary),
        "clock_prior_json": _json_dump(
            OUTPUT_ROOT / "clock_prior_sensitivity.json",
            {"rows": clock_rows, "summary": clock_summary, **ARTIFACT_FLAGS},
        ),
        "intermittent_csv": _csv_dump(OUTPUT_ROOT / "intermittent_gnss_clock_drift.csv", intermittent_rows),
        "intermittent_json": _json_dump(
            OUTPUT_ROOT / "intermittent_gnss_clock_drift.json",
            {"rows": intermittent_rows, **ARTIFACT_FLAGS},
        ),
        "degraded_gnss_csv": _csv_dump(OUTPUT_ROOT / "degraded_gnss_reference.csv", degraded_rows),
        "degraded_gnss_json": _json_dump(
            OUTPUT_ROOT / "degraded_gnss_reference.json",
            {"rows": degraded_rows, **ARTIFACT_FLAGS},
        ),
    }
    return artifacts


def write_metadata(artifacts: dict[str, Any], subagent_status: dict[str, Any]) -> str:
    """Write top-level metadata for tests and auditing."""

    payload = {
        **ARTIFACT_FLAGS,
        "branch": "codex/gps-gnss-baseline-exploration",
        "representative_cases": [f"Nu{nu}_Ns{ns}" for nu, ns in REPRESENTATIVE_CASES],
        "baseline_labels": [row["label"] for row in baseline_taxonomy_rows()],
        "position_prior_sweep_m": ["unavailable" if item is None else item for item in GNSS_POSITION_PRIOR_SIGMA_M],
        "clock_prior_sweep_ns": ["perfect_clock_oracle" if item == 0.0 else "unconstrained" if item is None else item for item in CLOCK_PRIOR_SIGMA_NS],
        "intermittent_update_seconds": INTERMITTENT_UPDATE_SECONDS,
        "bounded_mode": True,
        "full_sweep_run": False,
        "final_manuscript_figures_generated": False,
        "subagent_status": subagent_status,
        "artifacts": artifacts,
    }
    return _json_dump(OUTPUT_ROOT / "metadata.json", payload)


def run_exploration(*, subagent_status: dict[str, Any] | None = None) -> dict[str, Any]:
    """Run the complete bounded GNSS baseline exploration."""

    subagent_status = subagent_status or {}
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    PLOT_ROOT.mkdir(parents=True, exist_ok=True)
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)

    taxonomy = baseline_taxonomy_rows()
    literature = literature_rows()
    context_rows = context_comparison_rows()
    position_rows, position_summary = run_position_prior_sweep()
    clock_rows, clock_summary = run_clock_prior_sweep()
    intermittent_rows = intermittent_gnss_rows()
    degraded_rows = degraded_gnss_rows()

    artifacts: dict[str, Any] = {}
    artifacts.update(write_taxonomy(taxonomy))
    artifacts.update(write_literature_table(literature))
    artifacts.update(write_context_comparison(context_rows))
    artifacts.update(write_task_matrix(subagent_status))
    artifacts.update(
        write_raw_outputs(
            position_rows=position_rows,
            position_summary=position_summary,
            clock_rows=clock_rows,
            clock_summary=clock_summary,
            intermittent_rows=intermittent_rows,
            degraded_rows=degraded_rows,
        )
    )
    artifacts["gnss_prior_sensitivity_localization_pdf"] = _plot_prior_sensitivity(
        position_summary,
        metric="mean_localization_rmse_m",
        ylabel="Localization RMSE (m)",
        filename="gnss_prior_sensitivity_localization.pdf",
        level_field="position_prior_level",
    )
    artifacts["gnss_prior_sensitivity_synchronization_pdf"] = _plot_prior_sensitivity(
        position_summary,
        metric="mean_synchronization_rmse_ns",
        ylabel="Synchronization RMSE (ns)",
        filename="gnss_prior_sensitivity_synchronization.pdf",
        level_field="position_prior_level",
    )
    artifacts["clock_prior_sensitivity_localization_pdf"] = _plot_prior_sensitivity(
        clock_summary,
        metric="mean_localization_rmse_m",
        ylabel="Localization RMSE (m)",
        filename="clock_prior_sensitivity_localization.pdf",
        level_field="clock_prior_level",
    )
    artifacts["clock_prior_sensitivity_synchronization_pdf"] = _plot_prior_sensitivity(
        clock_summary,
        metric="mean_synchronization_rmse_ns",
        ylabel="Synchronization RMSE (ns)",
        filename="clock_prior_sensitivity_synchronization.pdf",
        level_field="clock_prior_level",
    )
    artifacts["intermittent_gnss_clock_drift_bias_pdf"] = _plot_intermittent(intermittent_rows)
    artifacts["baseline_taxonomy_matrix_pdf"] = _plot_taxonomy_matrix(taxonomy)
    report_paths = write_report(
        taxonomy=taxonomy,
        literature=literature,
        context_rows=context_rows,
        position_rows=position_rows,
        position_summary=position_summary,
        clock_rows=clock_rows,
        clock_summary=clock_summary,
        intermittent_rows=intermittent_rows,
        degraded_rows=degraded_rows,
        artifacts=artifacts,
    )
    artifacts.update({f"report_{key}": value for key, value in report_paths.items()})
    artifacts["metadata_json"] = write_metadata(artifacts, subagent_status)
    return {
        "taxonomy": taxonomy,
        "literature": literature,
        "position_summary": position_summary,
        "clock_summary": clock_summary,
        "intermittent_rows": intermittent_rows,
        "artifacts": artifacts,
    }


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print-json", action="store_true", help="Print artifact JSON to stdout.")
    return parser.parse_args()


def main() -> None:
    """CLI entrypoint."""

    args = parse_args()
    subagent_status = {
        "agent_a": "spawned_read_only; orchestrator fallback used for integrated literature table",
        "agent_b": "completed_read_only_taxonomy; integrated conservative labels",
        "agent_c": "spawned_read_only; orchestrator fallback implemented bounded position-prior model",
        "agent_d": "spawned_read_only; orchestrator fallback implemented bounded clock/intermittent model",
        "agent_e": "pending_red_team_or_orchestrator_fallback",
    }
    result = run_exploration(subagent_status=subagent_status)
    if args.print_json:
        print(json.dumps(result["artifacts"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
