# Tasks: Adaptive Traffic Simulation (Map-Realism-First Execution)

**Input**: Design documents from `/home/cosmosapjw/metro/specs/001-adaptive-traffic-sim/`  
**Prerequisites**: `/home/cosmosapjw/metro/specs/001-adaptive-traffic-sim/plan.md`, `/home/cosmosapjw/metro/specs/001-adaptive-traffic-sim/spec.md`, `/home/cosmosapjw/metro/specs/001-adaptive-traffic-sim/research.md`, `/home/cosmosapjw/metro/specs/001-adaptive-traffic-sim/data-model.md`, `/home/cosmosapjw/metro/specs/001-adaptive-traffic-sim/contracts/`

**Tests**: Tests are required by spec acceptance criteria and constitution gates.  
**Organization**: Tasks are grouped by user story and sequenced to enforce dual-gate delivery (documentation reconciliation + map-realism-first).

## Execution Protocol (Applies to Every Task)

For every `Txxx`, execution MUST follow this automation prompt shape:

```text
tasks.md의 [T-XXX]를 구현해줘. 먼저 관련 문서(계획/데이터모델)에서 근거 위치를 인용(파일 경로+섹션 제목)하고,
그 다음 최소 diff로 구현해. 마지막에 pytest와 데모 스모크를 돌린 로그 요약까지 줘.
리뷰: 방금 diff를 /review로 검토해줘. (1) 불변량 위반 가능성 (2) 성능 병목 (3) JAX jit 가능성 관점 우선순위 큐.
```

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Lock execution conventions and baseline tooling references before implementation.

- [ ] T001 Establish per-task execution protocol checklist in `/home/cosmosapjw/metro/specs/001-adaptive-traffic-sim/checklists/task-execution-protocol.md`
- [ ] T002 [P] Add task evidence log template (doc citations, smoke summary, review queue) in `/home/cosmosapjw/metro/specs/001-adaptive-traffic-sim/checklists/task-evidence-template.md`
- [ ] T003 [P] Add automation prompt snippets for `Txxx` execution in `/home/cosmosapjw/metro/docs/prompts/task-runner-prompts.md`

- [ ] T004 Align `map-realism-first` workflow notes in `/home/cosmosapjw/metro/specs/001-adaptive-traffic-sim/quickstart.md`
- [ ] T005 [P] Register `map_realism`/`sim_expansion` pytest markers in `/home/cosmosapjw/metro/tests/conftest.py`
- [ ] T006 [P] Add task-run artifact directory guidance in `/home/cosmosapjw/metro/artifacts/README.md`
- [ ] T007 Add command wrappers for per-task smoke/review workflow in `/home/cosmosapjw/metro/scripts/validate_adaptive_traffic_sim.sh`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build global gates that block all story work until map realism readiness is measurable.

**⚠️ CRITICAL**: No user story implementation starts until this phase is complete.

- [ ] T008 Add SC-020..SC-042 realism gate evaluation entrypoint in `/home/cosmosapjw/metro/src/metroflow/city/realism_metrics.py`
- [ ] T009 Add map-foundation gate status fields to run summary in `/home/cosmosapjw/metro/src/metroflow/sim/run_summary.py`
- [ ] T010 [P] Add benchmark report fields for map gate pass/fail in `/home/cosmosapjw/metro/src/metroflow/benchmarks/reporting.py`
- [ ] T011 [P] Add fixed-seed map gate contract test in `/home/cosmosapjw/metro/tests/contract/test_city_realism_metrics_contract.py`
- [ ] T012 [P] Add deterministic map export smoke gate in `/home/cosmosapjw/metro/tests/smoke/test_city_map_png_export.py`
- [ ] T013 Add scenario preset metadata for realism gate execution in `/home/cosmosapjw/metro/src/metroflow/sim/scenario_presets.py`
- [ ] T014 Add map-first sequencing assertion test (SC-042) in `/home/cosmosapjw/metro/tests/integration/test_us1_bridge_chokepoint_realism.py`

**Checkpoint**: Map-realism global gates exist and are enforceable.

---

