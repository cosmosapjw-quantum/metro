"""Routing decision mixer between baseline dynamic potential and adaptive scores."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import jax
import jax.numpy as jnp

from metroflow.learning.policy_blend import PolicyBlendState, apply_policy_blend_control
from metroflow.sim.config import LearningMixBounds

Array = jax.Array

__all__ = [
    "RoutingDecisionMixResult",
    "normalize_route_preference_scores_core",
    "mix_route_candidate_scores_core",
    "select_mixed_route_index_core",
    "mix_route_candidate_scores",
    "build_routing_decision_mix",
    "select_mixed_route_index",
    "choose_mixed_route_index",
]


@dataclass(slots=True)
class RoutingDecisionMixResult:
    """Mixed routing scores plus the blend state used to produce them."""

    mixed_scores: Array
    blend_state: PolicyBlendState
    selected_index: int | None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.mixed_scores = jnp.asarray(self.mixed_scores, dtype=jnp.float32)
        if self.mixed_scores.ndim != 1:
            raise ValueError("mixed_scores must be 1-D")
        if self.selected_index is not None:
            idx = int(self.selected_index)
            if not (0 <= idx < int(self.mixed_scores.shape[0])):
                raise ValueError("selected_index out of range")
            self.selected_index = idx
        if not isinstance(self.blend_state, PolicyBlendState):
            raise TypeError("blend_state must be a PolicyBlendState")
        if not isinstance(self.metadata, dict):
            self.metadata = dict(self.metadata)


def mix_route_candidate_scores(
    baseline_scores: Array | Any,
    adaptive_scores: Array | Any | None,
    *,
    blend_state: PolicyBlendState,
    target_lambda: float | None = None,
    bounds: LearningMixBounds | None = None,
    learning_enabled: bool = True,
    incident_mode: bool = False,
    adaptive_signal_available: bool | None = None,
    adaptive_output_valid: bool | None = None,
    baseline_prefer_higher: bool = False,
    adaptive_prefer_higher: bool = True,
) -> RoutingDecisionMixResult:
    """Blend baseline/adaptive candidate scores and pick the preferred action.

    Baseline dynamic-potential outputs are cost-like by default, while the first
    adaptive implementation target (OD-UCB) is reward-like. The mixer converts
    both inputs into a common preference space where higher is better, blends in
    that space, and then selects via `argmax`.
    """

    baseline = jnp.asarray(baseline_scores, dtype=jnp.float32)
    if baseline.ndim != 1:
        raise ValueError("baseline_scores must be 1-D")
    if not bool(jnp.all(jnp.isfinite(baseline))):
        raise ValueError("baseline_scores must be finite")

    adaptive_arr = None if adaptive_scores is None else jnp.asarray(adaptive_scores, dtype=jnp.float32)
    signal_available = adaptive_signal_available if adaptive_signal_available is not None else adaptive_arr is not None
    output_valid = adaptive_output_valid if adaptive_output_valid is not None else (
        adaptive_arr is not None
        and adaptive_arr.shape == baseline.shape
        and bool(jnp.all(jnp.isfinite(adaptive_arr)))
    )
    baseline_pref = normalize_route_preference_scores_core(
        baseline,
        prefer_higher=baseline_prefer_higher,
    )
    adaptive_pref = (
        None
        if not bool(signal_available and output_valid)
        else normalize_route_preference_scores_core(
            adaptive_arr,
            prefer_higher=adaptive_prefer_higher,
        )
    )
    next_blend_state = apply_policy_blend_control(
        blend_state,
        target_lambda=target_lambda,
        bounds=bounds,
        learning_enabled=learning_enabled,
        incident_mode=incident_mode,
        adaptive_signal_available=bool(signal_available),
        adaptive_output_valid=bool(output_valid),
    )
    mixed = mix_route_candidate_scores_core(
        baseline_preferences=baseline_pref,
        adaptive_preferences=adaptive_pref,
        blend_state=next_blend_state,
    )
    selected_index = select_mixed_route_index(mixed)
    return RoutingDecisionMixResult(
        mixed_scores=mixed,
        blend_state=next_blend_state,
        selected_index=selected_index,
        metadata={
            "baseline_score_count": int(baseline.shape[0]),
            "adaptive_signal_available": bool(signal_available),
            "adaptive_output_valid": bool(output_valid),
            "baseline_prefer_higher": bool(baseline_prefer_higher),
            "adaptive_prefer_higher": bool(adaptive_prefer_higher),
        },
    )


def build_routing_decision_mix(**kwargs) -> RoutingDecisionMixResult:
    """Alias for `mix_route_candidate_scores`."""

    return mix_route_candidate_scores(**kwargs)


def normalize_route_preference_scores_core(
    scores: Array | Any,
    *,
    prefer_higher: bool,
) -> Array:
    """Map route scores/costs into a bounded preference space where higher wins."""

    arr = jnp.asarray(scores, dtype=jnp.float32)
    if arr.ndim != 1:
        raise ValueError("scores must be 1-D")
    if int(arr.shape[0]) == 0:
        return arr
    finite_mask = jnp.isfinite(arr)
    safe_arr = jnp.where(finite_mask, arr, 0.0)
    directional = safe_arr if prefer_higher else -safe_arr
    lo = jnp.min(directional)
    hi = jnp.max(directional)
    span = hi - lo
    normalized = (directional - lo) / jnp.maximum(span, jnp.asarray(1.0e-6, dtype=jnp.float32))
    stable = jnp.where(span <= 1.0e-6, jnp.ones_like(normalized), normalized)
    return jnp.where(jnp.all(finite_mask), stable, jnp.zeros_like(stable))


def mix_route_candidate_scores_core(
    *,
    baseline_preferences: Array | Any,
    adaptive_preferences: Array | Any | None,
    blend_state: PolicyBlendState,
) -> Array:
    """Array-oriented mixer on already canonicalized preference scores."""

    baseline = jnp.asarray(baseline_preferences, dtype=jnp.float32)
    if baseline.ndim != 1:
        raise ValueError("baseline_preferences must be 1-D")
    if adaptive_preferences is None or blend_state.baseline_only_mode or blend_state.lambda_mix <= 0.0:
        return baseline
    adaptive = jnp.asarray(adaptive_preferences, dtype=jnp.float32)
    if adaptive.ndim != 1:
        raise ValueError("adaptive_preferences must be 1-D")
    if adaptive.shape != baseline.shape:
        raise ValueError("adaptive_preferences must match baseline_preferences shape")
    lam = jnp.asarray(blend_state.lambda_mix, dtype=jnp.float32)
    return (1.0 - lam) * baseline + lam * adaptive


def select_mixed_route_index_core(
    mixed_scores: Array | Any,
    *,
    prefer_higher_scores: bool = True,
) -> Array:
    """Array-only route selection core for JIT/batch call sites."""

    scores = jnp.asarray(mixed_scores, dtype=jnp.float32)
    if scores.ndim != 1:
        raise ValueError("mixed_scores must be 1-D")
    if prefer_higher_scores:
        return jnp.argmax(scores)
    return jnp.argmin(scores)


def select_mixed_route_index(
    mixed_scores: Array | Any,
    *,
    prefer_higher_scores: bool = True,
) -> int | None:
    """Return the chosen route index from already mixed scores."""

    scores = jnp.asarray(mixed_scores, dtype=jnp.float32)
    if scores.ndim != 1:
        raise ValueError("mixed_scores must be 1-D")
    if int(scores.shape[0]) == 0:
        return None
    if not bool(jnp.all(jnp.isfinite(scores))):
        raise ValueError("mixed_scores must be finite")
    return int(
        select_mixed_route_index_core(
            scores,
            prefer_higher_scores=prefer_higher_scores,
        )
    )


def choose_mixed_route_index(**kwargs) -> int | None:
    """Alias for `select_mixed_route_index`."""

    return select_mixed_route_index(**kwargs)
