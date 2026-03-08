# Implementation Plan: Unified SDD Gate + Map-Realism-First Execution

**Branch**: `001-transit-realism-upgrade` | **Date**: 2026-03-08 | **Spec**: `/home/cosmosapjw/metro/specs/001-adaptive-traffic-sim/spec.md`
**Input**: Consolidated planning baseline from:
- `/home/cosmosapjw/metro/specs/001-adaptive-traffic-sim/spec.md`
- `/home/cosmosapjw/metro/specs/001-adaptive-traffic-sim/contracts/document-reconciliation-report.md`
- `/home/cosmosapjw/metro/prototype.md`

## Summary

This unified SDD plan merges two previously separate planning streams into one
execution model:
1. Documentation integrity + prototype reconciliation + dependency coherence gate.
2. Map-realism foundation gate (`city/generator.py`, `city/zones.py`,
   `tools/render_city_map.py`, realism metrics evidence).

Simulator-construction expansion is blocked until both gates pass.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: `jax`, `jaxlib`, `numpy`, `pytest`, `ruff`, `matplotlib`, stdlib file/parsing utilities  
**Storage**: File-based configs/specs/contracts/artifacts/reports (no persistent DB)  
**Testing**: `pytest` (`tests/unit`, `tests/integration`, `tests/contract`, `tests/benchmarks`, `tests/smoke`)  
**Target Platform**: Linux + AMD ROCm container runtime  
**Project Type**: Python simulation engine + internal SDD governance/audit tooling  
**Performance Goals**: documentation audit <= 60 seconds for current repo scale; map/simulator evidence measured via benchmark and smoke runs  
**Constraints**: map-realism-first sequencing, constitution authority, deterministic output, container-only Python/JAX validation  
**Scale/Scope**: project-wide SDD/doc corpus plus 100k-scale synthetic city realism evidence gating before simulator expansion

## Constitution Check (Pre-Design)

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **SDD order enforced**: spec -> plan -> tasks sequencing is preserved.
- [x] **Safe baseline + online-only learning**: no external-data training path introduced.
- [x] **JAX-first + deterministic RNG**: simulator stream remains JAX-first and deterministic; audit stream requires deterministic report ordering.
- [x] **Invariant and boundary tests planned**: simulation invariants and documentation-readiness edge cases are both covered.
- [x] **Evidence-based performance plan**: runtime and realism claims are tied to benchmark/smoke evidence.
- [x] **Container runtime compliance**: Python/JAX validation commands are containerized with `./scripts/in_docker.sh`.
- [x] **Constitution path obligations mapped**: bridge/mirroring tasks include mandated files (`specs/001-adaptive-traffic-sim/tasks.md`, `specs/001-adaptive-traffic-sim/research.md`, `docs/ARCHITECTURE.md`).

## Project Structure

### Unified SDD Documentation Scope

```text
/home/cosmosapjw/metro/specs/
├── 001-adaptive-traffic-sim/
│   ├── spec.md
│   ├── plan.md
│   ├── research.md
│   ├── data-model.md
│   ├── contracts/
│   ├── tasks.md
│   └── reconciliation/
│       └── quickstart.md
```

### Source Code (repository root)

```text
/home/cosmosapjw/metro/
├── src/metroflow/
│   ├── city/
│   │   ├── generator.py
│   │   ├── zones.py
│   │   ├── graph.py
│   │   └── realism_metrics.py
│   ├── sim/
│   ├── routing/
│   ├── learning/
│   ├── transit/
│   ├── ui/
│   ├── gui/
│   ├── benchmarks/
│   └── tools/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── contract/
│   ├── benchmarks/
│   └── smoke/
├── docs/
├── prototype.md
├── pyproject.toml
└── Dockerfile.rocm
```

**Structure Decision**: Keep the existing single Python project layout and run
unified planning with two coordinated gates (doc-readiness gate + realism gate)
before simulator-construction expansion.

**Canonical Execution Entrypoint**: `/home/cosmosapjw/metro/specs/001-adaptive-traffic-sim/tasks.md`
is the primary task stream; reconciliation substream execution is mandatory via
Phase 8 (`T059`-`T065`) and must be completed before simulator-construction expansion.

**Canonical Phase Semantics (Cross-Doc)**:
- Phase 8: documentation/prototype/dependency reconciliation gate (`T059`-`T065`)
- Phase 9: transit static wiring semantics (implemented in tasks Phase 5; see
  contracts/data-model references for Phase 9 transit-static scope)
- Phase 10: first-release GUI runtime/control baseline
- Phase 11: evidence-policy reinforcement (screenshot/nightly/full-batch/min-repetition)

## Phase 0: Outline & Research

Unified research output resolves:
1. Authority and conflict disposition for docs/prototype/constitution.
2. Deterministic findings/report contract.
3. Dependency source-of-truth and mismatch policy.
4. Realism evidence gate required before simulator construction.

Primary artifacts:
- `/home/cosmosapjw/metro/specs/001-adaptive-traffic-sim/research.md`
- `/home/cosmosapjw/metro/specs/001-adaptive-traffic-sim/contracts/document-reconciliation-report.md`

## Phase 1: Design & Contracts

Design artifacts for unified execution:
- Documentation audit/reconciliation command flow in
  `/home/cosmosapjw/metro/specs/001-adaptive-traffic-sim/reconciliation-quickstart.md`
- Documentation conflict disposition contract in
  `/home/cosmosapjw/metro/specs/001-adaptive-traffic-sim/contracts/document-reconciliation-report.md`
- Map/simulation contracts and data model under
  `/home/cosmosapjw/metro/specs/001-adaptive-traffic-sim/`

Agent context update remains required:
- `.specify/scripts/bash/update-agent-context.sh codex`

## Phase 2: Unified Planning Strategy (Stop Point)

Execution order for `/speckit.tasks` and implementation staging:
1. Run constitution bridge/mirroring updates for mandated files.
2. Complete documentation integrity + prototype reconciliation + dependency
   coherence readiness gate tasks (main tasks Phase 8, `T059`-`T065`).
3. Validate map-realism foundation evidence (`synthetic_smoke` compatibility,
   key visual signal preservation, realism metrics thresholds).
4. Open simulator-construction expansion only after both gates pass.

This unified plan intentionally stops at planning scope.

## Constitution Check (Post-Design Re-check)

- [x] **SDD order enforced**: maintained with unified cross-spec gating.
- [x] **Safe baseline + online-only learning**: no violation introduced.
- [x] **JAX-first + deterministic RNG**: preserved for simulator stream and audit determinism stream.
- [x] **Invariant and boundary tests planned**: retained for both streams.
- [x] **Evidence-based performance plan**: retained with explicit benchmark/smoke outputs.
- [x] **Container runtime compliance**: explicit in validation tasks.
- [x] **Constitution path obligations mapped**: retained with bridge/mirror tasks.

## Complexity Tracking

No unresolved constitution violations are accepted in this unified plan.
