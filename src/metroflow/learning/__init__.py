"""Learning package public exports."""

from __future__ import annotations

__all__ = [
    "AdaptivePolicyPlugin",
    "PolicyPlugin",
    "register_policy_plugin",
    "register_adaptive_policy_plugin",
    "create_policy_plugin",
    "build_policy_plugin",
    "get_policy_plugin",
    "ODBanditState",
    "create_od_ucb_state",
    "build_od_ucb_state",
    "init_od_bandit_state",
    "select_ucb_arm",
    "choose_ucb_arm",
    "update_od_ucb_state",
    "update_online_od_bandit",
    "apply_od_bandit_reward_update",
    "compute_ucb_scores_core",
    "select_ucb_arm_core",
    "update_od_ucb_arrays_core",
    "LearningExperience",
    "create_learning_experience",
    "build_learning_experience",
    "compute_trip_outcome_reward",
    "extract_online_experience_batch",
    "build_experience_batch",
]


def __getattr__(name: str):
    if name in {
        "AdaptivePolicyPlugin",
        "PolicyPlugin",
        "register_policy_plugin",
        "register_adaptive_policy_plugin",
        "create_policy_plugin",
        "build_policy_plugin",
        "get_policy_plugin",
    }:
        from metroflow.learning import plugins as _plugins

        return getattr(_plugins, name)
    if name in {
        "ODBanditState",
        "create_od_ucb_state",
        "build_od_ucb_state",
        "init_od_bandit_state",
        "select_ucb_arm",
        "choose_ucb_arm",
        "update_od_ucb_state",
        "update_online_od_bandit",
        "apply_od_bandit_reward_update",
        "compute_ucb_scores_core",
        "select_ucb_arm_core",
        "update_od_ucb_arrays_core",
    }:
        from metroflow.learning import od_ucb as _od_ucb

        return getattr(_od_ucb, name)
    if name in {
        "LearningExperience",
        "create_learning_experience",
        "build_learning_experience",
        "compute_trip_outcome_reward",
        "extract_online_experience_batch",
        "build_experience_batch",
    }:
        from metroflow.learning import experience as _experience

        return getattr(_experience, name)
    raise AttributeError(name)
