# Feature Specification: Adaptive Traffic Simulation for Virtual City

**Feature Branch**: `001-adaptive-traffic-sim`  
**Created**: 2026-02-23  
**Status**: Draft  
**Input**: User description: "인구 약 10만의 가상 도시에서, 시민 개별 주소/직장/일정에 따라 이동하는 교통 시뮬레이션을 만든다. 목표는 도시게임에서 흔한 무조건 최단거리 이동 문제를 완화해 우회/분산/병목이 자연스럽게 나타나게 하는 것이다. 현실 지도 데이터는 사용하지 않으며, 계층형 도로망, 강/장벽과 대교 병목, 존 구조, 시민 일정 기반 트립, 이벤트 반응, 행동 다양성, 시뮬레이터 경험 기반 점진 학습, 최소 지도 UI, 플레이 가능한 속도를 포함한다."

## Clarifications

### Session 2026-02-23

- Q: Transit realism MVP 범위는 어디까지 포함할 것인가? → A: Station/line/headway + 승하차/대기/환승 포함, 차량 운영/적재율은 단순화(집계 가능)
- Q: 100k 도시에서 최소/권장 해상도 기준은? → A: Balanced 범위 채택 (nodes 500–1,500 / links 1,500–5,000 / zones 24–64 / POIs 5,000–20,000 / stations 20–60)
- Q: bridge/barrier 구조적 chokepoint는 어떻게 정의할 것인가? → A: Hybrid 기준 (closure 시 연결성 분리 또는 affected cross-barrier OD 평균 경로비용/ETA proxy 25% 이상 증가)
- Q: 멀티모달 경로선택 baseline 최소 동작은 어디까지인가? → A: 단계적 범위 채택 (baseline은 road-only vs transit 대안 비교 지원, in-trip 혼합 전환은 후속 확장)
- Q: 성능 목표는 road-only와 multimodal 각각 어떻게 둘 것인가? → A: 분리 목표 채택 (road-only >=2 ticks/s median, multimodal >=1 ticks/s median; 동일 하드웨어/컨테이너/시나리오 조건 명시)
- Q: Transit MVP의 보행 접근 모델은 explicit pedestrian graph인가, walk-time proxy인가? → A: MVP는 walk-time proxy, explicit pedestrian graph는 후속 phase
- Q: Collector road를 transit/metro realism MVP에 포함할 것인가? → A: 포함 (road class로 명시 추가)
- Q: Curved/terrain-adaptive roads를 transit/metro realism MVP에 포함할 것인가? → A: 포함 (true curved roads + terrain-adaptive curves를 MVP scope에 포함)
- Q: Density zoning 단계 수는 몇 단계로 둘 것인가? → A: 3단계 (low / medium / high)
- Q: Industrial separation / parks / parking / landmarks의 MVP 포함 범위는? → A: 모두 MVP 포함 (industrial separation은 완충 규칙 포함; parks/parking/landmarks/facilities 포함)

## Scope Labels

- `[BASELINE]`: 기존 road-only MVP 동작/데모/검증을 유지하기 위한 요구사항
- `[EXTENSION-MVP]`: 100k synthetic city + transit/metro realism 확장 MVP 요구사항
- `[CROSS-CUTTING]`: baseline/extension 모두에 적용되는 호환성, 관측성, 검증, 성능 비교 규칙
- Functional Requirements scope mapping:
  - Baseline-primary: `FR-001`, `FR-002`, `FR-003`, `FR-004`, `FR-005`, `FR-006`, `FR-007`-`FR-015`, `FR-019`
  - Extension-primary: `FR-002a`, `FR-005a`, `FR-005b`, `FR-006a`, `FR-006b`, `FR-020`-`FR-023`, `FR-025`-`FR-029`
  - Cross-cutting: `FR-003a`, `FR-016`-`FR-018`, `FR-024`
- Success Criteria scope mapping:
  - Baseline-primary: `SC-001`-`SC-006`
  - Extension-primary: `SC-007`-`SC-018`
  - Cross-cutting compatibility/regression: `SC-019`

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 가상 도시 교통 관찰 (Priority: P1)

