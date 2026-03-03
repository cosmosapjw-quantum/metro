# Data Model: Adaptive Traffic Simulation (Phase 1)

This document defines the feature data model for the virtual-city traffic
simulation, including validation rules and key state transitions.

## Modeling Scope

- Synthetic city topology and zoning
- Citizen schedule and trip demand generation
- Active-agent packed simulation state
- Link-queue + node model flow state
- Event/disruption state
- Routing baseline + adaptive learning state
- UI snapshot packet source data
- Road-only realism metric/report outputs for extension validation
- Transit/metro static network entities and phase-gated station summaries

## Core Configuration Entities

### `SimulationConfig`

- `population_target` (int, default ~100_000)
- `tick_seconds` (float > 0)
- `active_agent_capacity` (int, expected 10_000-30_000 active during peak)
- `random_seed` (int)
- `day_type_set` (weekday, weekend)
- `time_bands` (morning, lunch, evening, night)
- `ui_stream_enabled` (bool)
- `ui_stream_hz_limit` (float > 0)
- `learning_enabled` (bool)
- `learning_mix_bounds` (`lambda_min`, `lambda_max` in [0, 1])
- `ctm_mode_enabled` (bool; optional extension switch, default false)

Validation rules:
- `population_target` MUST be >= 1
- `active_agent_capacity` MUST be > 0 and sized for expected peak active demand
- `lambda_min <= lambda_max`
- `tick_seconds` and `ui_stream_hz_limit` MUST be positive

### `CityGenerationConfig`

- `road_hierarchy_profile` (local/arterial/expressway proportions)
- `ring_road_count` (int >= 0)
- `radial_corridor_count` (int >= 1)
- `barrier_count` (int >= 1 for this feature)
- `bridge_count` (int in [3, 5] for this feature)
- `interchange_density_profile`
- `zone_mix_targets` (residential, CBD/commercial, industrial, mixed-use shares)
- `poi_density_profile`

Validation rules:
- Bridge count MUST be 3-5
- Zone mix shares MUST sum to 1.0 (within tolerance)
- Barrier topology MUST not isolate all zones from each other

## Topology / Static Network Entities

### `Node`

- `node_id` (int)
- `kind` (intersection, ramp_merge, ramp_split, interchange, bridge_endpoint)
- `x`, `y` (float map coordinates)
- `zone_id` (optional int for zone membership)
- `signal_group_id` (optional int, simplified control grouping)

Relationships:
- One `Node` connects to zero or more outgoing `RoadLink`
- `Node` may belong to one `Zone`

### `RoadLink`

- `link_id` (int)
- `src_node_id` (int)
- `dst_node_id` (int)
- `road_class` (local, arterial, expressway, ramp, bridge)
- `length_m` (float > 0)
- `free_flow_speed_mps` (float > 0)
- `capacity_veh_per_tick` (float >= 0)
- `lanes` (int >= 1, simplified)
- `bridge_group_id` (optional int)
- `is_blockable` (bool)

Validation rules:
- `src_node_id != dst_node_id`
- Capacity MUST be non-negative
- `bridge_group_id` required when `road_class == bridge`

### `TurnMovement`

- `from_link_id` (int)
- `to_link_id` (int)
- `turn_type` (left, through, right, ramp_on, ramp_off, u_turn_forbidden)
- `base_priority` (float >= 0)
- `signal_phase_id` (optional int)

Validation rules:
- `from_link_id` and `to_link_id` MUST share a junction node
- Forbidden turns MUST not appear in route candidates

### `BridgeCrossing`

- `bridge_group_id` (int)
- `link_ids` (list[int])
- `barrier_id` (int)
- `crossing_name` (string)
- `bottleneck_rank_hint` (int, optional)

### `Zone`

- `zone_id` (int)
- `zone_type` (residential, cbd_commercial, industrial, mixed_use)
- `centroid_x`, `centroid_y` (float)
- `population_capacity` (int >= 0)
- `job_capacity` (int >= 0)
- `leisure_capacity` (int >= 0)

