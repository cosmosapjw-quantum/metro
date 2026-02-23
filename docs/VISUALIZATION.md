# Visualization (실시간 지도/네비게이터 스타일)

목표: “미적”보다 **읽히는 UI**. 실시간/시간대 토글/주말 토글을 지원.

## 1) 렌더링 레이어(권장 순)
A. Python 프로토타입(빠른 개발)
- `pyqtgraph`:
  - 도로망: line segments
  - 링크 혼잡: 색/두께
  - 주요 OD 흐름: 애니메이션 화살표(선택)
- 장점: 대규모 점/선 업데이트가 비교적 빠름, 의존성 가벼움

B. 웹 기반(배포/플레이어 친화)
- Python backend + WebSocket
- Frontend: Canvas/WebGL(Deck.gl 같은 대형 렌더러)
- 장점: UI 구성(시간 슬라이더/토글/레이어) 쉬움

C. 게임 엔진 연동
- 엔진(유니티/언리얼)의 UI 레이어로 교통량/혼잡 텍스처를 푸시
- Python은 코어만, 렌더는 엔진이 담당

## 2) 데이터 인터페이스
- “프레임”마다 전량 송신 금지.
- downsample / throttling:
  - 도로 링크 혼잡: E개 중 주요 링크만 또는 타일 heatmap으로 압축
  - 차량 점: 표본(sampling) 또는 “밀도 필드”로 표시

권장 패킷:
- time: (day_type, minutes)
- links: {edge_id -> (flow, density, speed)} (top-K 혹은 타일 bin)
- heatmap: (H,W) float (혼잡/속도)
- events: 사고/공사/신호 변경

## 3) 시간대/요일 모델
- day_type ∈ {WEEKDAY, WEEKEND}
- time_of_day: 0..1440 분
- UI:
  - 상단: 시간 슬라이더 + play/pause + x1/x4/x16
  - 토글: 평일/주말(또는 주간 캘린더)
  - 레이어: (혼잡, 평균속도, 흐름, 사고)

## 4) 최소 MVP UI
- 배경: 도시 구획(존) + 주요 간선(대로/고속도로/다리)
- 오버레이: 링크 혼잡 색상 + 노드 병목 강조
- 패널: 평균 통근시간, 상위 병목 10개, OD별 통행량

