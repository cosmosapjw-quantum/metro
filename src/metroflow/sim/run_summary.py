"""Baseline run summary aggregation helpers (US1/T041)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

import numpy as np

from metroflow.flow.state import LinkState
from metroflow.sim.state import SimulationState

__all__ = [
    "BaselineRunSummary",
    "build_baseline_run_summary",
]


@dataclass(slots=True)
class BaselineRunSummary:
    """Compact baseline run summary for demo/reporting output."""

    scenario_id: str
    seed: int | None
    tick_index: int
    day_type: str
    time_band: str
    trip_generation_total: int
    trip_completed_total: int
    trip_failed_total: int
    active_agents: int
    queued_trip_requests: int
    pending_trip_requests: int
    capacity_violation_count: int
    negative_queue_detected: bool
    ui_packets_emitted: int
    hotspot_links_top_k: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    ui_packet_counts: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.scenario_id = str(self.scenario_id)
        self.seed = None if self.seed is None else int(self.seed)
        self.tick_index = int(self.tick_index)
        self.day_type = str(self.day_type)
        self.time_band = str(self.time_band)
        self.trip_generation_total = int(self.trip_generation_total)
        self.trip_completed_total = int(self.trip_completed_total)
        self.trip_failed_total = int(self.trip_failed_total)
        self.active_agents = int(self.active_agents)
        self.queued_trip_requests = int(self.queued_trip_requests)
        self.pending_trip_requests = int(self.pending_trip_requests)
        self.capacity_violation_count = int(self.capacity_violation_count)
        self.negative_queue_detected = bool(self.negative_queue_detected)
        self.ui_packets_emitted = int(self.ui_packets_emitted)
        self.hotspot_links_top_k = tuple(dict(item) for item in self.hotspot_links_top_k)
        self.ui_packet_counts = {str(k): int(v) for k, v in dict(self.ui_packet_counts).items()}


def build_baseline_run_summary(
    state: SimulationState,
    *,
    ui_packet_counts: Mapping[str, int] | None = None,
    hotspot_top_k: int = 5,
) -> BaselineRunSummary:
    """Aggregate a baseline run summary from the current simulation state."""

    normalized_ui_packet_counts = {} if ui_packet_counts is None else {
        str(k): int(v) for k, v in dict(ui_packet_counts).items()
    }
    metrics_state = state.dynamic.metrics_state if isinstance(state.dynamic.metrics_state, Mapping) else {}
    generated_total = int(metrics_state.get("generated_trip_total", 0))
    completed_total = int(metrics_state.get("completed_trips_total", 0))
    failed_total = int(metrics_state.get("failed_trips_total", 0))
    queued = int(metrics_state.get("queued_trip_requests", 0))
    pending = int(metrics_state.get("pending_trip_requests", queued))
    active_agents = int(metrics_state.get("active_agents", _alive_count_fallback(state)))
    ui_packets_emitted = (
        int(sum(normalized_ui_packet_counts.values()))
        if normalized_ui_packet_counts
        else int(metrics_state.get("ui_packets_emitted", 0))
    )
    capacity_violation_count = int(
        metrics_state.get("capacity_violation_count", _capacity_violation_count_fallback(state))
    )
    negative_queue_detected = bool(
        metrics_state.get("negative_queue_detected", _negative_queue_detected_fallback(state))
    )

    return BaselineRunSummary(
        scenario_id=str(getattr(state.static, "scenario_id", "") or "unknown"),
        seed=_extract_seed(state),
        tick_index=int(state.tick_index),
        day_type=str(state.day_type.value),
        time_band=str(state.time_band.value),
        trip_generation_total=generated_total,
        trip_completed_total=completed_total,
        trip_failed_total=failed_total,
        active_agents=active_agents,
        queued_trip_requests=queued,
        pending_trip_requests=pending,
        capacity_violation_count=capacity_violation_count,
        negative_queue_detected=negative_queue_detected,
        ui_packets_emitted=ui_packets_emitted,
        hotspot_links_top_k=_hotspot_links_top_k(state, k=hotspot_top_k),
        ui_packet_counts=normalized_ui_packet_counts,
    )


def _extract_seed(state: SimulationState) -> int | None:
    for container in (state.metadata, getattr(state.static, "metadata", {}), getattr(state.dynamic, "metadata", {})):
        if isinstance(container, Mapping) and "scenario_seed" in container:
            try:
                return int(container["scenario_seed"])
            except Exception:
                continue
    return None


def _alive_count_fallback(state: SimulationState) -> int:
    pool = state.dynamic.active_agent_pool
    return int(getattr(pool, "alive_count", 0) or 0)


def _capacity_violation_count_fallback(state: SimulationState) -> int:
    link_state = state.dynamic.flow_link_state
    if isinstance(link_state, LinkState):
        return int(link_state.capacity_violation_count)
    return 0


def _negative_queue_detected_fallback(state: SimulationState) -> bool:
    invariant_state = state.dynamic.invariant_state
    counters = getattr(invariant_state, "counters", None)
    try:
        return int(getattr(counters, "negative_queue_violations", 0) or 0) > 0
    except Exception:
        return False


def _hotspot_links_top_k(state: SimulationState, *, k: int) -> tuple[dict[str, Any], ...]:
    k = max(0, int(k))
    if k == 0:
        return ()
    link_state = state.dynamic.flow_link_state
    routing_static = state.static.routing_static if isinstance(state.static.routing_static, Mapping) else {}
    road_csr = routing_static.get("road_csr")
    if not isinstance(link_state, LinkState) or road_csr is None:
        return ()
    links = getattr(road_csr, "links", None)
    if links is None:
        return ()
    try:
        link_count = int(link_state.link_count)
        if len(links) != link_count or link_count <= 0:
            return ()
    except Exception:
        return ()

    queue = np.asarray(link_state.queue_vehicles, dtype=np.float32)
    cap = np.asarray(link_state.effective_capacity_vehicles, dtype=np.float32)
    congestion = queue / np.maximum(cap, 1e-6)
    if k >= link_count:
        order = np.argsort(-congestion, kind="stable")[:k]
    else:
        cand = np.argpartition(-congestion, kth=(k - 1))[:k]
        order = cand[np.argsort(-congestion[cand], kind="stable")]
    order_arr = np.asarray(order, dtype=np.int32)
    cost = np.asarray(link_state.travel_time_cost[order_arr], dtype=np.float32)
    free_cost_src = link_state.metadata.get("free_flow_travel_time_cost", link_state.travel_time_cost)
    try:
        free_cost = np.asarray(free_cost_src[order_arr], dtype=np.float32)
        if free_cost.shape != cost.shape:
            free_cost = cost
    except Exception:
        free_cost = cost
    slowdown = cost / np.maximum(free_cost, 1e-6)
    queue_sel = queue[order_arr]
    congestion_sel = congestion[order_arr]
    out: list[dict[str, Any]] = []
    for pos, idx in enumerate(order.tolist()):
        link = links[int(idx)]
        out.append(
            {
                "link_id": int(link.link_id),
                "road_class": str(getattr(link.road_class, "value", link.road_class)),
                "queue_vehicles": float(queue_sel[pos]),
                "congestion_ratio": float(congestion_sel[pos]),
                "travel_time_ratio": float(slowdown[pos]),
            }
        )
    return tuple(out)
