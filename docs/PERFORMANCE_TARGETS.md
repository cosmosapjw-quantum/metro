# Performance Targets

이 문서는 MetroFlow의 benchmark 목표와 PR/review용 보고 규약을 정리한다.
기준은 “정밀 교통 공학”보다 “플레이 가능한 synthetic city simulation”이다.

## Runtime Scope
- 기본 benchmark 기준 시나리오: `synthetic_100k`
- 기본 population target: `100_000`
- 기대 active-agent band: `10_000` ~ `30_000`
- 실행 환경 기준: ROCm container 내부 실행
- baseline/adaptive 비교는 같은 container image, 같은 GPU/CPU, 같은 seed, 같은 시나리오 조건에서만 유효

## Tick Targets
- road-only baseline 목표: median `2` ~ `10` Hz
- minimum acceptable road-only baseline: median `>= 2` Hz
- adaptive routing benchmark는 road-only와 같은 시나리오 조건에서 별도 측정
- UI stream은 benchmark 대상이더라도 core loop를 막지 않아야 하며, frame drop/coalescing은 허용

## Required Metrics
벤치마크 보고에는 아래 값이 포함되어야 한다.

- `scenario_id`
- `seed`
- `population_target`
- `active_agent_median`
- `active_agent_p95`
- `duration_ticks`
- `duration_seconds`
- `tick_rate_median`
- `tick_rate_p10`
- `invariant_violation_counts`
- `event_mix`
- `ui_mode`
- `environment`

현재 구현 기준 source of truth:
- runner metric capture: `src/metroflow/benchmarks/run.py`
- review/report formatting: `src/metroflow/benchmarks/reporting.py`

## Reporting Conventions
- tick rate는 Hz 단위로 기록한다.
- 대표 성능치는 mean이 아니라 median / p10을 쓴다.
- invariant count는 빈 dict 대신 명시적 key/value 집합으로 남기는 것을 우선한다.
- baseline vs adaptive 비교에서는 `event_mix`를 각각 `baseline_only`, `adaptive_od_ucb`처럼 분리한다.
- demo/PR 로그에는 absolute scenario/seed를 함께 남긴다.
- 성능 주장은 반드시 측정값과 실행 조건을 같이 적는다.

## Standard Commands
기본 smoke/benchmark 명령은 아래를 기준으로 한다.

```bash
./scripts/in_docker.sh python -m metroflow.demo \
  --scenario synthetic_100k \
  --seed 42
```

```bash
./scripts/in_docker.sh python -m metroflow.benchmarks.run \
  --scenario synthetic_100k \
  --seed 42 \
  --duration-ticks 3600
```

adaptive benchmark 예시:

```bash
./scripts/in_docker.sh python -m metroflow.benchmarks.run \
  --scenario synthetic_100k \
  --seed 42 \
  --duration-ticks 3600 \
  --learning-enabled
```

## Review Template
- Scenario ID:
- Seed:
- Population target:
- Active agent median/p95:
- Duration (ticks / real time):
- Median tick rate (Hz):
- p10 tick rate (Hz):
- Invariant violations (counts):
- Event mix (if any):
- UI mode (off / stream):
- Environment (ROCm container image + GPU/CPU):

## Notes
- adaptive 성능 보고는 baseline 대비 비교값을 붙이되, baseline run 자체를 생략하지 않는다.
- reproducibility 이슈가 있으면 성능 수치보다 먼저 seed/scenario/environment mismatch를 확인한다.
- `jit` 가능한 수치 core와 host-side reporting은 분리해 유지한다. benchmark runner는 host-orchestrated tail stage다.
