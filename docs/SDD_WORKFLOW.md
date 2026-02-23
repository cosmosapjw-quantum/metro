# SDD Workflow (spec-kit + Codex) — MetroFlow

이 레포는 GitHub spec-kit의 SDD 흐름을 그대로 따른다: constitution → specify → plan → tasks → implement.

## A. 부트스트랩
1) specify-cli 설치
- `uv tool install specify-cli --from git+https://github.com/github/spec-kit.git`

2) 템플릿 주입(이미 레포에 파일이 있으면 `--force` 주의)
- `specify init . --ai codex --script sh --force`

이 작업은 `.specify/`(memory/templates/scripts)와, feature별 `specs/<id-...>/` 산출물을 만드는 데 필요한 골격을 넣는다.

## B. 문서 생성 순서
1) `/speckit.constitution`
- 코딩 규율/테스트/성능 목표/학습 금지(외부 데이터) 등 프로젝트 “헌법”을 확정

2) `/speckit.specify`
- 제품/행동 요구사항(what/why)을 **PRD 수준으로** 충분히 구체화(스택 이야기는 최소)

3) `/speckit.plan`
- 기술 설계(어떻게 만들지): 데이터 모델, 모듈 경계, JAX 텐서화 전략, 시각화 전략

4) `/speckit.tasks`
- plan을 작업 단위로 쪼갠 task list 생성(각 task는 작고, 검증 가능하게)

5) `/speckit.implement`
- tasks를 순서대로 구현

## C. Codex CLI 팁
- `/review`로 diff 기반 코드리뷰를 걸어라
- “한 번에 RL+GNN+LSTM 완성” 금지: 먼저 baseline(동적 퍼텐셜) → bandit → 작은 policy net 순으로.

