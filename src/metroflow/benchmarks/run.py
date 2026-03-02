"""Benchmark scenario runner and metric capture helpers."""

from __future__ import annotations

import argparse
import time
from collections import Counter
from dataclasses import asdict
from dataclasses import fields as dataclass_fields
from typing import Any, Mapping

import jax.numpy as jnp
import numpy as np

from metroflow.benchmarks.reporting import (
    benchmark_report_from_run_summary,
    format_benchmark_report_markdown,
)
from metroflow.sim.config import DayType, SimulationConfig, TimeBand
from metroflow.sim.control import SimulationControl
from metroflow.sim.run_summary import BaselineRunSummary, build_baseline_run_summary
from metroflow.sim.step import init_simulation, simulation_step
from metroflow.ui.stream_server import NavigatorUIStreamServer

__all__ = [
    "compute_benchmark_summary_metrics_core",
    "compute_benchmark_summary_metrics_host",
    "run_benchmark_scenario",
    "run_benchmark",
    "execute_benchmark",
    "main",
]


def run_benchmark_scenario(
    *,
    scenario_id: str | None = None,
    scenario: str | None = None,
    config: SimulationConfig | Mapping[str, Any] | None = None,
    seed: int | None = None,
    scenario_seed: int | None = None,
    duration_ticks: int | None = None,
    ticks: int | None = None,
    num_ticks: int | None = None,
    smoke: bool = False,
    day_type: DayType | str = DayType.WEEKDAY,
    time_band: TimeBand | str = TimeBand.MORNING,
    ui_mode: str = "off",
    learning_enabled: bool | None = None,
) -> dict[str, Any]:
    """Run a benchmark-shaped simulation and capture report metrics."""

    resolved_scenario = _resolve_scenario_id(
        scenario_id=scenario_id,
        scenario=scenario,
        config=config,
    )
    resolved_seed = _resolve_seed(seed=seed, scenario_seed=scenario_seed, config=config)
    resolved_duration_ticks = _resolve_duration_ticks(
        duration_ticks=duration_ticks,
        ticks=ticks,
        num_ticks=num_ticks,
        smoke=smoke,
    )
    resolved_day_type = DayType(day_type)
    resolved_time_band = TimeBand(time_band)
    resolved_ui_mode = _resolve_ui_mode(ui_mode)
    sim_config = _build_benchmark_config(
        resolved_scenario=resolved_scenario,
        resolved_seed=resolved_seed,
        resolved_ui_mode=resolved_ui_mode,
        learning_enabled=learning_enabled,
        config=config,
    )

    state, rng_key = init_simulation(sim_config, scenario_seed=resolved_seed)
    state = state.with_clock(day_type=resolved_day_type, time_band=resolved_time_band)

    ui_server = NavigatorUIStreamServer() if resolved_ui_mode == "stream" else None
    packet_counts: Counter[str] = Counter()
    ticks_with_ui_packets = 0
    tick_durations = np.zeros((resolved_duration_ticks,), dtype=np.float64)
    active_agent_counts = np.zeros((resolved_duration_ticks,), dtype=np.float64)
    invariant_counts_total: dict[str, int] = {}

    for step_idx in range(resolved_duration_ticks):
        force_ui_snapshot = ui_server is not None and step_idx == 0
        control = SimulationControl(ui_force_snapshot=force_ui_snapshot)
        started = time.perf_counter()
        state, telemetry, ui_snapshot_source, rng_key = simulation_step(state, control, rng_key)
        elapsed = max(time.perf_counter() - started, 1e-9)
        tick_durations[step_idx] = float(elapsed)
        active_agent_counts[step_idx] = float(telemetry.active_agent_count)
        _accumulate_invariant_counts(invariant_counts_total, state)

        if ui_server is not None and ui_snapshot_source is not None:
            packets = ui_server.ingest_step_output(
                state=state,
                telemetry=telemetry,
                ui_snapshot_source=ui_snapshot_source,
                force_snapshot_emit=force_ui_snapshot,
            )
            for packet in packets:
                packet_counts[packet.type.value] += 1
            if packets:
                ticks_with_ui_packets += 1

    summary = build_baseline_run_summary(
        state,
        ui_packet_counts=dict(packet_counts),
        hotspot_top_k=3,
    )
    run_summary = build_benchmark_run_summary(
        benchmark_scenario_id=resolved_scenario,
        summary=summary,
        population_target=sim_config.population_target,
        duration_ticks=resolved_duration_ticks,
        duration_seconds=float(np.sum(tick_durations)),
        tick_durations=tick_durations,
        active_agent_counts=active_agent_counts,
        invariant_violation_counts=invariant_counts_total,
    )
    benchmark_report = benchmark_report_from_run_summary(
        run_summary,
        population_target=sim_config.population_target,
        active_agent_median=run_summary["active_agent_median"],
        active_agent_p95=run_summary["active_agent_p95"],
        duration_ticks=run_summary["duration_ticks"],
        duration_seconds=run_summary["duration_seconds"],
        event_mix="adaptive_od_ucb" if sim_config.learning_enabled else "baseline_only",
        ui_mode=resolved_ui_mode,
        environment="rocm-container",
    )

    return {
        "run_summary": run_summary,
        "summary": run_summary,
        "benchmark_report": asdict(benchmark_report),
        "report": format_benchmark_report_markdown(benchmark_report),
        "ticks_with_ui_packets": int(ticks_with_ui_packets),
    }