Validation rules:
- Feature scope MUST include all four zone types across the city

### `POI`

- `poi_id` (int)
- `zone_id` (int)
- `poi_type` (home, workplace, leisure)
- `node_id` (nearest access node id)
- `capacity_hint` (int >= 0)

Relationships:
- `POI` belongs to one `Zone`
- `POI` is anchored to one access `Node`

## Transit / Metro Static Entities (Extension Phase 9+)

These entities are phase-gated extensions. They MUST remain optional for the
baseline road-only mode and are expected to be absent or empty when transit is
disabled.

### `TransitStation`

- `station_id` (int)
- `station_name` (string)
- `x`, `y` (float map coordinates)
- `station_kind` (local_stop, interchange, terminal)
- `serving_line_ids` (list[int])
- `nearest_node_id` (int)
- `zone_ids` (list[int])
- `platform_capacity_hint` (int >= 0)
- `amenity_level` (optional enum: basic, standard, hub)

Validation rules:
- Each station MUST reference at least one serving line
- `nearest_node_id` MUST resolve to an existing `Node`

### `TransitLine`

- `line_id` (int)
- `line_name` (string)
- `line_mode` (metro, suburban_rail, brt)
- `station_sequence` (ordered list[`station_id`])
- `headway_seconds_by_time_band` (mapping of time band -> headway seconds)
- `operating_day_types` (weekday, weekend, both)
- `is_loop` (bool)

Validation rules:
- `station_sequence` MUST contain at least two stations
- All referenced stations MUST exist
- Headway values MUST be positive for each configured time band

### `TransitTransfer`

- `transfer_id` (int)
- `from_station_id` (int)
- `to_station_id` (int)
- `walk_time_ticks` (int >= 0)
- `penalty_ticks` (int >= 0)
- `shared_complex_id` (optional int)
- `is_cross_platform` (bool)

Validation rules:
- `from_station_id != to_station_id`
- Both station ids MUST resolve to existing `TransitStation` entries

### `AccessConnector`

- `connector_id` (int)
- `station_id` (int)
- `anchor_node_id` (optional int)
- `anchor_zone_id` (optional int)
- `access_mode` (walk_proxy)
- `distance_m` (float >= 0)
- `walk_time_ticks` (int >= 0)
- `directionality` (entry, exit, bidirectional)

Validation rules:
- `station_id` MUST resolve to an existing `TransitStation`
- At least one of `anchor_node_id` or `anchor_zone_id` MUST be present
- `anchor_node_id`/`anchor_zone_id` MUST resolve when present
- `access_mode` remains `walk_proxy` for the MVP extension scope

## Demand / Schedule Entities

### `Citizen`

- `citizen_id` (int)
- `home_poi_id` (int)
- `work_poi_id` (optional int)
- `leisure_poi_preferences` (list of candidate POI ids / weights)
- `schedule_template_id` (int)
- `behavior_profile_id` (int)

Validation rules:
- Every citizen MUST have `home_poi_id`
- Workers MUST have `work_poi_id`

### `ScheduleTemplate`

- `schedule_template_id` (int)
- `applicable_day_type` (weekday, weekend, both)
- `time_band_rules` (per band trip propensity + destination type preferences)
- `departure_jitter_profile` (distribution identifier)

### `TripRequest`

- `trip_request_id` (int)
- `citizen_id` (int)
- `origin_poi_id` (int)
- `dest_poi_id` (int)
- `planned_depart_tick` (int)
- `day_type` (weekday, weekend)
- `time_band` (morning, lunch, evening, night)
- `status` (queued, activated, canceled)

Validation rules:
- `origin_poi_id != dest_poi_id`
- `planned_depart_tick >= 0`

### `Trip`

- `trip_id` (int)
- `trip_request_id` (int)
- `origin_node_id` (int)
- `dest_node_id` (int)
- `start_tick` (int)
- `end_tick` (optional int)
- `completion_status` (in_progress, completed, failed_no_route, failed_capacity_timeout)
- `selected_route_candidate_id` (optional int)
- `route_decision_source` (baseline, adaptive_bandit, adaptive_plugin, fallback_baseline)

