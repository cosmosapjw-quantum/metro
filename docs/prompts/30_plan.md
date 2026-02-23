# 30 — /speckit.plan 프롬프트(기술 계획)

아래를 그대로 입력:

/speckit.plan
기술 요구:
- Python 3.11+, JAX를 핵심으로 사용(jit/vmap/segment ops).
- 인구 100k를 유지하되 매 tick 전체를 업데이트하지 말고, 이동 중인 active agent만 packed array로 관리.
- 교통 엔진은 기본으로 link-queue + node model(교차로 턴/신호 단순화). CTM은 옵션.
- 라우팅은 안전한 baseline(혼잡 반영 동적 퍼텐셜) + 학습 정책(online) 혼합.
- 학습은 안정성을 우선: 먼저 OD별 bandit/UCB(경로 후보)로 시작하고, 확장으로 GNN+LSTM 정책을 플러그인 형태로 설계.
- 시각화는 pyqtgraph(프로토타입) 또는 WebSocket+Canvas(WebGL) 중 하나로 계획하고, 코어 루프를 막지 않게 throttling/downsample 설계.
- 테스트: 보존량/음수 queue/용량 위반, 시간대/요일 전환, 재현성(seed) 포함.
산출물:
- 모듈 경계, 데이터 모델, 시뮬 스텝 함수 시그니처, 성능 목표/벤치, UI 데이터 패킷을 문서화.
