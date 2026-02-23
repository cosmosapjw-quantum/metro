"""Simulation init/step function skeletons matching the phase-1 step contract."""

from __future__ import annotations

from typing import Any, Mapping

from metroflow.flow.state import create_link_state, create_node_state
from metroflow.learning.policy_blend import PolicyBlendState
from metroflow.sim.active_agents import create_active_agent_pool
from metroflow.sim.config import SimulationConfig
from metroflow.sim.control import SimulationControl, SimulationTelemetry
from metroflow.sim.invariants import InvariantReport
from metroflow.sim.invariants import validate_invariants as _validate_invariants_core
from metroflow.sim.rng import PRNGKeyArray, key_from_seed, next_key
from metroflow.sim.state import (
    SimulationClockState,
    SimulationDynamicRefs,
    SimulationStaticRefs,
    SimulationState,
)
from metroflow.ui.stream_buffer import UISnapshotStreamBuffer

__all__ = [
    "UISnapshotSource",
    "init_simulation",
    "simulation_step",
    "run_rollout",
    "validate_invariants",
]

UISnapshotSource = dict[str, Any]


def init_simulation(
    config: SimulationConfig,
    scenario_seed: int,
) -> tuple[SimulationState, PRNGKeyArray]:
    """Initialize a foundational simulation state skeleton and root PRNG key."""

    sim_config = _coerce_config(config)
    root_key = key_from_seed(scenario_seed)

    dynamic = SimulationDynamicRefs(
        clock_state=SimulationClockState(
            tick_index=0,
            day_type=sim_config.day_type_set[0],
            time_band=sim_config.time_bands[0],
        ),
        active_agent_pool=create_active_agent_pool(sim_config.active_agent_capacity),
        flow_link_state=create_link_state(0),
        flow_node_state=create_node_state([], [], node_count=0),
        policy_blend_state=PolicyBlendState(
            lambda_mix=0.0,
            baseline_only_mode=not sim_config.learning_enabled,
        ),
        metrics_state=_initial_metrics_state(),
        invariant_state=InvariantReport(tick_index=0),
        ui_state=(
            UISnapshotStreamBuffer(
                tick_seconds=sim_config.tick_seconds,
                hz_limit=sim_config.ui_stream_hz_limit,
            )
            if sim_config.ui_stream_enabled
            else None
        ),
        metadata={"scenario_seed": int(scenario_seed)},
    )

    state = SimulationState(
        config=sim_config,
        static=SimulationStaticRefs(
            scenario_id="skeleton",
            metadata={"scenario_seed": int(scenario_seed)},
        ),
        dynamic=dynamic,
        metadata={"scenario_seed": int(scenario_seed)},
    )
    return state, root_key


def simulation_step(
    state: SimulationState,
    control: SimulationControl,
    rng_key: PRNGKeyArray,
) -> tuple[SimulationState, SimulationTelemetry, UISnapshotSource | None, PRNGKeyArray]:
    """Advance one tick of the foundational simulation skeleton.

    Current behavior is intentionally minimal (no flow/agent updates yet):
    - apply control clock overrides on the step boundary
    - advance tick if not paused
    - run invariant validator hook on available state pieces
    - emit telemetry with contract keys
    - optionally produce a placeholder `UISnapshotSource` when forced
    """

    cur_state = _coerce_state(state)
    cur_control = _coerce_control(control)

    next_rng_key, _ = next_key(rng_key)

    next_state = _apply_control_to_state(cur_state, cur_control)
    invariant_report = _validate_invariants_core(next_state)

    ui_snapshot_source = _maybe_build_ui_snapshot_source(next_state, cur_control, invariant_report)
    ui_snapshot_emitted = ui_snapshot_source is not None

    metrics_state = _update_metrics_state_stub(
        next_state=next_state,
        prior_metrics_state=next_state.dynamic.metrics_state,
        invariant_report=invariant_report,
        ui_snapshot_emitted=ui_snapshot_emitted,
    )
    next_state = next_state.with_dynamic_updates(
        metrics_state=metrics_state,
        invariant_state=invariant_report,
        last_ui_snapshot_source=ui_snapshot_source,
    )

    telemetry = _build_step_telemetry(
        state=next_state,
        invariant_report=invariant_report,
        ui_snapshot_emitted=ui_snapshot_emitted,
    )
    return next_state, telemetry, ui_snapshot_source, next_rng_key


