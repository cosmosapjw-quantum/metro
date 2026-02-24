"""Route-choice behavior profile generation and sampling (US2/T050)."""

from __future__ import annotations

import math
from typing import Iterable

import jax.numpy as jnp
from jax import random as jrandom
from metroflow.sim.rng import PRNGKeyArray

from metroflow.demand.population import (
    RouteChoiceProfile,
    build_behavior_profiles as _build_behavior_profiles_from_demand,
    generate_behavior_profiles as _generate_behavior_profiles_from_demand,
)
from metroflow.sim.rng import fold_in_path, key_from_seed

__all__ = [
    "RouteChoiceProfile",
    "generate_route_choice_profiles",
    "build_route_choice_profiles",
    "sample_behavior_profile_ids",
    "sample_behavior_profile_ids_core",
]


def generate_route_choice_profiles(*, seed: int = 0, count: int = 8) -> tuple[RouteChoiceProfile, ...]:
    """Generate deterministic route-choice behavior profiles for routing logic."""

    return _generate_behavior_profiles_from_demand(seed=seed, count=count)


def build_route_choice_profiles(*, seed: int = 0, count: int = 8) -> tuple[RouteChoiceProfile, ...]:
    """Alias for `generate_route_choice_profiles`."""

    return _build_behavior_profiles_from_demand(seed=seed, count=count)


def sample_behavior_profile_ids(
    *,
    profiles: Iterable[RouteChoiceProfile],
    population_size: int,
    seed: int = 0,
) -> tuple[int, ...]:
    """Sample behavior-profile ids reproducibly for a population assignment pass."""

    profile_tuple = tuple(profiles)
    n = int(population_size)
    if n < 0:
        raise ValueError("population_size must be >= 0")
    if not profile_tuple:
        raise ValueError("profiles must not be empty")
    if n == 0:
        return ()

    profile_ids, weights = _prepare_sampling_arrays(profile_tuple)
    key = fold_in_path(key_from_seed(seed), "routing", "behavior_profiles", "sample_ids", n)
    sampled_ids = sample_behavior_profile_ids_core(
        profile_ids=profile_ids,
        weights=weights,
        population_size=n,
        key=key,
    )
    return tuple(int(v) for v in sampled_ids.tolist())


def sample_behavior_profile_ids_core(
    *,
    profile_ids: jnp.ndarray,
    weights: jnp.ndarray,
    population_size: int,
    key: PRNGKeyArray,
) -> jnp.ndarray:
    """Array-only core for behavior-profile id sampling (JAX-portable boundary)."""

    n = int(population_size)
    if n < 0:
        raise ValueError("population_size must be >= 0")
    if profile_ids.ndim != 1 or weights.ndim != 1:
        raise ValueError("profile_ids and weights must be 1-D arrays")
    if profile_ids.shape[0] != weights.shape[0]:
        raise ValueError("profile_ids and weights length mismatch")
    if profile_ids.shape[0] == 0:
        if n == 0:
            return jnp.asarray((), dtype=jnp.int32)
        raise ValueError("profile_ids must not be empty when population_size > 0")
    sampled_idx = jrandom.choice(
        key,
        a=weights.shape[0],
        shape=(int(n),),
        replace=True,
        p=weights,
    )
    return profile_ids[sampled_idx]


def _prepare_sampling_arrays(profiles: tuple[RouteChoiceProfile, ...]) -> tuple[jnp.ndarray, jnp.ndarray]:
    ids: list[int] = []
    delay_vals: list[float] = []
    reroute_vals: list[float] = []
    persist_vals: list[float] = []
    explore_vals: list[float] = []

    seen_ids: set[int] = set()
    for profile in profiles:
        profile_id = int(profile.behavior_profile_id)
        if profile_id in seen_ids:
            raise ValueError("behavior_profile_id values must be unique")
        seen_ids.add(profile_id)
        ids.append(profile_id)

        delay = float(profile.delay_sensitivity)
        reroute = float(profile.reroute_willingness)
        persist = float(profile.persistence_bias)
        explore = float(profile.exploration_bias)
        if not all(math.isfinite(v) for v in (delay, reroute, persist, explore)):
            raise ValueError("behavior profile numeric fields must be finite")
        if not 0.0 <= reroute <= 1.0:
            raise ValueError("reroute_willingness must be in [0, 1]")
        delay_vals.append(delay)
        reroute_vals.append(reroute)
        persist_vals.append(persist)
        explore_vals.append(explore)

    profile_ids = jnp.asarray(ids, dtype=jnp.int32)
    weights = _sampling_weights_from_arrays(
        delay=jnp.asarray(delay_vals, dtype=jnp.float32),
        reroute=jnp.asarray(reroute_vals, dtype=jnp.float32),
        persist=jnp.asarray(persist_vals, dtype=jnp.float32),
        explore=jnp.asarray(explore_vals, dtype=jnp.float32),
    )
    return profile_ids, weights


def _sampling_weights(profiles: tuple[RouteChoiceProfile, ...]) -> jnp.ndarray:
    _, weights = _prepare_sampling_arrays(profiles)
    return weights


def _sampling_weights_from_arrays(
    *,
    delay: jnp.ndarray,
    reroute: jnp.ndarray,
    persist: jnp.ndarray,
    explore: jnp.ndarray,
) -> jnp.ndarray:
    if not (delay.ndim == reroute.ndim == persist.ndim == explore.ndim == 1):
        raise ValueError("behavior profile arrays must be 1-D")
    if not (delay.shape == reroute.shape == persist.shape == explore.shape):
        raise ValueError("behavior profile arrays must have matching shapes")

    # Balanced nonzero weighting so all profiles remain sampleable while still
    # reflecting diversity dimensions relevant to US2 reroute behavior.
    centered_persist = jnp.abs(persist - jnp.mean(persist))
    raw = 0.25 + 0.35 * reroute + 0.15 * explore + 0.15 * centered_persist + 0.10 * (
        delay / jnp.maximum(1.0, jnp.max(delay))
    )
    raw = jnp.clip(raw, 1e-6, None)
    return raw / jnp.sum(raw)
