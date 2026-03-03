# Contract: Multimodal Routing Candidate Comparison (Phase 11)

This contract defines the planned comparison boundary between road-only and
transit-assisted route alternatives. It is intentionally limited to candidate
generation and scoring inputs/outputs; in-trip mixed-mode substitutions and
vehicle-level transit operations remain out of scope for this phase.

## Goals

- Compare road and transit alternatives under a single deterministic contract
- Preserve baseline road-only routing when transit is disabled or unavailable
- Expose walk-proxy access/egress fields explicitly instead of inferring them
- Keep candidate comparison compatible with future policy mixing and UI summary
  layers

## Core Types (Logical)

- `RouteCandidateSet`
- `MultimodalCandidateSet`
- `RoadCandidate`
- `TransitCandidate`
- `WalkProxyLeg`
- `MultimodalComparisonSummary`

Type details align with:
- `specs/001-adaptive-traffic-sim/data-model.md` /
  `## Behavior / Routing Entities`
- `specs/001-adaptive-traffic-sim/data-model.md` /
  `## Transit / Metro Static Entities (Extension Phase 9+)`

## Candidate Generation Entry Point Contract

```python
def build_multimodal_candidates(
    routing_context,
    road_candidate_set,
    transit_network_artifact,
    station_summaries,
    seed: int,
) -> MultimodalCandidateSet:
    ...
```

Behavior:
- Starts from the existing road route candidates for an OD pair
- Optionally derives transit alternatives using walk-proxy access connectors,
  line/headway metadata, and station summaries
- Returns a normalized candidate collection that can be compared without
  replacing the baseline routing fallback

## Input Contract

### `routing_context`

Must provide:
- `origin_zone_id`
- `dest_zone_id`
- `origin_node_id`
- `dest_node_id`
- `day_type`
- `time_band`
- `scenario_mode`

Rules:
- `scenario_mode == road_only` MUST suppress transit candidate generation
- Context MUST be sufficient to evaluate both road travel cost and transit
  access/egress feasibility for the same OD request

### `road_candidate_set`

Required fields:
- `od_key`
- `candidate_ids`
- `candidate_paths`
- `last_refresh_tick`

Rules:
- Road candidates remain the baseline fallback set
- An empty road candidate set is allowed only if the caller is already handling
  a no-route condition

### `transit_network_artifact`

Required fields when transit is enabled:
- `stations`
- `lines`
- `transfers`
- `access_connectors`
- `metadata`

Rules:
- Empty artifact is valid in `road_only` mode
- Candidate generation MUST NOT mutate the static transit artifact

### `station_summaries`

Expected shape:
- zero or more `StationSummary` objects keyed by station/time band

Rules:
- Phase 11 comparison MAY use zero-filled or missing summaries when passenger
  flow is unavailable, but it MUST treat those cases as reduced observability
  rather than malformed input

## Output Contract

### `MultimodalCandidateSet`

Fields:
- `od_key`
- `scenario_mode` (`road_only`, `multimodal`)
- `comparison_tick`
- `road_candidates` (list[`RoadCandidate`])
- `transit_candidates` (list[`TransitCandidate`])
- `comparison_summary` (`MultimodalComparisonSummary`)
- `fallback_mode` (`road_only`, `transit_filtered`, `no_route`)

Validation rules:
- `road_candidates` MUST preserve deterministic ordering from the baseline input
- `transit_candidates` MAY be empty even in `multimodal` mode
- `fallback_mode == road_only` is valid whenever transit generation is disabled,
  filtered out, or unsupported for the OD pair

## Candidate Entity Contract

### `RoadCandidate`

Required fields:
- `candidate_id`
- `mode` (`road`)
- `path_link_ids`
- `estimated_travel_time_ticks`
- `estimated_generalized_cost`
- `congestion_score`
- `source` (`baseline`, `adaptive`, `fallback_baseline`)

Rules:
- `path_link_ids` MUST contain legal road links only
- Travel-time and cost fields MUST be finite

### `TransitCandidate`

Required fields:
- `candidate_id`
- `mode` (`transit`)
- `access_leg` (`WalkProxyLeg`)
- `line_leg_ids` (ordered list of `line_id` or line-segment references)
- `transfer_station_ids`
- `egress_leg` (`WalkProxyLeg`)
- `estimated_in_vehicle_ticks`
- `estimated_wait_ticks`
- `estimated_transfer_ticks`
- `estimated_generalized_cost`
- `uses_station_summary` (bool)

Rules:
- Transit candidates MUST reference emitted transit lines/stations/connectors
- `line_leg_ids` MUST be non-empty for a valid transit alternative
- Cost components MUST be finite and non-negative

### `WalkProxyLeg`

Required fields:
- `connector_id`
- `station_id`
- `anchor_node_id`
- `anchor_zone_id`
- `walk_time_ticks`
- `distance_m`
- `leg_role` (`access`, `egress`)

Rules:
- Each walk-proxy leg MUST resolve to an emitted `AccessConnector`
- Either `anchor_node_id` or `anchor_zone_id` may be the primary routing anchor,
  but both fields MUST be present in the comparison payload for observability

## Comparison Summary Contract

### `MultimodalComparisonSummary`

Fields:
- `best_mode` (`road`, `transit`, `none`)
- `road_candidate_count`
- `transit_candidate_count`
- `best_road_cost`
- `best_transit_cost` (optional)
- `cost_delta_transit_minus_road` (optional)
- `filtered_transit_reason` (optional enum: transit_disabled, no_access, no_line, no_capacity_signal, invalid_candidate)

Rules:
- `best_transit_cost` and `cost_delta_transit_minus_road` MAY be omitted when
  no valid transit candidate exists
- `filtered_transit_reason` SHOULD be populated when multimodal mode is enabled
  but no transit candidate survives filtering

## Selection and Fallback Rules

- Road candidates MUST always remain eligible as the safe baseline option
- Multimodal comparison MAY rank transit above road, but MUST NOT require
  mid-trip substitution from a road path to a transit path in this phase
- If transit scoring produces invalid, missing, or non-finite values, the
  decision boundary MUST degrade to `fallback_mode == road_only`
- Candidate ids and ordering MUST remain deterministic for fixed seed and
  identical inputs

## Road-Only Compatibility Rules

- `road_only` mode MUST emit a valid `MultimodalCandidateSet` with empty
  `transit_candidates`
- Consumers MUST treat the absence of transit candidates as normal in
  `road_only` mode rather than as an error
- Road-only benchmark and demo paths MUST not depend on any transit-specific
  field being populated

## Validation Notes

- Referential integrity SHOULD be checked across walk connectors, stations, and
  line references before candidates are exposed to the policy mixer
- Comparison payloads SHOULD be machine-readable so later UI/reporting layers
  can summarize road-vs-transit outcomes without recomputing candidate fields
- This contract intentionally excludes detailed passenger queue state, boarding/
  alighting transitions, and UI packet schema details; those are handled by
  later implementation and UI contract tasks
