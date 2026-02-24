# SDD Upgrade Plan for 100k Transit/Metro-Ready Synthetic City

**Purpose**: `specs/001-adaptive-traffic-sim/` 문서군(`spec.md`, `plan.md`, `data-model.md`, `tasks.md`)을  
현재 baseline road-network 중심 정의에서, **현실성 있는 100k급 도시 + 대중교통/메트로 시뮬레이션** 목표를 다룰 수 있도록 확장하기 위한 문서 업그레이드 기준.

이 문서는 구현 작업이 아니라 **SDD 문서 개선 지침(addendum)** 이다.

## 1) Upgrade Objectives

### O1. Scope separation (must be explicit)
- 현재 baseline road-only MVP 범위와
- 향후 transit/metro realism 범위를
- `spec.md`와 `tasks.md`에서 명확히 분리한다.

### O2. Realism claims must become measurable
- “현실적” 표현을 계량 기준으로 바꾼다.
- 예: bridge criticality, zone granularity, POI density scaling, station spacing, transfer counts.

### O3. Keep JAX-first and incremental delivery
- 코어 루프는 JAX-first 유지
- 생성기/네트워크/수요/운영 계층은 분리
- baseline을 깨지 않고 realism/transit을 단계적 추가

## 2) Required `spec.md` Upgrades

### A. Scope framing
- `MVP (road baseline)`와 `Transit/Metro realism extension`를 별도 범위로 명시
- “100k playable speed”가 road-only인지 multimodal 포함인지 구분

### B. New/updated Functional Requirements (examples to introduce)
- Synthetic city must support multiple subdistricts per zone type (not only one zone each)
- POI count/density must scale with population target and zone size
- Barrier/bridge topology must produce measurable chokepoint behavior under closure scenarios
- System must support synthetic transit infrastructure:
  - stations
  - track/line topology
  - service patterns/headways
  - transfers / stop access
- System must simulate passenger boarding/alighting and station crowd metrics (baseline level)
- UI must render transit layer(s) and transit congestion/occupancy summary (phase-gated)

### C. Success Criteria / quality bars (examples)
- Structural metrics:
  - min node count / link count / zone count / POI count for 100k scenario
  - bridge closure increases avg path cost or disconnects targeted subareas within bounded criteria
- Transit metrics:
  - station count range, mean station spacing range
  - transfer-capable hubs count
  - peak load concentration on at least one corridor
- Performance metrics:
  - baseline road-only and multimodal modes reported separately

## 3) Required `data-model.md` Upgrades

### A. City morphology / zoning refinements
- Add `ZoneCluster` or `Subzone` concept (optional but recommended)
- Add corridor/land-use tags supporting subcenters and belt development
- Explicit POI scaling and density parameters

### B. Transit entities (minimum baseline set)
- `TransitStation`
- `TransitStopAccess` (zone/node to station walk access)
- `TransitLink` (track/segment)
- `TransitLine`
- `TransitServicePattern` or `TransitSchedule`
- `TransitVehicleState` (if in-scope)
- `PassengerTripLeg` / `TransitLeg` (or route representation extension)

### C. Multimodal state interfaces
- routing candidate sets across road/transit/walk access
- transfer penalties / waiting time estimates
- passenger queue / platform load metrics

## 4) Required `plan.md` Upgrades

### A. Architecture updates
- Preserve `city / demand / flow / routing / ui` separation
- Add explicit transit module boundary (e.g. `transit/`)
- Define integration contract with simulation step orchestration (`sim.init`, `sim.step`)

### B. Generator strategy
- Separate:
  - topology planning (numeric/JAX-portable)
  - object materialization
  - realism validation metrics
- Introduce morphology randomness constraints (avoid perfect symmetry)
- Introduce bridge criticality validation in generation loop

### C. Performance/JAX strategy
- Distinguish one-time init generators vs per-tick simulation kernels
- Specify which transit operations are JIT targets and which remain Python orchestration
- Keep packed arrays for active agents/passengers and sparse network structures

### D. Validation strategy
- Add map realism smoke metrics to quickstart/bench flow
- Add bridge closure sensitivity tests
- Add POI scaling and zone granularity regression tests

## 5) Required `tasks.md` Upgrades

### A. New documentation tasks (before code-heavy transit work)
- spec/plan/data-model updates for transit realism
- realism validation metrics doc
- UI contract extension doc for transit overlays

### B. New test tasks
- topology realism metrics tests (node/link/zone/poi thresholds)
- bridge criticality / closure sensitivity tests
- POI scaling vs population target tests
- transit network generation and station spacing tests
- multimodal routing / transfer integration tests

### C. New implementation tasks (phase-gated)
- city generator realism upgrades (irregularity, subzones, critical bridges)
- transit network generator (stations/lines)
- transit demand/access assignment
- passenger boarding/alighting + waiting
- multimodal route candidate generation
- transit UI packet/snapshot integration

### D. Task sequencing rule
- baseline road MVP tasks remain valid and should not be rewritten retroactively
- transit/realism tasks should be introduced as new phases/story sets
- each phase must define independent smoke validation

## 6) Acceptance Checklist for the SDD Upgrade (Documents Only)

문서 업그레이드가 완료되었다고 보기 위한 최소 조건:

- `spec.md`에 road-only MVP와 transit/realism target 구분이 존재한다
- `spec.md`에 계량 가능한 realism criteria가 추가되었다
- `data-model.md`에 transit entity skeleton이 정의되었다
- `plan.md`에 transit module boundary + JAX/perf strategy가 정의되었다
- `tasks.md`에 테스트 선행 + 단계적 구현 task가 추가되었다
- 기존 baseline task의 의미가 깨지지 않았다

## 7) Prompting Policy for This Upgrade

- 기존 문서를 한 번에 전면 리라이트하지 않는다
- 작은 diff 원칙으로 섹션 추가/보강을 우선한다
- 추상적 “현실성” 표현을 정량 지표로 바꾸게 유도한다
- 구현 코드는 아직 생성하지 않는다 (이번 라운드는 SDD 문서만)

