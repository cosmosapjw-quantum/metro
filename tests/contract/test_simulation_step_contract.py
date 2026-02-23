from __future__ import annotations

import inspect

from metroflow.sim.config import SimulationConfig
from metroflow.sim.control import SimulationControl, SimulationTelemetry
from metroflow.sim.step import init_simulation, run_rollout, simulation_step, validate_invariants


def test_step_contract_function_signatures():
    init_sig = inspect.signature(init_simulation)
    assert tuple(init_sig.parameters) == ("config", "scenario_seed")

    step_sig = inspect.signature(simulation_step)
    assert tuple(step_sig.parameters) == ("state", "control", "rng_key")

    rollout_sig = inspect.signature(run_rollout)
    assert tuple(rollout_sig.parameters) == ("initial_state", "controls", "rng_key")

    invariant_sig = inspect.signature(validate_invariants)
    assert tuple(invariant_sig.parameters) == ("state",)


def test_simulation_step_returns_contract_telemetry_keys_and_next_key():
    config = SimulationConfig(
        active_agent_capacity=4,
        ui_stream_enabled=False,
        learning_enabled=False,
    )
    state, rng_key = init_simulation(config=config, scenario_seed=42)

    next_state, telemetry, ui_snapshot_source, next_rng_key = simulation_step(
        state=state,
        control=SimulationControl.noop(),
        rng_key=rng_key,
    )

    assert telemetry.__class__ is SimulationTelemetry
    assert tuple(telemetry.as_dict()) == SimulationTelemetry.required_keys()
    assert ui_snapshot_source is None
    assert next_state.tick_index == 1
    assert next_rng_key.shape == rng_key.shape


def test_simulation_step_force_snapshot_returns_ui_snapshot_source_shape():
    config = SimulationConfig(
        active_agent_capacity=2,
        ui_stream_enabled=False,
    )
    state, rng_key = init_simulation(config=config, scenario_seed=7)

    _, telemetry, ui_snapshot_source, _ = simulation_step(
        state=state,
        control=SimulationControl(ui_force_snapshot=True),
        rng_key=rng_key,
    )

    assert telemetry.ui_snapshot_emitted is True
    assert isinstance(ui_snapshot_source, dict)
    assert set(ui_snapshot_source) == {
        "network_geometry_version",
        "sampled_link_congestion",
        "active_events",
        "clock_state",
        "summary_metrics",
    }
    assert set(ui_snapshot_source["clock_state"]) == {"day_type", "time_band", "sim_tick"}
