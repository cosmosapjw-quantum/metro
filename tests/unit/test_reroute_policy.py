from __future__ import annotations

import pytest

from metroflow.routing.behavior_profiles import RouteChoiceProfile
from metroflow.routing.reroute_policy import (
    RerouteDecisionReason,
    compute_reroute_trigger_score,
    decide_reroute_vs_persist,
)


def test_reroute_policy_triggers_reroute_for_high_willingness_and_strong_improvement():
    profile = RouteChoiceProfile(
        behavior_profile_id=1,
        delay_sensitivity=1.8,
        reroute_willingness=0.95,
        persistence_bias=0.2,
        exploration_bias=0.4,
    )
    decision = decide_reroute_vs_persist(
        profile=profile,
        current_remaining_cost=10.0,
        candidate_remaining_cost=6.0,
        incident_active=True,
        reroute_cooldown_ticks=0,
    )

    assert decision.should_reroute is True
    assert decision.reason is RerouteDecisionReason.REROUTE
    assert decision.improvement_ratio == pytest.approx(0.4)
    assert decision.next_reroute_cooldown_ticks >= 1


def test_reroute_policy_persists_when_on_cooldown_even_if_better_route_exists():
    profile = RouteChoiceProfile(
        behavior_profile_id=2,
        delay_sensitivity=1.0,
        reroute_willingness=0.9,
        persistence_bias=0.0,
        exploration_bias=0.2,
    )
    decision = decide_reroute_vs_persist(
        profile=profile,
        current_remaining_cost=12.0,
        candidate_remaining_cost=6.0,
        incident_active=True,
        reroute_cooldown_ticks=2,
    )

    assert decision.should_reroute is False
    assert decision.reason is RerouteDecisionReason.COOLDOWN
    assert decision.next_reroute_cooldown_ticks == 1


def test_reroute_policy_rejects_invalid_costs_and_non_finite_profile_fields():
    valid_profile = RouteChoiceProfile(
        behavior_profile_id=3,
        delay_sensitivity=1.0,
        reroute_willingness=0.7,
        persistence_bias=0.4,
        exploration_bias=0.2,
    )
    decision = decide_reroute_vs_persist(
        profile=valid_profile,
        current_remaining_cost=float("inf"),
        candidate_remaining_cost=5.0,
    )
    assert decision.should_reroute is False
    assert decision.reason is RerouteDecisionReason.INVALID_COSTS

    bad_profile = {
        "behavior_profile_id": 4,
        "delay_sensitivity": float("nan"),
        "reroute_willingness": 0.5,
        "persistence_bias": 0.5,
        "exploration_bias": 0.1,
    }
    with pytest.raises(ValueError, match="finite"):
        compute_reroute_trigger_score(profile=bad_profile, improvement_ratio=0.2)
    with pytest.raises(ValueError, match="improvement_ratio"):
        compute_reroute_trigger_score(profile=valid_profile, improvement_ratio=float("nan"))


def test_reroute_policy_no_incident_preserves_cooldown_by_default_and_can_decay():
    profile = RouteChoiceProfile(
        behavior_profile_id=5,
        delay_sensitivity=1.0,
        reroute_willingness=0.8,
        persistence_bias=0.3,
        exploration_bias=0.2,
    )
    keep = decide_reroute_vs_persist(
        profile=profile,
        current_remaining_cost=10.0,
        candidate_remaining_cost=8.0,
        incident_active=False,
        reroute_cooldown_ticks=3,
    )
    decay = decide_reroute_vs_persist(
        profile=profile,
        current_remaining_cost=10.0,
        candidate_remaining_cost=8.0,
        incident_active=False,
        reroute_cooldown_ticks=3,
        decay_cooldown_when_no_incident=True,
    )

    assert keep.reason is RerouteDecisionReason.NO_INCIDENT
    assert keep.next_reroute_cooldown_ticks == 3
    assert decay.reason is RerouteDecisionReason.NO_INCIDENT
    assert decay.next_reroute_cooldown_ticks == 2
