from __future__ import annotations

from dataclasses import replace

import pytest

from metroflow.sim.active_agents import (
    ActiveAgentSlot,
    allocate_active_agent_slot,
    create_active_agent_pool,
    read_active_agent_slot,
    release_active_agent_slot,
    validate_active_agent_pool,
)


def test_active_agent_pool_empty_pool_is_consistent():
    pool = create_active_agent_pool(4)

    assert pool.capacity == 4
    assert pool.alive_count == 0
    assert pool.available_slots == 4
    assert validate_active_agent_pool(pool) == ()


def test_active_agent_pool_allocate_release_reuses_recently_freed_slot():
    pool = create_active_agent_pool(3)

    slot_a = ActiveAgentSlot.spawn(
        citizen_id=10,
        trip_id=100,
        current_link_id=1000,
        dest_node_id=2000,
        behavior_profile_id=1,
    )
    slot_b = ActiveAgentSlot.spawn(
        citizen_id=11,
        trip_id=101,
        current_link_id=1001,
        dest_node_id=2001,
        behavior_profile_id=2,
    )

    pool, slot_id_a = allocate_active_agent_slot(pool, slot_a)
    pool, slot_id_b = allocate_active_agent_slot(pool, slot_b)
    assert (slot_id_a, slot_id_b) == (0, 1)
    assert validate_active_agent_pool(pool) == ()

    # Releasing the most recent allocation should make it the next slot reused.
    pool = release_active_agent_slot(pool, slot_id_b)
    assert validate_active_agent_pool(pool) == ()

    slot_c = ActiveAgentSlot.spawn(
        citizen_id=12,
        trip_id=102,
        current_link_id=1002,
        dest_node_id=2002,
        behavior_profile_id=3,
        progress_01=0.25,
    )
    pool, slot_id_c = allocate_active_agent_slot(pool, slot_c)
    assert slot_id_c == slot_id_b
    assert validate_active_agent_pool(pool) == ()

    read_back = read_active_agent_slot(pool, slot_id_c)
    assert read_back.alive is True
    assert read_back.trip_id == 102
    assert read_back.citizen_id == 12
    assert read_back.progress_01 == pytest.approx(0.25)


def test_active_agent_pool_release_resets_slot_fields():
    pool = create_active_agent_pool(2)
    slot = ActiveAgentSlot.spawn(
        citizen_id=1,
        trip_id=2,
        current_link_id=3,
        dest_node_id=4,
        behavior_profile_id=5,
        progress_01=0.75,
        remaining_route_ptr=6,
        reroute_cooldown_ticks=7,
    )
    pool, slot_id = allocate_active_agent_slot(pool, slot)
    pool = release_active_agent_slot(pool, slot_id)

    read_back = read_active_agent_slot(pool, slot_id)
    assert read_back.alive is False
    assert read_back.citizen_id == -1
    assert read_back.trip_id == -1
    assert read_back.current_link_id == -1
    assert read_back.dest_node_id == -1
    assert read_back.behavior_profile_id == -1
    assert read_back.progress_01 == pytest.approx(0.0)
    assert read_back.remaining_route_ptr == 0
    assert read_back.reroute_cooldown_ticks == 0


def test_active_agent_pool_validator_detects_alive_and_free_overlap():
    pool = create_active_agent_pool(2)
    slot = ActiveAgentSlot.spawn(
        citizen_id=1,
        trip_id=2,
        current_link_id=3,
        dest_node_id=4,
        behavior_profile_id=5,
    )
    pool, slot_id = allocate_active_agent_slot(pool, slot)

    corrupted = replace(
        pool,
        free_slot_count=pool.free_slot_count + 1,
        alive_count=pool.alive_count - 1,
        free_slot_stack=pool.free_slot_stack.at[pool.free_slot_count].set(slot_id),
    )
    issues = validate_active_agent_pool(corrupted)
    assert "slot ids appear in both alive set and free_slot_stack" in issues
