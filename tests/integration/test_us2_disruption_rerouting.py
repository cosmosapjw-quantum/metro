from __future__ import annotations

import runpy
from pathlib import Path

import pytest

from metroflow.sim.config import SimulationConfig
from metroflow.sim.control import SimulationControl
from metroflow.sim.step import init_simulation, run_rollout, validate_invariants

"""Contract-first integration tests for US2 disruption rerouting (T048-T052).

These tests may skip while event scheduling/effects/reroute modules are pending.
Once those modules are implemented, integration behavior assertions should fail
on real rerouting/failure regressions instead of silently skipping broad errors.
"""

_SCENARIOS = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "fixtures" / "simulation_scenarios.py")
)
SEED_REGISTRY = _SCENARIOS["SEED_REGISTRY"]


def test_us2_bridge_disruption_changes_rollout_outcomes_vs_control_pending_t048_t052():
    events_mod = _require_us2_disruption_modules()

    config = SimulationConfig(
        active_agent_capacity=24,
        ui_stream_enabled=False,
        learning_enabled=False,
    )
    baseline_state, baseline_key = init_simulation(
        config=config,
        scenario_seed=SEED_REGISTRY["disruption_bridge_closure"],
    )
    disrupted_state, disrupted_key = init_simulation(
        config=config,
        scenario_seed=SEED_REGISTRY["disruption_bridge_closure"],
    )

    bridge_group_id = _select_existing_bridge_group_id(disrupted_state)
    bridge_event = _build_pending_bridge_closure_event(events_mod, bridge_group_id=bridge_group_id)

    baseline_controls = [SimulationControl.noop() for _ in range(8)]
    disrupted_controls = [SimulationControl(inject_event=bridge_event)] + [
        SimulationControl.noop() for _ in range(7)
    ]

    baseline_final, baseline_telemetry, _ = run_rollout(
        initial_state=baseline_state,
        controls=baseline_controls,
        rng_key=baseline_key,
    )
    disrupted_final, disrupted_telemetry, _ = run_rollout(
        initial_state=disrupted_state,
        controls=disrupted_controls,
        rng_key=disrupted_key,
    )

    assert validate_invariants(baseline_final).ok is True
    assert validate_invariants(disrupted_final).ok is True

    base_totals = (
        sum(item.trip_completed_this_tick for item in baseline_telemetry),
        sum(item.trip_failed_this_tick for item in baseline_telemetry),
    )
    disrupted_totals = (
        sum(item.trip_completed_this_tick for item in disrupted_telemetry),
        sum(item.trip_failed_this_tick for item in disrupted_telemetry),
    )
    base_outcome_timeline = tuple(
        (t.trip_completed_this_tick, t.trip_failed_this_tick, t.active_agent_count)
        for t in baseline_telemetry
    )
    disrupted_outcome_timeline = tuple(
        (t.trip_completed_this_tick, t.trip_failed_this_tick, t.active_agent_count)
        for t in disrupted_telemetry
    )

    # Contract for US2: a major disruption must change observable outcomes for
    # some affected travelers under fixed-seed conditions (totals and/or timing).
    assert disrupted_totals != base_totals or disrupted_outcome_timeline != base_outcome_timeline


def test_us2_blocked_edge_disruption_records_failures_without_crash_pending_t048_t052():
    events_mod = _require_us2_disruption_modules()

    config = SimulationConfig(
        active_agent_capacity=24,
        ui_stream_enabled=False,
        learning_enabled=False,
    )
    state, rng_key = init_simulation(
        config=config,
        scenario_seed=SEED_REGISTRY["disruption_bridge_closure"],
    )
    blocked_link_id = _select_existing_blockable_link_id(state)
    blocked_edge_event = _build_pending_blocked_edge_event(events_mod, link_id=blocked_link_id)

    controls = [SimulationControl(inject_event=blocked_edge_event)] + [
        SimulationControl.noop() for _ in range(11)
    ]
    final_state, telemetry_log, _ = run_rollout(
        initial_state=state,
        controls=controls,
        rng_key=rng_key,
    )

    invariant_report = validate_invariants(final_state)
    assert invariant_report.ok is True

    failed_total = sum(item.trip_failed_this_tick for item in telemetry_log)
    completed_total = sum(item.trip_completed_this_tick for item in telemetry_log)

    # T044 wording explicitly calls for recorded failures under blocked-edge /
    # bridge disruptions. Scenario presets should make at least one failure visible.
    assert failed_total >= 1
    assert completed_total >= 0


