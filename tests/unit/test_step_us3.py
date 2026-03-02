from __future__ import annotations

import runpy
from pathlib import Path

import jax.numpy as jnp

from metroflow.sim.config import SimulationConfig
from metroflow.sim.control import SimulationControl
from metroflow.sim.step import (
    _US3_POLICY_BLEND_FALLBACK_INTEGRATED,
    init_simulation,
    run_rollout,
)

_SCENARIOS = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "fixtures" / "simulation_scenarios.py")
)
SEED_REGISTRY = _SCENARIOS["SEED_REGISTRY"]


def test_us3_step_rollout_populates_candidate_and_bandit_state():
    state, rng_key = init_simulation(
        config=SimulationConfig(
            active_agent_capacity=24,
            ui_stream_enabled=False,
            learning_enabled=True,
        ),
        scenario_seed=SEED_REGISTRY["reproducibility_adaptive"],
    )

    final_state, telemetry_log, _ = run_rollout(
        initial_state=state,
        controls=[SimulationControl.noop() for _ in range(8)],
        rng_key=rng_key,
    )

    assert _US3_POLICY_BLEND_FALLBACK_INTEGRATED is True
    assert final_state.dynamic.route_candidate_state["candidate_sets"]
    adaptive_state = final_state.dynamic.adaptive_learning_state
    assert isinstance(adaptive_state, dict)
    assert adaptive_state["od_bandit_states"]
    assert any(
        float(t.policy_mix_lambda) > 0.0 or bool(t.adaptive_fallback_triggered)
        for t in telemetry_log
    )


def test_us3_step_online_updates_bandit_after_trip_outcomes():
    state, rng_key = init_simulation(
        config=SimulationConfig(
            active_agent_capacity=24,
            ui_stream_enabled=False,
            learning_enabled=True,
        ),
        scenario_seed=SEED_REGISTRY["reproducibility_adaptive"],
    )

    final_state, _telemetry_log, _ = run_rollout(
        initial_state=state,
        controls=[SimulationControl.noop() for _ in range(12)],
        rng_key=rng_key,
    )

    adaptive_state = final_state.dynamic.adaptive_learning_state
    assert isinstance(adaptive_state, dict)
    assert adaptive_state["last_experience_batch_size"] > 0
    assert adaptive_state["last_online_update_count_delta"] > 0
    total_pulls = sum(
        int(jnp.sum(bandit_state.pull_count))
        for bandit_state in adaptive_state["od_bandit_states"].values()
    )
    assert total_pulls > 0
