# Research / Decisions Log

This document records Phase 0 research decisions for
`001-adaptive-traffic-sim`. All blocking technical choices from the plan are
resolved here; no `NEEDS CLARIFICATION` items remain.

## Decision: JAX-first core with active-agent packed arrays

- **Decision**: Use a JAX-first simulation core and update only active travelers
  each tick via packed arrays plus free-slot reuse, rather than updating all
  ~100k citizens every tick.
- **Rationale**: This directly targets the playable-speed goal while preserving
  per-citizen schedules and route-choice diversity. Packed active slots improve
  vectorization and memory locality for JAX operations.
- **Alternatives considered**:
  - Full-population per-tick updates: simpler indexing, but too costly at 100k.
  - Object-per-agent simulation loop: easier to read, but incompatible with
    `jit`/`vmap` performance goals.

## Decision: Base traffic engine = link-queue + node model, CTM optional

- **Decision**: Implement the primary traffic engine as link queues with a
  simplified node model for turns/signals/intersections. Expose a clear
  extension boundary for optional CTM mode later.
- **Rationale**: Link-queue + node model is sufficient for city-game style
  congestion, bottleneck emergence, and rerouting at the target scale while
  remaining JAX-friendly.
- **Alternatives considered**:
  - CTM as default: more detailed shockwave behavior, but higher complexity and
    larger state size for the first playable version.
  - Microscopic vehicle following as default: too expensive and unnecessary for
    the stated product goal.

## Decision: Baseline routing = congestion-aware dynamic potential

- **Decision**: Use dynamic-potential routing (congestion-aware shortest path
  cost field) as the always-available safe baseline policy.
- **Rationale**: It provides stable and explainable behavior under changing
  congestion while supporting immediate fallback if learning becomes unstable.
- **Alternatives considered**:
  - Static shortest path only: fails core product goal (natural rerouting and
    dispersion under congestion/events).
  - Learned routing only: too risky for early stability and debugging.

## Decision: Online learning starts with OD-level UCB bandits

- **Decision**: Begin adaptive learning with OD-specific path candidate bandits
  using UCB-style exploration/exploitation, and mix outcomes gradually with the
  baseline policy.
- **Rationale**: UCB bandits are simpler, more stable, and easier to debug than
  end-to-end policy learning while still enabling gradual route quality
  improvements from simulator experience only.
- **Alternatives considered**:
  - Actor-critic or policy gradient first: greater flexibility but higher
    instability and tuning burden.
  - Rule-based heuristics only: stable but does not satisfy self-improving
    adaptive learning requirement.

## Decision: Learning policy extension via plugin contract (GNN+LSTM later)

- **Decision**: Define a learning policy plugin contract now, with the initial
  implementation backed by OD-UCB and a reserved extension path for future
  GNN+LSTM policies.
- **Rationale**: Preserves separation of concerns and avoids coupling the
  simulation engine to one learning method. Supports incremental evolution from
  bandit to richer sequence/graph policies.
- **Alternatives considered**:
  - Hardcode bandit into routing engine: faster short term, expensive to replace.
  - Design only for GNN+LSTM now: over-engineering before stable baseline data
    flow and metrics exist.

## Decision: Visualization path = WebSocket + Canvas/WebGL (planned default)

- **Decision**: Plan a lightweight browser UI using a WebSocket stream from the
  simulation process and a Canvas/WebGL renderer for road/congestion layers.
  Keep `pyqtgraph` as an optional local debug prototype path, not the primary UI.
- **Rationale**: A packetized stream makes it easier to throttle/downsample and
  prevents renderer latency from blocking the core loop. Browser-based viewing is
  also more portable for future demos.
- **Alternatives considered**:
  - `pyqtgraph` primary UI: fast prototype path, but tighter coupling to local
    runtime and less natural separation for non-blocking packet contracts.
  - In-process custom renderer: maximal control, highest implementation cost.

## Decision: UI packets are versioned, throttled, and downsample-capable

- **Decision**: Define explicit UI packet types for topology snapshots,
  congestion overlays, simulation metrics, events, and control commands with
  schema version fields and throttle hints.
