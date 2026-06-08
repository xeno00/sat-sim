"""Controlled legacy-to-V24 migration step definitions.

The migration ladder intentionally starts from the working legacy-compatible
behavior and changes one configuration axis at a time. These helpers describe
the ladder; they do not import or execute notebook code.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class MigrationStep:
    """Configuration for one controlled migration step."""

    name: str
    estimator_mode: str
    internal_clock_mode: str
    acceptance_mode: str
    metric_mode: str
    weighting_mode: str
    geometry_noise_mode: str
    display_transform_mode: str
    map_covariance_mode: str
    map_update_mode: str
    exact_change: str
    expected_raw_metric_change: str

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""

        return asdict(self)


def legacy_behavior_freeze_step() -> MigrationStep:
    """Return the frozen legacy behavior baseline configuration."""

    return MigrationStep(
        name="legacy_behavior_freeze",
        estimator_mode="legacy_notebook_replay",
        internal_clock_mode="all_clock",
        acceptance_mode="truth_gated_legacy",
        metric_mode="legacy_all_clock_sync",
        weighting_mode="legacy_notebook",
        geometry_noise_mode="legacy_replay",
        display_transform_mode="legacy_replay_display",
        map_covariance_mode="truth_error_diagonal",
        map_update_mode="truth_gated_legacy",
        exact_change="None; this is the frozen behavioral baseline.",
        expected_raw_metric_change="none",
    )


def legacy_staged_compatible_step() -> MigrationStep:
    """Return package-accessible wrapper configuration for legacy behavior."""

    return MigrationStep(
        name="legacy_staged_compatible",
        estimator_mode="legacy_staged_compatible",
        internal_clock_mode="all_clock",
        acceptance_mode="truth_gated_legacy",
        metric_mode="legacy_all_clock_sync",
        weighting_mode="legacy_notebook",
        geometry_noise_mode="legacy_replay",
        display_transform_mode="legacy_replay_display",
        map_covariance_mode="truth_error_diagonal",
        map_update_mode="truth_gated_legacy",
        exact_change="Expose the legacy staged behavior as a package-described estimator mode without changing behavior.",
        expected_raw_metric_change="none",
    )


def step_a_no_display_smoothing() -> MigrationStep:
    """Return Step A configuration: raw metrics without display smoothing."""

    return MigrationStep(
        name="step_a_no_display_smoothing",
        estimator_mode="legacy_staged_compatible",
        internal_clock_mode="all_clock",
        acceptance_mode="truth_gated_legacy",
        metric_mode="legacy_all_clock_sync",
        weighting_mode="legacy_notebook",
        geometry_noise_mode="legacy_replay",
        display_transform_mode="raw_metrics_no_smoothing",
        map_covariance_mode="truth_error_diagonal",
        map_update_mode="truth_gated_legacy",
        exact_change="Remove display smoothing/fitting from graph metrics; raw metrics are unchanged.",
        expected_raw_metric_change="none",
    )


def step_b_lm_residual_acceptance() -> MigrationStep:
    """Return Step B configuration: LM residual/trust-region acceptance."""

    return MigrationStep(
        name="step_b_lm_residual_acceptance",
        estimator_mode="legacy_staged_compatible",
        internal_clock_mode="all_clock",
        acceptance_mode="residual_trust_region",
        metric_mode="legacy_all_clock_sync",
        weighting_mode="legacy_notebook",
        geometry_noise_mode="legacy_replay",
        display_transform_mode="raw_metrics_no_smoothing",
        map_covariance_mode="truth_error_diagonal",
        map_update_mode="truth_gated_legacy",
        exact_change=(
            "Replace LM true-state acceptance with observable residual-cost, "
            "finite-candidate, and bounded-step checks; keep all other legacy "
            "internals fixed."
        ),
        expected_raw_metric_change="possible; this is the first estimator-decision migration step",
    )


def _diagnosis_step(name: str, covariance_mode: str, update_mode: str, exact_change: str) -> MigrationStep:
    """Return a Step C diagnosis configuration."""

    return MigrationStep(
        name=name,
        estimator_mode="legacy_staged_compatible",
        internal_clock_mode="all_clock",
        acceptance_mode="residual_trust_region",
        metric_mode="legacy_all_clock_sync",
        weighting_mode="legacy_notebook",
        geometry_noise_mode="legacy_replay",
        display_transform_mode="raw_metrics_no_smoothing",
        map_covariance_mode=covariance_mode,
        map_update_mode=update_mode,
        exact_change=exact_change,
        expected_raw_metric_change="possible; this is a Step C MAP/EKF diagnosis sub-ablation",
    )


def step_c0_legacy_map_instrumented() -> MigrationStep:
    """Return C0: instrument legacy MAP without behavior change."""

    return _diagnosis_step(
        name="step_c0_legacy_map_instrumented",
        covariance_mode="truth_error_diagonal",
        update_mode="truth_gated_legacy_instrumented",
        exact_change="Instrument legacy MAP covariance/update behavior without changing behavior.",
    )


def step_c1_legacy_cov_observable_acceptance() -> MigrationStep:
    """Return C1: legacy covariance with observable MAP acceptance."""

    return _diagnosis_step(
        name="step_c1_legacy_cov_observable_acceptance",
        covariance_mode="truth_error_diagonal",
        update_mode="observable_residual_covariance_checks",
        exact_change="Keep legacy truth-derived MAP covariance but replace MAP acceptance/reversion with observable checks.",
    )


def step_c2_observable_cov_legacy_acceptance() -> MigrationStep:
    """Return C2: observable covariance with legacy MAP acceptance."""

    return _diagnosis_step(
        name="step_c2_observable_cov_legacy_acceptance",
        covariance_mode="damped_information_pseudoinverse",
        update_mode="truth_gated_legacy",
        exact_change="Replace MAP covariance with a non-truth damped information pseudoinverse while preserving legacy truth-gated MAP acceptance.",
    )


def step_c3_cov_diag_prior() -> MigrationStep:
    """Return C3 diagonal-prior covariance candidate."""

    return _diagnosis_step(
        name="step_c3_cov_diag_prior",
        covariance_mode="diagonal_prior",
        update_mode="observable_residual_covariance_checks",
        exact_change="Use a non-truth diagonal prior covariance with observable MAP acceptance.",
    )


def step_c3_cov_block_diag() -> MigrationStep:
    """Return C3 block-diagonal covariance candidate."""

    return _diagnosis_step(
        name="step_c3_cov_block_diag",
        covariance_mode="block_diagonal_position_clock",
        update_mode="observable_residual_covariance_checks",
        exact_change="Use a non-truth block-diagonal position/clock covariance with observable MAP acceptance.",
    )


def step_c3_cov_damped_inverse() -> MigrationStep:
    """Return C3 damped inverse covariance candidate."""

    return _diagnosis_step(
        name="step_c3_cov_damped_inverse",
        covariance_mode="damped_inverse_normal_matrix",
        update_mode="observable_residual_covariance_checks",
        exact_change="Use a non-truth damped inverse normal-matrix covariance with observable MAP acceptance.",
    )


def step_c3_cov_damped_pinv() -> MigrationStep:
    """Return C3 damped pseudoinverse covariance candidate."""

    return _diagnosis_step(
        name="step_c3_cov_damped_pinv",
        covariance_mode="damped_pseudoinverse_information_matrix",
        update_mode="observable_residual_covariance_checks",
        exact_change="Use a non-truth damped pseudoinverse information covariance with observable MAP acceptance.",
    )


def step_c3_cov_residual_scaled() -> MigrationStep:
    """Return C3 residual-scaled covariance candidate."""

    return _diagnosis_step(
        name="step_c3_cov_residual_scaled",
        covariance_mode="residual_scaled_information_pseudoinverse",
        update_mode="observable_residual_covariance_checks",
        exact_change="Use a non-truth residual-scaled information covariance with observable MAP acceptance.",
    )


def step_c4_composite_map_acceptance() -> MigrationStep:
    """Return C4: legacy covariance with composite observable MAP acceptance."""

    return _diagnosis_step(
        name="step_c4_composite_map_acceptance",
        covariance_mode="truth_error_diagonal",
        update_mode="composite_observable",
        exact_change=(
            "Keep Step B residual LM acceptance and legacy MAP covariance, "
            "but replace MAP truth-state acceptance with a composite observable "
            "MAP objective, covariance, and bounded-update acceptance rule."
        ),
    )


def migration_ladder_steps() -> list[MigrationStep]:
    """Return the implemented controlled migration ladder steps."""

    return [
        legacy_behavior_freeze_step(),
        legacy_staged_compatible_step(),
        step_a_no_display_smoothing(),
        step_b_lm_residual_acceptance(),
        step_c0_legacy_map_instrumented(),
        step_c1_legacy_cov_observable_acceptance(),
        step_c2_observable_cov_legacy_acceptance(),
        step_c3_cov_diag_prior(),
        step_c3_cov_block_diag(),
        step_c3_cov_damped_inverse(),
        step_c3_cov_damped_pinv(),
        step_c3_cov_residual_scaled(),
        step_c4_composite_map_acceptance(),
    ]


def step_diff(previous: MigrationStep, current: MigrationStep) -> dict[str, tuple[str, str]]:
    """Return changed fields between two migration steps."""

    before = previous.to_dict()
    after = current.to_dict()
    ignored = {"name", "exact_change", "expected_raw_metric_change"}
    return {
        key: (before[key], after[key])
        for key in sorted(before)
        if key not in ignored and before[key] != after[key]
    }