도시게임 디자이너는 현실 지도 없이도 10만 인구 규모의 가상 도시를 생성하고,
평일/주말 및 시간대 전환에 따라 시민 이동과 혼잡이 어떻게 형성되는지 지도에서
관찰하고 싶다. 최소한의 지도/혼잡 레이어와 시간·요일 토글을 통해 병목과 분산을
빠르게 확인할 수 있어야 한다.

**Why this priority**: 핵심 가치(고정 최단경로가 아닌 자연스러운 혼잡/분산)를
가장 먼저 검증할 수 있는 최소 기능이며, 이후 이벤트 반응/학습 기능의 기반이 된다.

**Independent Test**: 기본 시나리오에서 가상 도시를 생성하고 시뮬레이션을 실행한 뒤,
지도에서 도로망과 혼잡 레이어가 표시되고 요일/시간 전환에 따라 혼잡 패턴이 바뀌는지
관찰하면 독립 검증 가능하다.

**Acceptance Scenarios**:

1. **Given** 새 가상 도시를 생성한 상태에서, **When** 평일 아침 시간대로 시뮬레이션을
   실행하면, **Then** 지도에 계층형 도로망과 혼잡 레이어가 표시되고 주요 교량/간선
   접근로에 피크 혼잡이 나타난다.
2. **Given** 같은 도시를 실행 중인 상태에서, **When** 요일을 평일에서 주말로 바꾸고
   저녁 시간대로 전환하면, **Then** 혼잡 집중 구간이 평일 출퇴근 패턴과 다른 형태로
   재배치된다.

---

### User Story 2 - 이벤트 대응과 행동 다양성 관찰 (Priority: P2)

도시게임 디자이너는 사고/공사/혼잡 이벤트가 발생했을 때 시민들이 일괄적으로 같은
결정을 하지 않고, 일부는 우회하고 일부는 기존 경로를 고수하는 행동 다양성을 보고
싶다. 이를 통해 우회로, 대교, IC의 설계 효과를 비교하고 싶다.

**Why this priority**: 목표 문제(무조건 최단거리 이동)의 완화 여부를 가장 직접적으로
보여주며, 도시 구조 설계의 재미와 분석 가치를 크게 높인다.

**Independent Test**: 주요 대교 또는 간선에 이벤트를 적용하고 이벤트 전/후 혼잡과 경로
선택 분포를 비교하여 우회와 고수 행동이 동시에 나타나는지 확인하면 된다.

**Acceptance Scenarios**:

1. **Given** 평일 피크 시간에 주요 대교가 혼잡한 상태에서, **When** 해당 대교에 사고
   이벤트를 적용하면, **Then** 영향을 받는 이동 중 일부는 대체 교량/우회로로 전환하고
   일부는 지연을 감수하며 기존 경로를 유지한다.
2. **Given** 공사로 특정 연결로가 차단된 상태에서, **When** 시뮬레이션을 계속 진행하면,
   **Then** 차단 구간 접근 수요가 감소하고 인접 교차로/램프 및 대체 간선의 혼잡이
   증가하는 재분배 패턴이 지도에 반영된다.

---

### User Story 3 - 시뮬레이터 경험 기반 경로 개선 (Priority: P3)

도시게임 디자이너는 외부 데이터 없이 시뮬레이션을 반복 실행하면서 경로 선택이
점진적으로 개선되는 효과를 보고 싶다. 학습이 불안정할 때도 기본 정책 수준의 동작은
유지되어야 한다.

**Why this priority**: MetroFlow의 차별점인 점진적 자기개선 메커니즘을 제공하지만,
기본 교통 시뮬레이션과 이벤트 반응이 먼저 있어야 검증 가능한 기능이 된다.

**Independent Test**: 동일 도시/시나리오를 반복 실행하며 학습 기능을 켠 경우와 끈
경우를 비교해, 트립 완료율 악화 없이 평균 또는 중앙값 통행시간이 개선되는지 확인한다.

