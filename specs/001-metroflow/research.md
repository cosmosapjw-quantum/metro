# Research / Decisions Log

## Decision: 메조 엔진을 기본으로(링크 큐)
- 이유: 100k 규모에서 미시(IDM/차량추종)는 비용이 너무 큼
- tradeoff: 충격파/정밀 현상은 약함 → 옵션(CTM)으로 남김

## Decision: 학습은 bandit → policy net 순서
- 이유: 외부 데이터 없이 online RL은 불안정
- bandit은 안정적이며 “우회로 활성화”라는 목적에 충분히 기여 가능

## Decision: baseline fallback
- 이유: 학습 정책이 망가져도 게임 플레이가 깨지면 안 됨
- 구현: 혼잡 악화/비정상 검출 시 λ→0

## Open questions
- 후보 경로 K를 어떻게 생성/갱신할지(도시가 바뀌면 재생성 필요)
- 교차로 신호 모델의 단순화 수준(우선순위/고정 cycle vs adaptive)
- 시각화에서 edge 수가 많을 때의 효율적 downsample 방식

