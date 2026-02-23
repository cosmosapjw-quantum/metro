"""Link/node flow state containers for the baseline traffic engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import jax
import jax.numpy as jnp

__all__ = [
    "LinkState",
    "NodeState",
    "create_link_state",
    "create_node_state",
    "validate_link_state",
    "validate_node_state",
]

Array = jax.Array


@dataclass(slots=True)
class LinkState:
    """Per-link dynamic flow state for a simulation tick."""

    queue_vehicles: Array
    inflow_vehicles: Array
    outflow_vehicles: Array
    travel_time_cost: Array
    capacity_veh_per_tick: Array
    incident_capacity_multiplier: Array
    capacity_violation_flags: Array | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.queue_vehicles = jnp.asarray(self.queue_vehicles, dtype=jnp.float32)
        self.inflow_vehicles = jnp.asarray(self.inflow_vehicles, dtype=jnp.float32)
        self.outflow_vehicles = jnp.asarray(self.outflow_vehicles, dtype=jnp.float32)
        self.travel_time_cost = jnp.asarray(self.travel_time_cost, dtype=jnp.float32)
        self.capacity_veh_per_tick = jnp.asarray(self.capacity_veh_per_tick, dtype=jnp.float32)
        self.incident_capacity_multiplier = jnp.asarray(
            self.incident_capacity_multiplier,
            dtype=jnp.float32,
        )
        if self.capacity_violation_flags is None:
            self.capacity_violation_flags = jnp.zeros_like(self.queue_vehicles, dtype=jnp.bool_)
        else:
            self.capacity_violation_flags = jnp.asarray(
                self.capacity_violation_flags,
                dtype=jnp.bool_,
            )
        if not isinstance(self.metadata, dict):
            self.metadata = dict(self.metadata)

        _validate_same_shape(
            self.queue_vehicles,
            self.inflow_vehicles,
            self.outflow_vehicles,
            self.travel_time_cost,
            self.capacity_veh_per_tick,
            self.incident_capacity_multiplier,
            self.capacity_violation_flags,
        )
        if self.queue_vehicles.ndim != 1:
            raise ValueError("LinkState arrays must be 1-D")
        if bool(jnp.any(self.queue_vehicles < 0)):
            raise ValueError("queue_vehicles must be >= 0")
        if bool(jnp.any(self.inflow_vehicles < 0)):
            raise ValueError("inflow_vehicles must be >= 0")
        if bool(jnp.any(self.outflow_vehicles < 0)):
            raise ValueError("outflow_vehicles must be >= 0")
        if bool(jnp.any(self.travel_time_cost <= 0)):
            raise ValueError("travel_time_cost must be > 0")
        if bool(jnp.any(self.capacity_veh_per_tick < 0)):
            raise ValueError("capacity_veh_per_tick must be >= 0")
        if bool(jnp.any(self.incident_capacity_multiplier < 0)) or bool(
            jnp.any(self.incident_capacity_multiplier > 1)
        ):
            raise ValueError("incident_capacity_multiplier must be in [0, 1]")

    @property
    def link_count(self) -> int:
        return int(self.queue_vehicles.shape[0])

    @property
    def effective_capacity_vehicles(self) -> Array:
        return self.capacity_veh_per_tick * self.incident_capacity_multiplier

    @property
    def capacity_violation_count(self) -> int:
        return int(jnp.sum(self.capacity_violation_flags))


@dataclass(slots=True)
class NodeState:
    """Per-turn / per-node dynamic state for junction allocation updates."""

    turn_from_link_index: Array
    turn_to_link_index: Array
    turn_demand: Array
    turn_supply: Array
    turn_flow: Array
    signal_phase_index: Array
    signal_phase_timer: Array
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.turn_from_link_index = jnp.asarray(self.turn_from_link_index, dtype=jnp.int32)
        self.turn_to_link_index = jnp.asarray(self.turn_to_link_index, dtype=jnp.int32)
        self.turn_demand = jnp.asarray(self.turn_demand, dtype=jnp.float32)
        self.turn_supply = jnp.asarray(self.turn_supply, dtype=jnp.float32)
        self.turn_flow = jnp.asarray(self.turn_flow, dtype=jnp.float32)
        self.signal_phase_index = jnp.asarray(self.signal_phase_index, dtype=jnp.int32)
        self.signal_phase_timer = jnp.asarray(self.signal_phase_timer, dtype=jnp.int32)
        if not isinstance(self.metadata, dict):
            self.metadata = dict(self.metadata)

        _validate_same_shape(
            self.turn_from_link_index,
            self.turn_to_link_index,
            self.turn_demand,
            self.turn_supply,
            self.turn_flow,
        )
        if self.turn_demand.ndim != 1:
            raise ValueError("NodeState turn arrays must be 1-D")
        if self.signal_phase_index.ndim != 1 or self.signal_phase_timer.ndim != 1:
            raise ValueError("NodeState signal phase arrays must be 1-D")
        if bool(jnp.any(self.turn_demand < 0)):
            raise ValueError("turn_demand must be >= 0")
        if bool(jnp.any(self.turn_supply < 0)):
            raise ValueError("turn_supply must be >= 0")
        if bool(jnp.any(self.turn_flow < 0)):
            raise ValueError("turn_flow must be >= 0")
        if bool(jnp.any(self.signal_phase_timer < 0)):
            raise ValueError("signal_phase_timer must be >= 0")

    @property
    def turn_count(self) -> int:
        return int(self.turn_demand.shape[0])

    @property
    def node_count(self) -> int:
        return int(self.signal_phase_index.shape[0])

    @property
    def signal_phase_state(self) -> dict[str, Array]:
        """Convenience view matching the data-model's simplified signal state concept."""

        return {
            "phase_index": self.signal_phase_index,
            "phase_timer": self.signal_phase_timer,
        }