**Acceptance Scenarios**:

1. **Given** 동일한 도시와 이벤트 패턴으로 반복 가능한 시뮬레이션 조건이 준비된 상태에서,
   **When** 학습 기능을 켜고 여러 회차를 진행하면, **Then** 초기 회차 대비 후반 회차의
   피크 시간 통행 성과가 개선되고 기본 정책 대비 최소 동등 이상 수준을 유지한다.
2. **Given** 학습 기능이 활성화된 상태에서, **When** 학습 신호가 부족하거나 새로운
   이벤트 패턴이 발생하면, **Then** 시스템은 기본 정책 동작으로 안전하게 돌아가며
   비정상적인 경로 선택 급증 없이 시뮬레이션을 지속한다.

---

### User Story 4 - 대중교통/메트로 확장 관측과 비교 검증 (Priority: P2)

도시게임 디자이너는 기존 road-only baseline 시나리오를 유지한 상태에서, 같은 synthetic
도시에 대중교통/메트로 레이어를 추가했을 때 역/노선/환승/역혼잡 요약을 관찰하고
road-only 대안과 transit 대안을 비교하고 싶다.

**Why this priority**: 이번 spec 업그레이드의 핵심 목적이 baseline을 깨지 않으면서
transit/metro realism 확장 가능 요구사항을 정의하는 것이므로, 확장 범위의 관측성/비교
가능성을 별도 스토리로 명시해야 계획/태스크 분해가 안정적이다.

**Independent Test**: 표준 ~100k synthetic city validation scenario에서 transit
extension을 켠 run과 baseline road-only run을 각각 실행하여, transit layer/역 요약이
관측 가능하고 road-vs-transit 대안 비교 결과가 생성되는지 확인한다.

**Acceptance Scenarios**:

1. **Given** 표준 ~100k synthetic city validation scenario가 준비된 상태에서,
   **When** transit/metro realism extension을 활성화해 실행하면, **Then** 역/노선
   레이어와 승하차/대기/환승/역혼잡 요약이 관측 가능한 형태로 제공된다.
2. **Given** 동일한 도시/수요 조건의 baseline road-only run과 transit extension run이
   있는 상태에서, **When** 결과를 비교하면, **Then** baseline 결과는 계속 유효하며
   multimodal 대안 비교 결과가 별도로 보고된다.

---

### Edge Cases

- 요일 전환 시점(예: 금요일 밤 -> 토요일 새벽)에 이미 이동 중인 시민은 현재 트립을
  유지하고, 이후 생성되는 트립부터 새 요일 규칙을 적용해야 한다.
- 시간대 전환 시점(아침 -> 점심 등)에는 이동 중 트립을 강제 재생성하지 않고, 다음
  목적지 선택/출발 시점부터 새로운 시간대 분포를 적용해야 한다.
- 모든 대교 중 하나 이상이 차단되어도 대체 경로가 있는 시민은 재탐색을 시도하고,
  대체 경로가 없는 시민은 실패 사유가 기록된 미완료 트립으로 처리되어야 한다.
- 구조적 chokepoint 검증용 대교/장벽 폐쇄 시나리오에서는 대상 cross-barrier OD 집합에
  대해 연결성 분리 또는 평균 경로비용(ETA/hop proxy) 25% 이상 증가 중 하나가
  발생해야 하며, 측정 방법은 시나리오 정의에 포함되어야 한다.
- 대체 경로가 과포화되어도 큐 길이는 음수가 되지 않아야 하며, 용량 초과 상황은 탐지 및
  보고 대상 이벤트로 남아야 한다.
- 동일한 시드, 도시 생성 설정, 이벤트 스케줄, 요일/시간 조작 순서가 주어지면 동일한
  집계 결과(트립 수, 완료율, 주요 구간 혼잡 지표)가 재현되어야 한다.
- transit/metro realism extension이 비활성화된 baseline road-only 모드에서는 transit
  엔티티/레이어 부재로 인해 baseline 시나리오 검증 또는 데모 흐름이 실패해서는 안 된다.
