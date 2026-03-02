from __future__ import annotations

import jax
import jax.numpy as jnp
import pytest

from metroflow.city.generator import SyntheticCityTopology
from metroflow.city.graph import Node, NodeKind, RoadClass, RoadLink
from metroflow.flow.events import TrafficEvent, TrafficEventSchedulerState, TrafficEventStatus
from metroflow.flow.state import LinkState
from metroflow.sim.invariants import InvariantCounters, InvariantReport
from metroflow.sim.run_summary import (
    BaselineRunSummary,
    build_baseline_run_summary,
    build_run_summary_comparison,
    format_run_summary_comparison_markdown,
    run_summary_comparison_deltas_core,
)
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
    assert summary.reroute_decisions_total == 0
    assert summary.persistence_decisions_total == 0
    assert summary.corridor_shift_count == 0
    assert summary.disruption_response_metrics_available is False
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


def test_build_baseline_run_summary_includes_us2_disruption_response_metrics():
    event = TrafficEvent(
        event_id=7001,
        event_type="accident",
        start_tick=1,
        end_tick=10,
        target_scope={"link_ids": (10,)},
        severity=0.6,
        effect_model={"kind": "capacity_reduction", "multiplier": 0.4},
        status=TrafficEventStatus.ACTIVE,
    )
    state = SimulationState(
        static=SimulationStaticRefs(scenario_id="us2-demo"),
        dynamic=SimulationDynamicRefs(
            clock_state=SimulationClockState(tick_index=5),
            event_state=TrafficEventSchedulerState(active_events=(event,)),
            metrics_state={
                "generated_trip_total": 20,
                "completed_trips_total": 7,
                "failed_trips_total": 2,
                "us2_reroute_decisions_total": 6,
                "us2_persistence_decisions_total": 4,
                "us2_corridor_shift_count_total": 3,
            },
            metadata={"us2_active_event_affected_link_ids": (10, 11, 12)},
        ),
    )
    summary = build_baseline_run_summary(state)
    assert summary.disruption_active_event_count == 1
    assert summary.disruption_affected_link_count == 3
    assert summary.reroute_decisions_total == 6
    assert summary.persistence_decisions_total == 4
    assert summary.corridor_shift_count == 3
    assert summary.reroute_share == pytest.approx(0.6)
    assert summary.persistence_share == pytest.approx(0.4)
    assert summary.corridor_shift_share == pytest.approx(0.5)
    assert summary.disruption_response_metrics_available is True


def test_build_run_summary_comparison_reports_adaptive_deltas_and_rates():
    baseline = BaselineRunSummary(
        scenario_id="compare-demo",
        seed=42,
        tick_index=8,
        day_type="weekday",
        time_band="morning",
        trip_generation_total=100,
        trip_completed_total=60,
        trip_failed_total=10,
        active_agents=15,
        queued_trip_requests=30,
        pending_trip_requests=35,
        capacity_violation_count=2,
        negative_queue_detected=False,
        ui_packets_emitted=0,
        reroute_share=0.2,
        persistence_share=0.8,
        corridor_shift_share=0.1,
    )
    adaptive = BaselineRunSummary(
        scenario_id="compare-demo",
        seed=42,
        tick_index=8,
        day_type="weekday",
        time_band="morning",
        trip_generation_total=100,
        trip_completed_total=68,
        trip_failed_total=7,
        active_agents=12,
        queued_trip_requests=24,
        pending_trip_requests=28,
        capacity_violation_count=1,
        negative_queue_detected=False,
        ui_packets_emitted=0,
        reroute_share=0.35,
        persistence_share=0.65,
        corridor_shift_share=0.25,
    )

    comparison = build_run_summary_comparison(baseline, adaptive)
    md = format_run_summary_comparison_markdown(comparison)

    assert comparison.trip_completed_total_delta == 8
    assert comparison.trip_failed_total_delta == -3
    assert comparison.trip_completion_rate_delta == pytest.approx(0.08)
    assert comparison.trip_failure_rate_delta == pytest.approx(-0.03)
    assert comparison.queued_trip_requests_delta == -6
    assert comparison.capacity_violation_count_delta == -1
    assert comparison.adaptive_improved_completion is True
    assert comparison.adaptive_reduced_failures is True
    assert "Completed trips delta" in md
    assert "+8" in md


