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
