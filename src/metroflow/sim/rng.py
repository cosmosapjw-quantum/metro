"""PRNG seed/key helpers for reproducible JAX-based simulation flows."""

from __future__ import annotations

import hashlib
from typing import Final

import jax
from jax import random

__all__ = [
    "PRNGKeyArray",
    "normalize_seed",
    "key_from_seed",
    "split_keys",
    "next_key",
    "fold_in_u32",
    "fold_in_path",
]

PRNGKeyArray = jax.Array
_UINT32_MASK: Final[int] = 0xFFFFFFFF


def normalize_seed(seed: int) -> int:
    """Normalize any Python int into the unsigned 32-bit range used by JAX keys."""

    return int(seed) & _UINT32_MASK


def key_from_seed(seed: int) -> PRNGKeyArray:
    """Create a JAX PRNG key from a normalized seed."""

    return random.PRNGKey(normalize_seed(seed))


def split_keys(key: PRNGKeyArray, num: int = 2) -> tuple[PRNGKeyArray, ...]:
    """Split a PRNG key into `num` deterministic subkeys."""

    if num < 1:
        raise ValueError("num must be >= 1")
    return tuple(random.split(key, num))


def next_key(key: PRNGKeyArray) -> tuple[PRNGKeyArray, PRNGKeyArray]:
    """Return `(next_state_key, use_now_subkey)` for sequential RNG consumption."""

    next_state_key, use_now_subkey = random.split(key, 2)
    return next_state_key, use_now_subkey


def fold_in_u32(key: PRNGKeyArray, value: int) -> PRNGKeyArray:
    """Fold an integer token into a PRNG key using deterministic uint32 coercion."""

    return random.fold_in(key, normalize_seed(value))


def fold_in_path(key: PRNGKeyArray, *parts: int | str) -> PRNGKeyArray:
    """Fold a sequence of stable tokens into a PRNG key.

    String tokens are converted with a deterministic 32-bit hash (not Python's
    process-randomized `hash()`), so the result is reproducible across runs.
    """

    out = key
    for part in parts:
        token = _stable_token_u32(part)
        out = random.fold_in(out, token)
    return out


def _stable_token_u32(part: int | str) -> int:
    if isinstance(part, int):
        return normalize_seed(part)
    digest = hashlib.blake2s(part.encode("utf-8"), digest_size=4).digest()
    return int.from_bytes(digest, byteorder="little", signed=False)
