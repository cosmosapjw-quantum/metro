# SDD Realism Upgrade Runbook

목적:
- 단일 SDD 세트(`spec/plan/tasks`)를 기준으로 문서 정합성을 유지한다.
- realistic-map foundation 게이트를 먼저 통과시킨 뒤 시뮬레이터 확장 작업을 진행한다.

## Canonical Docs

- `docs/DOCS_MANIFEST.md` (문서 진실 원천 인덱스)
- `specs/001-adaptive-traffic-sim/spec.md`
- `specs/001-adaptive-traffic-sim/plan.md`
- `specs/001-adaptive-traffic-sim/tasks.md`
- `specs/001-adaptive-traffic-sim/research.md`
- `specs/001-adaptive-traffic-sim/data-model.md`
- `specs/001-adaptive-traffic-sim/quickstart.md`
- `specs/001-adaptive-traffic-sim/contracts/document-reconciliation-report.md`
- `specs/001-adaptive-traffic-sim/reconciliation-quickstart.md`

## Standard Sequence

1. `/speckit.analyze` 로 현행 `spec/plan/tasks` 정합성 확인
2. CRITICAL/HIGH 이슈 정리 후 재분석
3. `tasks.md`에서 다음 task부터 작은 diff로 진행
4. 각 task 완료 시 증거 기록(테스트/스모크/리뷰)

## Prompt Usage

- Task 실행 자동화 프롬프트는 단일 파일만 사용:
  - `docs/prompts/task-runner-prompts.md`

## Constraints

- map-realism-first 순서를 반드시 유지한다.
- `generator.py`/`zones.py`/`render_city_map.py`는 재작성 가능하나
  `synthetic_smoke` 시각 호환성과 핵심 시각 신호는 유지해야 한다.
- Python/JAX 검증은 반드시 `./scripts/in_docker.sh`로 실행한다.
