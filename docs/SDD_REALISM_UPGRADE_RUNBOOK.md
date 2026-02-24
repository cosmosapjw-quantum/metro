# SDD Realism Upgrade Runbook (spec-kit + Codex)

목적:
- `specs/001-adaptive-traffic-sim/` 문서군을
- “baseline road-only MVP”에서 “100k synthetic city + transit/metro realism 확장 가능” 형태로 업그레이드하는 데 필요한
- **프롬프트 실행 순서와 운영 방법**을 정리한다.

이 문서는 **문서 업그레이드용**이다. 구현 코드는 아직 생성하지 않는다.

## 1) 준비물

1. `specify-cli` 설치 (spec-kit)
- `uv tool install specify-cli --from git+https://github.com/github/spec-kit.git`

2. spec-kit 초기화(레포에 이미 있으면 생략 가능)
- `specify init . --ai codex --script sh --force`

3. 작업 브랜치 권장
- 예: `git checkout -b docs/001-sdd-realism-upgrade`

## 2) 입력 자료 (권장)

프롬프트 실행 전에 아래 문서를 열어두면 좋다:
- `specs/001-adaptive-traffic-sim/city-map-realism-assessment.md`
- `specs/001-adaptive-traffic-sim/city-map-realism-sdd-upgrade-plan.md`
- `specs/001-adaptive-traffic-sim/city-feature-realism-checklist.md`
- 기존 SDD 문서:
  - `specs/001-adaptive-traffic-sim/spec.md`
  - `specs/001-adaptive-traffic-sim/plan.md`
  - `specs/001-adaptive-traffic-sim/data-model.md`
  - `specs/001-adaptive-traffic-sim/tasks.md`

## 3) 실행 순서 (권장)

### Step A0. Checklist scope framing (optional but strongly recommended)
- 목적: 현실성 체크리스트 항목의 phase별 포함/제외 기준을 먼저 정리
- 입력 문서: `specs/001-adaptive-traffic-sim/city-feature-realism-checklist.md`
- 사용 프롬프트 파일(옵션):
  - `docs/prompts/28_clarify_city_feature_checklist_scope.md`

실행:
1. 체크리스트 문서를 열고 `Yes/Partial/No` 항목을 확인
2. 필요하면 위 clarify 프롬프트를 붙여넣어 scope-in/out 기준을 정리
3. 합의 결과를 이후 `specify/plan/tasks` 입력으로 사용

### Step A. Clarify (optional but recommended)
- 목적: “현실성”을 수치 기준으로 확정
- 사용 프롬프트 파일: `docs/prompts/26_clarify_city_realism_upgrade.md`

실행:
1. Codex/CLI에서 `/speckit.clarify` 실행 컨텍스트 준비
2. 위 프롬프트 파일 내용을 그대로 붙여넣기
3. 나온 질문/합의사항을 `spec.md` 업데이트 입력으로 사용

### Step B. Specify upgrade
- 목적: `spec.md` 요구사항/성공기준 업그레이드
- 사용 프롬프트 파일: `docs/prompts/22_specify_city_realism_upgrade.md`
- 체크리스트 중심 대안 프롬프트(옵션): `docs/prompts/24_specify_city_feature_checklist_upgrade.md`

실행:
1. 프롬프트 파일 내용을 붙여넣고 `/speckit.specify` 실행
2. 출력 diff에서 다음을 확인:
- baseline road-only scope 유지 여부
- transit/metro extension scope 분리 여부
- 수치화된 realism criteria 추가 여부

### Step C. Plan upgrade
- 목적: `plan.md` 아키텍처/성능/JAX/검증 전략 보강
- 사용 프롬프트 파일: `docs/prompts/32_plan_city_realism_upgrade.md`
- 체크리스트 중심 대안 프롬프트(옵션): `docs/prompts/34_plan_city_feature_checklist_upgrade.md`

실행:
1. 프롬프트 파일 내용을 붙여넣고 `/speckit.plan` 실행
2. 출력 diff에서 다음을 확인:
- transit module boundary 추가 여부
- JAX per-tick vs Python init generator 분리 전략
- realism validation metrics 설계 반영 여부

