from __future__ import annotations

import pytest

from metroflow.ui.packets import (
    UIPacketEnvelope,
    UIPacketType,
    build_ui_packet_envelope,
    build_ui_event_overlay_packet,
    validate_ui_packet_envelope,
)


def test_ui_event_overlay_packet_contract_shape_and_clear_case():
    event_packet = build_ui_packet_envelope(
        packet_type=UIPacketType.EVENT_OVERLAY,
        run_id="us2-run",
        tick=12,
        day_type="weekday",
        time_band="evening",
        payload={
            "events": (
                {
                    "event_id": 101,
                    "event_type": "construction",
                    "status": "active",
                    "severity": "high",
                    "target_scope": {"bridge_group_id": 1},
                },
            )
        },
    )
    clear_packet = build_ui_packet_envelope(
        packet_type=UIPacketType.EVENT_OVERLAY,
        run_id="us2-run",
        tick=13,
        day_type="weekday",
        time_band="evening",
        payload={"events": ()},
    )

    assert validate_ui_packet_envelope(event_packet) == ()
    assert validate_ui_packet_envelope(clear_packet.as_dict()) == ()

    payload = event_packet.payload
    assert set(payload) == {"events"}
    assert isinstance(payload["events"], tuple)
    assert set(payload["events"][0]) == {
        "event_id",
        "event_type",
        "status",
        "severity",
        "target_scope",
    }
    assert clear_packet.payload["events"] == ()


def test_ui_control_command_packet_contract_examples():
    set_day = build_ui_packet_envelope(
        packet_type=UIPacketType.CONTROL_COMMAND,
        run_id="ui-run",
        tick=20,
        day_type="weekday",
        time_band="morning",
        payload={
            "command_id": "cmd-1",
            "action": "set_day_type",
            "arguments": {"day_type": "weekend"},
        },
    )
    request_snapshot = build_ui_packet_envelope(
        packet_type=UIPacketType.CONTROL_COMMAND,
        run_id="ui-run",
        tick=20,
        day_type="weekday",
        time_band="morning",
        payload={
            "command_id": "cmd-2",
            "action": "request_snapshot",
            "arguments": {"force": True},
        },
    )
    inject_event = build_ui_packet_envelope(
        packet_type=UIPacketType.CONTROL_COMMAND,
        run_id="ui-run",
        tick=20,
        day_type="weekday",
        time_band="morning",
        payload={
            "command_id": "cmd-3",
            "action": "inject_event",
            "arguments": {
                "event_type": "construction",
                "target_scope": {"bridge_group_id": 1},
                "effect_model": "closure",
            },
        },
    )
    clear_event = build_ui_packet_envelope(
        packet_type=UIPacketType.CONTROL_COMMAND,
        run_id="ui-run",
        tick=20,
        day_type="weekday",
        time_band="morning",
        payload={
            "command_id": "cmd-4",
            "action": "clear_event",
            "arguments": {"event_id": 101},
        },
    )

    restored = UIPacketEnvelope.from_mapping(set_day.as_dict())
    assert restored.type is UIPacketType.CONTROL_COMMAND
    assert validate_ui_packet_envelope(restored) == ()
    assert validate_ui_packet_envelope(request_snapshot.as_dict()) == ()
    assert validate_ui_packet_envelope(inject_event.as_dict()) == ()
    assert validate_ui_packet_envelope(clear_event.as_dict()) == ()

    for payload in (
        set_day.payload,
        request_snapshot.payload,
        inject_event.payload,
        clear_event.payload,
    ):
        assert set(payload) == {"command_id", "action", "arguments"}
        assert isinstance(payload["command_id"], str)
        assert isinstance(payload["action"], str)
        assert isinstance(payload["arguments"], dict)


def test_ui_control_ack_packet_contract_accept_reject_shapes():
    accepted = build_ui_packet_envelope(
        packet_type=UIPacketType.CONTROL_ACK,
        run_id="ui-run",
        tick=21,
        day_type="weekend",
        time_band="night",
        payload={
            "command_id": "cmd-1",
            "accepted": True,
            "applied_tick": 21,
        },
    )
    rejected = build_ui_packet_envelope(
        packet_type=UIPacketType.CONTROL_ACK,
        run_id="ui-run",
        tick=21,
        day_type="weekend",
        time_band="night",
        payload={
            "command_id": "cmd-2",
            "accepted": False,
            "reason": "unsupported action",
        },
    )

    assert validate_ui_packet_envelope(accepted) == ()
    assert validate_ui_packet_envelope(rejected.as_dict()) == ()

    accepted_payload = accepted.payload
    rejected_payload = rejected.payload
    assert set(accepted_payload) == {"command_id", "accepted", "applied_tick"}
    assert set(rejected_payload) == {"command_id", "accepted", "reason"}
    assert isinstance(accepted_payload["accepted"], bool)
    assert isinstance(rejected_payload["accepted"], bool)
    assert isinstance(rejected_payload["reason"], str)


def test_ui_control_ack_invalid_envelope_common_fields_are_rejected():
    issues = validate_ui_packet_envelope(
        {
            "type": "ui.control_ack",
            "schema_version": 1,
            "run_id": "",
            "tick": -1,
            "sim_time": {"day_type": "weekday", "time_band": "morning"},
            "payload": {"command_id": "cmd-x", "accepted": False},
        }
    )
    assert issues
    assert issues[0].startswith("invalid_envelope:")


def test_ui_event_overlay_packet_type_roundtrip_string_value():
    envelope = build_ui_packet_envelope(
        packet_type="ui.event_overlay",
        run_id="ui-run",
        tick=5,
        day_type="weekday",
        time_band="lunch",
        payload={"events": ()},
    )
    restored = UIPacketEnvelope.from_mapping(envelope.as_dict())
    assert restored.type is UIPacketType.EVENT_OVERLAY
    assert validate_ui_packet_envelope(restored) == ()


def test_ui_event_overlay_builder_fail_soft_normalizes_malformed_event_items():
    packet = build_ui_event_overlay_packet(
        run_id="ui-run",
        tick=9,
        day_type="weekday",
        time_band="evening",
        events=(
            {
                "event_id": "not-an-int",
                "event_type": "accident",
                "status": "active",
                "severity": {"bad": "shape"},
                "target_scope": "not-an-object",
            },
        ),
    )
    assert validate_ui_packet_envelope(packet) == ()
    item = packet.payload["events"][0]
    assert item["event_id"] == -1
    assert isinstance(item["severity"], str)
    assert item["target_scope"] == {}


def test_ui_event_overlay_builder_emits_stable_string_severity_for_numeric_values():
    packet = build_ui_event_overlay_packet(
        run_id="ui-run",
        tick=10,
        day_type="weekday",
        time_band="night",
        events=(
            {
                "event_id": 11,
                "event_type": "construction",
                "status": "active",
                "severity": 0.75,
                "target_scope": {"link_ids": [1]},
            },
        ),
    )
    assert validate_ui_packet_envelope(packet) == ()
    assert packet.payload["events"][0]["severity"] == "0.75"
