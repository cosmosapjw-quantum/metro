"""Synthetic city topology generator for the baseline US1 scenario."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from metroflow.city.graph import (
    BridgeCrossing,
    Node,
    NodeKind,
    RoadNetworkCSR,
    RoadClass,
    RoadLink,
    TurnMovement,
    TurnType,
    TopologyValidationReport,
    build_road_network_csr,
    validate_road_network_topology,
)
from metroflow.sim.config import CityGenerationConfig

__all__ = [
    "SyntheticCityTopology",
    "generate_synthetic_city_topology",
    "build_synthetic_city_topology",
]


@dataclass(slots=True)
class SyntheticCityTopology:
    """Generated baseline city topology (static network only; zones/POIs excluded)."""

    nodes: tuple[Node, ...]
    links: tuple[RoadLink, ...]
    turns: tuple[TurnMovement, ...]
    bridge_crossings: tuple[BridgeCrossing, ...]
    metadata: dict[str, int | str | float] = field(default_factory=dict)
    _validated: bool = False

    def validate(self) -> TopologyValidationReport:
        """Validate graph references and bridge consistency."""

        report = validate_road_network_topology(
            nodes=self.nodes,
            links=self.links,
            turns=self.turns,
            bridge_crossings=self.bridge_crossings,
        )
        self._validated = report.ok
        return report

    def build_csr(self, *, validate: bool | None = None) -> RoadNetworkCSR:
        """Build CSR adjacency for the generated topology."""

        should_validate = (not self._validated) if validate is None else bool(validate)
        return build_road_network_csr(
            nodes=self.nodes,
            links=self.links,
            turns=self.turns,
            bridge_crossings=self.bridge_crossings,
            validate=should_validate,
        )


@dataclass(slots=True)
class _SyntheticCityLayoutPlan:
    radial_count: int
    x_positions: tuple[float, ...]
    bridge_indices: tuple[int, ...]
    ramp_indices: tuple[int, ...]


def generate_synthetic_city_topology(
    config: CityGenerationConfig | None = None,
    *,
    seed: int = 0,
    validate: bool = True,
) -> SyntheticCityTopology:
    """Build a deterministic synthetic city topology with bridge/barrier/ramp structure.

    The current implementation is intentionally simple and baseline-oriented:
    it guarantees a hierarchical network (local/arterial/expressway), a barrier
    crossed by 3-5 bridge corridors, and explicit interchange/ramp node types.
    """

    cfg = config if config is not None else CityGenerationConfig()
    seed = int(seed)

    node_builder = _NodeBuilder()
    link_builder = _LinkBuilder(node_builder=node_builder)
    layout = _plan_synthetic_city_layout(cfg, seed=seed)
    radial_count = layout.radial_count
    x_positions = layout.x_positions
    bridge_indices = layout.bridge_indices

    # Row coordinates. Barrier is the horizontal band centered at y=0.
    y_local_south = -900.0
    y_arterial_south = -350.0
    y_bridge_south = -80.0
    y_bridge_north = 80.0
    y_arterial_north = 350.0
    y_ramp_split = 520.0
    y_ramp_merge = 600.0
    y_expressway = 760.0
    y_local_north = 1050.0

    south_local_nodes = tuple(
        node_builder.add(kind=NodeKind.INTERSECTION, x=x, y=y_local_south)
        for x in x_positions
    )
    south_arterial_nodes = tuple(
        node_builder.add(kind=NodeKind.INTERSECTION, x=x, y=y_arterial_south)
        for x in x_positions
    )
    north_arterial_nodes = tuple(
        node_builder.add(kind=NodeKind.INTERSECTION, x=x, y=y_arterial_north)
        for x in x_positions
    )
    north_local_nodes = tuple(
        node_builder.add(kind=NodeKind.INTERSECTION, x=x, y=y_local_north)
        for x in x_positions
    )

    # Local rows + vertical connectors (local hierarchy layer).
    _link_bidirectional_chain(
        link_builder,
        south_local_nodes,
        road_class=RoadClass.LOCAL,
        lanes=1,
        speed_mps=11.0,
        capacity=8.0,
    )
    _link_bidirectional_chain(
        link_builder,
        north_local_nodes,
        road_class=RoadClass.LOCAL,
        lanes=1,
        speed_mps=11.0,
        capacity=8.0,
    )
    for south_local, south_art, north_art, north_local in zip(
        south_local_nodes,
        south_arterial_nodes,
        north_arterial_nodes,
        north_local_nodes,
        strict=True,
    ):
        _add_bidirectional_link_pair(
            link_builder,
            south_local.node_id,
            south_art.node_id,
            road_class=RoadClass.LOCAL,
            lanes=1,
            speed_mps=10.0,
            capacity=6.0,
        )
        _add_bidirectional_link_pair(
            link_builder,
            north_art.node_id,
            north_local.node_id,
            road_class=RoadClass.LOCAL,
            lanes=1,
            speed_mps=10.0,
            capacity=6.0,
        )

    # Arterial rows + radial corridors on both sides of the barrier.
    _link_bidirectional_chain(
        link_builder,
        south_arterial_nodes,
        road_class=RoadClass.ARTERIAL,
        lanes=2,
        speed_mps=17.0,
        capacity=24.0,
    )
    _link_bidirectional_chain(
        link_builder,
        north_arterial_nodes,
        road_class=RoadClass.ARTERIAL,
        lanes=2,
        speed_mps=17.0,
        capacity=24.0,
    )
    for idx, (south_art, north_art) in enumerate(
        zip(south_arterial_nodes, north_arterial_nodes, strict=True)
    ):
        # Barrier prevents direct connection; bridge corridors below will connect selected columns.
        _add_bidirectional_link_pair(
            link_builder,
            south_art.node_id,
            south_local_nodes[idx].node_id,
            road_class=RoadClass.ARTERIAL,
            lanes=1,
            speed_mps=14.0,
            capacity=14.0,
        )
        _add_bidirectional_link_pair(
            link_builder,
            north_art.node_id,
            north_local_nodes[idx].node_id,
            road_class=RoadClass.ARTERIAL,
            lanes=1,
            speed_mps=14.0,
            capacity=14.0,
        )

    bridge_crossings: list[BridgeCrossing] = []

    for rank, radial_index in enumerate(bridge_indices, start=1):
        x = x_positions[radial_index]
        barrier_id = 1 + ((rank - 1) % cfg.barrier_count)
        barrier_offset = _barrier_band_offset(barrier_id=barrier_id, barrier_count=cfg.barrier_count)
        south_endpoint = node_builder.add(
            kind=NodeKind.BRIDGE_ENDPOINT,
            x=x,
            y=y_bridge_south + barrier_offset,
        )
        north_endpoint = node_builder.add(
            kind=NodeKind.BRIDGE_ENDPOINT,
            x=x,
            y=y_bridge_north + barrier_offset,
        )
        south_art = south_arterial_nodes[radial_index]
        north_art = north_arterial_nodes[radial_index]
        bridge_group_id = rank

        _add_bidirectional_link_pair(
            link_builder,
            south_art.node_id,
            south_endpoint.node_id,
            road_class=RoadClass.ARTERIAL,
            lanes=2,
            speed_mps=15.0,
            capacity=20.0,
        )
        _add_bidirectional_link_pair(
            link_builder,
            north_endpoint.node_id,
            north_art.node_id,
            road_class=RoadClass.ARTERIAL,
            lanes=2,
            speed_mps=15.0,
            capacity=20.0,
        )
        bridge_fwd, bridge_rev = _add_bidirectional_link_pair(
            link_builder,
            south_endpoint.node_id,
            north_endpoint.node_id,
            road_class=RoadClass.BRIDGE,
            lanes=2,
            speed_mps=18.0,
            capacity=16.0,
            bridge_group_id=bridge_group_id,
        )
        bridge_crossings.append(
            BridgeCrossing(
                bridge_group_id=bridge_group_id,
                link_ids=(bridge_fwd.link_id, bridge_rev.link_id),
                barrier_id=barrier_id,
                crossing_name=f"bridge-{bridge_group_id}",
                bottleneck_rank_hint=rank,
            )
        )
    # Ring roads (rectangular arterial loops) around the barrier.
    for level in range(cfg.ring_road_count):
        inset = (level + 1) * 180.0
        min_x = x_positions[0] - 350.0 - inset
        max_x = x_positions[-1] + 350.0 + inset
        south_y = y_arterial_south - 250.0 - inset
        north_y = y_arterial_north + 250.0 + inset
        ring_nodes = (
            node_builder.add(kind=NodeKind.INTERSECTION, x=min_x, y=south_y),
            node_builder.add(kind=NodeKind.INTERSECTION, x=max_x, y=south_y),
            node_builder.add(kind=NodeKind.INTERSECTION, x=max_x, y=north_y),
            node_builder.add(kind=NodeKind.INTERSECTION, x=min_x, y=north_y),
        )
        _link_bidirectional_cycle(
            link_builder,
            ring_nodes,
            road_class=RoadClass.ARTERIAL,
            lanes=2,
            speed_mps=16.0,
            capacity=20.0,
        )

        _add_bidirectional_link_pair(
            link_builder,
            ring_nodes[0].node_id,
            south_arterial_nodes[0].node_id,
            road_class=RoadClass.ARTERIAL,
            lanes=1,
            speed_mps=14.0,
            capacity=14.0,
        )
        _add_bidirectional_link_pair(
            link_builder,
            ring_nodes[1].node_id,
            south_arterial_nodes[-1].node_id,
            road_class=RoadClass.ARTERIAL,
            lanes=1,
            speed_mps=14.0,
            capacity=14.0,
        )
        _add_bidirectional_link_pair(
            link_builder,
            ring_nodes[2].node_id,
            north_arterial_nodes[-1].node_id,
            road_class=RoadClass.ARTERIAL,
            lanes=1,
            speed_mps=14.0,
            capacity=14.0,
        )
        _add_bidirectional_link_pair(
            link_builder,
            ring_nodes[3].node_id,
            north_arterial_nodes[0].node_id,
            road_class=RoadClass.ARTERIAL,
            lanes=1,
            speed_mps=14.0,
            capacity=14.0,
        )

    # Expressway corridor on the north side with explicit interchange + ramps.
    interchange_nodes: list[Node] = []
    for x in x_positions:
        interchange_nodes.append(node_builder.add(kind=NodeKind.INTERCHANGE, x=x, y=y_expressway))
    _link_bidirectional_chain(
        link_builder,
        tuple(interchange_nodes),
        road_class=RoadClass.EXPRESSWAY,
        lanes=3,
        speed_mps=28.0,
        capacity=40.0,
    )

    ramp_indices = layout.ramp_indices
    for radial_index in ramp_indices:
        north_art = north_arterial_nodes[radial_index]
        interchange = interchange_nodes[radial_index]
        ramp_split = node_builder.add(
            kind=NodeKind.RAMP_SPLIT,
            x=interchange.x - 35.0,
            y=y_ramp_split,
        )
        ramp_merge = node_builder.add(
            kind=NodeKind.RAMP_MERGE,
            x=interchange.x + 35.0,
            y=y_ramp_merge,
        )

        # Arterial -> expressway on-ramp (two-segment).
        _add_link(
            link_builder,
            north_art.node_id,
            ramp_split.node_id,
            road_class=RoadClass.RAMP,
            lanes=1,
            speed_mps=16.0,
            capacity=12.0,
        )
        _add_link(
            link_builder,
            ramp_split.node_id,
            interchange.node_id,
            road_class=RoadClass.RAMP,
            lanes=1,
            speed_mps=18.0,
            capacity=12.0,
        )
        # Expressway -> arterial off-ramp (two-segment).
        _add_link(
            link_builder,
            interchange.node_id,
            ramp_merge.node_id,
            road_class=RoadClass.RAMP,
            lanes=1,
            speed_mps=18.0,
            capacity=12.0,
        )
        _add_link(
            link_builder,
            ramp_merge.node_id,
            north_art.node_id,
            road_class=RoadClass.RAMP,
            lanes=1,
            speed_mps=16.0,
            capacity=12.0,
        )

    turns = _generate_turn_movements(tuple(link_builder.links))

    topology = SyntheticCityTopology(
        nodes=tuple(node_builder.nodes),
        links=tuple(link_builder.links),
        turns=turns,
        bridge_crossings=tuple(bridge_crossings),
        metadata={
            "seed": seed,
            "radial_corridor_count": radial_count,
            "bridge_count": cfg.bridge_count,
            "barrier_count": cfg.barrier_count,
            "ring_road_count": cfg.ring_road_count,
            "ramp_corridor_count": len(ramp_indices),
        },
    )
    if validate:
        report = topology.validate()
        if not report.ok:
            raise ValueError(f"Generated invalid synthetic city topology: {report.summary()}")
    else:
        topology._validated = False
    return topology


def build_synthetic_city_topology(
    config: CityGenerationConfig | None = None,
    *,
    seed: int = 0,
    validate: bool = True,
) -> SyntheticCityTopology:
    """Alias for `generate_synthetic_city_topology`."""

    return generate_synthetic_city_topology(config=config, seed=seed, validate=validate)


@dataclass(slots=True)
class _NodeBuilder:
    nodes: list[Node] = field(default_factory=list)
    node_by_id: dict[int, Node] = field(default_factory=dict)
    _next_node_id: int = 1

    def add(self, *, kind: NodeKind, x: float, y: float) -> Node:
        node = Node(node_id=self._next_node_id, kind=kind, x=x, y=y)
        self.nodes.append(node)
        self.node_by_id[node.node_id] = node
        self._next_node_id += 1
        return node


@dataclass(slots=True)
class _LinkBuilder:
    node_builder: _NodeBuilder
    links: list[RoadLink] = field(default_factory=list)
    _next_link_id: int = 1

    def add(
        self,
        *,
        src_node_id: int,
        dst_node_id: int,
        road_class: RoadClass,
        lanes: int,
        speed_mps: float,
        capacity: float,
        bridge_group_id: int | None = None,
    ) -> RoadLink:
        src_node = self.node_builder.node_by_id[src_node_id]
        dst_node = self.node_builder.node_by_id[dst_node_id]
        length_m = max(1.0, math.hypot(dst_node.x - src_node.x, dst_node.y - src_node.y))
        link = RoadLink(
            link_id=self._next_link_id,
            src_node_id=src_node_id,
            dst_node_id=dst_node_id,
            road_class=road_class,
            length_m=length_m,
            free_flow_speed_mps=speed_mps,
            capacity_veh_per_tick=capacity,
            lanes=lanes,
            bridge_group_id=bridge_group_id,
            is_blockable=(road_class != RoadClass.RAMP),
        )
        self.links.append(link)
        self._next_link_id += 1
        return link


def _add_link(
    builder: _LinkBuilder,
    src_node_id: int,
    dst_node_id: int,
    *,
    road_class: RoadClass,
    lanes: int,
    speed_mps: float,
    capacity: float,
    bridge_group_id: int | None = None,
) -> RoadLink:
    return builder.add(
        src_node_id=src_node_id,
        dst_node_id=dst_node_id,
        road_class=road_class,
        lanes=lanes,
        speed_mps=speed_mps,
        capacity=capacity,
        bridge_group_id=bridge_group_id,
    )


def _add_bidirectional_link_pair(
    builder: _LinkBuilder,
    a_node_id: int,
    b_node_id: int,
    *,
    road_class: RoadClass,
    lanes: int,
    speed_mps: float,
    capacity: float,
    bridge_group_id: int | None = None,
) -> tuple[RoadLink, RoadLink]:
    forward = _add_link(
        builder,
        a_node_id,
        b_node_id,
        road_class=road_class,
        lanes=lanes,
        speed_mps=speed_mps,
        capacity=capacity,
        bridge_group_id=bridge_group_id,
    )
    reverse = _add_link(
        builder,
        b_node_id,
        a_node_id,
        road_class=road_class,
        lanes=lanes,
        speed_mps=speed_mps,
        capacity=capacity,
        bridge_group_id=bridge_group_id,
    )
    return forward, reverse


def _link_bidirectional_chain(
    builder: _LinkBuilder,
    nodes: tuple[Node, ...],
    *,
    road_class: RoadClass,
    lanes: int,
    speed_mps: float,
    capacity: float,
) -> None:
    for left, right in zip(nodes, nodes[1:], strict=False):
        _add_bidirectional_link_pair(
            builder,
            left.node_id,
            right.node_id,
            road_class=road_class,
            lanes=lanes,
            speed_mps=speed_mps,
            capacity=capacity,
        )


def _link_bidirectional_cycle(
    builder: _LinkBuilder,
    nodes: tuple[Node, ...],
    *,
    road_class: RoadClass,
    lanes: int,
    speed_mps: float,
    capacity: float,
) -> None:
    for current, nxt in zip(nodes, nodes[1:] + nodes[:1], strict=False):
        _add_bidirectional_link_pair(
            builder,
            current.node_id,
            nxt.node_id,
            road_class=road_class,
            lanes=lanes,
            speed_mps=speed_mps,
            capacity=capacity,
        )


def _rotated_indices(total: int, *, count: int, seed: int) -> tuple[int, ...]:
    if total <= 0 or count <= 0:
        return ()
    step = max(1, total // count)
    base = list(range(0, total, step))[:count]
    rotation = seed % total
    return tuple(sorted({(index + rotation) % total for index in base})[:count])


def _barrier_band_offset(*, barrier_id: int, barrier_count: int) -> float:
    if barrier_count <= 1:
        return 0.0
    center = (barrier_count - 1) / 2.0
    # Separate multiple implicit barrier bands so `barrier_id` maps to geometry.
    return (float(barrier_id - 1) - center) * 120.0


def _ramp_corridor_count(radial_count: int, interchange_density_profile: str) -> int:
    density = str(interchange_density_profile).lower()
    if density == "low":
        factor = 0.25
    elif density == "high":
        factor = 0.75
    else:
        factor = 0.5
    return max(1, min(radial_count, int(round(radial_count * factor))))


def _plan_synthetic_city_layout(
    cfg: CityGenerationConfig,
    *,
    seed: int,
) -> _SyntheticCityLayoutPlan:
    """Plan numeric layout indices separately from object materialization.

    This keeps the generator split into a deterministic planning stage and a
    dataclass materialization stage, which is easier to port to array/JAX code.
    """

    radial_count = max(cfg.radial_corridor_count, cfg.bridge_count)
    spacing_x = 1000.0
    x_positions = tuple(i * spacing_x for i in range(radial_count))
    bridge_indices = _rotated_indices(radial_count, count=cfg.bridge_count, seed=seed)
    ramp_target_count = _ramp_corridor_count(
        radial_count=radial_count,
        interchange_density_profile=cfg.interchange_density_profile,
    )
    ramp_indices = _rotated_indices(radial_count, count=ramp_target_count, seed=seed + 17)
    return _SyntheticCityLayoutPlan(
        radial_count=radial_count,
        x_positions=x_positions,
        bridge_indices=bridge_indices,
        ramp_indices=ramp_indices,
    )


def _generate_turn_movements(
    links: tuple[RoadLink, ...],
    *,
    max_non_u_turns_per_in_link: int = 4,
) -> tuple[TurnMovement, ...]:
    incoming_by_node: dict[int, list[RoadLink]] = {}
    outgoing_by_node: dict[int, list[RoadLink]] = {}
    outgoing_by_src_dst: dict[tuple[int, int], RoadLink] = {}
    for link in links:
        outgoing_by_node.setdefault(link.src_node_id, []).append(link)
        incoming_by_node.setdefault(link.dst_node_id, []).append(link)
        outgoing_by_src_dst[(link.src_node_id, link.dst_node_id)] = link

    turns: list[TurnMovement] = []
    for node_id in sorted(set(incoming_by_node) | set(outgoing_by_node)):
        incoming = incoming_by_node.get(node_id, [])
        outgoing = outgoing_by_node.get(node_id, [])
        for in_link in incoming:
            reverse_out = outgoing_by_src_dst.get((node_id, in_link.src_node_id))
            if reverse_out is not None:
                turns.append(
                    TurnMovement(
                        from_link_id=in_link.link_id,
                        to_link_id=reverse_out.link_id,
                        turn_type=TurnType.U_TURN_FORBIDDEN,
                        base_priority=0.0,
                    )
                )

            candidates: list[tuple[tuple[float, int], RoadLink]] = []
            for out_link in outgoing:
                if reverse_out is not None and out_link.link_id == reverse_out.link_id:
                    continue
                turn_type, priority = _classify_turn(in_link, out_link)
                # Prefer higher-priority turns and deterministic link order.
                candidates.append(((-priority, out_link.link_id), out_link))

            for _, out_link in sorted(candidates, key=lambda item: item[0])[
                :max_non_u_turns_per_in_link
            ]:
                turn_type, priority = _classify_turn(in_link, out_link)
                turns.append(
                    TurnMovement(
                        from_link_id=in_link.link_id,
                        to_link_id=out_link.link_id,
                        turn_type=turn_type,
                        base_priority=priority,
                    )
                )
    return tuple(turns)


def _classify_turn(in_link: RoadLink, out_link: RoadLink) -> tuple[TurnType, float]:
    if in_link.road_class == RoadClass.RAMP and out_link.road_class != RoadClass.RAMP:
        return (TurnType.RAMP_OFF, 0.7)
    if in_link.road_class != RoadClass.RAMP and out_link.road_class == RoadClass.RAMP:
        return (TurnType.RAMP_ON, 0.7)
    if (
        in_link.road_class in (RoadClass.EXPRESSWAY, RoadClass.BRIDGE)
        or out_link.road_class in (RoadClass.EXPRESSWAY, RoadClass.BRIDGE)
    ):
        return (TurnType.THROUGH, 1.4)
    if in_link.road_class == RoadClass.ARTERIAL or out_link.road_class == RoadClass.ARTERIAL:
        return (TurnType.THROUGH, 1.0)
    return (TurnType.THROUGH, 0.8)
