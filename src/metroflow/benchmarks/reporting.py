"""Benchmark report utility skeletons for MetroFlow."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

__all__ = [
    "BenchmarkReport",
    "benchmark_report_from_run_summary",
    "format_benchmark_report_markdown",
]


@dataclass(slots=True)
class BenchmarkReport:
    """PR/review friendly benchmark summary payload.

    This mirrors the planned benchmark reporting template while staying usable
    before the full benchmark runner and summary aggregation land.
    """

    scenario_id: str
    seed: int
    population_target: int | None = None
    active_agent_median: float | None = None
    active_agent_p95: float | None = None
    duration_ticks: int | None = None
    duration_seconds: float | None = None
    tick_rate_median_hz: float | None = None
    tick_rate_p10_hz: float | None = None
    invariant_violations: dict[str, int] = field(default_factory=dict)
    event_mix: str | None = None
    ui_mode: str | None = None
    environment: str | None = None


def benchmark_report_from_run_summary(
    run_summary: Mapping[str, Any],
    *,
    population_target: int | None = None,
    active_agent_median: float | None = None,
    active_agent_p95: float | None = None,
    duration_ticks: int | None = None,
    duration_seconds: float | None = None,
    event_mix: str | None = None,
    ui_mode: str | None = None,
    environment: str | None = None,
) -> BenchmarkReport:
    """Build a `BenchmarkReport` from a RunSummary-like mapping.

    The RunSummary fields are specified in the phase-1 data model. Extra
    benchmark-only values remain optional until benchmark aggregation is added.
    """

    invariant_counts = run_summary.get("invariant_violation_counts", {})
    if not isinstance(invariant_counts, Mapping):
        invariant_counts = {}

    return BenchmarkReport(
        scenario_id=str(run_summary.get("scenario_id", "unknown")),
        seed=int(run_summary.get("seed", 0)),
        population_target=population_target,
        active_agent_median=active_agent_median,
        active_agent_p95=active_agent_p95,
        duration_ticks=duration_ticks,
        duration_seconds=duration_seconds,
        tick_rate_median_hz=_as_optional_float(run_summary.get("tick_rate_median")),
        tick_rate_p10_hz=_as_optional_float(run_summary.get("tick_rate_p10")),
        invariant_violations={str(k): int(v) for k, v in invariant_counts.items()},
        event_mix=event_mix,
        ui_mode=ui_mode,
        environment=environment,
    )


def format_benchmark_report_markdown(report: BenchmarkReport) -> str:
    """Render the planned benchmark review template as markdown bullets."""

    return "\n".join(
        [
            f"- Scenario ID: {report.scenario_id}",
            f"- Seed: {report.seed}",
            f"- Population target: {_fmt(report.population_target)}",
            (
                "- Active agent median/p95: "
                f"{_fmt(report.active_agent_median)} / {_fmt(report.active_agent_p95)}"
            ),
            (
                "- Duration (ticks / real time): "
                f"{_fmt(report.duration_ticks)} / {_fmt(report.duration_seconds)}"
            ),
            f"- Median tick rate (Hz): {_fmt(report.tick_rate_median_hz)}",
            f"- p10 tick rate (Hz): {_fmt(report.tick_rate_p10_hz)}",
            f"- Invariant violations (counts): {_fmt_mapping(report.invariant_violations)}",
            f"- Event mix (if any): {_fmt(report.event_mix)}",
            f"- UI mode (off / stream): {_fmt(report.ui_mode)}",
            f"- Environment (ROCm container image + GPU/CPU): {_fmt(report.environment)}",
        ]
    )


def _as_optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _fmt(value: Any) -> str:
    return "N/A" if value is None else str(value)


def _fmt_mapping(values: Mapping[str, int]) -> str:
    if not values:
        return "N/A"
    return ", ".join(f"{key}={value}" for key, value in sorted(values.items()))
