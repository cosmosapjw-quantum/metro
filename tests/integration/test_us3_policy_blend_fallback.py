from __future__ import annotations

import runpy
from pathlib import Path

import pytest

from metroflow.learning.policy_blend import PolicyBlendFallbackReason
from metroflow.sim.config import SimulationConfig
from metroflow.sim.control import SimulationControl
from metroflow.sim.step import init_simulation, run_rollout, validate_invariants

"""Contract-first integration tests for US3 policy blending + safe fallback.

These tests are allowed to skip until adaptive plugin/OD-UCB/policy-mixer
modules and the T066 `sim.step` integration are implemented. Once enabled,
they should fail on real baseline/adaptive mixing or fallback safety regressions.
"""

_SCENARIOS = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "fixtures" / "simulation_scenarios.py")
)
SEED_REGISTRY = _SCENARIOS["SEED_REGISTRY"]


def test_us3_adaptive_rollout_exposes_policy_blend_telemetry_and_keeps_invariants_green_pending_t061_t066():
    _require_us3_adaptive_modules()

    config = SimulationConfig(
        active_agent_capacity=24,
        ui_stream_enabled=False,
        learning_enabled=True,
    )
    state, rng_key = init_simulation(
        config=config,
        scenario_seed=SEED_REGISTRY["reproducibility_adaptive"],
    )

    controls = [SimulationControl.noop() for _ in range(8)]
    final_state, telemetry_log, _ = run_rollout(
        initial_state=state,
        controls=controls,
        rng_key=rng_key,
    )
    report = validate_invariants(final_state)

    assert report.ok is True
    assert report.counters.total_violations == 0
    assert len(telemetry_log) == len(controls)
    assert all(0.0 <= float(t.policy_mix_lambda) <= 1.0 for t in telemetry_log)
    assert all(isinstance(t.adaptive_fallback_triggered, bool) for t in telemetry_log)
    observed_mix = any(float(t.policy_mix_lambda) > 0.0 for t in telemetry_log)
    observed_fallback = any(bool(t.adaptive_fallback_triggered) for t in telemetry_log)

    blend_state = getattr(getattr(final_state, "dynamic", None), "policy_blend_state", None)
    assert blend_state is not None
    lambda_mix = float(_field(blend_state, "lambda_mix", 0.0) or 0.0)
    assert 0.0 <= lambda_mix <= 1.0
    fallback_triggered = bool(_field(blend_state, "fallback_triggered", False))
    fallback_reason = _field(blend_state, "fallback_reason", None)
    if fallback_triggered:
        assert fallback_reason is not None
        assert str(getattr(fallback_reason, "value", fallback_reason)) in {
            reason.value for reason in PolicyBlendFallbackReason
        }
    # Once T066 is integrated, adaptive mode should surface either a non-zero
    # mix signal or an explicit fallback signal (and reason) in the run.
    assert observed_mix or observed_fallback or fallback_triggered


def test_us3_baseline_vs_adaptive_fixed_seed_rollouts_remain_safe_under_fallback_contract_pending_t061_t066():
    _require_us3_adaptive_modules()

    seed = SEED_REGISTRY["reproducibility_baseline"]
    baseline_state, baseline_key = init_simulation(
        config=SimulationConfig(
            active_agent_capacity=24,
            ui_stream_enabled=False,
            learning_enabled=False,
        ),
        scenario_seed=seed,
    )
    adaptive_state, adaptive_key = init_simulation(
        config=SimulationConfig(
            active_agent_capacity=24,
            ui_stream_enabled=False,
            learning_enabled=True,
        ),
        scenario_seed=seed,
    )

    controls = [SimulationControl.noop() for _ in range(6)]
    baseline_final, baseline_telemetry, _ = run_rollout(
        initial_state=baseline_state,
        controls=controls,
        rng_key=baseline_key,
    )
    adaptive_final, adaptive_telemetry, _ = run_rollout(
        initial_state=adaptive_state,
        controls=controls,
        rng_key=adaptive_key,
    )

    baseline_report = validate_invariants(baseline_final)
    adaptive_report = validate_invariants(adaptive_final)
    assert baseline_report.ok is True
    assert adaptive_report.ok is True

    assert baseline_final.tick_index == adaptive_final.tick_index == len(controls)
    assert len(baseline_telemetry) == len(adaptive_telemetry) == len(controls)

    adaptive_completed_total = sum(int(t.trip_completed_this_tick) for t in adaptive_telemetry)
    adaptive_failed_total = sum(int(t.trip_failed_this_tick) for t in adaptive_telemetry)
    assert adaptive_completed_total >= 0
    assert adaptive_failed_total >= 0
    assert all(0.0 <= float(t.policy_mix_lambda) <= 1.0 for t in adaptive_telemetry)
    assert all(isinstance(t.adaptive_fallback_triggered, bool) for t in adaptive_telemetry)
    baseline_signals = tuple(
        (float(t.policy_mix_lambda), bool(t.adaptive_fallback_triggered)) for t in baseline_telemetry
    )
    adaptive_signals = tuple(
        (float(t.policy_mix_lambda), bool(t.adaptive_fallback_triggered)) for t in adaptive_telemetry
    )
    # Adaptive rollout may validly reduce to baseline via fallback, but it must
    # expose that fact through blend/fallback signals once T066 is wired.
    assert adaptive_signals != baseline_signals or any(flag for _, flag in adaptive_signals)


def _require_us3_adaptive_modules() -> None:
    pytest.importorskip(
        "metroflow.learning.plugins",
        reason="T061 pending: learning.plugins not implemented yet",
    )
    pytest.importorskip(
        "metroflow.routing.candidates",
        reason="T062 pending: routing.candidates not implemented yet",
    )
    pytest.importorskip(
        "metroflow.learning.od_ucb",
        reason="T063 pending: learning.od_ucb not implemented yet",
    )
    pytest.importorskip(
        "metroflow.routing.policy_mixer",
        reason="T064 pending: routing.policy_mixer not implemented yet",
    )
    pytest.importorskip(
        "metroflow.learning.experience",
        reason="T065 pending: learning.experience not implemented yet",
    )
    step_mod = pytest.importorskip("metroflow.sim.step")
    if not hasattr(step_mod, "_US3_POLICY_BLEND_FALLBACK_INTEGRATED"):
        pytest.fail(
            "sim.step missing _US3_POLICY_BLEND_FALLBACK_INTEGRATED marker; "
            "T066 must expose this gate for US3 integration tests"
        )
    if not bool(getattr(step_mod, "_US3_POLICY_BLEND_FALLBACK_INTEGRATED", False)):
        pytest.skip(
            "T066 pending: sim.step US3 policy blend/fallback integration not implemented yet "
            "(set _US3_POLICY_BLEND_FALLBACK_INTEGRATED=True in T066)"
        )


def _field(obj: object, name: str, default: object) -> object:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)
