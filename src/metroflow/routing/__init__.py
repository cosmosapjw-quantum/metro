"""Routing package public exports."""

from __future__ import annotations

from importlib import import_module

from metroflow.routing.dynamic_potential import (
    BaselineNextLinkScores,
    DynamicPotentialState,
    build_greedy_route_candidate,
    compute_dynamic_potential_state,
    compute_next_link_action_costs_core,
    score_legal_next_links,
)

__all__ = [
    "DynamicPotentialState",
    "BaselineNextLinkScores",
    "RouteChoiceProfile",
    "generate_route_choice_profiles",
    "build_route_choice_profiles",
    "sample_behavior_profile_ids",
    "RerouteDecisionReason",
    "RerouteDecision",
    "compute_reroute_trigger_score",
    "decide_reroute_vs_persist",
    "compute_dynamic_potential_state",
    "compute_next_link_action_costs_core",
    "score_legal_next_links",
    "build_greedy_route_candidate",
]

_LAZY_EXPORTS = {
    "RouteChoiceProfile": ("metroflow.routing.behavior_profiles", "RouteChoiceProfile"),
    "generate_route_choice_profiles": ("metroflow.routing.behavior_profiles", "generate_route_choice_profiles"),
    "build_route_choice_profiles": ("metroflow.routing.behavior_profiles", "build_route_choice_profiles"),
    "sample_behavior_profile_ids": ("metroflow.routing.behavior_profiles", "sample_behavior_profile_ids"),
    "RerouteDecisionReason": ("metroflow.routing.reroute_policy", "RerouteDecisionReason"),
    "RerouteDecision": ("metroflow.routing.reroute_policy", "RerouteDecision"),
    "compute_reroute_trigger_score": ("metroflow.routing.reroute_policy", "compute_reroute_trigger_score"),
    "decide_reroute_vs_persist": ("metroflow.routing.reroute_policy", "decide_reroute_vs_persist"),
}


def __getattr__(name: str):
    if name not in _LAZY_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = _LAZY_EXPORTS[name]
    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value

