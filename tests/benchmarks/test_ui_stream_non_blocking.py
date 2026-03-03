from __future__ import annotations

from metroflow.city.generator import SyntheticCityTopology
from metroflow.city.graph import Node, NodeKind, RoadClass, RoadLink
from metroflow.city.zones import Zone
from metroflow.sim.config import SimulationConfig, ZoneType
from metroflow.sim.control import SimulationTelemetry
from metroflow.sim.state import SimulationClockState, SimulationDynamicRefs, SimulationState, SimulationStaticRefs
from metroflow.ui.packets import UIPacketType, validate_ui_packet_envelope
from metroflow.ui.stream_buffer import UISnapshotStreamBuffer
from metroflow.ui.stream_server import NavigatorUIStreamServer


def test_ui_stream_slow_consumer_coalesces_frames_without_blocking_tick_progress():
    server = NavigatorUIStreamServer(metrics_emit_interval_ticks=1)
    state = _make_state()

    congestion_packets = []
    metrics_count = 0
    topology_count = 0
    event_count = 0

    for tick in range(33):
        state = state.with_clock(tick_index=tick)
        packets = server.ingest_step_output(
            state=state,
            telemetry=_make_telemetry(tick=tick),
            ui_snapshot_source=_make_snapshot(tick=tick),
        )
        for packet in packets:
            assert validate_ui_packet_envelope(packet) == ()
            if packet.type is UIPacketType.CONGESTION_FRAME:
                congestion_packets.append(packet)
            elif packet.type is UIPacketType.METRICS_SUMMARY:
                metrics_count += 1
            elif packet.type is UIPacketType.TOPOLOGY_SNAPSHOT:
                topology_count += 1
            elif packet.type is UIPacketType.EVENT_OVERLAY:
                event_count += 1

    buffer = state.dynamic.ui_state
    assert isinstance(buffer, UISnapshotStreamBuffer)
    assert metrics_count == 33
    assert topology_count == 1
    assert event_count == 1
    assert len(congestion_packets) == 5
    assert [int(packet.payload["frame_seq"]) for packet in congestion_packets] == [0, 1, 2, 3, 4]
    assert int(congestion_packets[0].payload["dropped_frame_count_since_last"]) == 0
    assert all(
        int(packet.payload["dropped_frame_count_since_last"]) == 7
        for packet in congestion_packets[1:]
    )
    assert buffer.stats.offered == 33
    assert buffer.stats.emitted == 5
    assert buffer.stats.dropped_coalesced == 28
    assert buffer.has_pending_snapshot is False


def _make_state() -> SimulationState:
    city = SyntheticCityTopology(
        nodes=(
            Node(node_id=1, kind=NodeKind.INTERSECTION, x=0.0, y=0.0),
            Node(node_id=2, kind=NodeKind.INTERSECTION, x=1.0, y=0.0),
        ),
        links=(
            RoadLink(
                link_id=10,
                src_node_id=1,
                dst_node_id=2,
                road_class=RoadClass.ARTERIAL,
                length_m=100.0,
                free_flow_speed_mps=10.0,
                capacity_veh_per_tick=5.0,
            ),
        ),
        turns=(),
        bridge_crossings=(),
        metadata={},
    )
    road_csr = city.build_csr(validate=False)
    return SimulationState(
        config=SimulationConfig(ui_stream_enabled=True, tick_seconds=1.0),
        static=SimulationStaticRefs(
            scenario_id="ui-non-blocking",
            city_topology=city,
            zones=(
                Zone(
                    zone_id=1,
                    zone_type=ZoneType.RESIDENTIAL,
                    centroid_x=0.1,
                    centroid_y=0.1,
                    population_capacity=100,
                ),
            ),
            routing_static={"road_csr": road_csr},
            ui_network_geometry_version="geom-v1",
        ),
        dynamic=SimulationDynamicRefs(
            clock_state=SimulationClockState(tick_index=0),
            ui_state=UISnapshotStreamBuffer(tick_seconds=1.0, hz_limit=0.125),
            metrics_state={
                "generated_trip_total": 33,
                "completed_trips_total": 12,
                "failed_trips_total": 1,
                "capacity_violation_count": 0,
            },
        ),
    )


def _make_snapshot(*, tick: int) -> dict:
    return {
        "network_geometry_version": "geom-v1",
        "sampled_link_congestion": (
            {
                "link_id": 10,
                "congestion_ratio": min(1.0, 0.1 + 0.02 * tick),
                "slowdown_ratio": 1.0 + 0.01 * tick,
            },
        ),
        "active_events": (
            {
                "event_id": 1,
                "event_type": "construction",
                "status": "active",
                "severity": "medium",
                "target_scope": {"link_ids": [10]},
            },
        ),
        "clock_state": {"day_type": "weekday", "time_band": "morning", "sim_tick": tick},
        "summary_metrics": {
            "completed_trips_total": 12,
            "failed_trips_total": 1,
            "capacity_violation_count": 0,
        },
    }


def _make_telemetry(*, tick: int) -> SimulationTelemetry:
    return SimulationTelemetry(
        tick_index=tick,
        active_agent_count=10 + tick,
        ui_snapshot_emitted=True,
    )
