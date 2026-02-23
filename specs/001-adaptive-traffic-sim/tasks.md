---

description: "Task list for Adaptive Traffic Simulation for Virtual City"
---

# Tasks: Adaptive Traffic Simulation for Virtual City

**Input**: Design documents from `/specs/001-adaptive-traffic-sim/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: This feature explicitly requires invariant, boundary-condition, reproducibility, and benchmark validation. Test tasks are included for each user story and cross-cutting simulation behavior.

**Organization**: Tasks are grouped by user story so each phase can be implemented and validated as an independently testable increment.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (`[US1]`, `[US2]`, `[US3]`)
- Every task includes at least one exact file path

## Path Conventions

- Python package: `src/metroflow/`
- Tests: `tests/unit/`, `tests/integration/`, `tests/contract/`, `tests/benchmarks/`
- Feature docs: `specs/001-adaptive-traffic-sim/`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create module/test scaffolding and baseline configuration files needed before shared simulation code

- [ ] T001 Create package directories and `__init__.py` files in `src/metroflow/city/__init__.py`, `src/metroflow/demand/__init__.py`, `src/metroflow/flow/__init__.py`, `src/metroflow/routing/__init__.py`, `src/metroflow/learning/__init__.py`, `src/metroflow/sim/__init__.py`, `src/metroflow/ui/__init__.py`, and `src/metroflow/benchmarks/__init__.py`
- [ ] T002 [P] Create test directory scaffolding files `tests/unit/__init__.py`, `tests/integration/__init__.py`, `tests/contract/__init__.py`, and `tests/benchmarks/__init__.py`
- [ ] T003 [P] Add shared pytest fixtures skeleton in `tests/conftest.py`
- [ ] T004 [P] Add feature test constants/seed registry in `tests/fixtures/simulation_scenarios.py`
- [ ] T005 [P] Add benchmark report utility skeleton in `src/metroflow/benchmarks/reporting.py`
- [ ] T006 Record implementation task checkpoints and validation command placeholders in `specs/001-adaptive-traffic-sim/quickstart.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared simulation primitives and contracts that MUST exist before any user story implementation

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T007 Implement configuration dataclasses and enums in `src/metroflow/sim/config.py`
- [ ] T008 [P] Implement PRNG seed/key helper functions in `src/metroflow/sim/rng.py`
- [ ] T009 [P] Implement simulation control/telemetry dataclasses in `src/metroflow/sim/control.py`
- [ ] T010 Implement core simulation state containers (static + dynamic references) in `src/metroflow/sim/state.py`
- [ ] T011 [P] Implement active-agent packed pool primitives in `src/metroflow/sim/active_agents.py`
- [ ] T012 [P] Implement invariant validation/report structures in `src/metroflow/sim/invariants.py`
- [ ] T013 Implement graph CSR/topology primitives and validation in `src/metroflow/city/graph.py`
- [ ] T014 [P] Implement link/node flow state containers in `src/metroflow/flow/state.py`
- [ ] T015 [P] Implement baseline/adaptive policy blend controller skeleton in `src/metroflow/learning/policy_blend.py`
- [ ] T016 [P] Implement UI packet envelope and schema version helpers in `src/metroflow/ui/packets.py`
- [ ] T017 Implement throttled UI snapshot emission buffer in `src/metroflow/ui/stream_buffer.py`
- [ ] T018 Implement simulation step/init function skeletons matching `specs/001-adaptive-traffic-sim/contracts/simulation-step.md` in `src/metroflow/sim/step.py`
- [ ] T019 [P] Add contract tests for simulation step signatures and telemetry keys in `tests/contract/test_simulation_step_contract.py`
- [ ] T020 [P] Add contract tests for UI packet envelope/schema version behavior in `tests/contract/test_ui_packet_contract.py`
- [ ] T021 [P] Add unit tests for active-agent pool consistency and free-slot reuse in `tests/unit/test_active_agent_pool.py`
- [ ] T022 [P] Add unit tests for invariant validator core checks (conservation hooks, non-negative queue, capacity flags) in `tests/unit/test_invariants_core.py`

**Checkpoint**: Foundation ready - user story implementation can now proceed with stable state, contract, and validation primitives

---

## Phase 3: User Story 1 - 가상 도시 교통 관찰 (Priority: P1) 🎯 MVP

**Goal**: Generate a synthetic 100k-scale city with schedules/trips and visualize road network + congestion with day/time toggles at playable baseline behavior

**Independent Test**: Start a fixed-seed synthetic city scenario, run the baseline simulation, and confirm topology + congestion UI output plus day/time toggle effects appear without violating core invariants

### Tests for User Story 1

