from __future__ import annotations

import inspect

import jax
import jax.numpy as jnp
import pytest

from metroflow.benchmarks.reporting import (
    BenchmarkReport,
    benchmark_report_from_run_summary,
    format_benchmark_report_markdown,
)
from metroflow.benchmarks.run import (
    compute_benchmark_summary_metrics_core,
    run_benchmark_scenario,
)

"""US3 benchmark smoke/report parsing checks (T060).

This file intentionally mixes:
- active checks for benchmark report parsing/formatting (`benchmarks.reporting`)
- pending smoke-contract checks for the future benchmark runner (`T068`)
"""


def test_us3_benchmark_report_parsing_for_100k_run_summary_metrics():
    run_summary = {
        "scenario_id": "synthetic_100k",
        "seed": 42,
        "tick_rate_median": 2.75,
        "tick_rate_p10": 1.4,
        "invariant_violation_counts": {
            "negative_queue": 0,
            "capacity_overflow": 1,
        },
    }

    report = benchmark_report_from_run_summary(
        run_summary,
        population_target=100_000,
        active_agent_median=18_500.0,
        active_agent_p95=23_000.0,
        duration_ticks=600,
        duration_seconds=240.0,
        event_mix="baseline_only",
        ui_mode="off",
        environment="rocm-container/gpu",
    )
    md = format_benchmark_report_markdown(report)

    assert isinstance(report, BenchmarkReport)
    assert report.scenario_id == "synthetic_100k"
    assert report.seed == 42
    assert report.population_target == 100_000
    assert report.tick_rate_median_hz == pytest.approx(2.75)
    assert report.tick_rate_p10_hz == pytest.approx(1.4)
    assert report.invariant_violations == {"capacity_overflow": 1, "negative_queue": 0}
    assert "- Scenario ID: synthetic_100k" in md
    assert "- Population target: 100000" in md
    assert "- Median tick rate (Hz): 2.75" in md
    assert "capacity_overflow=1" in md


def test_us3_benchmark_runner_module_contract_pending_t068():
    mod = pytest.importorskip(
        "metroflow.benchmarks.run",
        reason="T068 pending: metroflow.benchmarks.run not implemented yet",
    )
    runner_fn = _pick_first_existing(
        mod,
        ("run_benchmark_scenario", "run_benchmark", "execute_benchmark"),
    )
    if runner_fn is None:
        pytest.skip("T068 pending: benchmark runner function export not implemented yet")

    assert runner_fn is not None
    fn = getattr(mod, runner_fn)
    sig = inspect.signature(fn)
    params = tuple(sig.parameters)
    # Keep this broad enough for implementation freedom while still pinning a
    # benchmark-scenario oriented entrypoint shape.
    assert any(name in params for name in ("scenario_id", "scenario", "config"))
    assert any(name in params for name in ("seed", "scenario_seed"))


def test_us3_benchmark_runner_smoke_output_shape_pending_t068():
    mod = pytest.importorskip(
        "metroflow.benchmarks.run",
        reason="T068 pending: metroflow.benchmarks.run not implemented yet",
    )
    runner_name = _pick_first_existing(
        mod,
        ("run_benchmark_scenario", "run_benchmark", "execute_benchmark"),
    )
    if runner_name is None:
        pytest.skip("T068 pending: benchmark runner function export not implemented yet")

    runner = getattr(mod, runner_name)
    try:
        result = _invoke_benchmark_runner_smoke(runner)
    except TypeError as exc:
        if _looks_like_signature_mismatch(exc):
            pytest.skip(f"T068 pending: benchmark runner signature not finalized ({exc})")
        raise

    result_map = _coerce_mapping_like(result)
    if result_map is None:
        pytest.skip("T068 pending: benchmark runner return shape not finalized")

    # Minimal contract for smoke benchmark report payload:
    # a RunSummary-like mapping and/or a rendered benchmark report string.
    has_summary_like = any(
        key in result_map
        for key in ("run_summary", "summary", "benchmark_report", "report")
    )
    assert has_summary_like is True
    if "report" in result_map:
        assert isinstance(result_map["report"], (str, dict))
    if "benchmark_report" in result_map:
        assert isinstance(result_map["benchmark_report"], (str, dict))
    if "summary" in result_map:
        assert _coerce_mapping_like(result_map["summary"]) is not None
    if "run_summary" in result_map:
        summary = _coerce_mapping_like(result_map["run_summary"])
        assert summary is not None
        assert float(summary["tick_rate_median"]) >= 0.0
        assert float(summary["tick_rate_p10"]) >= 0.0
        assert "invariant_violation_counts" in summary


