# GPU Full-Support Remediation Plan (Current Codebase)

## Purpose

Restore and validate GPU-capable execution for the current MetroFlow baseline codepaths
inside the ROCm container without violating the existing feature spec/plan constraints.

## Constraints (Must Preserve)

- Follow `specs/001-adaptive-traffic-sim/spec.md` baseline scope separation (road-only MVP remains valid)
- Follow `specs/001-adaptive-traffic-sim/plan.md` JAX-first architecture intent and ROCm target runtime
- Follow `specs/001-adaptive-traffic-sim/quickstart.md` container-first execution (no host Python/JAX runs)
- Avoid large rewrites; prefer minimal diff fixes at failure boundaries

## Scope for This Remediation

- Remove runtime code that forces demo execution onto CPU (`JAX_PLATFORMS=cpu`)
- Fix currently observed ROCm GPU runtime failures in baseline demo execution paths
- Keep host-side UI/reporting layers host-side, but ensure they do not block GPU execution of the simulation path
- Re-run regression tests and demo smokes in the ROCm container

## Non-Goals (This Pass)

- End-to-end JIT compilation of the entire simulation pipeline
- Rewriting all host-side packetization/reporting modules into JAX kernels
- Performance optimization beyond fixes needed for GPU correctness/support

## Acceptance Criteria

- `src/metroflow/demo.py` no longer hardcodes CPU-only JAX platform selection
- `bash scripts/in_docker.sh python -m metroflow.demo` succeeds in ROCm container
- `bash scripts/in_docker.sh python -m metroflow.demo --scenario synthetic_100k --ui stream --ticks 4 --ui-force-snapshot-every 1` succeeds in ROCm container
- `bash scripts/in_docker.sh pytest -q` passes
- Any fallback introduced for GPU compatibility is placed at a host-side wrapper boundary and documented in code comments (minimal scope)

## Execution Steps

1. Identify and remove CPU-forcing runtime settings in demo/runtime entrypoints.
2. Reproduce GPU failure in ROCm container on demo path without CPU override.
3. Patch failing codepath(s) with minimal diff:
   - Prefer GPU-safe JAX operation rewrite
   - If unstable on ROCm for host-heavy wrapper code, add targeted host fallback
4. Re-run demo smokes (default and UI stream mode) in ROCm container.
5. Re-run full `pytest -q` in ROCm container.
6. Summarize changes, trade-offs, and remaining risks.

## Progress Log

- [x] Step 1 complete
- [x] Step 2 complete
- [x] Step 3 complete
- [x] Step 4 complete
- [x] Step 5 complete
- [x] Step 6 complete

