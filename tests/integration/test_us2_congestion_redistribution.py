from __future__ import annotations

import runpy
from pathlib import Path

import numpy as np
import pytest

from metroflow.sim.config import SimulationConfig
from metroflow.sim.control import SimulationControl
from metroflow.sim.step import init_simulation, run_rollout, validate_invariants

"""Contract-first integration tests for US2 congestion redistribution (T048-T052).

These tests may skip while event/effects/reroute integration is pending. Once
implemented, they should validate observable hotspot redistribution after
incidents rather than silently skipping real behavior regressions.
"""

_SCENARIOS = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "fixtures" / "simulation_scenarios.py")
)
SEED_REGISTRY = _SCENARIOS["SEED_REGISTRY"]


def test_us2_bridge_incident_changes_hotspot_distribution_pending_t048_t052():
    events_mod = _require_us2_disruption_modules()
    config = SimulationConfig(
        active_agent_capacity=24,
        ui_stream_enabled=False,
        learning_enabled=False,
    )
    baseline_state, baseline_key = init_simulation(
        config=config,
        scenario_seed=SEED_REGISTRY["disruption_bridge_closure"],
    )
    disrupted_state, disrupted_key = init_simulation(
        config=config,
        scenario_seed=SEED_REGISTRY["disruption_bridge_closure"],
    )

    bridge_group_id = _select_existing_bridge_group_id(disrupted_state)
    affected_bridge_link_ids = _bridge_group_link_ids(disrupted_state, bridge_group_id=bridge_group_id)
    bridge_event = _build_disruption_event(
        events_mod,
        event_id=9101,
        event_type="construction",
        target_scope={"bridge_group_id": bridge_group_id},
        effect_model="closure",
        end_tick=20,
    )

    baseline_final, _, _ = run_rollout(
        initial_state=baseline_state,
        controls=[SimulationControl.noop() for _ in range(12)],
        rng_key=baseline_key,
    )
    disrupted_final, _, _ = run_rollout(
        initial_state=disrupted_state,
        controls=[SimulationControl(inject_event=bridge_event)] + [SimulationControl.noop() for _ in range(11)],
        rng_key=disrupted_key,
    )

    assert validate_invariants(baseline_final).ok is True
    assert validate_invariants(disrupted_final).ok is True

    base_congestion = _congestion_ratio_by_link_id(baseline_final)
    disrupted_congestion = _congestion_ratio_by_link_id(disrupted_final)
    _assert_redistribution_observable(
        base_congestion,
        disrupted_congestion,
        affected_link_ids=affected_bridge_link_ids,
    )


def test_us2_incident_redistribution_preserves_summary_and_invariants_pending_t048_t052():
    events_mod = _require_us2_disruption_modules()
    config = SimulationConfig(
        active_agent_capacity=24,
        ui_stream_enabled=False,
        learning_enabled=False,
    )
    state, rng_key = init_simulation(
        config=config,
        scenario_seed=SEED_REGISTRY["disruption_bridge_closure"],
    )
    baseline_state, baseline_key = init_simulation(
        config=config,
        scenario_seed=SEED_REGISTRY["disruption_bridge_closure"],
    )
    blocked_link_id = _select_existing_blockable_link_id(state)
    event = _build_disruption_event(
        events_mod,
        event_id=9102,
        event_type="accident",
        target_scope={"link_ids": (blocked_link_id,)},
        effect_model="closure",
        end_tick=12,
    )

    baseline_final, _, _ = run_rollout(
        initial_state=baseline_state,
        controls=[SimulationControl.noop() for _ in range(12)],
        rng_key=baseline_key,
    )
    final_state, telemetry_log, _ = run_rollout(
        initial_state=state,
        controls=[SimulationControl(inject_event=event)] + [SimulationControl.noop() for _ in range(11)],
        rng_key=rng_key,
    )
    invariant_report = validate_invariants(final_state)
    baseline_invariants = validate_invariants(baseline_final)

    assert invariant_report.ok is True
    assert baseline_invariants.ok is True
    assert len(telemetry_log) == 12
    assert final_state.tick_index == 12
    base_congestion = _congestion_ratio_by_link_id(baseline_final)
    disrupted_congestion = _congestion_ratio_by_link_id(final_state)
    _assert_redistribution_observable(
        base_congestion,
        disrupted_congestion,
        affected_link_ids={int(blocked_link_id)},
    )


def _require_us2_disruption_modules():
    events_mod = pytest.importorskip(
        "metroflow.flow.events",
        reason="T048 pending: flow.events not implemented yet",
    )
    pytest.importorskip(
        "metroflow.flow.event_effects",
        reason="T049 pending: flow.event_effects not implemented yet",
    )
    pytest.importorskip(
        "metroflow.routing.reroute_policy",
        reason="T051 pending: routing.reroute_policy not implemented yet",
    )
    step_mod = pytest.importorskip("metroflow.sim.step")
    if not bool(getattr(step_mod, "_US2_EVENTS_REROUTE_INTEGRATED", False)):
        pytest.skip("T052 pending: sim.step US2 event/reroute integration not implemented yet")
    return events_mod


