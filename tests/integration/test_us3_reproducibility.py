from __future__ import annotations

import runpy
from pathlib import Path

import pytest

from metroflow.sim.config import SimulationConfig
from metroflow.sim.control import SimulationControl
from metroflow.sim.run_summary import build_baseline_run_summary
from metroflow.sim.step import init_simulation, run_rollout, validate_invariants

"""Contract-first reproducibility integration tests for US3 (T059).

These tests may skip until adaptive plugin/mixer integration is wired into
`sim.step` (T061-T066). Once enabled, repeated fixed-seed runs with identical
controls/events should produce identical telemetry and run summaries.
"""

_SCENARIOS = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "fixtures" / "simulation_scenarios.py")
)
SEED_REGISTRY = _SCENARIOS["SEED_REGISTRY"]


def test_us3_fixed_seed_repeated_baseline_runs_with_identical_controls_events_match_pending_t061_t066():
    events_mod = _require_us3_repro_modules()

    sig_a = _run_repro_signature(
        events_mod,
        learning_enabled=False,
        seed=SEED_REGISTRY["reproducibility_baseline"],
        event_id=9301,
    )
    sig_b = _run_repro_signature(
        events_mod,
        learning_enabled=False,
        seed=SEED_REGISTRY["reproducibility_baseline"],
        event_id=9301,
    )

    assert sig_a == sig_b


def test_us3_fixed_seed_repeated_adaptive_runs_with_identical_controls_events_match_pending_t061_t066():
    events_mod = _require_us3_repro_modules()

    sig_a = _run_repro_signature(
        events_mod,
        learning_enabled=True,
        seed=SEED_REGISTRY["reproducibility_adaptive"],
        event_id=9302,
    )
    sig_b = _run_repro_signature(
        events_mod,
        learning_enabled=True,
        seed=SEED_REGISTRY["reproducibility_adaptive"],
        event_id=9302,
    )

    assert sig_a == sig_b


def _require_us3_repro_modules():
    events_mod = pytest.importorskip(
        "metroflow.flow.events",
        reason="T048 pending dependency: flow.events not implemented yet",
    )
    pytest.importorskip(
        "metroflow.flow.event_effects",
        reason="T049 pending dependency: flow.event_effects not implemented yet",
    )
    pytest.importorskip(
        "metroflow.routing.reroute_policy",
        reason="T051 pending dependency: routing.reroute_policy not implemented yet",
    )
    pytest.importorskip(
        "metroflow.learning.plugins",
        reason="T061 pending: learning.plugins not implemented yet",
    )
    pytest.importorskip(
        "metroflow.routing.candidates",
        reason="T062 pending: routing.candidates not implemented yet",
    )
    pytest.importorskip(
        "metroflow.learning.od_ucb",
        reason="T063 pending: learning.od_ucb not implemented yet",
    )
    pytest.importorskip(
        "metroflow.routing.policy_mixer",
        reason="T064 pending: routing.policy_mixer not implemented yet",
    )
    pytest.importorskip(
        "metroflow.learning.experience",
        reason="T065 pending: learning.experience not implemented yet",
    )

    step_mod = pytest.importorskip("metroflow.sim.step")
    if not hasattr(step_mod, "_US3_POLICY_BLEND_FALLBACK_INTEGRATED"):
        pytest.fail(
            "sim.step missing _US3_POLICY_BLEND_FALLBACK_INTEGRATED marker; "
            "T066 must expose this gate for US3 reproducibility tests"
        )
    if not bool(getattr(step_mod, "_US3_POLICY_BLEND_FALLBACK_INTEGRATED", False)):
        pytest.skip(
            "T066 pending: sim.step US3 policy blend/fallback integration not implemented yet "
            "(set _US3_POLICY_BLEND_FALLBACK_INTEGRATED=True in T066)"
        )
    return events_mod