- phase-gated transit UI/관측 기능에서 상위 단계(예: 상세 역혼잡 heatmap)가 비활성화된
  경우에도 MVP 단계 요약(노선/역 summary, 승하차/대기/환승 집계)은 계속 제공되어야 한다.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST generate a synthetic city for a target population of
  approximately 100,000 people without requiring real-world map data.
- **FR-002**: System MUST include a hierarchical road network with local roads,
  collector roads, arterials, and urban expressways including ring and radial
  patterns.
- **FR-002a**: For the transit/metro realism MVP extension, System MUST support
  curved road geometry and terrain-adaptive road curves (using synthetic terrain
  and barrier abstractions without real-world map import) rather than only
  straight grid-aligned road segments.
- **FR-003**: System MUST include at least one major barrier (e.g., river) and
  3 to 5 bridge crossings that can act as bottlenecks.
- **FR-003a**: Structural bridge/barrier chokepoint validation MUST use a
  hybrid criterion: a designated closure scenario MUST either disconnect at
  least one targeted cross-barrier OD/zone pair or increase affected
  cross-barrier average path cost (or documented ETA/hop proxy) by at least
  25% versus the non-closure control.
- **FR-004**: System MUST represent major intersections, interchanges, and ramps
  that connect local/arterial/expressway layers.
- **FR-005**: System MUST include zone types for residential bedroom towns,
  CBD/commercial districts, industrial districts, and mixed-use districts.
- **FR-005a**: For the transit/metro realism MVP extension, System MUST support
  density zoning tiers with at least three levels (`low`, `medium`, `high`)
  applicable to relevant zone areas/districts and used by POI/capacity
  generation and validation reporting.
- **FR-005b**: For the transit/metro realism MVP extension, System MUST enforce
  industrial-zone separation using documented synthetic distance and/or buffer
  zone rules relative to incompatible residential/leisure-dominant districts,
  and MUST report separation validation outcomes.
- **FR-006**: System MUST assign each citizen a home location and relevant daily
  destinations including work and leisure points of interest as applicable.
- **FR-006a**: For the transit/metro realism MVP extension, System MUST include
  POI taxonomy support beyond generic home/work/leisure, including essential
  facilities and landmark/leisure destinations with observable category labels
  and capacity hints.
- **FR-006b**: For the transit/metro realism MVP extension, System MUST include
  parks/green-space and parking supply representations (as land-use and/or POI/
  facility constructs) sufficient to appear in generated city outputs and
  validation summaries.
- **FR-007**: System MUST generate trips by day type (weekday/weekend) and time
  bands (morning/lunch/evening/night) using citizen schedules.
- **FR-008**: System MUST model congestion effects so route travel conditions can
  change during simulation and influence subsequent route choices.
- **FR-009**: System MUST react to congestion, accident, and construction events,
  including partial or full link disruptions where applicable.
- **FR-010**: System MUST produce behavioral diversity under disruption such that
  affected travelers do not all make the same route decision.
- **FR-011**: System MUST provide a safe default routing policy that remains
  available when adaptive behavior or learning signals are weak or unstable.
- **FR-012**: System MUST include a route-improvement mechanism that updates only
  from simulator-generated experience and MUST NOT require external training data.
- **FR-013**: System MUST apply adaptive route improvements gradually so observed
  behavior remains stable enough for interactive use and comparison.
- **FR-014**: Users MUST be able to view a navigator-style map showing the road
  network and a congestion overlay.
- **FR-015**: Users MUST be able to toggle day type and time-of-day state during
  exploration of the simulation.
- **FR-016**: System MUST preserve and validate core invariants, including
  conservation of tracked travelers/vehicles, non-negative queue lengths, and
  detection/reporting of capacity violations.
- **FR-017**: System MUST support fixed-seed reproducibility for comparable runs,
  including city generation, trip generation, and event scheduling outcomes.
- **FR-018**: System MUST provide run summaries that allow comparison of route
  performance and congestion outcomes before and after adaptive learning.
