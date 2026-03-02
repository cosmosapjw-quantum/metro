from __future__ import annotations

import math
from typing import Any

import jax
import jax.numpy as jnp
import pytest

"""Contract-first unit tests for T063 OD-UCB bandit state/updates.

These tests intentionally skip while `metroflow.learning.od_ucb` is pending.
Once implemented, they should fail on real arm-selection/update regressions.
"""


def test_od_ucb_bandit_api_contract_pending_t063():
    mod = pytest.importorskip(
        "metroflow.learning.od_ucb",
        reason="T063 pending: learning.od_ucb not implemented yet",
    )

    state_type = _pick_first_existing(mod, ("ODBanditState", "OdUcbBanditState"))
    init_fn = _pick_first_existing(mod, ("create_od_ucb_state", "build_od_ucb_state", "init_od_bandit_state"))
    select_fn = _pick_first_existing(mod, ("select_ucb_arm", "choose_ucb_arm"))
    update_fn = _pick_first_existing(
        mod,
        ("update_od_ucb_state", "update_online_od_bandit", "apply_od_bandit_reward_update"),
    )
    if None in (state_type, init_fn, select_fn, update_fn):
        missing: list[str] = []
        if state_type is None:
            missing.append("ODBanditState")
        if init_fn is None:
            missing.append("create_od_ucb_state|build_od_ucb_state|init_od_bandit_state")
        if select_fn is None:
            missing.append("select_ucb_arm|choose_ucb_arm")
        if update_fn is None:
            missing.append("update_od_ucb_state|update_online_od_bandit|apply_od_bandit_reward_update")
        pytest.skip(f"T063 pending: missing od-ucb API exports: {', '.join(missing)}")

    assert state_type is not None
    assert init_fn is not None
    assert select_fn is not None
    assert update_fn is not None


def test_od_ucb_select_prefers_unpulled_arm_contract_pending_t063():
    mod = pytest.importorskip(
        "metroflow.learning.od_ucb",
        reason="T063 pending: learning.od_ucb not implemented yet",
    )
    if _pick_first_existing(mod, ("ODBanditState", "OdUcbBanditState")) is None:
        pytest.skip("T063 pending: ODBanditState export not implemented yet")

    try:
        state = _make_bandit_state(
            mod,
            od_key=("z1", "z2"),
            arm_count=3,
            pull_count=(10, 0, 10),  # arm 1 intentionally unpulled
            estimated_reward=(0.8, 0.0, 0.7),
            last_update_tick=5,
        )
        selected = _select_arm(mod, state, tick_index=6, seed=11)
    except TypeError as exc:
        if _looks_like_signature_mismatch(exc):
            pytest.skip(f"T063 pending: od-ucb constructor/select signatures not finalized ({exc})")
        raise

    arm_idx, candidate_id = _coerce_selected_arm_choice(selected)
    assert (arm_idx is not None) or (candidate_id is not None)
    if arm_idx is not None:
        assert 0 <= arm_idx < 3
        # UCB baseline contract: unpulled arm should remain selectable/explorable.
        # With a single unpulled arm and deterministic setup, prefer it.
        assert arm_idx == 1
    else:
        expected_candidate_id = _candidate_id_for_arm(state, 1)
        if expected_candidate_id is None:
            pytest.skip("T063 pending: selection result uses candidate_id semantics but state lacks candidate_ids")
        assert candidate_id == expected_candidate_id


def test_od_ucb_online_update_increments_pull_count_and_updates_reward_contract_pending_t063():
    mod = pytest.importorskip(
        "metroflow.learning.od_ucb",
        reason="T063 pending: learning.od_ucb not implemented yet",
    )
    if _pick_first_existing(mod, ("ODBanditState", "OdUcbBanditState")) is None:
        pytest.skip("T063 pending: ODBanditState export not implemented yet")

    try:
        state = _make_bandit_state(
            mod,
            od_key=("z1", "z2"),
            arm_count=2,
            pull_count=(1, 2),
            estimated_reward=(0.2, 0.9),
            last_update_tick=3,
        )
        updated = _update_bandit_state(mod, state, arm_index=0, reward=1.0, tick_index=4, seed=13)
    except TypeError as exc:
        if _looks_like_signature_mismatch(exc):
            pytest.skip(f"T063 pending: od-ucb update signature not finalized ({exc})")
        raise

    next_state = _extract_updated_state(updated)
    pull = tuple(int(x) for x in _get_field(next_state, "pull_count", ()))
    est = tuple(float(x) for x in _get_field(next_state, "estimated_reward", ()))
    assert len(pull) >= 2 and len(est) >= 2
    arm_count = int(_get_field(next_state, "arm_count", len(pull)))
    assert arm_count >= 2
    assert len(pull) == arm_count
    assert len(est) == arm_count
    assert pull[0] == 2
    assert pull[1] == 2
    assert all(p >= 0 for p in pull)
    assert all(math.isfinite(v) for v in est)
    assert est[0] != pytest.approx(0.2)
    assert int(_get_field(next_state, "last_update_tick", 4)) >= 4


