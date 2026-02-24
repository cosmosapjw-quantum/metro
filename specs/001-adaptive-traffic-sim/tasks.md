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

- [X] T001 Create package directories and `__init__.py` files in `src/metroflow/city/__init__.py`, `src/metroflow/demand/__init__.py`, `src/metroflow/flow/__init__.py`, `src/metroflow/routing/__init__.py`, `src/metroflow/learning/__init__.py`, `src/metroflow/sim/__init__.py`, `src/metroflow/ui/__init__.py`, and `src/metroflow/benchmarks/__init__.py`
- [X] T002 [P] Create test directory scaffolding files `tests/unit/__init__.py`, `tests/integration/__init__.py`, `tests/contract/__init__.py`, and `tests/benchmarks/__init__.py`
- [X] T003 [P] Add shared pytest fixtures skeleton in `tests/conftest.py`
- [X] T004 [P] Add feature test constants/seed registry in `tests/fixtures/simulation_scenarios.py`
- [X] T005 [P] Add benchmark report utility skeleton in `src/metroflow/benchmarks/reporting.py`
- [X] T006 Record implementation task checkpoints and validation command placeholders in `specs/001-adaptive-traffic-sim/quickstart.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared simulation primitives and contracts that MUST exist before any user story implementation

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T007 Implement configuration dataclasses and enums in `src/metroflow/sim/config.py`
- [X] T008 [P] Implement PRNG seed/key helper functions in `src/metroflow/sim/rng.py`
- [X] T009 [P] Implement simulation control/telemetry dataclasses in `src/metroflow/sim/control.py`
- [X] T010 Implement core simulation state containers (static + dynamic references) in `src/metroflow/sim/state.py`
- [X] T011 [P] Implement active-agent packed pool primitives in `src/metroflow/sim/active_agents.py`
- [X] T012 [P] Implement invariant validation/report structures in `src/metroflow/sim/invariants.py`
- [X] T013 Implement graph CSR/topology primitives and validation in `src/metroflow/city/graph.py`
- [X] T014 [P] Implement link/node flow state containers in `src/metroflow/flow/state.py`
- [X] T015 [P] Implement baseline/adaptive policy blend controller skeleton in `src/metroflow/learning/policy_blend.py`
- [X] T016 [P] Implement UI packet envelope and schema version helpers in `src/metroflow/ui/packets.py`
- [X] T017 Implement throttled UI snapshot emission buffer in `src/metroflow/ui/stream_buffer.py`
- [X] T018 Implement simulation step/init function skeletons matching `specs/001-adaptive-traffic-sim/contracts/simulation-step.md` in `src/metroflow/sim/step.py`
- [X] T019 [P] Add contract tests for simulation step signatures and telemetry keys in `tests/contract/test_simulation_step_contract.py`
- [X] T020 [P] Add contract tests for UI packet envelope/schema version behavior in `tests/contract/test_ui_packet_contract.py`
- [X] T021 [P] Add unit tests for active-agent pool consistency and free-slot reuse in `tests/unit/test_active_agent_pool.py`
- [X] T022 [P] Add unit tests for invariant validator core checks (conservation hooks, non-negative queue, capacity flags) in `tests/unit/test_invariants_core.py`

**Checkpoint**: Foundation ready - user story implementation can now proceed with stable state, contract, and validation primitives

---

## Phase 3: User Story 1 - 가상 도시 교통 관찰 (Priority: P1) 🎯 MVP

**Goal**: Generate a synthetic 100k-scale city with schedules/trips and visualize road network + congestion with day/time toggles at playable baseline behavior

**Independent Test**: Start a fixed-seed synthetic city scenario, run the baseline simulation, and confirm topology + congestion UI output plus day/time toggle effects appear without violating core invariants

### Tests for User Story 1

- [X] T023 [P] [US1] Add unit tests for city generation hierarchy/bridge/zoning constraints in `tests/unit/test_city_generation.py`
- [X] T024 [P] [US1] Add unit tests for citizen schedule templates and trip request generation by weekday/weekend + time bands in `tests/unit/test_demand_schedules.py`
- [X] T025 [P] [US1] Add integration tests for baseline simulation smoke with topology/congestion outputs in `tests/integration/test_us1_baseline_simulation.py`
- [X] T026 [P] [US1] Add boundary-condition tests for day-type and time-band toggles on in-flight vs future trips in `tests/integration/test_us1_day_time_transitions.py`
- [X] T027 [P] [US1] Add contract tests for `ui.topology_snapshot`, `ui.congestion_frame`, and `ui.metrics_summary` packets in `tests/contract/test_ui_topology_congestion_contract.py`
- [X] T028 [US1] Add invariant regression test covering conservation/non-negative queues/capacity detection during baseline run in `tests/integration/test_us1_invariants.py`

### Implementation for User Story 1

- [X] T029 [P] [US1] Implement synthetic city topology generator (hierarchy, barrier, bridges, ramps/intersections) in `src/metroflow/city/generator.py`
- [X] T030 [P] [US1] Implement zoning and POI placement generation in `src/metroflow/city/zones.py`
- [X] T031 [P] [US1] Implement citizen population, behavior profiles, and schedule templates in `src/metroflow/demand/population.py`
- [X] T032 [US1] Implement trip request generation/activation pipeline in `src/metroflow/demand/trips.py`
- [X] T033 [US1] Implement link-queue + node model baseline flow updates in `src/metroflow/flow/engine.py`
- [X] T034 [US1] Implement congestion-aware dynamic-potential baseline routing in `src/metroflow/routing/dynamic_potential.py`
- [X] T035 [US1] Implement simulation initialization builder wiring city/demand/flow/routing state in `src/metroflow/sim/init.py`
- [X] T036 [US1] Implement baseline tick orchestration (spawn, route, advance, complete, validate invariants) in `src/metroflow/sim/step.py`
- [X] T037 [US1] Implement UI snapshot source builder for topology/congestion/metrics in `src/metroflow/ui/snapshots.py`
- [X] T038 [US1] Implement UI control handling for day-type/time-band toggles and snapshot requests in `src/metroflow/ui/control_adapter.py`
- [X] T039 [US1] Implement minimal stream server for navigator-style map packets in `src/metroflow/ui/stream_server.py`
- [X] T040 [US1] Integrate baseline scenario run and UI stream options into demo entrypoint `src/metroflow/demo.py`
- [X] T041 [US1] Implement baseline run summary aggregation (trip totals, hotspot metrics) in `src/metroflow/sim/run_summary.py`

**Checkpoint**: User Story 1 provides a playable baseline virtual-city traffic simulation with observable congestion and day/time toggles

---

## Phase 4: User Story 2 - 이벤트 대응과 행동 다양성 관찰 (Priority: P2)

**Goal**: Add accident/construction/congestion events and heterogeneous route behavior so disruptions cause rerouting, persistence, and visible network redistribution

**Independent Test**: Inject a bridge/arterial disruption in a fixed-seed peak scenario and verify mixed traveler responses plus UI-visible congestion redistribution without crashes or invariant regressions

### Tests for User Story 2

- [X] T042 [P] [US2] Add unit tests for traffic event scheduling/activation/clearing in `tests/unit/test_traffic_events.py`
- [X] T043 [P] [US2] Add unit tests for route-choice profile diversity sampling and persistence/reroute thresholds in `tests/unit/test_behavior_profiles.py`
- [X] T044 [P] [US2] Add integration tests for blocked-edge/bridge event rerouting and recorded failures in `tests/integration/test_us2_disruption_rerouting.py`
- [X] T045 [P] [US2] Add integration tests for congestion redistribution after incidents in `tests/integration/test_us2_congestion_redistribution.py`
- [X] T046 [P] [US2] Add contract tests for `ui.event_overlay`, `ui.control_command`, and `ui.control_ack` packets in `tests/contract/test_ui_event_control_contract.py`
- [X] T047 [US2] Add boundary/invariant regression tests for disruption scenarios (blocked edges + time transitions) in `tests/integration/test_us2_boundary_invariants.py`

### Implementation for User Story 2

- [X] T048 [P] [US2] Implement traffic event models and scheduler state transitions in `src/metroflow/flow/events.py`
- [X] T049 [US2] Implement event effects on link capacities/closures in `src/metroflow/flow/event_effects.py`
- [X] T050 [P] [US2] Implement route-choice behavior profile generation and diversity sampling in `src/metroflow/routing/behavior_profiles.py`
- [X] T051 [US2] Implement disruption-aware reroute trigger logic (reroute vs persist) in `src/metroflow/routing/reroute_policy.py`
- [X] T052 [US2] Integrate traffic events and behavior diversity into tick orchestration in `src/metroflow/sim/step.py`
- [X] T053 [US2] Implement event overlay packet generation and command acknowledgements in `src/metroflow/ui/packets.py`
- [X] T054 [US2] Implement disruption scenario presets for demos in `src/metroflow/ui/scenario_controls.py`
- [X] T055 [US2] Extend run summary with disruption response metrics (reroute share, persistence share, corridor shifts) in `src/metroflow/sim/run_summary.py`

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

## Phase 7: Extension Design Sync (100k Realism + Transit/Metro)

**Purpose**: Add extension-specific documentation/contracts before implementation while preserving baseline road-only task flow and acceptance boundaries

**⚠️ CRITICAL**: Extension implementation phases (Phase 8+) SHOULD NOT begin until extension docs/contracts in this phase are updated

- [ ] T076 Update extension phase sequencing and separate road-only vs multimodal benchmark plan notes in `specs/001-adaptive-traffic-sim/plan.md`; 완료 조건: `bash scripts/in_docker.sh pytest -q tests/unit/test_city_generation.py` (baseline no-regression smoke)
- [ ] T077 [P] Update transit/metro realism entities (station, line, transfer, access connector, station summary) and realism metric/report entities in `specs/001-adaptive-traffic-sim/data-model.md`; 완료 조건: `bash scripts/in_docker.sh pytest -q tests/unit/test_city_generation.py`
- [ ] T078 [P] Update transit UI overlay / station congestion / phase-gated packet schemas in `specs/001-adaptive-traffic-sim/contracts/ui-data-packets.md`; 완료 조건: `bash scripts/in_docker.sh pytest -q tests/contract/test_ui_packet_contract.py`
- [ ] T079 [P] Add transit network generation contract (stations/lines/headway/transfer metadata) in `specs/001-adaptive-traffic-sim/contracts/transit-network.md`; 완료 조건: `bash scripts/in_docker.sh pytest -q tests/contract/test_transit_network_contract.py`
- [ ] T080 [P] Add multimodal routing candidate comparison contract (road vs transit alternatives, walk proxy fields) in `specs/001-adaptive-traffic-sim/contracts/multimodal-routing.md`; 완료 조건: `bash scripts/in_docker.sh pytest -q tests/contract/test_multimodal_routing_contract.py`
- [ ] T081 [P] Record realism/transit validation and benchmark commands (road-only vs multimodal separated) in `specs/001-adaptive-traffic-sim/quickstart.md`; 완료 조건: `bash scripts/in_docker.sh python -m metroflow.demo`
- [ ] T082 [P] Document extension tradeoffs for topology realism metrics and transit MVP phase-gating in `specs/001-adaptive-traffic-sim/research.md`; 완료 조건: `bash scripts/in_docker.sh pytest -q tests/unit/test_city_generation.py`

**Checkpoint**: Extension docs/contracts are explicit enough to drive TDD for realism metrics and transit/multimodal features

---

## Phase 8: User Story 1 Extension - 100k Synthetic City Realism Metrics & Scaling (Priority: P1 Extension)

**Goal**: Improve the synthetic road-city generator for 100k realism (resolution, OD diversity, morphology non-uniformity, bridge chokepoint criticality) without introducing transit runtime behavior yet

**Independent Test**: Generate fixed-seed ~100k synthetic city scenarios and verify topology/zoning/POI thresholds plus bridge closure criticality and morphology metrics pass reported realism thresholds while baseline road-only demo still runs

### Tests for User Story 1 Extension (Realism) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T083 [P] [US1] Add topology realism metrics threshold tests (node/link/zone/POI counts, morphology summaries) in `tests/unit/test_city_realism_metrics.py`; 완료 조건: `bash scripts/in_docker.sh pytest -q tests/unit/test_city_realism_metrics.py`
- [ ] T084 [P] [US1] Add zoning/POI scaling tests tied to `population_target` and density tiers in `tests/unit/test_city_zoning_scaling.py`; 완료 조건: `bash scripts/in_docker.sh pytest -q tests/unit/test_city_zoning_scaling.py`
- [ ] T085 [P] [US1] Add bridge/barrier structural chokepoint closure sensitivity integration tests in `tests/integration/test_us1_bridge_chokepoint_realism.py`; 완료 조건: `bash scripts/in_docker.sh pytest -q tests/integration/test_us1_bridge_chokepoint_realism.py`
- [ ] T086 [P] [US1] Add contract/report schema tests for machine-readable realism metrics summaries in `tests/contract/test_city_realism_metrics_contract.py`; 완료 조건: `bash scripts/in_docker.sh pytest -q tests/contract/test_city_realism_metrics_contract.py`

### Implementation for User Story 1 Extension (Realism)

- [ ] T087 [P] [US1] Implement synthetic city realism metric computation/report helpers in `src/metroflow/city/realism_metrics.py`; 완료 조건: `bash scripts/in_docker.sh pytest -q tests/unit/test_city_realism_metrics.py`
- [ ] T088 [US1] Implement road generator morphology non-uniformity controls and bridge criticality tuning hooks in `src/metroflow/city/generator.py`; 완료 조건: `bash scripts/in_docker.sh pytest -q tests/unit/test_city_realism_metrics.py tests/integration/test_us1_bridge_chokepoint_realism.py`
- [ ] T089 [US1] Implement zoning/POI scaling and multi-zone-per-type realism generation updates in `src/metroflow/city/zones.py`; 완료 조건: `bash scripts/in_docker.sh pytest -q tests/unit/test_city_zoning_scaling.py tests/unit/test_city_generation.py`
- [ ] T090 [US1] Integrate realism metrics and thresholds into baseline run summaries in `src/metroflow/sim/run_summary.py`; 완료 조건: `bash scripts/in_docker.sh pytest -q tests/contract/test_city_realism_metrics_contract.py`
- [ ] T091 [US1] Add realism validation scenario presets and smoke hooks in `tests/fixtures/simulation_scenarios.py` and `src/metroflow/demo.py`; 완료 조건: `bash scripts/in_docker.sh python -m metroflow.demo`

**Checkpoint**: Baseline road-only path remains intact while the generator emits measurable ~100k realism metrics and stronger bridge chokepoint behavior

---

## Phase 9: User Story 4 - Transit Network Data Model, Generation, and Static Wiring (Priority: P2)

**Goal**: Introduce synthetic transit/metro network entities (stations, lines, headways, transfer nodes) and generation/wiring without yet modeling full passenger flow behavior

**Independent Test**: In a fixed-seed ~100k scenario, the system generates a transit network with station/line/headway data and transfer-capable nodes, validates contracts, and initializes simulation state without breaking road-only mode

### Tests for User Story 4 (Transit Network) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T092 [P] [US4] Add contract tests for transit network generation schema and required fields in `tests/contract/test_transit_network_contract.py`; 완료 조건: `bash scripts/in_docker.sh pytest -q tests/contract/test_transit_network_contract.py`
- [ ] T093 [P] [US4] Add unit tests for synthetic station/line/headway/transfer node generation in `tests/unit/test_transit_network_generation.py`; 완료 조건: `bash scripts/in_docker.sh pytest -q tests/unit/test_transit_network_generation.py`
- [ ] T094 [P] [US4] Add integration tests for city + transit static initialization and road-only compatibility in `tests/integration/test_us4_transit_network_generation.py`; 완료 조건: `bash scripts/in_docker.sh pytest -q tests/integration/test_us4_transit_network_generation.py`

### Implementation for User Story 4 (Transit Network)

- [ ] T095 [P] [US4] Create transit package scaffolding and exports in `src/metroflow/transit/__init__.py`; 완료 조건: `bash scripts/in_docker.sh pytest -q tests/contract/test_transit_network_contract.py`
- [ ] T096 [P] [US4] Implement transit static entities/dataclasses (station, line, transfer, headway) in `src/metroflow/transit/model.py`; 완료 조건: `bash scripts/in_docker.sh pytest -q tests/unit/test_transit_network_generation.py`
- [ ] T097 [US4] Implement synthetic transit network/station/line generator in `src/metroflow/transit/generator.py`; 완료 조건: `bash scripts/in_docker.sh pytest -q tests/unit/test_transit_network_generation.py tests/integration/test_us4_transit_network_generation.py`
- [ ] T098 [US4] Wire transit static state into simulation init/state while preserving road-only mode in `src/metroflow/sim/state.py` and `src/metroflow/sim/init.py`; 완료 조건: `bash scripts/in_docker.sh pytest -q tests/integration/test_us4_transit_network_generation.py`

**Checkpoint**: Transit network objects can be generated and initialized with contract coverage, and road-only runs remain valid when transit is disabled

---

## Phase 10: User Story 4 - Passenger Access/Boarding/Alighting/Transfer Baseline (Priority: P2)

**Goal**: Add baseline passenger access proxy and station passenger flow behaviors (boarding, alighting, waiting, transfer) for the transit/metro realism MVP

**Independent Test**: In a multimodal-enabled scenario, passenger trips can access stations via walk proxy, traverse line segments, and produce observable boarding/alighting/waiting/transfer summaries without breaking baseline invariants

### Tests for User Story 4 (Passenger Flow) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T099 [P] [US4] Add unit tests for walk access/egress proxy connectors and access-time calculations in `tests/unit/test_transit_access.py`; 완료 조건: `bash scripts/in_docker.sh pytest -q tests/unit/test_transit_access.py`
- [ ] T100 [P] [US4] Add unit tests for passenger boarding/alighting/waiting/transfer state transitions in `tests/unit/test_transit_passenger_flow.py`; 완료 조건: `bash scripts/in_docker.sh pytest -q tests/unit/test_transit_passenger_flow.py`
- [ ] T101 [P] [US4] Add integration tests for passenger access + boarding/alighting/transfer baseline flow in `tests/integration/test_us4_passenger_transfer_flow.py`; 완료 조건: `bash scripts/in_docker.sh pytest -q tests/integration/test_us4_passenger_transfer_flow.py`

### Implementation for User Story 4 (Passenger Flow)

- [ ] T102 [P] [US4] Implement walk access/egress proxy connectors and transfer penalties in `src/metroflow/transit/access.py`; 완료 조건: `bash scripts/in_docker.sh pytest -q tests/unit/test_transit_access.py`
- [ ] T103 [P] [US4] Implement station passenger flow engine for boarding/alighting/waiting/transfer summaries in `src/metroflow/transit/passenger_flow.py`; 완료 조건: `bash scripts/in_docker.sh pytest -q tests/unit/test_transit_passenger_flow.py`
- [ ] T104 [US4] Integrate transit passenger flow and summary updates into tick orchestration in `src/metroflow/sim/step.py`; 완료 조건: `bash scripts/in_docker.sh pytest -q tests/integration/test_us4_passenger_transfer_flow.py`

**Checkpoint**: Transit/metro MVP passenger behaviors are observable at station-summary level with walk proxy access and no road-only regression

---

## Phase 11: User Story 4 - Multimodal Routing Candidates and Transit UI Overlay (Priority: P2)

**Goal**: Add road-vs-transit candidate comparison, transit UI overlay packet/schema support, and station congestion summaries for phase-gated transit observability

**Independent Test**: In a standard ~100k multimodal validation scenario, the system emits transit overlay packets/summaries and compares road-only vs transit alternatives without requiring in-trip mixed-mode substitutions

### Tests for User Story 4 (Multimodal Routing + UI Overlay) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T105 [P] [US4] Add contract tests for transit overlay packets and station congestion summaries in `tests/contract/test_ui_transit_packet_contract.py`; 완료 조건: `bash scripts/in_docker.sh pytest -q tests/contract/test_ui_transit_packet_contract.py`
- [ ] T106 [P] [US4] Add integration tests for multimodal routing candidate comparison (road vs transit + walk proxy) in `tests/integration/test_us4_multimodal_routing_candidates.py`; 완료 조건: `bash scripts/in_docker.sh pytest -q tests/integration/test_us4_multimodal_routing_candidates.py`
- [ ] T107 [P] [US4] Add integration tests for transit overlay packet emission and phase-gated UI summaries in `tests/integration/test_us4_ui_transit_overlay.py`; 완료 조건: `bash scripts/in_docker.sh pytest -q tests/integration/test_us4_ui_transit_overlay.py`

### Implementation for User Story 4 (Multimodal Routing + UI Overlay)

- [ ] T108 [P] [US4] Implement multimodal route candidate generation/comparison helpers in `src/metroflow/routing/multimodal_candidates.py`; 완료 조건: `bash scripts/in_docker.sh pytest -q tests/integration/test_us4_multimodal_routing_candidates.py`
- [ ] T109 [US4] Integrate road-vs-transit candidate comparison into routing decision pipeline in `src/metroflow/routing/policy_mixer.py` and `src/metroflow/routing/candidates.py`; 완료 조건: `bash scripts/in_docker.sh pytest -q tests/integration/test_us4_multimodal_routing_candidates.py`
- [ ] T110 [P] [US4] Implement transit overlay packet/schema support in `src/metroflow/ui/packets.py`; 완료 조건: `bash scripts/in_docker.sh pytest -q tests/contract/test_ui_transit_packet_contract.py`
- [ ] T111 [US4] Implement transit line/station snapshot and station congestion summary packet builders in `src/metroflow/ui/snapshots.py`; 완료 조건: `bash scripts/in_docker.sh pytest -q tests/integration/test_us4_ui_transit_overlay.py`
- [ ] T112 [US4] Add transit overlay demo/control wiring and multimodal smoke path in `src/metroflow/demo.py`; 완료 조건: `bash scripts/in_docker.sh python -m metroflow.demo`

**Checkpoint**: Multimodal candidate comparison and transit UI overlay summaries are observable with contract coverage and phase-gated behavior

---

## Phase 12: Extension Benchmarks & Reporting (Road-Only vs Multimodal Split)

**Purpose**: Add separated benchmark/report tasks for road-only realism baseline and multimodal transit extension performance and comparability

- [ ] T113 [P] Add road-only realism benchmark smoke/report tests in `tests/benchmarks/test_road_only_realism_benchmark.py`; 완료 조건: `bash scripts/in_docker.sh pytest -q tests/benchmarks/test_road_only_realism_benchmark.py`
- [ ] T114 [P] Add multimodal transit benchmark smoke/report tests in `tests/benchmarks/test_multimodal_transit_benchmark.py`; 완료 조건: `bash scripts/in_docker.sh pytest -q tests/benchmarks/test_multimodal_transit_benchmark.py`
- [ ] T115 Implement split benchmark scenario runner/report outputs for road-only vs multimodal in `src/metroflow/benchmarks/run.py` and `src/metroflow/benchmarks/reporting.py`; 완료 조건: `bash scripts/in_docker.sh pytest -q tests/benchmarks/test_road_only_realism_benchmark.py tests/benchmarks/test_multimodal_transit_benchmark.py`
- [ ] T116 Update benchmark command examples and reporting checklist for split road-only/multimodal performance runs in `specs/001-adaptive-traffic-sim/quickstart.md` and `docs/PERFORMANCE_TARGETS.md`; 완료 조건: `bash scripts/in_docker.sh python -m metroflow.demo` + `bash scripts/in_docker.sh pytest -q tests/benchmarks/test_us3_benchmark_report.py`
- [ ] T117 Run and record separated road-only and multimodal performance smoke results in `specs/001-adaptive-traffic-sim/checklists/requirements.md`; 완료 조건: `bash scripts/in_docker.sh pytest -q` + road-only performance smoke (`bash scripts/in_docker.sh python -m metroflow.demo --scenario standard_100k --mode road-only`) + multimodal performance smoke (`bash scripts/in_docker.sh python -m metroflow.demo --scenario standard_100k --mode multimodal`)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational completion - establishes MVP baseline simulation and UI observation flow
- **User Story 2 (Phase 4)**: Depends on User Story 1 baseline simulation flow and UI packets
- **User Story 3 (Phase 5)**: Depends on User Story 1 baseline routing/metrics; can start before all US2 polish is complete, but benchmark comparisons are most meaningful after US2 event metrics are available
- **Baseline Polish (Phase 6)**: Depends on baseline user stories (US1-US3) being complete
- **Extension Design Sync (Phase 7)**: Can start after spec updates exist; SHOULD complete before extension implementation phases
- **US1 Realism Extension (Phase 8)**: Depends on Phase 7 docs/contracts and baseline US1 city/zoning/run-summary modules
- **US4 Transit Network (Phase 9)**: Depends on Phase 7 docs/contracts and baseline Foundational + US1 init/state wiring
- **US4 Passenger Flow (Phase 10)**: Depends on Phase 9 transit network generation/wiring
- **US4 Multimodal + UI Overlay (Phase 11)**: Depends on Phase 10 passenger flow and UI packet/schema contracts from Phase 7
- **Extension Benchmarks (Phase 12)**: Depends on targeted extension phases (Phase 8 and/or Phase 11) and benchmark runner/report plumbing

### User Story Dependencies

- **User Story 1 (P1)**: First executable increment and recommended MVP scope
- **User Story 1 Extension (Phase 8, [US1])**: Builds on baseline US1 city generation and adds realism metrics/scaling without requiring transit runtime behavior
- **User Story 2 (P2)**: Builds on US1 flow/routing/UI packet pipeline
- **User Story 3 (P3)**: Builds on US1 baseline routing and run summaries; benefits from US2 event scenarios for richer online-learning evaluation
- **User Story 4 (P2)**: Builds on Foundational + baseline US1 init/UI flow; transit network (Phase 9) -> passenger flow (Phase 10) -> multimodal/UI overlay (Phase 11)

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
- Extension design docs/contracts `T077`-`T082` can run in parallel after `T076`
- US1 realism tests `T083`-`T086` can run in parallel; realism generator/zoning work `T087`-`T089` can partially run in parallel
- US4 transit network tests `T092`-`T094` can run in parallel; transit entities/generator tasks `T095`-`T097` can run in parallel before wiring `T098`
- US4 passenger flow tests `T099`-`T101` can run in parallel; access and passenger engine work `T102`-`T103` can run in parallel before `T104`
- US4 multimodal/UI tests `T105`-`T107` can run in parallel; routing/UI implementation `T108`, `T110` can run in parallel before integration tasks `T109`, `T111`, `T112`
- Split benchmark tests `T113`-`T114` can run in parallel before report integration `T115`

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

## Parallel Example: User Story 1 Extension (Realism)

```bash
# US1 realism tests in parallel
Task: "T083 in tests/unit/test_city_realism_metrics.py"
Task: "T084 in tests/unit/test_city_zoning_scaling.py"
Task: "T085 in tests/integration/test_us1_bridge_chokepoint_realism.py"
Task: "T086 in tests/contract/test_city_realism_metrics_contract.py"

