# Feature Specification: Adaptive Traffic Simulation for Virtual City

**Feature Branch**: `001-adaptive-traffic-sim`  
**Created**: 2026-02-23  
**Status**: Draft  
**Input**: User description: "인구 약 10만의 가상 도시에서, 시민 개별 주소/직장/일정에 따라 이동하는 교통 시뮬레이션을 만든다. 목표는 도시게임에서 흔한 무조건 최단거리 이동 문제를 완화해 우회/분산/병목이 자연스럽게 나타나게 하는 것이다. 현실 지도 데이터는 사용하지 않으며, 계층형 도로망, 강/장벽과 대교 병목, 존 구조, 시민 일정 기반 트립, 이벤트 반응, 행동 다양성, 시뮬레이터 경험 기반 점진 학습, 최소 지도 UI, 플레이 가능한 속도를 포함한다."

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

### Edge Cases

- 요일 전환 시점(예: 금요일 밤 -> 토요일 새벽)에 이미 이동 중인 시민은 현재 트립을
  유지하고, 이후 생성되는 트립부터 새 요일 규칙을 적용해야 한다.
- 시간대 전환 시점(아침 -> 점심 등)에는 이동 중 트립을 강제 재생성하지 않고, 다음
  목적지 선택/출발 시점부터 새로운 시간대 분포를 적용해야 한다.
- 모든 대교 중 하나 이상이 차단되어도 대체 경로가 있는 시민은 재탐색을 시도하고,
  대체 경로가 없는 시민은 실패 사유가 기록된 미완료 트립으로 처리되어야 한다.
- 대체 경로가 과포화되어도 큐 길이는 음수가 되지 않아야 하며, 용량 초과 상황은 탐지 및
  보고 대상 이벤트로 남아야 한다.
- 동일한 시드, 도시 생성 설정, 이벤트 스케줄, 요일/시간 조작 순서가 주어지면 동일한
  집계 결과(트립 수, 완료율, 주요 구간 혼잡 지표)가 재현되어야 한다.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST generate a synthetic city for a target population of
  approximately 100,000 people without requiring real-world map data.
- **FR-002**: System MUST include a hierarchical road network with local roads,
  arterials, and urban expressways including ring and radial patterns.
- **FR-003**: System MUST include at least one major barrier (e.g., river) and
  3 to 5 bridge crossings that can act as bottlenecks.
- **FR-004**: System MUST represent major intersections, interchanges, and ramps
  that connect local/arterial/expressway layers.
- **FR-005**: System MUST include zone types for residential bedroom towns,
  CBD/commercial districts, industrial districts, and mixed-use districts.
- **FR-006**: System MUST assign each citizen a home location and relevant daily
  destinations including work and leisure points of interest as applicable.
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
- **POI (Point of Interest)**: A concrete destination such as a home address,
  workplace, or leisure venue used in citizen schedules.
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
- Initial scope focuses on private-vehicle-like road travel behavior; transit,
  walking, and freight can be omitted or simplified if they do not block core
  route-diversity goals.
- Real-world map import, real address accuracy, and legal traffic compliance are
  out of scope for this feature.
- The UI is a lightweight observation/control interface (map + congestion layer +
  day/time toggles), not a full city-building editor.
- Learning quality is evaluated by repeated simulator runs in comparable
  scenarios; external datasets, prerecorded trajectories, and manual labels are
  excluded.
- Success criteria performance measurements use a documented standard validation
  scenario and validation environment so results are comparable over time.

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
  simulation maintains a playable update rate of at least 2 simulation ticks per
  second median during active traffic periods, and users can observe day/time
  toggle effects on the map within 2 real-world seconds.
- **SC-006**: Across regression validation scenarios, no negative queue lengths
  occur, all detected capacity violations are reported, and fixed-seed reruns
  reproduce the same run-summary totals for trip generation and completion.

*Performance criteria MUST state measurement method/environment (including
container/runtime assumptions) and avoid unmeasured claims.*
