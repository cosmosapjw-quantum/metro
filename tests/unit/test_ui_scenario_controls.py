from __future__ import annotations

import pytest

from metroflow.flow.events import TrafficEvent
from metroflow.sim.config import DayType, TimeBand
from metroflow.ui.scenario_controls import (
    build_disruption_scenario_controls,
    list_disruption_scenario_presets,
)


def test_list_disruption_scenario_presets_contains_expected_ids():
    presets = list_disruption_scenario_presets()
    ids = {p.preset_id for p in presets}
    assert {"bridge_closure_peak", "blocked_edge_accident", "boundary_toggle_clear"} <= ids


def test_bridge_closure_peak_preset_builds_inject_and_clear_controls():
    controls = build_disruption_scenario_controls(
        "bridge_closure_peak",
        bridge_group_id=3,
        event_id=9101,
        start_tick=1,
        duration_ticks=3,
    )
    assert len(controls) >= 4
    first = controls[0]
    assert isinstance(first.inject_event, TrafficEvent)
    assert first.inject_event.event_id == 9101
    assert first.inject_event.target_scope == {"bridge_group_id": 3}
    assert first.ui_force_snapshot is True
    assert any(int(9101) in tuple(c.clear_event_ids) for c in controls)


def test_boundary_toggle_clear_preset_includes_pause_and_time_toggles():
    controls = build_disruption_scenario_controls(
        "boundary_toggle_clear",
        link_id=42,
        event_id=9202,
    )
    assert isinstance(controls[0].inject_event, TrafficEvent)
    assert controls[1].set_day_type == DayType.WEEKEND
    assert controls[2].set_time_band == TimeBand.EVENING
    pause_clear = next(c for c in controls if c.pause and c.clear_event_ids)
    assert pause_clear.pause is True
    assert pause_clear.set_day_type == DayType.WEEKDAY
    assert pause_clear.set_time_band == TimeBand.NIGHT
    assert pause_clear.clear_event_ids == (9202,)


def test_required_target_ids_are_validated():
    with pytest.raises(ValueError):
        build_disruption_scenario_controls("bridge_closure_peak")
    with pytest.raises(ValueError):
        build_disruption_scenario_controls("blocked_edge_accident")
    with pytest.raises(ValueError):
        build_disruption_scenario_controls("bridge_closure_peak", bridge_group_id=-1)
    with pytest.raises(ValueError):
        build_disruption_scenario_controls("blocked_edge_accident", link_id=-5)


def test_default_event_ids_are_unique_across_repeated_preset_builds():
    c1 = build_disruption_scenario_controls("blocked_edge_accident", link_id=11)
    c2 = build_disruption_scenario_controls("blocked_edge_accident", link_id=11)
    e1 = c1[0].inject_event
    e2 = c2[0].inject_event
    assert isinstance(e1, TrafficEvent) and isinstance(e2, TrafficEvent)
    assert e1.event_id != e2.event_id


def test_boundary_preset_duration_and_current_tick_are_reflected_in_event_timing_and_clear_step():
    controls = build_disruption_scenario_controls(
        "boundary_toggle_clear",
        link_id=7,
        event_id=9307,
        current_tick=100,
        start_tick=2,
        duration_ticks=3,
    )
    event = controls[0].inject_event
    assert isinstance(event, TrafficEvent)
    assert event.start_tick == 102
    assert event.end_tick == 105
    clear_idx = next(i for i, c in enumerate(controls) if c.clear_event_ids == (9307,))
    assert clear_idx > 3  # duration padding inserted before pause+clear step