- [ ] T023 [P] [US1] Add unit tests for city generation hierarchy/bridge/zoning constraints in `tests/unit/test_city_generation.py`
- [ ] T024 [P] [US1] Add unit tests for citizen schedule templates and trip request generation by weekday/weekend + time bands in `tests/unit/test_demand_schedules.py`
- [ ] T025 [P] [US1] Add integration tests for baseline simulation smoke with topology/congestion outputs in `tests/integration/test_us1_baseline_simulation.py`
- [ ] T026 [P] [US1] Add boundary-condition tests for day-type and time-band toggles on in-flight vs future trips in `tests/integration/test_us1_day_time_transitions.py`
- [ ] T027 [P] [US1] Add contract tests for `ui.topology_snapshot`, `ui.congestion_frame`, and `ui.metrics_summary` packets in `tests/contract/test_ui_topology_congestion_contract.py`
- [ ] T028 [US1] Add invariant regression test covering conservation/non-negative queues/capacity detection during baseline run in `tests/integration/test_us1_invariants.py`

### Implementation for User Story 1

- [ ] T029 [P] [US1] Implement synthetic city topology generator (hierarchy, barrier, bridges, ramps/intersections) in `src/metroflow/city/generator.py`
- [ ] T030 [P] [US1] Implement zoning and POI placement generation in `src/metroflow/city/zones.py`
- [ ] T031 [P] [US1] Implement citizen population, behavior profiles, and schedule templates in `src/metroflow/demand/population.py`
- [ ] T032 [US1] Implement trip request generation/activation pipeline in `src/metroflow/demand/trips.py`
- [ ] T033 [US1] Implement link-queue + node model baseline flow updates in `src/metroflow/flow/engine.py`
- [ ] T034 [US1] Implement congestion-aware dynamic-potential baseline routing in `src/metroflow/routing/dynamic_potential.py`
- [ ] T035 [US1] Implement simulation initialization builder wiring city/demand/flow/routing state in `src/metroflow/sim/init.py`
- [ ] T036 [US1] Implement baseline tick orchestration (spawn, route, advance, complete, validate invariants) in `src/metroflow/sim/step.py`
- [ ] T037 [US1] Implement UI snapshot source builder for topology/congestion/metrics in `src/metroflow/ui/snapshots.py`
- [ ] T038 [US1] Implement UI control handling for day-type/time-band toggles and snapshot requests in `src/metroflow/ui/control_adapter.py`
- [ ] T039 [US1] Implement minimal stream server for navigator-style map packets in `src/metroflow/ui/stream_server.py`
- [ ] T040 [US1] Integrate baseline scenario run and UI stream options into demo entrypoint `src/metroflow/demo.py`
- [ ] T041 [US1] Implement baseline run summary aggregation (trip totals, hotspot metrics) in `src/metroflow/sim/run_summary.py`

**Checkpoint**: User Story 1 provides a playable baseline virtual-city traffic simulation with observable congestion and day/time toggles

---

## Phase 4: User Story 2 - 이벤트 대응과 행동 다양성 관찰 (Priority: P2)

**Goal**: Add accident/construction/congestion events and heterogeneous route behavior so disruptions cause rerouting, persistence, and visible network redistribution

**Independent Test**: Inject a bridge/arterial disruption in a fixed-seed peak scenario and verify mixed traveler responses plus UI-visible congestion redistribution without crashes or invariant regressions

### Tests for User Story 2

- [ ] T042 [P] [US2] Add unit tests for traffic event scheduling/activation/clearing in `tests/unit/test_traffic_events.py`
- [ ] T043 [P] [US2] Add unit tests for route-choice profile diversity sampling and persistence/reroute thresholds in `tests/unit/test_behavior_profiles.py`
- [ ] T044 [P] [US2] Add integration tests for blocked-edge/bridge event rerouting and recorded failures in `tests/integration/test_us2_disruption_rerouting.py`
- [ ] T045 [P] [US2] Add integration tests for congestion redistribution after incidents in `tests/integration/test_us2_congestion_redistribution.py`
- [ ] T046 [P] [US2] Add contract tests for `ui.event_overlay`, `ui.control_command`, and `ui.control_ack` packets in `tests/contract/test_ui_event_control_contract.py`
- [ ] T047 [US2] Add boundary/invariant regression tests for disruption scenarios (blocked edges + time transitions) in `tests/integration/test_us2_boundary_invariants.py`

### Implementation for User Story 2

