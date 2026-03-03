# Quickstart (Developer Runbook and Smoke Flows)

This document is the container-first developer runbook for the implemented
road-only MetroFlow MVP. It records the supported command shapes used for smoke
validation, benchmark runs, reproducibility checks, and UI stream checks, plus
phase-gated extension command placeholders for separated road-only vs
multimodal validation/reporting.

## 1) Runtime Requirements (Mandatory)

- Use the ROCm container for Python/JAX commands
- Do not run Python/JAX tests or demos on the host

Build container image:

```bash
docker build -f Dockerfile.rocm -t metroflow:rocm .
```

Install project in container:

```bash
./scripts/in_docker.sh pip install --no-deps -e .
```

## 2) Developer Runbook

1. Build or refresh the ROCm image when `Dockerfile.rocm` changes
2. Install the package in editable mode inside the container
3. Run a baseline demo smoke before larger edits
4. Run focused `pytest` for touched areas, then broader regression as needed
5. Use the validation script for end-to-end smoke coverage
6. Record benchmark/report values with explicit scenario, seed, and UI mode

## 3) Validation Sequence

1. Run baseline smoke simulation on a synthetic city with fixed seed
2. Run invariant-focused tests (conservation, non-negative queues, capacity violations)
3. Run boundary-condition tests (weekday/weekend, time-band transitions, blocked edges)
4. Run reproducibility tests (same seed + same controls/events -> same run summary)
5. Run road-only benchmark/realism smoke before any multimodal validation
6. Run multimodal benchmark/validation only after transit network and passenger-flow phases are implemented
7. Run UI stream smoke test to confirm throttled packet emission and day/time toggles

## 4) Command Examples

These are the current supported commands. Python/JAX execution remains
container-only; the one exception is the T072 validation wrapper, which runs on
the host because it shells out to `scripts/in_docker.sh`.

Baseline simulation smoke:

```bash
./scripts/in_docker.sh python -m metroflow.demo \
  --scenario synthetic_smoke \
  --seed 42 \
  --ticks 4 \
  --day-type weekday \
  --time-band morning
```

Adaptive demo smoke:

```bash
./scripts/in_docker.sh python -m metroflow.demo \
  --scenario synthetic_smoke \
  --seed 42 \
  --ticks 4 \
  --learning-mode adaptive
```

UI stream smoke:

```bash
./scripts/in_docker.sh python -m metroflow.demo \
  --scenario synthetic_smoke \
  --seed 42 \
  --ticks 4 \
  --ui stream \
  --ui-force-snapshot-every 1
```

Unit + integration smoke:

```bash
./scripts/in_docker.sh python -m pytest -q tests/unit tests/integration
```

Reproducibility-focused tests:

```bash
./scripts/in_docker.sh python -m pytest -q tests/integration/test_us3_reproducibility.py
```

Focused UI non-blocking stress test:

```bash
./scripts/in_docker.sh python -m pytest -q tests/benchmarks/test_ui_stream_non_blocking.py
```

Benchmark smoke:

```bash
./scripts/in_docker.sh python -m metroflow.benchmarks.run \
  --scenario synthetic_100k \
  --seed 42 \
  --duration-ticks 4
```

Benchmark run (playable-speed target):

```bash
./scripts/in_docker.sh python -m metroflow.benchmarks.run \
  --scenario synthetic_100k \
  --seed 42 \
  --duration-ticks 3600
```

Adaptive benchmark example:

```bash
./scripts/in_docker.sh python -m metroflow.benchmarks.run \
  --scenario synthetic_100k \
  --seed 42 \
  --duration-ticks 3600 \
  --learning-enabled
```

Road-only realism validation and benchmark split:

```bash
./scripts/in_docker.sh pytest -q tests/unit/test_city_generation.py

./scripts/in_docker.sh python -m metroflow.demo \
  --scenario synthetic_100k \
  --seed 42 \
  --ticks 4 \
  --day-type weekday \
  --time-band morning

./scripts/in_docker.sh python -m metroflow.benchmarks.run \
  --scenario synthetic_100k \
  --seed 42 \
  --duration-ticks 3600 \
  --ui off
```

Multimodal/transit validation and benchmark split:

```bash
# Planned command shape for Phase 11/12; not supported by the current baseline CLI yet.
./scripts/in_docker.sh python -m metroflow.demo \
  --scenario synthetic_100k \
  --mode multimodal \
  --seed 42 \
  --ticks 4

# Planned command shape for Phase 11/12; keep multimodal reports separate from road-only runs.
./scripts/in_docker.sh python -m metroflow.benchmarks.run \
  --scenario synthetic_100k \
  --mode multimodal \
  --seed 42 \
  --duration-ticks 3600
```