Derived metrics:
- `travel_time_ticks` = `end_tick - start_tick` when completed

## Behavior / Routing Entities

### `RouteChoiceProfile`

- `behavior_profile_id` (int)
- `delay_sensitivity` (float)
- `reroute_willingness` (float in [0, 1])
- `persistence_bias` (float)
- `exploration_bias` (float)

Purpose:
- Encodes user-visible behavioral diversity (some reroute, some persist)

### `RouteCandidateSet`

- `od_key` (origin_zone_id, dest_zone_id)
- `candidate_ids` (list[int])
- `candidate_paths` (list[list[link_id]])
- `last_refresh_tick` (int)

Validation rules:
- Candidate paths MUST contain legal turn movements only
- Candidate set MUST be reproducible under fixed seed and same city state inputs

### `ODBanditState`

- `od_key`
- `arm_count`
- `pull_count[arm]`
- `estimated_reward[arm]`
- `exploration_bonus[arm]` (derived)
- `last_update_tick`

Validation rules:
- `pull_count >= 0`
- Reward updates only from simulator outcomes (completed or failed trips)

### `PolicyBlendState`

- `lambda_mix` (float in [0, 1])
- `fallback_triggered` (bool)
- `fallback_reason` (optional enum: instability, no_signal, invalid_output, incident_mode)

## Flow Engine Dynamic State (Per Tick)

### `LinkState`

- `queue_vehicles[link_id]` (float >= 0)
- `inflow_vehicles[link_id]` (float >= 0)
- `outflow_vehicles[link_id]` (float >= 0)
- `travel_time_cost[link_id]` (float > 0)
- `incident_capacity_multiplier[link_id]` (float in [0, 1])

Validation rules:
- Queue length MUST never be negative
- Outflow MUST not exceed effective capacity unless flagged as capacity violation

### `NodeState`

- `turn_demand[(from_link,to_link)]`
- `turn_supply[(from_link,to_link)]`
- `turn_flow[(from_link,to_link)]`
- `signal_phase_state` (simplified phase index / timer)

Validation rules:
- Turn flows MUST be consistent with upstream outflow and downstream supply

### `TrafficEvent`

- `event_id` (int)
- `event_type` (accident, construction, congestion_spike)
- `start_tick`, `end_tick`
- `target_scope` (link_ids, bridge_group_id, zone_id, corridor_id)
- `severity` (float)
- `effect_model` (capacity_reduction, closure, demand_spike)
- `status` (scheduled, active, cleared)

Validation rules:
- `start_tick < end_tick`
- Target scope MUST resolve to existing network elements

## Active-Agent Packed State

### `ActiveAgentSlot`

- `slot_id` (0..A_max-1)
- `alive` (bool)
- `citizen_id` (int, valid if alive)
- `trip_id` (int, valid if alive)
- `current_link_id` (int)
- `progress_01` (float in [0, 1])
- `remaining_route_ptr` (int index into route sequence)
- `dest_node_id` (int)
- `behavior_profile_id` (int)
- `reroute_cooldown_ticks` (int >= 0)

Optional plugin memory fields (reserved for future GNN+LSTM plugin):
- `policy_mem_h[...]`
- `policy_mem_c[...]`

### `ActiveAgentPool`

- `capacity` (`A_max`)
- `free_slot_stack` (stack/list of slot ids)
- `alive_mask[A_max]` (bool array)
- `alive_count` (int)

Validation rules:
- `alive_count` MUST equal `sum(alive_mask)`
- Slots MUST be either in free list or alive set, never both

## Simulation Run / Metrics Entities

### `CityRealismMetrics`

- `node_count`
- `road_link_count`
- `bridge_crossing_count`
- `zone_type_counts`
- `poi_count`
- `population_capacity_total`
- `job_capacity_total`
- `morphology_irregularity_score`
- `bridge_closure_delay_ratio`
- `bridge_closure_component_delta`
- `zoning_diversity_score`

