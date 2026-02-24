"""Simulation initialization builder wiring city/demand/flow/routing state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import jax.numpy as jnp

from metroflow.city.generator import SyntheticCityTopology, generate_synthetic_city_topology
from metroflow.city.zones import ZoningPlacementResult, generate_zones_and_pois
from metroflow.demand.population import PopulationGenerationResult, generate_citizen_population
from metroflow.demand.trips import TripRequestGenerationResult, generate_trip_requests
from metroflow.flow.state import LinkState, NodeState
from metroflow.learning.policy_blend import PolicyBlendState
from metroflow.routing.dynamic_potential import DynamicPotentialState, compute_dynamic_potential_state
from metroflow.sim.active_agents import create_active_agent_pool
from metroflow.sim.config import CityGenerationConfig, SimulationConfig
from metroflow.sim.invariants import InvariantReport
from metroflow.sim.rng import PRNGKeyArray, key_from_seed
from metroflow.sim.state import (
    SimulationClockState,
    SimulationDynamicRefs,
    SimulationStaticRefs,
    SimulationState,
)
from metroflow.ui.stream_buffer import UISnapshotStreamBuffer

__all__ = [
    "SimulationInitBundle",
    "build_initial_simulation_state",
]


@dataclass(slots=True)
class SimulationInitBundle:
    """Concrete initialized scenario bundle for T035 wiring."""

    state: SimulationState
    rng_key: PRNGKeyArray
    city_topology: SyntheticCityTopology
    zoning: ZoningPlacementResult
    population: PopulationGenerationResult
    trip_requests: TripRequestGenerationResult


@dataclass(slots=True)
class _SimulationInitLayoutPlan:
    """Small planning stage for scalar init choices before object assembly."""

    scenario_seed: int
    scenario_id: str
    eager_trip_generation: bool
    initial_day_type: Any
    initial_time_band: Any


def build_initial_simulation_state(
    *,
    config: SimulationConfig | None = None,
    scenario_seed: int = 0,
    city_config: CityGenerationConfig | None = None,
    eager_trip_generation: bool = False,
) -> SimulationInitBundle:
    """Build a fully wired initial simulation state across city/demand/flow/routing.

    This builder is introduced in T035 and can be integrated into `sim.step`
    later without changing the high-level `SimulationState` contract.
    """

    sim_config = config if config is not None else SimulationConfig()
    city_cfg = city_config if city_config is not None else CityGenerationConfig()
    scenario_seed = int(scenario_seed)
    rng_key = key_from_seed(scenario_seed)
    layout_plan = _plan_simulation_init_layout(
        sim_config=sim_config,
        scenario_seed=scenario_seed,
        eager_trip_generation=eager_trip_generation,
    )

    clock_state = SimulationClockState(
        tick_index=0,
        day_type=layout_plan.initial_day_type,
        time_band=layout_plan.initial_time_band,
    )

    city_topology = generate_synthetic_city_topology(config=city_cfg, seed=scenario_seed, validate=True)
    road_csr = city_topology.build_csr(validate=False)
    zoning = generate_zones_and_pois(
        city_topology,
        config=city_cfg,
        seed=scenario_seed,
        population_target=sim_config.population_target,
        validate=True,
    )
    population = generate_citizen_population(
        zoning,
        config=sim_config,
        seed=scenario_seed,
        population_target=sim_config.population_target,
    )
    trip_requests = _build_initial_trip_requests(
        population=population,
        zoning=zoning,
        config=sim_config,
        seed=scenario_seed,
        day_type=clock_state.day_type,
        time_band=clock_state.time_band,
        start_tick=clock_state.tick_index,
        eager_trip_generation=layout_plan.eager_trip_generation,
    )

    flow_link_state = _build_initial_link_state(road_csr)
    flow_node_state = _build_initial_node_state(road_csr)
    routing_baseline_state, route_candidate_state, routing_host_cache = _build_initial_routing_state(
        road_csr=road_csr,
        flow_link_state=flow_link_state,
        trip_requests=trip_requests,
        zoning=zoning,
    )

    dynamic = SimulationDynamicRefs(
        clock_state=clock_state,
        demand_state=_build_initial_demand_state(trip_requests),
        active_agent_pool=create_active_agent_pool(sim_config.active_agent_capacity),
        flow_link_state=flow_link_state,
        flow_node_state=flow_node_state,
        routing_baseline_state=routing_baseline_state,
        route_candidate_state=route_candidate_state,
        policy_blend_state=PolicyBlendState(
            lambda_mix=0.0,
            baseline_only_mode=not sim_config.learning_enabled,
        ),
        metrics_state=_initial_metrics_state(trip_requests),
        invariant_state=InvariantReport(tick_index=0),
        ui_state=(
            UISnapshotStreamBuffer(
                tick_seconds=sim_config.tick_seconds,
                hz_limit=sim_config.ui_stream_hz_limit,
            )
            if sim_config.ui_stream_enabled
            else None
        ),
        metadata={
            "scenario_seed": scenario_seed,
            "init_builder": "sim.init.build_initial_simulation_state",
            "routing_host_cache": routing_host_cache,
        },
    )

    geometry_version = f"city-{scenario_seed}-n{road_csr.node_count}-l{road_csr.link_count}"
    state = SimulationState(
        config=sim_config,
        static=SimulationStaticRefs(
            scenario_id=layout_plan.scenario_id,
            city_topology=city_topology,
            zones=zoning.zones,
            pois=zoning.pois,
            population=population.citizens,
            schedule_templates=population.schedule_templates,
            routing_static={
                "road_csr": road_csr,
                "node_zone_by_id": dict(zoning.node_zone_by_id),
                "zone_node_ids": dict(zoning.zone_node_ids),
            },
            ui_network_geometry_version=geometry_version,
            metadata={
                "scenario_seed": scenario_seed,
                "city_node_count": road_csr.node_count,
                "city_link_count": road_csr.link_count,
                "trip_request_count_init": len(trip_requests.trip_requests),
                "eager_trip_generation": int(layout_plan.eager_trip_generation),
            },
        ),
        dynamic=dynamic,
        metadata={"scenario_seed": scenario_seed, "builder_task": "T035"},
    )

    return SimulationInitBundle(
        state=state,
        rng_key=rng_key,
        city_topology=city_topology,
        zoning=zoning,
        population=population,
        trip_requests=trip_requests,
    )


def _plan_simulation_init_layout(
    *,
    sim_config: SimulationConfig,
    scenario_seed: int,
    eager_trip_generation: bool,
) -> _SimulationInitLayoutPlan:
    """Planning/materialization split for init scalar choices and metadata."""

    return _SimulationInitLayoutPlan(
        scenario_seed=int(scenario_seed),
        scenario_id=f"synthetic-{int(scenario_seed)}",
        eager_trip_generation=bool(eager_trip_generation),
        initial_day_type=sim_config.day_type_set[0],
        initial_time_band=sim_config.time_bands[0],
    )


def _build_initial_link_state(road_csr: Any) -> LinkState:
    travel_time_cost = jnp.asarray(
        [
            max(1e-3, float(link.length_m) / max(1e-3, float(link.free_flow_speed_mps)))
            for link in road_csr.links
        ],
        dtype=jnp.float32,
    )
    capacity = jnp.asarray(
        [max(0.0, float(link.capacity_veh_per_tick)) for link in road_csr.links],
        dtype=jnp.float32,
    )
    link_count = int(road_csr.link_count)
    zeros = jnp.zeros((link_count,), dtype=jnp.float32)
    ones = jnp.ones((link_count,), dtype=jnp.float32)
    return LinkState(
        queue_vehicles=zeros,
        inflow_vehicles=zeros,
        outflow_vehicles=zeros,
        travel_time_cost=travel_time_cost,
        capacity_veh_per_tick=capacity,
        incident_capacity_multiplier=ones,
        capacity_violation_flags=jnp.zeros((link_count,), dtype=jnp.bool_),
        metadata={"free_flow_travel_time_cost": travel_time_cost},
    )


def _build_initial_node_state(road_csr: Any) -> NodeState:
    turn_count = int(road_csr.turn_count)
    node_count = int(road_csr.node_count)
    zeros_turn = jnp.zeros((turn_count,), dtype=jnp.float32)
    return NodeState(
        turn_from_link_index=road_csr.turn_from_link_index,
        turn_to_link_index=road_csr.turn_to_link_index,
        turn_demand=zeros_turn,
        turn_supply=zeros_turn,
        turn_flow=zeros_turn,
        signal_phase_index=jnp.zeros((node_count,), dtype=jnp.int32),
        signal_phase_timer=jnp.zeros((node_count,), dtype=jnp.int32),
        metadata={
            "turn_base_priority": jnp.asarray(road_csr.turn_base_priority, dtype=jnp.float32),
            "turn_is_forbidden": jnp.asarray(road_csr.turn_is_forbidden, dtype=jnp.bool_),
        },
    )


def _build_initial_demand_state(trips: TripRequestGenerationResult) -> dict[str, Any]:
    trip_requests = tuple(trips.trip_requests)
    queued_count = sum(1 for trip in trip_requests if str(trip.status.value) == "queued")
    return {
        "trip_requests": trip_requests,
        "queued_trip_requests": queued_count,
        "pending_trip_requests": queued_count,
        "activated_trip_requests": 0,
        "last_generation_metadata": dict(trips.metadata),
    }


def _build_initial_routing_state(
    *,
    road_csr: Any,
    flow_link_state: LinkState,
    trip_requests: TripRequestGenerationResult,
    zoning: ZoningPlacementResult,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    poi_node_by_id = {poi.poi_id: poi.node_id for poi in zoning.pois}
    potential_cache: dict[Any, DynamicPotentialState] = {}
    warm_destination_node_id: int | None = None
    warm_dynamic_potential_state: DynamicPotentialState | None = None
    if trip_requests.trip_requests:
        first_trip = trip_requests.trip_requests[0]
        warm_destination_node_id = poi_node_by_id.get(first_trip.dest_poi_id)
        if warm_destination_node_id is not None:
            warm_dynamic_potential_state = compute_dynamic_potential_state(
                road_csr,
                destination_node_id=warm_destination_node_id,
                link_state=flow_link_state,
            )

    routing_baseline_state = {
        "dynamic_potential_cache_size": 0,
        "warm_destination_node_id": warm_destination_node_id,
        "last_refresh_tick": 0,
        "potential_state_version": 0,
    }
    route_candidate_state = {
        "candidate_sets": {},
        "last_refresh_tick": -1,
    }
    routing_host_cache = {
        "dynamic_potential_cache": potential_cache,
        "warm_dynamic_potential_state": warm_dynamic_potential_state,
    }
    return routing_baseline_state, route_candidate_state, routing_host_cache


def _build_initial_trip_requests(
    *,
    population: PopulationGenerationResult,
    zoning: ZoningPlacementResult,
    config: SimulationConfig,
    seed: int,
    day_type: Any,
    time_band: Any,
    start_tick: int,
    eager_trip_generation: bool,
) -> TripRequestGenerationResult:
    if not eager_trip_generation:
        return TripRequestGenerationResult(
            trip_requests=(),
            metadata={
                "seed": int(seed),
                "day_type": str(day_type.value),
                "time_band": str(time_band.value),
                "trip_request_count": 0,
                "requested_citizen_count": len(population.citizens),
                "eager_trip_generation": 0,
            },
        )
    trips = generate_trip_requests(
        population,
        zoning,
        config=config,
        seed=seed,
        day_type=day_type,
        time_band=time_band,
        start_tick=start_tick,
    )
    md = dict(trips.metadata)
    md["eager_trip_generation"] = 1
    return TripRequestGenerationResult(trip_requests=trips.trip_requests, metadata=md)


def _initial_metrics_state(trips: TripRequestGenerationResult) -> dict[str, Any]:
    generated_total = len(trips.trip_requests)
    return {
        "tick_index": 0,
        "active_agents": 0,
        "queued_trip_requests": generated_total,
        "completed_trips_total": 0,
        "failed_trips_total": 0,
        "capacity_violation_count": 0,
        "capacity_violation_count_delta": 0,
        "negative_queue_detected": False,
        "hotspot_links_top_k": (),
        "ui_packets_emitted": 0,
        "generated_trip_total": generated_total,
    }
