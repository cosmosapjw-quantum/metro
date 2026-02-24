from __future__ import annotations

import jax.numpy as jnp

from metroflow.city.generator import SyntheticCityTopology
from metroflow.city.graph import Node, NodeKind, RoadClass, RoadLink
from metroflow.flow.state import LinkState
from metroflow.sim.invariants import InvariantCounters, InvariantReport
from metroflow.sim.run_summary import build_baseline_run_summary
from metroflow.sim.state import SimulationClockState, SimulationDynamicRefs, SimulationState, SimulationStaticRefs


def test_build_baseline_run_summary_aggregates_trip_totals_and_hotspots():
    city = SyntheticCityTopology(
        nodes=(
            Node(node_id=1, kind=NodeKind.INTERSECTION, x=0.0, y=0.0),
            Node(node_id=2, kind=NodeKind.INTERSECTION, x=1.0, y=0.0),
            Node(node_id=3, kind=NodeKind.INTERSECTION, x=2.0, y=0.0),
        ),
        links=(
            RoadLink(10, 1, 2, RoadClass.ARTERIAL, 100.0, 10.0, 10.0),
            RoadLink(11, 2, 3, RoadClass.LOCAL, 100.0, 10.0, 10.0),
        ),
        turns=(),
        bridge_crossings=(),
    )
    road_csr = city.build_csr(validate=False)
    link_state = LinkState(
        queue_vehicles=jnp.asarray([9.0, 2.0], dtype=jnp.float32),
        inflow_vehicles=jnp.zeros((2,), dtype=jnp.float32),
        outflow_vehicles=jnp.zeros((2,), dtype=jnp.float32),
        travel_time_cost=jnp.asarray([2.0, 1.2], dtype=jnp.float32),
        capacity_veh_per_tick=jnp.asarray([3.0, 4.0], dtype=jnp.float32),
        incident_capacity_multiplier=jnp.ones((2,), dtype=jnp.float32),
        capacity_violation_flags=jnp.asarray([True, False], dtype=jnp.bool_),
        metadata={"free_flow_travel_time_cost": jnp.asarray([1.0, 1.0], dtype=jnp.float32)},
    )
    state = SimulationState(
        static=SimulationStaticRefs(
            scenario_id="us1-demo",
            city_topology=city,
            routing_static={"road_csr": road_csr},
            metadata={"scenario_seed": 42},
        ),
        dynamic=SimulationDynamicRefs(
            clock_state=SimulationClockState(tick_index=8),
            flow_link_state=link_state,
            metrics_state={
                "generated_trip_total": 100,
                "completed_trips_total": 70,
                "failed_trips_total": 5,
                "active_agents": 12,
                "queued_trip_requests": 30,
                "pending_trip_requests": 35,
                "capacity_violation_count": 1,
                "negative_queue_detected": False,
                "ui_packets_emitted": 4,
            },
        ),
        metadata={"scenario_seed": 42},
    ).with_clock(day_type="weekday", time_band="morning")

    summary = build_baseline_run_summary(
        state,
        ui_packet_counts={"ui.congestion_frame": 2, "ui.metrics_summary": 2},
        hotspot_top_k=2,
    )

    assert summary.scenario_id == "us1-demo"
    assert summary.seed == 42
    assert summary.trip_generation_total == 100
    assert summary.trip_completed_total == 70
    assert summary.trip_failed_total == 5
    assert summary.pending_trip_requests == 35
    assert summary.capacity_violation_count == 1
    assert summary.ui_packets_emitted == 4
    assert summary.hotspot_links_top_k[0]["link_id"] == 10
    assert summary.hotspot_links_top_k[0]["congestion_ratio"] > summary.hotspot_links_top_k[1]["congestion_ratio"]
    assert summary.ui_packet_counts["ui.congestion_frame"] == 2


def test_build_baseline_run_summary_handles_missing_flow_state():
    state = SimulationState(
        static=SimulationStaticRefs(scenario_id="noop"),
        dynamic=SimulationDynamicRefs(
            clock_state=SimulationClockState(tick_index=1),
            metrics_state={"generated_trip_total": 1, "completed_trips_total": 0, "failed_trips_total": 0},
        ),
    )
    summary = build_baseline_run_summary(state, hotspot_top_k=3)
    assert summary.hotspot_links_top_k == ()
    assert summary.trip_generation_total == 1


def test_build_baseline_run_summary_uses_packet_count_sum_and_invariant_fallback():
    state = SimulationState(
        static=SimulationStaticRefs(scenario_id="noop"),
        dynamic=SimulationDynamicRefs(
            clock_state=SimulationClockState(tick_index=2),
            metrics_state={
                "generated_trip_total": 2,
                "completed_trips_total": 1,
                "failed_trips_total": 0,
                "ui_packets_emitted": 1,  # stale/legacy tick-count-like metric
            },
            invariant_state=InvariantReport(
                tick_index=2,
                counters=InvariantCounters(negative_queue_violations=1, total_violations=1),
            ),
        ),
    )
    summary = build_baseline_run_summary(
        state,
        ui_packet_counts={"ui.congestion_frame": 3, "ui.metrics_summary": 1},
    )
    assert summary.ui_packets_emitted == 4
    assert summary.negative_queue_detected is True