Validation rules:
- Count fields MUST be non-negative
- Score/ratio fields MUST be finite and machine-readable for benchmark export

### `RealismReport`

- `scenario_id`
- `seed`
- `scenario_mode` (road_only, multimodal)
- `population_target`
- `metrics` (`CityRealismMetrics`)
- `threshold_results` (mapping metric key -> pass/fail/status)
- `notes` (optional list[string])

Validation rules:
- Fixed seed + same scenario config MUST reproduce the same metric keys and
  threshold result structure
- `scenario_mode` MUST be reported explicitly so road-only and multimodal
  benchmarks are not conflated

### `StationSummary`

- `station_id`
- `time_band`
- `entries`
- `boardings`
- `alightings`
- `transfer_count`
- `avg_wait_ticks`
- `crowding_ratio`
- `served_line_ids`

Validation rules:
- All count fields MUST be non-negative
- `crowding_ratio` MUST be finite and >= 0
- In Phase 9 static-wiring scenarios, station summaries MAY remain zero-filled
  placeholders until passenger-flow updates are introduced

### `RunMetrics`

- `tick_index`
- `active_agents`
- `queued_trip_requests`
- `completed_trips_total`
- `failed_trips_total`
- `capacity_violation_count`
- `negative_queue_detected` (bool, should remain false)
- `hotspot_links_top_k`
- `ui_packets_emitted`

### `RunSummary`

- `scenario_id`
- `seed`
- `scenario_mode` (road_only, multimodal)
- `day_type/time schedule config`
- `trip_generation_total`
- `trip_completion_rate`
- `median_trip_time`
- `p95_trip_time`
- `bridge_corridor_hotspot_frequency`
- `realism_report` (optional `RealismReport`)
- `station_summaries` (optional list[`StationSummary`])
- `tick_rate_median`
- `tick_rate_p10`
- `invariant_violation_counts`

Validation rules:
- Fixed seed + same scenario config MUST reproduce identical totals for trip
  generation and completion, and matching invariant counts
- `station_summaries` MUST be empty or omitted in road-only mode

## UI Source Data Entities (Pre-Packet)

### `UISnapshotSource`

- `network_geometry_version`
- `sampled_link_congestion` (possibly downsampled)
- `active_events`
- `clock_state` (day type, time band, sim tick)
- `summary_metrics`
- `station_summaries` (optional, phase-gated transit aggregate view)
- `transit_static_overlay` (optional stations/lines/connectors snapshot)

Purpose:
- Intermediate representation used by the UI packet contract to keep simulation
  state separate from transport schema and throttling policy.

## State Transitions (Simulation Tick)

The planned step pipeline (pure-function oriented) is:

1. Apply control input (day/time toggles, pause/resume, event injections)
2. Activate or clear scheduled `TrafficEvent` entries for current tick
3. Generate/activate `TripRequest` entries due at current tick
4. Allocate `ActiveAgentSlot` entries from free pool for newly activated trips
5. Refresh route candidates / dynamic potential as needed
6. Choose route actions via baseline + adaptive blend (with fallback support)
7. Update `NodeState` turn allocations and `LinkState` inflow/outflow
8. Advance active agent progress and complete/terminate trips
9. Update bandit/plugin learning state from simulator outcomes (online only)
10. Validate invariants and accumulate `RunMetrics`
11. Build throttled `UISnapshotSource` for optional UI packet emission

## Invariant Checklist (Model-Level)

- Conservation: tracked active agents + completed trips + failed trips + pending
  trip requests MUST reconcile with generated trip totals (within defined staging
  transitions at tick boundaries)
- No negative queue lengths on any link
- Capacity violations MUST be detected and counted when effective outflow exceeds
  allowed capacity
- Day/time transitions MUST affect future trip generation without corrupting
  in-progress trip state
- Fixed seed runs MUST reproduce the same scenario generation and run-summary
  totals under the same control/event sequence
