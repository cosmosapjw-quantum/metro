# MetroFlow — Self-Learning, Active-Matter-Inspired Traffic for City-Builders (JAX-first)

이 저장소는 “시티즈 스카이라인 2급” 도시(인구 ~10만)에서 **시민 개별 스케줄/주소 기반 agent**를 유지하면서도,
최단거리 고정 루틴으로 인한 비현실(우회로 무력화, 한두 간선 과집중 등)을 줄이기 위한
**자기학습형(외부 데이터 없이) 교통 시뮬레이션 보조 엔진**의 SDD(=spec-kit) 문서 + 개발 가이드 + 프롬프트 세트 번들이다.

핵심 아이디어
- 미시: 시민(드라이버)을 agent로 보되, **동일 policy 공유 + 개인 메모리(LSTM state)**만 유지해서 비용을 억제
- 중시/메조: 도로는 **link-queue / node model**로 업데이트(CTM 수준까지는 필요 시 옵션화)
- 내비게이션: **(동적 퍼텐셜) + (학습 policy)** 혼합. 학습은 온라인/자기강화로 천천히 진화
- 계산: JAX `jit` + `vmap` + (선택) `pmap/pjit`로 텐서화/병렬화

빠른 시작
1) spec-kit 초기화(권장)
- `uv tool install specify-cli --from git+https://github.com/github/spec-kit.git`
- `specify init . --ai codex --script sh --force` (이미 레포가 있다면 `--force` 주의)

2) Codex CLI 사용 시
- 루트의 `AGENTS.md`를 읽고 진행하도록 되어 있음(프로젝트 규율/워크플로우 포함)

3) 데모/검증 실행(ROCm 컨테이너 필수)
- `docker build -f Dockerfile.rocm -t metroflow:rocm .`
- `./scripts/in_docker.sh pip install --no-deps -e .`
- `./scripts/in_docker.sh python -m metroflow.demo`
- `./scripts/in_docker.sh pytest -q`

주의
- Python/JAX 기반 실행(데모, 테스트, 포매팅)은 호스트가 아니라 ROCm 컨테이너에서 수행한다.

GUI 확장 1차 범위(요약)
- 단일 인터랙티브 클라이언트 + 로컬호스트 실행만 지원(원격/LAN 및 인증은 후속 단계)
- 기본 패널: map(congestion), metrics summary, timeline, command log/ACK
- 기본 업데이트 모드: `every N ticks` (N 설정 가능)
- 벤치마크 수용 기준: tick-rate + dropped/coalesced frame 지표 동시 확인
- GUI 변경 PR: 최소 screenshot 1장 첨부(영상은 선택)

문서
- `docs/PRD.md` : 제품 요구사항(PRD)
- `docs/DOCS_MANIFEST.md` : 구현 기준 문서 인덱스(진실 원천)
- `docs/SDD_WORKFLOW.md` : spec-kit + Codex로 SDD 진행 절차
- `specs/001-adaptive-traffic-sim/` : spec/plan/tasks + 부속 문서(quickstart, data-model 등)
- `docs/prompts/task-runner-prompts.md` : Task 실행 자동화 프롬프트
