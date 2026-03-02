from __future__ import annotations

from metroflow.flow.events import TrafficEvent, TrafficEventSchedulerState, TrafficEventStatus
from metroflow.learning.experience import (
    build_experience_batch,
    compute_trip_outcome_reward,
)
from metroflow.sim.control import SimulationTelemetry
from metroflow.sim.state import SimulationClockState, SimulationDynamicRefs, SimulationState


def test_compute_trip_outcome_reward_is_bounded_and_outcome_only():
    assert compute_trip_outcome_reward(outcome="completed") == 1.0
    assert compute_trip_outcome_reward(outcome="failed") == -1.0
    assert compute_trip_outcome_reward(
        outcome="completed",
        observed_travel_time=12.0,
        baseline_travel_time=6.0,
    ) == 1.0 / 3.0


def test_build_experience_batch_extracts_completed_failed_rows_only():
    state = SimulationState(
        dynamic=SimulationDynamicRefs(
            clock_state=SimulationClockState(tick_index=9),
            event_state=TrafficEventSchedulerState(
                active_events=(
                    TrafficEvent(
                        event_id=101,
                        event_type="accident",
                        start_tick=1,
                        end_tick=12,
                        target_scope={"link_ids": (7,)},
                        severity=0.8,
                        effect_model="closure",
                        status=TrafficEventStatus.ACTIVE,
                    ),
                )
            ),
            metrics_state={
                "queued_trip_requests": 5,
                "pending_trip_requests": 4,
            },
            metadata={"us2_active_event_affected_link_ids": (7, 8)},
        )
    )
    telemetry = SimulationTelemetry(
        tick_index=9,
        active_agent_count=3,
        trip_completed_this_tick=1,
        trip_failed_this_tick=1,
        policy_mix_lambda=0.25,
        adaptive_fallback_triggered=True,
    )

    batch = build_experience_batch(
        state=state,
        telemetry=telemetry,
        outcome_rows=(
            {
                "trip_id": 11,
                "od_key": ("z1", "z2"),
                "outcome": "completed",
                "chosen_candidate_id": 3,
                "chosen_arm_index": 1,
                "observed_travel_time": 8.0,
                "baseline_travel_time": 4.0,
            },
            {
                "trip_id": 12,
                "od_key": ("z3", "z4"),
                "outcome": "failed",
            },
            {
                "trip_id": 13,
                "od_key": ("z5", "z6"),
                "outcome": "queued",
            },
        ),
    )

    assert len(batch) == 2
    assert batch[0].trip_id == 11
    assert batch[0].chosen_candidate_id == 3
    assert batch[0].chosen_arm_index == 1
    assert round(batch[0].reward, 6) == round(1.0 / 3.0, 6)
    assert batch[0].policy_mix_lambda == 0.25
    assert batch[0].adaptive_fallback_triggered is True
    assert batch[0].context_summary["active_agent_count"] == 3
    assert batch[0].event_context["active_event_ids"] == (101,)
    assert batch[0].event_context["affected_link_ids"] == (7, 8)
    assert batch[1].trip_id == 12
    assert batch[1].reward == -1.0


def test_build_experience_batch_skips_rows_with_insufficient_signal_and_accepts_partial_telemetry():
    state = SimulationState(
        dynamic=SimulationDynamicRefs(
            clock_state=SimulationClockState(tick_index=4),
            metrics_state={},
            metadata={},
        )
    )

    batch = build_experience_batch(
        state=state,
        telemetry={
            "tick_index": 4,
            "policy_mix_lambda": 0.5,
        },
        outcome_rows=(
            {
                "trip_id": 21,
                "od_key": ("z1", "z2"),
                "outcome": "completed",
            },
            {
                "trip_id": 22,
                "outcome": "failed",
            },
            {
                "od_key": ("z3", "z4"),
                "outcome": "completed",
            },
            {
                "trip_id": 23,
                "od_key": ("z5",),
                "outcome": "failed",
            },
        ),
    )

    assert len(batch) == 1
    assert batch[0].trip_id == 21
    assert batch[0].od_key == ("z1", "z2")
    assert batch[0].policy_mix_lambda == 0.5
    assert batch[0].context_summary["active_agent_count"] == 0
