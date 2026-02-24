from __future__ import annotations

import runpy
from pathlib import Path

import pytest

from metroflow.sim.config import DayType, SimulationConfig, TimeBand
from metroflow.sim.control import SimulationControl
from metroflow.sim.step import init_simulation, run_rollout, simulation_step, validate_invariants

"""Contract-first US2 boundary/invariant regression tests (T047).

These tests may skip until US2 event/effects/reroute modules exist (T048-T052).
Once implemented, they should exercise disruption + time-transition boundaries
without hiding real invariant regressions.
"""

_SCENARIOS = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "fixtures" / "simulation_scenarios.py")
)
SEED_REGISTRY = _SCENARIOS["SEED_REGISTRY"]


def test_us2_blocked_edge_with_day_time_transitions_keeps_invariants_green_pending_t048_t052():
    events_mod = _require_us2_disruption_modules()
    config = SimulationConfig(
        active_agent_capacity=24,
        ui_stream_enabled=False,
        learning_enabled=False,
    )
    state, rng_key = init_simulation(
        config=config,
        scenario_seed=SEED_REGISTRY["disruption_boundary"],
    )
    blocked_link_id = _select_existing_blockable_link_id(state)
    event = _build_disruption_event(events_mod, event_id=9201, link_id=blocked_link_id, end_tick=10)

    state_1, telemetry_1, _ui_1, rng_key_1 = simulation_step(
        state=state,
        control=SimulationControl(inject_event=event),
        rng_key=rng_key,
    )
    _assert_event_seen_in_state_boundary(state_1, event_id=9201)

    controls = [
        SimulationControl.noop(),
        SimulationControl(set_day_type=DayType.WEEKEND),
        SimulationControl(set_time_band=TimeBand.EVENING),
        SimulationControl(set_day_type=DayType.WEEKDAY, set_time_band=TimeBand.NIGHT),
        SimulationControl(clear_event_ids=(9201,)),
        SimulationControl.noop(),
        SimulationControl.noop(),
    ]
    final_state, telemetry_log, _ = run_rollout(
        initial_state=state_1,
        controls=controls,
        rng_key=rng_key_1,
    )
    report = validate_invariants(final_state)

    assert telemetry_1.tick_index == 1
    assert len(telemetry_log) == len(controls)
    assert final_state.tick_index == 1 + len(controls)
    assert final_state.day_type == DayType.WEEKDAY
    assert final_state.time_band == TimeBand.NIGHT
    assert report.ok is True
    assert report.counters.total_violations == 0
    assert all(item.tick_index >= 1 for item in telemetry_log)


def test_us2_pause_toggle_clear_boundary_does_not_advance_tick_or_break_invariants_pending_t048_t052():
    events_mod = _require_us2_disruption_modules()
    config = SimulationConfig(
        active_agent_capacity=16,
        ui_stream_enabled=False,
        learning_enabled=False,
    )
    state, rng_key = init_simulation(
        config=config,
        scenario_seed=SEED_REGISTRY["disruption_boundary"],
    )
    blocked_link_id = _select_existing_blockable_link_id(state)
    event = _build_disruption_event(events_mod, event_id=9202, link_id=blocked_link_id, end_tick=8)

    # Step 1: inject a disruption normally so later clear/toggle boundary is meaningful.
    state_1, telemetry_1, _ui_1, rng_key_1 = simulation_step(
        state=state,
        control=SimulationControl(inject_event=event),
        rng_key=rng_key,
    )
    _assert_event_seen_in_state_boundary(state_1, event_id=9202)
    # Step 2: pause + time toggle + explicit clear_event_ids should update labels
    # and preserve invariant safety. Tick advancement behavior is intentionally
    # not overconstrained here because pause/event-clear ordering is a US2
    # integration detail not yet fixed in the data-model text.
    state_2, telemetry_2, _ui_2, _rng_key_2 = simulation_step(
        state=state_1,
        control=SimulationControl(
            pause=True,
            set_day_type=DayType.WEEKEND,
            set_time_band=TimeBand.LUNCH,
            clear_event_ids=(9202,),
        ),
        rng_key=rng_key_1,
    )
    report = validate_invariants(state_2)

    assert state_1.tick_index == 1
    assert telemetry_1.tick_index == 1
    assert state_2.tick_index in {state_1.tick_index, state_1.tick_index + 1}
    assert telemetry_2.tick_index == state_2.tick_index
    assert state_2.day_type == DayType.WEEKEND
    assert state_2.time_band == TimeBand.LUNCH
    assert report.ok is True
    assert report.counters.total_violations == 0


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


def _build_disruption_event(events_mod, *, event_id: int, link_id: int, end_tick: int):
    if not hasattr(events_mod, "TrafficEvent") or not hasattr(events_mod, "TrafficEventStatus"):
        pytest.skip("T048 pending: TrafficEvent / TrafficEventStatus exports missing")
    TrafficEvent = events_mod.TrafficEvent
    TrafficEventStatus = events_mod.TrafficEventStatus
    try:
        return TrafficEvent(
            event_id=int(event_id),
            event_type="accident",
            start_tick=1,
            end_tick=int(end_tick),
            target_scope={"link_ids": (int(link_id),)},
            severity=1.0,
            effect_model="closure",
            status=TrafficEventStatus.SCHEDULED,
        )
    except TypeError as exc:
        pytest.skip(f"T048/T049 pending: event constructor/signature not finalized ({exc})")


def _select_existing_blockable_link_id(state) -> int:
    routing_static = getattr(getattr(state, "static", None), "routing_static", {}) or {}
    road_csr = routing_static.get("road_csr") if isinstance(routing_static, dict) else None
    links = getattr(road_csr, "links", ()) if road_csr is not None else ()
    best: tuple[int, float, int] | None = None
    for link in tuple(links):
        if not bool(_field(link, "is_blockable", False)):
            continue
        road_class = str(_field(_field(link, "road_class", "local"), "value", _field(link, "road_class", "local")))
        priority = {
            "bridge": 0,
            "arterial": 1,
            "expressway": 2,
            "ramp": 3,
            "local": 4,
        }.get(road_class, 9)
        capacity = float(_field(link, "capacity_veh_per_tick", 0.0) or 0.0)
        link_id = int(_field(link, "link_id", -1))
        candidate = (priority, -capacity, link_id)
        if best is None or candidate < best:
            best = candidate
    if best is not None:
        return int(best[2])
    pytest.fail("US2 boundary invariant fixture requires at least one blockable link")


def _field(obj: object, name: str, default: object) -> object:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _assert_event_seen_in_state_boundary(state, *, event_id: int) -> None:
    event_state = getattr(getattr(state, "dynamic", None), "event_state", None)
    if event_state is None:
        pytest.fail("US2 boundary invariant test requires non-null event_state after event injection")
    ids: set[int] = set()
    for field_name in ("scheduled_events", "active_events", "cleared_events"):
        container = getattr(event_state, field_name, ())
        try:
            values = tuple(container)
        except TypeError:
            values = ()
        for event in values:
            try:
                ids.add(int(_field(event, "event_id", -1)))
            except Exception:
                continue
    assert int(event_id) in ids
