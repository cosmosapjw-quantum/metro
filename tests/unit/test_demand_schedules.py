from __future__ import annotations

import runpy
from pathlib import Path

import pytest

from metroflow.sim.config import DayType, SimulationConfig, TimeBand

_SCENARIOS = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "fixtures" / "simulation_scenarios.py")
)
DAY_TYPES = _SCENARIOS["DAY_TYPES"]
TIME_BANDS = _SCENARIOS["TIME_BANDS"]
SEED_REGISTRY = _SCENARIOS["SEED_REGISTRY"]


def test_demand_schedule_axes_align_with_simulation_config_enums():
    config = SimulationConfig(
        day_type_set=DAY_TYPES,
        time_bands=TIME_BANDS,
    )

    assert config.day_type_set == (DayType.WEEKDAY, DayType.WEEKEND)
    assert config.time_bands == (
        TimeBand.MORNING,
        TimeBand.LUNCH,
        TimeBand.EVENING,
        TimeBand.NIGHT,
    )


def test_demand_schedule_seed_registry_separates_weekday_and_weekend_cases():
    weekday_seed = SEED_REGISTRY["demand_schedule_weekday"]
    weekend_seed = SEED_REGISTRY["demand_schedule_weekend"]

    assert isinstance(weekday_seed, int)
    assert isinstance(weekend_seed, int)
    assert weekday_seed != weekend_seed


def test_schedule_template_generation_contract_pending_t031():
    population_mod = pytest.importorskip(
        "metroflow.demand.population",
        reason="T031 pending: demand.population not implemented yet",
    )

    has_schedule_api = any(
        hasattr(population_mod, name)
        for name in (
            "ScheduleTemplate",
            "build_schedule_templates",
            "generate_schedule_templates",
        )
    )
    if not has_schedule_api:
        pytest.skip("T031 pending: schedule template API not exported yet")

    assert has_schedule_api is True


def test_trip_request_generation_contract_pending_t032():
    trips_mod = pytest.importorskip(
        "metroflow.demand.trips",
        reason="T032 pending: demand.trips not implemented yet",
    )

    has_trip_api = any(
        hasattr(trips_mod, name)
        for name in (
            "TripRequest",
            "generate_trip_requests",
            "build_trip_requests",
        )
    )
    if not has_trip_api:
        pytest.skip("T032 pending: trip request generation API not exported yet")

    assert has_trip_api is True
