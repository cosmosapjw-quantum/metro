"""Zoning and POI placement generation for synthetic city topologies."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, Iterator

from metroflow.city.generator import SyntheticCityTopology
from metroflow.city.graph import Node
from metroflow.sim.config import CityGenerationConfig, ZoneType

__all__ = [
    "POIType",
    "Zone",
    "POI",
    "ZoningPlacementResult",
    "generate_zones_and_pois",
    "build_zones_and_pois",
]


class StrEnum(str, Enum):
    """Local string enum base."""


class POIType(StrEnum):
    HOME = "home"
    WORKPLACE = "workplace"
    LEISURE = "leisure"


@dataclass(slots=True)
class Zone:
    """Land-use zone with aggregate capacities used by demand generation."""

    zone_id: int
    zone_type: ZoneType | str
    centroid_x: float
    centroid_y: float
    population_capacity: int = 0
    job_capacity: int = 0
    leisure_capacity: int = 0

    def __post_init__(self) -> None:
        self.zone_id = int(self.zone_id)
        self.zone_type = ZoneType(self.zone_type)
        self.centroid_x = float(self.centroid_x)
        self.centroid_y = float(self.centroid_y)
        self.population_capacity = int(self.population_capacity)
        self.job_capacity = int(self.job_capacity)
        self.leisure_capacity = int(self.leisure_capacity)
        if self.population_capacity < 0:
            raise ValueError("Zone population_capacity must be >= 0")
        if self.job_capacity < 0:
            raise ValueError("Zone job_capacity must be >= 0")
        if self.leisure_capacity < 0:
            raise ValueError("Zone leisure_capacity must be >= 0")


@dataclass(slots=True)
class POI:
    """Point of interest anchored to a zone and nearest access node."""

    poi_id: int
    zone_id: int
    poi_type: POIType | str
    node_id: int
    capacity_hint: int = 0

    def __post_init__(self) -> None:
        self.poi_id = int(self.poi_id)
        self.zone_id = int(self.zone_id)
        self.poi_type = POIType(self.poi_type)
        self.node_id = int(self.node_id)
        self.capacity_hint = int(self.capacity_hint)
        if self.capacity_hint < 0:
            raise ValueError("POI capacity_hint must be >= 0")


@dataclass(slots=True)
class ZoningPlacementResult:
    """Output container for zone and POI generation from a static topology."""

    zones: tuple[Zone, ...]
    pois: tuple[POI, ...]
    node_zone_by_id: dict[int, int] = field(default_factory=dict)
    zone_node_ids: dict[int, tuple[int, ...]] = field(default_factory=dict)
    metadata: dict[str, int | str | float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.zones = tuple(self.zones)
        self.pois = tuple(self.pois)
        self.node_zone_by_id = {int(k): int(v) for k, v in dict(self.node_zone_by_id).items()}
        self.zone_node_ids = {
            int(zone_id): tuple(int(node_id) for node_id in node_ids)
            for zone_id, node_ids in dict(self.zone_node_ids).items()
        }
        if not isinstance(self.metadata, dict):
            self.metadata = dict(self.metadata)

    def validate(
        self,
        *,
        topology: SyntheticCityTopology | None = None,
    ) -> tuple[str, ...]:
        """Return validation issues (empty tuple means valid)."""

        issues: list[str] = []
        zone_ids = [zone.zone_id for zone in self.zones]
        if len(set(zone_ids)) != len(zone_ids):
            issues.append("duplicate zone_id values")
        if set(zone.zone_type for zone in self.zones) != set(ZoneType):
            issues.append("zones must include all four zone types")

        zone_id_set = set(zone_ids)
        node_id_set = None
        if topology is not None:
            node_id_set = {node.node_id for node in topology.nodes}

        if set(self.zone_node_ids) != zone_id_set:
            issues.append("zone_node_ids keys must match zone ids")
        inverse_from_zone_nodes: dict[int, int] = {}
        duplicate_zone_node_refs = 0
        for zone_id, node_ids in self.zone_node_ids.items():
            if len(node_ids) != len(set(node_ids)):
                issues.append(f"zone_node_ids[{zone_id}] contains duplicate node ids")
            for node_id in node_ids:
                previous_zone = inverse_from_zone_nodes.get(node_id)
                if previous_zone is not None and previous_zone != zone_id:
                    duplicate_zone_node_refs += 1
                inverse_from_zone_nodes[node_id] = zone_id
        if duplicate_zone_node_refs:
            issues.append("zone_node_ids contains nodes assigned to multiple zones")

        for poi in self.pois:
            if poi.zone_id not in zone_id_set:
                issues.append(f"poi {poi.poi_id} references missing zone_id {poi.zone_id}")
            if node_id_set is not None and poi.node_id not in node_id_set:
                issues.append(f"poi {poi.poi_id} references missing node_id {poi.node_id}")

        for node_id, zone_id in self.node_zone_by_id.items():
            if zone_id not in zone_id_set:
                issues.append(f"node_zone_by_id maps node {node_id} to missing zone_id {zone_id}")
                continue
            if inverse_from_zone_nodes.get(node_id) != zone_id:
                issues.append(
                    f"node_zone_by_id / zone_node_ids mismatch for node {node_id} (zone {zone_id})"
                )

        for node_id, zone_id in inverse_from_zone_nodes.items():
            if self.node_zone_by_id.get(node_id) != zone_id:
                issues.append(
                    f"zone_node_ids / node_zone_by_id mismatch for node {node_id} (zone {zone_id})"
                )

        if node_id_set is not None:
            missing_nodes = sorted(node_id_set - set(self.node_zone_by_id))
            if missing_nodes:
                issues.append(f"node_zone_by_id missing {len(missing_nodes)} topology nodes")
        return tuple(issues)


def generate_zones_and_pois(
    topology: SyntheticCityTopology,
    config: CityGenerationConfig | None = None,
    *,
    seed: int = 0,
    population_target: int | None = None,
    validate: bool = True,
) -> ZoningPlacementResult:
    """Generate a deterministic zoning layout and POI anchors for a city topology."""

    cfg = config if config is not None else CityGenerationConfig()
    nodes = tuple(topology.nodes)
    if not nodes:
        raise ValueError("topology.nodes must not be empty")
    if len(nodes) < 4:
        raise ValueError("topology.nodes must contain at least 4 nodes for zone placement")

    seed = int(seed)
    layout_plan = _plan_zoning_layout(
        nodes=nodes,
        cfg=cfg,
        seed=seed,
        population_target=population_target,
        topology=topology,
    )
    node_by_id = {node.node_id: node for node in nodes}
    centers = tuple(node_by_id[node_id] for node_id in layout_plan.center_node_ids)
    zone_types = layout_plan.zone_types
    zones: list[Zone] = []
    for zone_id, (zone_type, center_node) in enumerate(zip(zone_types, centers, strict=True), start=1):
        population_capacity, job_capacity, leisure_capacity = _zone_capacities_for_type(
            zone_type=zone_type,
            share=float(cfg.zone_mix_targets[zone_type]),
            population_target=layout_plan.population_target,
        )
        zones.append(
            Zone(
                zone_id=zone_id,
                zone_type=zone_type,
                centroid_x=center_node.x,
                centroid_y=center_node.y,
                population_capacity=population_capacity,
                job_capacity=job_capacity,
                leisure_capacity=leisure_capacity,
            )
        )

    center_by_zone_id = {
        zone.zone_id: (zone.centroid_x, zone.centroid_y)
        for zone in zones
    }

    node_zone_by_id: dict[int, int] = {}
    zone_node_lists: dict[int, list[int]] = {zone.zone_id: [] for zone in zones}
    for node in nodes:
        zone_id = _nearest_zone_id(node, center_by_zone_id)
        node_zone_by_id[node.node_id] = zone_id
        zone_node_lists[zone_id].append(node.node_id)

    # Ensure each zone has at least one node anchor by assigning its center node.
    center_node_ids = [center.node_id for center in centers]
    for zone, center_node_id in zip(zones, center_node_ids, strict=True):
        if center_node_id not in zone_node_lists[zone.zone_id]:
            previous_zone = node_zone_by_id.get(center_node_id)
            if previous_zone is not None and center_node_id in zone_node_lists[previous_zone]:
                zone_node_lists[previous_zone].remove(center_node_id)
            zone_node_lists[zone.zone_id].append(center_node_id)
            node_zone_by_id[center_node_id] = zone.zone_id

    zone_node_ids = {
        zone_id: tuple(sorted(node_ids)) if node_ids else ()
        for zone_id, node_ids in zone_node_lists.items()
    }

    pois = _generate_pois(
        zones=tuple(zones),
        zone_node_ids=zone_node_ids,
        poi_density_profile=cfg.poi_density_profile,
        seed=seed,
    )

    result = ZoningPlacementResult(
        zones=tuple(zones),
        pois=pois,
        node_zone_by_id=node_zone_by_id,
        zone_node_ids=zone_node_ids,
        metadata={
            "seed": seed,
            "zone_count": len(zones),
            "poi_count": len(pois),
            "poi_density_profile": cfg.poi_density_profile,
            "population_target": layout_plan.population_target,
        },
    )
    if validate:
        issues = result.validate(topology=topology)
        if issues:
            raise ValueError("Invalid zoning/POI placement: " + "; ".join(issues))
    return result


def build_zones_and_pois(
    topology: SyntheticCityTopology,
    config: CityGenerationConfig | None = None,
    *,
    seed: int = 0,
    population_target: int | None = None,
    validate: bool = True,
) -> ZoningPlacementResult:
    """Alias for `generate_zones_and_pois`."""

    return generate_zones_and_pois(
        topology,
        config=config,
        seed=seed,
        population_target=population_target,
        validate=validate,
    )


@dataclass(slots=True)
class _ZoningLayoutPlan:
    center_node_ids: tuple[int, int, int, int]
    zone_types: tuple[ZoneType, ZoneType, ZoneType, ZoneType]
    population_target: int


def _plan_zoning_layout(
    *,
    nodes: tuple[Node, ...],
    cfg: CityGenerationConfig,
    seed: int,
    population_target: int | None,
    topology: SyntheticCityTopology,
) -> _ZoningLayoutPlan:
    """Plan zoning IDs/types before object materialization (JAX-portable boundary)."""

    centers = _choose_zone_centers(nodes, seed=seed)
    return _ZoningLayoutPlan(
        center_node_ids=tuple(node.node_id for node in centers),  # type: ignore[arg-type]
        zone_types=_zone_types_by_center_order(),
        population_target=_resolve_population_target(
            population_target=population_target,
            topology=topology,
        ),
    )


def _choose_zone_centers(nodes: tuple[Node, ...], *, seed: int) -> tuple[Node, Node, Node, Node]:
    west = min(nodes, key=lambda node: (node.x, node.y, node.node_id))
    east = min(nodes, key=lambda node: (-node.x, node.y, node.node_id))
    north = min(nodes, key=lambda node: (-node.y, node.x, node.node_id))
    south = min(nodes, key=lambda node: (node.y, node.x, node.node_id))
    central = min(
        nodes,
        key=lambda node: (abs(node.x) + abs(node.y), abs(node.x), abs(node.y), node.node_id),
    )
    far = min(nodes, key=lambda node: (-(abs(node.x) + abs(node.y)), node.node_id))

    candidates = [central, west, east, north, south, far]
    # Deterministic de-dup preserving order, then rotate by seed for mild variety.
    unique: list[Node] = []
    seen: set[int] = set()
    for node in candidates + list(nodes):
        if node.node_id in seen:
            continue
        unique.append(node)
        seen.add(node.node_id)
        if len(unique) >= 4 + (seed % 3):
            # collect a small seed-dependent prefix then stop
            break
    if len(unique) < 4:
        unique = []
        seen.clear()
        for node in nodes:
            if node.node_id in seen:
                continue
            unique.append(node)
            seen.add(node.node_id)
            if len(unique) == 4:
                break

    rotation = seed % len(unique)
    rotated = unique[rotation:] + unique[:rotation]
    # Pick four distinct centers and sort by x,y for stable mapping.
    selected = tuple(sorted(rotated[:4], key=lambda node: (node.x, node.y, node.node_id)))
    return selected  # type: ignore[return-value]


def _zone_types_by_center_order() -> tuple[ZoneType, ZoneType, ZoneType, ZoneType]:
    """Return canonical zone ordering used for stable zone IDs across seeds/runs."""

    return (
        ZoneType.RESIDENTIAL,
        ZoneType.CBD_COMMERCIAL,
        ZoneType.INDUSTRIAL,
        ZoneType.MIXED_USE,
    )


def _resolve_population_target(
    *,
    population_target: int | None,
    topology: SyntheticCityTopology,
) -> int:
    if population_target is not None:
        resolved = int(population_target)
    else:
        resolved = int(topology.metadata.get("population_target", 100_000))
    if resolved < 1:
        raise ValueError("population_target must be >= 1")
    return resolved


def _zone_capacities_for_type(
    *,
    zone_type: ZoneType,
    share: float,
    population_target: int,
) -> tuple[int, int, int]:
    base = max(1, int(round(population_target * share)))
    if zone_type == ZoneType.RESIDENTIAL:
        return (base, max(1, base // 5), max(1, base // 4))
    if zone_type == ZoneType.CBD_COMMERCIAL:
        return (max(1, base // 5), int(base * 2.0), max(1, base // 2))
    if zone_type == ZoneType.INDUSTRIAL:
        return (max(1, base // 8), int(base * 3.0 // 2), max(1, base // 6))
    return (max(1, int(base * 0.8)), max(1, int(base * 0.9)), max(1, int(base * 0.8)))


def _nearest_zone_id(
    node: Node,
    centers_by_zone_id: dict[int, tuple[float, float]],
) -> int:
    return min(
        centers_by_zone_id,
        key=lambda zone_id: (
            (node.x - centers_by_zone_id[zone_id][0]) ** 2
            + (node.y - centers_by_zone_id[zone_id][1]) ** 2,
            zone_id,
        ),
    )


def _generate_pois(
    *,
    zones: tuple[Zone, ...],
    zone_node_ids: dict[int, tuple[int, ...]],
    poi_density_profile: str,
    seed: int,
) -> tuple[POI, ...]:
    density = str(poi_density_profile).lower()
    poi_multiplier = {"sparse": 1, "baseline": 2, "dense": 3}.get(density, 2)
    poi_id = 1
    pois: list[POI] = []
    seed_offset = seed % 7

    for zone in zones:
        anchor_nodes = zone_node_ids.get(zone.zone_id, ())
        if not anchor_nodes:
            continue
        mix = _poi_mix_for_zone(zone.zone_type, multiplier=poi_multiplier)
        node_cycle = _cycle_nodes(anchor_nodes, offset=seed_offset + zone.zone_id)
        for poi_type, count in mix:
            for _ in range(count):
                node_id = next(node_cycle)
                capacity_hint = _poi_capacity_hint(zone, poi_type=poi_type)
                pois.append(
                    POI(
                        poi_id=poi_id,
                        zone_id=zone.zone_id,
                        poi_type=poi_type,
                        node_id=node_id,
                        capacity_hint=capacity_hint,
                    )
                )
                poi_id += 1
    return tuple(pois)


def _poi_mix_for_zone(zone_type: ZoneType, *, multiplier: int) -> tuple[tuple[POIType, int], ...]:
    if zone_type == ZoneType.RESIDENTIAL:
        return (
            (POIType.HOME, 3 * multiplier),
            (POIType.LEISURE, 1 * multiplier),
            (POIType.WORKPLACE, 1),
        )
    if zone_type == ZoneType.CBD_COMMERCIAL:
        return (
            (POIType.WORKPLACE, 4 * multiplier),
            (POIType.LEISURE, 2 * multiplier),
            (POIType.HOME, 1),
        )
    if zone_type == ZoneType.INDUSTRIAL:
        return (
            (POIType.WORKPLACE, 3 * multiplier),
            (POIType.LEISURE, 1),
            (POIType.HOME, 1),
        )
    return (
        (POIType.HOME, 2 * multiplier),
        (POIType.WORKPLACE, 2 * multiplier),
        (POIType.LEISURE, 2 * multiplier),
    )


def _poi_capacity_hint(zone: Zone, *, poi_type: POIType) -> int:
    if poi_type == POIType.HOME:
        return max(1, zone.population_capacity // 10)
    if poi_type == POIType.WORKPLACE:
        return max(1, zone.job_capacity // 10)
    return max(1, zone.leisure_capacity // 10)


def _cycle_nodes(node_ids: Iterable[int], *, offset: int = 0) -> Iterator[int]:
    ordered = tuple(int(node_id) for node_id in node_ids)
    if not ordered:
        raise ValueError("node_ids must not be empty")
    start = offset % len(ordered)
    idx = start
    while True:
        yield ordered[idx]
        idx = (idx + 1) % len(ordered)
