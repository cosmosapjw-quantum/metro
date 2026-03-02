from __future__ import annotations

import jax
import jax.numpy as jnp
import pytest

from metroflow.learning.policy_blend import PolicyBlendFallbackReason, PolicyBlendState
from metroflow.routing.policy_mixer import (
    mix_route_candidate_scores,
    mix_route_candidate_scores_core,
    normalize_route_preference_scores_core,
    select_mixed_route_index,
    select_mixed_route_index_core,
)
from metroflow.sim.config import LearningMixBounds


def test_policy_mixer_blends_cost_baseline_with_reward_adaptive_scores():
    result = mix_route_candidate_scores(
        baseline_scores=(5.0, 2.0, 3.0),
        adaptive_scores=(0.1, 0.2, 0.9),
        blend_state=PolicyBlendState(lambda_mix=0.0, baseline_only_mode=True),
        target_lambda=0.5,
        bounds=LearningMixBounds(lambda_min=0.0, lambda_max=1.0),
        learning_enabled=True,
    )

    assert tuple(round(float(x), 6) for x in result.mixed_scores) == (0.0, 0.5625, 0.833333)
    assert result.selected_index == 2
    assert result.blend_state.baseline_only_mode is False
    assert result.blend_state.fallback_triggered is False


def test_policy_mixer_falls_back_on_invalid_adaptive_output():
    result = mix_route_candidate_scores(
        baseline_scores=(5.0, 2.0, 3.0),
        adaptive_scores=(1.0, float("nan"), 6.0),
        blend_state=PolicyBlendState(lambda_mix=0.2, baseline_only_mode=False),
        target_lambda=0.4,
        bounds=LearningMixBounds(lambda_min=0.0, lambda_max=1.0),
        learning_enabled=True,
    )

    assert tuple(round(float(x), 6) for x in result.mixed_scores) == (0.0, 1.0, 0.666667)
    assert result.selected_index == 1
    assert result.blend_state.fallback_triggered is True
    assert result.blend_state.fallback_reason == PolicyBlendFallbackReason.INVALID_OUTPUT
    assert result.blend_state.baseline_only_mode is True


def test_policy_mixer_falls_back_on_shape_mismatch_and_records_reason():
    result = mix_route_candidate_scores(
        baseline_scores=(5.0, 2.0, 3.0),
        adaptive_scores=(0.8, 0.1),
        blend_state=PolicyBlendState(lambda_mix=0.2, baseline_only_mode=False),
        target_lambda=0.4,
        bounds=LearningMixBounds(lambda_min=0.0, lambda_max=1.0),
        learning_enabled=True,
    )

    assert tuple(round(float(x), 6) for x in result.mixed_scores) == (0.0, 1.0, 0.666667)
    assert result.selected_index == 1
    assert result.blend_state.fallback_triggered is True
    assert result.blend_state.fallback_reason == PolicyBlendFallbackReason.INVALID_OUTPUT


def test_select_mixed_route_index_handles_empty_and_invalid_inputs():
    assert select_mixed_route_index(()) is None

    with pytest.raises(ValueError):
        select_mixed_route_index((1.0, float("inf")))


def test_policy_mixer_handles_empty_candidate_set_without_reduction_error():
    result = mix_route_candidate_scores(
        baseline_scores=(),
        adaptive_scores=(),
        blend_state=PolicyBlendState(lambda_mix=0.3, baseline_only_mode=False),
        target_lambda=0.3,
        bounds=LearningMixBounds(lambda_min=0.0, lambda_max=1.0),
        learning_enabled=True,
    )

    assert tuple(float(x) for x in result.mixed_scores) == ()
    assert result.selected_index is None


def test_policy_mixer_core_is_jittable_after_preference_normalization():
    compiled = jax.jit(
        lambda baseline, adaptive: mix_route_candidate_scores_core(
            baseline_preferences=normalize_route_preference_scores_core(
                baseline,
                prefer_higher=False,
            ),
            adaptive_preferences=normalize_route_preference_scores_core(
                adaptive,
                prefer_higher=True,
            ),
            blend_state=PolicyBlendState(lambda_mix=0.5, baseline_only_mode=False),
        )
    )
    mixed = compiled(
        jnp.asarray((5.0, 2.0, 3.0), dtype=jnp.float32),
        jnp.asarray((0.1, 0.2, 0.9), dtype=jnp.float32),
    )
    selected = select_mixed_route_index_core(mixed)

    assert tuple(round(float(x), 6) for x in mixed) == (0.0, 0.5625, 0.833333)
    assert int(selected) == 2
