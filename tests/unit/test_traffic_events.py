from __future__ import annotations

import pytest

"""Contract-first tests for T048 traffic event scheduler.

These tests are allowed to skip while `metroflow.flow.events` is pending, but
once the module/API exists they should fail on real behavior bugs instead of
silently skipping broad runtime exceptions.
"""


def test_traffic_event_scheduler_api_contract_pending_t048():
    events_mod = pytest.importorskip(
        "metroflow.flow.events",
        reason="T048 pending: flow.events not implemented yet",
    )

    required = (
        "TrafficEvent",
        "TrafficEventStatus",
        "TrafficEventSchedulerState",
        "advance_traffic_event_scheduler",
    )
    missing = tuple(name for name in required if not hasattr(events_mod, name))
    if missing:
        pytest.skip(f"T048 pending: missing event scheduler API exports: {', '.join(missing)}")

    assert missing == ()


def test_traffic_event_scheduler_activates_and_clears_by_tick_contract_pending_t048():
    events_mod = pytest.importorskip(
        "metroflow.flow.events",
        reason="T048 pending: flow.events not implemented yet",
    )
    required = (
        "TrafficEvent",
        "TrafficEventStatus",
        "TrafficEventSchedulerState",
        "advance_traffic_event_scheduler",
    )
    if any(not hasattr(events_mod, name) for name in required):
        pytest.skip("T048 pending: event scheduler behavior API not implemented yet")

    TrafficEvent = events_mod.TrafficEvent
    TrafficEventStatus = events_mod.TrafficEventStatus
    SchedulerState = events_mod.TrafficEventSchedulerState
    advance = events_mod.advance_traffic_event_scheduler

    try:
        state = SchedulerState(
            scheduled_events=(
                TrafficEvent(
                    event_id=1,
                    event_type="accident",
                    start_tick=10,
                    end_tick=15,
                    target_scope={"link_ids": (10,)},
                    severity=0.8,
                    effect_model="capacity_reduction",
                    status=TrafficEventStatus.SCHEDULED,
                ),
            ),
            active_events=(),
            cleared_events=(),
        )
    except TypeError as exc:
        pytest.skip(f"T048 pending: scheduler constructors/signatures not finalized ({exc})")

    state_at_9 = advance(state, current_tick=9)
    assert len(tuple(_events_from_state(state_at_9, "active_events"))) == 0

    state_at_10 = advance(state_at_9, current_tick=10)
    active_10 = tuple(_events_from_state(state_at_10, "active_events"))
    assert any(int(_get_event_field(evt, "event_id", -1)) == 1 for evt in active_10)
    assert any(
        _coerce_status(_get_event_field(evt, "status", "")) == "active"
        for evt in active_10
    )

    # `end_tick` inclusive/exclusive semantics are not explicit in the current
    # data-model text. Assert a weaker, stable contract: the event must be
    # cleared no later than the first tick after `end_tick`.
    state_end = advance(state_at_10, current_tick=15)
    state_end_plus_1 = advance(state_end, current_tick=16)
    active_16 = tuple(_events_from_state(state_end_plus_1, "active_events"))
    assert not any(int(_get_event_field(evt, "event_id", -1)) == 1 for evt in active_16)
    cleared_16 = tuple(_events_from_state(state_end_plus_1, "cleared_events"))
    assert any(int(_get_event_field(evt, "event_id", -1)) == 1 for evt in cleared_16)