def test_build_run_summary_comparison_accepts_mapping_inputs():
    comparison = build_run_summary_comparison(
        {
            "scenario_id": "mapping-demo",
            "seed": 5,
            "tick_index": 4,
            "day_type": "weekday",
            "time_band": "night",
            "trip_generation_total": 10,
            "trip_completed_total": 4,
            "trip_failed_total": 1,
            "active_agents": 3,
            "queued_trip_requests": 5,
            "pending_trip_requests": 6,
            "capacity_violation_count": 0,
            "negative_queue_detected": False,
            "ui_packets_emitted": 0,
        },
        {
            "scenario_id": "mapping-demo",
            "seed": 5,
            "tick_index": 4,
            "day_type": "weekday",
            "time_band": "night",
            "trip_generation_total": 10,
            "trip_completed_total": 5,
            "trip_failed_total": 1,
            "active_agents": 2,
            "queued_trip_requests": 4,
            "pending_trip_requests": 5,
            "capacity_violation_count": 0,
            "negative_queue_detected": False,
            "ui_packets_emitted": 0,
        },
    )

    assert comparison.scenario_id == "mapping-demo"
    assert comparison.trip_completed_total_delta == 1


def test_build_run_summary_comparison_rejects_mismatched_experiment_identity():
    baseline = BaselineRunSummary(
        scenario_id="baseline-demo",
        seed=5,
        tick_index=4,
        day_type="weekday",
        time_band="night",
        trip_generation_total=10,
        trip_completed_total=4,
        trip_failed_total=1,
        active_agents=3,
        queued_trip_requests=5,
        pending_trip_requests=6,
        capacity_violation_count=0,
        negative_queue_detected=False,
        ui_packets_emitted=0,
    )
    adaptive = BaselineRunSummary(
        scenario_id="adaptive-demo",
        seed=6,
        tick_index=4,
        day_type="weekday",
        time_band="night",
        trip_generation_total=10,
        trip_completed_total=5,
        trip_failed_total=1,
        active_agents=2,
        queued_trip_requests=4,
        pending_trip_requests=5,
        capacity_violation_count=0,
        negative_queue_detected=False,
        ui_packets_emitted=0,
    )

    with pytest.raises(ValueError, match="not comparable"):
        build_run_summary_comparison(baseline, adaptive)


def test_run_summary_comparison_deltas_core_supports_jax_jit():
    compiled = jax.jit(run_summary_comparison_deltas_core)
    deltas = compiled(
        baseline_trip_generation_total=jnp.asarray(100, dtype=jnp.int32),
        adaptive_trip_generation_total=jnp.asarray(100, dtype=jnp.int32),
        baseline_trip_completed_total=jnp.asarray(60, dtype=jnp.int32),
        adaptive_trip_completed_total=jnp.asarray(68, dtype=jnp.int32),
        baseline_trip_failed_total=jnp.asarray(10, dtype=jnp.int32),
        adaptive_trip_failed_total=jnp.asarray(7, dtype=jnp.int32),
        baseline_active_agents=jnp.asarray(15, dtype=jnp.int32),
        adaptive_active_agents=jnp.asarray(12, dtype=jnp.int32),
        baseline_queued_trip_requests=jnp.asarray(30, dtype=jnp.int32),
        adaptive_queued_trip_requests=jnp.asarray(24, dtype=jnp.int32),
        baseline_pending_trip_requests=jnp.asarray(35, dtype=jnp.int32),
        adaptive_pending_trip_requests=jnp.asarray(28, dtype=jnp.int32),
        baseline_capacity_violation_count=jnp.asarray(2, dtype=jnp.int32),
        adaptive_capacity_violation_count=jnp.asarray(1, dtype=jnp.int32),
        baseline_reroute_share=jnp.asarray(0.2, dtype=jnp.float32),
        adaptive_reroute_share=jnp.asarray(0.35, dtype=jnp.float32),
        baseline_persistence_share=jnp.asarray(0.8, dtype=jnp.float32),
        adaptive_persistence_share=jnp.asarray(0.65, dtype=jnp.float32),
        baseline_corridor_shift_share=jnp.asarray(0.1, dtype=jnp.float32),
        adaptive_corridor_shift_share=jnp.asarray(0.25, dtype=jnp.float32),
    )

    assert int(deltas[0]) == 8
    assert int(deltas[1]) == -3
    assert float(deltas[2]) == pytest.approx(0.08)
    assert float(deltas[3]) == pytest.approx(-0.03)
