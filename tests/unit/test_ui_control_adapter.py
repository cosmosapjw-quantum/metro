from __future__ import annotations

import pytest

from metroflow.sim.config import DayType, TimeBand
from metroflow.ui.control_adapter import build_ui_control_ack_packet, parse_ui_control_command
from metroflow.ui.packets import UIPacketType, build_ui_packet_envelope


def test_parse_ui_control_command_supports_day_time_and_snapshot_actions():
    day_cmd = build_ui_packet_envelope(
        packet_type=UIPacketType.CONTROL_COMMAND,
        run_id="run-1",
        tick=3,
        day_type="weekday",
        time_band="morning",
        payload={
            "command_id": "cmd-day",
            "action": "set_day_type",
            "arguments": {"day_type": "weekend"},
        },
    )
    day_res = parse_ui_control_command(day_cmd)
    assert day_res.accepted is True
    assert day_res.control.set_day_type == DayType.WEEKEND
    assert day_res.control.set_time_band is None

    band_res = parse_ui_control_command(
        build_ui_packet_envelope(
            packet_type=UIPacketType.CONTROL_COMMAND,
            run_id="run-1",
            tick=4,
            day_type="weekday",
            time_band="morning",
            payload={
                "command_id": "cmd-band",
                "action": "set_time_band",
                "arguments": {"time_band": "evening"},
            },
        )
    )
    assert band_res.accepted is True
    assert band_res.control.set_time_band == TimeBand.EVENING

    snapshot_res = parse_ui_control_command(
        build_ui_packet_envelope(
            packet_type=UIPacketType.CONTROL_COMMAND,
            run_id="run-1",
            tick=5,
            day_type="weekday",
            time_band="morning",
            payload={
                "command_id": "cmd-snap",
                "action": "request_snapshot",
                "arguments": {"force": True},
            },
        )
    )
    assert snapshot_res.accepted is True
    assert snapshot_res.control.ui_force_snapshot is True


def test_parse_ui_control_command_rejects_invalid_or_unsupported_actions_safely():
    unsupported = parse_ui_control_command(
        build_ui_packet_envelope(
            packet_type=UIPacketType.CONTROL_COMMAND,
            run_id="run-1",
            tick=1,
            day_type="weekday",
            time_band="morning",
            payload={"command_id": "cmd-x", "action": "inject_event", "arguments": {}},
        )
    )
    assert unsupported.accepted is False
    assert unsupported.control.is_noop() is True
    assert "unsupported action" in (unsupported.reason or "")

    wrong_type = parse_ui_control_command(
        build_ui_packet_envelope(
            packet_type=UIPacketType.METRICS_SUMMARY,
            run_id="run-1",
            tick=1,
            day_type="weekday",
            time_band="morning",
            payload={"command_id": "cmd-y", "action": "request_snapshot", "arguments": {}},
        )
    )
    assert wrong_type.accepted is False
    assert wrong_type.control.is_noop() is True

    missing_id = parse_ui_control_command(
        build_ui_packet_envelope(
            packet_type=UIPacketType.CONTROL_COMMAND,
            run_id="run-1",
            tick=2,
            day_type="weekday",
            time_band="morning",
            payload={"command_id": None, "action": "request_snapshot", "arguments": {}},
        )
    )
    assert missing_id.accepted is False
    assert missing_id.reason == "missing command_id"

    bad_args = parse_ui_control_command(
        build_ui_packet_envelope(
            packet_type=UIPacketType.CONTROL_COMMAND,
            run_id="run-1",
            tick=2,
            day_type="weekday",
            time_band="morning",
            payload={
                "command_id": "cmd-bad-args",
                "action": "request_snapshot",
                "arguments": "force=true",
            },
        )
    )
    assert bad_args.accepted is False
    assert bad_args.control.is_noop() is True
    assert bad_args.reason == "arguments must be an object"


def test_build_ui_control_ack_packet_matches_contract_payload_shape():
    ack = build_ui_control_ack_packet(
        run_id="run-1",
        tick=7,
        day_type="weekday",
        time_band="night",
        command_id="cmd-1",
        accepted=True,
        applied_tick=7,
    )
    packet = ack.as_dict()
    assert packet["type"] == "ui.control_ack"
    assert set(packet["payload"]) == {"command_id", "accepted", "applied_tick"}
    assert packet["payload"]["accepted"] is True

    with pytest.raises(ValueError):
        build_ui_control_ack_packet(
            run_id="run-1",
            tick=7,
            day_type="weekday",
            time_band="night",
            command_id="cmd-2",
            accepted=False,
            applied_tick=7,
        )
