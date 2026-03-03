# Architecture Notes (JAX-first)

## 1) 3-레이어 분해
1. City Layer: 그래프(노드/링크), 존(land-use), 랜드마크, 이벤트(공사/사고)
2. Demand Layer: 인구/가구/직장/일정 → 트립 생성(OD + depart time)
3. Flow Layer: 링크/노드 유량 업데이트 + agent 상태 업데이트 + 학습

이렇게 나누면:
- 도시 생성기 교체 가능
- 교통 엔진을 다른 게임/도시에도 재사용 가능
- 학습 모듈을 분리해서 안정성/성능 튜닝이 쉬움

## 2) 메조 엔진 기본안(링크 큐 + 노드 모델)
- 각 링크 e에 대해:
  - length, free_flow_speed, capacity, jam_density(옵션)
  - queue_length q_e(t), outflow f_e(t)
- travel_time = free_flow_time + queue_delay(q_e, capacity) (간단한 점-큐)
- 노드(교차로)는 incoming 링크의 demand와 outgoing 링크의 supply를 매칭(신호/우선순위는 파라미터)

장점: 계산이 간단하고 JAX 텐서화가 쉬움.
옵션: 혼잡파(CTM)로 확장할 수 있게 인터페이스만 남김.

## 3) agent 업데이트(비용 억제)
- 인구 100k 전체를 매 tick 업데이트하지 말고,
  “현재 이동 중인 active agents”만 packed array로 관리한다.
- 예: 최대 30k active slot을 잡고 free-list로 재사용.
- agent 상태는 최소화:
  - current_link_id, progress(0..1), dest_zone_id, policy_state(LSTM hidden), preference params

## 4) 라우팅/학습(혼합)
- baseline: 동적 퍼텐셜(혼잡 반영 최단거리) = 안전 정책
- learned policy: 그래프 임베딩(GNN) + 개인 메모리(LSTM) 기반의 “턴 선택”
- 혼합:
  - action_logits = (1-λ) * (-phi_next) + λ * policy_logits
  - λ는 시간에 따라/혼잡도에 따라 조절(초기엔 baseline 위주)

학습은 온라인:
- 가장 단순: OD별 ε-greedy / UCB bandit(경로 후보 K개)
- 확장: actor-critic(advantage는 travel_time baseline 대비 개선) + 작은 MLP/LSTM

## 5) JAX 구현 팁
- 그래프는 “CSR-like” 정적 구조로:
  - `edge_src[E]`, `edge_dst[E]`
  - `out_edges_ptr[V+1]`, `out_edges[E]`
- per-step:
  - 링크 상태 update: `vmap`/segment ops(`jax.ops.segment_sum`)
  - 에이전트-링크 매핑: `edge_id`로 gather/scatter
- 시각화는 별도 스레드/프로세스에서 low-rate로 샘플링

## 6) US3 적응형 라우팅 tradeoff
- baseline routing은 동적 퍼텐셜을 유지하고, adaptive는 OD별 bandit/plugin 계층으로 분리한다.
  - 이유: baseline이 항상 fallback 가능해야 하고, 학습 실패가 core flow update를 막으면 안 된다.
- route candidate / bandit / policy blend는 `routing`/`learning`/`sim.step`로 나눠서 orchestration만 `sim.step`에 둔다.
  - 이유: candidate legality, reward update, fallback telemetry를 각각 독립 테스트 가능하게 유지한다.
- JAX 친화적인 core와 host-side wrapper를 분리한다.
  - 예: UCB update, run-summary delta, benchmark metric 집계는 core 계산 경계를 따로 두고, markdown/report/demo 출력은 host에서 처리한다.
  - 이유: CLI/demo/reporting은 `jit` 대상이 아니지만, 수치 core는 이후 batched/JAX 경로로 재사용할 수 있어야 한다.
- benchmark/demo/reporting은 의도적으로 host-orchestrated tail stage로 둔다.
  - 이유: `time.perf_counter`, markdown formatting, UI packet counting, git/PR용 보고 포맷은 JAX pure step과 관심사가 다르다.
- adaptive mixing telemetry는 “설정된 λ”와 “실제 adaptive 적용”을 구분해서 본다.
  - 이유: fallback tick은 λ가 남아 있어도 실제 결정은 baseline-only일 수 있으므로, observability가 실행 의미를 왜곡하면 안 된다.