- **FR-019**: System MUST operate at a user-observable playable speed for the
  standard ~100k population scenario and report the measurement conditions used.
- **FR-020**: For the transit/metro realism MVP extension, System MUST support
  synthetic transit stations, lines, and service headway definitions and MUST
  simulate passenger boarding, alighting, waiting, and transfers at a baseline
  behavioral level.
- **FR-021**: For the transit/metro realism MVP extension, vehicle-level transit
  operations (dispatching, per-vehicle occupancy/load management) MAY be
  simplified or represented using aggregate service/capacity approximations if
  passenger flow and transfer behavior remain observable and testable.
- **FR-022**: For the transit/metro realism MVP extension in the standard
  ~100k population scenario, System MUST support a balanced synthetic city
  resolution target of approximately 500-1,500 nodes, 1,500-5,000 links,
  24-64 zones, 5,000-20,000 POIs, and 20-60 transit stations, and MUST report
  the realized counts for validation scenarios.
- **FR-023**: For the transit/metro realism MVP baseline multimodal routing
  stage, System MUST support route-choice comparison between at least one
  road-only alternative and one transit alternative (including walk access/
  egress), while in-trip mixed-mode transfers such as park-and-ride MAY be
  deferred to a later extension stage.
- **FR-024**: System MUST define and report performance measurements separately
  for road-only baseline scenarios and transit/multimodal scenarios, using the
  same documented hardware, container/runtime environment, and published
  validation scenario conditions for each comparison set.
- **FR-025**: For the transit/metro realism MVP, pedestrian access/egress to
  transit stations MAY be modeled using a documented walk-time/distance proxy
  (from zone or road-node anchors to stations) instead of an explicit pedestrian
  network graph, provided the proxy is reproducible and observable in routing
  outputs; an explicit pedestrian graph is deferred to a later phase.
- **FR-026**: [EXTENSION-MVP] System MUST produce transit observability outputs
  (for UI and/or run-summary consumption) that include per-time-band boarding,
  alighting, waiting, transfer counts, and station-level congestion/crowding
  summary metrics.
- **FR-027**: [EXTENSION-MVP] System MUST define phase-gated transit UI/observation
  layers such that an MVP phase includes at least station/line visibility,
  transit flow/congestion summary, and station congestion summaries, while finer
  detailed overlays MAY be deferred to later phases without breaking MVP outputs.
- **FR-028**: [EXTENSION-MVP] In the standard ~100k synthetic city validation
  scenario, System MUST generate multi-zone land-use structure sufficient for OD
  diversity, including multiple zones per major land-use type (not a single zone
  per type), and MUST report zone-type counts and dominant-capacity distribution.
- **FR-029**: [EXTENSION-MVP] System MUST generate synthetic city morphology with
  documented non-uniformity/asymmetry controls (e.g., corridor spacing variation,
  barrier shape variation, curved/offset corridors) so validation scenarios are
  not limited to highly regular symmetric layouts, and MUST report morphology
  summary metrics used for realism validation.

### Non-Functional Requirements

- **NFR-001 [CROSS-CUTTING]**: This specification upgrade MUST preserve existing
  baseline road-only MVP scope and demo intent; extension requirements MUST be
  optional/phase-gated and MUST NOT redefine baseline acceptance outcomes unless
  explicitly marked as superseding in a future phase.
- **NFR-002 [EXTENSION-MVP]**: Transit/metro realism extension scenarios MUST
  remain synthetic-only and MUST NOT require external GIS, GTFS, or real-map
  imports to satisfy functional or success criteria in this spec.
- **NFR-003 [CROSS-CUTTING]**: All realism/performance/chokepoint claims MUST be
  tied to published validation scenarios with documented seeds, scenario inputs,
  and measurement conditions so repeated runs can be compared across revisions.
- **NFR-004 [BASELINE]**: Road-only baseline performance reporting MUST continue
  to use the published standard ~100k baseline scenario and preserve the existing
  playable-speed target and observation responsiveness criteria.