## Phase 3: User Story 1 - 가상 도시 교통 관찰 (Priority: P1) 🎯 MVP

**Goal**: Deliver realistic, deterministic synthetic map foundation and baseline observation behavior.

**Independent Test**: Generate fixed-seed `synthetic_100k` map and baseline run; verify map realism gates + day/time observation behavior pass independently.

### Tests for User Story 1

- [ ] T015 [P] [US1] Add unit test for morphology family distribution and share cap in `/home/cosmosapjw/metro/tests/unit/test_city_realism_morphology_metrics.py`
- [ ] T016 [P] [US1] Add unit test for hybrid zone/POI generation policy in `/home/cosmosapjw/metro/tests/unit/test_city_zoning_scaling.py`
- [ ] T017 [P] [US1] Add unit test for deterministic map rendering core signal preservation in `/home/cosmosapjw/metro/tests/unit/test_render_city_map.py`
- [ ] T018 [P] [US1] Add integration test for baseline map/congestion observation in `/home/cosmosapjw/metro/tests/integration/test_us1_baseline_simulation.py`
- [ ] T019 [P] [US1] Add integration test for weekday/weekend + time-band transitions in `/home/cosmosapjw/metro/tests/integration/test_us1_day_time_transitions.py`
- [ ] T020 [P] [US1] Add integration invariants test for conservation/non-negative queue/capacity in `/home/cosmosapjw/metro/tests/integration/test_us1_invariants.py`

### Implementation for User Story 1

- [ ] T021 [US1] Implement topology realism uplift and deterministic morphology controls in `/home/cosmosapjw/metro/src/metroflow/city/generator.py`
- [ ] T022 [US1] Implement hybrid zone/POI placement and district archetype metadata in `/home/cosmosapjw/metro/src/metroflow/city/zones.py`
- [ ] T023 [US1] Implement core visual-signal-preserving deterministic renderer behavior in `/home/cosmosapjw/metro/src/metroflow/tools/render_city_map.py`
- [ ] T024 [US1] Integrate map realism gate outputs into benchmark execution in `/home/cosmosapjw/metro/src/metroflow/benchmarks/run.py`
- [ ] T025 [US1] Integrate map-realism-first gate metadata into init/runtime state in `/home/cosmosapjw/metro/src/metroflow/sim/init.py`
- [ ] T026 [US1] Expose baseline map realism observability in UI snapshot payloads in `/home/cosmosapjw/metro/src/metroflow/ui/stream_server.py`
- [ ] T027 [US1] Wire US1 acceptance summary output in demo CLI path in `/home/cosmosapjw/metro/src/metroflow/demo.py`

**Checkpoint**: US1 map realism + baseline observation are independently functional and gate simulator expansion.

---

## Phase 4: User Story 2 - 이벤트 대응과 행동 다양성 관찰 (Priority: P2)

**Goal**: Validate disruption responses and reroute diversity on top of stabilized map realism foundation.

**Independent Test**: Apply disruption scenarios and verify mixed rerouting + congestion redistribution with invariants intact.

### Tests for User Story 2

- [ ] T028 [P] [US2] Add integration test for disruption rerouting diversity in `/home/cosmosapjw/metro/tests/integration/test_us2_disruption_rerouting.py`
- [ ] T029 [P] [US2] Add integration test for congestion redistribution around closures in `/home/cosmosapjw/metro/tests/integration/test_us2_congestion_redistribution.py`
- [ ] T030 [P] [US2] Add integration test for disruption boundary invariants in `/home/cosmosapjw/metro/tests/integration/test_us2_boundary_invariants.py`
- [ ] T031 [P] [US2] Add contract test for event-control packet behavior in `/home/cosmosapjw/metro/tests/contract/test_ui_event_control_contract.py`

### Implementation for User Story 2

