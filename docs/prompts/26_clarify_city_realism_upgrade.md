# 26 — /speckit.clarify 프롬프트(현실성 기준 수치화 질문)

아래를 그대로 입력:

/prompts:speckit.clarify
`specs/001-adaptive-traffic-sim/`를 100k synthetic city + transit/metro realism 방향으로 업그레이드하려고 한다.
specify/plan/tasks를 업데이트하기 전에 아래 항목을 먼저 명확히 하고 싶다.

명확화 질문(답변을 스펙에 반영할 수 있게 수치/범위 중심으로):
1. 100k 도시에서 최소 해상도 기준은?
- node/link/zone/POI/station의 최소 또는 권장 범위
2. bridge/barrier “구조적 chokepoint”의 정의는?
- closure 시 연결성 분리 or 평균 경로비용 증가율 같은 기준
3. transit realism MVP 범위는 어디까지인가?
- station/line/headway만?
- 승하차/대기/환승 포함?
- 차량 운영/적재율까지 포함?
4. 멀티모달 경로 선택에서 baseline 단계에 필요한 최소 동작은?
- walk-access + transit line + walk-egress 수준인지
- road/transit 혼합 대체까지 요구하는지
5. 성능 목표는 road-only와 multimodal 각각 어떻게 둘 것인가?
- 예: 동일 hardware에서 target tick rate/active agents/passengers

제약:
- 외부 지도/GTFS 없음
- JAX-first 유지
- baseline road-only MVP는 유지

