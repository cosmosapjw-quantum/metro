from __future__ import annotations

import pytest

from metroflow.ui.packets import (
    UI_PACKET_SCHEMA_VERSION,
    UIPacketEnvelope,
    UIPacketType,
    UISimTimeRef,
    assert_supported_ui_packet_schema_version,
    build_ui_packet_envelope,
    current_ui_packet_schema_version,
    is_supported_ui_packet_schema_version,
    validate_ui_packet_envelope,
)


def test_ui_packet_schema_version_helpers():
    assert current_ui_packet_schema_version() == UI_PACKET_SCHEMA_VERSION
    assert is_supported_ui_packet_schema_version(UI_PACKET_SCHEMA_VERSION) is True
    assert is_supported_ui_packet_schema_version(UI_PACKET_SCHEMA_VERSION + 1) is False

    assert_supported_ui_packet_schema_version(UI_PACKET_SCHEMA_VERSION)
    with pytest.raises(ValueError):
        assert_supported_ui_packet_schema_version(UI_PACKET_SCHEMA_VERSION + 1)


def test_ui_packet_envelope_common_fields_roundtrip():
    envelope = build_ui_packet_envelope(
        packet_type=UIPacketType.CONGESTION_FRAME,
        run_id="run-123",
        tick=17,
        day_type="weekday",
        time_band="morning",
        payload={"frame_seq": 1},
    )

    packet_dict = envelope.as_dict()
    assert packet_dict == {
        "type": "ui.congestion_frame",
        "schema_version": UI_PACKET_SCHEMA_VERSION,
        "run_id": "run-123",
        "tick": 17,
        "sim_time": {"day_type": "weekday", "time_band": "morning"},
        "payload": {"frame_seq": 1},
    }

    restored = UIPacketEnvelope.from_mapping(packet_dict)
    assert restored.type is UIPacketType.CONGESTION_FRAME
    assert restored.sim_time == UISimTimeRef(day_type="weekday", time_band="morning")
    assert validate_ui_packet_envelope(restored) == ()


def test_ui_packet_envelope_rejects_unsupported_schema_version():
    with pytest.raises(ValueError):
        UIPacketEnvelope(
            type=UIPacketType.METRICS_SUMMARY,
            schema_version=UI_PACKET_SCHEMA_VERSION + 1,
            run_id="run-1",
            tick=0,
            sim_time={"day_type": "weekday", "time_band": "lunch"},
            payload={},
        )

    issues = validate_ui_packet_envelope(
        {
            "type": "ui.metrics_summary",
            "schema_version": UI_PACKET_SCHEMA_VERSION + 1,
            "run_id": "run-1",
            "tick": 0,
            "sim_time": {"day_type": "weekday", "time_band": "lunch"},
            "payload": {},
        }
    )
    assert issues
    assert issues[0].startswith("invalid_envelope:")


def test_ui_packet_envelope_requires_common_envelope_fields():
    issues = validate_ui_packet_envelope(
        {
            "type": "ui.control_ack",
            "schema_version": UI_PACKET_SCHEMA_VERSION,
            "run_id": "",
            "tick": -1,
            "sim_time": {"day_type": "weekday", "time_band": "night"},
            "payload": {},
        }
    )
    # Construction fails fast on invalid common fields; validator reports parse failure.
    assert issues
    assert issues[0].startswith("invalid_envelope:")
