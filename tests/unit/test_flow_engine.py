from __future__ import annotations

import jax.numpy as jnp

from metroflow.flow.engine import update_link_node_flow
from metroflow.flow.state import create_link_state, create_node_state


def test_update_link_node_flow_moves_queue_via_turns_and_updates_costs():
    link_state = create_link_state(
        2,
        travel_time_cost=jnp.array([2.0, 3.0], dtype=jnp.float32),
        capacity_veh_per_tick=jnp.array([2.0, 3.0], dtype=jnp.float32),
    )
    link_state = type(link_state)(
        queue_vehicles=jnp.array([5.0, 0.0], dtype=jnp.float32),
        inflow_vehicles=link_state.inflow_vehicles,
        outflow_vehicles=link_state.outflow_vehicles,
        travel_time_cost=link_state.travel_time_cost,
        capacity_veh_per_tick=link_state.capacity_veh_per_tick,
        incident_capacity_multiplier=link_state.incident_capacity_multiplier,
        capacity_violation_flags=link_state.capacity_violation_flags,
        metadata=link_state.metadata,
    )
    node_state = create_node_state([0], [1], node_count=1)
    node_state = type(node_state)(
        turn_from_link_index=node_state.turn_from_link_index,
        turn_to_link_index=node_state.turn_to_link_index,
        turn_demand=jnp.array([3.0], dtype=jnp.float32),
        turn_supply=node_state.turn_supply,
        turn_flow=node_state.turn_flow,
        signal_phase_index=node_state.signal_phase_index,
        signal_phase_timer=node_state.signal_phase_timer,
        metadata=node_state.metadata,
    )

    result = update_link_node_flow(link_state, node_state)

    assert result.node_state.turn_flow.tolist() == [2.0]
    assert result.node_state.turn_supply.tolist() == [2.0]
    assert result.link_state.outflow_vehicles.tolist() == [2.0, 0.0]
    assert result.link_state.inflow_vehicles.tolist() == [0.0, 2.0]
    assert result.link_state.queue_vehicles.tolist() == [3.0, 2.0]
    assert bool(jnp.all(result.link_state.travel_time_cost > 0))
    assert result.node_state.signal_phase_timer.tolist() == [1]


def test_update_link_node_flow_respects_forbidden_turn_metadata():
    link_state = create_link_state(2, capacity_veh_per_tick=5.0)
    link_state = type(link_state)(
        queue_vehicles=jnp.array([4.0, 0.0], dtype=jnp.float32),
        inflow_vehicles=link_state.inflow_vehicles,
        outflow_vehicles=link_state.outflow_vehicles,
        travel_time_cost=link_state.travel_time_cost,
        capacity_veh_per_tick=link_state.capacity_veh_per_tick,
        incident_capacity_multiplier=link_state.incident_capacity_multiplier,
        capacity_violation_flags=link_state.capacity_violation_flags,
        metadata=link_state.metadata,
    )
    node_state = create_node_state([0], [1], node_count=1)
    node_state = type(node_state)(
        turn_from_link_index=node_state.turn_from_link_index,
        turn_to_link_index=node_state.turn_to_link_index,
        turn_demand=jnp.array([4.0], dtype=jnp.float32),
        turn_supply=node_state.turn_supply,
        turn_flow=node_state.turn_flow,
        signal_phase_index=node_state.signal_phase_index,
        signal_phase_timer=node_state.signal_phase_timer,
        metadata={"turn_is_forbidden": jnp.array([True])},
    )

    result = update_link_node_flow(link_state, node_state)

    assert result.node_state.turn_flow.tolist() == [0.0]
    assert result.link_state.inflow_vehicles.tolist() == [0.0, 0.0]
    assert result.link_state.outflow_vehicles.tolist() == [0.0, 0.0]
    assert result.link_state.queue_vehicles.tolist() == [4.0, 0.0]


def test_update_link_node_flow_uses_stable_free_flow_cost_baseline_across_ticks():
    link_state = create_link_state(
        2,
        travel_time_cost=jnp.array([2.0, 2.0], dtype=jnp.float32),
        capacity_veh_per_tick=jnp.array([2.0, 2.0], dtype=jnp.float32),
    )
    node_state = create_node_state([0], [1], node_count=1)
    node_state = type(node_state)(
        turn_from_link_index=node_state.turn_from_link_index,
        turn_to_link_index=node_state.turn_to_link_index,
        turn_demand=jnp.array([2.0], dtype=jnp.float32),
        turn_supply=node_state.turn_supply,
        turn_flow=node_state.turn_flow,
        signal_phase_index=node_state.signal_phase_index,
        signal_phase_timer=node_state.signal_phase_timer,
        metadata=node_state.metadata,
    )

    tick1_input = type(link_state)(
        queue_vehicles=jnp.array([4.0, 0.0], dtype=jnp.float32),
        inflow_vehicles=link_state.inflow_vehicles,
        outflow_vehicles=link_state.outflow_vehicles,
        travel_time_cost=link_state.travel_time_cost,
        capacity_veh_per_tick=link_state.capacity_veh_per_tick,
        incident_capacity_multiplier=link_state.incident_capacity_multiplier,
        capacity_violation_flags=link_state.capacity_violation_flags,
        metadata=link_state.metadata,
    )
    tick1 = update_link_node_flow(tick1_input, node_state)
    tick2 = update_link_node_flow(
        type(tick1.link_state)(
            queue_vehicles=jnp.array([0.0, 0.0], dtype=jnp.float32),
            inflow_vehicles=tick1.link_state.inflow_vehicles,
            outflow_vehicles=tick1.link_state.outflow_vehicles,
            travel_time_cost=tick1.link_state.travel_time_cost,
            capacity_veh_per_tick=tick1.link_state.capacity_veh_per_tick,
            incident_capacity_multiplier=tick1.link_state.incident_capacity_multiplier,
            capacity_violation_flags=tick1.link_state.capacity_violation_flags,
            metadata=tick1.link_state.metadata,
        ),
        node_state,
    )

    assert tick2.link_state.travel_time_cost.tolist() == [2.0, 2.0]


def test_update_link_node_flow_validate_rejects_turns_without_links():
    link_state = create_link_state(0)
    node_state = create_node_state([0], [0], node_count=1)
    try:
        update_link_node_flow(link_state, node_state, validate=True)
    except ValueError as exc:
        assert "non-empty LinkState" in str(exc)
    else:
        raise AssertionError("expected ValueError")