def test_traffic_event_scheduler_supports_explicit_clear_ids_contract_pending_t048():
    events_mod = pytest.importorskip(
        "metroflow.flow.events",
        reason="T048 pending: flow.events not implemented yet",
    )
    required = (
        "TrafficEvent",
        "TrafficEventStatus",
        "TrafficEventSchedulerState",
        "advance_traffic_event_scheduler",
    )
    if any(not hasattr(events_mod, name) for name in required):
        pytest.skip("T048 pending: explicit clear contract pending event scheduler API")

    TrafficEvent = events_mod.TrafficEvent
    TrafficEventStatus = events_mod.TrafficEventStatus
    SchedulerState = events_mod.TrafficEventSchedulerState
    advance = events_mod.advance_traffic_event_scheduler

    try:
        state = SchedulerState(
            scheduled_events=(),
            active_events=(
                TrafficEvent(
                    event_id=7,
                    event_type="construction",
                    start_tick=1,
                    end_tick=99,
                    target_scope={"bridge_group_id": 3},
                    severity=1.0,
                    effect_model="closure",
                    status=TrafficEventStatus.ACTIVE,
                ),
            ),
            cleared_events=(),
        )
    except TypeError as exc:
        pytest.skip(f"T048 pending: scheduler constructors/signatures not finalized ({exc})")

    try:
        cleared = advance(state, current_tick=5, clear_event_ids=(7,))
    except TypeError:
        pytest.skip("T048 pending: advance_traffic_event_scheduler clear_event_ids parameter not implemented yet")

    active = tuple(_events_from_state(cleared, "active_events"))
    assert not any(int(_get_event_field(evt, "event_id", -1)) == 7 for evt in active)
    cleared_events = tuple(_events_from_state(cleared, "cleared_events"))
    assert any(int(_get_event_field(evt, "event_id", -1)) == 7 for evt in cleared_events)


def test_traffic_event_scheduler_state_rejects_duplicate_ids_and_bucket_status_mismatch():
    events_mod = pytest.importorskip("metroflow.flow.events")
    TrafficEvent = events_mod.TrafficEvent
    TrafficEventStatus = events_mod.TrafficEventStatus
    SchedulerState = events_mod.TrafficEventSchedulerState

    with pytest.raises(ValueError, match="duplicate event_id"):
        SchedulerState(
            scheduled_events=(
                TrafficEvent(
                    event_id=11,
                    event_type="accident",
                    start_tick=1,
                    end_tick=3,
                    target_scope={"link_ids": (1,)},
                    severity=0.5,
                    effect_model="closure",
                    status=TrafficEventStatus.SCHEDULED,
                ),
            ),
            active_events=(
                TrafficEvent(
                    event_id=11,
                    event_type="construction",
                    start_tick=1,
                    end_tick=4,
                    target_scope={"link_ids": (2,)},
                    severity=0.8,
                    effect_model="capacity_reduction",
                    status=TrafficEventStatus.ACTIVE,
                ),
            ),
            cleared_events=(),
        )

    with pytest.raises(ValueError, match="scheduled_events"):
        SchedulerState(
            scheduled_events=(
                TrafficEvent(
                    event_id=12,
                    event_type="accident",
                    start_tick=1,
                    end_tick=5,
                    target_scope={"link_ids": (3,)},
                    severity=0.5,
                    effect_model="closure",
                    status=TrafficEventStatus.ACTIVE,
                ),
            ),
            active_events=(),
            cleared_events=(),
        )


def test_traffic_event_rejects_severity_outside_unit_interval():
    events_mod = pytest.importorskip("metroflow.flow.events")
    TrafficEvent = events_mod.TrafficEvent

    with pytest.raises(ValueError, match="severity"):
        TrafficEvent(
            event_id=99,
            event_type="congestion_spike",
            start_tick=1,
            end_tick=2,
            target_scope={"corridor_id": "c1"},
            severity=1.5,
            effect_model="demand_spike",
            status="scheduled",
        )


def _events_from_state(state: object, field_name: str) -> tuple[object, ...]:
    if isinstance(state, dict):
        value = state.get(field_name, ())
    else:
        value = getattr(state, field_name, ())
    try:
        return tuple(value)
    except TypeError:
        return ()


def _get_event_field(event: object, field_name: str, default: object) -> object:
    if isinstance(event, dict):
        return event.get(field_name, default)
    return getattr(event, field_name, default)


def _coerce_status(value: object) -> str:
    return str(getattr(value, "value", value)).lower()
