# 28 — /speckit.clarify 프롬프트(체크리스트 항목 scope-in/out 확정)

아래를 그대로 입력:

/prompts:speckit.clarify
`specs/001-adaptive-traffic-sim/city-feature-realism-checklist.md` 기준으로, 100k synthetic city + transit/metro realism MVP에 무엇을 포함/제외할지 먼저 확정하고 싶다.

명확화 질문 방향(수치/범위 중심):
- collector road를 MVP에 포함할지? (road class 확장 vs 후속)
- curved/terrain-adaptive roads를 MVP에 포함할지, 아니면 geometry perturbation 수준으로 제한할지?
- density zoning을 몇 단계(low/med/high 등)로 둘지?
- industrial separation은 거리/완충구역 규칙까지 포함할지?
- transit MVP에 pedestrian access network를 explicit graph로 넣을지, 단순 walk-time proxy로 시작할지?
- parking/parks/landmarks 중 무엇을 MVP에서 제외하고 이후 phase로 넘길지?

제약:
- baseline road-only MVP 유지
- JAX-first 유지
- 외부 지도/GTFS 없음
- 구현 코드 수정 없이 문서 명확화만 진행

