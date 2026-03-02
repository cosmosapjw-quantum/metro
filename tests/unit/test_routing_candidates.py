from __future__ import annotations

from metroflow.city.graph import Node, RoadClass, RoadLink, TurnMovement, TurnType, build_road_network_csr
from metroflow.flow.state import create_link_state
from metroflow.routing.candidates import create_route_candidate_set
from metroflow.routing.dynamic_potential import build_greedy_route_candidate, compute_dynamic_potential_state


def test_build_greedy_route_candidate_respects_incoming_link_on_first_turn():
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

    path = build_greedy_route_candidate(
        csr,
        potential,
        origin_node_id=2,
        incoming_link_id=12,
    )

    assert path == ()


def test_create_route_candidate_set_returns_empty_when_first_turn_is_illegal():
    csr = build_road_network_csr(
        nodes=(Node(1), Node(2), Node(3), Node(4)),
        links=(
            RoadLink(10, 1, 2, RoadClass.ARTERIAL, 100.0, 10.0, 5.0),
            RoadLink(11, 2, 3, RoadClass.ARTERIAL, 100.0, 10.0, 5.0),
            RoadLink(12, 4, 2, RoadClass.ARTERIAL, 100.0, 10.0, 5.0),
        ),
        turns=(TurnMovement(10, 11, TurnType.THROUGH),),
    )
    link_state = create_link_state(csr.link_count, capacity_veh_per_tick=5.0)

    candidate_set = create_route_candidate_set(
        road_csr=csr,
        link_state=link_state,
        od_key=("z4", "z3"),
        origin_node_id=2,
        destination_node_id=3,
        current_tick=7,
        incoming_link_id=12,
    )

    assert candidate_set.candidate_ids == ()
    assert candidate_set.candidate_paths == ()