- [ ] T032 [US2] Implement disruption lifecycle scheduling in `/home/cosmosapjw/metro/src/metroflow/flow/events.py`
- [ ] T033 [US2] Implement link/node disruption effects and closure propagation in `/home/cosmosapjw/metro/src/metroflow/flow/event_effects.py`
- [ ] T034 [US2] Implement behavior-diverse reroute decision tuning in `/home/cosmosapjw/metro/src/metroflow/routing/reroute_policy.py`
- [ ] T035 [US2] Integrate disruption outcome accounting into step/run summary in `/home/cosmosapjw/metro/src/metroflow/sim/step.py`

**Checkpoint**: US2 disruption realism is independently testable on map-realism-stable baseline.

---

## Phase 5: User Story 4 - 대중교통/메트로 확장 관측과 비교 검증 (Priority: P2)

**Goal**: Add phase-gated transit observability and road-vs-transit comparison without regressing road-only baseline.
This story phase corresponds to the transit static-wiring scope referenced as
`Phase 9` in external contracts/data-model artifacts.

**Independent Test**: Run road-only and transit-enabled scenarios on same seed and verify separate observability/summary outputs.

### Tests for User Story 4

- [ ] T036 [P] [US4] Add contract test for transit static artifact integrity in `/home/cosmosapjw/metro/tests/contract/test_transit_network_contract.py`
- [ ] T037 [P] [US4] Add contract test for transit overlay/station summary packets in `/home/cosmosapjw/metro/tests/contract/test_ui_packet_contract.py`
- [ ] T038 [P] [US4] Add integration test for transit generation + road-only compatibility in `/home/cosmosapjw/metro/tests/integration/test_us4_transit_network_generation.py`
- [ ] T039 [P] [US4] Add benchmark test for multimodal report split and thresholds in `/home/cosmosapjw/metro/tests/benchmarks/test_us3_benchmark_report.py`

### Implementation for User Story 4

- [ ] T040 [US4] Implement transit static network generation refinements in `/home/cosmosapjw/metro/src/metroflow/transit/generator.py`
- [ ] T041 [US4] Implement transit artifact schema/validation updates in `/home/cosmosapjw/metro/src/metroflow/transit/model.py`
- [ ] T042 [US4] Implement multimodal candidate comparison integration in `/home/cosmosapjw/metro/src/metroflow/routing/candidates.py`
- [ ] T043 [US4] Implement transit observability summaries in `/home/cosmosapjw/metro/src/metroflow/sim/run_summary.py`
- [ ] T044 [US4] Implement phase-gated transit packet emission wiring in `/home/cosmosapjw/metro/src/metroflow/ui/packets.py`

**Checkpoint**: US4 transit observability works independently and preserves baseline fallback.

---

## Phase 6: User Story 3 - 시뮬레이터 경험 기반 경로 개선 (Priority: P3)

**Goal**: Deliver stable simulator-internal online learning improvements with deterministic fallback-safe behavior.

**Independent Test**: Compare repeated runs with learning on/off and verify no regression in completion while travel metrics improve.

### Tests for User Story 3

- [ ] T045 [P] [US3] Add unit tests for OD-UCB update stability in `/home/cosmosapjw/metro/tests/unit/test_od_ucb_bandit.py`
- [ ] T046 [P] [US3] Add unit tests for policy mix fallback guardrails in `/home/cosmosapjw/metro/tests/unit/test_routing_policy_mixer.py`
- [ ] T047 [P] [US3] Add integration test for learning fallback behavior in `/home/cosmosapjw/metro/tests/integration/test_us3_policy_blend_fallback.py`
- [ ] T048 [P] [US3] Add integration reproducibility test for learning mode in `/home/cosmosapjw/metro/tests/integration/test_us3_reproducibility.py`

### Implementation for User Story 3

- [ ] T049 [US3] Implement simulator-only experience capture updates in `/home/cosmosapjw/metro/src/metroflow/learning/experience.py`
- [ ] T050 [US3] Implement OD-UCB update and bounded exploration behavior in `/home/cosmosapjw/metro/src/metroflow/learning/od_ucb.py`
- [ ] T051 [US3] Implement gradual baseline/adaptive mixing policy in `/home/cosmosapjw/metro/src/metroflow/learning/policy_blend.py`
- [ ] T052 [US3] Integrate adaptive update loop into simulation step and reporting in `/home/cosmosapjw/metro/src/metroflow/sim/step.py`