- **NFR-005 [EXTENSION-MVP]**: Transit/multimodal performance reporting MUST be
  measured separately from road-only baseline and MUST use the same documented
  hardware and runtime/container environment for within-mode comparisons.
- **NFR-006 [EXTENSION-MVP]**: Transit observability summaries MUST be available
  at both run-summary and UI-consumable granularity for the MVP phase, even when
  detailed later-phase overlays are disabled.
- **NFR-007 [CROSS-CUTTING]**: Online learning behavior MUST remain simulator-
  internal-only and MUST NOT depend on external pretraining data or imported
  trajectories for baseline or extension validation scenarios.
- **NFR-008 [EXTENSION-MVP]**: Realism-oriented metrics (resolution, chokepoint
  closure sensitivity, zoning diversity, morphology non-uniformity) MUST be
  reported in a machine-readable validation summary for each published extension
  validation scenario.

### Key Entities *(include if feature involves data)*

- **City**: A generated virtual city containing the road network, barrier/bridges,
  zones, and scenario settings for one simulation run.
- **Road Link**: A directed travel segment with road class, capacity, current
  traffic state, and connectivity to adjacent links.
- **Node / Junction**: A connection point such as an intersection, ramp merge, or
  interchange that links multiple road segments.
- **Bridge Crossing**: A designated bottleneck link group spanning the barrier and
  used to test concentration and rerouting behavior.
- **Zone**: A land-use area category (residential, CBD/commercial, industrial,
  mixed-use) that anchors homes, jobs, and leisure destinations.
- **Zone Density Tier**: A density classification (`low`, `medium`, `high`) used
  to control and validate population/jobs/leisure capacity allocation within
  zone areas or subdistricts.
- **POI (Point of Interest)**: A concrete destination such as a home address,
  workplace, or leisure venue used in citizen schedules.
- **Transit Station**: A synthetic passenger access/egress node for one or more
  transit lines, with service headways and observable boarding/waiting/crowding
  summaries.
- **Transit Line**: A named or identified synthetic transit service corridor with
  ordered stops/stations and service headway configuration.
- **Transfer Node**: A station or station-complex location where passengers can
  change between lines and incur observable waiting/transfer behavior.
- **Access Connector (Walk Proxy)**: A documented synthetic walk access/egress
  connection from zone/node anchors to transit stations used in multimodal route
  comparison without an explicit pedestrian graph in the MVP phase.
- **Station Congestion Summary**: Aggregated station-level metrics for boarding,
  alighting, waiting, transfers, and crowding over defined time bands.
- **Citizen**: A simulated traveler with assigned home/destination POIs, schedule
  patterns, and route-choice behavior profile.
- **Trip**: A single travel demand instance with origin, destination, departure
  context (day type/time band), and completion outcome.
- **Traffic Event**: A time-bounded condition such as congestion spike, accident,
  or construction that alters travel conditions on part of the network.
- **Route Choice Profile**: Parameters describing how a traveler balances delay
  sensitivity, persistence, and willingness to reroute.
- **Simulation Run**: One execution of the city scenario under a fixed seed and
  configured controls, producing comparable outcome metrics.
- **Run Summary**: Aggregated outcomes for trip completion, travel times, and
  congestion distribution used to compare baseline and adaptive behavior.

## Assumptions & Scope Boundaries

- Primary user is a city-game designer or simulation operator evaluating traffic
  behavior patterns, not a civil engineering certification workflow.
- Baseline MVP scope focuses on private-vehicle-like road travel behavior; this
  road-only baseline remains in scope and should not be regressed by later
  transit/metro realism extensions.
- Transit/metro realism MVP extension scope includes synthetic stations/lines/
  headways and passenger boarding/alighting/waiting/transfer behavior, while
  vehicle-level transit operations and occupancy/load control may be simplified
  or aggregated in the first extension stage.
- Transit/metro realism MVP extension targets a balanced spatial resolution for
  ~100k scenarios (nodes 500-1,500; links 1,500-5,000; zones 24-64; POIs
  5,000-20,000; stations 20-60), with exact counts configurable per scenario.
