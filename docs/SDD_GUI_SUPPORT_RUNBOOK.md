# SDD GUI Support Runbook

This runbook explains how to use the consolidated GUI-related SDD artifacts
before implementation.

## Consolidated Spec Bundle

- `specs/001-adaptive-traffic-sim/spec.md`
- `specs/001-adaptive-traffic-sim/plan.md`
- `specs/001-adaptive-traffic-sim/tasks.md`
- `specs/001-adaptive-traffic-sim/research.md`
- `specs/001-adaptive-traffic-sim/data-model.md`
- `specs/001-adaptive-traffic-sim/quickstart.md`
- `specs/001-adaptive-traffic-sim/reconciliation-quickstart.md`
- `specs/001-adaptive-traffic-sim/contracts/document-reconciliation-report.md`
- `docs/DOCS_MANIFEST.md`

## What Was Decided

- First complete GUI release is browser-first, not native desktop-first.
- The simulation remains containerized and authoritative.
- GUI updates may be per tick or at a configured cadence; full wall-clock
  real-time rendering is not required.
- The GUI must prefer latest-only coalescing over blocking the simulation.

## Why This Direction Was Chosen

- It matches the current packetized UI architecture.
- It respects the repo's ROCm-container-first workflow.
- It gives a practical path to a complete operator GUI without first solving
  native desktop packaging.

## Recommended Next Flow

1. Run `/speckit.analyze` on the consolidated `001-adaptive-traffic-sim` set.
2. Resolve remaining High/Medium findings.
3. Re-run `/speckit.analyze` to confirm no unresolved blocking issues.
4. Start implementation from `specs/001-adaptive-traffic-sim/tasks.md`.

## Resolved Policy Snapshot

- First release is single-client only.
- Browser target is Chromium-class first; Firefox parity is deferred.
- First release excludes recording/replay.
- First release GUI controls are pause/resume/single-step/day/time only;
  ad-hoc event injection/clear is deferred.
- GUI runtime uses dedicated `metroflow.gui.app` path and remains separated from
  `metroflow.demo`.

## Implementation Guidance

- Do not wire rendering directly into `simulation_step`.
- Keep the existing `ui.packets`, `ui.stream_buffer`, and `ui.stream_server`
  modules as the low-level packet/cadence foundation.
- Add GUI-specific behavior as a higher layer in `src/metroflow/gui/`.
- Preserve latest-authoritative-state semantics; missing intermediate frames
  must remain normal and observable.

## Validation Guidance

Minimum pre-merge validation for GUI work should include:

- contract tests for command ACK semantics
- unit tests for bounded snapshot coalescing
- integration smoke for GUI launch + pause/step controls
- slow-consumer benchmark tests
- at least one recorded `synthetic_100k` GUI-enabled smoke on the reference
  hardware profile
- at least one screenshot artifact for each GUI-impacting PR
