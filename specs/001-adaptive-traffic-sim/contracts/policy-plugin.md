# Contract: Routing Policy and Adaptive Learning Plugin (Phase 1)

This contract defines the boundary between the routing engine, safe baseline
policy, and adaptive learning plugins. The first implementation target is OD-UCB
bandits, with a future extension slot for GNN+LSTM policies.

## Goals

- Preserve a safe baseline policy at all times
- Allow gradual adaptive mixing without destabilizing simulation
- Support online-only learning from simulator outcomes
- Keep routing engine independent of plugin-specific model internals

## Baseline Policy Contract

### `BaselineRoutingContext`

Inputs:
- Current link travel costs / congestion estimates
- Network topology and legal turns
- Origin/destination or next-turn decision context
- Event/disruption state

Outputs:
- `baseline_action_scores` or `baseline_cost_to_go` for legal next actions
- `baseline_route_candidate_scores` (if selecting among OD candidates)

Requirements:
- Deterministic for fixed state and seed-independent baseline computation
- Available even when adaptive plugin is disabled or invalid

## Adaptive Plugin Contract

### Plugin Identity

- `plugin_name` (e.g., `od_ucb_v1`, future `gnn_lstm_v1`)
- `plugin_version`
- `supports_online_update` (bool)
- `supports_batch_context` (bool)

### `AdaptivePolicyPlugin.init`

```python
def init(config, seed) -> PluginState:
    ...
```

Rules:
- Initializes plugin state only from config/seed
- Must not consume external training data

### `AdaptivePolicyPlugin.score_actions`

```python
def score_actions(
    plugin_state,
    routing_context_batch,
    rng_key,
) -> tuple[action_scores_batch, plugin_aux, rng_key]:
    ...
```

Rules:
- Scores only legal actions/candidates presented by routing engine
- Must return finite scores or signal invalid output
- Must not mutate global engine state directly

### `AdaptivePolicyPlugin.update_online`

```python
def update_online(
    plugin_state,
    experience_batch,
    rng_key,
) -> tuple[plugin_state, update_metrics, rng_key]:
    ...
```

`experience_batch` sources (simulator-only):
- Trip outcomes (completion/failure, travel time)
- Route candidate chosen
- Context summaries at decision time
- Event/disruption context

Rules:
- No external/offline dataset ingestion
- Update may be skipped on insufficient signal

## OD-UCB First Implementation Contract

### `od_key`

- Tuple keyed by origin zone and destination zone (or POI cluster)

### Required State

- Candidate arms for each `od_key`
- Pull counts and estimated rewards per arm
- Optional recency weighting metadata

### Reward Definition (Planning)

- Reward derived from simulator trip outcome metrics (e.g., lower travel time,
  success/completion bonus, failure penalty)
- Reward normalization strategy must be documented for reproducibility

## Policy Mixing and Fallback Contract

### `PolicyBlendController`

Inputs:
- Baseline scores
- Adaptive scores
- `lambda_mix` policy
- Stability/validity signals

Output:
- Final action scores or action distribution
- Fallback status and reason code

Rules:
- Final decision MUST reduce to baseline-only behavior when:
  - Adaptive plugin disabled
  - Adaptive output invalid / non-finite
  - Insufficient training signal / cold start
  - Explicit safety fallback condition triggered
- `lambda_mix` MUST remain within configured bounds and change gradually

## Plugin Telemetry Contract

Per-tick or per-update metrics:
- `plugin_active` (bool)
- `lambda_mix`
- `fallback_count_delta`
- `invalid_output_count_delta`
- `online_update_count_delta`
- `mean_reward_estimate` (where applicable)

Purpose:
- Support debugging and benchmark comparisons without exposing plugin internals

## Future GNN+LSTM Extension Compatibility

The contract reserves support for:
- Graph context inputs
- Agent memory state references
- Batched recurrent updates

Compatibility rule:
- Future plugins may add plugin-specific state fields, but MUST continue to work
  with the same baseline/fallback and online-update boundaries defined here.