**Checkpoint**: US3 adaptive improvement is independently testable and fallback-safe.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Finalize evidence pipeline, docs, and release-quality validation.

- [ ] T053 Update architecture decision records for map-first sequencing in `/home/cosmosapjw/metro/docs/ARCHITECTURE.md`
- [ ] T054 [P] Refresh quickstart command matrix and acceptance evidence checklist in `/home/cosmosapjw/metro/specs/001-adaptive-traffic-sim/quickstart.md`
- [ ] T055 [P] Generate/refresh fixed-seed map audit artifacts under `/home/cosmosapjw/metro/artifacts/maps/`
- [ ] T056 [P] Generate/refresh benchmark evidence artifacts under `/home/cosmosapjw/metro/artifacts/benchmarks/`
- [ ] T057 Run containerized regression command set and store summarized logs in `/home/cosmosapjw/metro/artifacts/benchmarks/regression_summary.md`
- [ ] T058 Finalize task execution evidence index in `/home/cosmosapjw/metro/specs/001-adaptive-traffic-sim/checklists/task-evidence-index.md`

---

## Phase 8: Documentation Integrity & Prototype Reconciliation Gate

**Purpose**: Enforce document/prototype/dependency coherence before simulator-construction expansion phases proceed.

**⚠️ CRITICAL**: Simulator-construction expansion phases (US2/US4/US3) remain blocked until this gate passes.

- [ ] T059 Create consolidated reconciliation-gate checklist mapped to `/home/cosmosapjw/metro/docs/DOCS_MANIFEST.md` and `/home/cosmosapjw/metro/specs/001-adaptive-traffic-sim/contracts/document-reconciliation-report.md` in `/home/cosmosapjw/metro/specs/001-adaptive-traffic-sim/checklists/reconciliation-gate.md`
- [ ] T060 [P] Reconcile prototype-vs-SDD conflicts and update disposition report in `/home/cosmosapjw/metro/specs/001-adaptive-traffic-sim/contracts/document-reconciliation-report.md`
- [ ] T061 [P] Align dependency source-of-truth mapping for docs/manifests in `/home/cosmosapjw/metro/docs/ARCHITECTURE.md`
- [ ] T062 [P] Synchronize reconciliation quickstart and command flow in `/home/cosmosapjw/metro/specs/001-adaptive-traffic-sim/reconciliation-quickstart.md`
- [ ] T063 Run deterministic reconciliation audit sequence and summarize run-equality evidence in `/home/cosmosapjw/metro/artifacts/doc-audit/benchmark.md`
- [ ] T064 Run reconciliation-focused validation commands and publish pass/fail summary in `/home/cosmosapjw/metro/artifacts/doc-audit/validation-summary.md`
- [ ] T065 Publish reconciliation readiness gate status (`PASS`/`FAIL`) for implementation entry in `/home/cosmosapjw/metro/artifacts/doc-audit/readiness-summary.md`

**Checkpoint**: Documentation/prototype/dependency reconciliation gate passes and unblocks simulator-construction expansion.

---

## Phase 10: User Story 4 - GUI Runtime/Control Baseline (Priority: P2)

**Goal**: Satisfy first-release GUI runtime/control/observability requirements for US4 without coupling GUI lifecycle to `metroflow.demo`.

**Independent Test**: Launch dedicated GUI entrypoint on local-host, confirm mandatory panels and control set, and verify dropped/coalesced frame counters and benchmark evidence outputs.

### Tests for User Story 4 (GUI)

- [ ] T066 [P] [US4] Add contract test for dedicated GUI entrypoint and local-host binding in `/home/cosmosapjw/metro/tests/contract/test_gui_entrypoint_contract.py`
- [ ] T067 [P] [US4] Add integration test for mandatory panel/control set and paused-state semantics in `/home/cosmosapjw/metro/tests/integration/test_us4_gui_controls_panels.py`
- [ ] T068 [P] [US4] Add contract test ensuring ad-hoc GUI `inject_event`/`clear_event` commands are rejected in first-release scope in `/home/cosmosapjw/metro/tests/contract/test_gui_deferred_controls_contract.py`
- [ ] T069 [P] [US4] Add contract test ensuring GUI recording/replay commands remain disabled in first-release scope in `/home/cosmosapjw/metro/tests/contract/test_gui_recording_replay_deferred_contract.py`

