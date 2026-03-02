"""Baseline demo entrypoint with optional UI packet stream smoke wiring."""

from __future__ import annotations

import argparse
from collections import Counter

from metroflow.sim.config import DayType, SimulationConfig, TimeBand
from metroflow.sim.control import SimulationControl
from metroflow.sim.run_summary import build_baseline_run_summary
from metroflow.sim.step import init_simulation, simulation_step
from metroflow.ui.stream_server import NavigatorUIStreamServer


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    if args.scenario not in {"synthetic_smoke", "synthetic_100k"}:
        raise SystemExit(f"unsupported scenario: {args.scenario}")
    population_target = 100_000 if args.scenario == "synthetic_100k" else 10_000

    ui_stream_enabled = args.ui == "stream"
    config = SimulationConfig(
        population_target=population_target,
        random_seed=args.seed,
        ui_stream_enabled=ui_stream_enabled,
        learning_enabled=args.learning_mode == "adaptive",
    )
    state, rng_key = init_simulation(config, scenario_seed=args.seed)
    state = state.with_clock(day_type=args.day_type, time_band=args.time_band)

    ui_server = NavigatorUIStreamServer() if ui_stream_enabled else None
    packet_counts: Counter[str] = Counter()
    ticks_with_ui_packets = 0
    adaptive_mix_ticks = 0
    adaptive_fallback_ticks = 0
    max_policy_mix_lambda = 0.0

    for step_idx in range(args.ticks):
        force_ui_snapshot = (
            ui_stream_enabled
            and args.ui_force_snapshot_every > 0
            and (step_idx % args.ui_force_snapshot_every == 0)
        )
        control = SimulationControl(ui_force_snapshot=force_ui_snapshot)
        state, telemetry, ui_snapshot_source, rng_key = simulation_step(state, control, rng_key)
        adaptive_applied, fallback_triggered, applied_lambda = _resolve_adaptive_tick_metrics(
            state=state,
            telemetry=telemetry,
        )
        adaptive_mix_ticks += int(adaptive_applied)
        adaptive_fallback_ticks += int(fallback_triggered)
        max_policy_mix_lambda = max(max_policy_mix_lambda, applied_lambda)

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

    print("MetroFlow demo run complete.")
    print(
        "Run:",
        f"scenario={args.scenario}",
        f"seed={args.seed}",
        f"ticks={args.ticks}",
        f"population_target={population_target}",
        f"day_type={state.day_type.value}",
        f"time_band={state.time_band.value}",
        f"ui={args.ui}",
        f"learning_mode={args.learning_mode}",
    )
    summary = build_baseline_run_summary(
        state,
        ui_packet_counts=dict(packet_counts),
        hotspot_top_k=3,
    )
    print(
        "Summary:",
        f"tick_index={summary.tick_index}",
        f"active_agents={summary.active_agents}",
        f"queued={summary.queued_trip_requests}",
        f"pending={summary.pending_trip_requests}",
        f"completed_total={summary.trip_completed_total}",
        f"failed_total={summary.trip_failed_total}",
    )
    if summary.hotspot_links_top_k:
        top = summary.hotspot_links_top_k[0]
        print(
            "Hotspot:",
            f"link_id={top['link_id']}",
            f"class={top['road_class']}",
            f"congestion_ratio={top['congestion_ratio']:.3f}",
            f"travel_time_ratio={top['travel_time_ratio']:.3f}",
        )
    if args.learning_mode == "adaptive":
        print(
            "Adaptive:",
            f"mix_ticks={adaptive_mix_ticks}",
            f"fallback_ticks={adaptive_fallback_ticks}",
            f"max_lambda={max_policy_mix_lambda:.3f}",
        )
    else:
        print("Adaptive: disabled")
    if ui_stream_enabled:
        print(
            "UI stream:",
            f"ticks_with_ui_packets={ticks_with_ui_packets}",
            f"congestion_frames={packet_counts.get('ui.congestion_frame', 0)}",
            f"forced_snapshot_every={args.ui_force_snapshot_every}",
            f"packet_counts={dict(sorted(summary.ui_packet_counts.items()))}",
        )
    else:
        print("UI stream: disabled")
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MetroFlow synthetic-city demo runner")
    parser.add_argument("--scenario", default="synthetic_smoke", choices=("synthetic_smoke", "synthetic_100k"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--ticks", type=int, default=4)
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
    parser.add_argument(
        "--learning-mode",
        default="baseline",
        choices=("baseline", "adaptive"),
        help="Choose baseline-only routing or adaptive policy blending.",
    )
    parser.add_argument(
        "--ui-force-snapshot-every",
        type=int,
        default=0,
        help="Force a UI snapshot request every N ticks when --ui=stream (0 disables forced snapshots).",
    )
    args = parser.parse_args(argv)
    args.day_type = DayType(args.day_type)
    args.time_band = TimeBand(args.time_band)
    if args.ticks < 0:
        parser.error("--ticks must be >= 0")
    if args.ui_force_snapshot_every < 0:
        parser.error("--ui-force-snapshot-every must be >= 0")
    return args


def _resolve_adaptive_tick_metrics(
    *,
    state,
    telemetry,
) -> tuple[bool, bool, float]:
    policy_blend_state = getattr(getattr(state, "dynamic", None), "policy_blend_state", None)
    fallback_triggered = bool(
        getattr(policy_blend_state, "fallback_triggered", telemetry.adaptive_fallback_triggered)
    )
    adaptive_enabled = bool(getattr(policy_blend_state, "adaptive_enabled", False))
    applied_lambda = float(getattr(policy_blend_state, "lambda_mix", telemetry.policy_mix_lambda))
    adaptive_applied = adaptive_enabled and not fallback_triggered
    return adaptive_applied, fallback_triggered, applied_lambda if adaptive_applied else 0.0


if __name__ == "__main__":
    raise SystemExit(main())
