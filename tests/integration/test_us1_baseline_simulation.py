from __future__ import annotations

import runpy
from pathlib import Path

from metroflow.sim.config import SimulationConfig
from metroflow.sim.control import SimulationControl
from metroflow.sim.step import init_simulation, run_rollout, simulation_step, validate_invariants

_SCENARIOS = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "fixtures" / "simulation_scenarios.py")
)
SEED_REGISTRY = _SCENARIOS["SEED_REGISTRY"]


def test_us1_baseline_simulation_smoke_forced_snapshot_exposes_topology_and_congestion_outputs():
    config = SimulationConfig(
        active_agent_capacity=8,
        ui_stream_enabled=True,
        ui_stream_hz_limit=5.0,
        learning_enabled=False,
    )
    state, rng_key = init_simulation(
        config=config,
        scenario_seed=SEED_REGISTRY["baseline_smoke"],
    )

    next_state, telemetry, ui_snapshot_source, _ = simulation_step(
        state=state,
        control=SimulationControl(ui_force_snapshot=True),
        rng_key=rng_key,
    )

    assert next_state.tick_index == 1
    assert telemetry.ui_snapshot_emitted is True
    assert isinstance(ui_snapshot_source, dict)

    # Topology/congestion outputs are placeholders until T037, but keys/shape are fixed.
    assert "network_geometry_version" in ui_snapshot_source
    assert "sampled_link_congestion" in ui_snapshot_source
    assert "summary_metrics" in ui_snapshot_source
    assert isinstance(ui_snapshot_source["sampled_link_congestion"], tuple)
    assert set(ui_snapshot_source["clock_state"]) == {"day_type", "time_band", "sim_tick"}
    assert set(ui_snapshot_source["summary_metrics"]) == {
        "active_agents",
        "capacity_violation_count",
        "negative_queue_detected",
    }


def test_us1_baseline_rollout_smoke_keeps_core_invariants_green():
    config = SimulationConfig(
        active_agent_capacity=16,
        ui_stream_enabled=False,
        learning_enabled=False,
    )
    initial_state, rng_key = init_simulation(
        config=config,
        scenario_seed=SEED_REGISTRY["baseline_smoke"],
    )

    controls = [
        SimulationControl.noop(),
        SimulationControl.noop(),
        SimulationControl(ui_force_snapshot=True),
        SimulationControl.noop(),
    ]
    final_state, telemetry_log, _ = run_rollout(
        initial_state=initial_state,
        controls=controls,
        rng_key=rng_key,
    )
    invariant_report = validate_invariants(final_state)

    assert len(telemetry_log) == len(controls)
    assert final_state.tick_index == len(controls)
    assert telemetry_log[0].tick_index == 1
    assert telemetry_log[-1].tick_index == len(controls)
    assert any(item.ui_snapshot_emitted for item in telemetry_log)
    assert invariant_report.ok is True
    assert invariant_report.counters.total_violations == 0

