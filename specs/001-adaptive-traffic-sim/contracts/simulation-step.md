# Contract: Simulation Step Function (Phase 1)

This contract defines the planned pure-function simulation step interfaces for
the JAX-first core. Signatures are design-time contracts and may be refined
during implementation, but compatibility with these responsibilities should be
preserved.

## Design Goals

- JAX `jit`-friendly pure state transitions
- Explicit `PRNGKey` flow for reproducibility
- Separation between core simulation state, control input, telemetry, and UI data
- Safe baseline routing fallback and online learning update hooks

## Core Types (Logical)

- `SimulationConfig`
- `SimulationState`
- `SimulationControl`
- `SimulationTelemetry`
- `UISnapshotSource` (optional output source for packetization)
- `PRNGKey`

Type details are defined in `specs/001-adaptive-traffic-sim/data-model.md`.

## Initialization Contract

```python
def init_simulation(
    config: SimulationConfig,
    scenario_seed: int,
) -> tuple[SimulationState, PRNGKey]:
    ...
```

Behavior:
- Builds synthetic city, zones, POIs, citizens, and initial schedule state
- Initializes link/node dynamic state, event schedule, routing baseline state,
  adaptive learning state, and active-agent pool
- Returns initial `SimulationState` and root `PRNGKey`

## Single Tick Step Contract

```python
def simulation_step(
    state: SimulationState,
    control: SimulationControl,
    rng_key: PRNGKey,
) -> tuple[SimulationState, SimulationTelemetry, UISnapshotSource | None, PRNGKey]:
    ...
```

### Input Contract

#### `SimulationState`

Must contain:
- Static city topology references
- Demand generation state
- Active-agent packed arrays and free-slot bookkeeping
- Link-queue and node-model dynamic state
- Routing baseline state
- Adaptive learning state (OD-UCB initially; plugin slot reserved)
- Metrics accumulators and invariant counters

#### `SimulationControl`

Fields:
- `pause` (bool)
- `set_day_type` (optional weekday/weekend override)
- `set_time_band` (optional time band override)
- `inject_event` (optional `TrafficEvent` or batch)
- `clear_event_ids` (optional list[int])
- `ui_force_snapshot` (bool; request snapshot emission without raising UI cadence)

Control rules:
- Control changes MUST not mutate in-progress trip identity/state outside the step
- Day/time overrides affect future trip generation and routing context, not
  retroactive trip reconstruction

### Output Contract

#### `SimulationState` (next)

- Represents the complete next tick state after flow, agent, and learning updates
- Maintains invariant counters and run metrics
- Records fallback state if adaptive outputs are disabled or invalid

#### `SimulationTelemetry`

Must include:
- `tick_index`
- `active_agent_count`
- `trip_generated_this_tick`
- `trip_completed_this_tick`
- `trip_failed_this_tick`
- `capacity_violation_count_delta`
- `negative_queue_detected` (bool)
- `policy_mix_lambda`
- `adaptive_fallback_triggered` (bool)
- `ui_snapshot_emitted` (bool)

#### `UISnapshotSource | None`

- `None` when no UI emission is due this tick (throttled)
- Non-`None` source object when UI update cadence or `ui_force_snapshot` requires
  snapshot emission

#### `PRNGKey`

- Returned key MUST be the only valid source for the next call in deterministic
  execution order

## Batch / Rollout Contract (Optional Helper)

```python
def run_rollout(
    initial_state: SimulationState,
    controls: list[SimulationControl],
    rng_key: PRNGKey,
) -> tuple[SimulationState, list[SimulationTelemetry], PRNGKey]:
    ...
```

Rules:
- Semantics MUST match repeated `simulation_step` calls in the same order
- Used for benchmark and reproducibility tests

## Invariant Validation Hook Contract

```python
def validate_invariants(state: SimulationState) -> InvariantReport:
    ...
```

Expected checks:
- Conservation reconciliation
- Non-negative queues
- Capacity violation detection/reporting integrity
- Active-agent pool slot consistency

## Benchmark Contract (Planning Target)

```python
def benchmark_scenario(
    scenario_id: str,
    seed: int,
    duration_ticks: int,
) -> BenchmarkReport:
    ...
```

Report fields:
- `median_tick_rate_hz`
- `p10_tick_rate_hz`
- `active_agent_count_median`
- `active_agent_count_p95`
- `invariant_violation_counts`
- `environment_descriptor` (container/runtime info)

## Compatibility Notes

- Future CTM mode may extend `SimulationState` and flow-update internals without
  changing the top-level `simulation_step` signature.
- Future GNN+LSTM plugin may extend adaptive policy memory fields without
  removing baseline routing or fallback behavior.
