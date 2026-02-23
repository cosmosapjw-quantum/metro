"""Shared feature-test scenario constants and seed registry."""

from __future__ import annotations

from typing import Any, Final

DEFAULT_TEST_SEED: Final[int] = 42

DAY_TYPES: Final[tuple[str, str]] = ("weekday", "weekend")
TIME_BANDS: Final[tuple[str, str, str, str]] = ("morning", "lunch", "evening", "night")

SCENARIO_IDS: Final[dict[str, str]] = {
    "smoke": "synthetic_smoke",
    "benchmark_100k": "synthetic_100k",
}

# Stable per-purpose seeds keep tests reproducible while avoiding accidental
# coupling between unrelated suites as new scenarios are added.
SEED_REGISTRY: Final[dict[str, int]] = {
    "baseline_smoke": DEFAULT_TEST_SEED,
    "city_generation": 101,
    "demand_schedule_weekday": 201,
    "demand_schedule_weekend": 202,
    "day_time_transition": 301,
    "disruption_bridge_closure": 401,
    "disruption_boundary": 402,
    "reproducibility_baseline": 501,
    "reproducibility_adaptive": 502,
    "benchmark_smoke": DEFAULT_TEST_SEED,
    "ui_stream_smoke": 601,
}


def scenario_config_overrides() -> dict[str, dict[str, Any]]:
    """Return lightweight, test-focused scenario presets for future suites."""

    return {
        "us1_baseline_weekday_morning": {
            "scenario_id": SCENARIO_IDS["benchmark_100k"],
            "seed": SEED_REGISTRY["baseline_smoke"],
            "day_type": "weekday",
            "time_band": "morning",
            "ui_stream_enabled": True,
        },
        "us1_weekend_evening_transition": {
            "scenario_id": SCENARIO_IDS["smoke"],
            "seed": SEED_REGISTRY["day_time_transition"],
            "day_type": "weekend",
            "time_band": "evening",
            "ui_stream_enabled": False,
        },
        "us2_bridge_disruption_peak": {
            "scenario_id": SCENARIO_IDS["benchmark_100k"],
            "seed": SEED_REGISTRY["disruption_bridge_closure"],
            "day_type": "weekday",
            "time_band": "evening",
            "event_profile": "bridge_closure_peak",
        },
        "us3_reproducibility_baseline": {
            "scenario_id": SCENARIO_IDS["benchmark_100k"],
            "seed": SEED_REGISTRY["reproducibility_baseline"],
            "learning_enabled": False,
        },
        "us3_reproducibility_adaptive": {
            "scenario_id": SCENARIO_IDS["benchmark_100k"],
            "seed": SEED_REGISTRY["reproducibility_adaptive"],
            "learning_enabled": True,
        },
    }
