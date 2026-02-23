# Plan — 001 MetroFlow (JAX-first)

## Tech stack
- Python 3.11+
- JAX (CPU/GPU)
- Visualization MVP: pyqtgraph (옵션: WebSocket+Canvas)

## Modules
- `metroflow/citygen/` : 가상 도시 그래프/존/랜드마크 생성
- `metroflow/demand/` : 인구/가구/직장/일정 → trip 생성
- `metroflow/flow/` : 링크큐 + 노드 모델 + 이벤트(사고/공사)
- `metroflow/routing/` :
  - baseline: dynamic potential (periodic shortest path on congestion-weighted costs)
  - learning: bandit(OD-path) → policy_net(GNN+LSTM) 플러그인
- `metroflow/viz/` : 렌더러 + UI(시간/요일/레이어)
- `metroflow/api/` : 게임 연동을 위한 step/reset/observe 인터페이스

## Data model (high-level)
- Graph:
  - nodes V, edges E (directed)
  - out_edges_ptr[V+1], out_edges[E]
- Edge state:
  - queue_len[E], flow[E], speed[E], capacity[E], length[E], free_flow_time[E]
- Agent state (active only):
  - edge_id[A], progress[A], dest_zone[A], policy_h[A,H], policy_c[A,H], preference[A,K]
- Demand:
  - household_id[N], job_id[N], home_zone[N], work_zone[N]
  - schedule templates by day_type/time_of_day

## Update loops
- tick(dt=0.1~0.5s):
  1) spawn trips (based on schedule + time)
  2) update edge queues / node flows (vectorized)
  3) advance agents along edges; at nodes choose next edge (baseline/policy mix)
  4) record stats; emit viz packet (throttled)

## Learning plan
- MVP: OD별 후보 경로 K개를 생성(초기엔 k-shortest or perturbation) 후 UCB/Thompson으로 선택
- v1: Graph encoder(GNN)로 node/edge embedding을 만들고, per-agent LSTM hidden으로 “습관”을 표현.
  - 학습은 online actor-critic or supervised-on-advantages(보수적)
  - 안정장치: baseline fallback + KL penalty + reward clipping

## Visualization plan
- renderer process/thread 분리
- packet: time, heatmap(HxW), topK congested edges(list), optional sampled vehicles
- UI: 시간 슬라이더 + 평일/주말 토글 + 레이어 토글

