from __future__ import annotations

import runpy
from pathlib import Path

from metroflow.sim.active_agents import (
    ActiveAgentSlot,
    allocate_active_agent_slot,
    create_active_agent_pool,
)
from metroflow.sim.config import SimulationConfig
from metroflow.sim.control import SimulationControl
from metroflow.sim.step import init_simulation, simulation_step

_SCENARIOS = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "fixtures" / "simulation_scenarios.py")
)
SEED_REGISTRY = _SCENARIOS["SEED_REGISTRY"]


def test_us1_invariant_regression_detects_conservation_queue_and_capacity_issues():
    config = SimulationConfig(
        active_agent_capacity=4,
        ui_stream_enabled=False,
        learning_enabled=False,
    )
    state, rng_key = init_simulation(
        config=config,
        scenario_seed=SEED_REGISTRY["baseline_smoke"],
    )

    pool = create_active_agent_pool(4)
    pool, _ = allocate_active_agent_slot(
        pool,
        ActiveAgentSlot.spawn(
            citizen_id=11,
            trip_id=1001,
            current_link_id=200,
            dest_node_id=201,
            behavior_profile_id=1,
        ),
    )

    # Intentionally inconsistent placeholder dynamic refs to ensure the invariant
    # hook catches regressions before full baseline engine (T033/T036) exists.
    state = state.with_dynamic_updates(
        active_agent_pool=pool,
        demand_state={"queued_trip_requests": 1},
        flow_link_state={
            "queue_vehicles": [0.0, -1.0, 2.0],
            "outflow_vehicles": [0.5, 3.0, 0.0],
            "effective_capacity_vehicles": [1.0, 2.0, 1.0],
        },
        metrics_state={
            "generated_trip_total": 5,
            "completed_trips_total": 1,
            "failed_trips_total": 0,
            "capacity_violation_count": 0,  # observed exceed count is 1
            "queued_trip_requests": 1,
            "ui_packets_emitted": 0,
        },
    )

    next_state, telemetry, _ui_snapshot_source, _ = simulation_step(
        state=state,
        control=SimulationControl.noop(),
        rng_key=rng_key,
    )

    report = next_state.dynamic.invariant_state
    violation_codes = {violation.code for violation in report.violations}

    assert report.ok is False
    assert report.tick_index == 1
    assert {"conservation", "non_negative_queue", "capacity_flags"} <= set(report.checks_run)
    assert "conservation_mismatch" in violation_codes
    assert "negative_queue_detected" in violation_codes
    assert "capacity_flag_count_mismatch" in violation_codes

    assert report.counters.conservation_violations == 1
    assert report.counters.negative_queue_violations == 1
    assert report.counters.capacity_flag_violations == 1
    assert report.counters.total_violations >= 3

    # Telemetry should surface the queue violation signal on the same step.
    assert telemetry.tick_index == 1
    assert telemetry.negative_queue_detected is True
    assert telemetry.active_agent_count == 1

