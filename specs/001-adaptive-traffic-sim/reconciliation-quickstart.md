# Quickstart: SDD and Prototype Reconciliation Audit

## Goal

Run a pre-implementation documentation integrity workflow that:
1. Inventories and analyzes repository docs.
2. Reconciles `prototype.md` with active SDD artifacts.
3. Verifies dependency-doc/manifest coherence.
4. Produces readiness `PASS/FAIL` for implementation gating.

## Prerequisites

- Repository root: `/home/cosmosapjw/metro`
- Active branch: `001-transit-realism-upgrade`
- ROCm container command wrapper available: `./scripts/in_docker.sh`

## Scenario A: Full documentation audit (US1)

1. Build/refresh inventory scope (expected in implementation task phase):
   ```bash
   rg --files docs specs '*.md' pyproject.toml Dockerfile.rocm AGENTS.md
   ```
2. Run audit command (target command shape for implementation):
   ```bash
   ./scripts/in_docker.sh python -m metroflow.tools.doc_reconciliation_audit \
     --repo-root /home/cosmosapjw/metro \
     --prototype /home/cosmosapjw/metro/prototype.md \
     --active-spec /home/cosmosapjw/metro/specs/001-adaptive-traffic-sim/spec.md \
     --output /home/cosmosapjw/metro/artifacts/doc-audit/report.yaml
   ```
3. Confirm output includes inventory + categorized findings with file-level references.

Expected result:
- Every in-scope document is listed.
- Findings have category, severity, location, and recommendation.

## Scenario B: Prototype reconciliation decisions (US2)

1. Filter prototype-vs-SDD conflicts from report output.
2. Validate every conflict has exactly one disposition:
   - `ADOPT_SDD`
   - `REVISE_SDD`
   - `DEFER_PHASE_GATED`
   - `DEPRECATE_PROTOTYPE`
3. Confirm rationale and authority source are present per decision.

Expected result:
- Reconciliation completeness is 100%.
- No unresolved prototype conflict remains unclassified.

## Scenario C: Dependency coherence gate (US3)

1. Validate dependency records against source files:
   - `pyproject.toml`
   - `Dockerfile.rocm`
   - `AGENTS.md`
   - active runbooks/spec docs
2. Verify mismatches are surfaced as `DependencyMismatch` findings.
3. Evaluate readiness gate from report.

Expected result:
- Readiness is `FAIL` when unresolved high-severity dependency mismatches exist.
- Readiness is `PASS` only when blocking mismatches/conflicts are resolved or explicitly waived.

## Validation Commands (post-implementation)

```bash
./scripts/in_docker.sh pytest -q
./scripts/in_docker.sh pytest -q tests/contract -k reconciliation
./scripts/in_docker.sh pytest -q tests/smoke -k doc_audit
```

## Performance Check (post-implementation)

```bash
./scripts/in_docker.sh python -m metroflow.tools.doc_reconciliation_audit \
  --repo-root /home/cosmosapjw/metro \
  --prototype /home/cosmosapjw/metro/prototype.md \
  --active-spec /home/cosmosapjw/metro/specs/001-adaptive-traffic-sim/spec.md \
  --benchmark
```

Acceptance target:
- Full audit runtime <= 60 seconds on current repository scale.
- Re-running without repository changes yields identical report ordering/content.
