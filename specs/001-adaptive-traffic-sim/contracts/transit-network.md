# Contract: Transit Network Generation and Static Wiring (Phase 9)

This contract defines the planned schema and validation boundary for synthetic
transit/metro network generation. It covers static network artifacts only:
stations, lines, headways, transfer metadata, and walk-proxy access connectors.
Passenger boarding/alighting/waiting behavior is intentionally deferred to
Phase 10.

## Goals

- Generate transit network artifacts that remain optional in `road_only` mode
- Keep transit static topology separate from per-tick passenger-flow state
- Preserve fixed-seed reproducibility for station/line/headway generation
- Expose explicit metadata that later routing, UI, and initialization steps can
  consume without inferring hidden fields

## Core Types (Logical)

- `TransitStation`
- `TransitLine`
- `TransitTransfer`
- `AccessConnector`
- `TransitNetworkArtifact`

Type details align with
`specs/001-adaptive-traffic-sim/data-model.md` under
`## Transit / Metro Static Entities (Extension Phase 9+)`.

## Generation Entry Point Contract

```python
def generate_transit_network(
    city_topology,
    config,
    seed: int,
) -> TransitNetworkArtifact:
    ...
```

Behavior:
- Selects station candidates from the synthetic city topology
- Builds one or more transit lines with ordered station sequences
- Assigns headway metadata by time band and operating day type
- Generates transfer metadata between compatible stations or station complexes
- Generates walk-proxy access connectors from nodes/zones to stations

## Input Contract

### `city_topology`

Must provide:
- `nodes`
- `road_links`
- `zones`
- `bridge_crossings`

Rules:
- Transit generation MAY use road topology and zones as anchors, but MUST NOT
  mutate the underlying road network definition
- Missing or empty transit generation config MUST be treated as "transit
  disabled" rather than as an implicit error in `road_only` scenarios

### `config`

Expected fields:
- `transit_enabled` (bool)
- `target_station_count` (int >= 0)
- `target_line_count` (int >= 0)
- `station_spacing_profile`
- `headway_profile_by_time_band`
- `transfer_radius_m`
- `connector_walk_speed_mps`

Rules:
- `transit_enabled == False` MUST return an empty but valid
  `TransitNetworkArtifact`
- Enabled generation MUST use positive headway and walk-speed values

## Output Contract

### `TransitNetworkArtifact`

Fields:
- `network_id` (string)
- `schema_version` (int)
- `generation_mode` (`disabled`, `synthetic_static`)
- `stations` (list[`TransitStation`])
- `lines` (list[`TransitLine`])
- `transfers` (list[`TransitTransfer`])
- `access_connectors` (list[`AccessConnector`])
- `metadata` (object with generator summary fields)

Required metadata keys:
- `seed`
- `station_count`
- `line_count`
- `transfer_count`
- `connector_count`
- `time_bands`
- `operating_day_types`

Validation rules:
- Metadata counts MUST match emitted collection sizes
- `generation_mode == disabled` MUST imply all emitted collections are empty
- `generation_mode == synthetic_static` MUST preserve deterministic ordering for
  fixed seed and identical city/config inputs

## Entity Contract

### `TransitStation`

Required fields:
- `station_id`
- `station_name`
- `x`
- `y`
- `station_kind`
- `serving_line_ids`
- `nearest_node_id`
- `zone_ids`
- `platform_capacity_hint`

Optional fields:
- `amenity_level`

Rules:
- `serving_line_ids` MUST be non-empty
- `nearest_node_id` MUST resolve to an existing city node
- `station_kind` MUST be one of `local_stop`, `interchange`, `terminal`

### `TransitLine`

Required fields:
- `line_id`
- `line_name`
- `line_mode`
- `station_sequence`
- `headway_seconds_by_time_band`
- `operating_day_types`
- `is_loop`

Rules:
- `station_sequence` MUST contain at least two valid station ids
- Headway values MUST be positive for every emitted time band
- `line_mode` MUST be one of `metro`, `suburban_rail`, `brt`

### `TransitTransfer`

Required fields:
- `transfer_id`
- `from_station_id`
- `to_station_id`
- `walk_time_ticks`
- `penalty_ticks`
- `is_cross_platform`

Optional fields:
- `shared_complex_id`

Rules:
- Source and destination station ids MUST differ
- Both station ids MUST resolve to emitted `TransitStation` entries
- `walk_time_ticks` and `penalty_ticks` MUST be non-negative

### `AccessConnector`

Required fields:
- `connector_id`
- `station_id`
- `access_mode`
- `distance_m`
- `walk_time_ticks`
- `directionality`

Optional fields:
- `anchor_node_id`
- `anchor_zone_id`

Rules:
- `station_id` MUST resolve to an emitted `TransitStation`
- At least one anchor (`anchor_node_id` or `anchor_zone_id`) MUST be present
- `access_mode` is restricted to `walk_proxy` in the MVP extension scope

## Headway and Operating-Day Contract

- `headway_seconds_by_time_band` MUST be represented as a mapping keyed by the
  simulation time-band labels (`morning`, `lunch`, `evening`, `night`)
- Omitted time bands are allowed only when the line is explicitly not operating
  during that band
- `operating_day_types` MUST be compatible with the available day-type labels
  (`weekday`, `weekend`, `both`)
- Later passenger-flow logic may derive waiting estimates from this metadata,
  but Phase 9 generation only guarantees the static headway declarations

## Road-Only Compatibility Rules

- `road_only` scenarios MUST remain valid when the entire
  `TransitNetworkArtifact` is empty
- Transit generation failure MUST degrade to `generation_mode == disabled`
  rather than corrupting baseline road topology initialization
- UI and routing consumers MUST treat absent transit artifacts as normal in
  `road_only` mode

## Determinism and Validation Notes

- Fixed seed + identical city topology/config MUST reproduce the same emitted
  ids, collection ordering, and metadata counts
- Validation SHOULD check referential integrity across stations, lines,
  transfers, and access connectors before the artifact is attached to simulation
  state
- This contract intentionally excludes passenger counts, waiting queues,
  boarding/alighting, and station congestion summaries; those are introduced in
  later phases
