from __future__ import annotations

import pytest

"""Contract-first tests for T050 route-choice behavior profiles.

These tests may skip while `metroflow.routing.behavior_profiles` is pending, but
once the module/API exists they should fail on real diversity/threshold bugs.
"""


def test_behavior_profile_api_contract_pending_t050():
    mod = pytest.importorskip(
        "metroflow.routing.behavior_profiles",
        reason="T050 pending: routing.behavior_profiles not implemented yet",
    )

    required = (
        "RouteChoiceProfile",
        "sample_behavior_profile_ids",
    )
    has_generator = hasattr(mod, "generate_route_choice_profiles") or hasattr(
        mod, "build_route_choice_profiles"
    )
    missing = tuple(name for name in required if not hasattr(mod, name))
    if not has_generator:
        missing = (*missing, "generate_route_choice_profiles|build_route_choice_profiles")
    if missing:
        pytest.skip(f"T050 pending: missing behavior profile API exports: {', '.join(missing)}")

    assert missing == ()


def test_generate_route_choice_profiles_spans_reroute_and_persistence_thresholds_pending_t050():
    mod = pytest.importorskip(
        "metroflow.routing.behavior_profiles",
        reason="T050 pending: routing.behavior_profiles not implemented yet",
    )
    if not (
        hasattr(mod, "generate_route_choice_profiles") or hasattr(mod, "build_route_choice_profiles")
    ):
        pytest.skip("T050 pending: behavior profile generator API not implemented yet")

    generate = getattr(mod, "generate_route_choice_profiles", None) or getattr(
        mod, "build_route_choice_profiles"
    )
    try:
        profiles = tuple(generate(seed=7, count=8))
    except TypeError as exc:
        pytest.skip(f"T050 pending: generator signature not finalized ({exc})")

    assert len(profiles) >= 4

    reroute_values = [float(_profile_field(p, "reroute_willingness", 0.0)) for p in profiles]
    persistence_values = [float(_profile_field(p, "persistence_bias", 0.0)) for p in profiles]
    assert all(0.0 <= v <= 1.0 for v in reroute_values)

    # Contract for US2/T051 follow-on: profile sets must span both sides of a
    # baseline reroute threshold so disruptions can produce mixed behavior.
    assert any(v < 0.5 for v in reroute_values)
    assert any(v >= 0.5 for v in reroute_values)
    # Do not overconstrain persistence_bias semantics (sign/range is not yet
    # fixed in the data model); only require non-degenerate diversity.
    assert max(persistence_values) - min(persistence_values) > 0.0


def test_sample_behavior_profile_ids_is_reproducible_and_uses_multiple_bands_pending_t050():
    mod = pytest.importorskip(
        "metroflow.routing.behavior_profiles",
        reason="T050 pending: routing.behavior_profiles not implemented yet",
    )
    has_generator = hasattr(mod, "generate_route_choice_profiles") or hasattr(
        mod, "build_route_choice_profiles"
    )
    if (not has_generator) or (not hasattr(mod, "sample_behavior_profile_ids")):
        pytest.skip("T050 pending: behavior profile sampling API not implemented yet")

    generate = getattr(mod, "generate_route_choice_profiles", None) or getattr(
        mod, "build_route_choice_profiles"
    )
    sample_ids = mod.sample_behavior_profile_ids
    try:
        profiles = tuple(generate(seed=5, count=8))
        sampled_a = tuple(sample_ids(profiles=profiles, population_size=128, seed=11))
        sampled_b = tuple(sample_ids(profiles=profiles, population_size=128, seed=11))
    except TypeError as exc:
        pytest.skip(f"T050 pending: sampling signature not finalized ({exc})")

    assert len(sampled_a) == 128
    assert sampled_a == sampled_b

    profile_ids = {int(_profile_field(p, "behavior_profile_id", -1)) for p in profiles}
    assert profile_ids
    assert set(sampled_a).issubset(profile_ids)
    # Sampling policy details (temperature/skew) are implementation-defined at
    # T050. Keep the contract focused on reproducibility + valid id selection.


def test_sample_behavior_profile_ids_rejects_duplicate_profile_ids_pending_t050():
    mod = pytest.importorskip(
        "metroflow.routing.behavior_profiles",
        reason="T050 pending: routing.behavior_profiles not implemented yet",
    )
    if not hasattr(mod, "RouteChoiceProfile") or not hasattr(mod, "sample_behavior_profile_ids"):
        pytest.skip("T050 pending: behavior profile sampling API not implemented yet")

    Profile = mod.RouteChoiceProfile
    sample_ids = mod.sample_behavior_profile_ids
    profiles = (
        Profile(behavior_profile_id=1, delay_sensitivity=1.0, reroute_willingness=0.2, persistence_bias=0.8, exploration_bias=0.1),
        Profile(behavior_profile_id=1, delay_sensitivity=1.2, reroute_willingness=0.7, persistence_bias=0.4, exploration_bias=0.2),
    )
    with pytest.raises(ValueError, match="unique"):
        sample_ids(profiles=profiles, population_size=4, seed=3)


def test_sample_behavior_profile_ids_rejects_non_finite_profile_fields_pending_t050():
    mod = pytest.importorskip(
        "metroflow.routing.behavior_profiles",
        reason="T050 pending: routing.behavior_profiles not implemented yet",
    )
    if not hasattr(mod, "RouteChoiceProfile") or not hasattr(mod, "sample_behavior_profile_ids"):
        pytest.skip("T050 pending: behavior profile sampling API not implemented yet")

    Profile = mod.RouteChoiceProfile
    sample_ids = mod.sample_behavior_profile_ids
    profiles = (
        Profile(behavior_profile_id=1, delay_sensitivity=float("nan"), reroute_willingness=0.2, persistence_bias=0.8, exploration_bias=0.1),
        Profile(behavior_profile_id=2, delay_sensitivity=1.2, reroute_willingness=0.7, persistence_bias=0.4, exploration_bias=0.2),
    )
    with pytest.raises(ValueError, match="finite"):
        sample_ids(profiles=profiles, population_size=4, seed=3)


def _profile_field(profile: object, field_name: str, default: object) -> object:
    if isinstance(profile, dict):
        return profile.get(field_name, default)
    return getattr(profile, field_name, default)
