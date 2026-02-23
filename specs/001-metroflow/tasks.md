# Tasks — 001 MetroFlow

## Phase 0 — Repo + skeleton
- [T-000] 프로젝트 스켈레톤(pyproject, src layout, ruff/pytest) 만들기
- [T-010] core API: reset/step/observe 시그니처 정의 + 더미 구현
- [T-020] 시드/PRNGKey 재현성 유틸

## Phase 1 — City generator (가상 도시)
- [T-100] hierarchical road graph 생성(소로/대로/고속도로/환상+방사)
- [T-110] 강/장벽 + 3~5개 다리(병목) 생성
- [T-120] 존 생성(주거/상업/CBD/공업/혼합) + POI 배치

## Phase 2 — Demand (인구 100k)
- [T-200] 가구/직장/POI 샘플링(존 기반)
- [T-210] 평일/주말 + 시간대 schedule 템플릿
- [T-220] 트립 생성기(spawn queue) + active agent allocator

## Phase 3 — Flow engine (메조)
- [T-300] link-queue 모델(큐 업데이트, travel time)
- [T-310] node model(턴/신호 단순화)
- [T-320] 사고/공사 이벤트(간선 capacity 감소)

## Phase 4 — Routing baseline
- [T-400] 혼잡 반영 cost 계산 + 주기적 shortest path potential
- [T-410] baseline 내비 + stochasticity(softmin)로 분산

## Phase 5 — Online learning (safe-first)
- [T-500] OD별 후보 경로 K 생성(초기 k-shortest)
- [T-510] bandit(UCB/Thompson) 라우팅(online)
- [T-520] 안전장치(학습 실패 시 baseline fallback)

## Phase 6 — Viz MVP
- [T-600] pyqtgraph 렌더러(도로망 + 혼잡 레이어)
- [T-610] 시간 슬라이더 + 평일/주말 토글 + play/pause
- [T-620] top bottlenecks panel(상위 10개 링크)

## Phase 7 — Policy net plugin (GNN + LSTM) [stretch]
- [T-700] graph encoder(간단한 message passing) + node embedding 캐시
- [T-710] per-agent LSTM state + action head
- [T-720] 보수적 online 업데이트(클리핑/KL) + 평가 리포트

각 task의 완료 조건은 구현 시 구체화:
- 테스트 추가
- 데모 스모크(인구 100k, 1~5분 시뮬)
- step latency 측정(간단 벤치)