def create_link_state(
    link_count: int,
    *,
    travel_time_cost: float | Array = 1.0,
    capacity_veh_per_tick: float | Array = 1.0,
) -> LinkState:
    """Create a zeroed `LinkState` for `link_count` links."""

    link_count = int(link_count)
    if link_count < 0:
        raise ValueError("link_count must be >= 0")
    zeros = jnp.zeros((link_count,), dtype=jnp.float32)
    ones = jnp.ones((link_count,), dtype=jnp.float32)
    travel = _broadcast_1d(travel_time_cost, link_count, dtype=jnp.float32)
    capacity = _broadcast_1d(capacity_veh_per_tick, link_count, dtype=jnp.float32)
    return LinkState(
        queue_vehicles=zeros,
        inflow_vehicles=zeros,
        outflow_vehicles=zeros,
        travel_time_cost=travel,
        capacity_veh_per_tick=capacity,
        incident_capacity_multiplier=ones,
        capacity_violation_flags=jnp.zeros((link_count,), dtype=jnp.bool_),
    )


def create_node_state(
    turn_from_link_index: Array | list[int] | tuple[int, ...],
    turn_to_link_index: Array | list[int] | tuple[int, ...],
    *,
    node_count: int,
) -> NodeState:
    """Create a zeroed `NodeState` for a fixed turn list and node count."""

    node_count = int(node_count)
    if node_count < 0:
        raise ValueError("node_count must be >= 0")
    from_idx = jnp.asarray(turn_from_link_index, dtype=jnp.int32)
    to_idx = jnp.asarray(turn_to_link_index, dtype=jnp.int32)
    if from_idx.shape != to_idx.shape:
        raise ValueError("turn_from_link_index and turn_to_link_index must have same shape")
    if from_idx.ndim != 1:
        raise ValueError("turn link index arrays must be 1-D")
    turn_count = int(from_idx.shape[0])
    zeros_turn = jnp.zeros((turn_count,), dtype=jnp.float32)
    return NodeState(
        turn_from_link_index=from_idx,
        turn_to_link_index=to_idx,
        turn_demand=zeros_turn,
        turn_supply=zeros_turn,
        turn_flow=zeros_turn,
        signal_phase_index=jnp.zeros((node_count,), dtype=jnp.int32),
        signal_phase_timer=jnp.zeros((node_count,), dtype=jnp.int32),
    )


def validate_link_state(link_state: LinkState) -> tuple[str, ...]:
    """Return validation issues (empty tuple if valid) for `LinkState`."""

    issues: list[str] = []
    if bool(jnp.any(link_state.queue_vehicles < 0)):
        issues.append("queue_vehicles contains negative values")
    if bool(jnp.any(link_state.outflow_vehicles < 0)):
        issues.append("outflow_vehicles contains negative values")
    if bool(jnp.any(link_state.inflow_vehicles < 0)):
        issues.append("inflow_vehicles contains negative values")
    if bool(jnp.any(link_state.travel_time_cost <= 0)):
        issues.append("travel_time_cost contains non-positive values")
    if bool(jnp.any(link_state.incident_capacity_multiplier < 0)) or bool(
        jnp.any(link_state.incident_capacity_multiplier > 1)
    ):
        issues.append("incident_capacity_multiplier contains values outside [0, 1]")
    observed_capacity_exceed = link_state.outflow_vehicles > (
        link_state.effective_capacity_vehicles + 1e-6
    )
    expected_flags = int(jnp.sum(observed_capacity_exceed))
    actual_flags = int(jnp.sum(link_state.capacity_violation_flags))
    if actual_flags < expected_flags:
        issues.append("capacity_violation_flags under-report outflow > effective capacity")
    return tuple(issues)


def validate_node_state(node_state: NodeState, *, tolerance: float = 1e-6) -> tuple[str, ...]:
    """Return validation issues (empty tuple if valid) for `NodeState`."""

    issues: list[str] = []
    if bool(jnp.any(node_state.turn_demand < 0)):
        issues.append("turn_demand contains negative values")
    if bool(jnp.any(node_state.turn_supply < 0)):
        issues.append("turn_supply contains negative values")
    if bool(jnp.any(node_state.turn_flow < 0)):
        issues.append("turn_flow contains negative values")
    if bool(jnp.any(node_state.turn_flow - node_state.turn_demand > float(tolerance))):
        issues.append("turn_flow exceeds turn_demand")
    if bool(jnp.any(node_state.turn_flow - node_state.turn_supply > float(tolerance))):
        issues.append("turn_flow exceeds turn_supply")
    if bool(jnp.any(node_state.signal_phase_timer < 0)):
        issues.append("signal_phase_timer contains negative values")
    return tuple(issues)


def _validate_same_shape(*arrays: Array) -> None:
    shapes = {tuple(jnp.asarray(array).shape) for array in arrays}
    if len(shapes) != 1:
        raise ValueError(f"all arrays must have the same shape, got {sorted(shapes)}")


def _broadcast_1d(value: float | Array, size: int, *, dtype: Any) -> Array:
    arr = jnp.asarray(value, dtype=dtype)
    if arr.ndim == 0:
        return jnp.full((size,), arr, dtype=dtype)
    if arr.ndim == 1 and int(arr.shape[0]) == size:
        return arr
    raise ValueError(f"value must be scalar or shape ({size},), got {tuple(arr.shape)}")
