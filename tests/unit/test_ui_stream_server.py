from __future__ import annotations

from metroflow.city.generator import SyntheticCityTopology
from metroflow.city.graph import Node, NodeKind, RoadClass, RoadLink
from metroflow.city.zones import Zone
from metroflow.sim.config import SimulationConfig, ZoneType
from metroflow.sim.control import SimulationTelemetry
from metroflow.sim.state import SimulationClockState, SimulationDynamicRefs, SimulationState, SimulationStaticRefs
from metroflow.ui.packets import UIPacketType, build_ui_packet_envelope, validate_ui_packet_envelope
from metroflow.ui.stream_buffer import UISnapshotStreamBuffer
from metroflow.ui.stream_server import NavigatorUIStreamServer


def _make_state(*, tick: int = 0) -> SimulationState:
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
            scenario_id="us1-run",
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
            clock_state=SimulationClockState(tick_index=tick),
            ui_state=UISnapshotStreamBuffer(tick_seconds=1.0, hz_limit=30.0),
            metrics_state={
                "generated_trip_total": 11,
                "completed_trips_total": 7,
                "failed_trips_total": 1,
                "capacity_violation_count": 2,
            },
        ),
    )


def _make_snapshot(*, event_id: int = 1) -> dict:
    return {
        "network_geometry_version": "geom-v1",
        "sampled_link_congestion": (
            {
                "link_id": 10,
                "congestion_ratio": 0.6,
                "slowdown_ratio": 1.4,
            },
        ),
        "active_events": (
            {
                "event_id": event_id,
                "event_type": "construction",
                "status": "active",
                "severity": "medium",
                "target_scope": {"link_ids": [10]},
            },
        ),
        "clock_state": {"day_type": "weekday", "time_band": "morning", "sim_tick": 0},
        "summary_metrics": {
            "completed_trips_total": 7,
            "failed_trips_total": 1,
            "capacity_violation_count": 2,
        },
    }


def _make_telemetry(*, tick: int, ui_snapshot_emitted: bool = True) -> SimulationTelemetry:
    return SimulationTelemetry(
        tick_index=tick,
        active_agent_count=3,
        ui_snapshot_emitted=ui_snapshot_emitted,
    )


def test_stream_server_emits_topology_congestion_event_and_metrics_packets():
    server = NavigatorUIStreamServer(metrics_emit_interval_ticks=1)
    state = _make_state(tick=0)
    packets = server.ingest_step_output(
        state=state,
        telemetry=_make_telemetry(tick=0),
        ui_snapshot_source=_make_snapshot(),
    )

    assert tuple(packet.type for packet in packets) == (
        UIPacketType.TOPOLOGY_SNAPSHOT,
        UIPacketType.CONGESTION_FRAME,
        UIPacketType.EVENT_OVERLAY,
        UIPacketType.METRICS_SUMMARY,
    )
    for packet in packets:
        assert validate_ui_packet_envelope(packet) == ()

    congestion_payload = packets[1].payload
    assert congestion_payload["frame_seq"] == 0
    assert congestion_payload["link_congestion"][0]["link_id"] == 10
    metrics_payload = packets[-1].payload
    assert metrics_payload["trip_generated_total"] == 11
    assert metrics_payload["trip_completed_total"] == 7


def test_stream_server_suppresses_repeat_topology_and_unchanged_event_overlay():
    server = NavigatorUIStreamServer(metrics_emit_interval_ticks=1)
    state0 = _make_state(tick=0)
    _ = server.ingest_step_output(
        state=state0,
        telemetry=_make_telemetry(tick=0),
        ui_snapshot_source=_make_snapshot(event_id=1),
    )

    state1 = state0.with_clock(tick_index=1)
    packets = server.ingest_step_output(
        state=state1,
        telemetry=_make_telemetry(tick=1),
        ui_snapshot_source=_make_snapshot(event_id=1),
    )
    packet_types = tuple(packet.type for packet in packets)
    assert UIPacketType.TOPOLOGY_SNAPSHOT not in packet_types
    assert UIPacketType.EVENT_OVERLAY not in packet_types
    assert UIPacketType.CONGESTION_FRAME in packet_types
    assert UIPacketType.METRICS_SUMMARY in packet_types


def test_stream_server_parses_control_packet_and_returns_ack():
    server = NavigatorUIStreamServer()
    state = _make_state(tick=5)
    packet = build_ui_packet_envelope(
        packet_type=UIPacketType.CONTROL_COMMAND,
        run_id="ui-client",
        tick=5,
        day_type="weekday",
        time_band="morning",
        payload={
            "command_id": "cmd-1",
            "action": "set_time_band",
            "arguments": {"time_band": "evening"},
        },
    )

    control, ack = server.handle_ui_control_packet(packet, state=state)
    assert control.set_time_band is not None
    assert str(control.set_time_band.value) == "evening"
    assert ack.type is UIPacketType.CONTROL_ACK
    assert ack.payload["accepted"] is True
    assert "applied_tick" not in ack.payload
    assert validate_ui_packet_envelope(ack) == ()


def test_stream_server_emits_event_clear_packet_on_transition_to_empty():
    server = NavigatorUIStreamServer(metrics_emit_interval_ticks=10)
    state0 = _make_state(tick=0)
    _ = server.ingest_step_output(
        state=state0,
        telemetry=_make_telemetry(tick=0),
        ui_snapshot_source=_make_snapshot(event_id=1),
    )

    state1 = state0.with_clock(tick_index=1)
    cleared_snapshot = dict(_make_snapshot(event_id=1))
    cleared_snapshot["active_events"] = ()
    packets = server.ingest_step_output(
        state=state1,
        telemetry=_make_telemetry(tick=1),
        ui_snapshot_source=cleared_snapshot,
    )
    event_packets = [p for p in packets if p.type is UIPacketType.EVENT_OVERLAY]
    assert len(event_packets) == 1
    assert event_packets[0].payload["events"] == ()


def test_stream_server_emits_metrics_even_when_congestion_frame_throttled():
    server = NavigatorUIStreamServer(metrics_emit_interval_ticks=1)
    state0 = _make_state(tick=0)
    # Make congestion cadence sparse so tick 1 suppresses the congestion frame.
    state0.dynamic.ui_state.min_emit_interval_ticks = 10
    _ = server.ingest_step_output(
        state=state0,
        telemetry=_make_telemetry(tick=0),
        ui_snapshot_source=_make_snapshot(event_id=1),
    )

    state1 = state0.with_clock(tick_index=1)
    packets = server.ingest_step_output(
        state=state1,
        telemetry=_make_telemetry(tick=1),
        ui_snapshot_source=_make_snapshot(event_id=2),
    )
    packet_types = tuple(packet.type for packet in packets)
    assert UIPacketType.CONGESTION_FRAME not in packet_types
    assert UIPacketType.EVENT_OVERLAY in packet_types
    assert UIPacketType.METRICS_SUMMARY in packet_types
