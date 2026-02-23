# Quickstart (Plan Validation and Target Smoke Flows)

This document defines the planned validation flow for the feature after
implementation tasks are generated. It is written now so the plan includes
benchmark, invariant, and reproducibility expectations up front.

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

## 2) Planned Validation Sequence (After Implementation)

1. Run baseline smoke simulation on a synthetic city with fixed seed
2. Run invariant-focused tests (conservation, non-negative queues, capacity violations)
3. Run boundary-condition tests (weekday/weekend, time-band transitions, blocked edges)
4. Run reproducibility tests (same seed + same controls/events -> same run summary)
5. Run performance benchmark for ~100k population playable-speed target
6. Run UI stream smoke test to confirm throttled packet emission and day/time toggles

## 3) Target Smoke Commands (Planned Interface)

These command shapes are planning targets for implementation tasks. Final command
names may be refined, but container-first execution is mandatory.

Baseline simulation smoke:

```bash
./scripts/in_docker.sh python -m metroflow.demo \
  --scenario synthetic_100k \
  --seed 42 \
  --day-type weekday \
  --time-band morning \
  --ui stream
```

Invariant and boundary tests:

```bash
./scripts/in_docker.sh pytest -q tests/unit tests/integration
```

Reproducibility-focused tests:

```bash
./scripts/in_docker.sh pytest -q -k "reproducibility or seed"
```

Benchmark run (playable-speed target):

```bash
./scripts/in_docker.sh python -m metroflow.benchmarks.run \
  --scenario synthetic_100k \
  --seed 42 \
  --duration-ticks 3600
```

UI packet stream smoke (separate viewer/client if applicable):

```bash
./scripts/in_docker.sh python -m metroflow.ui.stream_server --scenario synthetic_100k --seed 42
```

## 4) Minimum Acceptance Checks for This Feature

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
- Target interpretation:
  - minimum acceptable: >= 2 Hz median during active periods
  - desired range: 2-10 Hz depending on scenario/event load

### UI Non-Blocking Behavior

- UI congestion frames may be throttled/dropped/coalesced under load
- Simulation tick progression must continue even when UI consumer is slow
- Day/time toggle commands are acknowledged and applied on step boundaries

## 5) Benchmark Reporting Template (Use in PR/Review Notes)

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

## 6) Cross-Document References

- Plan: `specs/001-adaptive-traffic-sim/plan.md`
- Research decisions: `specs/001-adaptive-traffic-sim/research.md`
- Data model: `specs/001-adaptive-traffic-sim/data-model.md`
- Contracts: `specs/001-adaptive-traffic-sim/contracts/`

## 7) Phase 1 Setup Task Checkpoints (Placeholders)

Use this checklist to record setup-task completion and quick validation notes as
implementation progresses.

- [ ] `T001` Package scaffolding (`src/metroflow/*/__init__.py`)
- [ ] `T002` Test directory scaffolding (`tests/unit`, `tests/integration`, `tests/contract`, `tests/benchmarks`)
- [ ] `T003` Shared pytest fixtures skeleton (`tests/conftest.py`)
- [ ] `T004` Feature test constants/seed registry (`tests/fixtures/simulation_scenarios.py`)
- [ ] `T005` Benchmark reporting utility skeleton (`src/metroflow/benchmarks/reporting.py`)
- [ ] `T006` Quickstart checkpoint/validation placeholders (this section + section 8)

## 8) Validation Command Log Placeholders

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
./scripts/in_docker.sh pytest -q

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
