# City Feature Realism Checklist (100k Synthetic City + Transit/Metro Target)

목적:
- 현재 구현이 어떤 도시 설계 요소를 지원/미지원하는지 **체크리스트 형태**로 정리한다.
- `specs/001-adaptive-traffic-sim/` SDD 문서 업그레이드 시, 어떤 항목을 FR/SC/data-model/tasks에 반영해야 하는지 추적한다.

범위:
- 구현 코드 현황 진단 체크리스트 (문서/프롬프트 입력용)
- 구현 계획/우선순위 확정 문서는 아님

판정 기준:
- `Yes`: 현재 코드로 실질 기능 존재
- `Partial`: 개념/축은 있으나 현실성 수준 또는 세부 모델 부족
- `No`: 현재 코드 기준 미구현

## 1) Road Types & Geometry

| Feature | Current | Notes / Evidence | SDD Upgrade Need |
|---|---|---|---|
| Highway / Expressway | Partial | `expressway` 존재 (`src/metroflow/city/graph.py`) | 용어 정합성(`highway` vs `expressway`) 명시 |
| Arterial | Yes | `arterial` road class 존재 | 성능/혼잡 검증 지표 보강 |
| Collector | No | `collector` road class 없음 | `spec.md`, `data-model.md`, generator/tasks 추가 |
| Local | Yes | `local` road class 존재 | 공간 해상도/밀도 기준 보강 |
| Ramps / Interchange connectors | Partial | `ramp`, `ramp_merge/split`, `interchange` 존재 | 다양한 램프/IC 형태는 미구현 |
| Curved roads | No | node-to-node 직선 링크 중심 | polyline/curvature 모델 필요 |
| Terrain-adaptive curves | No | 고정 격자형 좌표 | terrain/elevation + curve constraints 필요 |
| Bridge corridors / barrier crossings | Partial | bridge/barrier 있음 | 구조적 chokepoint 검증 기준 필요 |

## 2) Intersections & Junction Types

| Feature | Current | Notes / Evidence | SDD Upgrade Need |
|---|---|---|---|
| Basic intersections | Yes | `intersection` node kind 존재 | 신호/우선순위 다양성 보강 가능 |
| Ramp merge / split | Yes | `ramp_merge`, `ramp_split` 존재 | lane-level / merge behavior는 미구현 |
| Interchanges | Partial | `interchange` node kind 존재 | 형태 다양성(다이아몬드/클로버 등) 미구현 |
| Signalized vs unsignalized intersection types | No | `signal_group_id` 필드만 존재, 타입 체계 없음 | junction control model 필요 |
| Roundabouts / special junctions | No | 없음 | data-model + generator 확장 필요 |

## 3) Zoning & Land Use

| Feature | Current | Notes / Evidence | SDD Upgrade Need |
|---|---|---|---|
| Density zoning (low/med/high) | Partial | zone capacity는 있으나 density zone class/gradient 없음 | density zoning requirements/data model 추가 |
| Mixed-use districts | Yes (basic) | `mixed_use` zone type 존재 | subdistrict granularity/밀도 계층 보강 |
| Industrial zone separation | Partial | `industrial` zone type 존재, 단순 공간 분할 | separation/buffer/compatibility 규칙 필요 |
| Multiple subcenters / subzones | No | zone types 4개 중심, coarse partition | subzone/cluster 모델 필요 |
| Parks/green-space land use type | No | zone/POI 타입 없음 | land-use/POI taxonomy 확장 필요 |

## 4) Transit & Active Travel

| Feature | Current | Notes / Evidence | SDD Upgrade Need |
|---|---|---|---|
| Line-based public transport | No | transit line/station/service 미구현 | transit core entities + generator 필요 |
| Transfer nodes / hubs | No | station/transfer 개념 없음 | station + transfer model 필요 |
| Headway/service patterns | No | 없음 | transit schedule/service pattern 모델 필요 |
| Passenger boarding/alighting/waiting | No | 없음 | transit passenger flow state/task 필요 |
| Pedestrian infrastructure (sidewalk/walk network) | No | explicit walk network 없음 | walk access/egress network 모델 필요 |
| Bicycle/active travel network | No | 없음 | optional future multimodal extension 정의 필요 |

## 5) Environment & Flow Modifiers

| Feature | Current | Notes / Evidence | SDD Upgrade Need |
|---|---|---|---|
| Natural features / terrain | Partial | abstract barrier only | terrain/elevation/river geometry 확장 필요 |
| Greenery / parks | No | 없음 | parks/green-space land-use + POI extensions |
| Parking (lot/garage/on-street) | No | 없음 | parking supply + access/route effects 모델 필요 |
| Weather/environment modifiers | No | 없음 | optional future event/environment system 확장 |

## 6) Major Destinations & Landmarks (POI)

| Feature | Current | Notes / Evidence | SDD Upgrade Need |
|---|---|---|---|
| Generic POIs (home/workplace/leisure) | Yes | `POIType` supports home/workplace/leisure | POI density scaling/variety 보강 |
| Essential facilities (hospital/school/etc.) | No | typed facilities 없음 | POI taxonomy + demand rules 필요 |
| Leisure landmarks / attractions | Partial | generic `leisure`만 존재 | landmark/capacity/attractor classes 필요 |
| Civic/administrative landmarks | No | 없음 | POI taxonomy 확장 필요 |
| Freight/logistics destinations | No | 없음 | optional industrial/freight extension 정의 필요 |

## 7) Readiness Classification (Checklist Summary)

### Good enough now (baseline road traffic prototype)
- Arterial / local / expressway hierarchy (without collector)
- Bridges/barrier concept (but chokepoint realism validation needs strengthening)
- Basic ramp/interchange node kinds
- Coarse zoning + generic POIs (home/workplace/leisure)

### Not realistic enough yet (100k transit/metro realism target)
- Collector roads and richer intersection taxonomy
- Curved / terrain-adaptive geometry
- Fine-grained density zoning and industrial separation rules
- Transit lines/stations/transfers/headways
- Passenger boarding/alighting/waiting/transfer behavior
- Pedestrian infrastructure and access network
- Parks/parking/environment modifiers
- Essential facilities and landmark-specific POIs

## 8) How to Use This Checklist in spec-kit Upgrades

권장 방식:
1. `clarify`: 어떤 항목을 transit realism MVP에 포함할지 범위 결정
2. `specify`: 위 표의 `No/Partial` 항목 중 이번 phase에 포함할 항목을 FR/SC로 수치화
3. `plan`: 포함된 항목에 대한 data-model/module boundary/JAX-perf 전략 설계
4. `tasks`: 체크리스트 항목별 문서/테스트/구현 task를 단계적으로 분해

주의:
- 한 번에 전부 포함하지 말 것
- baseline road-only MVP 회귀 금지
- “현실성” 표현은 수치/검증 기준으로 환원할 것

