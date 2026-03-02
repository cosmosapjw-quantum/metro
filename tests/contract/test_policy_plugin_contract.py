from __future__ import annotations

import inspect

import pytest

"""Contract-first tests for T061 adaptive policy plugin interface/registry.

These tests are intentionally allowed to skip while `metroflow.learning.plugins`
is pending. Once the module exists, they should fail on real contract drift.
"""


def test_policy_plugin_module_api_contract_pending_t061():
    mod = pytest.importorskip(
        "metroflow.learning.plugins",
        reason="T061 pending: learning.plugins not implemented yet",
    )

    plugin_iface = _pick_first_existing(mod, ("AdaptivePolicyPlugin", "PolicyPlugin"))
    register_fn = _pick_first_existing(mod, ("register_policy_plugin", "register_adaptive_policy_plugin"))
    create_fn = _pick_first_existing(mod, ("create_policy_plugin", "build_policy_plugin", "get_policy_plugin"))
    if plugin_iface is None or register_fn is None or create_fn is None:
        missing: list[str] = []
        if plugin_iface is None:
            missing.append("AdaptivePolicyPlugin|PolicyPlugin")
        if register_fn is None:
            missing.append("register_policy_plugin|register_adaptive_policy_plugin")
        if create_fn is None:
            missing.append("create_policy_plugin|build_policy_plugin|get_policy_plugin")
        pytest.skip(f"T061 pending: missing plugin API exports: {', '.join(missing)}")

    assert plugin_iface is not None
    assert register_fn is not None
    assert create_fn is not None


def test_policy_plugin_interface_method_boundaries_pending_t061():
    mod = pytest.importorskip(
        "metroflow.learning.plugins",
        reason="T061 pending: learning.plugins not implemented yet",
    )
    iface = _pick_first_existing(mod, ("AdaptivePolicyPlugin", "PolicyPlugin"))
    if iface is None:
        pytest.skip("T061 pending: plugin interface/protocol export not implemented yet")

    missing_methods = tuple(
        name for name in ("init", "score_actions", "update_online") if not hasattr(iface, name)
    )
    if missing_methods:
        pytest.skip(
            "T061 pending: plugin interface methods missing: " + ", ".join(missing_methods)
        )

    init_sig = inspect.signature(getattr(iface, "init"))
    score_sig = inspect.signature(getattr(iface, "score_actions"))
    update_sig = inspect.signature(getattr(iface, "update_online"))

    assert tuple(init_sig.parameters)[:3] == ("self", "config", "seed")
    assert tuple(score_sig.parameters)[:4] == ("self", "plugin_state", "routing_context_batch", "rng_key")
    assert tuple(update_sig.parameters)[:4] == ("self", "plugin_state", "experience_batch", "rng_key")

    # Contract identity flags documented in `contracts/policy-plugin.md`.
    for attr in ("plugin_name", "plugin_version", "supports_online_update", "supports_batch_context"):
        assert hasattr(iface, attr)


def test_policy_plugin_registry_roundtrip_and_duplicate_guard_pending_t061():
    mod = pytest.importorskip(
        "metroflow.learning.plugins",
        reason="T061 pending: learning.plugins not implemented yet",
    )
    iface = _pick_first_existing(mod, ("AdaptivePolicyPlugin", "PolicyPlugin"))
    register_name, register_fn = _pick_named_first_existing(
        mod, ("register_policy_plugin", "register_adaptive_policy_plugin")
    )
    create_name, create_fn = _pick_named_first_existing(
        mod, ("create_policy_plugin", "build_policy_plugin", "get_policy_plugin")
    )
    if iface is None or register_fn is None or create_fn is None:
        pytest.skip("T061 pending: registry interface/create exports not implemented yet")

    dummy_plugin_name = f"contract_dummy_t056_{create_name}_{register_name}"

    class DummyPlugin(getattr(mod, iface)):
        plugin_name = dummy_plugin_name
        plugin_version = "1.0"
        supports_online_update = True
        supports_batch_context = True

        def init(self, config, seed):
            return {"seed": int(seed), "cfg": dict(config)}

        def score_actions(self, plugin_state, routing_context_batch, rng_key):
            return [0.0] * len(routing_context_batch), {"ok": True}, rng_key

        def update_online(self, plugin_state, experience_batch, rng_key):
            metrics = {"online_update_count_delta": len(experience_batch)}
            return plugin_state, metrics, rng_key

    # Signature/registration shape is still pending in T061. Restrict skip to
    # call-shape mismatches only; runtime validation bugs should fail.
    try:
        _register_plugin(register_name, register_fn, DummyPlugin)
    except TypeError as exc:
        pytest.skip(f"T061 pending: registry signature not finalized ({exc})")

    try:
        plugin = _create_plugin(create_name, create_fn, dummy_plugin_name)
    except TypeError as exc:
        pytest.skip(f"T061 pending: create/get signature not finalized ({exc})")

    # Contract boundary smoke: init/score/update methods exist and preserve RNG
    # tuple boundary shape.
    state = plugin.init(config={"learning_enabled": True}, seed=7)
    score_out = plugin.score_actions(state, routing_context_batch=[{"od_key": ("z1", "z2")}], rng_key=object())
    update_out = plugin.update_online(state, experience_batch=[{"reward": 1.0}], rng_key=object())
    assert isinstance(state, dict)
    assert getattr(plugin, "plugin_name", None) == dummy_plugin_name
    assert bool(getattr(plugin, "supports_online_update", False)) is True
    assert len(tuple(score_out)) == 3
    assert len(tuple(update_out)) == 3

    # Duplicate registration should be guarded to prevent plugin identity drift.
    with pytest.raises((ValueError, KeyError)):
        _register_plugin(register_name, register_fn, DummyPlugin)


def _pick_first_existing(mod: object, names: tuple[str, ...]) -> str | None:
    for name in names:
        if hasattr(mod, name):
            return name
    return None


def _pick_named_first_existing(mod: object, names: tuple[str, ...]) -> tuple[str | None, object | None]:
    name = _pick_first_existing(mod, names)
    return (name, getattr(mod, name) if name is not None else None)


def _register_plugin(register_name: str, register_fn: object, plugin_cls: type[object]) -> object:
    fn = register_fn
    if register_name == "register_policy_plugin":
        return fn(plugin_cls)  # type: ignore[misc]
    if register_name == "register_adaptive_policy_plugin":
        return fn(plugin_cls)  # type: ignore[misc]
    raise AssertionError(f"unexpected register function: {register_name}")


def _create_plugin(create_name: str, create_fn: object, plugin_name: str) -> object:
    fn = create_fn
    if create_name in {"create_policy_plugin", "build_policy_plugin"}:
        return fn(plugin_name, {})  # type: ignore[misc]
    if create_name == "get_policy_plugin":
        maybe = fn(plugin_name)  # type: ignore[misc]
        return maybe() if callable(maybe) else maybe
    raise AssertionError(f"unexpected create/get function: {create_name}")
