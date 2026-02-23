# Implementation Plan: Adaptive Traffic Simulation for Virtual City

**Branch**: `001-adaptive-traffic-sim` | **Date**: 2026-02-23 | **Spec**: `specs/001-adaptive-traffic-sim/spec.md`
**Input**: Feature specification from `/specs/001-adaptive-traffic-sim/spec.md`

**Note**: This plan covers Phase 0 research and Phase 1 design artifacts only
(no implementation tasks yet).

## Summary

Build a playable-speed virtual-city traffic simulation design for ~100k population
that produces realistic congestion concentration, rerouting, and bottlenecks
without relying on real-world map data. The planned technical approach uses a
JAX-first simulation core with active-agent packed arrays, a link-queue + node
model traffic engine, congestion-aware dynamic-potential baseline routing, and a
gradually mixed online learning policy starting with OD-level UCB bandits.
Visualization is planned as a non-blocking WebSocket + Canvas/WebGL stream with
throttled/downsampled UI packets.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: JAX (jit/vmap/segment ops), NumPy-compatible array tooling,
pytest, ruff, WebSocket-based UI stream + browser Canvas/WebGL client (planned),
optional `pyqtgraph` for local debugging prototype only  
**Storage**: N/A for persistent DB; file-based configs/scenario specs/benchmark outputs  
**Testing**: `pytest` (unit/integration/invariant/reproducibility), containerized smoke benchmarks  
**Target Platform**: Linux ROCm container for simulation runtime; desktop browser for UI viewer
**Project Type**: Python simulation engine + lightweight visualization client  
**Performance Goals**: 100k population scenario, 10k-30k active agents, 2-10 Hz tick target;
benchmark and smoke runs report measured tick rate/conditions  
**Constraints**: JAX-first pure step functions; update only active agents via packed arrays;
default traffic engine = link-queue + node model; CTM optional extension; baseline routing
always available; learning uses simulator-only online experience; visualization cannot block core loop  
**Scale/Scope**: Synthetic city with hierarchical roads, barrier + 3-5 bridges, IC/ramps,
zoning, citizen schedule-based trips, disruption events, behavior diversity, adaptive routing,
minimal map/congestion UI + day/time toggles

## Constitution Check (Pre-Research)

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] SDD order preserved (`spec -> plan -> tasks -> implement`); this output is
      planning documentation only, before `/speckit.tasks` and implementation
- [x] Routing/control design keeps a safe baseline (dynamic potential) and
      documents gradual mixing for learned policy in `research.md`
- [x] Learning/training changes use simulator-internal experience only; no
      external data training is included in scope
- [x] Core loop design is JAX-first and `jit`-compatible with explicit state and
      `PRNGKey` handling in `contracts/simulation-step.md`
- [x] Validation plan includes invariants (conservation, non-negative queues,
      capacity violation detection) in `quickstart.md` and `data-model.md`
- [x] Validation plan covers boundary conditions (weekday/weekend, time
      transitions, blocked edges/incidents) in `quickstart.md`
- [x] Reproducibility plan defines fixed-seed expectations in `quickstart.md`
- [x] Performance plan defines benchmark method and target impact in
      `research.md` and `quickstart.md`
- [x] Visualization design is asynchronous and rate-limited via UI packet
      throttling/downsampling in `contracts/ui-data-packets.md`
- [x] Trade-offs are recorded in `specs/001-adaptive-traffic-sim/research.md`
      and flagged for shared architecture sync in `docs/ARCHITECTURE.md`

## Project Structure

### Documentation (this feature)

```text
specs/001-adaptive-traffic-sim/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── simulation-step.md
│   ├── policy-plugin.md
│   └── ui-data-packets.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (next command)
```

### Source Code (repository root)

```text
src/
└── metroflow/
    ├── city/            # synthetic city generation (roads, bridges, zones)
    ├── demand/          # citizens, schedules, trip generation
    ├── flow/            # link-queue + node model state updates
    ├── routing/         # dynamic potential baseline + route candidates
    ├── learning/        # OD bandit/UCB (phase 1), policy plugin adapters
    ├── sim/             # simulation loop orchestration, step/state wrappers
    ├── ui/              # UI packet generation + throttled streaming
    ├── benchmarks/      # benchmark specs and measurement helpers
    └── demo.py

tests/
├── unit/
├── integration/
├── contract/
└── benchmarks/
```

**Structure Decision**: Use the existing single-package Python layout
(`src/metroflow`) and add domain modules aligned to the City/Demand/Flow/Routing/
Learning/UI separation required by the constitution. UI remains loosely coupled
through packet contracts instead of direct rendering calls from the core loop.

## Phase 0 Research Output

- `specs/001-adaptive-traffic-sim/research.md` resolves architecture choices,
  learning sequence, visualization transport choice, and benchmark strategy.
- No unresolved `NEEDS CLARIFICATION` items remain after research.

## Phase 1 Design Output

- `specs/001-adaptive-traffic-sim/data-model.md` defines entities, validation
  rules, and state transitions.
- `specs/001-adaptive-traffic-sim/contracts/simulation-step.md` defines the
  pure-step function signatures and state/telemetry contracts.
- `specs/001-adaptive-traffic-sim/contracts/policy-plugin.md` defines baseline +
  learning plugin boundaries for OD-UCB first and GNN/LSTM extension later.
- `specs/001-adaptive-traffic-sim/contracts/ui-data-packets.md` defines throttled
  non-blocking UI packet schemas and control messages.
- `specs/001-adaptive-traffic-sim/quickstart.md` defines container-first
  validation steps, smoke benchmarks, and invariants/boundary/repro checks.

## Constitution Check (Post-Design Re-Check)

*GATE: Re-check after Phase 1 design artifacts are drafted.*

- [x] Safe baseline routing and gradual learning mix are explicitly defined in
      `contracts/policy-plugin.md` and `research.md`
- [x] Online-only learning source is documented (simulator episodes/rollouts only)
- [x] JAX-first pure-step contract and RNG flow are documented in
      `contracts/simulation-step.md`
- [x] Invariant/boundary/reproducibility validation is specified in
      `data-model.md` and `quickstart.md`
- [x] Performance target and benchmark methodology are documented in
      `research.md` and `quickstart.md`
- [x] UI non-blocking throttling/downsampling is documented in
      `contracts/ui-data-packets.md`
- [x] No constitution violations require complexity exception tracking

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | No constitution violations identified in plan/design phase |
