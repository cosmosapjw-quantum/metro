# 44 — /speckit.tasks 프롬프트(체크리스트 gap 기반 task 분해)

아래를 그대로 입력:

/speckit.tasks

`specs/001-adaptive-traffic-sim/city-feature-realism-checklist.md`의 `No/Partial` 항목을 기반으로,
`tasks.md`에 문서/테스트/구현 task를 단계적으로 추가하라.

분해 원칙:
- baseline road-only task는 유지 (회귀 금지)
- 문서 → 테스트 → 구현 순서
- 작은 diff / 검증 가능 / phase-gated
- 각 task에 파일 경로 + 완료 조건(`pytest`, smoke, benchmark) 명시

반드시 task 후보를 만들 것:
- collector road + junction taxonomy tests/implementation (if scoped-in)
- curved geometry / morphology perturbation tests/implementation (if scoped-in)
- density zoning / industrial separation tests/implementation
- transit station/line/service/headway data-model + generator tests/implementation
- transfer node + passenger boarding/alighting/waiting tests/implementation
- pedestrian access graph (or walk-time proxy) tests/implementation
- POI taxonomy expansion (essential facilities/landmarks) tests/implementation
- parks/parking/environment modifiers (scope-in/out에 따라 phase 분리)

출력 지시:
- checklist 항목과 task를 추적 가능하게 묶어라 (예: 주석/라벨/설명)
- 이번 phase 제외 항목은 `Deferred` 또는 다음 phase 후보로 명시하라