- [ ] T048 [P] [US2] Implement traffic event models and scheduler state transitions in `src/metroflow/flow/events.py`
- [ ] T049 [US2] Implement event effects on link capacities/closures in `src/metroflow/flow/event_effects.py`
- [ ] T050 [P] [US2] Implement route-choice behavior profile generation and diversity sampling in `src/metroflow/routing/behavior_profiles.py`
- [ ] T051 [US2] Implement disruption-aware reroute trigger logic (reroute vs persist) in `src/metroflow/routing/reroute_policy.py`
- [ ] T052 [US2] Integrate traffic events and behavior diversity into tick orchestration in `src/metroflow/sim/step.py`
- [ ] T053 [US2] Implement event overlay packet generation and command acknowledgements in `src/metroflow/ui/packets.py`
- [ ] T054 [US2] Implement disruption scenario presets for demos in `src/metroflow/ui/scenario_controls.py`
- [ ] T055 [US2] Extend run summary with disruption response metrics (reroute share, persistence share, corridor shifts) in `src/metroflow/sim/run_summary.py`

**Checkpoint**: User Story 2 demonstrates event-driven congestion changes and mixed route behavior for affected travelers

---

## Phase 5: User Story 3 - 시뮬레이터 경험 기반 경로 개선 (Priority: P3)

**Goal**: Add simulator-only online adaptive learning (OD-UCB first) mixed safely with baseline routing, with reproducible comparisons and benchmark reporting

**Independent Test**: Run repeated fixed-seed scenarios with adaptive learning on/off and verify stable baseline fallback, reproducible run summaries, and measurable travel-time improvement without completion-rate collapse

### Tests for User Story 3

- [ ] T056 [P] [US3] Add contract tests for adaptive policy plugin init/score/update boundaries in `tests/contract/test_policy_plugin_contract.py`
- [ ] T057 [P] [US3] Add unit tests for OD-UCB arm selection and online reward updates in `tests/unit/test_od_ucb_bandit.py`
- [ ] T058 [P] [US3] Add integration tests for baseline/adaptive mixing and fallback-to-baseline safety behavior in `tests/integration/test_us3_policy_blend_fallback.py`
- [ ] T059 [P] [US3] Add reproducibility tests for fixed-seed repeated runs with identical controls/events in `tests/integration/test_us3_reproducibility.py`
- [ ] T060 [P] [US3] Add benchmark smoke test/report parsing checks for 100k scenario metrics in `tests/benchmarks/test_us3_benchmark_report.py`

### Implementation for User Story 3

- [ ] T061 [P] [US3] Implement adaptive policy plugin interface and registry in `src/metroflow/learning/plugins.py`
- [ ] T062 [P] [US3] Implement OD route candidate set state and refresh policy in `src/metroflow/routing/candidates.py`
- [ ] T063 [US3] Implement OD-UCB bandit policy state and online update logic in `src/metroflow/learning/od_ucb.py`
- [ ] T064 [US3] Implement routing decision mixer between dynamic potential baseline and adaptive plugin scores in `src/metroflow/routing/policy_mixer.py`
- [ ] T065 [US3] Implement simulator experience extraction for online learning updates in `src/metroflow/learning/experience.py`
- [ ] T066 [US3] Integrate OD-UCB scoring/updating and fallback telemetry into `src/metroflow/sim/step.py`
- [ ] T067 [US3] Extend run summary comparison outputs for baseline vs adaptive experiments in `src/metroflow/sim/run_summary.py`
- [ ] T068 [US3] Implement benchmark scenario runner and metric capture in `src/metroflow/benchmarks/run.py`
- [ ] T069 [US3] Add demo flags/config plumbing for baseline-only vs adaptive runs in `src/metroflow/demo.py`

**Checkpoint**: User Story 3 enables gradual simulator-only online route improvement with reproducible, benchmarkable comparisons and safe fallback behavior

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Cross-story hardening, documentation sync, and end-to-end validation

