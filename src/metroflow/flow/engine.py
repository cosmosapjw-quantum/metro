"""Baseline link-queue + node-model flow updates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import jax
import jax.numpy as jnp

from metroflow.flow.state import LinkState, NodeState, validate_link_state, validate_node_state

__all__ = [
    "BaselineFlowUpdateResult",
    "compute_baseline_flow_arrays",
    "compute_baseline_flow_arrays_core",
    "update_link_node_flow",
]

Array = jax.Array
_FREE_FLOW_TRAVEL_TIME_KEY = "free_flow_travel_time_cost"


@dataclass(slots=True)
class BaselineFlowUpdateResult:
    """Container for updated flow state after one baseline allocation step."""

    link_state: LinkState
    node_state: NodeState


def update_link_node_flow(
    link_state: LinkState,
    node_state: NodeState,
    *,
    validate: bool = False,
) -> BaselineFlowUpdateResult:
    """Apply a simplified node-turn allocation and link queue update.

    The baseline model treats `node_state.turn_demand` as the desired movement
    volume for the current tick, then allocates feasible `turn_flow` while
    respecting upstream effective capacity, downstream receiving supply, and
    optional turn metadata (`turn_base_priority`, `turn_is_forbidden`).
    """

    if validate:
        _validate_turn_index_ranges(node_state, link_state.link_count)

    arrays = compute_baseline_flow_arrays(link_state=link_state, node_state=node_state)
    next_link_metadata = dict(link_state.metadata)
    next_link_metadata[_FREE_FLOW_TRAVEL_TIME_KEY] = arrays["base_travel_time_cost"]

    next_link_state = LinkState(
        queue_vehicles=arrays["queue_vehicles_next"],
        inflow_vehicles=arrays["inflow_vehicles_next"],
        outflow_vehicles=arrays["outflow_vehicles_next"],
        travel_time_cost=arrays["travel_time_cost_next"],
        capacity_veh_per_tick=link_state.capacity_veh_per_tick,
        incident_capacity_multiplier=link_state.incident_capacity_multiplier,
        capacity_violation_flags=arrays["capacity_violation_flags_next"],
        metadata=next_link_metadata,
    )
    next_node_state = NodeState(
        turn_from_link_index=node_state.turn_from_link_index,
        turn_to_link_index=node_state.turn_to_link_index,
        turn_demand=arrays["turn_demand_next"],
        turn_supply=arrays["turn_supply_next"],
        turn_flow=arrays["turn_flow_next"],
        signal_phase_index=node_state.signal_phase_index,
        signal_phase_timer=arrays["signal_phase_timer_next"],
        metadata=dict(node_state.metadata),
    )

    if validate:
        link_issues = validate_link_state(next_link_state)
        node_issues = validate_node_state(next_node_state)
        if link_issues or node_issues:
            raise ValueError(
                "invalid flow update result: "
                + "; ".join((*link_issues, *node_issues))
            )

    return BaselineFlowUpdateResult(link_state=next_link_state, node_state=next_node_state)


def compute_baseline_flow_arrays(
    *,
    link_state: LinkState,
    node_state: NodeState,
) -> dict[str, Array]:
    """Compute baseline node/link flow arrays (numeric core, JAX-portable)."""

    if link_state.link_count == 0 and node_state.turn_count > 0:
        raise ValueError("NodeState turns require non-empty LinkState")

    turn_demand = jnp.maximum(jnp.asarray(node_state.turn_demand, dtype=jnp.float32), 0.0)
    turn_count = int(turn_demand.shape[0])
    turn_priority = _read_turn_metadata(
        node_state.metadata,
        "turn_base_priority",
        turn_count,
        dtype=jnp.float32,
        default=1.0,
    )
    turn_is_forbidden = _read_turn_metadata(
        node_state.metadata,
        "turn_is_forbidden",
        turn_count,
        dtype=jnp.bool_,
        default=False,
    )
    base_travel_time_cost = _read_link_base_travel_time(link_state)
    arrays = compute_baseline_flow_arrays_core(
        queue_vehicles=link_state.queue_vehicles,
        effective_capacity_vehicles=link_state.effective_capacity_vehicles,
        turn_from_link_index=node_state.turn_from_link_index,
        turn_to_link_index=node_state.turn_to_link_index,
        turn_demand=turn_demand,
        signal_phase_timer=node_state.signal_phase_timer,
        base_travel_time_cost=base_travel_time_cost,
        turn_priority=turn_priority,
        turn_is_forbidden=turn_is_forbidden,
    )
    arrays["base_travel_time_cost"] = base_travel_time_cost
    return arrays


def compute_baseline_flow_arrays_core(
    *,
    queue_vehicles: Array,
    effective_capacity_vehicles: Array,
    turn_from_link_index: Array,
    turn_to_link_index: Array,
    turn_demand: Array,
    signal_phase_timer: Array,
    base_travel_time_cost: Array,
    turn_priority: Array | None = None,
    turn_is_forbidden: Array | None = None,
) -> dict[str, Array]:
    """Array-only baseline flow update core (JIT-friendly entry point)."""

    queue_now = jnp.maximum(jnp.asarray(queue_vehicles, dtype=jnp.float32), 0.0)
    effective_capacity = jnp.maximum(jnp.asarray(effective_capacity_vehicles, dtype=jnp.float32), 0.0)
    from_idx = jnp.asarray(turn_from_link_index, dtype=jnp.int32)
    to_idx = jnp.asarray(turn_to_link_index, dtype=jnp.int32)
    turn_demand = jnp.maximum(jnp.asarray(turn_demand, dtype=jnp.float32), 0.0)
    link_count = int(queue_now.shape[0])
    turn_count = int(turn_demand.shape[0])

    zeros_link = jnp.zeros((link_count,), dtype=jnp.float32)
    zeros_turn = jnp.zeros((turn_count,), dtype=jnp.float32)

    if link_count == 0:
        return {
            "turn_demand_next": turn_demand,
            "turn_supply_next": zeros_turn,
            "turn_flow_next": zeros_turn,
            "inflow_vehicles_next": zeros_link,
            "outflow_vehicles_next": zeros_link,
            "queue_vehicles_next": zeros_link,
            "travel_time_cost_next": _update_travel_time_cost(base_travel_time_cost, zeros_link, zeros_link),
            "capacity_violation_flags_next": jnp.zeros((0,), dtype=jnp.bool_),
            "signal_phase_timer_next": jnp.asarray(signal_phase_timer, dtype=jnp.int32) + 1,
        }
    if turn_count == 0:
        return {
            "turn_demand_next": turn_demand,
            "turn_supply_next": zeros_turn,
            "turn_flow_next": zeros_turn,
            "inflow_vehicles_next": zeros_link,
            "outflow_vehicles_next": zeros_link,
            "queue_vehicles_next": queue_now,
            "travel_time_cost_next": _update_travel_time_cost(base_travel_time_cost, queue_now, effective_capacity),
            "capacity_violation_flags_next": jnp.zeros((link_count,), dtype=jnp.bool_),
            "signal_phase_timer_next": jnp.asarray(signal_phase_timer, dtype=jnp.int32) + 1,
        }

    if turn_priority is None:
        turn_priority = jnp.ones((turn_count,), dtype=jnp.float32)
    else:
        turn_priority = jnp.asarray(turn_priority, dtype=jnp.float32)
    if turn_is_forbidden is None:
        turn_is_forbidden = jnp.zeros((turn_count,), dtype=jnp.bool_)
    else:
        turn_is_forbidden = jnp.asarray(turn_is_forbidden, dtype=jnp.bool_)

    priority_weight = jnp.where(turn_is_forbidden, 0.0, jnp.maximum(turn_priority, 0.0))
    weighted_demand = jnp.where(turn_demand > 0, turn_demand * priority_weight, 0.0)

    from_available_link = jnp.minimum(queue_now, effective_capacity)
    receiving_supply_link = jnp.maximum(effective_capacity - queue_now, 0.0)

    weighted_by_from = _segment_sum(weighted_demand, from_idx, link_count)
    weighted_by_to = _segment_sum(weighted_demand, to_idx, link_count)
    from_den = weighted_by_from[from_idx]
    to_den = weighted_by_to[to_idx]
    from_share = jnp.where(from_den > 0, weighted_demand / from_den, 0.0)
    to_share = jnp.where(to_den > 0, weighted_demand / to_den, 0.0)

    turn_supply = jnp.minimum(
        from_available_link[from_idx] * from_share,
        receiving_supply_link[to_idx] * to_share,
    )
    turn_flow = jnp.where(turn_is_forbidden, 0.0, jnp.minimum(turn_demand, turn_supply))

    outflow = _segment_sum(turn_flow, from_idx, link_count)
    inflow = _segment_sum(turn_flow, to_idx, link_count)
    queue_next = jnp.maximum(0.0, queue_now - outflow + inflow)

    return {
        "turn_demand_next": turn_demand,
        "turn_supply_next": jnp.maximum(turn_supply, 0.0),
        "turn_flow_next": jnp.maximum(turn_flow, 0.0),
        "inflow_vehicles_next": inflow,
        "outflow_vehicles_next": outflow,
        "queue_vehicles_next": queue_next,
        "travel_time_cost_next": _update_travel_time_cost(base_travel_time_cost, queue_next, effective_capacity),
        "capacity_violation_flags_next": outflow > (effective_capacity + 1e-6),
        "signal_phase_timer_next": jnp.asarray(signal_phase_timer, dtype=jnp.int32) + 1,
    }


def _read_turn_metadata(
    metadata: dict[str, Any],
    key: str,
    size: int,
    *,
    dtype: Any,
    default: float | bool,
) -> Array:
    raw = metadata.get(key)
    if raw is None:
        return jnp.full((size,), default, dtype=dtype)
    arr = jnp.asarray(raw, dtype=dtype)
    if arr.ndim == 0:
        return jnp.full((size,), arr, dtype=dtype)
    if arr.ndim != 1 or int(arr.shape[0]) != size:
        raise ValueError(f"{key} must be scalar or shape ({size},)")
    return arr


def _read_link_base_travel_time(link_state: LinkState) -> Array:
    raw = link_state.metadata.get(_FREE_FLOW_TRAVEL_TIME_KEY)
    if raw is None:
        return jnp.asarray(link_state.travel_time_cost, dtype=jnp.float32)
    arr = jnp.asarray(raw, dtype=jnp.float32)
    if arr.ndim == 0:
        return jnp.full((link_state.link_count,), arr, dtype=jnp.float32)
    if arr.ndim != 1 or int(arr.shape[0]) != link_state.link_count:
        raise ValueError(
            f"{_FREE_FLOW_TRAVEL_TIME_KEY} must be scalar or shape ({link_state.link_count},)"
        )
    return arr


def _validate_turn_index_ranges(node_state: NodeState, link_count: int) -> None:
    link_count = int(link_count)
    if link_count == 0 and node_state.turn_count > 0:
        raise ValueError("NodeState turns require non-empty LinkState")
    if node_state.turn_count == 0:
        return
    from_idx = jnp.asarray(node_state.turn_from_link_index)
    to_idx = jnp.asarray(node_state.turn_to_link_index)
    if bool(jnp.any(from_idx < 0)) or bool(jnp.any(from_idx >= link_count)):
        raise ValueError("turn_from_link_index contains out-of-range link indices")
    if bool(jnp.any(to_idx < 0)) or bool(jnp.any(to_idx >= link_count)):
        raise ValueError("turn_to_link_index contains out-of-range link indices")


def _segment_sum(values: Array, indices: Array, num_segments: int) -> Array:
    return jax.ops.segment_sum(
        jnp.asarray(values, dtype=jnp.float32),
        jnp.asarray(indices, dtype=jnp.int32),
        num_segments=int(num_segments),
    )


def _update_travel_time_cost(
    base_cost: Array,
    queue_vehicles: Array,
    effective_capacity: Array,
) -> Array:
    base = jnp.maximum(jnp.asarray(base_cost, dtype=jnp.float32), 1e-3)
    queue = jnp.maximum(jnp.asarray(queue_vehicles, dtype=jnp.float32), 0.0)
    cap = jnp.maximum(jnp.asarray(effective_capacity, dtype=jnp.float32), 1e-3)
    congestion_ratio = queue / (cap + 1e-3)
    return base * (1.0 + congestion_ratio)