def run_rollout(
    initial_state: SimulationState,
    controls: list[SimulationControl],
    rng_key: PRNGKeyArray,
) -> tuple[SimulationState, list[SimulationTelemetry], PRNGKeyArray]:
    """Optional helper matching repeated `simulation_step` semantics."""

    state = _coerce_state(initial_state)
    key = rng_key
    telemetry_log: list[SimulationTelemetry] = []
    for control in controls:
        state, telemetry, _ui_snapshot, key = simulation_step(state, control, key)
        telemetry_log.append(telemetry)
    return state, telemetry_log, key


def validate_invariants(state: SimulationState) -> InvariantReport:
    """Contract wrapper around the invariant validation hook."""

    return _validate_invariants_core(_coerce_state(state))


def _coerce_config(config: SimulationConfig | Mapping[str, Any]) -> SimulationConfig:
    if isinstance(config, SimulationConfig):
        return config
    return SimulationConfig(**dict(config))


def _coerce_state(state: SimulationState | Mapping[str, Any]) -> SimulationState:
    if isinstance(state, SimulationState):
        return state
    return SimulationState(**dict(state))


def _coerce_control(control: SimulationControl | Mapping[str, Any]) -> SimulationControl:
    if isinstance(control, SimulationControl):
        return control
    return SimulationControl(**dict(control))


def _apply_control_to_state(state: SimulationState, control: SimulationControl) -> SimulationState:
    next_state = state.with_clock(
        day_type=control.set_day_type if control.set_day_type is not None else None,
        time_band=control.set_time_band if control.set_time_band is not None else None,
    )
    if not control.pause:
        next_state = next_state.with_clock(tick_index=next_state.tick_index + 1)
    return next_state


def _build_step_telemetry(
    *,
    state: SimulationState,
    invariant_report: InvariantReport,
    ui_snapshot_emitted: bool,
) -> SimulationTelemetry:
    active_agent_count = _extract_active_agent_count(state)
    policy_blend_state = state.dynamic.policy_blend_state
    policy_mix_lambda = 0.0
    adaptive_fallback_triggered = False
    if isinstance(policy_blend_state, PolicyBlendState):
        policy_mix_lambda = policy_blend_state.lambda_mix
        adaptive_fallback_triggered = policy_blend_state.fallback_triggered

    negative_queue_detected = invariant_report.counters.negative_queue_violations > 0
    capacity_violation_count_delta = 0
    metrics_state = state.dynamic.metrics_state
    if isinstance(metrics_state, Mapping):
        capacity_violation_count_delta = int(metrics_state.get("capacity_violation_count_delta", 0))

    return SimulationTelemetry(
        tick_index=state.tick_index,
        active_agent_count=active_agent_count,
        trip_generated_this_tick=0,
        trip_completed_this_tick=0,
        trip_failed_this_tick=0,
        capacity_violation_count_delta=capacity_violation_count_delta,
        negative_queue_detected=negative_queue_detected,
        policy_mix_lambda=policy_mix_lambda,
        adaptive_fallback_triggered=adaptive_fallback_triggered,
        ui_snapshot_emitted=ui_snapshot_emitted,
    )


