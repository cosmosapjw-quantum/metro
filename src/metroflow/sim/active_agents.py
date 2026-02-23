"""Active-agent packed pool primitives."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

import jax
import jax.numpy as jnp

__all__ = [
    "ActiveAgentSlot",
    "ActiveAgentPool",
    "create_active_agent_pool",
    "allocate_active_agent_slot",
    "release_active_agent_slot",
    "read_active_agent_slot",
    "validate_active_agent_pool",
]

Array = jax.Array


@dataclass(slots=True)
class ActiveAgentSlot:
    """Logical slot payload matching the ActiveAgentSlot data-model fields."""

    slot_id: int = -1
    alive: bool = False
    citizen_id: int = -1
    trip_id: int = -1
    current_link_id: int = -1
    progress_01: float = 0.0
    remaining_route_ptr: int = 0
    dest_node_id: int = -1
    behavior_profile_id: int = -1
    reroute_cooldown_ticks: int = 0
    plugin_memory: dict[int, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.slot_id = int(self.slot_id)
        self.alive = bool(self.alive)
        self.citizen_id = int(self.citizen_id)
        self.trip_id = int(self.trip_id)
        self.current_link_id = int(self.current_link_id)
        self.progress_01 = float(self.progress_01)
        self.remaining_route_ptr = int(self.remaining_route_ptr)
        self.dest_node_id = int(self.dest_node_id)
        self.behavior_profile_id = int(self.behavior_profile_id)
        self.reroute_cooldown_ticks = int(self.reroute_cooldown_ticks)
        if not 0.0 <= self.progress_01 <= 1.0:
            raise ValueError("progress_01 must be in [0, 1]")
        if self.reroute_cooldown_ticks < 0:
            raise ValueError("reroute_cooldown_ticks must be >= 0")
        if not isinstance(self.plugin_memory, dict):
            self.plugin_memory = dict(self.plugin_memory)

    @classmethod
    def spawn(
        cls,
        *,
        citizen_id: int,
        trip_id: int,
        current_link_id: int,
        dest_node_id: int,
        behavior_profile_id: int,
        progress_01: float = 0.0,
        remaining_route_ptr: int = 0,
        reroute_cooldown_ticks: int = 0,
    ) -> "ActiveAgentSlot":
        """Convenience constructor for an alive slot payload before allocation."""

        return cls(
            alive=True,
            citizen_id=citizen_id,
            trip_id=trip_id,
            current_link_id=current_link_id,
            progress_01=progress_01,
            remaining_route_ptr=remaining_route_ptr,
            dest_node_id=dest_node_id,
            behavior_profile_id=behavior_profile_id,
            reroute_cooldown_ticks=reroute_cooldown_ticks,
        )


@dataclass(slots=True)
class ActiveAgentPool:
    """Packed active-agent state plus free-slot stack bookkeeping."""

    capacity: int
    free_slot_stack: Array
    free_slot_count: int
    alive_mask: Array
    alive_count: int
    citizen_id: Array
    trip_id: Array
    current_link_id: Array
    progress_01: Array
    remaining_route_ptr: Array
    dest_node_id: Array
    behavior_profile_id: Array
    reroute_cooldown_ticks: Array
    plugin_memory: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.capacity = int(self.capacity)
        self.free_slot_count = int(self.free_slot_count)
        self.alive_count = int(self.alive_count)

        self.free_slot_stack = jnp.asarray(self.free_slot_stack, dtype=jnp.int32)
        self.alive_mask = jnp.asarray(self.alive_mask, dtype=jnp.bool_)
        self.citizen_id = jnp.asarray(self.citizen_id, dtype=jnp.int32)
        self.trip_id = jnp.asarray(self.trip_id, dtype=jnp.int32)
        self.current_link_id = jnp.asarray(self.current_link_id, dtype=jnp.int32)
        self.progress_01 = jnp.asarray(self.progress_01, dtype=jnp.float32)
        self.remaining_route_ptr = jnp.asarray(self.remaining_route_ptr, dtype=jnp.int32)
        self.dest_node_id = jnp.asarray(self.dest_node_id, dtype=jnp.int32)
        self.behavior_profile_id = jnp.asarray(self.behavior_profile_id, dtype=jnp.int32)
        self.reroute_cooldown_ticks = jnp.asarray(self.reroute_cooldown_ticks, dtype=jnp.int32)

        if self.capacity <= 0:
            raise ValueError("capacity must be > 0")
        _validate_pool_array_shapes(self)
        if not (0 <= self.free_slot_count <= self.capacity):
            raise ValueError("free_slot_count out of range")
        if not (0 <= self.alive_count <= self.capacity):
            raise ValueError("alive_count out of range")
        if self.free_slot_count + self.alive_count != self.capacity:
            raise ValueError("free_slot_count + alive_count must equal capacity")
        if not isinstance(self.plugin_memory, dict):
            self.plugin_memory = dict(self.plugin_memory)

    @property
    def available_slots(self) -> int:
        return self.free_slot_count


def create_active_agent_pool(capacity: int) -> ActiveAgentPool:
    """Create an empty active-agent packed pool with all slots free."""

    capacity = int(capacity)
    if capacity <= 0:
        raise ValueError("capacity must be > 0")

    free_slot_stack = jnp.arange(capacity - 1, -1, -1, dtype=jnp.int32)
    zeros_i = jnp.zeros((capacity,), dtype=jnp.int32)
    return ActiveAgentPool(
        capacity=capacity,
        free_slot_stack=free_slot_stack,
        free_slot_count=capacity,
        alive_mask=jnp.zeros((capacity,), dtype=jnp.bool_),
        alive_count=0,
        citizen_id=zeros_i - 1,
        trip_id=zeros_i - 1,
        current_link_id=zeros_i - 1,
        progress_01=jnp.zeros((capacity,), dtype=jnp.float32),
        remaining_route_ptr=zeros_i,
        dest_node_id=zeros_i - 1,
        behavior_profile_id=zeros_i - 1,
        reroute_cooldown_ticks=zeros_i,
    )


def allocate_active_agent_slot(
    pool: ActiveAgentPool,
    slot_payload: ActiveAgentSlot,
) -> tuple[ActiveAgentPool, int]:
    """Allocate one free slot and write packed slot fields.

    Returns the updated pool and the allocated `slot_id`. The free-slot stack is
    treated as LIFO so recently released slots are reused first.
    """

    if pool.free_slot_count <= 0:
        raise RuntimeError("active-agent pool is full")
    if not slot_payload.alive:
        raise ValueError("slot_payload.alive must be True for allocation")

    top_index = pool.free_slot_count - 1
    slot_id = int(pool.free_slot_stack[top_index])
    _validate_slot_index(slot_id, pool.capacity)

    next_pool = replace(
        pool,
        free_slot_count=pool.free_slot_count - 1,
        alive_count=pool.alive_count + 1,
        alive_mask=pool.alive_mask.at[slot_id].set(True),
        citizen_id=pool.citizen_id.at[slot_id].set(slot_payload.citizen_id),
        trip_id=pool.trip_id.at[slot_id].set(slot_payload.trip_id),
        current_link_id=pool.current_link_id.at[slot_id].set(
            slot_payload.current_link_id
        ),
        progress_01=pool.progress_01.at[slot_id].set(slot_payload.progress_01),
        remaining_route_ptr=pool.remaining_route_ptr.at[slot_id].set(
            slot_payload.remaining_route_ptr
        ),
        dest_node_id=pool.dest_node_id.at[slot_id].set(slot_payload.dest_node_id),
        behavior_profile_id=pool.behavior_profile_id.at[slot_id].set(
            slot_payload.behavior_profile_id
        ),
        reroute_cooldown_ticks=pool.reroute_cooldown_ticks.at[slot_id].set(
            slot_payload.reroute_cooldown_ticks
        ),
    )
    return next_pool, slot_id


def release_active_agent_slot(pool: ActiveAgentPool, slot_id: int) -> ActiveAgentPool:
    """Release an alive slot back to the free-slot stack (LIFO reuse)."""

    slot_id = int(slot_id)
    _validate_slot_index(slot_id, pool.capacity)
    if not bool(pool.alive_mask[slot_id]):
        raise ValueError(f"slot {slot_id} is not alive")
    if pool.free_slot_count >= pool.capacity:
        raise RuntimeError("free_slot_stack overflow")

    next_free_stack = pool.free_slot_stack.at[pool.free_slot_count].set(slot_id)
    return replace(
        pool,
        free_slot_stack=next_free_stack,
        free_slot_count=pool.free_slot_count + 1,
        alive_count=pool.alive_count - 1,
        alive_mask=pool.alive_mask.at[slot_id].set(False),
        citizen_id=pool.citizen_id.at[slot_id].set(-1),
        trip_id=pool.trip_id.at[slot_id].set(-1),
        current_link_id=pool.current_link_id.at[slot_id].set(-1),
        progress_01=pool.progress_01.at[slot_id].set(0.0),
        remaining_route_ptr=pool.remaining_route_ptr.at[slot_id].set(0),
        dest_node_id=pool.dest_node_id.at[slot_id].set(-1),
        behavior_profile_id=pool.behavior_profile_id.at[slot_id].set(-1),
        reroute_cooldown_ticks=pool.reroute_cooldown_ticks.at[slot_id].set(0),
    )


def read_active_agent_slot(pool: ActiveAgentPool, slot_id: int) -> ActiveAgentSlot:
    """Read one logical slot view from packed arrays."""

    slot_id = int(slot_id)
    _validate_slot_index(slot_id, pool.capacity)
    raw_plugin_memory = pool.plugin_memory.get(slot_id, {})
    slot_plugin_memory = (
        dict(raw_plugin_memory) if isinstance(raw_plugin_memory, dict) else {}
    )

    return ActiveAgentSlot(
        slot_id=slot_id,
        alive=bool(pool.alive_mask[slot_id]),
        citizen_id=int(pool.citizen_id[slot_id]),
        trip_id=int(pool.trip_id[slot_id]),
        current_link_id=int(pool.current_link_id[slot_id]),
        progress_01=float(pool.progress_01[slot_id]),
        remaining_route_ptr=int(pool.remaining_route_ptr[slot_id]),
        dest_node_id=int(pool.dest_node_id[slot_id]),
        behavior_profile_id=int(pool.behavior_profile_id[slot_id]),
        reroute_cooldown_ticks=int(pool.reroute_cooldown_ticks[slot_id]),
        plugin_memory=slot_plugin_memory,
    )


def validate_active_agent_pool(pool: ActiveAgentPool) -> tuple[str, ...]:
    """Return consistency violations for the packed pool (empty tuple == valid)."""

    issues: list[str] = []

    alive_count_from_mask = int(jnp.sum(pool.alive_mask).item())
    if pool.alive_count != alive_count_from_mask:
        issues.append("alive_count != sum(alive_mask)")

    if pool.free_slot_count + pool.alive_count != pool.capacity:
        issues.append("free_slot_count + alive_count != capacity")

    free_ids = [
        int(x)
        for x in jnp.asarray(pool.free_slot_stack[: pool.free_slot_count]).tolist()
    ]
    if len(set(free_ids)) != len(free_ids):
        issues.append("duplicate slot ids in free_slot_stack")

    if any(slot_id < 0 or slot_id >= pool.capacity for slot_id in free_ids):
        issues.append("free_slot_stack contains out-of-range slot ids")

    alive_ids = {
        int(i)
        for i, is_alive in enumerate(jnp.asarray(pool.alive_mask).tolist())
        if bool(is_alive)
    }
    if alive_ids.intersection(free_ids):
        issues.append("slot ids appear in both alive set and free_slot_stack")

    progress = jnp.asarray(pool.progress_01)
    if bool(jnp.any(progress < 0.0)) or bool(jnp.any(progress > 1.0)):
        issues.append("progress_01 contains values outside [0, 1]")

    cooldown = jnp.asarray(pool.reroute_cooldown_ticks)
    if bool(jnp.any(cooldown < 0)):
        issues.append("reroute_cooldown_ticks contains negative values")

    return tuple(issues)


def _validate_pool_array_shapes(pool: ActiveAgentPool) -> None:
    expected = (pool.capacity,)
    arrays = (
        ("free_slot_stack", pool.free_slot_stack),
        ("alive_mask", pool.alive_mask),
        ("citizen_id", pool.citizen_id),
        ("trip_id", pool.trip_id),
        ("current_link_id", pool.current_link_id),
        ("progress_01", pool.progress_01),
        ("remaining_route_ptr", pool.remaining_route_ptr),
        ("dest_node_id", pool.dest_node_id),
        ("behavior_profile_id", pool.behavior_profile_id),
        ("reroute_cooldown_ticks", pool.reroute_cooldown_ticks),
    )
    for name, array in arrays:
        if tuple(array.shape) != expected:
            raise ValueError(f"{name} must have shape {expected}, got {tuple(array.shape)}")


def _validate_slot_index(slot_id: int, capacity: int) -> None:
    if slot_id < 0 or slot_id >= capacity:
        raise IndexError(f"slot_id {slot_id} out of range for capacity {capacity}")
