# AGENTS.md — MetroFlow Repo Instructions (Codex)

이 파일은 Codex가 작업 시작 전에 읽는 “프로젝트 규율/가이드”다.

## 0) 큰 원칙
- SDD 우선: spec -> plan -> tasks -> implement 순서를 깨지 말 것
- 큰 리라이트 금지: 작은 diff, 작은 task, 빠른 테스트
- 성능은 “증거 기반”: 프로파일/벤치/측정 없이 성능 주장 금지
- 외부 데이터 학습 금지: 학습은 시뮬레이터 내부 경험(online)만 사용
- 결정은 문서화: trade-off는 `specs/001-metroflow/research.md`와 `docs/ARCHITECTURE.md`에 남길 것

## 1) 개발 모드
- Python 3.11+ / uv / ruff / pytest 기준
- JAX-first: 핵심 루프는 가능한 `jit` 가능 형태로 설계
- 랜덤성은 PRNGKey로 관리(재현성)

## 2) 코드 품질
- 타입힌트(최소한 public API) + docstring
- 테스트: 핵심 불변량(차량/agent 보존, 음수 queue 금지, capacity 상한 등)부터
- 경계 조건: 주말/평일, 시간대 전환, 막힌 간선(공사/사고) 등

## 3) 작업 방식
- 먼저 `specs/001-metroflow/tasks.md`의 다음 task를 선택
- 구현 전: 관련 문서(특히 plan/data-model) 위치를 task 내에 링크/참조
- 구현 후: `pytest -q` + 최소한의 성능 스모크(예: 1분 시뮬 100k 도시) 실행
- 필요하면 `/review`(Codex CLI)로 diff 리뷰 수행

## 4) 금지/주의
- “한 번에 다 만들기” 금지(특히 RL/GNN/LSTM 전체를 한 번에)
- 도시 생성기와 교통 엔진을 강결합하지 말 것(그래프/수요/유량 레이어 분리)
- 시각화는 core loop를 막지 않게(비동기 큐/다운샘플/프레임 스킵)