# US1 realism implementation bootstrap in parallel
Task: "T087 in src/metroflow/city/realism_metrics.py"
Task: "T088 in src/metroflow/city/generator.py"
Task: "T089 in src/metroflow/city/zones.py"
```

---

## Parallel Example: User Story 4

```bash
# US4 transit network tests in parallel
Task: "T092 in tests/contract/test_transit_network_contract.py"
Task: "T093 in tests/unit/test_transit_network_generation.py"
Task: "T094 in tests/integration/test_us4_transit_network_generation.py"

# US4 multimodal/UI contract + implementation bootstrap in parallel
Task: "T105 in tests/contract/test_ui_transit_packet_contract.py"
Task: "T108 in src/metroflow/routing/multimodal_candidates.py"
Task: "T110 in src/metroflow/ui/packets.py"
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
5. Baseline Polish (Phase 6) -> freeze/validate road-only MVP flow before extension
6. Extension Design Sync (Phase 7) -> docs/contracts for realism + transit/multimodal
7. Add US1 realism extension (Phase 8) -> measurable 100k synthetic city realism without transit runtime
8. Add US4 transit network + passenger flow + multimodal UI overlay (Phases 9-11)
9. Run split benchmarks/reporting (Phase 12) -> road-only vs multimodal performance evidence

### Parallel Team Strategy

1. Team completes Setup + Foundational interfaces together
2. During US1:
   - Developer A: city/zoning/demand generation modules
   - Developer B: flow/routing baseline modules
   - Developer C: UI packetization/streaming + contract tests
3. During US2/US3:
   - Split event/behavior work from learning/benchmark work after shared `sim/step.py` interfaces stabilize
4. During extension phases:
   - Developer A: realism metrics + generator/zoning scaling (Phase 8)
   - Developer B: transit network/passenger flow (Phases 9-10)
   - Developer C: multimodal routing + UI transit overlay contracts/packets (Phase 11)
   - Developer D (optional): split benchmark/report automation (Phase 12)

---

## Notes

- All task execution and validation commands for Python/JAX MUST run through `./scripts/in_docker.sh`
- Do not claim performance improvements without benchmark/profile evidence recorded in benchmark outputs or review notes
- Keep diffs small and aligned to task IDs; update docs/contracts when interfaces change
- Extension tasks `T076+` preserve baseline task numbering/flow and split road-generator realism work (Phase 8) from transit feature introduction (Phases 9-11)
