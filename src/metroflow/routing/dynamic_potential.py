"""Congestion-aware dynamic-potential baseline routing helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from heapq import heappop, heappush
from typing import Any

import jax
import jax.numpy as jnp

from metroflow.city.graph import RoadNetworkCSR
from metroflow.flow.state import LinkState

__all__ = [
    "DynamicPotentialState",
    "BaselineNextLinkScores",
    "compute_dynamic_potential_state",
    "compute_next_link_action_costs_core",
    "score_legal_next_links",
    "build_greedy_route_candidate",
]

Array = jax.Array
_INF_COST = 1e12
_TURN_SUCCESSOR_CACHE: dict[
    tuple[int, int, int, int, int],
    tuple[dict[int, tuple[int, ...]], dict[int, tuple[int, ...]]],
] = {}


@dataclass(slots=True)
class DynamicPotentialState:
    """Destination-anchored node cost-to-go field for baseline routing."""

    destination_node_id: int
    destination_node_index: int
    node_cost_to_go: Array
    link_travel_time_cost: Array
    blocked_link_mask: Array
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.destination_node_id = int(self.destination_node_id)
        self.destination_node_index = int(self.destination_node_index)
        self.node_cost_to_go = jnp.asarray(self.node_cost_to_go, dtype=jnp.float32)
        self.link_travel_time_cost = jnp.asarray(self.link_travel_time_cost, dtype=jnp.float32)
        self.blocked_link_mask = jnp.asarray(self.blocked_link_mask, dtype=jnp.bool_)
        if not isinstance(self.metadata, dict):
            self.metadata = dict(self.metadata)
        if self.node_cost_to_go.ndim != 1:
            raise ValueError("node_cost_to_go must be 1-D")
        if self.link_travel_time_cost.ndim != 1 or self.blocked_link_mask.ndim != 1:
            raise ValueError("link arrays must be 1-D")
        if self.link_travel_time_cost.shape != self.blocked_link_mask.shape:
            raise ValueError("link_travel_time_cost and blocked_link_mask must have same shape")
        if self.destination_node_index < 0 or self.destination_node_index >= int(self.node_cost_to_go.shape[0]):
            raise ValueError("destination_node_index out of range")


@dataclass(slots=True)
class BaselineNextLinkScores:
    """Sorted legal next-link action costs for a node decision context."""

    current_node_id: int
    destination_node_id: int
    incoming_link_id: int | None
    candidate_link_ids: tuple[int, ...]
    action_costs: tuple[float, ...]
    best_link_id: int | None
    best_cost: float | None


def compute_dynamic_potential_state(
    network: RoadNetworkCSR,
    *,
    destination_node_id: int,
    link_state: LinkState | None = None,
    link_travel_time_cost: Array | None = None,
    cache: dict[Any, DynamicPotentialState] | None = None,
    cache_key: Any | None = None,
) -> DynamicPotentialState:
    """Compute a congestion-aware shortest-path cost-to-go field to destination.

    When `link_state` is provided, current `travel_time_cost` drives the
    baseline potential and links with zero effective capacity are treated as
    blocked if the static link is blockable.
    """

    if not isinstance(network, RoadNetworkCSR):
        raise TypeError("network must be a RoadNetworkCSR")
    effective_cache_key = None
    if cache is not None:
        effective_cache_key = (
            cache_key
            if cache_key is not None
            else (
                "dynamic_potential",
                id(network),
                int(destination_node_id),
                id(link_state) if link_state is not None else None,
                id(link_travel_time_cost) if link_travel_time_cost is not None else None,
            )
        )
        cached = cache.get(effective_cache_key)
        if cached is not None:
            return cached
    if network.link_count == 0:
        dest_idx = network.node_id_to_index[int(destination_node_id)]
        node_cost = jnp.full((network.node_count,), _INF_COST, dtype=jnp.float32).at[dest_idx].set(0.0)
        state = DynamicPotentialState(
            destination_node_id=int(destination_node_id),
            destination_node_index=dest_idx,
            node_cost_to_go=node_cost,
            link_travel_time_cost=jnp.zeros((0,), dtype=jnp.float32),
            blocked_link_mask=jnp.zeros((0,), dtype=jnp.bool_),
        )
        if cache is not None and effective_cache_key is not None:
            cache[effective_cache_key] = state
        return state

    dest_idx = network.node_id_to_index[int(destination_node_id)]
    costs = _resolve_link_costs(network, link_state=link_state, link_travel_time_cost=link_travel_time_cost)
    blocked = _resolve_blocked_link_mask(network, link_state=link_state, size=network.link_count)
    node_cost = _reverse_dijkstra_node_costs(network, costs=costs, blocked=blocked, destination_node_index=dest_idx)

    state = DynamicPotentialState(
        destination_node_id=int(destination_node_id),
        destination_node_index=dest_idx,
        node_cost_to_go=node_cost,
        link_travel_time_cost=costs,
        blocked_link_mask=blocked,
        metadata={
            "link_count": network.link_count,
            "node_count": network.node_count,
            "cache_key": effective_cache_key,
        },
    )
    if cache is not None and effective_cache_key is not None:
        cache[effective_cache_key] = state
    return state


def score_legal_next_links(
    network: RoadNetworkCSR,
    potential_state: DynamicPotentialState,
    *,
    current_node_id: int,
    incoming_link_id: int | None = None,
) -> BaselineNextLinkScores:
    """Score legal next links by `link_cost + potential(dst_node)` (lower is better)."""

    node_index = network.node_id_to_index[int(current_node_id)]
    outgoing_idx = _outgoing_link_indices_for_node(network, node_index)
    allowed_idx = _filter_legal_turn_successors(
        network,
        outgoing_idx=outgoing_idx,
        incoming_link_id=incoming_link_id,
    )

    candidate_indices = jnp.asarray(list(allowed_idx), dtype=jnp.int32)
    raw_costs = compute_next_link_action_costs_core(
        candidate_link_indices=candidate_indices,
        link_dst_node_index=network.link_dst_node_index,
        node_cost_to_go=potential_state.node_cost_to_go,
        link_travel_time_cost=potential_state.link_travel_time_cost,
        blocked_link_mask=potential_state.blocked_link_mask,
    )
    scored: list[tuple[float, int]] = []
    for i, link_index in enumerate(allowed_idx):
        total_cost = float(raw_costs[i]) if int(raw_costs.shape[0]) > 0 else _INF_COST
        if (not bool(jnp.isfinite(raw_costs[i]))) or total_cost >= _INF_COST * 0.5:
            continue
        scored.append((total_cost, int(network.links[link_index].link_id)))

    scored.sort(key=lambda x: (x[0], x[1]))
    candidate_link_ids = tuple(link_id for _cost, link_id in scored)
    action_costs = tuple(float(cost) for cost, _link_id in scored)
    best_link_id = candidate_link_ids[0] if candidate_link_ids else None
    best_cost = action_costs[0] if action_costs else None
    return BaselineNextLinkScores(
        current_node_id=int(current_node_id),
        destination_node_id=potential_state.destination_node_id,
        incoming_link_id=None if incoming_link_id is None else int(incoming_link_id),
        candidate_link_ids=candidate_link_ids,
        action_costs=action_costs,
        best_link_id=best_link_id,
        best_cost=best_cost,
    )


def build_greedy_route_candidate(
    network: RoadNetworkCSR,
    potential_state: DynamicPotentialState,
    *,
    origin_node_id: int,
    max_hops: int | None = None,
) -> tuple[int, ...]:
    """Build a deterministic greedy route candidate from dynamic potential scores."""

    destination_node_id = potential_state.destination_node_id
    if int(origin_node_id) == int(destination_node_id):
        return ()
    hop_limit = max(1, int(max_hops)) if max_hops is not None else max(1, network.link_count + 1)
    cur_node_id = int(origin_node_id)
    incoming_link_id: int | None = None
    visited_nodes = {cur_node_id}
    path: list[int] = []

    for _ in range(hop_limit):
        scores = score_legal_next_links(
            network,
            potential_state,
            current_node_id=cur_node_id,
            incoming_link_id=incoming_link_id,
        )
        if scores.best_link_id is None:
            break
        next_link = network.links[network.link_id_to_index[scores.best_link_id]]
        path.append(next_link.link_id)
        incoming_link_id = next_link.link_id
        cur_node_id = next_link.dst_node_id
        if cur_node_id == destination_node_id:
            return tuple(path)
        if cur_node_id in visited_nodes:
            break
        visited_nodes.add(cur_node_id)
    return ()


def compute_next_link_action_costs_core(
    *,
    candidate_link_indices: Array,
    link_dst_node_index: Array,
    node_cost_to_go: Array,
    link_travel_time_cost: Array,
    blocked_link_mask: Array,
) -> Array:
    """Array-only next-action scoring core for JAX-friendly routing extensions."""

    cand = jnp.asarray(candidate_link_indices, dtype=jnp.int32)
    if cand.ndim != 1:
        raise ValueError("candidate_link_indices must be 1-D")
    dst_idx = jnp.asarray(link_dst_node_index, dtype=jnp.int32)[cand]
    tail = jnp.asarray(node_cost_to_go, dtype=jnp.float32)[dst_idx]
    link_cost = jnp.asarray(link_travel_time_cost, dtype=jnp.float32)[cand]
    blocked = jnp.asarray(blocked_link_mask, dtype=jnp.bool_)[cand]
    total = link_cost + tail
    valid = (~blocked) & jnp.isfinite(tail) & (tail < (_INF_COST * 0.5))
    return jnp.where(valid, total, jnp.asarray(_INF_COST, dtype=jnp.float32))


def _resolve_link_costs(
    network: RoadNetworkCSR,
    *,
    link_state: LinkState | None,
    link_travel_time_cost: Array | None,
) -> Array:
    if link_state is not None:
        if link_state.link_count != network.link_count:
            raise ValueError("link_state.link_count must match network.link_count")
        return jnp.maximum(jnp.asarray(link_state.travel_time_cost, dtype=jnp.float32), 1e-6)
    if link_travel_time_cost is not None:
        arr = jnp.asarray(link_travel_time_cost, dtype=jnp.float32)
        if arr.ndim != 1 or int(arr.shape[0]) != network.link_count:
            raise ValueError(f"link_travel_time_cost must have shape ({network.link_count},)")
        return jnp.maximum(arr, 1e-6)
    free_flow = [
        max(1e-6, float(link.length_m) / max(1e-6, float(link.free_flow_speed_mps)))
        for link in network.links
    ]
    return jnp.asarray(free_flow, dtype=jnp.float32)


def _resolve_blocked_link_mask(
    network: RoadNetworkCSR,
    *,
    link_state: LinkState | None,
    size: int,
) -> Array:
    if link_state is None:
        return jnp.zeros((size,), dtype=jnp.bool_)
    static_blockable = jnp.asarray([bool(link.is_blockable) for link in network.links], dtype=jnp.bool_)
    blocked = link_state.effective_capacity_vehicles <= 0.0
    return jnp.asarray(blocked, dtype=jnp.bool_) & static_blockable


def _reverse_dijkstra_node_costs(
    network: RoadNetworkCSR,
    *,
    costs: Array,
    blocked: Array,
    destination_node_index: int,
) -> Array:
    node_count = network.node_count
    dist = [_INF_COST] * node_count
    dist[int(destination_node_index)] = 0.0
    heap: list[tuple[float, int]] = [(0.0, int(destination_node_index))]

    incoming_indptr = jnp.asarray(network.incoming_indptr)
    incoming_link_indices = jnp.asarray(network.incoming_link_indices)
    link_src = jnp.asarray(network.link_src_node_index)

    while heap:
        cur_cost, node_idx = heappop(heap)
        if cur_cost > dist[node_idx]:
            continue
        start = int(incoming_indptr[node_idx])
        end = int(incoming_indptr[node_idx + 1])
        for pos in range(start, end):
            link_index = int(incoming_link_indices[pos])
            if bool(blocked[link_index]):
                continue
            prev_node_idx = int(link_src[link_index])
            cand = cur_cost + float(costs[link_index])
            if cand < dist[prev_node_idx]:
                dist[prev_node_idx] = cand
                heappush(heap, (cand, prev_node_idx))
    return jnp.asarray(dist, dtype=jnp.float32)


def _outgoing_link_indices_for_node(network: RoadNetworkCSR, node_index: int) -> tuple[int, ...]:
    start = int(network.outgoing_indptr[node_index])
    end = int(network.outgoing_indptr[node_index + 1])
    return tuple(int(x) for x in jnp.asarray(network.outgoing_link_indices[start:end]).tolist())


def _filter_legal_turn_successors(
    network: RoadNetworkCSR,
    *,
    outgoing_idx: tuple[int, ...],
    incoming_link_id: int | None,
) -> tuple[int, ...]:
    if incoming_link_id is None or not outgoing_idx:
        return outgoing_idx
    if network.turn_count == 0:
        return outgoing_idx
    incoming_index = network.link_id_to_index.get(int(incoming_link_id))
    if incoming_index is None:
        return ()
    all_succ_by_from, allowed_succ_by_from = _get_turn_successor_lookup(network)
    all_successors = all_succ_by_from.get(incoming_index)
    if all_successors is None:
        return ()
    candidates = set(outgoing_idx)
    legal = tuple(
        idx
        for idx in allowed_succ_by_from.get(incoming_index, ())
        if idx in candidates and idx in all_successors
    )
    return legal


def _get_turn_successor_lookup(
    network: RoadNetworkCSR,
) -> tuple[dict[int, tuple[int, ...]], dict[int, tuple[int, ...]]]:
    cache_key = (
        id(network),
        int(network.node_count),
        int(network.link_count),
        int(network.turn_count),
        int(hash(tuple(int(link.link_id) for link in network.links))),
    )
    cached = _TURN_SUCCESSOR_CACHE.get(cache_key)
    if cached is not None:
        return cached

    turn_from = jnp.asarray(network.turn_from_link_index)
    turn_to = jnp.asarray(network.turn_to_link_index)
    turn_forbidden = jnp.asarray(network.turn_is_forbidden)

    all_map: dict[int, set[int]] = {}
    allowed_map: dict[int, set[int]] = {}
    for t_idx in range(network.turn_count):
        from_idx = int(turn_from[t_idx])
        to_idx = int(turn_to[t_idx])
        all_map.setdefault(from_idx, set()).add(to_idx)
        if not bool(turn_forbidden[t_idx]):
            allowed_map.setdefault(from_idx, set()).add(to_idx)

    frozen = (
        {k: tuple(sorted(v)) for k, v in all_map.items()},
        {k: tuple(sorted(v)) for k, v in allowed_map.items()},
    )
    _TURN_SUCCESSOR_CACHE[cache_key] = frozen
    return frozen
