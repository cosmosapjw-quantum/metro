from __future__ import annotations

import jax.numpy as jnp

from metroflow.city.graph import (
    Node,
    RoadClass,
    RoadLink,
    TurnMovement,
    TurnType,
    build_road_network_csr,
)
from metroflow.flow.state import create_link_state
from metroflow.routing.dynamic_potential import (
    build_greedy_route_candidate,
    compute_dynamic_potential_state,
    score_legal_next_links,
)


def test_dynamic_potential_prefers_lower_congestion_path():
    csr = build_road_network_csr(
        nodes=(
            Node(1),
            Node(2),
            Node(3),
            Node(4),
        ),
        links=(
            RoadLink(10, 1, 2, RoadClass.ARTERIAL, 100.0, 10.0, 5.0),
            RoadLink(11, 2, 4, RoadClass.ARTERIAL, 100.0, 10.0, 5.0),
            RoadLink(12, 1, 3, RoadClass.ARTERIAL, 100.0, 10.0, 5.0),
            RoadLink(13, 3, 4, RoadClass.ARTERIAL, 100.0, 10.0, 5.0),
        ),
        turns=(
            TurnMovement(10, 11, TurnType.THROUGH),
            TurnMovement(12, 13, TurnType.THROUGH),
        ),
    )
    link_state = create_link_state(4, capacity_veh_per_tick=5.0)
    link_state = type(link_state)(
        queue_vehicles=link_state.queue_vehicles,
        inflow_vehicles=link_state.inflow_vehicles,
        outflow_vehicles=link_state.outflow_vehicles,
        travel_time_cost=jnp.array([50.0, 1.0, 1.0, 1.0], dtype=jnp.float32),
        capacity_veh_per_tick=link_state.capacity_veh_per_tick,
        incident_capacity_multiplier=link_state.incident_capacity_multiplier,
        capacity_violation_flags=link_state.capacity_violation_flags,
        metadata=link_state.metadata,
    )

    potential = compute_dynamic_potential_state(csr, destination_node_id=4, link_state=link_state)
    scores = score_legal_next_links(csr, potential, current_node_id=1)
    path = build_greedy_route_candidate(csr, potential, origin_node_id=1)

    assert scores.best_link_id == 12
    assert path == (12, 13)


def test_dynamic_potential_excludes_forbidden_turn_candidates():
    csr = build_road_network_csr(
        nodes=(
            Node(1),
            Node(2),
            Node(3),
            Node(4),
            Node(5),
        ),
        links=(
            RoadLink(10, 1, 2, RoadClass.ARTERIAL, 100.0, 10.0, 5.0),
            RoadLink(11, 2, 3, RoadClass.ARTERIAL, 100.0, 10.0, 5.0),
            RoadLink(12, 2, 4, RoadClass.ARTERIAL, 100.0, 10.0, 5.0),
            RoadLink(13, 4, 3, RoadClass.ARTERIAL, 100.0, 10.0, 5.0),
        ),
        turns=(
            TurnMovement(10, 11, TurnType.U_TURN_FORBIDDEN),
            TurnMovement(10, 12, TurnType.RIGHT),
            TurnMovement(12, 13, TurnType.THROUGH),
        ),
    )
    potential = compute_dynamic_potential_state(csr, destination_node_id=3)
    scores = score_legal_next_links(csr, potential, current_node_id=2, incoming_link_id=10)

    assert 11 not in scores.candidate_link_ids
    assert scores.best_link_id == 12


def test_dynamic_potential_treats_zero_capacity_blockable_link_as_blocked():
    csr = build_road_network_csr(
        nodes=(Node(1), Node(2), Node(3)),
        links=(
            RoadLink(10, 1, 2, RoadClass.BRIDGE, 100.0, 10.0, 5.0, bridge_group_id=1),
            RoadLink(11, 2, 3, RoadClass.ARTERIAL, 100.0, 10.0, 5.0),
        ),
        turns=(TurnMovement(10, 11, TurnType.THROUGH),),
    )
    link_state = create_link_state(2, capacity_veh_per_tick=5.0)
    link_state = type(link_state)(
        queue_vehicles=link_state.queue_vehicles,
        inflow_vehicles=link_state.inflow_vehicles,
        outflow_vehicles=link_state.outflow_vehicles,
        travel_time_cost=jnp.array([1.0, 1.0], dtype=jnp.float32),
        capacity_veh_per_tick=link_state.capacity_veh_per_tick,
        incident_capacity_multiplier=jnp.array([0.0, 1.0], dtype=jnp.float32),
        capacity_violation_flags=link_state.capacity_violation_flags,
        metadata=link_state.metadata,
    )

    potential = compute_dynamic_potential_state(csr, destination_node_id=3, link_state=link_state)
    path = build_greedy_route_candidate(csr, potential, origin_node_id=1)

    assert bool(potential.blocked_link_mask[0]) is True
    assert path == ()


def test_dynamic_potential_returns_empty_when_route_cannot_reach_destination():
    csr = build_road_network_csr(
        nodes=(Node(1), Node(2), Node(3)),
        links=(RoadLink(10, 1, 2, RoadClass.ARTERIAL, 100.0, 10.0, 5.0),),
        turns=(),
    )
    potential = compute_dynamic_potential_state(csr, destination_node_id=3)
    path = build_greedy_route_candidate(csr, potential, origin_node_id=1)
    assert path == ()


def test_dynamic_potential_strict_turn_filter_returns_no_candidate_when_missing_turn_data():
    csr = build_road_network_csr(
        nodes=(Node(1), Node(2), Node(3), Node(4)),
        links=(
            RoadLink(10, 1, 2, RoadClass.ARTERIAL, 100.0, 10.0, 5.0),
            RoadLink(11, 2, 3, RoadClass.ARTERIAL, 100.0, 10.0, 5.0),
            RoadLink(12, 4, 2, RoadClass.ARTERIAL, 100.0, 10.0, 5.0),
        ),
        turns=(TurnMovement(10, 11, TurnType.THROUGH),),
    )
    potential = compute_dynamic_potential_state(csr, destination_node_id=3)
    scores = score_legal_next_links(csr, potential, current_node_id=2, incoming_link_id=12)
    assert scores.candidate_link_ids == ()
    assert scores.best_link_id is None