def _run_repro_signature(events_mod, *, learning_enabled: bool, seed: int, event_id: int):
    config = SimulationConfig(
        active_agent_capacity=24,
        ui_stream_enabled=False,
        learning_enabled=bool(learning_enabled),
    )
    state, rng_key = init_simulation(config=config, scenario_seed=int(seed))
    blocked_link_id = _select_existing_blockable_link_id(state)
    event = _build_disruption_event(events_mod, event_id=event_id, link_id=blocked_link_id)
    controls = _repro_controls(event)

    final_state, telemetry_log, _ = run_rollout(
        initial_state=state,
        controls=controls,
        rng_key=rng_key,
    )
    report = validate_invariants(final_state)
    assert report.ok is True
    assert report.counters.total_violations == 0

    summary = build_baseline_run_summary(final_state)
    if learning_enabled:
        # US3 reproducibility test should still observe that adaptive mode is
        # active in some way (non-zero mix or explicit safety fallback).
        assert any(
            float(t.policy_mix_lambda) > 0.0 or bool(t.adaptive_fallback_triggered)
            for t in telemetry_log
        )
    telemetry_signature = tuple(
        (
            int(t.tick_index),
            int(t.active_agent_count),
            int(t.trip_generated_this_tick),
            int(t.trip_completed_this_tick),
            int(t.trip_failed_this_tick),
            int(t.capacity_violation_count_delta),
            bool(t.negative_queue_detected),
            round(float(t.policy_mix_lambda), 6),
            bool(t.adaptive_fallback_triggered),
            bool(t.ui_snapshot_emitted),
        )
        for t in telemetry_log
    )
    summary_signature = (
        int(summary.tick_index),
        int(summary.active_agents),
        int(summary.queued_trip_requests),
        int(summary.pending_trip_requests),
        int(summary.completed_trips_total),
        int(summary.failed_trips_total),
        int(summary.capacity_violation_count),
        bool(summary.negative_queue_detected),
        int(summary.ui_packets_emitted),
        _hotspot_summary_signature(getattr(summary, "hotspot_links_top_k", ())),
        bool(getattr(summary, "disruption_response_metrics_available", False)),
        int(getattr(summary, "disruption_active_event_count", 0)),
        int(getattr(summary, "disruption_affected_link_count", 0)),
        int(getattr(summary, "reroute_decisions_total", 0)),
        int(getattr(summary, "persistence_decisions_total", 0)),
        round(float(getattr(summary, "reroute_share", 0.0)), 6),
        round(float(getattr(summary, "persistence_share", 0.0)), 6),
    )
    return telemetry_signature, summary_signature


def _repro_controls(event) -> list[SimulationControl]:
    return [
        SimulationControl(inject_event=event),
        SimulationControl.noop(),
        SimulationControl.noop(),
        SimulationControl(clear_event_ids=(int(_field(event, "event_id", -1)),)),
        SimulationControl.noop(),
        SimulationControl.noop(),
    ]


def _build_disruption_event(events_mod, *, event_id: int, link_id: int):
    if not hasattr(events_mod, "TrafficEvent") or not hasattr(events_mod, "TrafficEventStatus"):
        pytest.skip("T048 pending: TrafficEvent / TrafficEventStatus exports missing")
    TrafficEvent = events_mod.TrafficEvent
    TrafficEventStatus = events_mod.TrafficEventStatus
    try:
        return TrafficEvent(
            event_id=int(event_id),
            event_type="accident",
            start_tick=1,
            end_tick=6,
            target_scope={"link_ids": (int(link_id),)},
            severity=1.0,
            effect_model="closure",
            status=TrafficEventStatus.SCHEDULED,
        )
    except TypeError as exc:
        if _looks_like_signature_mismatch(exc):
            pytest.skip(f"T048/T049 pending: event constructor/signature not finalized ({exc})")
        raise


def _select_existing_blockable_link_id(state) -> int:
    routing_static = getattr(getattr(state, "static", None), "routing_static", {}) or {}
    road_csr = routing_static.get("road_csr") if isinstance(routing_static, dict) else None
    links = getattr(road_csr, "links", ()) if road_csr is not None else ()
    for link in tuple(links):
        if bool(_field(link, "is_blockable", False)):
            return int(_field(link, "link_id", -1))
    pytest.fail("US3 reproducibility fixture requires at least one blockable link")


def _field(obj: object, name: str, default: object) -> object:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _hotspot_summary_signature(items: object) -> tuple[tuple[int, float, float], ...]:
    try:
        seq = tuple(items)  # type: ignore[arg-type]
    except TypeError:
        return ()
    # Avoid over-coupling to full hotspot ordering/tie-breaks; compare a stable
    # top-1/top-2 subset signature only.
    out: list[tuple[int, float, float]] = []
    for item in seq[:2]:
        if isinstance(item, (tuple, list)):
            raw_link_id = item[0] if len(item) > 0 else -1
            raw_congestion = item[2] if len(item) > 2 else (item[1] if len(item) > 1 else 0.0)
            raw_travel_time = item[3] if len(item) > 3 else (item[2] if len(item) > 2 else 0.0)
        else:
            raw_link_id = _field(item, "link_id", -1)
            raw_congestion = _field(item, "congestion_ratio", 0.0)
            raw_travel_time = _field(item, "travel_time_ratio", 0.0)
        link_id = int(raw_link_id)
        congestion_ratio = float(raw_congestion or 0.0)
        travel_time_ratio = float(raw_travel_time or 0.0)
        out.append((link_id, round(congestion_ratio, 6), round(travel_time_ratio, 6)))
    return tuple(out)


def _looks_like_signature_mismatch(exc: TypeError) -> bool:
    msg = str(exc)
    hints = (
        "unexpected keyword",
        "positional argument",
        "required positional argument",
        "missing",
        "takes",
        "got an unexpected",
    )
    return any(token in msg for token in hints)