- Transit/metro realism MVP extension includes collector roads as an explicit
  road hierarchy class (not just a speed/capacity proxy band) to improve
  neighborhood-to-arterial connectivity realism.
- Transit/metro realism MVP extension includes true curved roads and
  terrain-adaptive curves using synthetic terrain/barrier abstractions; this is
  not deferred to a later phase.
- Transit/metro realism MVP extension uses three density-zoning tiers
  (`low`/`medium`/`high`) as the minimum land-use density granularity.
- Transit/metro realism MVP extension includes industrial separation constraints
  with documented synthetic buffer/distance rules, rather than deferring them to
  a later phase.
- Transit/metro realism MVP extension includes parks/green-space, parking, and
  landmark/essential-facility representations in generated city outputs (not
  deferred), though detailed operations/behavior effects may still be phase-
  gated in later design/tasks documents.
- Transit/metro realism MVP extension includes explicit transit/metro entities
  (stations, lines, transfer-capable nodes, headways) and passenger flow
  observability, but may defer vehicle-level dispatch/load management detail.
- Bridge/barrier chokepoint claims use a published hybrid validation method
  (connectivity split OR >=25% affected cross-barrier path-cost increase),
  rather than hotspot ranking alone.
- Walking access/egress may be simplified in the transit/metro realism MVP
  extension as long as transit boarding, waiting, and transfer behavior are
  represented consistently for route-choice and observability purposes.
- In the transit/metro realism MVP, walking access/egress is represented by a
  documented walk-time/distance proxy (zone/node anchor to station) rather than
  an explicit pedestrian network graph; explicit pedestrian infrastructure is a
  later-phase extension.
- Multimodal baseline route choice in the transit/metro realism MVP extension
  is staged: road-only vs transit alternatives are compared, but in-trip mixed
  mode substitutions (e.g., park-and-ride / kiss-and-ride) are deferred.
- Transit/metro realism MVP extension requires phase-gated UI/observability:
  MVP includes transit line/station visibility and station congestion summaries;
  finer-grained crowding overlays and richer editor-like tools are later-phase.
- ~100k transit/metro realism MVP extension requires zone multiplicity and OD
  diversity beyond the historical "4 zones (one per type)" limitation and
  requires reported diversity metrics in validation outputs.
- ~100k transit/metro realism MVP extension requires synthetic morphology
  variability beyond highly regular symmetric layouts, validated via published
  morphology summary metrics rather than visual inspection alone.
- Real-world map import, real address accuracy, and legal traffic compliance are
  out of scope for this feature.
- The UI is a lightweight observation/control interface (map + congestion layer +
  day/time toggles), not a full city-building editor.
- Learning quality is evaluated by repeated simulator runs in comparable
  scenarios; external datasets, prerecorded trajectories, and manual labels are
  excluded.
- Success criteria performance measurements use a documented standard validation
  scenario and validation environment so results are comparable over time.
- Performance targets are phase-specific and mode-specific: road-only baseline
  and transit/multimodal scenarios use separate tick-rate targets measured under
  identical hardware/container/runtime conditions within each published
  comparison set.
- Project constraint retention: the existing JIT-first compiled-array
  performance direction and simulator-internal-only (online-only) learning
  principle remain unchanged by this spec upgrade.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a standard generated city scenario with approximately 100,000
  citizens, a user can start the simulation and view the road network plus
  congestion overlay within 60 seconds of scenario launch.
- **SC-002**: In weekday morning and evening peak scenarios, at least one bridge
  corridor and one CBD approach corridor appear among the top congestion hotspots
  in at least 80% of validation runs using the published scenario settings.
- **SC-003**: When a major bridge or arterial is disrupted during peak demand,
  the system shows mixed behavior within 15 simulated minutes, with both rerouted
  and delay-tolerant travelers present in the affected population.
- **SC-004**: With adaptive learning enabled over repeated comparable simulation
  runs, peak-period median trip travel time improves by at least 5% versus a
  baseline-only control, without reducing trip completion rate by more than 1%.
