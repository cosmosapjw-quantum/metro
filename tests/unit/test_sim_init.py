from __future__ import annotations

import runpy
from pathlib import Path

from metroflow.sim.config import SimulationConfig
from metroflow.sim.init import build_initial_simulation_state

_SCENARIOS = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "fixtures" / "simulation_scenarios.py")
)
SEED_REGISTRY = _SCENARIOS["SEED_REGISTRY"]


def test_build_initial_simulation_state_wires_city_demand_flow_and_routing_refs():
    bundle = build_initial_simulation_state(
        config=SimulationConfig(
            active_agent_capacity=64,
            ui_stream_enabled=False,
            learning_enabled=False,
        ),
        scenario_seed=SEED_REGISTRY["baseline_smoke"],
    )
    state = bundle.state
    road_csr = state.static.routing_static["road_csr"]

    assert state.tick_index == 0
    assert bundle.city_topology.nodes
    assert bundle.zoning.zones and bundle.zoning.pois
    assert bundle.population.citizens

    assert state.static.city_topology is bundle.city_topology
    assert len(state.static.pois) == len(bundle.zoning.pois)
    assert len(state.static.population) == len(bundle.population.citizens)

    assert state.dynamic.flow_link_state.link_count == road_csr.link_count
    assert state.dynamic.flow_node_state.turn_count == road_csr.turn_count
    assert "turn_base_priority" in state.dynamic.flow_node_state.metadata
    assert "turn_is_forbidden" in state.dynamic.flow_node_state.metadata

    assert state.dynamic.demand_state["queued_trip_requests"] == len(bundle.trip_requests.trip_requests)
    assert state.dynamic.metrics_state["generated_trip_total"] == len(bundle.trip_requests.trip_requests)

    routing_state = state.dynamic.routing_baseline_state
    assert routing_state["dynamic_potential_cache_size"] == 0
    assert road_csr is state.static.routing_static["road_csr"]
    assert "node_zone_by_id" in state.static.routing_static
    assert "zone_node_ids" in state.static.routing_static
    assert isinstance(state.dynamic.metadata["routing_host_cache"]["dynamic_potential_cache"], dict)
    assert "candidate_sets" in state.dynamic.route_candidate_state


def test_build_initial_simulation_state_is_reproducible_for_same_seed_counts():
    cfg = SimulationConfig(active_agent_capacity=32, ui_stream_enabled=False)
    a = build_initial_simulation_state(config=cfg, scenario_seed=123)
    b = build_initial_simulation_state(config=cfg, scenario_seed=123)

    assert a.state.static.scenario_id == b.state.static.scenario_id
    assert len(a.city_topology.nodes) == len(b.city_topology.nodes)
    assert len(a.city_topology.links) == len(b.city_topology.links)
    assert len(a.zoning.pois) == len(b.zoning.pois)
    assert len(a.population.citizens) == len(b.population.citizens)
    assert len(a.trip_requests.trip_requests) == len(b.trip_requests.trip_requests)
    assert a.state.static.routing_static["node_zone_by_id"] == b.state.static.routing_static["node_zone_by_id"]
