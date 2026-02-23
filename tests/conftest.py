"""Shared pytest fixtures for MetroFlow tests."""

from __future__ import annotations

from typing import Any

import pytest


@pytest.fixture
def default_random_seed() -> int:
    """Stable seed for reproducible tests until sim RNG helpers exist."""

    return 42


@pytest.fixture
def simulation_config_stub(default_random_seed: int) -> dict[str, Any]:
    """Minimal config-shaped payload aligned with the Phase 1 data model."""

    return {
        "population_target": 1_000,
        "tick_seconds": 1.0,
        "active_agent_capacity": 2_000,
        "random_seed": default_random_seed,
        "day_type_set": ("weekday", "weekend"),
        "time_bands": ("morning", "lunch", "evening", "night"),
        "ui_stream_enabled": False,
        "ui_stream_hz_limit": 5.0,
        "learning_enabled": False,
        "learning_mix_bounds": {"lambda_min": 0.0, "lambda_max": 0.0},
        "ctm_mode_enabled": False,
    }


@pytest.fixture
def city_generation_config_stub() -> dict[str, Any]:
    """Minimal citygen config-shaped payload aligned with the Phase 1 data model."""

    return {
        "road_hierarchy_profile": {
            "local": 0.7,
            "arterial": 0.2,
            "expressway": 0.1,
        },
        "ring_road_count": 1,
        "radial_corridor_count": 4,
        "barrier_count": 1,
        "bridge_count": 3,
        "interchange_density_profile": "medium",
        "zone_mix_targets": {
            "residential": 0.4,
            "cbd_commercial": 0.2,
            "industrial": 0.2,
            "mixed_use": 0.2,
        },
        "poi_density_profile": "baseline",
    }