def test_od_ucb_state_validation_rejects_invalid_od_key_and_duplicate_candidate_ids():
    mod = pytest.importorskip("metroflow.learning.od_ucb")
    state_cls = getattr(mod, _pick_first_existing(mod, ("ODBanditState", "OdUcbBanditState")))

    with pytest.raises(ValueError):
        state_cls(
            od_key=("z1",),
            arm_count=1,
            pull_count=(0,),
            estimated_reward=(0.0,),
        )

    with pytest.raises(ValueError):
        state_cls(
            od_key=("z1", "z2"),
            arm_count=2,
            pull_count=(0, 0),
            estimated_reward=(0.0, 0.0),
            candidate_ids=(10, 10),
        )


def test_create_od_ucb_state_rejects_arm_count_candidate_count_mismatch():
    mod = pytest.importorskip("metroflow.learning.od_ucb")
    init_name = _pick_first_existing(mod, ("create_od_ucb_state", "build_od_ucb_state", "init_od_bandit_state"))
    if init_name is None:
        pytest.skip("T063 pending: init function alias unavailable")
    init_fn = getattr(mod, init_name)
    with pytest.raises(ValueError):
        init_fn(od_key=("z1", "z2"), arm_count=2, candidate_count=3)


def test_od_ucb_update_allows_tick_rollback_for_replay_semantics():
    mod = pytest.importorskip("metroflow.learning.od_ucb")
    state = _make_bandit_state(
        mod,
        od_key=("z1", "z2"),
        arm_count=2,
        pull_count=(1, 1),
        estimated_reward=(0.5, 0.5),
        last_update_tick=10,
    )
    updated = _update_bandit_state(mod, state, arm_index=0, reward=0.0, tick_index=4, seed=1)
    next_state = _extract_updated_state(updated)
    assert int(_get_field(next_state, "last_update_tick", -1)) == 4


def test_create_od_ucb_state_allows_empty_candidate_set_for_safe_fallback():
    mod = pytest.importorskip("metroflow.learning.od_ucb")
    init_name = _pick_first_existing(mod, ("create_od_ucb_state", "build_od_ucb_state", "init_od_bandit_state"))
    if init_name is None:
        pytest.skip("T063 pending: init function alias unavailable")
    init_fn = getattr(mod, init_name)

    state = init_fn(od_key=("z1", "z2"), arm_count=0, candidate_ids=())
    select_name = _pick_first_existing(mod, ("select_ucb_arm", "choose_ucb_arm"))
    assert select_name is not None
    select_fn = getattr(mod, select_name)

    assert int(_get_field(state, "arm_count", -1)) == 0
    assert tuple(int(x) for x in _get_field(state, "pull_count", ())) == ()
    assert tuple(float(x) for x in _get_field(state, "estimated_reward", ())) == ()
    assert select_fn(state=state) is None


def test_od_ucb_core_update_is_jittable_with_array_scalars():
    mod = pytest.importorskip("metroflow.learning.od_ucb")
    core_fn = getattr(mod, "update_od_ucb_arrays_core", None)
    if core_fn is None:
        pytest.skip("T063 pending: array core update export unavailable")

    compiled = jax.jit(
        lambda pulls, rewards, arm_idx, reward: core_fn(
            pulls,
            rewards,
            arm_index=arm_idx,
            reward=reward,
        )
    )
    next_pulls, next_rewards, next_bonus = compiled(
        jnp.asarray((1, 0), dtype=jnp.int32),
        jnp.asarray((0.25, 0.0), dtype=jnp.float32),
        jnp.asarray(1, dtype=jnp.int32),
        jnp.asarray(0.5, dtype=jnp.float32),
    )

    assert tuple(int(x) for x in next_pulls) == (1, 1)
    assert tuple(round(float(x), 6) for x in next_rewards) == (0.25, 0.5)
    assert len(tuple(float(x) for x in next_bonus)) == 2


def test_ucb_score_core_accepts_traced_exploration_scale():
    mod = pytest.importorskip("metroflow.learning.od_ucb")
    score_fn = getattr(mod, "compute_ucb_scores_core", None)
    if score_fn is None:
        pytest.skip("T063 pending: score core export unavailable")

    compiled = jax.jit(
        lambda rewards, pulls, scale: score_fn(
            rewards,
            pulls,
            exploration_scale=scale,
        )
    )
    scores = compiled(
        jnp.asarray((0.25, 0.5), dtype=jnp.float32),
        jnp.asarray((1, 3), dtype=jnp.int32),
        jnp.asarray(0.75, dtype=jnp.float32),
    )

    assert len(tuple(float(x) for x in scores)) == 2
    assert all(math.isfinite(float(x)) for x in scores)


