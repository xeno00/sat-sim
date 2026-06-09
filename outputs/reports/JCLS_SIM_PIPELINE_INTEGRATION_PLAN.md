# jcls_sim Pipeline Integration Plan

Generated: 2026-06-09

## Objective

Create one canonical package interface for pipeline definitions and standard benchmark-card runs. The next benchmark-card runner should call this interface rather than embedding another script-local pipeline schema.

## Proposed Package Layout

```text
jcls_sim/
  pipelines/
    __init__.py
    specs.py
    registry.py
    legacy.py
    migration.py
    package_native.py
    c7.py
    legacy_surgical.py
  benchmark/
    __init__.py
    standard_cases.py
    runner.py
    metrics.py
```

## Key Data Structures

```python
@dataclass(frozen=True)
class PipelineStageVersions:
    system_model_version: str
    initialization_version: str | None
    stage_a_version: str | None
    stage_b_version: str | None
    stage_c_version: str | None
    metric_version: str
    units_version: str
```

```python
@dataclass(frozen=True)
class TruthUseLedger:
    truth_state_used_for_initialization: bool
    truth_state_used_for_stage_a_acceptance: bool
    truth_state_used_for_lm_acceptance: bool
    truth_state_used_for_map_covariance: bool
    truth_state_used_for_map_acceptance: bool
    truth_state_used_for_prior_simulation: bool
    truth_state_used_for_metrics: bool
    notes: tuple[str, ...] = ()
```

```python
@dataclass(frozen=True)
class PipelineSpec:
    pipeline_id: str
    label: str
    versions: PipelineStageVersions
    truth_use: TruthUseLedger
    readiness: str
    recommended_use: str
    runner_kind: str
    adapter_name: str
```

```python
@dataclass(frozen=True)
class StandardCaseSpec:
    case_id: str
    num_users: int
    num_satellites: int
    clock_std_dev_seconds: float
    seed: int
    sidelink_graph: str = "full_mesh"
    operation_time_seconds: float | None = 0.5
    trial_count: int = 1
```

```python
@dataclass(frozen=True)
class StageMetrics:
    position_error_m: float | None
    sync_error_ns: float | None
    missing_reason: str | None = None
```

```python
@dataclass(frozen=True)
class PipelineRunResult:
    pipeline: PipelineSpec
    case: StandardCaseSpec
    initialization: StageMetrics
    step_a: StageMetrics
    step_b: StageMetrics
    step_c: StageMetrics
    truth_usage: TruthUseLedger
    units_status: str
    warnings: tuple[str, ...]
    raw_diagnostics: dict[str, Any]
```

```python
@dataclass(frozen=True)
class BenchmarkCard:
    case: StandardCaseSpec
    rows: tuple[PipelineRunResult, ...]
    generated_at: str
    artifact_status: str = "non_final_benchmark_card"
```

## Common Interface

Every benchmark-capable pipeline should eventually expose:

```python
def run_pipeline(case: StandardCaseSpec, pipeline: PipelineSpec) -> PipelineRunResult:
    ...
```

If a metric is unavailable, the adapter must return `None` with a reason rather than omitting the field.

## What Belongs In jcls_sim

| item | current_path | classification | target_path | integrate_now | reason | risk | test_needed |
|---|---|---|---|---|---|---|---|
| Pipeline dataclasses | not present | new reusable schema | `jcls_sim/pipelines/specs.py` | yes | Needed before benchmark-card runner. | low | Unit tests for JSON-ready fields and missing metrics. |
| Pipeline registry | script/report scattered | reusable registry | `jcls_sim/pipelines/registry.py` | yes | Prevent script-local pipeline IDs. | low | Test required pipeline IDs present. |
| Primary/secondary standard cases | scattered in reports/scripts | reusable standard cases | `jcls_sim/benchmark/standard_cases.py` | yes | Stops primary-case drift. | low | Test primary is Ns=10 and Ns=4 is secondary only. |
| Benchmark card schema | not present | reusable benchmark model | `jcls_sim/benchmark/runner.py` | yes | Gives next runner one schema. | medium | Test rows preserve missing metrics and metadata. |
| Package-native C7 adapter | `jcls_sim/algorithm.py`, `figure_generation.py` | reusable estimator adapter | `jcls_sim/pipelines/c7.py` | yes | Already package-native; easiest first adapter. | medium | Smoke test tiny card, no figure output. |
| Controlled Step B spec | `jcls_sim/migration.py`, `scripts/run_controlled_migration_ladder.py` | pipeline definition + script execution | `jcls_sim/pipelines/migration.py` | yes, spec first | Needed as benchmark backbone. | medium | Registry/spec tests before execution adapter. |
| Legacy-surgical specs | `scripts/run_legacy_surgical_*.py` | script-local pipeline spec | `jcls_sim/pipelines/legacy_surgical.py` | yes, spec first | Recommended primary path. | medium-high | Tests for truth-use ledger and standard-case mapping. |
| Legacy namespace execution hooks | replay/migration scripts | legacy/provenance adapter | remain script-only initially | no | Unsafe to pull notebook execution into core package before adapter boundary. | high | Later adapter tests with no notebook mutation. |
| Report builders/gallery | scripts | report_builder/gallery_builder | remain `scripts/` | no | CLI side effects and output writing are not package API. | low | Existing tests. |
| CRLB candidate scripts | scripts + package FIM/bounds | diagnostic runner | mostly remain `scripts/` | no for benchmark | Estimator benchmark should not mix CRLB figure diagnostics. | low | Existing CRLB tests. |
| GNSS/wave branches | parked worktrees | exploratory | parked only | no | Not in current downselect. | unknown | Needs lineage/units before any integration. |

## Standard Benchmark Runner Plan

First implementation should create package schemas and a tiny runner wrapper, not execute broad grids.

Target case:

`std_nu3_ns10_fullmesh_los_clock1us_seed0`

Candidate pipelines:

1. `legacy_surgical_prior_region`;
2. `controlled_migration_step_b_lm_only`;
3. `package_native_c7`;
4. `legacy_truth_gated_l0_reference_only`.

Expected output fields:

- pipeline tuple;
- truth-use ledger;
- units status;
- readiness and recommended use;
- initialization, Step A, Step B, Step C localization error in meters;
- initialization, Step A, Step B, Step C synchronization error in ns;
- missing-metric reasons;
- warnings.

## Implementation Phases

1. **Schema-only phase**: add `jcls_sim/pipelines/specs.py`, `registry.py`, `jcls_sim/benchmark/standard_cases.py`, and tests. No simulations.
2. **Package-native adapter phase**: add C7/package-native adapter that calls existing `jcls_sim` functions and returns `PipelineRunResult`. Tiny smoke only.
3. **Legacy-surgical spec phase**: port script-local `PipelineSpec`, `StandardCase`, `PriorConfig`, and truth/unit ledgers into package modules without moving notebook execution hooks.
4. **Legacy execution adapter phase**: create a thin adapter that can call existing legacy-surgical runner internals under a benchmark interface while keeping notebook extraction side effects in scripts.
5. **Benchmark-card CLI phase**: write a script that calls only `jcls_sim.benchmark.runner` and writes non-final CSV/JSON cards.

## First Integration Step

Implement the schema-only phase. This is the safest next step because it creates the canonical package interface without rerunning or moving any legacy execution logic.

## Stop Gates

- Need to execute the notebook.
- Need to move legacy namespace execution into `jcls_sim` before the adapter boundary is tested.
- Any benchmark runner starts writing figure outputs.
- Any pipeline cannot provide truth-use or units metadata.