### Step D. Tasks upgrade
- 목적: `tasks.md`에 문서/테스트/구현 작업을 단계적으로 추가
- 사용 프롬프트 파일: `docs/prompts/42_tasks_city_realism_upgrade.md`
- 체크리스트 gap 기반 대안 프롬프트(옵션): `docs/prompts/44_tasks_city_feature_checklist_upgrade.md`

실행:
1. 프롬프트 파일 내용을 붙여넣고 `/speckit.tasks` 실행
2. 출력 diff에서 다음을 확인:
- 문서 task 선행 여부
- 테스트 선행 여부
- road realism 개선과 transit 기능 task 분리 여부
- 완료 조건(`pytest`, smoke, benchmark`) 명시 여부

## 4) Codex에서 프롬프트 실행하는 실전 팁

1. 한 번에 다 하지 말고 단계별로 commit
- `spec.md` 업그레이드
- `plan.md`/`data-model.md` 업그레이드
- `tasks.md` 업그레이드
- (옵션) 체크리스트 문서 업데이트

2. 각 단계마다 `/review`
- 특히 다음 관점으로 요청:
- scope regression (baseline MVP 깨짐 여부)
- measurable criteria 부족 여부
- task sequencing/검증 가능성

3. 작은 diff 원칙 유지
- 전면 리라이트 대신 섹션 추가/보강
- 기존 task 번호 체계를 가능한 한 보존
4. 체크리스트를 진실 원천으로 사용
- `city-feature-realism-checklist.md`의 `No/Partial` → spec/plan/tasks 반영 여부를 추적
- 이번 phase 제외 항목은 spec/tasks에 명시적으로 defer 표시

## 5) 검토 체크리스트 (문서 업그레이드 완료 판정)

- `spec.md`:
- baseline vs transit/realism scope 분리
- FR/NFR/SC 수치화

- `plan.md`:
- transit 모듈 경계
- JAX/perf 전략
- realism validation 전략

- `data-model.md`:
- transit entity skeleton
- multimodal state/route 개념 반영

- `tasks.md`:
- 문서/테스트 선행
- road realism vs transit 기능 분리
- 완료 조건 명시

## 6) Suggested Command Snippets (Local Workflow)

문서 변경 후:
- `git diff -- specs/001-adaptive-traffic-sim docs/prompts docs/SDD_REALISM_UPGRADE_RUNBOOK.md`
- `git status --short`

리뷰 요청 예시:
- `/review 방금 생성한 spec/plan/tasks 문서 diff를 검토해줘. scope regression, 측정가능성, task sequencing 관점으로`

## 7) Important Constraints to Re-State in Every Prompt

- baseline road-only MVP 유지 (regression 금지)
- synthetic city 유지 (외부 지도/GTFS 없음)
- JAX-first + reproducibility 유지
- 구현 코드는 아직 하지 않고 SDD 문서만 수정

## 8) Prompt Set Selection Guide (When to Use Which)

### A. Metrics-first upgrade path (기본)
사용 프롬프트:
- `26_clarify_city_realism_upgrade.md`
- `22_specify_city_realism_upgrade.md`
- `32_plan_city_realism_upgrade.md`
- `42_tasks_city_realism_upgrade.md`

적합한 경우:
- 해상도/성능/bridge criticality/멀티모달 최소동작 같은 수치 기준을 먼저 정하고 싶을 때

### B. Feature-checklist-first upgrade path (추가)
사용 프롬프트:
- `28_clarify_city_feature_checklist_scope.md` (옵션)
- `24_specify_city_feature_checklist_upgrade.md`
- `34_plan_city_feature_checklist_upgrade.md`
- `44_tasks_city_feature_checklist_upgrade.md`

적합한 경우:
- “collector road, curved roads, parks, parking, landmarks, pedestrian infrastructure”처럼
  기능 카탈로그 관점에서 scope-in/out과 phase 분리를 하고 싶을 때

권장 운영:
- A path로 수치 기준을 먼저 확정한 뒤, B path로 기능 누락을 점검/보강
