# 24 — /speckit.specify 프롬프트(도시 기능 체크리스트 기반 업그레이드)

아래를 그대로 입력:

/prompts:speckit.specify
`specs/001-adaptive-traffic-sim/city-feature-realism-checklist.md`를 입력 근거로 사용해,
기존 `specs/001-adaptive-traffic-sim/spec.md`를 **도시 기능 현실성 체크리스트 관점**에서 업그레이드하라.

핵심 목표:
- 현재 `No/Partial` 항목 중 이번 phase(100k synthetic city + transit/metro realism MVP)에 포함할 항목을 명확히 scope-in/out 한다.
- baseline road-only MVP는 유지하고 회귀시키지 않는다.
- 포함한 항목은 FR/Success Criteria에서 계량 가능하게 정의한다.

반드시 반영할 주제(체크리스트 기반):
- Road types: collector road 포함 여부
- Geometry realism: curved roads / terrain-adaptive curves 포함 여부(phase-gated 가능)
- Junction realism: intersection taxonomy 확장 범위
- Zoning/Land use: density zoning, mixed-use granularity, industrial separation
- Transit/Active travel: line-based transit, transfer nodes, pedestrian access
- Environment modifiers: terrain, parks/greenery, parking (scope-in/out 명시)
- POI taxonomy: essential facilities / landmarks / leisure 다양화

작성 지시:
- `spec.md` 전면 리라이트 금지, 작은 diff 우선
- `Assumptions & Scope Boundaries`에 이번 phase 제외 항목을 명확히 적어라
- `Success Criteria`는 “관찰 가능” + “측정 가능” 기준으로 바꿔라
- 모호한 표현(현실적/풍부한/자연스러운)을 수치/판정 기준으로 치환하라

