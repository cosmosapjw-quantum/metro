# 32 — /speckit.plan 프롬프트(도시/대중교통 현실성 확장 기술 계획)

아래를 그대로 입력:

/prompts:speckit.plan
기존 `specs/001-adaptive-traffic-sim/plan.md`는 baseline road traffic 중심 계획이다.
이를 유지하면서, 100k synthetic city + transit/metro realism 확장용 기술계획을 보강하라.

필수 반영사항:
- 기존 아키텍처 분리(city/demand/flow/routing/ui) 유지
- transit 모듈 경계(예: station/line/service/passenger ops)를 명확히 추가
- 도로망 생성기와 zoning/POI 생성기, transit network 생성기의 결합도를 낮춰라
- one-time init generator(파이썬 orchestration)와 per-tick JAX kernel을 분리해서 설계하라
- map realism validation(노드/존/POI density, bridge criticality, morphology 다양성) 지표를 정의하라
- 성능 목표는 road-only baseline과 multimodal 모드를 분리해 측정 계획을 제시하라
- UI 패킷/스냅샷 계약에 transit overlay 확장 포인트를 문서화하라

데이터 모델/계약 측면 요구:
- `data-model.md` 보강이 필요한 transit entity 목록을 plan에서 명시하라
- `contracts/simulation-step.md`와 `contracts/ui-data-packets.md`에 필요한 변경 포인트를 지정하라

작성 방식:
- 기존 plan을 전면 리라이트하지 말고, section addendum/확장 섹션 중심의 작은 diff를 목표로 하라
- JAX-first와 reproducibility(seed/PRNGKey) 원칙은 유지하라