def _make_bandit_state(
    mod: Any,
    *,
    od_key: tuple[str, str],
    arm_count: int,
    pull_count: tuple[int, ...],
    estimated_reward: tuple[float, ...],
    last_update_tick: int,
) -> Any:
    init_name = _pick_first_existing(mod, ("create_od_ucb_state", "build_od_ucb_state", "init_od_bandit_state"))
    if init_name is not None:
        init_fn = getattr(mod, init_name)
        # Try a small set of likely keyword conventions before failing.
        for kwargs in (
            {
                "od_key": od_key,
                "arm_count": arm_count,
                "pull_count": pull_count,
                "estimated_reward": estimated_reward,
                "last_update_tick": last_update_tick,
            },
            {
                "od_key": od_key,
                "candidate_count": arm_count,
                "pull_count": pull_count,
                "estimated_reward": estimated_reward,
                "last_update_tick": last_update_tick,
            },
        ):
            try:
                return init_fn(**kwargs)
            except TypeError as exc:
                # Only continue for call-shape mismatches while T063 is pending.
                if not _looks_like_signature_mismatch(exc):
                    raise
                continue

    state_name = _pick_first_existing(mod, ("ODBanditState", "OdUcbBanditState"))
    if state_name is None:
        raise TypeError("ODBanditState constructor unavailable")
    state_cls = getattr(mod, state_name)
    try:
        return state_cls(
            od_key=od_key,
            arm_count=arm_count,
            pull_count=pull_count,
            estimated_reward=estimated_reward,
            last_update_tick=last_update_tick,
        )
    except TypeError as exc:
        if _looks_like_signature_mismatch(exc):
            raise
        raise


def _select_arm(mod: Any, state: Any, *, tick_index: int, seed: int) -> Any:
    select_name = _pick_first_existing(mod, ("select_ucb_arm", "choose_ucb_arm"))
    if select_name is None:
        raise TypeError("selection function unavailable")
    fn = getattr(mod, select_name)
    for kwargs in (
        {"state": state, "current_tick": tick_index, "seed": seed},
        {"state": state, "tick_index": tick_index, "seed": seed},
        {"bandit_state": state, "current_tick": tick_index, "seed": seed},
        {"state": state},
    ):
        try:
            return fn(**kwargs)
        except TypeError as exc:
            if not _looks_like_signature_mismatch(exc):
                raise
            continue
    raise TypeError("selection signature not matched")


def _update_bandit_state(
    mod: Any,
    state: Any,
    *,
    arm_index: int,
    reward: float,
    tick_index: int,
    seed: int,
) -> Any:
    update_name = _pick_first_existing(
        mod,
        ("update_od_ucb_state", "update_online_od_bandit", "apply_od_bandit_reward_update"),
    )
    if update_name is None:
        raise TypeError("update function unavailable")
    fn = getattr(mod, update_name)
    for kwargs in (
        {"state": state, "arm_index": arm_index, "reward": reward, "current_tick": tick_index, "seed": seed},
        {"state": state, "arm_idx": arm_index, "reward": reward, "tick_index": tick_index, "seed": seed},
        {"bandit_state": state, "arm_index": arm_index, "reward": reward, "tick_index": tick_index, "seed": seed},
        {"state": state, "arm_index": arm_index, "reward": reward, "tick_index": tick_index},
    ):
        try:
            return fn(**kwargs)
        except TypeError as exc:
            if not _looks_like_signature_mismatch(exc):
                raise
            continue
    raise TypeError("update signature not matched")


def _extract_updated_state(update_out: Any) -> Any:
    if isinstance(update_out, tuple) and update_out:
        return update_out[0]
    if isinstance(update_out, list) and update_out:
        return update_out[0]
    return update_out


def _coerce_selected_arm_choice(selected: Any) -> tuple[int | None, int | None]:
    if isinstance(selected, tuple) and selected:
        first = selected[0]
        if isinstance(first, (int, float)):
            return int(first), None
        if isinstance(first, dict):
            for key in ("arm_index", "selected_arm_index", "arm_idx"):
                if key in first:
                    return int(first[key]), None
            for key in ("candidate_id", "selected_candidate_id"):
                if key in first:
                    return None, int(first[key])
    if isinstance(selected, dict):
        for key in ("arm_index", "selected_arm_index", "arm_idx"):
            if key in selected:
                return int(selected[key]), None
        for key in ("candidate_id", "selected_candidate_id"):
            if key in selected:
                return None, int(selected[key])
    try:
        return int(selected), None
    except Exception:
        return None, None


def _get_field(obj: Any, field_name: str, default: Any) -> Any:
    if isinstance(obj, dict):
        return obj.get(field_name, default)
    return getattr(obj, field_name, default)


def _pick_first_existing(mod: object, names: tuple[str, ...]) -> str | None:
    for name in names:
        if hasattr(mod, name):
            return name
    return None


def _candidate_id_for_arm(state: Any, arm_index: int) -> int | None:
    raw = _get_field(state, "candidate_ids", None)
    if raw is None:
        return None
    try:
        seq = tuple(raw)
    except Exception:
        return None
    if not (0 <= int(arm_index) < len(seq)):
        return None
    return int(seq[int(arm_index)])


def _looks_like_signature_mismatch(exc: TypeError) -> bool:
    msg = str(exc).lower()
    return any(
        token in msg
        for token in (
            "unexpected keyword",
            "positional argument",
            "required positional argument",
            "got an unexpected",
            "missing",
            "takes ",
        )
    )