### Implementation for User Story 4 (GUI)

- [ ] T070 [US4] Implement dedicated GUI entrypoint separated from demo lifecycle in `/home/cosmosapjw/metro/src/metroflow/gui/app.py`
- [ ] T071 [US4] Implement local-host-only binding and default N-tick update mode in `/home/cosmosapjw/metro/src/metroflow/ui/stream_server.py`
- [ ] T072 [US4] Implement dropped/coalesced frame counter exposure in GUI packets in `/home/cosmosapjw/metro/src/metroflow/ui/packets.py`
- [ ] T073 [US4] Integrate GUI frame-quality evidence export into benchmark run reporting in `/home/cosmosapjw/metro/src/metroflow/benchmarks/run.py`
- [ ] T074 [P] [US4] Add integration smoke for Chromium/WebGL profile and Canvas fallback capability flags in `/home/cosmosapjw/metro/tests/integration/test_us4_gui_browser_profile.py`
- [ ] T075 [US4] Implement GUI runtime profile capability contract (Chromium/WebGL-primary/fallback) in `/home/cosmosapjw/metro/src/metroflow/gui/runtime_profile.py`
- [ ] T076 [US4] Implement first-release deferred GUI control rejection for `inject_event`/`clear_event` in `/home/cosmosapjw/metro/src/metroflow/ui/control_adapter.py`
- [ ] T077 [US4] Implement first-release recording/replay rejection contract in `/home/cosmosapjw/metro/src/metroflow/ui/control_adapter.py`

**Checkpoint**: US4 GUI baseline requirements are independently testable and aligned with SC-030..SC-034.

---

## Phase 11: Evidence Policy Reinforcement

**Purpose**: Close remaining evidence-policy gates for GUI and realism-surgery acceptance.

- [ ] T078 [P] Add GUI PR screenshot evidence checklist and reviewer sign-off fields in `/home/cosmosapjw/metro/specs/001-adaptive-traffic-sim/checklists/gui-pr-artifact-policy.md`
- [ ] T079 Add nightly full-batch realism image-audit command profile in `/home/cosmosapjw/metro/scripts/validate_adaptive_traffic_sim.sh`
- [ ] T080 Add minimum-3 auto self-audit repetition gate and failure-summary output in `/home/cosmosapjw/metro/scripts/validate_adaptive_traffic_sim.sh`

**Checkpoint**: Screenshot/nightly/full-batch/min-repetition evidence gates are explicitly enforceable.

---

## Dependencies & Execution Order

### Canonical Phase Semantics (Cross-Doc)

- Transit static-wiring semantics are canonical Phase 9 requirements and are
  implemented by tasks Phase 5 (US4 transit static scope).
- GUI runtime/control baseline is canonical Phase 10 (tasks Phase 10 section).
- Evidence-policy reinforcement is canonical Phase 11 (tasks Phase 11 section).

### Phase Dependencies

- Phase 1 (Setup): start immediately
- Phase 2 (Foundational): depends on Phase 1; blocks all user stories
- Phase 3 (US1): depends on Phase 2
- Phase 8 (Reconciliation Gate): depends on Phase 1 and can run in parallel with Phases 2-3
- Phase 4 (US2): depends on Phase 3 + Phase 8 gate pass
- Phase 5 (US4): depends on Phase 3 + Phase 8 gate pass (and can proceed in parallel with Phase 4)
- Phase 10 (US4 GUI): depends on Phase 5 + Phase 8 gate pass
- Phase 6 (US3): depends on Phase 3 + Phase 8 gate pass + stable runtime signals from Phase 4
- Phase 7 (Polish): depends on selected story completion (including Phase 10 when GUI scope is enabled)
- Phase 11 (Evidence Policy): depends on Phase 7 + Phase 10 + Phase 8 gate pass