def test_us3_benchmark_runner_smoke_captures_metric_fields():
    result = run_benchmark_scenario(
        scenario_id="synthetic_100k",
        seed=42,
        duration_ticks=4,
    )
    summary = result["run_summary"]
    report = result["benchmark_report"]

    assert summary["scenario_id"] == "synthetic_100k"
    assert summary["seed"] == 42
    assert summary["duration_ticks"] == 4
    assert summary["population_target"] == 100_000
    assert float(summary["tick_rate_median"]) >= 0.0
    assert float(summary["tick_rate_p10"]) >= 0.0
    assert float(summary["active_agent_median"]) >= 0.0
    assert float(summary["active_agent_p95"]) >= 0.0
    assert isinstance(summary["invariant_violation_counts"], dict)
    assert report["scenario_id"] == "synthetic_100k"


def test_us3_benchmark_runner_mapping_config_accepts_scenario_id_metadata():
    result = run_benchmark_scenario(
        config={
            "scenario_id": "synthetic_smoke",
            "population_target": 10_000,
            "random_seed": 7,
            "learning_enabled": False,
        },
        duration_ticks=2,
    )

    summary = result["run_summary"]
    assert summary["scenario_id"] == "synthetic_smoke"
    assert summary["seed"] == 7
    assert summary["duration_ticks"] == 2


def test_us3_benchmark_runner_explicit_learning_flag_overrides_config():
    result = run_benchmark_scenario(
        scenario_id="synthetic_smoke",
        seed=11,
        duration_ticks=2,
        learning_enabled=True,
        config={
            "population_target": 10_000,
            "random_seed": 11,
            "learning_enabled": False,
        },
    )

    assert result["benchmark_report"]["event_mix"] == "adaptive_od_ucb"


def test_us3_benchmark_metric_core_supports_jax_jit():
    compiled = jax.jit(compute_benchmark_summary_metrics_core)
    metrics = compiled(
        tick_durations=jnp.asarray([0.5, 1.0, 2.0, 4.0], dtype=jnp.float32),
        active_agent_counts=jnp.asarray([10.0, 20.0, 30.0, 40.0], dtype=jnp.float32),
    )

    assert float(metrics["tick_rate_median"]) >= 0.0
    assert float(metrics["tick_rate_p10"]) >= 0.0
    assert float(metrics["active_agent_median"]) == pytest.approx(25.0)
    assert float(metrics["active_agent_p95"]) >= 0.0


def _pick_first_existing(mod: object, names: tuple[str, ...]) -> str | None:
    for name in names:
        if hasattr(mod, name):
            return name
    return None


def _invoke_benchmark_runner_smoke(runner):
    # Avoid accidentally triggering a heavy full benchmark in a "smoke shape"
    # test. If the runner does not expose a short-run control, keep this pending.
    params = tuple(inspect.signature(runner).parameters)
    if not any(name in params for name in ("ticks", "num_ticks", "duration_ticks", "smoke")):
        raise TypeError("missing smoke-limiting parameter")
    for kwargs in (
        {"scenario_id": "synthetic_100k", "seed": 42, "ticks": 4},
        {"scenario": "synthetic_100k", "seed": 42, "ticks": 4},
        {"scenario_id": "synthetic_100k", "seed": 42, "num_ticks": 4},
        {"scenario": "synthetic_100k", "scenario_seed": 42, "num_ticks": 4},
        {"scenario_id": "synthetic_100k", "seed": 42, "duration_ticks": 4},
        {"scenario": "synthetic_100k", "scenario_seed": 42, "duration_ticks": 4},
        {"scenario_id": "synthetic_100k", "seed": 42, "smoke": True},
        {"scenario": "synthetic_100k", "scenario_seed": 42, "smoke": True},
    ):
        try:
            return runner(**kwargs)
        except TypeError as exc:
            if not _looks_like_signature_mismatch(exc):
                raise
            continue
    raise TypeError("benchmark runner signature not matched")


def _coerce_mapping_like(value: object) -> dict | None:
    if isinstance(value, dict):
        return value
    if hasattr(value, "to_dict") and callable(getattr(value, "to_dict")):
        maybe = value.to_dict()
        return maybe if isinstance(maybe, dict) else None
    return None


def _looks_like_signature_mismatch(exc: TypeError) -> bool:
    msg = str(exc)
    hints = (
        "unexpected keyword",
        "positional argument",
        "required positional argument",
        "missing",
        "takes",
        "got an unexpected",
    )
    return any(token in msg for token in hints)
