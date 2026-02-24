from __future__ import annotations

from types import SimpleNamespace

import jax.numpy as jnp
import pytest

from metroflow.city.graph import RoadLink, RoadClass
from metroflow.flow.event_effects import (
    apply_active_event_effects_to_link_state,
    compute_incident_capacity_multiplier_from_events,
)
from metroflow.flow.events import TrafficEvent, TrafficEventStatus
from metroflow.flow.state import create_link_state


def test_event_effects_apply_closure_and_capacity_reduction_by_link_and_bridge_group():
    road_csr = _fake_road_csr(
        links=(
            RoadLink(1, 1, 2, RoadClass.ARTERIAL, 100.0, 15.0, 4.0, bridge_group_id=None, is_blockable=True),
            RoadLink(2, 2, 3, RoadClass.BRIDGE, 120.0, 12.0, 3.0, bridge_group_id=7, is_blockable=True),
            RoadLink(3, 3, 4, RoadClass.BRIDGE, 120.0, 12.0, 3.0, bridge_group_id=7, is_blockable=True),
        )
    )
    link_state = create_link_state(3, travel_time_cost=1.0, capacity_veh_per_tick=jnp.asarray([4.0, 3.0, 3.0]))

    events = (
        TrafficEvent(
            event_id=1,
            event_type="construction",
            start_tick=1,
            end_tick=5,
            target_scope={"bridge_group_id": 7},
            severity=1.0,
            effect_model="closure",
            status=TrafficEventStatus.ACTIVE,
        ),
        TrafficEvent(
            event_id=2,
            event_type="accident",
            start_tick=1,
            end_tick=5,
            target_scope={"link_ids": (1,)},
            severity=0.25,
            effect_model="capacity_reduction",
            status=TrafficEventStatus.ACTIVE,
        ),
    )

    result = apply_active_event_effects_to_link_state(
        road_csr=road_csr,
        link_state=link_state,
        active_events=events,
        validate=True,
    )

    assert result.applied_event_ids == (1, 2)
    assert result.ignored_event_ids == ()
    assert set(result.affected_link_ids) == {1, 2, 3}
    assert tuple(float(x) for x in result.link_state.incident_capacity_multiplier.tolist()) == (0.75, 0.0, 0.0)


def test_event_effects_ignore_non_active_unsupported_or_non_blockable_closures():
    road_csr = _fake_road_csr(
        links=(
            RoadLink(10, 1, 2, RoadClass.EXPRESSWAY, 100.0, 20.0, 5.0, is_blockable=False),
            RoadLink(11, 2, 3, RoadClass.ARTERIAL, 80.0, 12.0, 4.0, is_blockable=True),
        )
    )
    multipliers, applied, ignored, affected = compute_incident_capacity_multiplier_from_events(
        road_csr=road_csr,
        active_events=(
            TrafficEvent(
                event_id=11,
                event_type="accident",
                start_tick=1,
                end_tick=4,
                target_scope={"link_ids": (10,)},
                severity=1.0,
                effect_model="closure",
                status=TrafficEventStatus.ACTIVE,
            ),
            TrafficEvent(
                event_id=12,
                event_type="congestion_spike",
                start_tick=1,
                end_tick=4,
                target_scope={"link_ids": (11,)},
                severity=0.4,
                effect_model="demand_spike",
                status=TrafficEventStatus.ACTIVE,
            ),
            TrafficEvent(
                event_id=13,
                event_type="construction",
                start_tick=1,
                end_tick=4,
                target_scope={"link_ids": (11,)},
                severity=1.0,
                effect_model="closure",
                status=TrafficEventStatus.SCHEDULED,
            ),
        ),
    )

    assert tuple(float(x) for x in multipliers.tolist()) == (1.0, 1.0)
    assert applied == ()
    assert set(ignored) == {11, 12, 13}
    assert affected == ()


def test_event_effects_combine_overlapping_events_by_min_multiplier():
    road_csr = _fake_road_csr(
        links=(
            RoadLink(21, 1, 2, RoadClass.ARTERIAL, 100.0, 15.0, 4.0, is_blockable=True),
            RoadLink(22, 2, 3, RoadClass.ARTERIAL, 100.0, 15.0, 4.0, is_blockable=True),
        )
    )
    multipliers, applied, ignored, affected = compute_incident_capacity_multiplier_from_events(
        road_csr=road_csr,
        active_events=(
            TrafficEvent(
                event_id=21,
                event_type="accident",
                start_tick=1,
                end_tick=4,
                target_scope={"link_ids": (21,)},
                severity=0.2,
                effect_model="capacity_reduction",
                status=TrafficEventStatus.ACTIVE,
            ),
            TrafficEvent(
                event_id=22,
                event_type="construction",
                start_tick=1,
                end_tick=4,
                target_scope={"link_ids": (21,)},
                severity=0.8,
                effect_model="capacity_reduction",
                status=TrafficEventStatus.ACTIVE,
            ),
        ),
    )

    assert tuple(float(x) for x in multipliers.tolist()) == pytest.approx((0.2, 1.0))
    assert applied == (21, 22)
    assert ignored == ()
    assert affected == (21,)


def test_event_effects_fail_fast_on_link_axis_mismatch():
    road_csr = _fake_road_csr(
        links=(RoadLink(31, 1, 2, RoadClass.LOCAL, 50.0, 8.0, 2.0, is_blockable=True),)
    )
    with pytest.raises(ValueError, match="LinkState link axis"):
        compute_incident_capacity_multiplier_from_events(
            road_csr=road_csr,
            active_events=(),
            link_count=0,
        )


def test_event_effects_resolve_bridge_group_from_bridge_crossings():
    links = (
        RoadLink(41, 1, 2, RoadClass.ARTERIAL, 100.0, 10.0, 3.0, bridge_group_id=None, is_blockable=True),
        RoadLink(42, 2, 3, RoadClass.ARTERIAL, 100.0, 10.0, 3.0, bridge_group_id=None, is_blockable=True),
        RoadLink(43, 3, 4, RoadClass.ARTERIAL, 100.0, 15.0, 4.0, bridge_group_id=None, is_blockable=True),
    )
    road_csr = _fake_road_csr(
        links=links,
        bridge_crossings=(SimpleNamespace(bridge_group_id=9, link_ids=(41, 42)),),
    )
    multipliers, applied, ignored, affected = compute_incident_capacity_multiplier_from_events(
        road_csr=road_csr,
        active_events=(
            TrafficEvent(
                event_id=41,
                event_type="construction",
                start_tick=1,
                end_tick=5,
                target_scope={"bridge_group_id": 9},
                severity=1.0,
                effect_model="closure",
                status=TrafficEventStatus.ACTIVE,
            ),
        ),
    )

    assert tuple(float(x) for x in multipliers.tolist()) == pytest.approx((0.0, 0.0, 1.0))
    assert applied == (41,)
    assert ignored == ()
    assert affected == (41, 42)


def _fake_road_csr(*, links: tuple[RoadLink, ...], bridge_crossings: tuple[object, ...] = ()):
    return SimpleNamespace(
        links=tuple(links),
        link_count=len(links),
        link_id_to_index={int(link.link_id): idx for idx, link in enumerate(links)},
        bridge_crossings=tuple(bridge_crossings),
    )