def _require_us2_disruption_modules():
    events_mod = pytest.importorskip(
        "metroflow.flow.events",
        reason="T048 pending: flow.events not implemented yet",
    )
    pytest.importorskip(
        "metroflow.flow.event_effects",
        reason="T049 pending: flow.event_effects not implemented yet",
    )
    pytest.importorskip(
        "metroflow.routing.reroute_policy",
        reason="T051 pending: routing.reroute_policy not implemented yet",
    )
    step_mod = pytest.importorskip("metroflow.sim.step")
    if not bool(getattr(step_mod, "_US2_EVENTS_REROUTE_INTEGRATED", False)):
        pytest.skip("T052 pending: sim.step US2 event/reroute integration not implemented yet")
    return events_mod


def _build_pending_bridge_closure_event(events_mod, *, bridge_group_id: int):
    if not hasattr(events_mod, "TrafficEvent") or not hasattr(events_mod, "TrafficEventStatus"):
        pytest.skip("T048 pending: TrafficEvent / TrafficEventStatus exports missing")
    TrafficEvent = events_mod.TrafficEvent
    TrafficEventStatus = events_mod.TrafficEventStatus
    try:
        return TrafficEvent(
            event_id=9001,
            event_type="construction",
            start_tick=1,
            end_tick=20,
            target_scope={"bridge_group_id": int(bridge_group_id)},
            severity=1.0,
            effect_model="closure",
            status=TrafficEventStatus.SCHEDULED,
        )
    except TypeError as exc:
        pytest.skip(f"T048/T049 pending: event constructor or validation not finalized ({exc})")


def _build_pending_blocked_edge_event(events_mod, *, link_id: int):
    if not hasattr(events_mod, "TrafficEvent") or not hasattr(events_mod, "TrafficEventStatus"):
        pytest.skip("T048 pending: TrafficEvent / TrafficEventStatus exports missing")
    TrafficEvent = events_mod.TrafficEvent
    TrafficEventStatus = events_mod.TrafficEventStatus
    try:
        return TrafficEvent(
            event_id=9002,
            event_type="accident",
            start_tick=1,
            end_tick=12,
            target_scope={"link_ids": (int(link_id),)},
            severity=1.0,
            effect_model="closure",
            status=TrafficEventStatus.SCHEDULED,
        )
    except TypeError as exc:
        pytest.skip(f"T048/T049 pending: event constructor or validation not finalized ({exc})")


def _select_existing_bridge_group_id(state) -> int:
    city_topology = getattr(getattr(state, "static", None), "city_topology", None)
    bridge_crossings = getattr(city_topology, "bridge_crossings", ()) if city_topology is not None else ()
    for crossing in tuple(bridge_crossings):
        bridge_group_id = _field(crossing, "bridge_group_id", None)
        if bridge_group_id is not None:
            return int(bridge_group_id)
    pytest.fail("US2 bridge disruption test fixture requires at least one bridge crossing/group")


def _select_existing_blockable_link_id(state) -> int:
    routing_static = getattr(getattr(state, "static", None), "routing_static", {}) or {}
    road_csr = routing_static.get("road_csr") if isinstance(routing_static, dict) else None
    links = getattr(road_csr, "links", ()) if road_csr is not None else ()
    for link in tuple(links):
        if bool(_field(link, "is_blockable", False)):
            return int(_field(link, "link_id", -1))
    pytest.fail("US2 blocked-edge disruption test fixture requires at least one blockable link")


def _field(obj: object, name: str, default: object) -> object:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)
