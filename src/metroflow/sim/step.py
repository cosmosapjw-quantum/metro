"""Simulation init/step function skeletons matching the phase-1 step contract."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping

import jax.numpy as jnp

from metroflow.demand.trips import TripRequest, TripRequestStatus, activate_trip_requests, generate_trip_requests
from metroflow.flow.event_effects import apply_active_event_effects_to_link_state
from metroflow.flow.events import (
    TrafficEvent,
    TrafficEventSchedulerState,
    TrafficEventStatus,
    advance_traffic_event_scheduler,
)
from metroflow.flow.engine import update_link_node_flow
from metroflow.flow.state import LinkState, NodeState
from metroflow.learning.experience import build_experience_batch
from metroflow.learning.od_ucb import (
    ODBanditState,
    compute_ucb_scores_core,
    create_od_ucb_state,
    update_od_ucb_state,
)
from metroflow.learning.policy_blend import PolicyBlendState
from metroflow.routing.behavior_profiles import generate_route_choice_profiles
from metroflow.routing.candidates import RouteCandidateSet, refresh_od_route_candidate_set
from metroflow.routing.dynamic_potential import build_greedy_route_candidate, compute_dynamic_potential_state
from metroflow.routing.policy_mixer import mix_route_candidate_scores
from metroflow.routing.reroute_policy import decide_reroute_vs_persist
from metroflow.sim.active_agents import (
    ActiveAgentSlot,
    ActiveAgentPool,
    allocate_active_agent_slot,
    create_active_agent_pool,
    release_active_agent_slot,
)
from metroflow.sim.config import SimulationConfig
from metroflow.sim.control import SimulationControl, SimulationTelemetry
from metroflow.sim.init import build_initial_simulation_state
from metroflow.sim.invariants import InvariantReport
from metroflow.sim.invariants import validate_invariants as _validate_invariants_core
from metroflow.sim.rng import PRNGKeyArray, next_key
from metroflow.sim.state import SimulationState
from metroflow.ui.snapshots import build_ui_snapshot_source

__all__ = [
    "UISnapshotSource",
    "init_simulation",
    "simulation_step",
    "run_rollout",
    "validate_invariants",
]

UISnapshotSource = dict[str, Any]
_US2_EVENTS_REROUTE_INTEGRATED = True
_US3_POLICY_BLEND_FALLBACK_INTEGRATED = True
_LINK_ID_LOOKUP_CACHE: dict[tuple[int, int], jnp.ndarray] = {}


def init_simulation(
    config: SimulationConfig,
    scenario_seed: int,
) -> tuple[SimulationState, PRNGKeyArray]:
    """Initialize a foundational simulation state skeleton and root PRNG key."""

    bundle = build_initial_simulation_state(
        config=_coerce_config(config),
        scenario_seed=int(scenario_seed),
        eager_trip_generation=False,
    )
    return bundle.state, bundle.rng_key


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
    next_state = _apply_us2_event_and_effects_step_boundary(next_state, cur_control)
    tick_counters = _zero_tick_counters()
    if not cur_control.pause:
        next_state, tick_counters = _run_baseline_tick_orchestration(next_state)
    invariant_report = _validate_invariants_core(next_state)

    ui_snapshot_source = _build_optional_ui_snapshot_source_for_step(
        state=next_state,
        control=cur_control,
        invariant_report=invariant_report,
        tick_counters=tick_counters,
    )
    ui_snapshot_emitted = ui_snapshot_source is not None

    metrics_state = _update_metrics_state_stub(
        next_state=next_state,
        prior_metrics_state=next_state.dynamic.metrics_state,
        invariant_report=invariant_report,
        ui_snapshot_emitted=ui_snapshot_emitted,
        tick_counters=tick_counters,
    )
    next_dynamic_metadata = (
        dict(next_state.dynamic.metadata)
        if isinstance(next_state.dynamic.metadata, Mapping)
        else {}
    )
    for key in (
        "us2_reroute_decisions_total",
        "us2_persistence_decisions_total",
        "us2_corridor_shift_count_total",
    ):
        if key in metrics_state:
            next_dynamic_metadata[key] = int(metrics_state.get(key, 0))
    next_state = next_state.with_dynamic_updates(
        metrics_state=metrics_state,
        invariant_state=invariant_report,
        last_ui_snapshot_source=ui_snapshot_source,
        metadata=next_dynamic_metadata,
    )

    telemetry = _build_step_telemetry(
        state=next_state,
        invariant_report=invariant_report,
        ui_snapshot_emitted=ui_snapshot_emitted,
        tick_counters=tick_counters,
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
    tick_counters: Mapping[str, int] | None = None,
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

    counters = tick_counters or {}
    return SimulationTelemetry(
        tick_index=state.tick_index,
        active_agent_count=active_agent_count,
        trip_generated_this_tick=int(counters.get("trip_generated_this_tick", 0)),
        trip_completed_this_tick=int(counters.get("trip_completed_this_tick", 0)),
        trip_failed_this_tick=int(counters.get("trip_failed_this_tick", 0)),
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

    return build_ui_snapshot_source(
        state=state,
        invariant_report=invariant_report,
    )


def _build_optional_ui_snapshot_source_for_step(
    *,
    state: SimulationState,
    control: SimulationControl,
    invariant_report: InvariantReport,
    tick_counters: Mapping[str, int] | None = None,
) -> UISnapshotSource | None:
    # UI snapshot building is a host-side tail stage and should be skipped unless
    # UI emission is even possible on this tick.
    if not (state.config.ui_stream_enabled or control.ui_force_snapshot):
        return None
    preview_metrics_state = _update_metrics_state_stub(
        next_state=state,
        prior_metrics_state=state.dynamic.metrics_state,
        invariant_report=invariant_report,
        ui_snapshot_emitted=False,
        tick_counters=tick_counters,
    )
    snapshot_state = state.with_dynamic_updates(metrics_state=preview_metrics_state)
    return _maybe_build_ui_snapshot_source(snapshot_state, control, invariant_report)


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
    tick_counters: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    metrics = (
        dict(prior_metrics_state)
        if isinstance(prior_metrics_state, Mapping)
        else _initial_metrics_state()
    )
    prev_capacity_count = int(metrics.get("capacity_violation_count", 0))
    counters = tick_counters or {}
    active_agents = _extract_active_agent_count(next_state)
    queued_trip_requests = _extract_queued_trip_requests(next_state)
    pending_trip_requests = _extract_pending_trip_requests(next_state, fallback=queued_trip_requests)
    current_capacity_count = _extract_capacity_violation_count(
        next_state,
        fallback=prev_capacity_count,
    )

    metrics.update(
        {
            "tick_index": next_state.tick_index,
            "active_agents": active_agents,
            "queued_trip_requests": queued_trip_requests,
            "pending_trip_requests": pending_trip_requests,
            "capacity_violation_count": current_capacity_count,
            "capacity_violation_count_delta": max(
                0,
                current_capacity_count - prev_capacity_count,
            ),
            "negative_queue_detected": invariant_report.counters.negative_queue_violations > 0,
            "ui_packets_emitted": int(metrics.get("ui_packets_emitted", 0))
            + int(ui_snapshot_emitted),
            "generated_trip_total": int(metrics.get("generated_trip_total", 0))
            + int(counters.get("trip_generated_this_tick", 0)),
            "completed_trips_total": int(metrics.get("completed_trips_total", 0))
            + int(counters.get("trip_completed_this_tick", 0)),
            "failed_trips_total": int(metrics.get("failed_trips_total", 0))
            + int(counters.get("trip_failed_this_tick", 0)),
            "us2_reroute_decisions_total": int(metrics.get("us2_reroute_decisions_total", 0))
            + int(counters.get("us2_reroute_decisions_this_tick", 0)),
            "us2_persistence_decisions_total": int(metrics.get("us2_persistence_decisions_total", 0))
            + int(counters.get("us2_persistence_decisions_this_tick", 0)),
            "us2_corridor_shift_count_total": int(metrics.get("us2_corridor_shift_count_total", 0))
            + int(counters.get("us2_corridor_shifts_this_tick", 0)),
        }
    )
    return metrics


def _zero_tick_counters() -> dict[str, int]:
    return {
        "trip_generated_this_tick": 0,
        "trip_completed_this_tick": 0,
        "trip_failed_this_tick": 0,
        "us2_reroute_decisions_this_tick": 0,
        "us2_persistence_decisions_this_tick": 0,
        "us2_corridor_shifts_this_tick": 0,
    }


def _apply_us2_event_and_effects_step_boundary(
    state: SimulationState,
    control: SimulationControl,
) -> SimulationState:
    """US2 step-boundary hook: inject/advance events and apply active effects."""

    if not _is_structured_baseline_state(state):
        return state

    scheduler_state = _coerce_event_scheduler_state(state.dynamic.event_state)
    try:
        injected = _normalize_injected_events(control.inject_event)
    except (TypeError, ValueError):
        # Fail-soft on malformed injected event controls at step boundary.
        injected = ()
    if injected:
        scheduler_state = _merge_injected_events(
            scheduler_state,
            injected_events=injected,
        )
    scheduler_state = advance_traffic_event_scheduler(
        scheduler_state,
        current_tick=state.tick_index,
        clear_event_ids=tuple(control.clear_event_ids),
    )

    next_link_state = state.dynamic.flow_link_state
    affected_link_ids: tuple[int, ...] = ()
    if isinstance(next_link_state, LinkState):
        routing_static = state.static.routing_static if isinstance(state.static.routing_static, Mapping) else {}
        road_csr = routing_static.get("road_csr")
        if road_csr is not None:
            effects = apply_active_event_effects_to_link_state(
                road_csr=road_csr,
                link_state=next_link_state,
                active_events=scheduler_state.active_events,
                validate=False,
            )
            next_link_state = effects.link_state
            affected_link_ids = tuple(int(v) for v in effects.affected_link_ids)

    next_metadata = dict(state.dynamic.metadata) if isinstance(state.dynamic.metadata, Mapping) else {}
    next_metadata["us2_active_event_affected_link_ids"] = affected_link_ids
    next_metadata["us2_active_event_ids"] = tuple(int(ev.event_id) for ev in scheduler_state.active_events)

    return state.with_dynamic_updates(
        event_state=scheduler_state,
        flow_link_state=next_link_state,
        metadata=next_metadata,
    )


def _run_baseline_tick_orchestration(
    state: SimulationState,
) -> tuple[SimulationState, dict[str, int]]:
    """Best-effort baseline tick pipeline for T036 on structured init state."""

    if not _is_structured_baseline_state(state):
        return state, _zero_tick_counters()

    counters = _zero_tick_counters()
    demand_state = dict(state.dynamic.demand_state or {})
    if isinstance(demand_state.get("spawned_slot_ids"), Mapping):
        demand_state["spawned_slot_ids"] = dict(demand_state["spawned_slot_ids"])
    dynamic_metadata = _copy_dynamic_metadata_for_step(state.dynamic.metadata)
    host_cache = _routing_host_cache_from_metadata(dynamic_metadata)
    _prepare_dynamic_potential_cache_for_tick(host_cache, tick_index=state.tick_index)
    route_candidate_state = _coerce_route_candidate_state(state.dynamic.route_candidate_state)
    adaptive_learning_state = _coerce_adaptive_learning_state(state.dynamic.adaptive_learning_state)
    policy_blend_state = _coerce_policy_blend_state(
        state.dynamic.policy_blend_state,
        learning_enabled=state.config.learning_enabled,
    )
    if state.config.learning_enabled:
        policy_blend_state = policy_blend_state.with_lambda(
            state.config.learning_mix_bounds.lambda_max,
            bounds=state.config.learning_mix_bounds,
        )

    trip_requests = tuple(demand_state.get("trip_requests", ()))
    if not trip_requests:
        generated = _generate_current_band_trip_requests_if_needed(state, demand_state, host_cache)
        if generated is not None:
            trip_requests = generated
            demand_state["trip_requests"] = trip_requests
            counters["trip_generated_this_tick"] += len(trip_requests)

    activated = activate_trip_requests(trip_requests, current_tick=state.tick_index)
    demand_state["trip_requests"] = activated

    next_pool, demand_state, route_candidate_state, adaptive_learning_state, policy_blend_state, spawn_failures = (
        _spawn_due_activated_trips(
        state,
        demand_state,
        route_candidate_state=route_candidate_state,
        adaptive_learning_state=adaptive_learning_state,
        policy_blend_state=policy_blend_state,
        host_cache=host_cache,
    )
    )
    counters["trip_failed_this_tick"] += spawn_failures

    next_pool, completed_count, failed_count, outcome_rows = _advance_and_complete_active_agents(
        state,
        next_pool,
        host_cache=host_cache,
        tick_counters=counters,
    )
    counters["trip_completed_this_tick"] += completed_count
    counters["trip_failed_this_tick"] += failed_count
    if state.config.learning_enabled:
        adaptive_learning_state = _apply_online_learning_updates(
            state=state,
            adaptive_learning_state=adaptive_learning_state,
            policy_blend_state=policy_blend_state,
            outcome_rows=outcome_rows,
        )

    demand_state = _refresh_demand_counters(demand_state)
    next_link_state, next_node_state = _update_flow_states_from_active_pool(state, next_pool)

    next_state = state.with_dynamic_updates(
        demand_state=demand_state,
        active_agent_pool=next_pool,
        flow_link_state=next_link_state,
        flow_node_state=next_node_state,
        route_candidate_state=route_candidate_state,
        adaptive_learning_state=adaptive_learning_state,
        policy_blend_state=policy_blend_state,
        metadata=dynamic_metadata,
    )
    return next_state, counters


def _is_structured_baseline_state(state: SimulationState) -> bool:
    demand_state = state.dynamic.demand_state
    if not isinstance(demand_state, Mapping):
        return False
    if "trip_requests" not in demand_state:
        return False
    routing_static = state.static.routing_static
    if not isinstance(routing_static, Mapping):
        return False
    return "road_csr" in routing_static and state.static.population is not None and state.static.pois is not None


def _generate_current_band_trip_requests_if_needed(
    state: SimulationState,
    demand_state: dict[str, Any],
    host_cache: dict[str, Any],
) -> tuple[TripRequest, ...] | None:
    if state.static.population is None or state.static.schedule_templates is None:
        return None
    if state.static.pois is None or state.static.zones is None:
        return None

    batch_key = f"{state.day_type.value}:{state.time_band.value}"
    generated_batches = tuple(str(x) for x in demand_state.get("generated_trip_request_batches", ()))
    if batch_key in generated_batches:
        return None

    routing_static = state.static.routing_static if isinstance(state.static.routing_static, Mapping) else {}
    node_zone_by_id = routing_static.get("node_zone_by_id")
    zone_node_ids = routing_static.get("zone_node_ids")
    if node_zone_by_id is None or zone_node_ids is None:
        return None

    context = _trip_generation_context(
        state=state,
        host_cache=host_cache,
        node_zone_by_id=node_zone_by_id,
        zone_node_ids=zone_node_ids,
    )
    generated = generate_trip_requests(
        context["population"],
        context["zoning"],
        config=state.config,
        seed=int(state.metadata.get("scenario_seed", state.config.random_seed)),
        day_type=state.day_type,
        time_band=state.time_band,
        start_tick=state.tick_index,
    )
    next_trip_request_id = int(demand_state.get("next_trip_request_id", 1))
    remapped, next_trip_request_id = _remap_trip_request_ids(
        tuple(generated.trip_requests),
        start_trip_request_id=next_trip_request_id,
    )
    demand_state["next_trip_request_id"] = next_trip_request_id
    demand_state["generated_trip_request_batches"] = (*generated_batches, batch_key)
    return remapped


def _spawn_due_activated_trips(
    state: SimulationState,
    demand_state: dict[str, Any],
    *,
    route_candidate_state: dict[str, Any],
    adaptive_learning_state: dict[str, Any],
    policy_blend_state: PolicyBlendState,
    host_cache: dict[str, Any],
) -> tuple[ActiveAgentPool, dict[str, Any], dict[str, Any], dict[str, Any], PolicyBlendState, int]:
    pool = state.dynamic.active_agent_pool
    if not isinstance(pool, ActiveAgentPool):
        return (
            create_active_agent_pool(state.config.active_agent_capacity),
            demand_state,
            route_candidate_state,
            adaptive_learning_state,
            policy_blend_state,
            0,
        )
    trips = tuple(demand_state.get("trip_requests", ()))
    if not trips:
        return pool, demand_state, route_candidate_state, adaptive_learning_state, policy_blend_state, 0

    routing_static = state.static.routing_static if isinstance(state.static.routing_static, Mapping) else {}
    road_csr = routing_static.get("road_csr")
    if road_csr is None:
        return pool, demand_state, route_candidate_state, adaptive_learning_state, policy_blend_state, 0

    pois = tuple(state.static.pois or ())
    poi_node_by_id = {int(poi.poi_id): int(poi.node_id) for poi in pois}
    node_zone_by_id = routing_static.get("node_zone_by_id", {})
    citizens = tuple(state.static.population or ())
    citizen_by_id = {int(c.citizen_id): c for c in citizens}
    active_routes = host_cache.setdefault("active_trip_routes", {})
    active_trip_learning_context = host_cache.setdefault("active_trip_learning_context", {})
    candidate_sets = route_candidate_state.setdefault("candidate_sets", {})
    bandit_states = adaptive_learning_state.setdefault("od_bandit_states", {})
    incident_active = bool(_active_event_affected_link_ids_from_metadata(state.dynamic.metadata)) and _has_active_traffic_events(
        state.dynamic.event_state
    )
    tick_fallback_triggered = bool(policy_blend_state.fallback_triggered)
    tick_fallback_reason = policy_blend_state.fallback_reason
    tick_adaptive_enabled = bool(policy_blend_state.adaptive_enabled)
    tick_decision_count = 0

    failed = 0
    next_trips: list[TripRequest] = []
    for trip in trips:
        if trip.status != TripRequestStatus.ACTIVATED:
            next_trips.append(trip)
            continue
        if int(pool.free_slot_count) <= 0:
            next_trips.append(trip)
            continue

        origin_node_id = poi_node_by_id.get(int(trip.origin_poi_id))
        dest_node_id = poi_node_by_id.get(int(trip.dest_poi_id))
        citizen = citizen_by_id.get(int(trip.citizen_id))
        if origin_node_id is None or dest_node_id is None or citizen is None:
            failed += 1
            continue

        od_key = _od_key_for_trip(
            origin_node_id=origin_node_id,
            destination_node_id=dest_node_id,
            node_zone_by_id=node_zone_by_id,
        )
        selection = _select_route_for_trip_spawn(
            state=state,
            road_csr=road_csr,
            origin_node_id=origin_node_id,
            dest_node_id=dest_node_id,
            od_key=od_key,
            route_candidate_state=route_candidate_state,
            adaptive_learning_state=adaptive_learning_state,
            policy_blend_state=policy_blend_state,
            incident_active=incident_active,
            host_cache=host_cache,
        )
        selection_blend_state = selection["policy_blend_state"]
        policy_blend_state = selection_blend_state
        tick_decision_count += 1
        tick_fallback_triggered = tick_fallback_triggered or bool(selection_blend_state.fallback_triggered)
        if tick_fallback_reason is None and selection_blend_state.fallback_reason is not None:
            tick_fallback_reason = selection_blend_state.fallback_reason
        tick_adaptive_enabled = tick_adaptive_enabled or bool(selection_blend_state.adaptive_enabled)
        candidate_sets[selection["candidate_state_key"]] = selection["candidate_set"]
        bandit_state = selection.get("bandit_state")
        if isinstance(bandit_state, ODBanditState):
            bandit_states[selection["bandit_state_key"]] = bandit_state
        path = selection["path"]
        if not path:
            failed += 1
            continue

        try:
            pool, slot_id = allocate_active_agent_slot(
                pool,
                ActiveAgentSlot.spawn(
                    citizen_id=trip.citizen_id,
                    trip_id=trip.trip_request_id,
                    current_link_id=int(path[0]),
                    dest_node_id=dest_node_id,
                    behavior_profile_id=int(citizen.behavior_profile_id),
                    progress_01=0.0,
                    remaining_route_ptr=1,
                ),
            )
        except RuntimeError:
            next_trips.append(trip)
            continue
        active_routes[int(trip.trip_request_id)] = tuple(int(x) for x in path)
        active_trip_learning_context[int(trip.trip_request_id)] = {
            "trip_id": int(trip.trip_request_id),
            "tick_index": int(state.tick_index),
            "od_key": tuple(od_key),
            "chosen_candidate_id": selection["chosen_candidate_id"],
            "chosen_arm_index": selection["chosen_arm_index"],
            "baseline_travel_time": selection["baseline_travel_time"],
            "policy_mix_lambda": float(policy_blend_state.lambda_mix),
            "adaptive_fallback_triggered": bool(policy_blend_state.fallback_triggered),
            "bandit_state_key": selection["bandit_state_key"],
        }
        demand_state.setdefault("spawned_slot_ids", {})[int(trip.trip_request_id)] = int(slot_id)
        # Spawned trips leave the pending request pool for conservation accounting.
    demand_state["trip_requests"] = tuple(next_trips)
    route_candidate_state["candidate_sets"] = candidate_sets
    route_candidate_state["last_refresh_tick"] = int(state.tick_index)
    adaptive_learning_state["od_bandit_states"] = bandit_states
    if tick_decision_count > 0:
        policy_blend_state = replace(
            policy_blend_state,
            fallback_triggered=tick_fallback_triggered,
            fallback_reason=tick_fallback_reason,
            baseline_only_mode=not tick_adaptive_enabled,
        )
    return pool, demand_state, route_candidate_state, adaptive_learning_state, policy_blend_state, failed


def _advance_and_complete_active_agents(
    state: SimulationState,
    pool: ActiveAgentPool,
    *,
    host_cache: dict[str, Any],
    tick_counters: dict[str, int] | None = None,
) -> tuple[ActiveAgentPool, int, int, tuple[dict[str, Any], ...]]:
    if not isinstance(pool, ActiveAgentPool):
        return pool, 0, 0, ()
    routing_static = state.static.routing_static if isinstance(state.static.routing_static, Mapping) else {}
    road_csr = routing_static.get("road_csr")
    if road_csr is None:
        return pool, 0, 0, ()

    active_routes = host_cache.setdefault("active_trip_routes", {})
    active_trip_learning_context = host_cache.setdefault("active_trip_learning_context", {})
    completed = 0
    failed = 0
    outcome_rows: list[dict[str, Any]] = []
    next_pool = pool
    profile_by_id = _behavior_profile_map_for_state(state, host_cache=host_cache)
    affected_link_ids = _active_event_affected_link_ids_from_metadata(state.dynamic.metadata)
    incident_active = bool(affected_link_ids) and _has_active_traffic_events(state.dynamic.event_state)
    alive_mask = jnp.asarray(pool.alive_mask, dtype=jnp.bool_)
    progress_candidate = jnp.asarray(pool.progress_01, dtype=jnp.float32) + 0.5
    ready_mask = alive_mask & (progress_candidate >= 1.0)
    next_pool = replace(
        next_pool,
        progress_01=jnp.where(
            alive_mask & (~ready_mask),
            progress_candidate,
            jnp.asarray(next_pool.progress_01, dtype=jnp.float32),
        ),
    )
    alive_indices = [int(i) for i in jnp.where(ready_mask)[0].tolist()]

    for slot_id in alive_indices:
        if not bool(next_pool.alive_mask[slot_id]):
            continue
        trip_id = int(next_pool.trip_id[slot_id])
        current_link_id = int(next_pool.current_link_id[slot_id])
        dest_node_id = int(next_pool.dest_node_id[slot_id])
        route = tuple(active_routes.get(trip_id, ()))
        route_ptr = int(next_pool.remaining_route_ptr[slot_id])
        link_index = road_csr.link_id_to_index.get(current_link_id)
        if link_index is None:
            _append_learning_outcome_row(
                outcome_rows,
                active_trip_learning_context.pop(trip_id, None),
                outcome="failed",
                tick_index=state.tick_index,
            )
            next_pool = release_active_agent_slot(next_pool, slot_id)
            active_routes.pop(trip_id, None)
            failed += 1
            continue
        current_link = road_csr.links[link_index]
        if int(current_link.dst_node_id) == dest_node_id:
            _append_learning_outcome_row(
                outcome_rows,
                active_trip_learning_context.pop(trip_id, None),
                outcome="completed",
                tick_index=state.tick_index,
            )
            next_pool = release_active_agent_slot(next_pool, slot_id)
            active_routes.pop(trip_id, None)
            completed += 1
            continue

        updated_route = route
        updated_route_ptr = route_ptr
        updated_cooldown = int(next_pool.reroute_cooldown_ticks[slot_id])
        if incident_active and route_ptr < len(route) and _route_intersects_affected_links(
            current_link_id=current_link_id,
            route=route,
            route_ptr=route_ptr,
            affected_link_ids=affected_link_ids,
        ):
            reroute_out = _maybe_reroute_active_trip_at_link_boundary(
                state=state,
                road_csr=road_csr,
                flow_link_state=state.dynamic.flow_link_state,
                host_cache=host_cache,
                profile_by_id=profile_by_id,
                active_routes=active_routes,
                trip_id=trip_id,
                current_link=current_link,
                dest_node_id=dest_node_id,
                route=route,
                route_ptr=route_ptr,
                behavior_profile_id=int(next_pool.behavior_profile_id[slot_id]),
                reroute_cooldown_ticks=int(next_pool.reroute_cooldown_ticks[slot_id]),
                affected_link_ids=affected_link_ids,
                tick_counters=tick_counters,
            )
            if tick_counters is not None and bool(reroute_out.get("decision_evaluated", False)):
                if bool(reroute_out.get("did_reroute", False)):
                    tick_counters["us2_reroute_decisions_this_tick"] = int(
                        tick_counters.get("us2_reroute_decisions_this_tick", 0)
                    ) + 1
                else:
                    tick_counters["us2_persistence_decisions_this_tick"] = int(
                        tick_counters.get("us2_persistence_decisions_this_tick", 0)
                    ) + 1
                if bool(reroute_out.get("corridor_shifted", False)):
                    tick_counters["us2_corridor_shifts_this_tick"] = int(
                        tick_counters.get("us2_corridor_shifts_this_tick", 0)
                    ) + 1
            updated_route = reroute_out["route"]
            updated_route_ptr = int(reroute_out["route_ptr"])
            updated_cooldown = int(reroute_out["next_cooldown"])
            active_routes[trip_id] = tuple(int(x) for x in updated_route)

        if updated_route_ptr < len(updated_route):
            next_link_id = int(updated_route[updated_route_ptr])
            next_pool = replace(
                next_pool,
                current_link_id=next_pool.current_link_id.at[slot_id].set(next_link_id),
                progress_01=next_pool.progress_01.at[slot_id].set(0.0),
                remaining_route_ptr=next_pool.remaining_route_ptr.at[slot_id].set(updated_route_ptr + 1),
                reroute_cooldown_ticks=next_pool.reroute_cooldown_ticks.at[slot_id].set(updated_cooldown),
            )
            continue

        _append_learning_outcome_row(
            outcome_rows,
            active_trip_learning_context.pop(trip_id, None),
            outcome="failed",
            tick_index=state.tick_index,
        )
        next_pool = release_active_agent_slot(next_pool, slot_id)
        active_routes.pop(trip_id, None)
        failed += 1

    return next_pool, completed, failed, tuple(outcome_rows)


def _refresh_demand_counters(demand_state: dict[str, Any]) -> dict[str, Any]:
    trips = tuple(demand_state.get("trip_requests", ()))
    pending_count = len(trips)
    queued_count = sum(
        1
        for trip in trips
        if isinstance(trip, TripRequest) and trip.status == TripRequestStatus.QUEUED
    )
    activated_count = sum(
        1
        for trip in trips
        if isinstance(trip, TripRequest) and trip.status == TripRequestStatus.ACTIVATED
    )
    out = dict(demand_state)
    out["trip_requests"] = trips
    out["queued_trip_requests"] = queued_count
    out["pending_trip_requests"] = pending_count
    out["activated_trip_requests"] = activated_count
    return out


def _update_flow_states_from_active_pool(
    state: SimulationState,
    pool: ActiveAgentPool,
) -> tuple[LinkState | Any, NodeState | Any]:
    flow_link_state = state.dynamic.flow_link_state
    flow_node_state = state.dynamic.flow_node_state
    routing_static = state.static.routing_static if isinstance(state.static.routing_static, Mapping) else {}
    road_csr = routing_static.get("road_csr")
    if road_csr is None or not isinstance(flow_link_state, LinkState) or not isinstance(flow_node_state, NodeState):
        return flow_link_state, flow_node_state

    link_count = int(flow_link_state.link_count)
    current_link_ids = jnp.asarray(pool.current_link_id, dtype=jnp.int32)
    alive_mask = jnp.asarray(pool.alive_mask, dtype=jnp.bool_)
    queue_counts = _compute_queue_counts_from_active_pool_core(
        current_link_ids=current_link_ids,
        alive_mask=alive_mask,
        link_count=link_count,
        road_csr=road_csr,
    )

    pre_link = LinkState(
        queue_vehicles=queue_counts,
        inflow_vehicles=jnp.zeros_like(flow_link_state.inflow_vehicles),
        outflow_vehicles=jnp.zeros_like(flow_link_state.outflow_vehicles),
        travel_time_cost=flow_link_state.travel_time_cost,
        capacity_veh_per_tick=flow_link_state.capacity_veh_per_tick,
        incident_capacity_multiplier=flow_link_state.incident_capacity_multiplier,
        capacity_violation_flags=jnp.zeros_like(flow_link_state.capacity_violation_flags, dtype=jnp.bool_),
        metadata=dict(flow_link_state.metadata),
    )
    pre_node = NodeState(
        turn_from_link_index=flow_node_state.turn_from_link_index,
        turn_to_link_index=flow_node_state.turn_to_link_index,
        turn_demand=jnp.zeros_like(flow_node_state.turn_demand),
        turn_supply=jnp.zeros_like(flow_node_state.turn_supply),
        turn_flow=jnp.zeros_like(flow_node_state.turn_flow),
        signal_phase_index=flow_node_state.signal_phase_index,
        signal_phase_timer=flow_node_state.signal_phase_timer,
        metadata=dict(flow_node_state.metadata),
    )
    result = update_link_node_flow(pre_link, pre_node, validate=False)
    return result.link_state, result.node_state


def _copy_dynamic_metadata_for_step(metadata: Any) -> dict[str, Any]:
    copied = dict(metadata) if isinstance(metadata, Mapping) else {}
    host_cache = copied.get("routing_host_cache")
    if isinstance(host_cache, Mapping):
        host_copy = dict(host_cache)
        for key in ("active_trip_routes", "active_trip_learning_context", "dynamic_potential_cache", "trip_generation_context"):
            if isinstance(host_copy.get(key), Mapping):
                host_copy[key] = dict(host_copy[key])
        copied["routing_host_cache"] = host_copy
    return copied


def _coerce_route_candidate_state(value: Any) -> dict[str, Any]:
    out = dict(value) if isinstance(value, Mapping) else {}
    candidate_sets = out.get("candidate_sets")
    out["candidate_sets"] = dict(candidate_sets) if isinstance(candidate_sets, Mapping) else {}
    out["last_refresh_tick"] = int(out.get("last_refresh_tick", -1))
    return out


def _coerce_adaptive_learning_state(value: Any) -> dict[str, Any]:
    out = dict(value) if isinstance(value, Mapping) else {}
    bandit_states = out.get("od_bandit_states")
    out["od_bandit_states"] = dict(bandit_states) if isinstance(bandit_states, Mapping) else {}
    out["last_experience_batch_size"] = int(out.get("last_experience_batch_size", 0))
    out["last_online_update_count_delta"] = int(out.get("last_online_update_count_delta", 0))
    out["last_mean_reward_estimate"] = float(out.get("last_mean_reward_estimate", 0.0))
    return out


def _coerce_policy_blend_state(value: Any, *, learning_enabled: bool) -> PolicyBlendState:
    if isinstance(value, PolicyBlendState):
        return value
    if isinstance(value, Mapping):
        return PolicyBlendState(**dict(value))
    return PolicyBlendState(
        lambda_mix=0.0,
        baseline_only_mode=not learning_enabled,
    )


def _od_key_for_trip(
    *,
    origin_node_id: int,
    destination_node_id: int,
    node_zone_by_id: Any,
) -> tuple[int, int]:
    if isinstance(node_zone_by_id, Mapping):
        origin_zone = int(node_zone_by_id.get(int(origin_node_id), origin_node_id))
        dest_zone = int(node_zone_by_id.get(int(destination_node_id), destination_node_id))
        return origin_zone, dest_zone
    return int(origin_node_id), int(destination_node_id)


def _select_route_for_trip_spawn(
    *,
    state: SimulationState,
    road_csr: Any,
    origin_node_id: int,
    dest_node_id: int,
    od_key: tuple[int, int],
    route_candidate_state: dict[str, Any],
    adaptive_learning_state: dict[str, Any],
    policy_blend_state: PolicyBlendState,
    incident_active: bool,
    host_cache: dict[str, Any],
) -> dict[str, Any]:
    candidate_sets = route_candidate_state.setdefault("candidate_sets", {})
    dynamic_potential_cache = host_cache.setdefault("dynamic_potential_cache", {})
    candidate_state_key = _route_candidate_state_key(
        od_key=od_key,
        origin_node_id=origin_node_id,
        destination_node_id=dest_node_id,
    )
    existing_candidate_set = candidate_sets.get(candidate_state_key)
    candidate_set = refresh_od_route_candidate_set(
        existing_candidate_set if isinstance(existing_candidate_set, RouteCandidateSet) else None,
        road_csr=road_csr,
        link_state=state.dynamic.flow_link_state,
        od_key=tuple(od_key),
        origin_node_id=int(origin_node_id),
        destination_node_id=int(dest_node_id),
        current_tick=state.tick_index,
        incident_active=incident_active,
        potential_cache=dynamic_potential_cache,
    )
    baseline_scores = tuple(
        _sum_route_link_costs(path, road_csr=road_csr, flow_link_state=state.dynamic.flow_link_state)
        for path in candidate_set.candidate_paths
    )
    chosen_arm_index = 0 if baseline_scores else None
    chosen_candidate_id = None if not candidate_set.candidate_ids else int(candidate_set.candidate_ids[0])
    selected_path = candidate_set.candidate_paths[0] if candidate_set.candidate_paths else ()
    bandit_state_key = _bandit_state_key_for_candidate_set(
        od_key=od_key,
        origin_node_id=origin_node_id,
        destination_node_id=dest_node_id,
        candidate_set=candidate_set,
    )
    bandit_state = _sync_od_bandit_state_for_candidate_set(
        adaptive_learning_state.get("od_bandit_states", {}).get(bandit_state_key),
        od_key=tuple(od_key),
        candidate_set=candidate_set,
        current_tick=state.tick_index,
    )

    if not state.config.learning_enabled:
        return {
            "candidate_set": candidate_set,
            "bandit_state": bandit_state,
            "path": tuple(selected_path),
            "chosen_arm_index": chosen_arm_index,
            "chosen_candidate_id": chosen_candidate_id,
            "baseline_travel_time": None if chosen_arm_index is None else float(baseline_scores[chosen_arm_index]),
            "policy_blend_state": policy_blend_state,
            "candidate_state_key": candidate_state_key,
            "bandit_state_key": bandit_state_key,
        }

    adaptive_scores = (
        None
        if bandit_state.arm_count <= 0
        else compute_ucb_scores_core(
            bandit_state.estimated_reward,
            bandit_state.pull_count,
        )
    )
    mix_result = mix_route_candidate_scores(
        baseline_scores=baseline_scores,
        adaptive_scores=adaptive_scores,
        blend_state=policy_blend_state,
        target_lambda=state.config.learning_mix_bounds.lambda_max,
        bounds=state.config.learning_mix_bounds,
        learning_enabled=True,
        incident_mode=False,
    )
    chosen_arm_index = mix_result.selected_index
    if chosen_arm_index is None:
        chosen_candidate_id = None
        selected_path = ()
    else:
        chosen_candidate_id = int(candidate_set.candidate_ids[chosen_arm_index])
        selected_path = tuple(candidate_set.candidate_paths[chosen_arm_index])
    return {
        "candidate_set": candidate_set,
        "bandit_state": bandit_state,
        "path": tuple(selected_path),
        "chosen_arm_index": chosen_arm_index,
        "chosen_candidate_id": chosen_candidate_id,
        "baseline_travel_time": None if chosen_arm_index is None else float(baseline_scores[chosen_arm_index]),
        "policy_blend_state": mix_result.blend_state,
        "candidate_state_key": candidate_state_key,
        "bandit_state_key": bandit_state_key,
    }


def _route_candidate_state_key(
    *,
    od_key: tuple[int, int],
    origin_node_id: int,
    destination_node_id: int,
) -> tuple[Any, ...]:
    return (
        "route_candidate_set",
        tuple(int(x) for x in od_key),
        int(origin_node_id),
        int(destination_node_id),
    )


def _bandit_state_key_for_candidate_set(
    *,
    od_key: tuple[int, int],
    origin_node_id: int,
    destination_node_id: int,
    candidate_set: RouteCandidateSet,
) -> tuple[Any, ...]:
    return (
        "od_ucb_bandit",
        tuple(int(x) for x in od_key),
        int(origin_node_id),
        int(destination_node_id),
        tuple(candidate_set.candidate_paths),
    )


def _sync_od_bandit_state_for_candidate_set(
    existing_state: Any,
    *,
    od_key: tuple[int, int],
    candidate_set: RouteCandidateSet,
    current_tick: int,
) -> ODBanditState:
    candidate_ids = tuple(int(x) for x in candidate_set.candidate_ids)
    if isinstance(existing_state, ODBanditState) and not candidate_ids:
        return existing_state
    if (
        isinstance(existing_state, ODBanditState)
        and existing_state.candidate_ids is not None
        and tuple(int(x) for x in existing_state.candidate_ids.tolist()) == candidate_ids
        and int(existing_state.arm_count) == len(candidate_ids)
    ):
        return existing_state
    return create_od_ucb_state(
        od_key=tuple(od_key),
        candidate_count=len(candidate_ids),
        candidate_ids=candidate_ids,
        last_update_tick=current_tick,
    )


def _apply_online_learning_updates(
    *,
    state: SimulationState,
    adaptive_learning_state: dict[str, Any],
    policy_blend_state: PolicyBlendState,
    outcome_rows: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    if not outcome_rows:
        adaptive_learning_state["last_experience_batch_size"] = 0
        adaptive_learning_state["last_online_update_count_delta"] = 0
        adaptive_learning_state["last_mean_reward_estimate"] = 0.0
        return adaptive_learning_state

    experience_batch = build_experience_batch(
        state=state,
        telemetry={
            "tick_index": int(state.tick_index),
            "policy_mix_lambda": float(policy_blend_state.lambda_mix),
            "adaptive_fallback_triggered": bool(policy_blend_state.fallback_triggered),
        },
        outcome_rows=outcome_rows,
    )
    bandit_states = dict(adaptive_learning_state.get("od_bandit_states", {}))
    updated_count = 0
    observed_rewards: list[float] = []
    for experience in experience_batch:
        if experience.chosen_arm_index is None:
            continue
        bandit_state_key = experience.metadata.get("bandit_state_key")
        bandit_state = bandit_states.get(bandit_state_key)
        if not isinstance(bandit_state, ODBanditState):
            continue
        if not (0 <= int(experience.chosen_arm_index) < int(bandit_state.arm_count)):
            continue
        bandit_states[bandit_state_key] = update_od_ucb_state(
            state=bandit_state,
            arm_index=int(experience.chosen_arm_index),
            reward=float(experience.reward),
            tick_index=int(experience.tick_index),
        )
        updated_count += 1
        observed_rewards.append(float(experience.reward))
    adaptive_learning_state["od_bandit_states"] = bandit_states
    adaptive_learning_state["last_experience_batch_size"] = len(experience_batch)
    adaptive_learning_state["last_online_update_count_delta"] = updated_count
    adaptive_learning_state["last_mean_reward_estimate"] = (
        float(sum(observed_rewards) / len(observed_rewards))
        if observed_rewards
        else 0.0
    )
    return adaptive_learning_state


def _append_learning_outcome_row(
    out: list[dict[str, Any]],
    context: Any,
    *,
    outcome: str,
    tick_index: int,
) -> None:
    if not isinstance(context, Mapping):
        return
    started_tick = int(context.get("tick_index", tick_index))
    out.append(
        {
            "tick_index": int(tick_index),
            "trip_id": int(context["trip_id"]),
            "od_key": tuple(context["od_key"]),
            "outcome": str(outcome),
            "chosen_candidate_id": context.get("chosen_candidate_id"),
            "chosen_arm_index": context.get("chosen_arm_index"),
            "observed_travel_time": max(0.0, float(int(tick_index) - started_tick)),
            "baseline_travel_time": context.get("baseline_travel_time"),
            "policy_mix_lambda": float(context.get("policy_mix_lambda", 0.0)),
            "adaptive_fallback_triggered": bool(context.get("adaptive_fallback_triggered", False)),
            "metadata": {
                "bandit_state_key": context.get("bandit_state_key"),
            },
        }
    )


def _routing_host_cache_from_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    host_cache = metadata.get("routing_host_cache")
    if isinstance(host_cache, dict):
        return host_cache
    host_cache = {}
    metadata["routing_host_cache"] = host_cache
    return host_cache


def _prepare_dynamic_potential_cache_for_tick(host_cache: dict[str, Any], *, tick_index: int) -> None:
    tick_index = int(tick_index)
    if int(host_cache.get("dynamic_potential_cache_tick", -1)) == tick_index:
        return
    host_cache["dynamic_potential_cache_tick"] = tick_index
    host_cache["dynamic_potential_cache"] = {}


def _trip_generation_context(
    *,
    state: SimulationState,
    host_cache: dict[str, Any],
    node_zone_by_id: Any,
    zone_node_ids: Any,
) -> dict[str, Any]:
    context = host_cache.get("trip_generation_context")
    signature = (
        id(state.static.population),
        id(state.static.schedule_templates),
        id(state.static.zones),
        id(state.static.pois),
        id(node_zone_by_id),
        id(zone_node_ids),
    )
    if isinstance(context, dict) and context.get("signature") == signature:
        return context

    from metroflow.city.zones import ZoningPlacementResult
    from metroflow.demand.population import PopulationGenerationResult

    context = {
        "signature": signature,
        "zoning": ZoningPlacementResult(
            zones=tuple(state.static.zones or ()),
            pois=tuple(state.static.pois or ()),
            node_zone_by_id=dict(node_zone_by_id),
            zone_node_ids={int(k): tuple(v) for k, v in dict(zone_node_ids).items()},
            metadata={},
        ),
        "population": PopulationGenerationResult(
            citizens=tuple(state.static.population or ()),
            behavior_profiles=(),
            schedule_templates=tuple(state.static.schedule_templates or ()),
            metadata={},
        ),
    }
    host_cache["trip_generation_context"] = context
    return context


def _coerce_event_scheduler_state(event_state: Any) -> TrafficEventSchedulerState:
    if isinstance(event_state, TrafficEventSchedulerState):
        return event_state
    if isinstance(event_state, Mapping):
        return TrafficEventSchedulerState(**dict(event_state))
    return TrafficEventSchedulerState()


def _normalize_injected_events(raw: Any) -> tuple[TrafficEvent, ...]:
    if raw is None:
        return ()
    if isinstance(raw, tuple):
        items = raw
    elif isinstance(raw, list):
        items = tuple(raw)
    else:
        items = (raw,)
    out: list[TrafficEvent] = []
    for item in items:
        if item is None:
            continue
        if isinstance(item, TrafficEvent):
            ev = item
        elif isinstance(item, Mapping):
            ev = TrafficEvent(**dict(item))
        else:
            raise TypeError("inject_event items must be TrafficEvent or Mapping")
        if ev.status is not TrafficEventStatus.SCHEDULED:
            ev = replace(ev, status=TrafficEventStatus.SCHEDULED)
        out.append(ev)
    return tuple(out)


def _merge_injected_events(
    scheduler_state: TrafficEventSchedulerState,
    *,
    injected_events: tuple[TrafficEvent, ...],
) -> TrafficEventSchedulerState:
    if not injected_events:
        return scheduler_state
    replace_ids = {int(ev.event_id) for ev in injected_events}
    scheduled = tuple(
        ev for ev in scheduler_state.scheduled_events if int(ev.event_id) not in replace_ids
    )
    active = tuple(
        ev for ev in scheduler_state.active_events if int(ev.event_id) not in replace_ids
    )
    cleared = tuple(
        ev for ev in scheduler_state.cleared_events if int(ev.event_id) not in replace_ids
    )
    return TrafficEventSchedulerState(
        scheduled_events=(*scheduled, *injected_events),
        active_events=active,
        cleared_events=cleared,
    )


def _has_active_traffic_events(event_state: Any) -> bool:
    if event_state is None:
        return False
    active = _lookup_attr_or_key(event_state, "active_events")
    if active is None:
        return False
    try:
        return len(tuple(active)) > 0
    except TypeError:
        return False


def _behavior_profile_map_for_state(
    state: SimulationState,
    *,
    host_cache: dict[str, Any],
) -> dict[int, Any]:
    cached = host_cache.get("behavior_profile_map")
    static_meta = state.static.metadata if isinstance(state.static.metadata, Mapping) else {}
    explicit_profiles = static_meta.get("behavior_profiles")
    if explicit_profiles is not None:
        try:
            explicit_tuple = tuple(explicit_profiles)
        except TypeError:
            explicit_tuple = ()
    else:
        explicit_tuple = ()
    signature = (
        "explicit" if explicit_tuple else "generated",
        id(explicit_tuple) if explicit_tuple else id(state.static.population),
        int(state.metadata.get("scenario_seed", state.config.random_seed)),
        int(_max_behavior_profile_id_cached(state.static.population, host_cache=host_cache)),
    )
    if isinstance(cached, dict) and cached.get("signature") == signature:
        profiles = cached.get("profiles")
        if isinstance(profiles, Mapping):
            return dict(profiles)

    if explicit_tuple:
        profiles = explicit_tuple
    else:
        max_id = max(1, int(signature[3]))
        profiles = generate_route_choice_profiles(seed=int(signature[2]), count=max_id)
    profile_map = {int(p.behavior_profile_id): p for p in profiles}
    host_cache["behavior_profile_map"] = {
        "signature": signature,
        "profiles": dict(profile_map),
    }
    return profile_map


def _max_behavior_profile_id_cached(population: Any, *, host_cache: dict[str, Any]) -> int:
    cached = host_cache.get("behavior_profile_max_id")
    signature = id(population)
    if isinstance(cached, dict) and int(cached.get("population_id", -1)) == int(signature):
        return int(cached.get("value", 0))
    value = _max_behavior_profile_id(population)
    host_cache["behavior_profile_max_id"] = {"population_id": int(signature), "value": int(value)}
    return int(value)


def _max_behavior_profile_id(population: Any) -> int:
    max_id = 0
    try:
        people = tuple(population or ())
    except TypeError:
        return 0
    for citizen in people:
        value = _lookup_attr_or_key(citizen, "behavior_profile_id")
        if value is None:
            continue
        try:
            max_id = max(max_id, int(value))
        except Exception:
            continue
    return max_id


def _active_event_affected_link_ids_from_metadata(metadata: Any) -> frozenset[int]:
    if not isinstance(metadata, Mapping):
        return frozenset()
    raw = metadata.get("us2_active_event_affected_link_ids", ())
    try:
        return frozenset(int(v) for v in tuple(raw))
    except Exception:
        return frozenset()


def _route_intersects_affected_links(
    *,
    current_link_id: int,
    route: tuple[int, ...],
    route_ptr: int,
    affected_link_ids: frozenset[int],
) -> bool:
    if not affected_link_ids:
        return False
    if int(current_link_id) in affected_link_ids:
        return True
    tail = route[max(0, int(route_ptr)) :]
    return any(int(link_id) in affected_link_ids for link_id in tail)


def _maybe_reroute_active_trip_at_link_boundary(
    *,
    state: SimulationState,
    road_csr: Any,
    flow_link_state: Any,
    host_cache: dict[str, Any],
    profile_by_id: Mapping[int, Any],
    active_routes: dict[int, tuple[int, ...]],
    trip_id: int,
    current_link: Any,
    dest_node_id: int,
    route: tuple[int, ...],
    route_ptr: int,
    behavior_profile_id: int,
    reroute_cooldown_ticks: int,
    affected_link_ids: frozenset[int],
    tick_counters: dict[str, int] | None = None,
) -> dict[str, Any]:
    out = {
        "route": route,
        "route_ptr": route_ptr,
        "next_cooldown": max(0, int(reroute_cooldown_ticks)),
        "decision_evaluated": False,
        "did_reroute": False,
        "corridor_shifted": False,
    }
    if not isinstance(flow_link_state, LinkState):
        return out
    if route_ptr >= len(route):
        return out
    profile = profile_by_id.get(int(behavior_profile_id))
    if profile is None:
        return out
    origin_node_id = int(getattr(current_link, "dst_node_id", -1))
    if origin_node_id < 0:
        return out

    dynamic_potential_cache = host_cache.setdefault("dynamic_potential_cache", {})
    potential = compute_dynamic_potential_state(
        road_csr,
        destination_node_id=int(dest_node_id),
        link_state=flow_link_state,
        cache=dynamic_potential_cache,
        cache_key=("dest", int(dest_node_id)),
    )
    candidate_route = build_greedy_route_candidate(
        road_csr,
        potential,
        origin_node_id=origin_node_id,
    )
    if not candidate_route:
        return out

    current_remaining_cost = _sum_route_link_costs(route[route_ptr:], road_csr=road_csr, flow_link_state=flow_link_state)
    candidate_remaining_cost = _sum_route_link_costs(candidate_route, road_csr=road_csr, flow_link_state=flow_link_state)
    decision = decide_reroute_vs_persist(
        profile=profile,
        current_remaining_cost=current_remaining_cost,
        candidate_remaining_cost=candidate_remaining_cost,
        incident_active=True,
        reroute_cooldown_ticks=int(reroute_cooldown_ticks),
    )
    out["decision_evaluated"] = True
    out["next_cooldown"] = int(decision.next_reroute_cooldown_ticks)
    if not bool(decision.should_reroute):
        return out

    rerouted_full = (int(getattr(current_link, "link_id")),) + tuple(int(x) for x in candidate_route)
    out["did_reroute"] = True
    current_affected_exposure = sum(1 for link_id in route[route_ptr:] if int(link_id) in affected_link_ids)
    candidate_affected_exposure = sum(1 for link_id in candidate_route if int(link_id) in affected_link_ids)
    out["corridor_shifted"] = bool(candidate_affected_exposure < current_affected_exposure)
    active_routes[int(trip_id)] = rerouted_full
    out["route"] = rerouted_full
    out["route_ptr"] = 1
    return out


def _sum_route_link_costs(route_link_ids: tuple[int, ...], *, road_csr: Any, flow_link_state: LinkState) -> float:
    if not route_link_ids:
        return float("inf")
    total = 0.0
    travel_cost = jnp.asarray(flow_link_state.travel_time_cost, dtype=jnp.float32)
    for link_id in route_link_ids:
        idx = road_csr.link_id_to_index.get(int(link_id))
        if idx is None:
            return float("inf")
        total += float(travel_cost[int(idx)])
    return float(total)


def _remap_trip_request_ids(
    trip_requests: tuple[TripRequest, ...],
    *,
    start_trip_request_id: int,
) -> tuple[tuple[TripRequest, ...], int]:
    next_id = int(start_trip_request_id)
    if next_id < 1:
        next_id = 1
    if not trip_requests:
        return trip_requests, next_id
    remapped = tuple(
        replace(trip, trip_request_id=(next_id + i))
        for i, trip in enumerate(trip_requests)
    )
    return remapped, next_id + len(remapped)


def _link_id_index_lookup_array(road_csr: Any) -> jnp.ndarray:
    cache_key = (
        id(road_csr),
        int(getattr(road_csr, "link_count", 0)),
    )
    cached = _LINK_ID_LOOKUP_CACHE.get(cache_key)
    if cached is not None:
        return cached
    mapping = getattr(road_csr, "link_id_to_index", {})
    if not mapping:
        arr = jnp.asarray([], dtype=jnp.int32)
        _LINK_ID_LOOKUP_CACHE[cache_key] = arr
        _prune_link_lookup_cache()
        return arr
    max_link_id = max(int(k) for k in mapping)
    arr = jnp.full((max_link_id + 1,), -1, dtype=jnp.int32)
    for link_id, idx in mapping.items():
        arr = arr.at[int(link_id)].set(int(idx))
    _LINK_ID_LOOKUP_CACHE[cache_key] = arr
    _prune_link_lookup_cache()
    return arr


def _prune_link_lookup_cache(max_entries: int = 32) -> None:
    while len(_LINK_ID_LOOKUP_CACHE) > int(max_entries):
        _LINK_ID_LOOKUP_CACHE.pop(next(iter(_LINK_ID_LOOKUP_CACHE)))


def _compute_queue_counts_from_active_pool_core(
    *,
    current_link_ids: jnp.ndarray,
    alive_mask: jnp.ndarray,
    link_count: int,
    road_csr: Any,
) -> jnp.ndarray:
    if int(link_count) <= 0:
        return jnp.zeros((0,), dtype=jnp.float32)
    lookup = _link_id_index_lookup_array(road_csr)
    if int(lookup.shape[0]) == 0:
        return jnp.zeros((int(link_count),), dtype=jnp.float32)

    upper = int(lookup.shape[0])
    clipped_link_ids = jnp.clip(current_link_ids, 0, upper - 1)
    mapped_indices = lookup[clipped_link_ids]
    in_range = (current_link_ids >= 0) & (current_link_ids < upper)
    valid = alive_mask & in_range & (mapped_indices >= 0)
    safe_indices = jnp.where(valid, mapped_indices, 0).astype(jnp.int32)
    weights = valid.astype(jnp.float32)
    return jnp.asarray(jnp.bincount(safe_indices, weights=weights, length=int(link_count)), dtype=jnp.float32)


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


def _extract_pending_trip_requests(state: SimulationState, *, fallback: int = 0) -> int:
    demand_state = state.dynamic.demand_state
    value = _lookup_attr_or_key(demand_state, "pending_trip_requests")
    if value is not None:
        return int(value)
    trips = _lookup_attr_or_key(demand_state, "trip_requests")
    if trips is not None:
        try:
            return len(trips)
        except TypeError:
            pass
    value = _lookup_attr_or_key(demand_state, "queued_trip_requests")
    if value is not None:
        return int(value)
    return int(fallback)


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
