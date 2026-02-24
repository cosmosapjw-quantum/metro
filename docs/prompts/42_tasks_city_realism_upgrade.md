# 42 — /speckit.tasks 프롬프트(현실성/대중교통 확장 task 분해)

아래를 그대로 입력:

/prompts:speckit.tasks

목표:
- 기존 baseline road-only task 흐름을 유지하면서,
- 100k synthetic city realism + transit/metro 확장을 위한 문서/테스트/구현 task를 신규 phase 또는 user story로 추가한다.

분해 규칙:
- 작은 diff, 작은 task, 검증 가능(task마다 완료 조건 명시)
- 문서 업데이트(spec/plan/data-model/contracts) task를 먼저 두고
- 테스트를 구현보다 먼저 둔다
- baseline road generator 개선(현실성 지표)과 transit 기능 도입을 분리한다
- 성능/벤치 태스크는 road-only vs multimodal을 분리해 작성한다

반드시 포함할 task 그룹:
- topology realism metrics tests (node/link/zone/poi thresholds, bridge criticality)
- zoning/POI scaling tests (population target 연동)
- transit network data-model/contracts 문서 업데이트
- transit network/station/line generation tests and implementation
- passenger access/boarding/alighting/transfer baseline tests and implementation
- multimodal routing candidate integration tests and implementation
- UI transit overlay packet/schema tests and implementation
- benchmark/report tasks (road-only baseline vs multimodal)

출력 형식 지시:
- 각 task에 파일 경로를 넣어라
- 완료 조건에 `pytest -q` 또는 대상 테스트, 데모/스모크, 성능 스모크를 명시하라
- baseline 기존 task 번호는 되도록 유지하고, 확장 task는 신규 번호로 추가하라

