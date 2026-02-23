from __future__ import annotations

import pytest

from metroflow.city.graph import (
    BridgeCrossing,
    Node,
    RoadClass,
    RoadLink,
    validate_road_network_topology,
)
from metroflow.sim.config import CityGenerationConfig, RoadHierarchyClass, ZoneType


def test_city_generation_config_coerces_hierarchy_and_zone_keys_to_enums():
    config = CityGenerationConfig(
        road_hierarchy_profile={
            "local": 0.6,
            "arterial": 0.3,
            "expressway": 0.1,
        },
        zone_mix_targets={
            "residential": 0.4,
            "cbd_commercial": 0.2,
            "industrial": 0.2,
            "mixed_use": 0.2,
        },
    )

    assert set(config.road_hierarchy_profile) == set(RoadHierarchyClass)
    assert set(config.zone_mix_targets) == set(ZoneType)


@pytest.mark.parametrize("bridge_count", [2, 6])
def test_city_generation_config_rejects_bridge_count_out_of_range(bridge_count: int):
    with pytest.raises(ValueError, match="bridge_count must be in \\[3, 5\\]"):
        CityGenerationConfig(bridge_count=bridge_count)


def test_city_generation_config_rejects_zone_mix_missing_zone_type():
    with pytest.raises(ValueError, match="zone_mix_targets must include all zone types"):
        CityGenerationConfig(
            zone_mix_targets={
                ZoneType.RESIDENTIAL: 0.5,
                ZoneType.CBD_COMMERCIAL: 0.2,
                ZoneType.INDUSTRIAL: 0.3,
            }
        )


def test_city_generation_config_rejects_negative_road_hierarchy_share():
    with pytest.raises(ValueError, match="road_hierarchy_profile shares must be non-negative"):
        CityGenerationConfig(
            road_hierarchy_profile={
                RoadHierarchyClass.LOCAL: 0.8,
                RoadHierarchyClass.ARTERIAL: 0.3,
                RoadHierarchyClass.EXPRESSWAY: -0.1,
            }
        )


def test_bridge_road_link_requires_bridge_group_id():
    with pytest.raises(ValueError, match="bridge_group_id is required"):
        RoadLink(
            link_id=10,
            src_node_id=1,
            dst_node_id=2,
            road_class=RoadClass.BRIDGE,
            length_m=100.0,
            free_flow_speed_mps=15.0,
            capacity_veh_per_tick=5.0,
            lanes=1,
        )


def test_topology_validator_reports_bridge_crossing_group_mismatch():
    nodes = (
        Node(node_id=1, x=0.0, y=0.0),
        Node(node_id=2, x=1.0, y=0.0),
    )
    links = (
        RoadLink(
            link_id=100,
            src_node_id=1,
            dst_node_id=2,
            road_class=RoadClass.BRIDGE,
            length_m=120.0,
            free_flow_speed_mps=12.0,
            capacity_veh_per_tick=8.0,
            lanes=2,
            bridge_group_id=7,
        ),
    )
    crossings = (
        BridgeCrossing(
            bridge_group_id=99,
            link_ids=(100,),
            barrier_id=1,
            crossing_name="north crossing",
        ),
    )

    report = validate_road_network_topology(nodes=nodes, links=links, bridge_crossings=crossings)
    assert report.ok is False
    assert any(issue.code == "bridge_crossing_group_mismatch" for issue in report.issues)

