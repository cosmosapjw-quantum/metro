from __future__ import annotations

import runpy
from pathlib import Path

import pytest

from metroflow.sim.active_agents import (
    ActiveAgentSlot,
    allocate_active_agent_slot,
    create_active_agent_pool,
    read_active_agent_slot,
)
from metroflow.sim.config import DayType, SimulationConfig, TimeBand
from metroflow.sim.control import SimulationControl
from metroflow.sim.step import init_simulation, simulation_step

_SCENARIOS = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "fixtures" / "simulation_scenarios.py")
)
SEED_REGISTRY = _SCENARIOS["SEED_REGISTRY"]


def test_day_time_toggle_changes_clock_context_without_mutating_in_flight_or_future_trips():
    config = SimulationConfig(
        active_agent_capacity=4,
        ui_stream_enabled=False,
        learning_enabled=False,
    )
    state, rng_key = init_simulation(
        config=config,
        scenario_seed=SEED_REGISTRY["day_time_transition"],
    )

    pool = create_active_agent_pool(4)
    pool, slot_id = allocate_active_agent_slot(
        pool,
        ActiveAgentSlot.spawn(
            citizen_id=101,
            trip_id=5001,
            current_link_id=900,
            dest_node_id=901,
            behavior_profile_id=1,
            progress_01=0.4,
            remaining_route_ptr=3,
        ),
    )
    future_trip_requests = (
        {
            "trip_request_id": 1,
            "planned_depart_tick": 10,
            "day_type": "weekday",
            "time_band": "lunch",
        },
        {
            "trip_request_id": 2,
            "planned_depart_tick": 20,
            "day_type": "weekday",
            "time_band": "evening",
        },
    )
    state = state.with_dynamic_updates(
        active_agent_pool=pool,
        demand_state={
            "queued_trip_requests": len(future_trip_requests),
            "pending_trip_requests_payload": future_trip_requests,
        },
    )

    before_slot = read_active_agent_slot(state.dynamic.active_agent_pool, slot_id)
    before_future = tuple(state.dynamic.demand_state["pending_trip_requests_payload"])

    next_state, telemetry, ui_snapshot_source, _ = simulation_step(
        state=state,
        control=SimulationControl(set_day_type="weekend", set_time_band="night"),
        rng_key=rng_key,
    )

    after_slot = read_active_agent_slot(next_state.dynamic.active_agent_pool, slot_id)
    after_future = tuple(next_state.dynamic.demand_state["pending_trip_requests_payload"])

    assert next_state.tick_index == 1
    assert next_state.day_type == DayType.WEEKEND
    assert next_state.time_band == TimeBand.NIGHT
    assert telemetry.tick_index == 1
    assert telemetry.active_agent_count == 1
    assert telemetry.ui_snapshot_emitted is False
    assert ui_snapshot_source is None

    # Control overrides change global routing/generation context only; they do
    # not retroactively rewrite active or already-scheduled trip placeholders.
    assert after_slot.trip_id == before_slot.trip_id
    assert after_slot.citizen_id == before_slot.citizen_id
    assert after_slot.current_link_id == before_slot.current_link_id
    assert after_slot.progress_01 == pytest.approx(before_slot.progress_01)
    assert after_future == before_future


def test_day_time_toggle_while_paused_updates_clock_labels_but_not_tick_index():
    config = SimulationConfig(
        active_agent_capacity=2,
        ui_stream_enabled=False,
        learning_enabled=False,
    )
    state, rng_key = init_simulation(
        config=config,
        scenario_seed=SEED_REGISTRY["day_time_transition"],
    )

    next_state, telemetry, ui_snapshot_source, _ = simulation_step(
        state=state,
        control=SimulationControl(
            pause=True,
            set_day_type=DayType.WEEKEND,
            set_time_band=TimeBand.EVENING,
        ),
        rng_key=rng_key,
    )

    assert next_state.tick_index == 0
    assert telemetry.tick_index == 0
    assert next_state.day_type == DayType.WEEKEND
    assert next_state.time_band == TimeBand.EVENING
    assert telemetry.ui_snapshot_emitted is False
    assert ui_snapshot_source is None
