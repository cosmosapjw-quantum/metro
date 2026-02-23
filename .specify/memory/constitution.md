<!--
Sync Impact Report
- Version change: template (unratified placeholder) -> 1.0.0
- Modified principles:
  - Template Principle 1 -> I. SDD-First, Small-Diff Delivery
  - Template Principle 2 -> II. Safe Baseline Routing and Online-Only Learning
  - Template Principle 3 -> III. JAX-First Pure Core and Deterministic Randomness
  - Template Principle 4 -> IV. Testable Invariants, Boundary Coverage, Reproducibility
  - Template Principle 5 -> V. Evidence-Based Performance and Non-Blocking Visualization
- Added sections:
  - Technical Constraints and Architecture Boundaries
  - Development Workflow and Quality Gates
- Removed sections:
  - None
- Templates requiring updates:
  - ✅ `.specify/templates/plan-template.md`
  - ✅ `.specify/templates/spec-template.md`
  - ✅ `.specify/templates/tasks-template.md`
  - ✅ `.specify/templates/commands/` (directory absent; no command templates to update)
- Runtime guidance docs reviewed:
  - ✅ `README.md` (container execution guidance aligned)
  - ✅ `AGENTS.md` (already aligned; no content change)
- Follow-up TODOs:
  - None
-->
# MetroFlow Constitution

## Core Principles

### I. SDD-First, Small-Diff Delivery
All work MUST follow `spec -> plan -> tasks -> implement`. Implementations MUST be
delivered as small, reviewable diffs tied to concrete tasks, and each task MUST
be independently verifiable by tests, smoke runs, or invariant checks. Large
rewrites that bypass the current task list are prohibited unless an amendment or
documented exception is approved in advance. Rationale: MetroFlow combines
simulation, routing, and learning; small validated increments reduce regression
risk and keep performance/debugging traceable.

### II. Safe Baseline Routing and Online-Only Learning
The default control policy MUST remain a safe baseline using congestion-aware
shortest-path or dynamic-potential routing. Any learned policy MUST be mixed in
gradually and MUST degrade safely to the baseline when confidence, stability, or
coverage is insufficient. Policy/model updates MUST use only experience generated
inside the simulator during runtime or controlled simulator rollouts; external
data training is prohibited. Rationale: this preserves predictable behavior while
allowing adaptive improvements without data leakage or offline overfitting.

### III. JAX-First Pure Core and Deterministic Randomness
Core simulation loops MUST be designed as JAX-first, `jit`-compatible pure
functions with explicit state transitions. Mutable host-side control flow inside
the hot path is prohibited unless justified and measured. Randomness MUST be
controlled via explicit `PRNGKey` management and seed propagation so runs are
reproducible. Rationale: JAX-compatible purity is required for target throughput,
and explicit RNG handling is required for debugging and scientific comparison.

### IV. Testable Invariants, Boundary Coverage, Reproducibility
Changes affecting the simulator core, routing, demand generation, or learning
logic MUST include tests for conservation of vehicles/agents, non-negative queue
lengths, and capacity-violation detection. Boundary-condition tests MUST cover
weekday/weekend behavior, time-of-day transitions, and blocked edges
(construction/accident or equivalent closures) where relevant. Fixed-seed
reproducibility tests MUST be added or updated for nondeterministic paths.
Rationale: these are the minimum correctness properties for a dynamic traffic
simulator and prevent silent physics/logic drift.

### V. Evidence-Based Performance and Non-Blocking Visualization
Performance claims MUST be backed by measurements, profiles, or benchmarks with
documented conditions; unmeasured performance assertions are non-compliant. The
project target is a population of 100k with 10k-30k active agents at 2-10 Hz
game ticks. Visualization MUST NOT block the core loop and MUST use asynchronous
processing, downsampling, frame skipping, or equivalent isolation. Rationale:
MetroFlow is only useful if correctness and throughput are demonstrated together,
and visualization overhead must not distort core simulation behavior.

## Technical Constraints and Architecture Boundaries

- Python/JAX test runs, demo runs, and formatting commands MUST execute inside
  the ROCm container via `./scripts/in_docker.sh`; host Python/JAX execution is
  prohibited for project validation.
- The system MUST preserve separation between City, Demand, and Flow layers, and
  MUST avoid strong coupling between the city generator and traffic engine.
- Trade-offs and architecture decisions MUST be recorded in
  `specs/001-metroflow/research.md` and `docs/ARCHITECTURE.md`.
- Learning integrations MUST document baseline fallback behavior, mixing schedule,
  and simulator-only experience source before implementation begins.
- Visualization integrations MUST document buffering/sampling strategy and prove
  they cannot block or stall simulation ticks.

## Development Workflow and Quality Gates

- Implementation MUST start from the next actionable item in
  `specs/001-metroflow/tasks.md`, with references to relevant plan/data-model
  docs captured in the task or implementation notes.
- Before Phase 0 research and again before implementation, each plan MUST pass a
  Constitution Check covering all five core principles and any declared
  exceptions.
- After implementation, contributors MUST run `./scripts/in_docker.sh pytest -q`
  and a relevant smoke run; simulator-core changes MUST include a performance
  smoke or benchmark that documents tick rate and scenario size.
- Reviews MUST verify invariant coverage, boundary-condition coverage, seed
  reproducibility, and evidence for any performance-sensitive claims.
- Exceptions MAY be granted only when documented with scope, rationale, rollback
  plan, and follow-up owner in feature docs or architecture notes.

## Governance

This constitution supersedes conflicting local practices for MetroFlow
development. Operational guidance in `AGENTS.md`, `README.md`, and `.specify`
templates MUST remain aligned with this document.

Amendments MUST include: (1) the proposed rule change, (2) rationale and tradeoff
analysis, (3) dependent template/document updates or an explicit deferred TODO,
and (4) a version bump selected by the policy below.

Versioning policy for this constitution follows semantic versioning:
- MAJOR: Removes or materially redefines a core principle or governance rule in a
  backward-incompatible way.
- MINOR: Adds a new principle/section or materially expands mandatory guidance.
- PATCH: Clarifies wording, fixes ambiguity/typos, or makes non-semantic edits.

Compliance review expectations:
- Plans MUST record a pass/fail Constitution Check before design and before
  implementation.
- Code review and task review MUST explicitly confirm compliance or document
  approved exceptions.
- Performance, correctness, and reproducibility claims MUST cite the test/smoke
  evidence used to support them.

**Version**: 1.0.0 | **Ratified**: 2026-02-23 | **Last Amended**: 2026-02-23
