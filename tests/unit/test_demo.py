from __future__ import annotations

from types import SimpleNamespace

from metroflow.learning.policy_blend import PolicyBlendState
from metroflow.sim.control import SimulationTelemetry
from metroflow.sim.state import SimulationClockState, SimulationDynamicRefs, SimulationState, SimulationStaticRefs


def test_demo_main_baseline_mode_keeps_learning_disabled(monkeypatch, capsys):
    from metroflow import demo

    captured: dict[str, object] = {}

    def fake_init_simulation(config, scenario_seed):
        captured["config"] = config
        state = SimulationState(
            config=config,
            static=SimulationStaticRefs(scenario_id="synthetic-42"),
            dynamic=SimulationDynamicRefs(
                clock_state=SimulationClockState(tick_index=0),
                policy_blend_state=PolicyBlendState(lambda_mix=0.0, baseline_only_mode=True),
            ),
        ).with_clock(day_type="weekday", time_band="morning")
        return state, "rng"

    def fake_simulation_step(state, control, rng_key):
        next_state = state.with_clock(tick_index=state.tick_index + 1)
        telemetry = SimulationTelemetry(
            tick_index=next_state.tick_index,
            active_agent_count=0,
        )
        return next_state, telemetry, None, rng_key

    monkeypatch.setattr(demo, "init_simulation", fake_init_simulation)
    monkeypatch.setattr(demo, "simulation_step", fake_simulation_step)
    monkeypatch.setattr(
        demo,
        "build_baseline_run_summary",
        lambda *args, **kwargs: SimpleNamespace(
            tick_index=1,
            active_agents=0,
            queued_trip_requests=0,
            pending_trip_requests=0,
            trip_completed_total=0,
            trip_failed_total=0,
            hotspot_links_top_k=(),
            ui_packet_counts={},
        ),
    )

    assert demo.main(["--ticks", "1", "--learning-mode", "baseline"]) == 0
    assert bool(captured["config"].learning_enabled) is False
    stdout = capsys.readouterr().out
    assert "learning_mode=baseline" in stdout
    assert "Adaptive: disabled" in stdout


def test_demo_main_adaptive_mode_enables_learning_and_reports_mix(monkeypatch, capsys):
    from metroflow import demo

    captured: dict[str, object] = {}

    def fake_init_simulation(config, scenario_seed):
        captured["config"] = config
        state = SimulationState(
            config=config,
            static=SimulationStaticRefs(scenario_id="synthetic-42"),
            dynamic=SimulationDynamicRefs(
                clock_state=SimulationClockState(tick_index=0),
                policy_blend_state=PolicyBlendState(
                    lambda_mix=0.25,
                    baseline_only_mode=False,
                    fallback_triggered=False,
                ),
            ),
        ).with_clock(day_type="weekday", time_band="morning")
        return state, "rng"

    def fake_simulation_step(state, control, rng_key):
        next_state = state.with_clock(tick_index=state.tick_index + 1).with_dynamic_updates(
            policy_blend_state=PolicyBlendState(
                lambda_mix=0.25,
                baseline_only_mode=False,
                fallback_triggered=False,
            )
        )
        telemetry = SimulationTelemetry(
            tick_index=next_state.tick_index,
            active_agent_count=1,
            policy_mix_lambda=0.25,
            adaptive_fallback_triggered=False,
        )
        return next_state, telemetry, None, rng_key

    monkeypatch.setattr(demo, "init_simulation", fake_init_simulation)
    monkeypatch.setattr(demo, "simulation_step", fake_simulation_step)
    monkeypatch.setattr(
        demo,
        "build_baseline_run_summary",
        lambda *args, **kwargs: SimpleNamespace(
            tick_index=1,
            active_agents=1,
            queued_trip_requests=0,
            pending_trip_requests=0,
            trip_completed_total=0,
            trip_failed_total=0,
            hotspot_links_top_k=(),
            ui_packet_counts={},
        ),
    )

    assert demo.main(["--ticks", "1", "--learning-mode", "adaptive"]) == 0
    assert bool(captured["config"].learning_enabled) is True
    stdout = capsys.readouterr().out
    assert "learning_mode=adaptive" in stdout
    assert "Adaptive:" in stdout
    assert "mix_ticks=1" in stdout
    assert "fallback_ticks=0" in stdout
    assert "max_lambda=0.250" in stdout


def test_demo_main_adaptive_mode_does_not_count_fallback_ticks_as_mix(monkeypatch, capsys):
    from metroflow import demo

    def fake_init_simulation(config, scenario_seed):
        state = SimulationState(
            config=config,
            static=SimulationStaticRefs(scenario_id="synthetic-42"),
            dynamic=SimulationDynamicRefs(
                clock_state=SimulationClockState(tick_index=0),
                policy_blend_state=PolicyBlendState(
                    lambda_mix=0.25,
                    baseline_only_mode=True,
                    fallback_triggered=True,
                ),
            ),
        ).with_clock(day_type="weekday", time_band="morning")
        return state, "rng"

    def fake_simulation_step(state, control, rng_key):
        next_state = state.with_clock(tick_index=state.tick_index + 1).with_dynamic_updates(
            policy_blend_state=PolicyBlendState(
                lambda_mix=0.25,
                baseline_only_mode=True,
                fallback_triggered=True,
            )
        )
        telemetry = SimulationTelemetry(
            tick_index=next_state.tick_index,
            active_agent_count=1,
            policy_mix_lambda=0.25,
            adaptive_fallback_triggered=True,
        )
        return next_state, telemetry, None, rng_key

    monkeypatch.setattr(demo, "init_simulation", fake_init_simulation)
    monkeypatch.setattr(demo, "simulation_step", fake_simulation_step)
    monkeypatch.setattr(
        demo,
        "build_baseline_run_summary",
        lambda *args, **kwargs: SimpleNamespace(
            tick_index=1,
            active_agents=1,
            queued_trip_requests=0,
            pending_trip_requests=0,
            trip_completed_total=0,
            trip_failed_total=0,
            hotspot_links_top_k=(),
            ui_packet_counts={},
        ),
    )

    assert demo.main(["--ticks", "1", "--learning-mode", "adaptive"]) == 0
    stdout = capsys.readouterr().out
    assert "mix_ticks=0" in stdout
    assert "fallback_ticks=1" in stdout
    assert "max_lambda=0.000" in stdout