def run_benchmark(**kwargs: Any) -> dict[str, Any]:
    """Alias for `run_benchmark_scenario`."""

    return run_benchmark_scenario(**kwargs)


def execute_benchmark(**kwargs: Any) -> dict[str, Any]:
    """Alias for `run_benchmark_scenario`."""

    return run_benchmark_scenario(**kwargs)


def build_benchmark_run_summary(
    *,
    benchmark_scenario_id: str,
    summary: BaselineRunSummary,
    population_target: int,
    duration_ticks: int,
    duration_seconds: float,
    tick_durations: np.ndarray,
    active_agent_counts: np.ndarray,
    invariant_violation_counts: Mapping[str, int],
) -> dict[str, Any]:
    """Extend a baseline run summary with benchmark-only metrics."""

    metrics = compute_benchmark_summary_metrics_host(
        tick_durations=tick_durations,
        active_agent_counts=active_agent_counts,
    )
    run_summary = asdict(summary)
    run_summary.update(
        {
            "scenario_id": str(benchmark_scenario_id),
            "trip_completion_rate": float(summary.trip_completion_rate),
            "trip_failure_rate": float(summary.trip_failure_rate),
            "population_target": int(population_target),
            "duration_ticks": int(duration_ticks),
            "duration_seconds": float(duration_seconds),
            "tick_rate_median": float(metrics["tick_rate_median"]),
            "tick_rate_p10": float(metrics["tick_rate_p10"]),
            "active_agent_median": float(metrics["active_agent_median"]),
            "active_agent_p95": float(metrics["active_agent_p95"]),
            "invariant_violation_counts": {
                str(key): int(value) for key, value in invariant_violation_counts.items()
            },
        }
    )
    return run_summary


def compute_benchmark_summary_metrics_core(
    *,
    tick_durations: Any,
    active_agent_counts: Any,
) -> dict[str, Any]:
    """JAX-friendly benchmark metric aggregation core."""

    durations = jnp.asarray(tick_durations, dtype=jnp.float32)
    active_agents = jnp.asarray(active_agent_counts, dtype=jnp.float32)
    if durations.size == 0 or active_agents.size == 0:
        zero = jnp.asarray(0.0, dtype=jnp.float32)
        return {
            "tick_rate_median": zero,
            "tick_rate_p10": zero,
            "active_agent_median": zero,
            "active_agent_p95": zero,
        }
    safe_rates = jnp.where(durations > 0.0, 1.0 / durations, 0.0)
    return {
        "tick_rate_median": jnp.quantile(safe_rates, 0.5),
        "tick_rate_p10": jnp.quantile(safe_rates, 0.1),
        "active_agent_median": jnp.quantile(active_agents, 0.5),
        "active_agent_p95": jnp.quantile(active_agents, 0.95),
    }