- **Rationale**: Versioned packets support iterative UI evolution and prevent
  accidental tight coupling between UI and simulation internals. Throttle hints
  formalize the non-blocking visualization rule.
- **Alternatives considered**:
  - Direct Python object sharing: simple but incompatible with loose coupling and
    future browser clients.
  - Framebuffer/image streaming only: easier rendering path but harder to inspect
    structured congestion and route metrics.

## Decision: Benchmark plan uses scenario-defined median tick rate + invariants

- **Decision**: Measure performance using a documented standard synthetic city
  scenario (~100k population, 10k-30k active target band) and report median tick
  rate, active-agent count distribution, and invariant violations per run.
- **Rationale**: Median tick rate and active counts are directly tied to the
  "playable speed" goal. Including invariants prevents performance regressions
  that silently break simulation correctness.
- **Alternatives considered**:
  - Only microbenchmarks of isolated kernels: useful for optimization but not
    sufficient to claim playable end-to-end performance.
  - Mean-only tick rate: too sensitive to warmup spikes and outliers.

## Decision: Module boundaries follow City / Demand / Flow / Routing / Learning / UI

- **Decision**: Keep city generation, demand/trip generation, traffic flow,
  routing, learning, and UI packetization as separate modules with narrow data
  contracts.
- **Rationale**: Matches constitution guidance, improves testability, and makes
  future engine or UI replacements less risky.
- **Alternatives considered**:
  - Monolithic simulation module: simpler initial coding, poor maintainability.
  - UI-driven simulation loop ownership: risks blocking core loop and mixed
    responsibilities.

## Decision: Topology realism metrics are machine-readable threshold checks, not visual-only judgment

- **Decision**: Evaluate the Phase 8 road-generator realism upgrade with
  explicit machine-readable metrics and threshold results (`node/link/zone/POI`
  counts, morphology irregularity, bridge closure sensitivity, zoning
  diversity), and attach them to a `RealismReport` that names the
  `scenario_mode`.
- **Rationale**: The extension needs measurable evidence for realism claims
  without conflating road-only generator quality with later transit runtime
  behavior. Machine-readable thresholds make regression tests and benchmark
  reporting stable across revisions and fixed seeds.
- **Alternatives considered**:
  - Screenshot/manual map review only: useful for spotting issues, but too
    subjective to gate regressions or benchmark claims.
  - One aggregate realism score only: easier to compare, but hides which aspect
    regressed (resolution, chokepoint criticality, zoning diversity, or
    morphology).

## Decision: Transit MVP remains phase-gated behind road-only baseline and static-to-dynamic milestones

- **Decision**: Keep the transit/metro extension split across three gates:
  Phase 9 static network wiring, Phase 10 passenger-flow summaries, and Phase
  11 multimodal candidate comparison/UI reporting. Road-only mode remains the
  default fallback and multimodal benchmarks stay separate until both static and
  passenger-flow contracts exist.
- **Rationale**: This reduces regression risk against the baseline road-only
  demo and preserves a narrow debugging surface at each stage. It also matches
  the data model boundary where `StationSummary` may remain zero-filled during
  static-wiring scenarios and only becomes behaviorally meaningful after
  passenger-flow updates.
- **Alternatives considered**:
  - Introduce transit network, passenger flow, and multimodal routing in one
    step: faster on paper, but too hard to isolate failures in contracts,
    invariants, and benchmark deltas.
  - Enable multimodal benchmarking as soon as static transit topology exists:
    misleading, because waiting/transfer behavior and station summaries are not
    representative until later phases.

## Deferred (Non-blocking) Choices

- Exact browser rendering stack details beyond Canvas/WebGL (pure Canvas2D vs
  WebGL helper library) are deferred to implementation tasks.
- Exact OD path-candidate generation heuristic (K-shortest vs periodic refresh
  from dynamic potential) is deferred to implementation tasks, but the contract
  requires deterministic behavior under fixed seeds.

## Documentation Sync Notes

- Feature-specific tradeoffs are documented here for planning.
- Shared architecture tradeoffs that affect all future features should also be
  summarized in `docs/ARCHITECTURE.md` during implementation or architecture
  review.
