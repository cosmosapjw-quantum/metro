from __future__ import annotations

from metroflow.ui.packets import (
    UIPacketEnvelope,
    UIPacketType,
    build_ui_packet_envelope,
    validate_ui_packet_envelope,
)


def test_ui_topology_snapshot_packet_contract_shape():
    envelope = build_ui_packet_envelope(
        packet_type=UIPacketType.TOPOLOGY_SNAPSHOT,
        run_id="us1-run",
        tick=0,
        day_type="weekday",
        time_band="morning",
        payload={
            "network_geometry_version": "geom-v1",
            "nodes": ({"node_id": 1, "x": 0.0, "y": 0.0, "kind": "intersection"},),
            "links": (
                {
                    "link_id": 10,
                    "class": "arterial",
                    "bridge": False,
                    "polyline": ((0.0, 0.0), (1.0, 0.0)),
                },
            ),
            "zones": ({"zone_id": 1, "zone_type": "residential", "centroid": (0.2, 0.3)},),
            "bridges": ({"bridge_group_id": 7, "name": "north", "corridor": "river"},),
        },
    )

    assert validate_ui_packet_envelope(envelope) == ()
    packet = envelope.as_dict()
    assert packet["type"] == "ui.topology_snapshot"

    payload = packet["payload"]
    assert set(payload) == {
        "network_geometry_version",
        "nodes",
        "links",
        "zones",
        "bridges",
    }


def test_ui_congestion_frame_packet_contract_shape_and_sampling_mode():
    envelope = build_ui_packet_envelope(
        packet_type=UIPacketType.CONGESTION_FRAME,
        run_id="us1-run",
        tick=12,
        day_type="weekday",
        time_band="evening",
        payload={
            "frame_seq": 3,
            "sampling_mode": "top_k_hotspots",
            "link_congestion": (
                {
                    "link_id": 10,
                    "congestion_level": 0.75,
                    "travel_time_ratio": 1.8,
                },
            ),
            "active_agent_count": 123,
            "dropped_frame_count_since_last": 2,
        },
    )

    restored = UIPacketEnvelope.from_mapping(envelope.as_dict())
    assert validate_ui_packet_envelope(restored) == ()
    assert restored.type is UIPacketType.CONGESTION_FRAME

    payload = restored.payload
    assert set(payload) == {
        "frame_seq",
        "sampling_mode",
        "link_congestion",
        "active_agent_count",
        "dropped_frame_count_since_last",
    }
    assert payload["sampling_mode"] in {
        "full",
        "top_k_hotspots",
        "corridor_focus",
        "downsampled",
    }
    assert set(payload["link_congestion"][0]) == {
        "link_id",
        "congestion_level",
        "travel_time_ratio",
    }


def test_ui_metrics_summary_packet_contract_shape():
    envelope = build_ui_packet_envelope(
        packet_type=UIPacketType.METRICS_SUMMARY,
        run_id="us1-run",
        tick=20,
        day_type="weekend",
        time_band="night",
        payload={
            "trip_generated_total": 10,
            "trip_completed_total": 7,
            "trip_failed_total": 1,
            "capacity_violation_count": 0,
            "policy_mix_lambda": 0.0,
            "adaptive_fallback_active": False,
            "tick_rate_recent_hz": 58.2,
        },
    )

    assert validate_ui_packet_envelope(envelope.as_dict()) == ()

    payload = envelope.payload
    assert set(payload) == {
        "trip_generated_total",
        "trip_completed_total",
        "trip_failed_total",
        "capacity_violation_count",
        "policy_mix_lambda",
        "adaptive_fallback_active",
        "tick_rate_recent_hz",
    }
    assert isinstance(payload["adaptive_fallback_active"], bool)

