# 22 — /speckit.specify 프롬프트(100k 도시/대중교통 현실성 업그레이드)

아래를 그대로 입력:

/prompts:speckit.specify
기존 feature `specs/001-adaptive-traffic-sim/`는 baseline 도로교통 MVP 중심으로 잘 정의되어 있다.
이번에는 **기존 baseline을 유지**하면서, “인구 100k급 도시에서 현실성 있는 대중교통/메트로 시뮬레이션까지 확장 가능한 요구사항”으로 spec를 업그레이드하고 싶다.

중요 제약:
- 기존 baseline road-only MVP 요구사항/데모 목표는 유지한다 (깨지 말 것)
- 외부 GIS/GTFS/실지도 데이터는 사용하지 않는다 (synthetic city 유지)
- JAX-first 성능 목표와 online-only learning 원칙 유지
- 구현 코드는 아직 만들지 않고, 문서(spec)만 개선한다

현재 지도 생성의 한계(반영 필요):
- 도로 계층/장벽/교량은 있으나 transit/metro 엔티티가 없다
- 100k 대비 node/POI/zone 해상도가 너무 낮다
- zone이 4개(각 타입 1개) 수준이라 OD 다양성이 부족하다
- bridge가 구조적 chokepoint로 충분히 작동하지 않는다(폐쇄 시 우회가 너무 쉬움)
- 지도 형태가 지나치게 규칙적/대칭적이다

spec 업그레이드 목표:
- baseline road-only scope vs transit/metro realism extension scope를 명확히 분리
- “현실성”을 계량 가능한 요구사항/성공 기준으로 바꾼다
- synthetic city + multimodal(road/transit/access) 요구사항을 추가한다
- 100k city에 맞는 최소 공간 해상도(노드/존/POI/역) 기준을 정의한다
- bridge/barrier 병목의 구조적 임계성 기준(closure sensitivity)을 정의한다
- UI/관측 측면에서 transit layer/혼잡/승하차/역 혼잡 summary 요구를 phase-gated로 정의한다

산출물 작성 지시:
- `spec.md`의 기존 구조를 최대한 유지하되, 작은 diff로 섹션을 추가/보강하라
- FR/NFR/Success Criteria를 업데이트하라
- baseline과 확장 범위를 혼동하지 않도록 명시적 scope labels를 넣어라
- 추상 문구 대신 수치/검증 기준을 가능한 한 넣어라