- [ ] T070 [P] Document architecture tradeoffs from this feature in `docs/ARCHITECTURE.md`
- [ ] T071 [P] Document benchmark targets/reporting conventions in `docs/PERFORMANCE_TARGETS.md`
- [ ] T072 Add end-to-end container smoke validation script for quickstart commands in `scripts/validate_adaptive_traffic_sim.sh`
- [ ] T073 [P] Add UI non-blocking stress test (slow consumer / frame drops) in `tests/benchmarks/test_ui_stream_non_blocking.py`
- [ ] T074 [P] Update developer runbook steps and command examples in `specs/001-adaptive-traffic-sim/quickstart.md`
- [ ] T075 Run and record feature validation results in `specs/001-adaptive-traffic-sim/checklists/requirements.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational completion - establishes MVP baseline simulation and UI observation flow
- **User Story 2 (Phase 4)**: Depends on User Story 1 baseline simulation flow and UI packets
- **User Story 3 (Phase 5)**: Depends on User Story 1 baseline routing/metrics; can start before all US2 polish is complete, but benchmark comparisons are most meaningful after US2 event metrics are available
- **Polish (Phase 6)**: Depends on all targeted user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: First executable increment and recommended MVP scope
- **User Story 2 (P2)**: Builds on US1 flow/routing/UI packet pipeline
- **User Story 3 (P3)**: Builds on US1 baseline routing and run summaries; benefits from US2 event scenarios for richer online-learning evaluation

### Within Each User Story

- Tests MUST be written and fail before implementation tasks for that story
- Simulation-impacting tasks MUST preserve/update invariant, boundary, and reproducibility coverage
- Data/state structures before engine integrations
- Core engine logic before UI/demo wiring
- Story checkpoint validation before starting next priority story

### Parallel Opportunities

- Setup file scaffolding tasks `T002`-`T005` can run in parallel after `T001`
- Foundational primitives `T008`, `T009`, `T011`, `T012`, `T014`, `T015`, `T016` can run in parallel after `T007`/`T010` interfaces are agreed
- US1 city/demand modules `T029`-`T031` can run in parallel; tests `T023`-`T027` can run in parallel
- US2 event/behavior modules `T048`, `T050` and tests `T042`-`T046` can run in parallel
- US3 contract/unit/integration tests `T056`-`T060` can run in parallel; plugin/candidate modules `T061`-`T062` can run in parallel
- Polish docs/tests `T070`, `T071`, `T073`, `T074` can run in parallel

---

## Parallel Example: User Story 1

```bash
# Write US1 tests in parallel
Task: "T023 in tests/unit/test_city_generation.py"
Task: "T024 in tests/unit/test_demand_schedules.py"
Task: "T025 in tests/integration/test_us1_baseline_simulation.py"
Task: "T027 in tests/contract/test_ui_topology_congestion_contract.py"

# Build US1 base modules in parallel
Task: "T029 in src/metroflow/city/generator.py"
Task: "T030 in src/metroflow/city/zones.py"
Task: "T031 in src/metroflow/demand/population.py"
```

---

## Parallel Example: User Story 2

```bash
# US2 tests in parallel
Task: "T042 in tests/unit/test_traffic_events.py"
Task: "T043 in tests/unit/test_behavior_profiles.py"
Task: "T046 in tests/contract/test_ui_event_control_contract.py"

# US2 module work in parallel
Task: "T048 in src/metroflow/flow/events.py"
Task: "T050 in src/metroflow/routing/behavior_profiles.py"
Task: "T053 in src/metroflow/ui/packets.py"
```

---

## Parallel Example: User Story 3

```bash
# US3 tests in parallel
Task: "T056 in tests/contract/test_policy_plugin_contract.py"
Task: "T057 in tests/unit/test_od_ucb_bandit.py"
Task: "T059 in tests/integration/test_us3_reproducibility.py"
Task: "T060 in tests/benchmarks/test_us3_benchmark_report.py"

# US3 implementation bootstrap in parallel
Task: "T061 in src/metroflow/learning/plugins.py"
Task: "T062 in src/metroflow/routing/candidates.py"
Task: "T068 in src/metroflow/benchmarks/run.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL)
3. Complete Phase 3: User Story 1
4. Validate baseline simulation, invariants, and day/time UI toggles
5. Demo the baseline virtual-city congestion behavior before adding disruptions or learning

### Incremental Delivery

1. Setup + Foundational -> stable simulation primitives and contracts
2. Add US1 -> baseline observable traffic simulation (MVP)
3. Add US2 -> disruption response + behavior diversity
4. Add US3 -> online adaptive learning + benchmarkable improvements
5. Polish -> architecture/performance docs and end-to-end validation scripts

### Parallel Team Strategy

1. Team completes Setup + Foundational interfaces together
2. During US1:
   - Developer A: city/zoning/demand generation modules
   - Developer B: flow/routing baseline modules
   - Developer C: UI packetization/streaming + contract tests
3. During US2/US3:
   - Split event/behavior work from learning/benchmark work after shared `sim/step.py` interfaces stabilize

---

## Notes

- All task execution and validation commands for Python/JAX MUST run through `./scripts/in_docker.sh`
- Do not claim performance improvements without benchmark/profile evidence recorded in benchmark outputs or review notes
- Keep diffs small and aligned to task IDs; update docs/contracts when interfaces change
- `check-prerequisites.sh` reported duplicate `001-*` spec prefixes (`001-metroflow`, `001-adaptive-traffic-sim`); continue using `specs/001-adaptive-traffic-sim/` for this feature's artifacts
