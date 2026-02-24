# City Map Realism Assessment (100k Transit/Metro Readiness)

**Feature**: `specs/001-adaptive-traffic-sim/`  
**Assessment Date**: 2026-02-23  
**Inputs Reviewed**:
- `artifacts/sample_city_maps/city_map_baseline_seed7.png`
- `artifacts/sample_city_maps/city_map_multibarrier_seed11.png`
- `artifacts/sample_city_maps/city_map_dense_ring_seed23.png`
- `artifacts/sample_city_maps/manifest.json`
- `artifacts/sample_city_maps/analysis.json` (generated during review)

## 1) Summary Verdict

현재 생성된 지도는 다음 용도에는 충분하다:
- 초기 baseline 도로교통 시뮬레이션
- UI/패킷/혼잡 시각화 스모크
- 회귀 테스트용 synthetic fixture

하지만 다음 용도에는 충분하지 않다:
- 인구 100k 도시의 **현실성 있는 대중교통/메트로 시뮬레이션**
- 멀티모달(도로+대중교통) 정책 비교
- 실제 도시 형태와 유사한 병목/접근성/환승 패턴 검증

## 2) Evidence Snapshot

샘플 크기(현재 구현 기준):

| Sample | Population Target | Nodes | Links | Turns | Bridges | Zones | POIs |
|---|---:|---:|---:|---:|---:|---:|---:|
| baseline_seed7 | 100,000 | 34 | 104 | 376 | 3 | 4 | 42 |
| multibarrier_seed11 | 120,000 | 45 | 136 | 490 | 4 | 4 | 42 |
| dense_ring_seed23 | 150,000 | 56 | 176 | 640 | 5 | 4 | 61 |

정성/정량 관찰:
- 그래프는 연결되어 있음(시뮬 안정성에는 긍정적)
- 도로 계층(local/arterial/expressway/ramp/bridge)은 명확함
- 하지만 도시 공간 해상도(node/POI 수)가 100k급 도시 대비 매우 낮음
- 멀티배리어 샘플도 bridge 제거 시 네트워크가 분리되지 않음(bridge bottleneck realism 약함)
- zone 수가 항상 4개(각 타입 1개)로 고정되어 OD 다양성/서브센터 표현이 부족함
- transit/metro 엔티티(선로/역/노선/환승/운행) 자체가 없음

## 3) What Is Realistic Enough Today

### A. Good Enough (Current Scope)
- 도로 계층 구조 실험
- 장벽/교량이 있는 synthetic road network 테스트
- 혼잡 레이어 시각화 패킷 데모
- baseline routing/flow/invariant 실험용 fixture

### B. Not Yet Realistic (Target Scope: 100k Transit/Metro)
- 메트로 운영/수송(차량, headway, 역별 승하차)
- 환승/접근성 기반 통행 선택
- 다핵 도시 형태(복수 고용 중심지)
- 대중교통 수요 집중/분산 재현
- 구조적 병목(bridge closure 시 도시 단절/우회 폭증)

## 4) Gap List (Mapped to SDD Artifacts)

### G1. Transit network model is absent (Hard blocker)
- **Impact**: 메트로/대중교통 시뮬레이션 불가
- **SDD updates needed**:
  - `spec.md`: transit/metro 기능 요구사항 추가
  - `data-model.md`: Station / TransitLink / TransitLine / ServicePattern / StopAccess 등 추가
  - `contracts/*`: UI 및 step 계약에 transit state/telemetry 반영
  - `tasks.md`: transit network generation + ops tasks 추가

### G2. Spatial resolution is too coarse for 100k
- **Evidence**: 100k population에서 node=34, POI=42 수준
- **Impact**: 접근성/환승/혼잡 hotspot 재현 불가
- **SDD updates needed**:
  - `spec.md`: 최소 node/zone/POI density 요구 추가
  - `plan.md`: 계층적 공간 해상도/압축 전략 설계
  - `tasks.md`: zoning granularity / POI scaling task 추가

### G3. Zone model is overly coarse (4 zones total)
- **Impact**: 단순한 OD 패턴만 생성, 실제 도시 다핵 구조 표현 불가
- **SDD updates needed**:
  - `spec.md`: 다중 residential district / employment subcenter 요구
  - `data-model.md`: zone cluster / subzone / corridor annotations 고려
  - `tasks.md`: zone subdivision generator task 추가

### G4. Bridges do not act as structural chokepoints
- **Evidence**: bridge 제거 후에도 single component 유지
- **Impact**: 이벤트/폐쇄 시 재분배 시뮬 realism 약함
- **SDD updates needed**:
  - `spec.md`: bridge criticality criteria(연결성/우회비용 증가) 명시
  - `plan.md`: barrier-cut validation metric 설계
  - `tasks.md`: topology realism validation task 추가

### G5. Geometric regularity is too grid-like / symmetric
- **Impact**: 실제 도시 형태/경로 다양성 부족
- **SDD updates needed**:
  - `spec.md`: morphology diversity requirements (irregular blocks, asymmetric districts)
  - `plan.md`: generator parameterization + stochastic constraints 설계
  - `tasks.md`: morphology perturbation + validation tasks 추가

### G6. POI count scales weakly with population
- **Impact**: 100k↔120k에서 spatial demand granularity 변화 미미
- **SDD updates needed**:
  - `spec.md`: POI density scaling requirement
  - `plan.md`: POI generation scaling formula + caps
  - `tasks.md`: POI scaling regression tests/task 추가

## 5) Readiness Matrix

| Use Case | Current Readiness | Notes |
|---|---|---|
| Baseline road congestion demo | Good | current generator is adequate |
| UI topology/congestion packet dev | Good | stable synthetic structure |
| 100k macro toy traffic simulation | Limited | coarse but workable for early prototyping |
| 100k metro/transit operations simulation | Not Ready | transit entities absent |
| Urban-plausible multimodal policy evaluation | Not Ready | resolution + morphology + transit gaps |

## 6) Recommended SDD Upgrade Strategy (High Level)

이 문서는 **문제 진단** 문서다. 즉시 기존 `spec.md/plan.md/tasks.md`를 덮어쓰지 않고, 다음 순서로 진행한다.

1. `spec.md`에 “baseline road-only MVP”와 “transit/metro realism target”을 명확히 분리
2. `plan.md`에 멀티모달 데이터모델/성능 전략/JAX 텐서화 경계 추가
3. `tasks.md`에 현실성 검증용 작업(지도 품질/브리지 임계성/POI scaling) + transit 기능 작업 추가
4. 기존 US1 baseline 작업은 유지하고, realism/transit upgrade를 신규 story/phase로 추가

## 7) Non-Goals (For the Upgrade Prompting Round)

이번 문서/프롬프트 업그레이드 단계에서 아직 하지 않는 것:
- 실제 구현 코드 수정
- 기존 알고리즘의 즉시 교체
- 외부 GIS/GTFS 데이터 의존 추가