### User Story Dependency Graph

- US1 (P1) -> US2 (P2) -> US3 (P3)
- US1 (P1) -> US4 (P2)
- US4 and US2 can run in parallel after US1 map realism gates pass.
- US2/US4/US3 expansion stories require Phase 8 reconciliation gate `PASS`.

### Independent Test Criteria by Story

- US1: fixed-seed map realism + baseline observation/day-time behavior pass
- US2: disruption reroute diversity + redistribution + invariants pass
- US4: transit observability + GUI baseline controls/panels + frame counters pass with road-only compatibility preserved, with deferred `inject_event`/`clear_event` and recording/replay controls explicitly rejected in first-release scope
- US3: learning improvements pass with fallback/reproducibility preserved
- Reconciliation Gate: prototype-vs-SDD conflicts resolved + dependency coherence readiness PASS

---

## Parallel Execution Examples

### US1

```bash
Task: "T015 [US1] ... /home/cosmosapjw/metro/tests/unit/test_city_realism_morphology_metrics.py"
Task: "T016 [US1] ... /home/cosmosapjw/metro/tests/unit/test_city_zoning_scaling.py"
Task: "T017 [US1] ... /home/cosmosapjw/metro/tests/unit/test_render_city_map.py"
```

### US2

```bash
Task: "T028 [US2] ... /home/cosmosapjw/metro/tests/integration/test_us2_disruption_rerouting.py"
Task: "T029 [US2] ... /home/cosmosapjw/metro/tests/integration/test_us2_congestion_redistribution.py"
Task: "T030 [US2] ... /home/cosmosapjw/metro/tests/integration/test_us2_boundary_invariants.py"
```

### US4

```bash
Task: "T036 [US4] ... /home/cosmosapjw/metro/tests/contract/test_transit_network_contract.py"
Task: "T037 [US4] ... /home/cosmosapjw/metro/tests/contract/test_ui_packet_contract.py"
Task: "T038 [US4] ... /home/cosmosapjw/metro/tests/integration/test_us4_transit_network_generation.py"
Task: "T066 [US4] ... /home/cosmosapjw/metro/tests/contract/test_gui_entrypoint_contract.py"
Task: "T067 [US4] ... /home/cosmosapjw/metro/tests/integration/test_us4_gui_controls_panels.py"
Task: "T068 [US4] ... /home/cosmosapjw/metro/tests/contract/test_gui_deferred_controls_contract.py"
Task: "T069 [US4] ... /home/cosmosapjw/metro/tests/contract/test_gui_recording_replay_deferred_contract.py"
Task: "T074 [US4] ... /home/cosmosapjw/metro/tests/integration/test_us4_gui_browser_profile.py"
```

### US3

```bash
Task: "T045 [US3] ... /home/cosmosapjw/metro/tests/unit/test_od_ucb_bandit.py"
Task: "T046 [US3] ... /home/cosmosapjw/metro/tests/unit/test_routing_policy_mixer.py"
Task: "T047 [US3] ... /home/cosmosapjw/metro/tests/integration/test_us3_policy_blend_fallback.py"
```

---

## Implementation Strategy

### MVP First (Map-Realism + US1)

1. Complete Phase 1 + Phase 2
2. Complete Phase 3 (US1)
3. Validate SC-020..SC-042 map-first gates
4. Only then proceed to US2/US4/US3 expansions

### Incremental Delivery

1. Map realism foundation and baseline observation (US1)
2. Documentation/prototype/dependency reconciliation gate pass (Phase 8)
3. Event/disruption realism (US2)
4. Transit observability extension + GUI baseline controls (US4, Phase 5 + Phase 10)
5. Adaptive learning improvements (US3)
6. Polish and evidence consolidation
7. Evidence policy reinforcement gates (Phase 11)

### Notes

- All Python/JAX execution commands must run in container via `./scripts/in_docker.sh`.
- Every task execution must include: doc citation -> minimal diff -> pytest+demo smoke summary -> `/review` triage queue.
- Keep diffs task-scoped and maintain deterministic seed behavior.