def compute_benchmark_summary_metrics_host(
    *,
    tick_durations: np.ndarray,
    active_agent_counts: np.ndarray,
) -> dict[str, float]:
    """Host-safe benchmark metric aggregation used by the runner."""

    if tick_durations.size == 0 or active_agent_counts.size == 0:
        return {
            "tick_rate_median": 0.0,
            "tick_rate_p10": 0.0,
            "active_agent_median": 0.0,
            "active_agent_p95": 0.0,
        }
    safe_rates = np.divide(
        1.0,
        tick_durations,
        out=np.zeros_like(tick_durations, dtype=np.float64),
        where=tick_durations > 0.0,
    )
    return {
        "tick_rate_median": float(np.percentile(safe_rates, 50.0)),
        "tick_rate_p10": float(np.percentile(safe_rates, 10.0)),
        "active_agent_median": float(np.percentile(active_agent_counts, 50.0)),
        "active_agent_p95": float(np.percentile(active_agent_counts, 95.0)),
    }


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = run_benchmark_scenario(
        scenario_id=args.scenario,
        seed=args.seed,
        duration_ticks=args.duration_ticks,
        smoke=args.smoke,
        day_type=args.day_type,
        time_band=args.time_band,
        ui_mode=args.ui,
        learning_enabled=args.learning_enabled,
    )
    run_summary = result["run_summary"]
    print("MetroFlow benchmark run complete.")
    print(
        "Run:",
        f"scenario={run_summary['scenario_id']}",
        f"seed={run_summary['seed']}",
        f"ticks={run_summary['duration_ticks']}",
        f"population_target={run_summary['population_target']}",
        f"day_type={run_summary['day_type']}",
        f"time_band={run_summary['time_band']}",
        f"ui={args.ui}",
        f"learning={args.learning_enabled}",
    )
    print(
        "Summary:",
        f"tick_index={run_summary['tick_index']}",
        f"active_agents={run_summary['active_agents']}",
        f"queued={run_summary['queued_trip_requests']}",
        f"pending={run_summary['pending_trip_requests']}",
        f"completed_total={run_summary['trip_completed_total']}",
        f"failed_total={run_summary['trip_failed_total']}",
        f"tick_rate_median={run_summary['tick_rate_median']:.3f}",
        f"tick_rate_p10={run_summary['tick_rate_p10']:.3f}",
    )
    print(result["report"])
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MetroFlow benchmark scenario runner")
    parser.add_argument("--scenario", default="synthetic_100k", choices=("synthetic_smoke", "synthetic_100k"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--duration-ticks", type=int, default=3600)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument(
        "--day-type",
        default=DayType.WEEKDAY.value,
        choices=[day.value for day in DayType],
    )
    parser.add_argument(
        "--time-band",
        default=TimeBand.MORNING.value,
        choices=[band.value for band in TimeBand],
    )
    parser.add_argument("--ui", default="off", choices=("off", "stream"))
    parser.add_argument("--learning-enabled", action="store_true")
    args = parser.parse_args(argv)
    if args.duration_ticks < 0:
        parser.error("--duration-ticks must be >= 0")
    args.day_type = DayType(args.day_type)
    args.time_band = TimeBand(args.time_band)
    return args


def _build_benchmark_config(
    *,
    resolved_scenario: str,
    resolved_seed: int,
    resolved_ui_mode: str,
    learning_enabled: bool | None,
    config: SimulationConfig | Mapping[str, Any] | None,
) -> SimulationConfig:
    if isinstance(config, SimulationConfig):
        base_config = config
    elif isinstance(config, Mapping):
        config_fields = {field.name for field in dataclass_fields(SimulationConfig)}
        base_config = SimulationConfig(
            **{key: value for key, value in config.items() if key in config_fields}
        )
    else:
        population_target = 100_000 if resolved_scenario == "synthetic_100k" else 10_000
        base_config = SimulationConfig(
            population_target=population_target,
            random_seed=resolved_seed,
            ui_stream_enabled=resolved_ui_mode == "stream",
            learning_enabled=False if learning_enabled is None else bool(learning_enabled),
        )
    resolved_learning_enabled = (
        bool(base_config.learning_enabled) if learning_enabled is None else bool(learning_enabled)
    )
    return SimulationConfig(
        population_target=base_config.population_target,
        tick_seconds=base_config.tick_seconds,
        active_agent_capacity=base_config.active_agent_capacity,
        random_seed=resolved_seed,
        day_type_set=base_config.day_type_set,
        time_bands=base_config.time_bands,
        ui_stream_enabled=resolved_ui_mode == "stream",
        ui_stream_hz_limit=base_config.ui_stream_hz_limit,
        learning_enabled=resolved_learning_enabled,
        learning_mix_bounds=base_config.learning_mix_bounds,
        ctm_mode_enabled=base_config.ctm_mode_enabled,
    )


def _resolve_scenario_id(
    *,
    scenario_id: str | None,
    scenario: str | None,
    config: SimulationConfig | Mapping[str, Any] | None,
) -> str:
    resolved = scenario_id or scenario
    if resolved is None and isinstance(config, Mapping):
        resolved = config.get("scenario_id")
    if resolved is None:
        resolved = "synthetic_100k"
    resolved = str(resolved)
    if resolved not in {"synthetic_smoke", "synthetic_100k"}:
        raise ValueError(f"unsupported scenario: {resolved}")
    return resolved


def _resolve_seed(
    *,
    seed: int | None,
    scenario_seed: int | None,
    config: SimulationConfig | Mapping[str, Any] | None,
) -> int:
    if seed is not None:
        return int(seed)
    if scenario_seed is not None:
        return int(scenario_seed)
    if isinstance(config, SimulationConfig):
        return int(config.random_seed)
    if isinstance(config, Mapping) and "random_seed" in config:
        return int(config["random_seed"])
    return 42


def _resolve_duration_ticks(
    *,
    duration_ticks: int | None,
    ticks: int | None,
    num_ticks: int | None,
    smoke: bool,
) -> int:
    if smoke:
        return 4
    for candidate in (duration_ticks, ticks, num_ticks):
        if candidate is not None:
            value = int(candidate)
            if value < 0:
                raise ValueError("duration ticks must be >= 0")
            return value
    return 3600


def _resolve_ui_mode(ui_mode: str) -> str:
    resolved = str(ui_mode)
    if resolved not in {"off", "stream"}:
        raise ValueError(f"unsupported ui_mode: {resolved}")
    return resolved


def _accumulate_invariant_counts(target: dict[str, int], state: Any) -> None:
    invariant_state = getattr(getattr(state, "dynamic", None), "invariant_state", None)
    counters = getattr(invariant_state, "counters", None)
    if counters is None or not hasattr(counters, "as_dict"):
        return
    for key, value in counters.as_dict().items():
        target[str(key)] = int(target.get(str(key), 0)) + int(value)


if __name__ == "__main__":
    raise SystemExit(main())