- **SC-005**: In the standard ~100k population validation scenario, the
  road-only baseline simulation maintains a playable update rate of at least 2
  simulation ticks per second median during active traffic periods, and users
  can observe day/time toggle effects on the map within 2 real-world seconds.
- **SC-006**: Across regression validation scenarios, no negative queue lengths
  occur, all detected capacity violations are reported, and fixed-seed reruns
  reproduce the same run-summary totals for trip generation and completion.
- **SC-007**: In the standard ~100k transit/metro realism MVP validation
  scenario, the generated city and transit network report realized counts within
  the configured balanced resolution ranges for nodes, links, zones, POIs, and
  transit stations.
- **SC-008**: In the published bridge/barrier closure validation scenario, at
  least one designated structural chokepoint closure satisfies the hybrid
  criterion by causing either targeted cross-barrier connectivity separation or
  a >=25% increase in affected cross-barrier average path cost (or documented
  ETA/hop proxy) versus the non-closure control run.
- **SC-009**: In the standard ~100k transit/metro realism MVP validation
  scenario, the system can evaluate both road-only and transit alternatives for
  a published multimodal demand subset and produce observable mode-choice
  outputs without requiring in-trip mixed-mode substitutions.
- **SC-010**: In the standard ~100k transit/metro realism MVP validation
  scenario, the transit/multimodal simulation maintains a playable update rate
  of at least 1 simulation tick per second median during active demand periods,
  measured under the same documented hardware, container/runtime environment,
  and published scenario conditions used for multimodal performance reporting.
- **SC-011**: In the standard ~100k transit/metro realism MVP validation
  scenario, the generated road network includes documented curved/terrain-
  adaptive segments under the published synthetic terrain/barrier settings, and
  the validation report publishes the proportion or count of non-straight road
  geometries generated.
- **SC-012**: In the standard ~100k transit/metro realism MVP validation
  scenario, the generated zoning output reports at least three density-zoning
  levels (`low`, `medium`, `high`) and publishes per-density counts/capacity
  totals for validation and comparison.
- **SC-013**: In the standard ~100k transit/metro realism MVP validation
  scenario, industrial-zone separation validation reports compliance with the
  published synthetic buffer/distance rules and identifies any violating zone or
  subdistrict pairs.
- **SC-014**: In the standard ~100k transit/metro realism MVP validation
  scenario, generated city outputs and summaries include reported counts (or
  capacities) for parks/green-space, parking supply, essential facilities, and
  landmark/leisure destination categories.
- **SC-015**: In the standard ~100k transit/metro realism MVP validation
  scenario, a user can enable the transit observation layer and view line/station
  visibility plus station congestion summaries within 3 real-world seconds after
  scenario load, without disabling baseline road congestion observation.
- **SC-016**: In the standard ~100k transit/metro realism MVP validation
  scenario, published transit observability summaries include per-time-band
  boarding, alighting, waiting, transfer, and station congestion/crowding
  metrics for at least 95% of active transit stations.
- **SC-017**: In the standard ~100k transit/metro realism MVP validation
  scenario, the zoning output contains at least 24 zones and reports multiple
  zones for each major land-use type, including at least 8 residential zones,
  2 industrial zones, and 4 mixed-use or commercial/CBD-dominant zones.
- **SC-018**: In the standard ~100k transit/metro realism MVP validation
  scenario, the published morphology summary confirms non-uniform synthetic city
  layout generation by reporting at least two distinct corridor spacing bands and
  at least one asymmetric or non-rectilinear morphology feature (e.g., curved or
  offset corridor/barrier geometry) in the generated city.
- **SC-019**: In regression validation, enabling or disabling the transit/metro
  realism extension does not invalidate the published baseline road-only
  validation scenarios, and baseline scenarios continue to satisfy `SC-001`
  through `SC-006` under the same published baseline conditions.

*Performance criteria MUST state measurement method/environment (including
container/runtime assumptions) and avoid unmeasured claims.*