End-to-end quickstart smoke wrapper:

```bash
bash scripts/validate_adaptive_traffic_sim.sh
```

Full regression:

```bash
./scripts/in_docker.sh python -m pytest -q
```

Lint:

```bash
./scripts/in_docker.sh ruff check .
```

## 5) Minimum Acceptance Checks for This Feature

### Invariants

- No negative queue lengths during smoke and regression tests
- Capacity violations are detected and counted when intentionally induced
- Conservation checks reconcile generated/active/completed/failed trips

### Boundary Conditions

- Weekday vs weekend trip generation produces different demand patterns
- Time-band transitions change future trip generation without corrupting
  in-flight trips
- Blocked edge / bridge closure scenarios trigger rerouting or recorded failures
  without crashing the run

### Reproducibility

- Same seed + same event schedule + same UI control sequence yields identical:
  - trip generation totals
  - trip completion totals
  - invariant violation counts

### Performance / Playability

- Standard ~100k population benchmark reports:
  - median tick rate (Hz)
  - p10 tick rate (Hz)
  - active agent count median/p95
- Road-only realism reports additionally record explicit `scenario_mode=road_only`
- Multimodal extension reports MUST record `scenario_mode=multimodal` separately
- Target interpretation:
  - minimum acceptable: >= 2 Hz median during active periods
  - desired range: 2-10 Hz depending on scenario/event load

### UI Non-Blocking Behavior

- UI congestion frames may be throttled/dropped/coalesced under load
- Simulation tick progression must continue even when UI consumer is slow
- Day/time toggle commands are acknowledged and applied on step boundaries

## 6) Benchmark Reporting Template (Use in PR/Review Notes)

- Scenario ID:
- Scenario mode (`road_only` / `multimodal`):
- Seed:
- Population target:
- Active agent median/p95:
- Duration (ticks / real time):
- Median tick rate (Hz):
- p10 tick rate (Hz):
- Invariant violations (counts):
- Event mix (if any):
- Realism report attached (yes/no):
- Station summaries attached (yes/no):
- UI mode (off / stream):
- Environment (ROCm container image + GPU/CPU):

## 7) Cross-Document References

- Plan: `specs/001-adaptive-traffic-sim/plan.md`
- Research decisions: `specs/001-adaptive-traffic-sim/research.md`
- Data model: `specs/001-adaptive-traffic-sim/data-model.md`
- Contracts: `specs/001-adaptive-traffic-sim/contracts/`
- Architecture notes: `docs/ARCHITECTURE.md`
- Performance/reporting conventions: `docs/PERFORMANCE_TARGETS.md`

## 8) Phase 1 Setup Task Checkpoints (Placeholders)

Use this checklist to record setup-task completion and quick validation notes as
implementation progresses.

- [ ] `T001` Package scaffolding (`src/metroflow/*/__init__.py`)
- [ ] `T002` Test directory scaffolding (`tests/unit`, `tests/integration`, `tests/contract`, `tests/benchmarks`)
- [ ] `T003` Shared pytest fixtures skeleton (`tests/conftest.py`)
- [ ] `T004` Feature test constants/seed registry (`tests/fixtures/simulation_scenarios.py`)
- [ ] `T005` Benchmark reporting utility skeleton (`src/metroflow/benchmarks/reporting.py`)
- [ ] `T006` Quickstart checkpoint/validation placeholders (this section + section 9)

## 9) Validation Command Log Placeholders

Record the exact command, environment, and outcome when running setup/foundational
validation during implementation.

### Setup / Sanity

```bash
# [placeholder] Build ROCm image (run when image changes)
docker build -f Dockerfile.rocm -t metroflow:rocm .

# [placeholder] Install editable package in container
./scripts/in_docker.sh pip install --no-deps -e .
```

### Per-Task Validation

```bash
# [placeholder] Pytest smoke after setup/foundational tasks
./scripts/in_docker.sh python -m pytest -q

# [placeholder] Demo smoke after setup/foundational tasks
./scripts/in_docker.sh python -m metroflow.demo

# [placeholder] Lint check for touched files / repo
./scripts/in_docker.sh ruff check .
```

### Run Log Template

- Date (UTC):
- Task(s):
- Command:
- Environment (container image/tag):
- Result (pass/fail):
- Notes:
