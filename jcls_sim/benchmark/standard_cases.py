"""Canonical standard benchmark-case definitions."""

from __future__ import annotations

from dataclasses import asdict, dataclass

STANDARD_CASE_ROLES = frozenset(
    {
        "primary_standard",
        "secondary_low_satellite_stress",
        "diagnostic",
    }
)

PRIMARY_STANDARD_CASE_ID = "std_nu3_ns10_fullmesh_los_clock1us_seed0"
SECONDARY_LOW_SATELLITE_STRESS_CASE_ID = "std_nu3_ns4_fullmesh_los_clock1us_seed0"


@dataclass(frozen=True)
class StandardCaseSpec:
    """Schema for a non-final benchmark-card standard case."""

    case_id: str
    role: str
    num_users: int
    num_satellites: int
    sidelink_graph: str
    clock_std_seconds: float
    seed: int
    operation_time_seconds: float
    trial_count: int
    channel_model: str
    geometry_model: str
    notes: str

    def __post_init__(self) -> None:
        """Validate standard-case fields."""

        if not self.case_id:
            raise ValueError("case_id must be nonempty.")
        if self.role not in STANDARD_CASE_ROLES:
            raise ValueError(f"Unsupported standard-case role: {self.role!r}.")
        if self.num_users < 1:
            raise ValueError("num_users must be at least 1.")
        if self.num_satellites < 1:
            raise ValueError("num_satellites must be at least 1.")
        if self.clock_std_seconds <= 0.0:
            raise ValueError("clock_std_seconds must be positive.")
        if self.seed < 0:
            raise ValueError("seed must be nonnegative.")
        if self.operation_time_seconds <= 0.0:
            raise ValueError("operation_time_seconds must be positive.")
        if self.trial_count < 1:
            raise ValueError("trial_count must be at least 1.")
        for field_name in ("sidelink_graph", "channel_model", "geometry_model", "notes"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value:
                raise ValueError(f"{field_name} must be a nonempty string.")

    def to_dict(self) -> dict[str, float | int | str]:
        """Return a JSON-compatible dictionary."""

        return asdict(self)


def primary_standard_case() -> StandardCaseSpec:
    """Return the universal primary standard benchmark case."""

    case = StandardCaseSpec(
        case_id=PRIMARY_STANDARD_CASE_ID,
        role="primary_standard",
        num_users=3,
        num_satellites=10,
        sidelink_graph="full_mesh",
        clock_std_seconds=1.0e-6,
        seed=0,
        operation_time_seconds=0.5,
        trial_count=1,
        channel_model="LOS/Rician when supported",
        geometry_model="manuscript-like MIT/Stata UE geometry and Starlink-like LEO geometry when supported",
        notes="Primary universal benchmark fingerprint; do not substitute the low-satellite stress case.",
    )
    if case.case_id == SECONDARY_LOW_SATELLITE_STRESS_CASE_ID or case.role != "primary_standard":
        raise RuntimeError("primary_standard_case attempted to return a non-primary case.")
    return case


def secondary_low_satellite_stress_case() -> StandardCaseSpec:
    """Return the secondary low-satellite observability stress case."""

    return StandardCaseSpec(
        case_id=SECONDARY_LOW_SATELLITE_STRESS_CASE_ID,
        role="secondary_low_satellite_stress",
        num_users=3,
        num_satellites=4,
        sidelink_graph="full_mesh",
        clock_std_seconds=1.0e-6,
        seed=0,
        operation_time_seconds=0.5,
        trial_count=1,
        channel_model="LOS/Rician when supported",
        geometry_model="manuscript-like MIT/Stata UE geometry and Starlink-like LEO geometry when supported",
        notes="Secondary stress case only; never the primary universal benchmark.",
    )


def standard_cases() -> tuple[StandardCaseSpec, ...]:
    """Return all canonical standard cases."""

    return (primary_standard_case(), secondary_low_satellite_stress_case())


def get_standard_case(case_id: str) -> StandardCaseSpec:
    """Return a standard case by ID."""

    for case in standard_cases():
        if case.case_id == case_id:
            return case
    raise KeyError(f"Unknown standard case ID: {case_id}")


def is_primary_standard_case(case_id: str) -> bool:
    """Return True only for the primary universal benchmark case."""

    return case_id == PRIMARY_STANDARD_CASE_ID