def _maybe_build_ui_snapshot_source(
    state: SimulationState,
    control: SimulationControl,
    invariant_report: InvariantReport,
) -> UISnapshotSource | None:
    if not (state.config.ui_stream_enabled or control.ui_force_snapshot):
        return None
    if not control.ui_force_snapshot:
        # Throttled emission policy is implemented by `ui.stream_buffer` (T017).
        # This foundational skeleton emits only on explicit force requests.
        return None

    metrics_state = (
        state.dynamic.metrics_state
        if isinstance(state.dynamic.metrics_state, Mapping)
        else {}
    )
    return {
        "network_geometry_version": state.static.ui_network_geometry_version,
        "sampled_link_congestion": (),
        "active_events": (),
        "clock_state": {
            "day_type": state.day_type.value,
            "time_band": state.time_band.value,
            "sim_tick": state.tick_index,
        },
        "summary_metrics": {
            "active_agents": _extract_active_agent_count(state),
            "capacity_violation_count": int(metrics_state.get("capacity_violation_count", 0)),
            "negative_queue_detected": invariant_report.counters.negative_queue_violations > 0,
        },
    }


def _initial_metrics_state() -> dict[str, Any]:
    return {
        "tick_index": 0,
        "active_agents": 0,
        "queued_trip_requests": 0,
        "completed_trips_total": 0,
        "failed_trips_total": 0,
        "capacity_violation_count": 0,
        "capacity_violation_count_delta": 0,
        "negative_queue_detected": False,
        "hotspot_links_top_k": (),
        "ui_packets_emitted": 0,
        "generated_trip_total": 0,
    }


def _update_metrics_state_stub(
    *,
    next_state: SimulationState,
    prior_metrics_state: Any,
    invariant_report: InvariantReport,
    ui_snapshot_emitted: bool,
) -> dict[str, Any]:
    metrics = (
        dict(prior_metrics_state)
        if isinstance(prior_metrics_state, Mapping)
        else _initial_metrics_state()
    )
    prev_capacity_count = int(metrics.get("capacity_violation_count", 0))
    active_agents = _extract_active_agent_count(next_state)
    queued_trip_requests = _extract_queued_trip_requests(next_state)
    current_capacity_count = _extract_capacity_violation_count(
        next_state,
        fallback=prev_capacity_count,
    )

    metrics.update(
        {
            "tick_index": next_state.tick_index,
            "active_agents": active_agents,
            "queued_trip_requests": queued_trip_requests,
            "capacity_violation_count": current_capacity_count,
            "capacity_violation_count_delta": max(
                0,
                current_capacity_count - prev_capacity_count,
            ),
            "negative_queue_detected": invariant_report.counters.negative_queue_violations > 0,
            "ui_packets_emitted": int(metrics.get("ui_packets_emitted", 0))
            + int(ui_snapshot_emitted),
        }
    )
    return metrics


def _extract_active_agent_count(state: SimulationState) -> int:
    pool = state.dynamic.active_agent_pool
    alive_count = getattr(pool, "alive_count", None)
    if alive_count is None:
        return 0
    return int(alive_count)


def _extract_queued_trip_requests(state: SimulationState) -> int:
    demand_state = state.dynamic.demand_state
    for key in ("queued_trip_requests", "pending_trip_requests"):
        value = _lookup_attr_or_key(demand_state, key)
        if value is not None:
            return int(value)
    return 0


def _extract_capacity_violation_count(state: SimulationState, *, fallback: int = 0) -> int:
    flow_link_state = state.dynamic.flow_link_state
    if flow_link_state is None:
        return int(fallback)
    count = _lookup_attr_or_key(flow_link_state, "capacity_violation_count")
    if count is not None:
        return int(count)
    flags = _lookup_attr_or_key(flow_link_state, "capacity_violation_flags")
    if flags is None:
        return int(fallback)
    try:
        return int(sum(bool(x) for x in flags))
    except TypeError:
        return int(fallback)


def _lookup_attr_or_key(source: Any, key: str) -> Any | None:
    if source is None:
        return None
    if hasattr(source, key):
        return getattr(source, key)
    if isinstance(source, Mapping):
        return source.get(key)
    return None