def _build_disruption_event(
    events_mod,
    *,
    event_id: int,
    event_type: str,
    target_scope: dict[str, object],
    effect_model: str,
    end_tick: int,
):
    if not hasattr(events_mod, "TrafficEvent") or not hasattr(events_mod, "TrafficEventStatus"):
        pytest.skip("T048 pending: TrafficEvent / TrafficEventStatus exports missing")
    TrafficEvent = events_mod.TrafficEvent
    TrafficEventStatus = events_mod.TrafficEventStatus
    try:
        return TrafficEvent(
            event_id=int(event_id),
            event_type=str(event_type),
            start_tick=1,
            end_tick=int(end_tick),
            target_scope=dict(target_scope),
            severity=1.0,
            effect_model=str(effect_model),
            status=TrafficEventStatus.SCHEDULED,
        )
    except TypeError as exc:
        pytest.skip(f"T048/T049 pending: event constructor/signature not finalized ({exc})")


def _select_existing_bridge_group_id(state) -> int:
    city_topology = getattr(getattr(state, "static", None), "city_topology", None)
    bridge_crossings = getattr(city_topology, "bridge_crossings", ()) if city_topology is not None else ()
    best: tuple[float, int] | None = None
    for crossing in tuple(bridge_crossings):
        bridge_group_id = _field(crossing, "bridge_group_id", None)
        if bridge_group_id is None:
            continue
        rank_hint = float(_field(crossing, "bottleneck_rank_hint", 0.0) or 0.0)
        candidate = (rank_hint, int(bridge_group_id))
        if best is None or candidate[0] > best[0]:
            best = candidate
    if best is not None:
        return best[1]
    pytest.fail("US2 congestion redistribution fixture requires at least one bridge crossing/group")


def _select_existing_blockable_link_id(state) -> int:
    routing_static = getattr(getattr(state, "static", None), "routing_static", {}) or {}
    road_csr = routing_static.get("road_csr") if isinstance(routing_static, dict) else None
    links = getattr(road_csr, "links", ()) if road_csr is not None else ()
    best: tuple[int, float, int] | None = None
    for link in tuple(links):
        if not bool(_field(link, "is_blockable", False)):
            continue
        road_class = str(_field(_field(link, "road_class", "local"), "value", _field(link, "road_class", "local")))
        priority = {
            "bridge": 0,
            "arterial": 1,
            "expressway": 2,
            "ramp": 3,
            "local": 4,
        }.get(road_class, 9)
        capacity = float(_field(link, "capacity_veh_per_tick", 0.0) or 0.0)
        link_id = int(_field(link, "link_id", -1))
        candidate = (priority, -capacity, link_id)
        if best is None or candidate < best:
            best = candidate
    if best is not None:
        return int(best[2])
    pytest.fail("US2 congestion redistribution fixture requires at least one blockable link")


def _field(obj: object, name: str, default: object) -> object:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _bridge_group_link_ids(state, *, bridge_group_id: int) -> set[int]:
    city_topology = getattr(getattr(state, "static", None), "city_topology", None)
    bridge_crossings = getattr(city_topology, "bridge_crossings", ()) if city_topology is not None else ()
    for crossing in tuple(bridge_crossings):
        if int(_field(crossing, "bridge_group_id", -1)) != int(bridge_group_id):
            continue
        link_ids = _field(crossing, "link_ids", ())
        try:
            ids = {int(v) for v in tuple(link_ids)}
        except Exception:
            ids = set()
        if ids:
            return ids
    return set()


def _congestion_ratio_by_link_id(state) -> dict[int, float]:
    flow_link_state = getattr(getattr(state, "dynamic", None), "flow_link_state", None)
    routing_static = getattr(getattr(state, "static", None), "routing_static", {}) or {}
    road_csr = routing_static.get("road_csr") if isinstance(routing_static, dict) else None
    links = getattr(road_csr, "links", ()) if road_csr is not None else ()
    if flow_link_state is None:
        pytest.fail("flow_link_state missing for congestion redistribution contract test")
    queue = np.asarray(getattr(flow_link_state, "queue_vehicles", ()), dtype=np.float32)
    cap = np.asarray(getattr(flow_link_state, "effective_capacity_vehicles", ()), dtype=np.float32)
    if queue.size == 0 or cap.size == 0 or queue.shape != cap.shape:
        pytest.fail("flow_link_state queue/effective_capacity arrays missing or mismatched")
    if len(tuple(links)) != int(queue.shape[0]):
        pytest.fail("road_csr.links length does not match flow link axis")
    ratios = queue / np.maximum(cap, 1e-6)
    out: dict[int, float] = {}
    for idx, link in enumerate(tuple(links)):
        out[int(_field(link, "link_id", idx))] = float(ratios[idx])
    return out


def _assert_redistribution_observable(
    base_congestion: dict[int, float],
    disrupted_congestion: dict[int, float],
    *,
    affected_link_ids: set[int],
) -> None:
    assert set(base_congestion) == set(disrupted_congestion)
    deltas = {
        link_id: abs(float(disrupted_congestion[link_id]) - float(base_congestion[link_id]))
        for link_id in base_congestion
    }
    total_delta = sum(deltas.values())
    assert total_delta > 1e-6
    unaffected_ids = set(deltas) - set(int(v) for v in affected_link_ids)
    if unaffected_ids:
        unaffected_delta = sum(deltas[link_id] for link_id in unaffected_ids)
        assert unaffected_delta > 1e-6
