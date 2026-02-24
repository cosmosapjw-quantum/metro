# 34 — /speckit.plan 프롬프트(체크리스트 항목 기반 기술 계획 보강)

아래를 그대로 입력:

/prompts:speckit.plan
`specs/001-adaptive-traffic-sim/city-feature-realism-checklist.md`와 현재 `spec.md` 명확화 결과를 반영해,
`plan.md`를 체크리스트 기반으로 보강하라.

계획에 반드시 포함할 항목:
- Road generator 확장 경계:
  - collector road 추가 여부
  - curved/polyline geometry 모델 여부
  - terrain/barrier abstraction 수준
- Junction/intersection taxonomy 확장 계획
- Zoning/Land-use 확장 계획:
  - density zoning
  - subdistrict/mixed-use granularity
  - industrial separation constraints
- Transit/active travel 모듈 경계:
  - station/line/service/headway
  - transfer nodes
  - pedestrian access graph vs walk-time proxy
- Environment modifiers:
  - parks/parking/terrain를 어떤 phase에 넣을지
- POI taxonomy 확장:
  - essential facilities / landmarks / leisure classes

작성 규칙:
- one-time generator 단계와 per-tick JAX kernel 단계를 분리
- baseline road-only 성능 목표와 multimodal 목표를 분리
- checklist 항목별로 “이번 phase 포함 / 후속 phase”를 명시
- 기존 `plan.md` 구조는 유지하고 addendum 방식의 작은 diff로 작성

