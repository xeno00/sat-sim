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
        exact_change="Remove display smoothing/fitting from graph metrics; raw metrics are unchanged.",
        expected_raw_metric_change="none",
    )


def migration_ladder_steps() -> list[MigrationStep]:
    """Return the implemented controlled migration ladder steps."""

    return [
        legacy_behavior_freeze_step(),
        legacy_staged_compatible_step(),
        step_a_no_display_smoothing(),
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
